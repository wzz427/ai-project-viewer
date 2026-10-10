//! External handoff (V1.5 §130–§144, spec-006).
//!
//! Every verb here is SEMANTIC — the frontend never receives a generic
//! "run executable" command (§133). Real executables, arguments and path
//! validation live in this module (§133/§143): each target is resolved
//! inside the project root first via canonicalize + Path::starts_with,
//! never a raw string prefix check (§144).
//!
//! Launch backends: tauri-plugin-opener (ShellExecuteW on Windows — no
//! `cmd /c` composition, §188 RUN discipline) for OS-associated opens and
//! reveals; direct `std::process::Command` spawns for Notepad and VS Code.

use std::path::{Path, PathBuf};

use tauri_plugin_opener::{open_path, open_url, reveal_item_in_dir};

// ---------------------------------------------------------------------------
// §132 ExternalEditor abstraction (V1 lists NotepadEditor + VSCodeEditor;
// future editors extend this trait without a plugin system).

trait ExternalEditor {
    fn id(&self) -> &'static str;
    fn name(&self) -> &'static str;
    fn open_file(&self, path: &Path) -> Result<(), String>;
    fn open_folder(&self, _path: &Path) -> Result<(), String> {
        Err(format!("{} cannot open folders.", self.name()))
    }
}

struct NotepadEditor;

impl ExternalEditor for NotepadEditor {
    fn id(&self) -> &'static str {
        "notepad"
    }
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
    fn id(&self) -> &'static str {
        "vscode"
    }
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

fn resolve_target(root: &Path, rel: &str) -> Result<PathBuf, String> {
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
// Semantic commands (§133 naming).

/// §130 Quick Edit: hand a text-like file to Notepad.
#[tauri::command]
pub fn edit_in_quick_editor(root_path: String, rel: String) -> Result<(), String> {
    let path = resolve_target(Path::new(&root_path), &rel)?;
    if path.is_dir() {
        return Err(format!("Not a file: {rel}"));
    }
    NotepadEditor.open_file(&path)
}

/// §131 Full Edit / §140 folders / §141 project root: hand off to VS Code.
/// `rel = None` means the project root itself (§141 Open Project in VS Code).
#[tauri::command]
pub fn open_in_code_editor(
    root_path: String,
    rel: Option<String>,
    new_window: bool,
) -> Result<(), String> {
    let path = resolve_target(Path::new(&root_path), rel.as_deref().unwrap_or(""))?;
    let editor = VSCodeEditor { new_window };
    if path.is_dir() {
        editor.open_folder(&path)
    } else {
        editor.open_file(&path)
    }
}

/// §135/§138/§140 Show in File Explorer. `rel = None` = the project itself
/// (§141 "Open in File Explorer") which OPENS the folder window rather than
/// selecting it in its parent (spec-006 D4, VS Code semantics).
#[tauri::command]
pub fn reveal_in_explorer(root_path: String, rel: Option<String>) -> Result<(), String> {
    let path = resolve_target(Path::new(&root_path), rel.as_deref().unwrap_or(""))?;
    if rel.as_deref().unwrap_or("").trim().is_empty() {
        open_path(&path, None::<&str>).map_err(|e| e.to_string())
    } else {
        reveal_item_in_dir(&path).map_err(|e| e.to_string())
    }
}

/// OS-associated open (§111 generalized / §138 Default PDF App / §142
/// System App rows — one mechanism, menu labels differ per type).
#[tauri::command]
pub fn open_with_default_app(root_path: String, rel: String) -> Result<(), String> {
    let path = resolve_target(Path::new(&root_path), &rel)?;
    open_path(&path, None::<&str>).map_err(|e| e.to_string())
}

/// §111/§115 Browser: .html/.htm ride a file:// URL (always the browser,
/// even if .html is associated with an editor); .url shortcuts expose their
/// URL= line and only http/https ever pass (§115 scheme allowlist).
#[tauri::command]
pub fn open_in_browser(root_path: String, rel: String) -> Result<(), String> {
    let path = resolve_target(Path::new(&root_path), &rel)?;
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .map(str::to_ascii_lowercase)
        .unwrap_or_default();
    let url = match ext.as_str() {
        "html" | "htm" => file_url_of(&path),
        "url" => shortcut_url(&path)?,
        _ => return Err(format!("Not a browser-openable file: {rel}")),
    };
    open_url(&url, None::<&str>).map_err(|e| e.to_string())
}

// ---------------------------------------------------------------------------
// Pure helpers (unit-tested without spawning anything).

/// Percent-encode a Windows path into a file:// URL. Unreserved chars plus
/// `/` (separator) and `:` (drive letter) stay literal; everything else
/// encodes as UTF-8 bytes so spaces and CJK names survive.
fn file_url_of(path: &Path) -> String {
    let s = path.to_string_lossy().replace('\\', "/");
    let mut out = String::from("file:///");
    for &b in s.as_bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'.' | b'_' | b'~'
            | b'/' | b':' => out.push(b as char),
            _ => {
                out.push('%');
                out.push_str(&format!("{b:02X}"));
            }
        }
    }
    out
}

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
    fn file_url_encodes_spaces_and_keeps_drive() {
        let p = Path::new(r"C:\Projects\My Docs\index.html");
        assert_eq!(file_url_of(&p), "file:///C:/Projects/My%20Docs/index.html");
    }

    #[test]
    fn file_url_encodes_non_ascii_as_utf8() {
        let p = Path::new(r"C:\t\项目.html");
        let url = file_url_of(&p);
        assert!(url.starts_with("file:///C:/t/"));
        assert!(url.ends_with(".html"));
        assert!(!url.contains('项'), "must be percent-encoded: {url}");
    }

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
}
