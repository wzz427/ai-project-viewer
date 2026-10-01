mod file_inspect;
mod file_tree;
mod project;

use std::sync::OnceLock;
use std::time::Instant;

use tauri::Manager;

/// Process start timestamp, set once in `run()`. Baseline for startup-time
/// measurement (V1.5 §164): the frontend reports readiness via
/// `startup_elapsed_ms` on mount.
static STARTED_AT: OnceLock<Instant> = OnceLock::new();

#[tauri::command]
fn startup_elapsed_ms() -> u64 {
    STARTED_AT
        .get()
        .map(|t| t.elapsed().as_millis() as u64)
        .unwrap_or(0)
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
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                disable_browser_accelerators(&window);
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            startup_elapsed_ms,
            project::resolve_project,
            file_tree::list_directory,
            file_inspect::inspect_file
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
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
