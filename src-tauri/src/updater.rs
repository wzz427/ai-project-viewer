//! Experience-channel update mechanism (SPEC-INFRA-001).
//!
//! The owner runs an "experience" build that lives in its own directory,
//! fully isolated from development builds. Shipping a new version =
//! dropping the new exe + update.json into an `updates\` directory next to
//! the app; the client compares file CONTENT (streamed md5 — no whole-file
//! buffers, memory-minimization principle) and swaps itself when asked.
//!
//! Windows allows renaming a running exe, so the swap is:
//!   copy updates\app.exe -> app\*.new   (verify md5)
//!   rename current exe   -> *.old
//!   rename *.new         -> current name
//! Restarting loads the new version; stale .old/.new are cleaned at boot.
//!
//! Everything is local file sync — no network, no signatures, no update
//! server (V1.5 §184 keeps the online updater out of scope).

use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

use serde::Serialize;

const UPDATE_NOTE: &str = "update.json";

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateInfo {
    pub available: bool,
    pub note: String,
}

/// updates\ lives next to the app directory:
/// `<parent>\app\ai-project-viewer.exe` + `<parent>\updates\...`.
/// In dev builds (exe inside target\) the folder simply doesn't exist and
/// check_update reports nothing — the mechanism only arms itself where the
/// experience build is installed.
fn layout() -> Option<(PathBuf, PathBuf)> {
    let exe = std::env::current_exe().ok()?;
    let app_dir = exe.parent()?.to_path_buf();
    let updates = app_dir.parent()?.join("updates");
    Some((app_dir, updates))
}

fn md5_of(path: &Path) -> Result<String, String> {
    let mut ctx = md5::Context::new();
    let mut file = fs::File::open(path).map_err(|e| format!("Cannot open {}: {e}", path.display()))?;
    let mut buf = [0u8; 8192]; // streamed: O(8KB) regardless of file size
    loop {
        let n = file.read(&mut buf).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        ctx.consume(&buf[..n]);
    }
    Ok(format!("{:x}", ctx.compute()))
}

fn read_note(updates: &Path) -> String {
    fs::read_to_string(updates.join(UPDATE_NOTE))
        .ok()
        .and_then(|text| {
            // PowerShell's `Out-File -Encoding utf8` writes a BOM (lessons
            // L2 family) — strip it before parsing.
            let text = text.trim_start_matches('\u{feff}').to_string();
            serde_json::from_str::<serde_json::Value>(&text)
                .ok()
                .and_then(|v| {
                    v.get("note")
                        .and_then(|n| n.as_str())
                        .map(str::to_string)
                })
        })
        .unwrap_or_default()
}

#[tauri::command]
pub fn check_update() -> UpdateInfo {
    let Some((app_dir, updates)) = layout() else {
        return UpdateInfo { available: false, note: String::new() };
    };
    let incoming = updates.join("ai-project-viewer.exe");
    let current = match std::env::current_exe() {
        Ok(p) => p,
        Err(_) => return UpdateInfo { available: false, note: String::new() },
    };
    let _ = app_dir;
    let available = match (md5_of(&incoming), md5_of(&current)) {
        (Ok(a), Ok(b)) => a != b,
        _ => false, // no update staged or unreadable -> not available
    };
    UpdateInfo { available, note: read_note(&updates) }
}

/// Pure swap logic, unit-tested against a tempdir (no running-exe games
/// in tests).
pub fn perform_swap(current: &Path, incoming: &Path) -> Result<(), String> {
    let staged = current.with_extension("exe.new");
    fs::copy(incoming, &staged).map_err(|e| format!("Copy failed: {e}"))?;
    let want = md5_of(incoming)?;
    if md5_of(&staged)? != want {
        let _ = fs::remove_file(&staged);
        return Err("Staged copy failed verification.".into());
    }
    let backup = current.with_extension("exe.old");
    let _ = fs::remove_file(&backup);
    fs::rename(current, &backup).map_err(|e| format!("Backup failed: {e}"))?;
    if let Err(e) = fs::rename(&staged, current) {
        // roll back so the running app keeps its original binary
        let _ = fs::rename(&backup, current);
        return Err(format!("Swap failed: {e}"));
    }
    Ok(())
}

#[tauri::command]
pub fn apply_update() -> Result<(), String> {
    let Some((_, updates)) = layout() else {
        return Err("Not an experience install.".into());
    };
    let incoming = updates.join("ai-project-viewer.exe");
    if !incoming.exists() {
        return Err("No update staged.".into());
    }
    let current = std::env::current_exe().map_err(|e| e.to_string())?;
    perform_swap(&current, &incoming)
}

/// Best-effort removal of leftovers from a previous swap (called from
/// setup — the old binary can only be deleted once it's not running).
pub fn clean_stale_swap_files() {
    if let Ok(exe) = std::env::current_exe() {
        let _ = fs::remove_file(exe.with_extension("exe.old"));
        let _ = fs::remove_file(exe.with_extension("exe.new"));
    }
}

/// Restart into the (just-updated) binary: spawn a fresh instance, then
/// exit. The single-instance plugin only guards same-identifier apps; the
/// child starts as this process dies, so activation races are avoided by
/// the exit-then-start ordering here.
#[tauri::command]
pub fn relaunch() -> Result<(), String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    std::process::Command::new(&exe)
        .spawn()
        .map_err(|e| format!("Cannot relaunch: {e}"))?;
    std::process::exit(0);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn swap_replaces_content_and_cleans_up() {
        let dir = tempfile::tempdir().unwrap();
        let updates = dir.path().join("updates");
        fs::create_dir_all(&updates).unwrap();
        let current = dir.path().join("app.exe");
        let incoming = updates.join("ai-project-viewer.exe");
        fs::write(&current, b"version-1").unwrap();
        fs::write(&incoming, b"version-2").unwrap();

        perform_swap(&current, &incoming).unwrap();
        assert_eq!(fs::read(&current).unwrap(), b"version-2");
        assert!(current.with_extension("exe.old").exists(), "backup kept for the running session");
    }

    #[test]
    fn corrupted_staged_copy_is_rejected() {
        let dir = tempfile::tempdir().unwrap();
        let current = dir.path().join("app.exe");
        let incoming = dir.path().join("new.exe");
        fs::write(&current, b"version-1").unwrap();
        // incoming unreadable -> md5 fails -> whole swap refuses
        let err = perform_swap(&current, &incoming);
        assert!(err.is_err());
        assert_eq!(fs::read(&current).unwrap(), b"version-1", "original untouched");
    }

    #[test]
    fn md5_is_content_addressed() {
        let dir = tempfile::tempdir().unwrap();
        let a = dir.path().join("a");
        fs::write(&a, b"same").unwrap();
        let b = dir.path().join("b");
        fs::write(&b, b"same").unwrap();
        let c = dir.path().join("c");
        fs::write(&c, b"different").unwrap();
        assert_eq!(md5_of(&a).unwrap(), md5_of(&b).unwrap());
        assert_ne!(md5_of(&a).unwrap(), md5_of(&c).unwrap());
    }
}
