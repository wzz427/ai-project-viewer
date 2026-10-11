//! Script / EXE launching (V1.5 §116–§127, spec-008).
//!
//! Two SEMANTIC commands only (§133) — the frontend never receives a
//! generic "run anything" verb. Every target is resolved inside the
//! project root via canonicalize (§143/§144, same fence as handoff.rs),
//! and the runnable-extension whitelist lives HERE, not in the frontend.
//!
//! Console strategy (§117/§118, decided by the 2026-10-10 experiment —
//! spec-008 §一): scripts run under a PERSISTENT HOST so the console
//! survives the script body and its output stays readable —
//!   .cmd/.bat → cmd.exe /K <script>
//!   .ps1      → powershell.exe -NoExit -File <script>   (no -ExecutionPolicy
//!               flag: §120 obeys the system policy; a Restricted machine
//!               shows the policy error INSIDE the persistent window)
//! .exe launches directly (§123: absolute path, no cmd /c composition)
//! with cwd = its own directory (§124); console exes get CREATE_NEW_CONSOLE,
//! GUI exes just open their window.

use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};

use crate::handoff::resolve_target;

const CREATE_NEW_CONSOLE: u32 = 0x0000_0010;
/// Test-only stand-in (windowless host semantics): lives under cfg(test)
/// so production builds don't carry an unused constant.
#[cfg(test)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

pub const SCRIPT_EXTENSIONS: [&str; 3] = ["ps1", "cmd", "bat"];

fn ext_of(path: &Path) -> String {
    path.extension()
        .and_then(|e| e.to_str())
        .map(str::to_ascii_lowercase)
        .unwrap_or_default()
}

/// One argv element with Windows command-line encoding intent (§145,
/// Phase 10 audit).
#[derive(Debug)]
pub enum SpawnArg {
    /// Standard Rust quoting — host flags and PowerShell's `-File` path
    /// (powershell.exe parses argv itself; `&` is not special there).
    Std(String),
    /// Emitted VERBATIM (no Rust quoting): the cmd.exe `/K` target. cmd
    /// re-parses everything after /K as its own command line under cmd's
    /// rules (Rust's quoting is not cmd's), so the script path arrives
    /// wrapped in its OWN quote pair by us. It must be a DOUBLE pair:
    /// cmd's documented /C//K parsing strips the outer quotes when the
    /// inner text carries a metacharacter (`&<>()@^|`) — a folder named
    /// `x&calc` would then split the line and let `calc` run as a bare
    /// PATH command (probe-verified 2026-10-11: single quotes inject,
    /// `""path""` runs the script untouched).
    CmdPath(String),
}

fn quoted_cmd_path(script: &Path) -> SpawnArg {
    SpawnArg::CmdPath(format!("\"\"{}\"\"", script.to_string_lossy()))
}

/// Apply argv elements with their per-shell encoding (shared by the real
/// spawn and the windowless tests).
fn apply_args(cmd: &mut std::process::Command, args: &[SpawnArg]) {
    use std::os::windows::process::CommandExt;
    for a in args {
        match a {
            SpawnArg::Std(s) => {
                cmd.arg(s);
            }
            SpawnArg::CmdPath(s) => {
                cmd.raw_arg(s);
            }
        }
    }
}

/// Host program + arguments for one script (§117/§120/§121). Pure — the
/// exact argv (notably: NO -ExecutionPolicy) is unit-testable without
/// spawning anything. cwd = Project Root is applied by the caller (§121).
pub fn script_argv(script: &Path) -> Result<(PathBuf, Vec<SpawnArg>), String> {
    match ext_of(script).as_str() {
        "ps1" => Ok((
            PathBuf::from("powershell.exe"),
            vec![
                SpawnArg::Std("-NoExit".into()),
                SpawnArg::Std("-File".into()),
                SpawnArg::Std(script.to_string_lossy().into()),
            ],
        )),
        "cmd" | "bat" => {
            // cmd.exe re-expands %VAR% inside the /K payload, so a literal
            // '%' pair in the path could in theory splice environment text
            // inside our quotes (spec-012 L-r5; precondition is exotic —
            // refusing is cheap and total). PowerShell -File has no such
            // reparse, so .ps1 paths with '%' stay allowed.
            if script.to_string_lossy().contains('%') {
                return Err(format!(
                    "Cannot run .cmd/.bat from a path containing '%' (cmd.exe would expand it) — rename the folder: {}",
                    script.display()
                ));
            }
            Ok((PathBuf::from("cmd.exe"), vec![SpawnArg::Std("/K".into()), quoted_cmd_path(script)]))
        }
        other => Err(format!("Not a runnable script (.{other}): use Run on .ps1/.cmd/.bat only")),
    }
}

