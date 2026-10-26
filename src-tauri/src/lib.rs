mod file_inspect;
mod file_tree;
mod git;
mod handoff;
mod project;
mod properties;
mod run;
mod state;
mod updater;
mod watcher;

use std::sync::OnceLock;
use std::time::Instant;

use tauri::Manager;

/// Restore + focus the main window from the tray (shared by the tray
/// click and menu handlers).
fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

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

/// Compose WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS.
///
/// The DirectComposition fallback rides along in EVERY channel
/// (2026-10-12 black-line hunt, round 4): a transient black line at the
/// webview's TOP edge appears to the naked eye on big repaints (project
/// switches), moves with the window, and is absent from EVERY pixel
/// capture (owner PixPin + 197 forced-composite CDP frames) — i.e. it
/// lives in the DirectComposition presentation layer, not in app pixels.
/// This flag falls back to the conservative presentation path. Revisit if
/// it costs measurable CPU/GPU. e2e sets its own args env, so suites keep
/// exercising the default path.
///
/// The live-inspect CDP port (owner 2026-10-12, freeze hunt: "你应该有一
/// 种机制,能够直接获取到我在本地打开的这个软件里面的信息") is gated by
/// `cdp_allowed`: only dev & experience builds listen on it so live-
/// inspect.py can attach to the RUNNING app. FORMAL INSTALLS NEVER DO
/// (spec-011 NSIS step): the default identifier in a release build means
/// "NSIS setup" — no debug backdoor, not even when a parent process hands
/// us browser arguments.
fn merge_webview_args(current: Option<&str>, cdp_allowed: bool) -> String {
    const DCOMP: &str = "--disable-direct-composition";
    const PORT: &str = "--remote-debugging-port=9322";
    match current {
        None => {
            if cdp_allowed {
                format!("{PORT} {DCOMP}")
            } else {
                DCOMP.to_string()
            }
        }
        // L48 (2026-10-12, 0.7.19 field case): the updater's relaunch
        // spawns this exe WITH THE PARENT'S ENV — the parent (older
        // build) had set this var to its own value, so the first-write
        // gate above skipped and freshly added flags were silently
        // dropped after every update-restart. Append-only patch: add
        // whatever flag is missing; an e2e-provided port (different
        // number) counts as present and is never duplicated.
        Some(cur) => {
            let mut args = cur.trim().to_string();
            let has_port = args
                .split_whitespace()
                .any(|a| a.starts_with("--remote-debugging-port"));
            if cdp_allowed && !has_port {
                if !args.is_empty() {
                    args.push(' ');
                }
                args.push_str(PORT);
            }
            if !args.contains(DCOMP) {
                if !args.is_empty() {
                    args.push(' ');
                }
                args.push_str(DCOMP);
            }
            args
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let _ = STARTED_AT.set(Instant::now());

    // Channel gate for the CDP port: experience builds run under the .exp
    // identifier (SPEC-INFRA-001), dev builds are debug-compiled — both
    // keep live-inspect. A release build under the DEFAULT identifier is
    // the NSIS install: port closed, fail-safe (nothing to remember at
    // packaging time).
    let context = tauri::generate_context!();
    let cdp_allowed =
        context.config().identifier.ends_with(".exp") || cfg!(debug_assertions);

    if std::env::var_os("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS").is_none() {
        std::env::set_var(
            "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
            merge_webview_args(None, cdp_allowed),
        );
    } else {
        let cur = std::env::var("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS")
            .unwrap_or_default();
        let args = merge_webview_args(Some(&cur), cdp_allowed);
        if args != cur {
            std::env::set_var("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", args);
        }
    }

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
        // Owner 2026-10-02 + 2026-10-09 clarification: closing the window
        // hides it into the SYSTEM TRAY (taskbar corner, next to the clock
        // — not the main taskbar row). The tray icon is how you get back:
        // single-click restores, right-click menu has the only real Exit.
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .manage(state::LastState::default())
        // Phase 9 (spec-009 D6): ONE live watch for the active project;
        // start_project_watch atomically swaps this slot. The generation
        // marker inside retires out-of-order completions (spec-012 M4/D3).
        .manage(std::sync::Mutex::new(watcher::WatchState::default()))
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

            // System tray (owner 2026-10-09): single-click restores the
            // window; right-click menu carries Show + the only real Exit.
            // Exit goes through app.exit -> RunEvent::Exit -> the state
            // flush already wired there. Labels are English at boot; a
            // language switch (or restored zh preference) rebuilds the
            // menu in place via set_tray_language (spec-016).
            use tauri::menu::{Menu, MenuItem};
            use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
            let (show_label, exit_label) = tray_labels("en");
            let show = MenuItem::with_id(app, "tray-show", show_label, true, None::<&str>)?;
            let exit = MenuItem::with_id(app, "tray-exit", exit_label, true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &exit])?;
            TrayIconBuilder::with_id("main-tray")
                .tooltip("AI Project Viewer")
                .icon(app.default_window_icon().cloned().ok_or("no app icon")?)
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "tray-exit" => app.exit(0),
                    _ => show_main_window(app),
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window(tray.app_handle());
                    }
                })
                .build(app)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            startup_elapsed_ms,
            build_timestamp,
            channel,
            set_tray_language,
            test_project_arg,
            test_mode_active,
            project::resolve_project,
            project::paths_exist,
            file_tree::list_directory,
            file_inspect::inspect_file,
            file_inspect::read_text_file,
            file_inspect::read_media_file,
            file_inspect::read_binary_file,
            git::git_snapshot,
            git::git_diff,
            git::git_commit_detail,
            git::git_file_history,
            properties::file_properties,
            handoff::edit_in_quick_editor,
            handoff::open_in_code_editor,
            handoff::reveal_in_explorer,
            handoff::open_with_default_app,
            handoff::open_in_browser,
            run::run_project_script,
            run::run_project_executable,
            state::app_version,
            state::write_diagnostics,
            state::load_state,
            state::save_state,
            watcher::start_project_watch,
            watcher::stop_project_watch,
            updater::check_update,
            updater::apply_update,
            updater::relaunch
        ])
        .build(context)
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

