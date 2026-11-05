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
use std::sync::OnceLock;
use std::time::Duration;

use notify_debouncer_full::notify::RecursiveMode;
use notify_debouncer_full::{new_debouncer_opt, notify, Debouncer, NoCache};
use serde::Serialize;
use tauri::Emitter;

const UPDATE_NOTE: &str = "update.json";

/// spec-019: event name for "the updates folder changed on disk". Dumb on
/// purpose (D2) — the frontend re-runs check_update, the only place that
/// decides availability; no IO happens on the watcher thread.
pub const UPDATE_STAGED_EVENT: &str = "update-staged";

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
    use md5::{Digest, Md5};
    let mut hasher = Md5::new();
    let mut file = fs::File::open(path).map_err(|e| format!("Cannot open {}: {e}", path.display()))?;
    let mut buf = [0u8; 8192]; // streamed: O(8KB) regardless of file size
    loop {
        let n = file.read(&mut buf).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(format!("{:x}", hasher.finalize()))
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

/// Pure availability decision: an update exists iff BOTH hashes read AND
/// they differ. None on either side = nothing staged/unreadable → quiet.
fn decide(incoming_md5: Option<String>, current_md5: Option<String>) -> bool {
    matches!((incoming_md5, current_md5), (Some(a), Some(b)) if a != b)
}

/// ASYNC on purpose (spec-012 H2, L35 family): UpdateButton invokes this on
/// mount, so a sync command would md5 the whole running exe (~6 MB) on the
/// NATIVE main thread at every experience-client startup — even in dev
/// builds where no `updates\` exists.
#[tauri::command]
pub async fn check_update() -> UpdateInfo {
    tauri::async_runtime::spawn_blocking(check_update_blocking)
        .await
        .unwrap_or_else(|_| UpdateInfo { available: false, note: String::new() })
}

fn check_update_blocking() -> UpdateInfo {
    let Some((_app_dir, updates)) = layout() else {
        return UpdateInfo { available: false, note: String::new() };
    };
    let incoming = updates.join("ai-project-viewer.exe");
    // Gate BEFORE any read: with nothing staged (every dev build) the old
    // code still md5'd the running exe (spec-012 H2 — the tuple evaluated
    // both arms).
    if !incoming.exists() {
        return UpdateInfo { available: false, note: read_note(&updates) };
    }
    let current = match std::env::current_exe() {
        Ok(p) => p,
        Err(_) => return UpdateInfo { available: false, note: read_note(&updates) },
    };
    let available = decide(md5_of(&incoming).ok(), md5_of(&current).ok());
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

/// ASYNC on purpose (spec-012 H2): the swap copies the whole exe and md5s
/// it twice more (~24 MB IO) — clicking Update on a sync command froze the
/// window for the whole copy.
#[tauri::command]
pub async fn apply_update() -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(apply_update_blocking)
        .await
        .map_err(|e| format!("update task failed: {e}"))?
}

fn apply_update_blocking() -> Result<(), String> {
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

/// The running update watcher, if one was started (spec-019). Held for its
/// Drop side effect only — dropping the debouncer stops the watch and joins
/// its thread; since the slot is process-lifetime, that happens at exit.
static UPDATE_WATCH: OnceLock<Option<Debouncer<notify::RecommendedWatcher, NoCache>>> =
    OnceLock::new();

/// Light the owner's Update button the moment a new build LANDS in the
/// updates folder (spec-019, owner 2026-11-05: "你让我更新的时候,你自己
/// 去点亮 update" — the app being open must not hide a publish).
///
/// Event-driven, NOT polling (SPEC-INFRA-001 keeps polls out; D1): one
/// non-recursive notify watch on the updates dir with a 600 ms debounce
/// absorbs the publish script's copy/delete churn, then one dumb event —
/// the frontend's check_update (exists-gated, md5-comparing) is the single
/// decider of "available", so a mid-rename gap reads as "nothing staged"
/// instead of a false light, and the atomic publish (D3) means the file
/// the button offers is always complete. Dev builds have no updates\
/// -> no watcher, zero cost (R4). Failures are quiet by design: the button
/// keeps its mount-time check and click-to-recheck as fallbacks.
pub fn watch_updates(app: tauri::AppHandle) {
    let Some((_app_dir, updates)) = layout() else { return };
    if !updates.is_dir() {
        return;
    }
    let app_for_events = app.clone();
    let debounced = move |result: notify_debouncer_full::DebounceEventResult| {
        // Only real events matter; watcher errors just go quiet (fallbacks
        // above cover the owner).
        if let Ok(events) = result {
            if !events.is_empty() {
                let _ = app_for_events.emit(UPDATE_STAGED_EVENT, ());
            }
        }
    };
    // Timeout is required by the debouncer but irrelevant here: there is no
    // second tick to merge — the events themselves are edge-triggered.
    // NoCache per watcher.rs (L33): the file-ID cache only pays off for
    // rename pairing, useless for a two-file flat directory.
    let Ok(mut debouncer) = new_debouncer_opt(
        Duration::from_millis(600),
        None,
        debounced,
        NoCache::new(),
        notify::Config::default(),
    ) else {
        return;
    };
    if debouncer.watch(&updates, RecursiveMode::NonRecursive).is_err() {
        return; // unreadable dir: stay on mount-check + manual recheck
    }
    let _ = UPDATE_WATCH.set(Some(debouncer)); // loser of the race drops = stops
}

/// Restart into the (just-updated) binary. `std::process::exit` bypasses
/// RunEvent::Exit — the exit-time state flush would never run, so the last
/// debounced window (e.g. a just-opened tab) was lost; flush SYNCHRONOUSLY
/// before spawning (spec-012 L-r4/D8). The single-instance plugin only
/// guards same-identifier apps; the child starts as this process dies, so
/// activation races are avoided by the spawn-then-exit ordering.
#[tauri::command]
pub fn relaunch(app: tauri::AppHandle) -> Result<(), String> {
    crate::state::flush_on_exit(&app);
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

    /// spec-012 H2: nothing staged (or unreadable) must read as "no update"
    /// — None on either arm stays quiet; only two differing hashes arm it.
    #[test]
    fn decide_requires_both_hashes_and_a_difference() {
        assert!(!decide(None, None));
        assert!(!decide(None, Some("x".into())));
        assert!(!decide(Some("x".into()), None));
        assert!(!decide(Some("x".into()), Some("x".into())));
        assert!(decide(Some("x".into()), Some("y".into())));
    }
}