/// §116/§137 Run Script: persistent host + visible console, cwd = project
/// root. Spawn-and-forget — the child belongs to the user from here on.
/// ASYNC (spec-012 M12, L35 family): resolve_target canonicalizes on disk
/// and the spawn itself can block; never on the native main thread.
#[tauri::command]
pub async fn run_project_script(root_path: String, rel: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || run_script_inner(&root_path, &rel))
        .await
        .map_err(|e| format!("run task failed: {e}"))?
}

fn run_script_inner(root_path: &str, rel: &str) -> Result<(), String> {
    let script = resolve_target(Path::new(root_path), rel)?;
    if script.is_dir() {
        return Err(format!("Not a file: {rel}"));
    }
    if !SCRIPT_EXTENSIONS.contains(&ext_of(&script).as_str()) {
        return Err(format!(
            "Not a runnable script: {rel} (Run Script covers .ps1/.cmd/.bat, §116)"
        ));
    }
    let (program, args) = script_argv(&script)?;
    spawn_visible(&program, &args, Path::new(root_path))
}

/// §122/§123/§139 Run: direct launch of the absolute exe path, never via
/// cmd /c string composition; cwd = the exe's own directory (§124).
/// ASYNC for the same reason as run_project_script.
#[tauri::command]
pub async fn run_project_executable(root_path: String, rel: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || run_executable_inner(&root_path, &rel))
        .await
        .map_err(|e| format!("run task failed: {e}"))?
}

fn run_executable_inner(root_path: &str, rel: &str) -> Result<(), String> {
    let exe = resolve_target(Path::new(root_path), rel)?;
    if exe.is_dir() {
        return Err(format!("Not a file: {rel}"));
    }
    if ext_of(&exe) != "exe" {
        return Err(format!("Not an executable: {rel} (Run covers .exe only, §123)"));
    }
    let cwd = exe
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| Path::new(root_path).to_path_buf());
    spawn_visible(&exe, &[], &cwd)
}

fn spawn_visible(program: &Path, args: &[SpawnArg], cwd: &Path) -> Result<(), String> {
    let mut cmd = std::process::Command::new(program);
    apply_args(&mut cmd, args);
    cmd.current_dir(cwd).creation_flags(CREATE_NEW_CONSOLE);
    cmd.spawn()
        .map(|_| ())
        .map_err(|e| format!("Cannot start {}: {e}", program.display()))
}

