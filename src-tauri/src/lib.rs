mod file_inspect;
mod file_tree;
mod project;
mod state;
mod updater;

use std::sync::OnceLock;
use std::time::Instant;

use tauri::Manager;

/// Process start timestamp, set once in `run()`. Baseline for startup-time
/// measurement (V1.5 §164): the frontend reports readiness via
/// `startup_elapsed_ms` on mount.
static STARTED_AT: OnceLock<Instant> = OnceLock::new();

/// Test hook (testing.md 1): project to auto-add, avoiding the native
/// picker dialog during GUI tests. Pull-based so the frontend can ask
/// once its listeners are ready.
#[tauri::command]
fn test_project_arg() -> Option<String> {
    std::env::var("AIV_TEST_PROJECT").ok().filter(|s| !s.is_empty())
}

/// True under a scripted GUI test (AIV_TEST_PROJECT set). Used to skip
/// NATIVE modal confirmations a script cannot drive — rfd's Windows
/// dialogs are TaskDialogs (owner-drawn buttons, no child HWNDs, lessons
/// L7 addendum); an undriven one would hang on the owner's desktop.
#[tauri::command]
fn test_mode_active() -> bool {
    std::env::var("AIV_TEST_PROJECT").map(|v| !v.is_empty()).unwrap_or(false)
}

#[tauri::command]
fn startup_elapsed_ms() -> u64 {
    STARTED_AT
        .get()
        .map(|t| t.elapsed().as_millis() as u64)
        .unwrap_or(0)
}

/// Build time = the exe file's own modification time, read at runtime —
/// always truthful, no build-script plumbing. Lets the owner (and any
/// screenshot) tell a stale instance from a fresh one (single-instance
/// revives old windows, which has cost two false bug reports already).
#[tauri::command]
fn build_timestamp() -> u64 {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.metadata().ok())
        .and_then(|m| m.modified().ok())
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Which channel this binary belongs to (SPEC-INFRA-001): the experience
/// client runs under a dedicated identifier. Shown in Diagnostics so "am I
/// on the dev build or the installed client?" is answerable at a glance.
#[tauri::command]
fn channel(app: tauri::AppHandle) -> String {
    if app.config().identifier.ends_with(".exp") {
        "experience".into()
    } else {
        "dev".into()
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let _ = STARTED_AT.set(Instant::now());

    tauri::Builder::default()
        // Must be the first registered plugin (V1.5 §16): a second launch
        // activates the existing window instead of spawning a new instance.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(state::LastState::default())
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                disable_browser_accelerators(&window);
                // Test mode (testing.md §1): AIV_HIDDEN=1 keeps the window
                // off the owner's desktop entirely — GUI tests must never
                // steal focus or flash. Normal launches show as usual.
                if std::env::var("AIV_HIDDEN").as_deref() != Ok("1") {
                    let _ = window.show();
                }
            }
            // Experience channel (SPEC-INFRA-001): remove leftovers from
            // a previous self-update swap.
            updater::clean_stale_swap_files();
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            startup_elapsed_ms,
            build_timestamp,
            channel,
            test_project_arg,
            test_mode_active,
            project::resolve_project,
            file_tree::list_directory,
            file_inspect::inspect_file,
            file_inspect::read_text_file,
            file_inspect::read_media_file,
            file_inspect::read_binary_file,
            state::load_state,
            state::save_state,
            updater::check_update,
            updater::apply_update,
            updater::relaunch
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            // V1.5 §26 final write on normal exit: the frontend flushes on
            // pagehide too, but async invokes are unreliable while the
            // WebView tears down — this is the safety net.
            if let tauri::RunEvent::Exit = event {
                state::flush_on_exit(app);
            }
        });
}

/// Application shortcuts must take priority over WebView2 browser
/// accelerators (V1.5 §147): disable them so Ctrl+F/Ctrl+R/etc. reach the
/// DOM, where the frontend dispatcher claims them. Tauri 2 has no config
/// field for this — it must go through the WebView2 COM settings.
#[cfg(target_os = "windows")]
fn disable_browser_accelerators(window: &tauri::WebviewWindow) {
    use webview2_com::Microsoft::Web::WebView2::Win32::ICoreWebView2Settings3;
    use windows_core::Interface;

    let result = window.with_webview(|webview| unsafe {
        let attempt = (|| -> windows_core::Result<()> {
            let core = webview.controller().CoreWebView2()?;
            let settings = core.Settings()?;
            let settings3: ICoreWebView2Settings3 = settings.cast()?;
            settings3.SetAreBrowserAcceleratorKeysEnabled(false)?;
            Ok(())
        })();
        if let Err(err) = attempt {
            eprintln!("failed to disable WebView2 browser accelerators: {err}");
        }
    });
    if let Err(err) = result {
        eprintln!("with_webview failed: {err}");
    }
}

#[cfg(not(target_os = "windows"))]
fn disable_browser_accelerators(_window: &tauri::WebviewWindow) {}
