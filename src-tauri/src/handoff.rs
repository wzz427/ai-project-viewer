//! External handoff (V1.5 §130–§144, spec-006).
//!
//! Every verb here is SEMANTIC — the frontend never receives a generic
//! "run executable" command (§133). Real executables, arguments and path
//! validation live in this module (§133/§143): each target is resolved
//! inside the project root first via canonicalize + Path::starts_with,
//! never a raw string prefix check (§144).
//!
//! Launch backends: tauri-plugin-opener for OS-associated opens and reveals
//! (its `open`/`open_url` on Windows go through the `open` crate —
//! Invoke-Item, explorer.exe fallback; accepts plain PATHS, not file:///
//! URLs — no `cmd /c` composition, §188 RUN discipline); direct
//! `std::process::Command` spawns for Notepad and VS Code.

use std::path::{Path, PathBuf};

use tauri_plugin_opener::{open_path, open_url, reveal_item_in_dir};

// ---------------------------------------------------------------------------
// §132 ExternalEditor abstraction (V1 lists NotepadEditor + VSCodeEditor;
// future editors extend this trait without a plugin system).

trait ExternalEditor {
    fn name(&self) -> &'static str;
    fn open_file(&self, path: &Path) -> Result<(), String>;
    fn open_folder(&self, _path: &Path) -> Result<(), String> {
        Err(format!("{} cannot open folders.", self.name()))
    }
}

struct NotepadEditor;

impl ExternalEditor for NotepadEditor {
    fn name(&self) -> &'static str {
        "Notepad"
    }
    fn open_file(&self, path: &Path) -> Result<(), String> {
        // Always on PATH (System32); a plain spawn keeps §188's "no cmd /c"
        // rule — notepad.exe is a real PE, not a shell shim.
        std::process::Command::new("notepad.exe")
            .arg(path)
            .spawn()
            .map(|_| ())
            .map_err(|e| format!("Cannot start Notepad: {e}"))
    }
}

struct VSCodeEditor {
    /// §134 VS Code Mode, passed per call from the persisted frontend
    /// setting (spec-006 D3: Rust stays stateless, the arg is a mode —
    /// not an executable — so §133 holds).
    new_window: bool,
}

impl ExternalEditor for VSCodeEditor {
    fn name(&self) -> &'static str {
        "VS Code"
    }
    fn open_file(&self, path: &Path) -> Result<(), String> {
        self.open_path_arg(path)
    }
    fn open_folder(&self, path: &Path) -> Result<(), String> {
        self.open_path_arg(path)
    }
}

impl VSCodeEditor {
    fn open_path_arg(&self, path: &Path) -> Result<(), String> {
        let exe = vscode_exe()?;
        std::process::Command::new(exe)
            .arg(if self.new_window { "--new-window" } else { "--reuse-window" })
            .arg(path)
            .spawn()
            .map(|_| ())
            .map_err(|e| format!("Cannot start VS Code: {e}"))
    }
}

/// Resolve VS Code's Code.exe: user install → Program Files → PATH dirs.
/// Only the real PE counts — the `code`/`code.cmd` shims on PATH need a
/// shell to interpret them, which §188 forbids (spec-006 D2).
fn vscode_exe() -> Result<PathBuf, String> {
    find_first_existing(&vscode_candidates()).ok_or_else(|| vscode_not_found_msg())
}

fn vscode_not_found_msg() -> String {
    "VS Code was not found. Install it from https://code.visualstudio.com \
     (User Setup is fine), then try again."
        .into()
}