// ---------------------------------------------------------------------------
// Tests — windowless. Host PERSISTENCE (the §118 property) is proven with
// the CREATE_NO_WINDOW variant: the host staying alive after the script
// body finished is exactly "output stays readable", independent of
// visibility; visibility itself is CREATE_NEW_CONSOLE by construction and
// was eyeballed in the strategy experiment.

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{Duration, Instant};

    fn marker_dir() -> (tempfile::TempDir, std::path::PathBuf) {
        let dir = tempfile::tempdir().unwrap();
        let marker = dir.path().join("marker.txt");
        (dir, marker)
    }

    #[test]
    fn ps1_argv_has_no_execution_policy_flag() {
        let (_, argv) = script_argv(Path::new("C:/x/s.ps1")).unwrap();
        let joined = argv
            .iter()
            .map(|a| match a {
                SpawnArg::Std(s) | SpawnArg::CmdPath(s) => s.as_str(),
            })
            .collect::<Vec<_>>()
            .join(" ");
        assert!(!joined.to_ascii_lowercase().contains("executionpolicy"));
        assert!(joined.contains("-NoExit"));
        assert!(joined.contains("-File"));
    }

    #[test]
    fn bat_uses_cmd_k_host() {
        let (program, argv) = script_argv(Path::new("C:/x/s.bat")).unwrap();
        assert_eq!(program, PathBuf::from("cmd.exe"));
        assert!(matches!(argv[0], SpawnArg::Std(ref s) if s == "/K"));
        let SpawnArg::CmdPath(path) = &argv[1] else {
            panic!("script path must ride the verbatim cmd channel");
        };
        assert!(path.starts_with("\"\"") && path.ends_with("\"\""));
        assert!(path.contains("s.bat"));
    }

    /// §145 / Phase 10 audit: cmd.exe re-parses the `/K` payload and
    /// strips an outer quote pair that carries a metacharacter — a folder
    /// named `x&calc` must ride the double-quoted verbatim channel.
    #[test]
    fn cmd_path_with_metacharacter_stays_one_token() {
        let (program, argv) =
            script_argv(Path::new(r"C:\proj\a&calc&\run.bat")).unwrap();
        assert_eq!(program, PathBuf::from("cmd.exe"));
        let SpawnArg::CmdPath(path) = &argv[1] else {
            panic!("expected CmdPath");
        };
        assert_eq!(path, "\"\"C:\\proj\\a&calc&\\run.bat\"\"");
    }

    /// Real-spawn regression for the same property: with the quoting, the
    /// script body inside the `&`-named folder actually runs (unquoted, cmd
    /// would split the line into `C:\...\a` & `calc&\run.bat` and neither
    /// exists). Windowless via the shared apply_args + CREATE_NO_WINDOW.
    #[test]
    fn bat_in_ampersand_folder_runs_via_verbatim_quoting() {
        let dir = tempfile::tempdir().unwrap();
        let nest = dir.path().join("a&calc&");
        std::fs::create_dir_all(&nest).unwrap();
        let marker = dir.path().join("marker.txt");
        let bat = nest.join("run.bat");
        std::fs::write(
            &bat,
            format!("@echo off\r\necho done> \"{}\"\r\n", marker.display()),
        )
        .unwrap();

        let (program, argv) = script_argv(&bat).unwrap();
        let mut launcher = std::process::Command::new(&program);
        apply_args(&mut launcher, &argv);
        launcher
            .stdin(std::process::Stdio::piped())
            .creation_flags(CREATE_NO_WINDOW)
            .current_dir(dir.path());
        let mut child = launcher.spawn().unwrap();
        // Hold stdin open (no console window; a closed pipe would EOF the
        // host before the script body finishes — same trick as the §118
        // persistence tests).
        let _stdin_hold = child.stdin.take();
        let start = Instant::now();
        while !marker.exists() && start.elapsed() < Duration::from_secs(8) {
            std::thread::sleep(Duration::from_millis(100));
        }
        assert!(marker.exists(), "script in '&'-named folder never ran — path was split by cmd");
    }

    #[test]
    fn non_script_extension_rejected() {
        assert!(script_argv(Path::new("C:/x/s.py")).is_err());
        assert!(script_argv(Path::new("C:/x/s.exe")).is_err());
    }

    /// spec-012 L-r5: cmd /K re-expands %VAR% — a '%' in a .cmd/.bat path is
    /// refused with a rename hint; .ps1 (powershell -File) is unaffected.
    #[test]
    fn cmd_path_with_percent_is_refused() {
        let err = script_argv(Path::new(r"C:\proj\100%\run.bat")).unwrap_err();
        assert!(err.contains("rename") || err.contains("cmd.exe"), "{err}");
        assert!(script_argv(Path::new(r"C:\proj\100%\run.ps1")).is_ok());
    }

    #[test]
    fn run_script_rejects_non_whitelisted_and_missing() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("x.py"), b"print(1)\n").unwrap();
        let err = run_script_inner(
            dir.path().to_string_lossy().into_owned().as_str(),
            "x.py",
        )
        .unwrap_err();
        assert!(err.contains("Not a runnable script"), "{err}");
        let err = run_script_inner(dir.path().to_string_lossy().into_owned().as_str(), "nope.bat")
            .unwrap_err();
        assert!(err.contains("Not found"), "{err}");
    }

    #[test]
    fn run_executable_rejects_non_exe() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("x.bat"), b"@echo off\r\n").unwrap();
        let err = run_executable_inner(
            dir.path().to_string_lossy().into_owned().as_str(),
            "x.bat",
        )
        .unwrap_err();
        assert!(err.contains("Not an executable"), "{err}");
    }

    #[test]
    fn run_executable_rejects_dotdot_escape() {
        let a = tempfile::tempdir().unwrap();
        let b = tempfile::tempdir().unwrap();
        std::fs::write(b.path().join("tool.exe"), b"MZ fake").unwrap();
        let bname = b.path().file_name().unwrap().to_str().unwrap();
        let err = run_executable_inner(
            a.path().to_string_lossy().into_owned().as_str(),
            &format!("../{bname}/tool.exe"),
        )
        .unwrap_err();
        assert!(err.contains("escapes"), "{err}");
    }

    /// §117/§118 quick-end readability: the HOST outlives the script body.
    /// A truly windowless spawn has NO console, so the host's interactive
    /// stdin hits EOF instantly and /K exits on its own — exactly the §118
    /// failure mode. To test the MECHANISM windowless we give the host a
    /// stdin pipe we keep open (a real console's stdin never EOFs either);
    /// the host must still be alive well after the script body finished.
    /// Visibility itself is CREATE_NEW_CONSOLE by construction and was
    /// verified in the strategy experiment (spec-008 §一).
    #[test]
    fn bat_host_outlives_script_body() {
        let (dir, marker) = marker_dir();
        let bat = dir.path().join("hello.bat");
        std::fs::write(
            &bat,
            format!("@echo off\r\necho step\r\necho done> \"{}\"\r\n", marker.display()),
        )
        .unwrap();
        // Production argv path (spec-012 L-r7): ride apply_args + script_argv
        // so the /K payload keeps its verbatim double-quoted encoding.
        let (program, argv) = script_argv(&bat).unwrap();
        let mut launcher = std::process::Command::new(&program);
        apply_args(&mut launcher, &argv);
        launcher
            .stdin(std::process::Stdio::piped())
            .creation_flags(CREATE_NO_WINDOW)
            .current_dir(dir.path());
        let mut child = launcher.spawn().unwrap();
        // Hold the write end open for the whole test = "input never EOFs".
        let _stdin_hold = child.stdin.take();
        let start = Instant::now();
        while !marker.exists() && start.elapsed() < Duration::from_secs(8) {
            std::thread::sleep(Duration::from_millis(100));
        }
        assert!(marker.exists(), "script body did not run");
        std::thread::sleep(Duration::from_secs(2));
        let alive = child.try_wait().unwrap().is_none();
        let _ = child.kill();
        assert!(alive, "cmd /K host exited with the script — output would vanish");
    }

    /// Same property for the PowerShell host (§120: no policy flag, so on a
    /// Restricted machine the error text itself stays readable in-window).
    #[test]
    fn ps1_host_outlives_script_body() {
        let (dir, marker) = marker_dir();
        let ps1 = dir.path().join("hello.ps1");
        std::fs::write(
            &ps1,
            format!("Set-Content -Path '{}' -Value done\n", marker.display()),
        )
        .unwrap();
        let mut child = std::process::Command::new("powershell.exe")
            .arg("-NoExit")
            .arg("-File")
            .arg(&ps1)
            .stdin(std::process::Stdio::piped())
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .unwrap();
        let _stdin_hold = child.stdin.take();
        let start = Instant::now();
        while !marker.exists() && start.elapsed() < Duration::from_secs(12) {
            std::thread::sleep(Duration::from_millis(200));
        }
        assert!(marker.exists(), "script body did not run (policy blocked?)");
        std::thread::sleep(Duration::from_secs(2));
        let alive = child.try_wait().unwrap().is_none();
        let _ = child.kill();
        assert!(alive, "powershell -NoExit host exited with the script");
    }
}
