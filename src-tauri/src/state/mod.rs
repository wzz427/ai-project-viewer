//! AppState persistence commands (V1.5 §23–§26, spec-004).
//!
//! The frontend owns the state shape and serializes it (spec-004 D1); this
//! module only stores bytes: atomic replace on save, self-healing load,
//! and an exit-time flush of the last received state (§26 "final write on
//! normal exit" — async invokes are unreliable while the WebView tears
//! down, so the Rust process is the safety net).

mod migration;
mod persistence;

use std::fs;
use std::path::PathBuf;
use std::sync::RwLock;

use tauri::Manager;

/// Last state JSON received from the frontend; flushed again on exit.
#[derive(Default)]
pub struct LastState(pub RwLock<Option<String>>);

/// Which state file the process may touch (spec-004 D10).
///
/// AIV_STATE_FILE redirects all persistence (GUI-test throwaway file).
/// AIV_TEST_PROJECT without AIV_STATE_FILE = full denial: tests that
/// auto-add a project must never read or overwrite the owner's real
/// state.json.
enum Access {
    Denied,
    Override(PathBuf),
    Normal,
}

fn access(test_project: Option<String>, state_file: Option<String>) -> Access {
    let explicit = state_file.filter(|s| !s.is_empty());
    match explicit {
        Some(f) => Access::Override(PathBuf::from(f)),
        None if test_project.map(|s| !s.is_empty()).unwrap_or(false) => Access::Denied,
        None => Access::Normal,
    }
}

fn state_path(app: &tauri::AppHandle) -> Result<Option<PathBuf>, String> {
    match access(
        std::env::var("AIV_TEST_PROJECT").ok(),
        std::env::var("AIV_STATE_FILE").ok(),
    ) {
        Access::Denied => Ok(None),
        Access::Override(p) => Ok(Some(p)),
        Access::Normal => {
            let dir = app.path().app_config_dir().map_err(|e| e.to_string())?;
            Ok(Some(dir.join("state.json")))
        }
    }
}

/// App version from tauri.conf.json — for the diagnostics export header.
#[tauri::command]
pub fn app_version(app: tauri::AppHandle) -> String {
    app.config()
        .version
        .clone()
        .unwrap_or_else(|| "unknown".into())
}

/// Write a diagnostics report under the app config dir (0.6.12, owner
/// 2026-10-10: "在客户端 setting 中增加一个诊断的按钮…生成运行信息").
/// Returns the absolute path for the UI to show/copy.
/// ASYNC (spec-012 M12): the report can be hundreds of KB — keep the write
/// off the native main thread.
#[tauri::command]
pub async fn write_diagnostics(app: tauri::AppHandle, text: String) -> Result<String, String> {
    let dir = app
        .path()
        .app_config_dir()
        .map_err(|e| e.to_string())?
        .join("diagnostics");
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_secs();
    tauri::async_runtime::spawn_blocking(move || {
        fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
        let path = dir.join(format!("aiv-diagnostics-{ts}.txt"));
        fs::write(&path, text.as_bytes()).map_err(|e| e.to_string())?;
        Ok(path.to_string_lossy().into_owned())
    })
    .await
    .map_err(|e| format!("diagnostics task failed: {e}"))?
}

/// ASYNC (spec-012 M12): reading state.json off a slow disk must not stall
/// the native main thread during startup.
#[tauri::command]
pub async fn load_state(app: tauri::AppHandle) -> Result<Option<String>, String> {
    let Some(path) = state_path(&app)? else {
        return Ok(None);
    };
    tauri::async_runtime::spawn_blocking(move || persistence::load(&path))
        .await
        .map_err(|e| format!("load state task failed: {e}"))?
}

/// ASYNC (spec-012 M12): the atomic write does tmp→flush→rename (an fsync);
/// save_state fires on the 800 ms debounce, so a slow disk would otherwise
/// freeze the window right after any tab/theme change. The in-memory slot
/// update stays INLINE — it is the exit flush's source of truth and must
/// land before this command returns.
#[tauri::command]
pub async fn save_state(
    app: tauri::AppHandle,
    json: String,
) -> Result<(), String> {
    {
        let last = app.state::<LastState>();
        let mut slot = last.0.write().map_err(|e| e.to_string())?;
        *slot = Some(json);
    }
    tauri::async_runtime::spawn_blocking(move || write_current(&app))
        .await
        .map_err(|e| format!("save state task failed: {e}"))?
}

/// Write the in-memory last state to disk if access allows. Shared by the
/// save command and the exit flush.
fn write_current(app: &tauri::AppHandle) -> Result<(), String> {
    let json = {
        let last = app.state::<LastState>();
        let guard = last.0.read().map_err(|e| e.to_string())?;
        guard.clone()
    };
    let Some(json) = json else {
        return Ok(());
    };
    let Some(path) = state_path(app)? else {
        return Ok(());
    };
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    }
    persistence::atomic_write(&path, json.as_bytes())
}

/// RunEvent::Exit hook: one final atomic write (V1.5 §26).
pub fn flush_on_exit(app: &tauri::AppHandle) {
    if let Err(err) = write_current(app) {
        eprintln!("exit state flush failed: {err}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn access_redirects_overrides_and_denies() {
        // Pure routing (spec-004 D10): explicit file wins; a test project
        // alone denies; nothing set = normal app usage.
        match access(None, None) {
            Access::Normal => {}
            _ => panic!("expected Normal"),
        }
        match access(None, Some("X:\\tmp\\s.json".into())) {
            Access::Override(p) => assert_eq!(p, PathBuf::from("X:\\tmp\\s.json")),
            _ => panic!("expected Override"),
        }
        match access(Some("C:\\proj".into()), None) {
            Access::Denied => {}
            _ => panic!("expected Denied"),
        }
        match access(Some("C:\\proj".into()), Some(String::new())) {
            Access::Denied => {}
            _ => panic!("empty state file must fall back to Denied"),
        }
        match access(Some(String::new()), None) {
            Access::Normal => {}
            _ => panic!("empty test project must fall back to Normal"),
        }
    }
}