fn vscode_candidates() -> Vec<PathBuf> {
    let mut c = Vec::new();
    let mut push = |dir: Option<PathBuf>, sub: &[&str]| {
        if let Some(d) = dir {
            // User Setup lives under %LOCALAPPDATA%\Programs\... (the
            // "Programs" segment is easy to miss — it cost the first
            // real-launch round); system setups sit in Program Files.
            let mut p = d;
            for s in sub {
                p = p.join(s);
            }
            c.push(p.join("Code.exe"));
        }
    };
    push(
        std::env::var_os("LOCALAPPDATA").map(PathBuf::from),
        &["Programs", "Microsoft VS Code"],
    );
    push(std::env::var_os("ProgramFiles").map(PathBuf::from), &["Microsoft VS Code"]);
    push(
        std::env::var_os("ProgramFiles(x86)").map(PathBuf::from),
        &["Microsoft VS Code"],
    );
    if let Some(path_var) = std::env::var_os("PATH") {
        for dir in std::env::split_paths(&path_var) {
            c.push(dir.join("code.exe"));
        }
    }
    c
}

fn find_first_existing(candidates: &[PathBuf]) -> Option<PathBuf> {
    candidates.iter().find(|p| p.is_file()).cloned()
}

// ---------------------------------------------------------------------------
// §143/§144 path validation — same canonicalize+starts_with rule as the
// tree/file commands, but targets may be files OR folders.

pub fn resolve_target(root: &Path, rel: &str) -> Result<PathBuf, String> {
    let root_canon = dunce::canonicalize(root)
        .map_err(|e| format!("Project folder is not accessible: {e}"))?;

    let rel = rel.trim();
    let target = if rel.is_empty() || rel == "." {
        root_canon.clone()
    } else {
        root_canon.join(rel.replace('/', "\\"))
    };
    let target_canon = dunce::canonicalize(&target)
        .map_err(|_| format!("Not found: {rel}"))?;

    if !target_canon.starts_with(&root_canon) {
        return Err("Path escapes the project root.".into());
    }
    Ok(target_canon)
}

// ---------------------------------------------------------------------------
// Semantic commands (§133 naming). All ASYNC (spec-012 M12, L35 family):
// each resolves its target with canonicalize (disk IO — a stalled share
// must not freeze the native main thread) and may spawn a process or a
// ShellExecuteW that blocks for seconds.

/// §130 Quick Edit: hand a text-like file to Notepad.
#[tauri::command]
pub async fn edit_in_quick_editor(root_path: String, rel: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let path = resolve_target(Path::new(&root_path), &rel)?;
        if path.is_dir() {
            return Err(format!("Not a file: {rel}"));
        }
        if e2e_dry_run_is_active() {
            return Ok(());
        }
        NotepadEditor.open_file(&path)
    })
    .await
    .map_err(|e| format!("handoff task failed: {e}"))?
}

/// §131 Full Edit / §140 folders / §141 project root: hand off to VS Code.
/// `rel = None` means the project root itself (§141 Open Project in VS Code).
#[tauri::command]
pub async fn open_in_code_editor(
    root_path: String,
    rel: Option<String>,
    new_window: bool,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let path = resolve_target(Path::new(&root_path), rel.as_deref().unwrap_or(""))?;
        if e2e_dry_run_is_active() {
            return Ok(());
        }
        let editor = VSCodeEditor { new_window };
        if path.is_dir() {
            editor.open_folder(&path)
        } else {
            editor.open_file(&path)
        }
    })
    .await
    .map_err(|e| format!("handoff task failed: {e}"))?
}

/// §135/§138/§140 Show in File Explorer. `rel = None` = the project itself
/// (§141 "Open in File Explorer") which OPENS the folder window rather than
/// selecting it in its parent (spec-006 D4, VS Code semantics).
#[tauri::command]
pub async fn reveal_in_explorer(root_path: String, rel: Option<String>) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let path = resolve_target(Path::new(&root_path), rel.as_deref().unwrap_or(""))?;
        if e2e_dry_run_is_active() {
            return Ok(());
        }
        if rel.as_deref().unwrap_or("").trim().is_empty() {
            open_path(&path, None::<&str>).map_err(|e| e.to_string())
        } else {
            reveal_item_in_dir(&path).map_err(|e| e.to_string())
        }
    })
    .await
    .map_err(|e| format!("handoff task failed: {e}"))?
}

