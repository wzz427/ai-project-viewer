//! Active-project file watcher (V1.5 §76–§85/§183, spec-009).
//!
//! One watcher slot for the ACTIVE project only (§77): starting a new
//! watch stops the previous one — never two live watchers (spec-009 D6).
//! The 400 ms debounce (§81, D1) and the §32 ignore filter live HERE,
//! Rust-side, so ignored directories never cross the IPC boundary (§80
//! event-storm control). Rename pairing uses the kernel's From/To events
//! when available (§84 reliable identification, D2).

use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::Duration;

use notify_debouncer_full::notify::event::{ModifyKind, RenameMode};
use notify_debouncer_full::notify::{Event, EventKind, RecursiveMode};
use notify_debouncer_full::{
    new_debouncer_opt, notify, Debouncer, DebounceEventResult, NoCache,
};
use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager};

/// (V1.5 §32) Directories the watcher ignores. Deliberate twin of
/// src/lib/services/watcherIgnore.ts and deliberately NOT shared with
/// tree visibility (§28 — two separate lists; `dist`/`build`/`target`
/// are visible in the tree but not watched).
const WATCH_IGNORE_DIRS: [&str; 11] = [
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".cache",
    ".next",
    "coverage",
    "dist",
    "build",
    "target",
];

/// §81 debounce window (spec-009 D1: Rust-side, frontend adds none).
const DEBOUNCE_MS: u64 = 400;

/// Events per window above which itemizing stops and the frontend is told
/// to do ONE full refresh instead (§80 storm guard, spec-009 D5).
const STORM_LIMIT: usize = 200;

/// Watcher slot. NoCache on purpose: `Debouncer::watch` synchronously
/// feeds the cache via `add_path`, and the default Windows cache
/// (FileIdMap) WALKS THE ENTIRE TREE with `follow_links(true)`, opening a
/// handle per entry — minutes of 100% CPU on real projects (node_modules,
/// build dirs, pnpm's symlink farm) and, inside a sync command, a frozen
/// window (0.7.0/0.7.1 startup freeze, lessons L36). We pair renames from
/// the kernel's From/To paths instead (L33), so the file-ID cache buys
/// nothing here.
pub struct WatchSlot {
    /// Held for its Drop side effect only (dropping the debouncer stops the
    /// watch and joins its thread) — never read directly.
    #[allow(dead_code)]
    debouncer: Debouncer<notify::RecommendedWatcher, NoCache>,
}

/// Managed watcher state = live slot + the generation marker
/// `expected_root` (spec-012 M4/D3). `start_project_watch` runs its
/// canonicalize+watch() on a worker thread; two rapid switches A→B race,
/// and whichever finishes LAST used to win the slot — fast A on a warm
/// cache could resurrect A's watcher over B's, silently killing the new
/// project's live refresh. The marker is claimed at request time and
/// re-checked at completion; a superseded start drops its own watcher.
#[derive(Default)]
pub struct WatchState {
    pub(crate) expected_root: Option<PathBuf>,
    pub(crate) slot: Option<WatchSlot>,
}

/// Record `root` as the watcher the frontend last asked for. Called BEFORE
/// the blocking watch setup begins.
pub(crate) fn claim_start(state: &mut WatchState, root: PathBuf) {
    state.expected_root = Some(root);
}

/// Install `debouncer` only if `root` is still the claimed root (M4/D3).
/// Returns false for a superseded start — the caller then drops the
/// debouncer (joining its thread) instead of installing it.
pub(crate) fn install_if_current(
    state: &mut WatchState,
    root: &Path,
    debouncer: Debouncer<notify::RecommendedWatcher, NoCache>,
) -> bool {
    if state.expected_root.as_deref() == Some(root) {
        state.slot = Some(WatchSlot { debouncer });
        true
    } else {
        false
    }
}