/// Tray menu labels per locale (spec-016). Single source for the boot
/// build (English) and the in-place rebuild on a language switch.
fn tray_labels(locale: &str) -> (&'static str, &'static str) {
    if locale == "zh" {
        ("显示 AI Project Viewer", "退出")
    } else {
        ("Show AI Project Viewer", "Exit")
    }
}

/// Rebuild the tray menu in the requested language (spec-016). Item ids
/// stay stable, so the existing menu-event handlers keep working.
#[tauri::command]
fn set_tray_language(app: tauri::AppHandle, locale: String) -> Result<(), String> {
    use tauri::menu::{Menu, MenuItem};
    let (show_label, exit_label) = tray_labels(&locale);
    let show = MenuItem::with_id(&app, "tray-show", show_label, true, None::<&str>)
        .map_err(|e| e.to_string())?;
    let exit = MenuItem::with_id(&app, "tray-exit", exit_label, true, None::<&str>)
        .map_err(|e| e.to_string())?;
    let menu = Menu::with_items(&app, &[&show, &exit]).map_err(|e| e.to_string())?;
    let tray = app
        .tray_by_id("main-tray")
        .ok_or_else(|| "tray not found".to_string())?;
    tray.set_menu(Some(menu)).map_err(|e| e.to_string())
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

#[cfg(test)]
mod tests {
    use super::{merge_webview_args, tray_labels};

    const PORT: &str = "--remote-debugging-port=9322";
    const DCOMP: &str = "--disable-direct-composition";

    /// spec-011 NSIS step: a formal install (cdp off) must NEVER carry the
    /// live-inspect port — not on first write, not appended to inherited
    /// browser arguments.
    #[test]
    fn formal_first_write_has_no_cdp_port() {
        let got = merge_webview_args(None, false);
        assert!(!got.contains("remote-debugging-port"), "got: {got}");
        assert_eq!(got, DCOMP);
    }

    #[test]
    fn formal_never_appends_port_to_inherited_args() {
        let got = merge_webview_args(Some("--foo=1"), false);
        assert!(!got.contains("remote-debugging-port"), "got: {got}");
        assert!(got.contains("--foo=1") && got.contains(DCOMP));
    }

    /// dev (tauri dev, debug) and experience (.exp identifier) keep the
    /// port — live-inspect.py attaches there.
    #[test]
    fn dev_and_experience_first_write_carries_port() {
        assert_eq!(merge_webview_args(None, true), format!("{PORT} {DCOMP}"));
    }

    /// L48: updater relaunch inherits parent env — missing flags are
    /// appended, and a second pass changes nothing.
    #[test]
    fn inherited_args_get_missing_flags_appended() {
        let got = merge_webview_args(Some(DCOMP), true);
        assert_eq!(got, format!("{DCOMP} {PORT}"));
    }

    #[test]
    fn second_pass_is_stable() {
        let once = merge_webview_args(Some("--foo=1"), true);
        let twice = merge_webview_args(Some(&once), true);
        assert_eq!(once, twice);
    }

    /// aivlaunch presets its own port — that must count as present and
    /// never be duplicated with the default one.
    #[test]
    fn foreign_port_is_never_duplicated() {
        let e2e = "--remote-debugging-port=9455";
        let got = merge_webview_args(Some(e2e), true);
        assert_eq!(got, format!("{e2e} {DCOMP}"));
        assert!(!got.contains("9322"));
    }

    /// spec-016: the tray menu is the one Rust-owned UI surface — its
    /// labels must follow the language switch (set_tray_language).
    #[test]
    fn tray_labels_follow_locale() {
        assert_eq!(tray_labels("en"), ("Show AI Project Viewer", "Exit"));
        assert_eq!(tray_labels("zh"), ("显示 AI Project Viewer", "退出"));
    }
}