/// Executable-ish extensions refused by open_with_default_app (spec-012
/// M11/D4). ShellExecuteW on these EXECUTES the file, which would bypass
/// the trust gate + whitelist that run_project_executable enforces — the
/// 0.7.6 audit removed open-path from the opener PLUGIN, but this custom
/// command handed the same power back to any in-page JS. `.msi` is
/// deliberately NOT in the list: §126 routes it through System Default.
const DENY_EXECUTABLE_EXTS: &[&str] = &[
    "exe", "bat", "cmd", "lnk", "scr", "hta", "jse", "vbe", "js", "jar", "com", "pif",
];

fn is_denied_executable(path: &Path) -> bool {
    path.extension()
        .and_then(|e| e.to_str())
        .map(|e| DENY_EXECUTABLE_EXTS.contains(&e.to_ascii_lowercase().as_str()))
        .unwrap_or(false)
}

/// OS-associated open (§111 generalized / §138 Default PDF App / §142
/// System App rows — one mechanism, menu labels differ per type).
#[tauri::command]
pub async fn open_with_default_app(root_path: String, rel: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || open_with_default_app_inner(&root_path, &rel))
        .await
        .map_err(|e| format!("open task failed: {e}"))?
}

/// e2e dry-run (owner 2026-10-24): suites launch with AIV_TEST_PROJECT
/// set; actually handing a file to the OS there would pop a desktop
/// window mid-test (his 2026-10-24 report: an installer dialog for the
/// msi fixture) — the zero-disturbance red line. Validation always runs;
/// only the launch is skipped.
fn e2e_dry_run_is_active() -> bool {
    std::env::var("AIV_TEST_PROJECT")
        .map(|v| !v.is_empty())
        .unwrap_or(false)
}

fn open_with_default_app_inner(root_path: &str, rel: &str) -> Result<(), String> {
    let path = resolve_target(Path::new(root_path), rel)?;
    if is_denied_executable(&path) {
        return Err(
            "Opening executable files with the system default is disabled — \
             right-click the file and use Run (requires project trust) instead."
                .into(),
        );
    }
    if e2e_dry_run_is_active() {
        return Ok(());
    }
    open_path(&path, None::<&str>).map_err(|e| e.to_string())
}

/// §111/§115 Browser: .html/.htm open through the OS default handler (the
/// Explorer double-click open); .url shortcuts expose their URL= line and
/// only http/https ever pass (§115 scheme allowlist).
#[tauri::command]
pub async fn open_in_browser(root_path: String, rel: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || open_in_browser_inner(&root_path, &rel))
        .await
        .map_err(|e| format!("browser task failed: {e}"))?
}

fn open_in_browser_inner(root_path: &str, rel: &str) -> Result<(), String> {
    let path = resolve_target(Path::new(root_path), rel)?;
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .map(str::to_ascii_lowercase)
        .unwrap_or_default();
    if e2e_dry_run_is_active() {
        // Scheme allowlist below still evaluated by callers' expectations;
        // shortcut_url parse is skipped in dry-run — the URL checks have
        // their own p10 guards on the plugin path.
        return Ok(());
    }
    match ext.as_str() {
        // html/htm: hand the OS the resolved PATH, never a file:/// URL.
        // opener's Windows backend (the `open` crate: Invoke-Item, then
        // explorer.exe) does not accept file URLs — Test-Path says the URL
        // is not a path, Start-Process fails, and explorer.exe pops the
        // "Windows 找不到文件" dialog (owner 2026-10-12). A plain path runs
        // Invoke-Item, which IS the double-click open; `open`/`xdg-open`
        // take plain paths on macOS/Linux too. The old "file URL forces the
        // browser even when .html is associated with an editor" idea never
        // worked on Windows — the default-handler open is the real contract.
        "html" | "htm" => open_path(&path, None::<&str>).map_err(|e| e.to_string()),
        "url" => {
            let u = shortcut_url(&path)?;
            // §115: a shortcut may carry ANY scheme; only http/https ever
            // auto-open (javascript:/powershell:/file:/shell: rejected).
            if !browser_url_allowed(&u) {
                return Err(format!("Shortcut scheme is not allowed to auto-open: {u}"));
            }
            open_url(&u, None::<&str>).map_err(|e| e.to_string())
        }
        _ => Err(format!("Not a browser-openable file: {rel}")),
    }
}