#[derive(Serialize, Clone, Debug, PartialEq)]
#[serde(rename_all = "camelCase")]
pub(crate) struct FsChangeBatch {
    pub root: String,
    pub changed: Vec<String>,
    pub removed: Vec<String>,
    pub renames: Vec<RenamePair>,
    pub storm: bool,
}

#[derive(Serialize, Clone, Debug, PartialEq)]
pub(crate) struct RenamePair {
    pub from: String,
    pub to: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ChangeKind {
    Changed,
    Removed,
    RenameFrom,
    RenameTo,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct RawChange {
    pub kind: ChangeKind,
    pub rel: String,
}

/// Project-relative path with `/` separators; None for the root itself
/// or paths outside it.
pub(crate) fn rel_of(root: &Path, path: &Path) -> Option<String> {
    let rel = path.strip_prefix(root).ok()?;
    let mut out = String::new();
    for seg in rel.components() {
        if !out.is_empty() {
            out.push('/');
        }
        out.push_str(&seg.as_os_str().to_string_lossy());
    }
    if out.is_empty() {
        None
    } else {
        Some(out)
    }
}

/// True when ANY path segment is in the §32 ignore list.
pub(crate) fn is_ignored_rel(rel: &str) -> bool {
    rel.split('/').any(|seg| WATCH_IGNORE_DIRS.contains(&seg))
}

/// Folds one debounce window into the IPC batch. Rename pairing is
/// ADJACENT-only: the kernel emits a rename as From immediately followed
/// by To, so a From pairs only with the very next raw change when that is
/// a To (§84 reliable identification — zipping all Froms with all Tos
/// would weld an unrelated move-out + move-in into a phantom rename).
/// Unpaired From → removed (moved away); unpaired To → changed (moved in).
pub(crate) fn build_batch(root: &str, raws: &[RawChange]) -> FsChangeBatch {
    if raws.len() > STORM_LIMIT {
        return FsChangeBatch {
            root: root.to_string(),
            changed: Vec::new(),
            removed: Vec::new(),
            renames: Vec::new(),
            storm: true,
        };
    }
    let mut changed: Vec<String> = Vec::new();
    let mut removed: Vec<String> = Vec::new();
    let mut renames: Vec<RenamePair> = Vec::new();
    let mut i = 0;
    while i < raws.len() {
        match raws[i].kind {
            ChangeKind::Changed => push_unique(&mut changed, &raws[i].rel),
            ChangeKind::Removed => push_unique(&mut removed, &raws[i].rel),
            ChangeKind::RenameFrom => {
                let paired = matches!(raws.get(i + 1), Some(n) if n.kind == ChangeKind::RenameTo);
                if paired {
                    renames.push(RenamePair {
                        from: raws[i].rel.clone(),
                        to: raws[i + 1].rel.clone(),
                    });
                    i += 2;
                    continue;
                }
                push_unique(&mut removed, &raws[i].rel);
            }
            ChangeKind::RenameTo => push_unique(&mut changed, &raws[i].rel),
        }
        i += 1;
    }
    FsChangeBatch {
        root: root.to_string(),
        changed,
        removed,
        renames,
        storm: false,
    }
}

fn push_unique(list: &mut Vec<String>, item: &str) {
    if !list.iter().any(|x| x == item) {
        list.push(item.to_string());
    }
}

/// Classify one notify event into raw rel-path changes. Access (read)
/// events are dropped — a read is not a change. Windows emits a rename as
/// a SINGLE `Name(Both)` event carrying [from, to] (probe-verified
/// 2026-10-11); it is split into the adjacent From/To pair that
/// build_batch pairs (§84).
pub(crate) fn classify_event(root: &Path, ev: &Event) -> Vec<RawChange> {
    if let EventKind::Modify(ModifyKind::Name(RenameMode::Both)) = ev.kind {
        if ev.paths.len() >= 2 {
            let mut out = Vec::new();
            for (path, kind) in [
                (&ev.paths[0], ChangeKind::RenameFrom),
                (&ev.paths[1], ChangeKind::RenameTo),
            ] {
                if let Some(rel) = rel_of(root, path) {
                    out.push(RawChange { kind, rel });
                }
            }
            return out;
        }
    }
    fn kind_of(ev: &Event) -> Option<ChangeKind> {
        match ev.kind {
            EventKind::Create(_) => Some(ChangeKind::Changed),
            EventKind::Remove(_) => Some(ChangeKind::Removed),
            EventKind::Modify(ModifyKind::Name(mode)) => match mode {
                RenameMode::From => Some(ChangeKind::RenameFrom),
                RenameMode::To => Some(ChangeKind::RenameTo),
                _ => Some(ChangeKind::Changed),
            },
            EventKind::Modify(_) => Some(ChangeKind::Changed),
            EventKind::Access(_) | EventKind::Other | EventKind::Any => None,
        }
    }
    let Some(kind) = kind_of(ev) else {
        return Vec::new();
    };
    ev.paths
        .iter()
        .filter_map(|p| rel_of(root, p))
        .map(|rel| RawChange { kind, rel })
        .collect()
}

/// Fold one debouncer result into the batch to sink, or None when the
/// window carried nothing reportable. An `Err` result (e.g. the OS event
/// buffer overflowed) means events were LOST, not that nothing happened —
/// it becomes a storm batch so the frontend does one full refresh instead
/// of silently missing external writes (owner 2026-10-17 staleness
/// report: swallowed errors were a silent-loss hole).
pub(crate) fn fold_result(
    root: &Path,
    res: DebounceEventResult,
) -> Option<FsChangeBatch> {
    let root_str = root.to_string_lossy().to_string();
    match res {
        Ok(events) => {
            let mut raws = Vec::new();
            for ev in events {
                for r in classify_event(root, &ev.event) {
                    if !is_ignored_rel(&r.rel) {
                        raws.push(r);
                    }
                }
            }
            if raws.is_empty() {
                return None;
            }
            Some(build_batch(&root_str, &raws))
        }
        Err(_) => Some(FsChangeBatch {
            root: root_str,
            changed: Vec::new(),
            removed: Vec::new(),
            renames: Vec::new(),
            storm: true,
        }),
    }
}

/// Build the debounced watcher; `sink` receives one batch per window.
/// Generic over the sink so cargo tests can watch a tempdir through an
/// mpsc channel without a Tauri app (spec-009 testability note).
pub(crate) fn spawn_watcher<F>(
    root: PathBuf,
    sink: F,
) -> Result<Debouncer<notify::RecommendedWatcher, NoCache>, notify_debouncer_full::notify::Error>
where
    F: Fn(FsChangeBatch) + Send + 'static,
{
    let cb_root = root.clone();
    let mut debouncer = new_debouncer_opt(
        Duration::from_millis(DEBOUNCE_MS),
        None,
        move |res: DebounceEventResult| {
            if let Some(batch) = fold_result(&cb_root, res) {
                sink(batch);
            }
        },
        NoCache::new(),
        notify::Config::default(),
    )?;
    debouncer.watch(&root, RecursiveMode::Recursive)?;
    Ok(debouncer)
}

#[tauri::command]
pub async fn start_project_watch(app: AppHandle, root_path: String) -> Result<(), String> {
    // Async + spawn_blocking (L35/L36): `watch()` round-trips into the
    // notify event loop, and watcher lifecycle work must NEVER run on the
    // native main thread — a sync command there froze the window for the
    // whole watch setup (owner 0.7.0/0.7.1 startup freeze).
    tauri::async_runtime::spawn_blocking(move || {
        let root = std::fs::canonicalize(&root_path)
            .map_err(|e| format!("cannot watch {root_path}: {e}"))?;
        let root = dunce::simplified(&root).to_path_buf();
        // Claim the generation FIRST (M4/D3): if a newer start/stop lands
        // while this watcher is being built, the completion check retires
        // this one instead of clobbering the newer watcher.
        {
            let state: tauri::State<'_, Mutex<WatchState>> = app.state();
            claim_start(&mut state.lock().unwrap(), root.clone());
        }
        let emit_app = app.clone();
        let debouncer = spawn_watcher(root.clone(), move |batch| {
            let _ = emit_app.emit("fs-changed", &batch);
        })
        .map_err(|e| format!("cannot watch {}: {e}", root.display()))?;
        {
            let state: tauri::State<'_, Mutex<WatchState>> = app.state();
            let mut guard = state.lock().unwrap();
            if !install_if_current(&mut guard, &root, debouncer) {
                // Superseded by a newer request — drop our own watcher.
                // Dropping joins the debouncer thread right here on the
                // worker thread, never the main one.
                return Ok(());
            }
        }
        Ok(())
    })
    .await
    .map_err(|e| format!("watch start failed: {e}"))?
}

#[tauri::command]
pub async fn stop_project_watch(app: AppHandle) -> Result<(), String> {
    // Dropping the slot joins the debouncer thread — off the main thread
    // for the same reason as start (L35/L36).
    tauri::async_runtime::spawn_blocking(move || {
        let state: tauri::State<'_, Mutex<WatchState>> = app.state();
        let mut guard = state.lock().unwrap();
        // Clearing the marker also retires any start still in flight
        // (its completion check will see None ≠ Some(root) and self-drop).
        guard.expected_root = None;
        guard.slot = None;
        Ok(())
    })
    .await
    .map_err(|e| format!("watch stop failed: {e}"))?
}

#[cfg(test)]
mod tests {
    use super::*;
    use notify_debouncer_full::notify::event::{CreateKind, RemoveKind};

    fn raw(kind: ChangeKind, rel: &str) -> RawChange {
        RawChange {
            kind,
            rel: rel.to_string(),
        }
    }

    #[test]
    fn ignore_list_matches_path_segments_only() {
        assert!(is_ignored_rel("node_modules/foo.js"));
        assert!(is_ignored_rel("src/target/main.rs"));
        assert!(is_ignored_rel(".git"));
        assert!(!is_ignored_rel("src/main.rs"));
        assert!(!is_ignored_rel("src/targets/main.rs")); // segment, not prefix
        assert!(!is_ignored_rel("target.json")); // file, not directory
    }

    #[test]
    fn rel_of_uses_forward_slashes_and_stays_inside_root() {
        let root = Path::new("C:\\proj");
        assert_eq!(rel_of(root, Path::new("C:\\proj\\src\\main.py")).as_deref(), Some("src/main.py"));
        assert_eq!(rel_of(root, Path::new("C:\\proj\\a.md")).as_deref(), Some("a.md"));
        assert_eq!(rel_of(root, Path::new("C:\\proj")), None);
        assert_eq!(rel_of(root, Path::new("C:\\other\\x.md")), None);
    }

    #[test]
    fn build_batch_pairs_renames_in_order() {
        let raws = vec![
            raw(ChangeKind::RenameFrom, "a.md"),
            raw(ChangeKind::RenameTo, "b.md"),
            raw(ChangeKind::RenameFrom, "src/old.rs"),
            raw(ChangeKind::RenameTo, "src/new.rs"),
        ];
        let b = build_batch("R", &raws);
        assert_eq!(
            b.renames,
            vec![
                RenamePair { from: "a.md".into(), to: "b.md".into() },
                RenamePair { from: "src/old.rs".into(), to: "src/new.rs".into() },
            ]
        );
        assert!(b.changed.is_empty() && b.removed.is_empty() && !b.storm);
    }

    #[test]
    fn build_batch_leftovers_become_removed_and_changed() {
        let raws = vec![
            raw(ChangeKind::RenameFrom, "gone.md"), // moved away: no To follows
            raw(ChangeKind::Changed, "c.txt"),
            raw(ChangeKind::Changed, "c.txt"), // dedup
            raw(ChangeKind::RenameTo, "appeared.md"), // moved in: no From precedes
        ];
        let b = build_batch("R", &raws);
        assert!(b.renames.is_empty());
        assert_eq!(b.removed, vec!["gone.md"]);
        assert_eq!(b.changed, vec!["c.txt", "appeared.md"]);
    }

    #[test]
    fn build_batch_does_not_weld_unrelated_move_out_and_in() {
        // From, then an unrelated change, then To: NOT adjacent → no pair.
        let raws = vec![
            raw(ChangeKind::RenameFrom, "left.md"),
            raw(ChangeKind::Changed, "touched.txt"),
            raw(ChangeKind::RenameTo, "right.md"),
        ];
        let b = build_batch("R", &raws);
        assert!(b.renames.is_empty());
        assert_eq!(b.removed, vec!["left.md"]);
        assert_eq!(b.changed, vec!["touched.txt", "right.md"]);
    }

    #[test]
    fn build_batch_folds_storms_into_one_full_refresh() {
        let raws: Vec<RawChange> = (0..STORM_LIMIT + 1)
            .map(|i| raw(ChangeKind::Changed, &format!("f{i}.txt")))
            .collect();
        let b = build_batch("R", &raws);
        assert!(b.storm);
        assert!(b.changed.is_empty() && b.removed.is_empty() && b.renames.is_empty());
    }

    #[test]
    fn classify_event_covers_rename_remove_create_and_drops_access() {
        let root = Path::new("C:\\proj");
        let mk = |kind: EventKind, p: &str| Event::new(kind).add_path(PathBuf::from(p));
        let ev = mk(
            EventKind::Modify(ModifyKind::Name(RenameMode::From)),
            "C:\\proj\\a.md",
        );
        assert_eq!(classify_event(&root, &ev), vec![raw(ChangeKind::RenameFrom, "a.md")]);
        let ev = mk(EventKind::Remove(RemoveKind::File), "C:\\proj\\a.md");
        assert_eq!(classify_event(&root, &ev), vec![raw(ChangeKind::Removed, "a.md")]);
        let ev = mk(EventKind::Create(CreateKind::File), "C:\\proj\\a.md");
        assert_eq!(classify_event(&root, &ev), vec![raw(ChangeKind::Changed, "a.md")]);
        let ev = mk(
            EventKind::Access(notify_debouncer_full::notify::event::AccessKind::Read),
            "C:\\proj\\a.md",
        );
        assert!(classify_event(&root, &ev).is_empty());
        // Outside the root: dropped.
        let ev = mk(EventKind::Create(CreateKind::File), "C:\\other\\x");
        assert!(classify_event(&root, &ev).is_empty());
    }

    #[test]
    fn classify_event_splits_windows_both_rename() {
        // Windows shape (probe 2026-10-11): ONE event, paths [from, to].
        let root = Path::new("C:\\proj");
        let mut ev = Event::new(EventKind::Modify(ModifyKind::Name(RenameMode::Both)));
        ev.paths = vec![
            PathBuf::from("C:\\proj\\old.md"),
            PathBuf::from("C:\\proj\\new.md"),
        ];
        assert_eq!(
            classify_event(&root, &ev),
            vec![
                raw(ChangeKind::RenameFrom, "old.md"),
                raw(ChangeKind::RenameTo, "new.md"),
            ]
        );
        // And the adjacent pair survives build_batch as one rename (§84).
        let raws = classify_event(&root, &ev);
        let b = build_batch("R", &raws);
        assert_eq!(b.renames, vec![RenamePair { from: "old.md".into(), to: "new.md".into() }]);
    }

    #[test]
    fn fold_result_turns_watcher_error_into_storm_refresh() {
        let root = Path::new("C:\\proj");
        // A lost-events error must NOT vanish: it surfaces as a storm batch
        // (frontend does one full refresh).
        let err = DebounceEventResult::Err(vec![notify::Error::new(
            notify::ErrorKind::Generic("buffer overflow".into()),
        )]);
        let b = fold_result(root, err).expect("error must surface as a batch");
        assert!(b.storm);
        assert!(b.changed.is_empty() && b.removed.is_empty() && b.renames.is_empty());
        // An all-ignored window stays silent (no IPC).
        let ev = notify_debouncer_full::DebouncedEvent {
            event: Event::new(EventKind::Create(CreateKind::File))
                .add_path(PathBuf::from("C:\\proj\\node_modules\\x.js")),
            time: std::time::Instant::now(),
        };
        assert!(fold_result(root, Ok(vec![ev])).is_none());
    }

    #[test]
    fn real_watcher_smoke_delivers_a_batch() {
        let dir = tempfile::tempdir().unwrap();
        let (tx, rx) = std::sync::mpsc::channel::<FsChangeBatch>();
        let mut watcher = spawn_watcher(dir.path().to_path_buf(), move |b| {
            let _ = tx.send(b);
        })
        .unwrap();
        std::fs::write(dir.path().join("hello.txt"), b"v1").unwrap();
        let deadline = std::time::Instant::now() + Duration::from_secs(10);
        let mut got = false;
        while std::time::Instant::now() < deadline {
            if let Ok(b) = rx.recv_timeout(Duration::from_millis(200)) {
                if b.changed.iter().any(|c| c == "hello.txt") {
                    got = true;
                    break;
                }
            }
        }
        assert!(got, "watcher never reported hello.txt");
        // And an ignored directory never crosses the boundary (§80).
        std::fs::create_dir(dir.path().join("node_modules")).unwrap();
        std::fs::write(dir.path().join("node_modules\\x.js"), b"").unwrap();
        let deadline = std::time::Instant::now() + Duration::from_secs(2);
        while std::time::Instant::now() < deadline {
            if let Ok(b) = rx.recv_timeout(Duration::from_millis(200)) {
                assert!(
                    !b.changed.iter().any(|c| c.starts_with("node_modules")),
                    "ignored dir crossed IPC: {b:?}"
                );
            }
        }
        watcher.unwatch(dir.path()).ok();
    }

    /// spec-012 M4/D3: the completion check retires superseded starts and
    /// never clobbers a newer watcher. Real debouncers on tempdirs stand in
    /// for the real race (A claimed, B claims, A finishes last).
    #[test]
    fn superseded_start_self_retires_and_newer_watcher_survives() {
        let dir_a = tempfile::tempdir().unwrap();
        let dir_b = tempfile::tempdir().unwrap();
        let mut state = WatchState::default();

        // A claims, then B claims (the frontend switched projects).
        claim_start(&mut state, dir_a.path().to_path_buf());
        claim_start(&mut state, dir_b.path().to_path_buf());

        // A's watcher finishes building LAST: must self-retire.
        let deb_a = spawn_watcher(dir_a.path().to_path_buf(), |_| {}).unwrap();
        assert!(!install_if_current(&mut state, dir_a.path(), deb_a));
        assert!(state.slot.is_none(), "superseded watcher must not install");

        // B's watcher installs and stays.
        let deb_b = spawn_watcher(dir_b.path().to_path_buf(), |_| {}).unwrap();
        assert!(install_if_current(&mut state, dir_b.path(), deb_b));
        assert!(state.slot.is_some());
        assert_eq!(state.expected_root.as_deref(), Some(dir_b.path()));
    }

    /// M4: `stop` clears the marker, so a start still in flight at stop
    /// time retires itself at completion.
    #[test]
    fn stop_retires_in_flight_start() {
        let dir = tempfile::tempdir().unwrap();
        let mut state = WatchState::default();
        claim_start(&mut state, dir.path().to_path_buf());
        // stop_project_watch's blocking body:
        state.expected_root = None;
        state.slot = None;
        let deb = spawn_watcher(dir.path().to_path_buf(), |_| {}).unwrap();
        assert!(!install_if_current(&mut state, dir.path(), deb));
        assert!(state.slot.is_none());
    }
}