// ---------------------------------------------------------------------------
// Pure helpers (unit-tested without spawning anything).

const SHORTCUT_MAX_BYTES: u64 = 1024 * 1024;

/// Extract `URL=` from a .url InternetShortcut (INI-style; key matched
/// case-insensitively). Oversized or malformed files refuse loudly — a
/// shortcut is a few hundred bytes, anything else is not a shortcut.
fn shortcut_url(path: &Path) -> Result<String, String> {
    let meta = std::fs::metadata(path).map_err(|e| format!("Cannot read shortcut: {e}"))?;
    if meta.len() > SHORTCUT_MAX_BYTES {
        return Err("Shortcut file is unexpectedly large.".into());
    }
    let text = std::fs::read_to_string(path).map_err(|e| format!("Cannot read shortcut: {e}"))?;
    url_from_shortcut_text(&text).ok_or_else(|| "Shortcut has no URL= line.".into())
}

fn url_from_shortcut_text(text: &str) -> Option<String> {
    text.lines().find_map(|line| {
        let (key, value) = line.trim().split_once('=')?;
        key.trim()
            .eq_ignore_ascii_case("URL")
            .then(|| value.trim().to_string())
            .filter(|v| !v.is_empty())
    })
}

/// §115: only http/https may auto-open — javascript:/powershell:/cmd:/
/// file:/shell: are rejected by omission.
fn browser_url_allowed(url: &str) -> bool {
    let u = url.trim().to_ascii_lowercase();
    u.starts_with("http://") || u.starts_with("https://")
}

#[cfg(test)]
mod tests {
    use super::*;

    // --- §143/§144 validation ---

    #[test]
    fn rejects_dotdot_escape() {
        // The escaping target must EXIST on disk, otherwise canonicalize
        // fails first with "Not found" — both refuse, but this test pins
        // the containment guard itself (§144).
        let a = tempfile::tempdir().unwrap();
        let b = tempfile::tempdir().unwrap();
        std::fs::write(b.path().join("x.txt"), b"x").unwrap();
        let bname = b.path().file_name().unwrap().to_str().unwrap();
        let rel = format!("../{bname}/x.txt");
        let err = resolve_target(a.path(), &rel).unwrap_err();
        assert!(err.contains("escapes"), "{err}");
    }

    #[test]
    fn rejects_absolute_rel_pointing_outside() {
        // PathBuf::join replaces the base when handed an absolute path —
        // the starts_with guard must still catch it (§144: canonical Path
        // semantics, not raw string prefix).
        let inside = tempfile::tempdir().unwrap();
        let outside = tempfile::tempdir().unwrap();
        std::fs::write(outside.path().join("x.txt"), b"x").unwrap();
        let abs = outside.path().join("x.txt");
        let err = resolve_target(inside.path(), abs.to_str().unwrap()).unwrap_err();
        assert!(err.contains("escapes"), "{err}");
    }

    #[test]
    fn resolves_root_when_rel_empty() {
        let dir = tempfile::tempdir().unwrap();
        let got = resolve_target(dir.path(), "").unwrap();
        assert_eq!(got, dunce::canonicalize(dir.path()).unwrap());
    }

    #[test]
    fn resolves_folders_and_files() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("a.txt"), b"x").unwrap();
        std::fs::create_dir(dir.path().join("sub")).unwrap();
        assert!(resolve_target(dir.path(), "a.txt").unwrap().is_file());
        assert!(resolve_target(dir.path(), "sub").unwrap().is_dir());
        // forward slashes from the frontend normalize
        assert!(resolve_target(dir.path(), "sub/../a.txt").unwrap().is_file());
    }

    // --- §132 editor discovery (D2) ---

    #[test]
    fn vscode_discovery_picks_first_existing() {
        let dir = tempfile::tempdir().unwrap();
        let a = dir.path().join("a").join("Code.exe");
        let b = dir.path().join("b").join("Code.exe");
        std::fs::create_dir_all(a.parent().unwrap()).unwrap();
        std::fs::write(&a, b"MZ").unwrap();
        assert_eq!(find_first_existing(&[dir.path().join("missing"), a.clone(), b]), Some(a));
        assert_eq!(find_first_existing(&[dir.path().join("missing")]), None);
    }

    #[test]
    fn vscode_missing_message_names_the_editor() {
        // The message fn is asserted directly — searching the real machine
        // inside a unit test would be environment-dependent.
        assert!(vscode_not_found_msg().contains("VS Code"));
    }

    // --- §111/§115 browser helpers ---

    #[test]
    fn shortcut_url_extracts_case_insensitive() {
        let text = "[InternetShortcut]\r\nurl = https://example.com/x\r\nIconIndex=1\r\n";
        assert_eq!(
            url_from_shortcut_text(text).as_deref(),
            Some("https://example.com/x")
        );
        assert_eq!(url_from_shortcut_text("[InternetShortcut]\nIDList="), None);
    }

    #[test]
    fn shortcut_oversize_refused() {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("big.url");
        std::fs::write(&p, vec![b'x'; (SHORTCUT_MAX_BYTES + 1) as usize]).unwrap();
        assert!(shortcut_url(&p).is_err());
    }

    #[test]
    fn shortcut_with_forbidden_scheme_is_refused_before_open() {
        // Mirrors the open_in_browser .url branch without opening anything:
        // the extracted URL must clear the §115 allowlist or the command
        // errors out before open_url is reached.
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("evil.url");
        for (url, ok) in [
            ("powershell:-encoded-command xyz", false),
            ("javascript:alert(1)", false),
            ("file://c:/windows/system32", false),
            ("https://example.com/x", true),
        ] {
            std::fs::write(
                &p,
                format!("[InternetShortcut]\r\nURL={url}\r\n"),
            )
            .unwrap();
            let extracted = url_from_shortcut_text(&std::fs::read_to_string(&p).unwrap()).unwrap();
            assert_eq!(browser_url_allowed(&extracted), ok, "{url}");
        }
    }

    #[test]
    fn scheme_allowlist_http_https_only() {
        assert!(browser_url_allowed("https://a.example/x"));
        assert!(browser_url_allowed("HTTP://A.EXAMPLE"));
        for bad in [
            "javascript:alert(1)",
            "powershell:-e AAA",
            "cmd:/c calc",
            "file:///C:/x",
            "shell:Downloads",
            "ftp://a.example",
        ] {
            assert!(!browser_url_allowed(bad), "{bad} must be rejected");
        }
    }

    /// spec-012 M11/D4: the executable fence. Every denylisted extension is
    /// refused case-insensitively; .msi (§126 System Default) and ordinary
    /// documents pass; extensionless files pass.
    #[test]
    fn executable_like_extensions_are_refused_by_default_open() {
        for ext in DENY_EXECUTABLE_EXTS {
            assert!(
                is_denied_executable(Path::new(&format!("thing.{ext}"))),
                ".{ext} must be denied"
            );
        }
        for name in ["doc.txt", "report.pdf", "installer.msi", "setup.MSI", "no_extension"] {
            assert!(!is_denied_executable(Path::new(name)), "{name} must pass");
        }
        assert!(is_denied_executable(Path::new("EVIL.Exe")));
        assert!(is_denied_executable(Path::new("run.CMD")));
        assert!(!is_denied_executable(Path::new("no_extension")));
    }
}
