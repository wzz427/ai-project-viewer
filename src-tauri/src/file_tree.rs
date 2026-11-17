//! Single-level directory listing for the lazy file tree (V1.5 §27–§31).
//!
//! The command is deliberately dumb: it lists ONE directory level, tags
//! entries against the default tree-visibility list, and never filters or
//! recurses. Filtering and display order are frontend concerns — toggling
//! visibility must not trigger IO (spec-002 decision D1).

use std::path::{Path, PathBuf};

use serde::Serialize;

/// Directories hidden from the tree by default (V1.5 §29). Visibility only —
/// watcher ignore is a SEPARATE concept (V1.5 §28) with its own list in the
/// frontend `services/watcherIgnore.ts`; the two must not share one list.
const DEFAULT_HIDDEN_DIRS: &[&str] = &[
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".cache",
    ".next",
    "coverage",
];

#[derive(Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct TreeEntry {
    pub name: String,
    pub is_dir: bool,
    pub system_generated: bool,
}

#[derive(Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct DirectoryListing {
    pub entries: Vec<TreeEntry>,
    pub hidden_count: u32,
}

/// Resolve `rel_dir` (project-relative, `/`-separated, `.` or "" = root)
/// inside `root`, rejecting anything that escapes the project (spec-002:
/// `..` traversal must never reach outside the added project).
pub fn resolve_inside(root: &Path, rel_dir: &str) -> Result<PathBuf, String> {
    let root_canon = dunce::canonicalize(root)
        .map_err(|e| format!("Project folder is not accessible: {e}"))?;

    let rel = rel_dir.trim();
    let rel = if rel.is_empty() || rel == "." {
        PathBuf::new()
    } else {
        PathBuf::from(rel.replace('/', "\\"))
    };

    let target = root_canon.join(&rel);
    let target_canon = dunce::canonicalize(&target)
        .map_err(|_| format!("Folder not found: {rel_dir}"))?;

    if !target_canon.starts_with(&root_canon) {
        return Err("Path escapes the project root.".into());
    }
    if !target_canon.is_dir() {
        return Err(format!("Not a folder: {rel_dir}"));
    }
    Ok(target_canon)
}

/// List exactly one directory level, sorted by name for a stable base order.
/// Display ordering (folders first, pinned area, natural sort) happens in the
/// frontend; Rust does not sort for display (spec-002 D1/D4).
pub fn list_level(root: &Path, rel_dir: &str) -> Result<DirectoryListing, String> {
    let dir = resolve_inside(root, rel_dir)?;

    let mut entries: Vec<TreeEntry> = Vec::new();
    let mut hidden_count = 0u32;

    let reader = std::fs::read_dir(&dir).map_err(|e| format!("Cannot list folder: {e}"))?;
    for entry in reader {
        let entry = entry.map_err(|e| format!("Cannot read entry: {e}"))?;
        let is_dir = entry.file_type().map(|t| t.is_dir()).unwrap_or(false);
        let name = entry.file_name().to_string_lossy().into_owned();

        let system_generated = is_dir && DEFAULT_HIDDEN_DIRS.contains(&name.as_str());
        if system_generated {
            hidden_count += 1;
        }

        entries.push(TreeEntry {
            name,
            is_dir,
            system_generated,
        });
    }

    entries.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));

    Ok(DirectoryListing {
        entries,
        hidden_count,
    })
}

/// ASYNC on purpose (spec-012 M12, L35 family): expanding a tree node is
/// the highest-frequency IO in the app; a network drive that stalls turns a
/// sync command into a frozen native window.
#[tauri::command]
pub async fn list_directory(
    root_path: String,
    rel_dir: String,
) -> Result<DirectoryListing, String> {
    tauri::async_runtime::spawn_blocking(move || list_level(Path::new(&root_path), &rel_dir))
        .await
        .map_err(|e| format!("list task failed: {e}"))?
}

// ---------------------------------------------------------------------------
// Quick Open by name (V1.5 §148–§149; owner 2026-11-10 报障: bare
// `client-runtime-delivery-closeout.md` must find the file, not demand its
// full path). On-demand recursive walk with the TREE's visibility rules —
// no index, nothing cached, results die with the dialog (§149: never scan
// at startup, never keep a resident file list).
// ---------------------------------------------------------------------------

#[derive(Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct SearchMatch {
    /// True-case project-relative path, `/`-separated.
    pub rel: String,
    pub is_dir: bool,
}

#[derive(Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct SearchResult {
    pub matches: Vec<SearchMatch>,
    /// Matches collected before the cap (== matches.len() unless truncated).
    pub total: u32,
    /// The walk stopped at the collection cap — ranking past it unknown.
    pub truncated: bool,
}

/// Collection hard cap so a broad query ("a") can't balloon memory on a
/// huge tree; the UI asks the user to type more instead.
const COLLECT_CAP: usize = 2000;

/// Match rank (lower = better, sorted first). Without `/` in the query the
/// user is naming a FILE — basename classes come first; a path-contains
/// class still catches queries that are really folder names ("docs").
/// With `/` they're specifying structure — suffix-at-segment-boundary
/// ("specs/designs/x.md" → docs/specs/designs/x.md) beats plain contains.
fn match_rank(query: &str, by_name: bool, name_lower: &str, rel_lower: &str) -> Option<u8> {
    if by_name {
        if name_lower == query {
            Some(0)
        } else if name_lower.starts_with(query) {
            Some(1)
        } else if name_lower.contains(query) {
            Some(2)
        } else if rel_lower.contains(query) {
            Some(3)
        } else {
            None
        }
    } else if rel_lower == query || rel_lower.ends_with(&format!("/{query}")) {
        Some(0)
    } else if rel_lower.contains(query) {
        Some(1)
    } else {
        None
    }
}

pub fn search_level(
    root: &Path,
    raw_query: &str,
    include_system: bool,
    limit: usize,
    cap: usize,
) -> Result<SearchResult, String> {
    let root_canon = dunce::canonicalize(root)
        .map_err(|e| format!("Project folder is not accessible: {e}"))?;
    let query = raw_query.trim().replace('\\', "/").to_lowercase();
    if query.is_empty() {
        return Ok(SearchResult { matches: vec![], total: 0, truncated: false });
    }
    let by_name = !query.contains('/');

    struct Hit {
        rank: u8,
        depth: u16,
        rel_lower: String,
        rel: String,
        is_dir: bool,
    }

    // Parallel walk (0.8.32, owner 2026-11-17 报障 "搜个文件半分钟"):
    // the cross-tab sweep was the first component to enumerate whole
    // projects, and the owner's open set holds ~1.28M entries — a single
    // scandir thread needs ~30s cold. N scoped threads pull directories
    // off a shared worklist instead (std only; rayon isn't in the graph
    // and doesn't earn its way in for one walk). Symlinks/junctions are
    // never descended (file_type on Windows reports reparse points as
    // non-dirs) — no cycles, same entry taxonomy as list_level.
    // Termination: a thread that finds the list empty sleeps while
    // `active > 0` (others may still push); empty AND active == 0 ends.
    // Output determinism: hits are fully re-sorted below (rank, depth,
    // rel) regardless of thread interleaving; cap/truncated semantics
    // are exactly the sequential contract (≤ cap kept, truncated = a
    // hit was discarded), just applied at merge time.
    struct Shared {
        work: Vec<(PathBuf, String)>,
        active: usize,
        hits: Vec<Hit>,
        truncated: bool,
    }
    let shared = std::sync::Mutex::new(Shared {
        work: vec![(root_canon, String::new())],
        active: 0,
        hits: Vec::new(),
        truncated: false,
    });
    let cv = std::sync::Condvar::new();
    let threads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4)
        .clamp(1, 8);

    std::thread::scope(|scope| {
        for _ in 0..threads {
            scope.spawn(|| loop {
                let mut st = shared.lock().unwrap();
                let (dir, prefix) = loop {
                    if st.truncated {
                        return; // cap reached — stop everywhere
                    }
                    if let Some(item) = st.work.pop() {
                        break item;
                    }
                    if st.active == 0 {
                        return; // drained: nothing running, nothing queued
                    }
                    st = cv.wait(st).unwrap();
                };
                st.active += 1;
                drop(st);

                // Enumerate OUTSIDE the lock: child dirs and local hits
                // buffer up, then merge in one short critical section.
                let mut children: Vec<(PathBuf, String)> = Vec::new();
                let mut found: Vec<Hit> = Vec::new();
                if let Ok(reader) = std::fs::read_dir(&dir) {
                    for entry in reader.flatten() {
                        let is_dir = entry.file_type().map(|t| t.is_dir()).unwrap_or(false);
                        let name = entry.file_name().to_string_lossy().into_owned();
                        // Same visibility list as the tree (§29): hidden
                        // dirs are skipped entirely — a result the tree
                        // refuses to render would reveal nowhere.
                        if is_dir && DEFAULT_HIDDEN_DIRS.contains(&name.as_str()) && !include_system {
                            continue;
                        }
                        let rel = if prefix.is_empty() {
                            name.clone()
                        } else {
                            format!("{prefix}/{name}")
                        };
                        if is_dir {
                            children.push((entry.path(), rel.clone()));
                        }
                        let rel_lower = rel.to_lowercase();
                        let Some(rank) =
                            match_rank(&query, by_name, &name.to_lowercase(), &rel_lower)
                        else {
                            continue;
                        };
                        found.push(Hit {
                            rank,
                            depth: rel.matches('/').count() as u16,
                            rel_lower,
                            rel,
                            is_dir,
                        });
                    }
                } // unreadable folder: children stay empty — skip, don't kill

                let mut st = shared.lock().unwrap();
                st.active -= 1;
                if st.truncated {
                    // Another thread hit the cap mid-walk; drop these.
                } else if st.hits.len() >= cap {
                    if !found.is_empty() {
                        st.truncated = true;
                    }
                } else {
                    let room = cap - st.hits.len();
                    if found.len() > room {
                        st.truncated = true;
                    }
                    st.hits.extend(found.into_iter().take(room));
                }
                st.work.extend(children);
                drop(st);
                cv.notify_all();
            });
        }
    });

    // The truncated flag is authoritative from merge time (set only when
    // a hit was actually discarded — exactly the sequential contract; a
    // tree with exactly `cap` matches completes untruncated).
    let shared = shared.into_inner().unwrap();
    let mut hits = shared.hits;
    let truncated = shared.truncated;

    let total = hits.len() as u32;
    hits.sort_by(|a, b| {
        (a.rank, a.depth, &a.rel_lower).cmp(&(b.rank, b.depth, &b.rel_lower))
    });
    let matches = hits
        .into_iter()
        .take(limit)
        .map(|h| SearchMatch { rel: h.rel, is_dir: h.is_dir })
        .collect();
    Ok(SearchResult { matches, total, truncated })
}

/// Async like list_directory: a broad query over a big tree is real IO and
/// must never block the webview's command thread.
#[tauri::command]
pub async fn search_project_files(
    root_path: String,
    query: String,
    include_system: bool,
    limit: usize,
) -> Result<SearchResult, String> {
    tauri::async_runtime::spawn_blocking(move || {
        search_level(Path::new(&root_path), &query, include_system, limit, COLLECT_CAP)
    })
    .await
    .map_err(|e| format!("search task failed: {e}"))?
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn tmp_project(name: &str) -> PathBuf {
        let dir = tempfile::tempdir().expect("tempdir");
        let project = dir.path().join(name);
        std::fs::create_dir_all(&project).expect("create project dir");
        std::mem::forget(dir);
        project
    }

    fn mkdir(p: &Path, name: &str) {
        std::fs::create_dir_all(p.join(name)).expect("mkdir");
    }

    fn touch(p: &Path, name: &str) {
        std::fs::write(p.join(name), "x").expect("write");
    }

    fn names(listing: &DirectoryListing) -> Vec<String> {
        listing.entries.iter().map(|e| e.name.clone()).collect()
    }

    #[test]
    fn lists_exactly_one_level() {
        let root = tmp_project("Lazy");
        mkdir(&root, "a");
        mkdir(&root, "a/b");
        mkdir(&root, "a/b/c");

        let listing = list_level(&root, ".").unwrap();
        assert_eq!(names(&listing), ["a"]);
    }

    #[test]
    fn lists_deep_level_when_expanded() {
        let root = tmp_project("Deep");
        mkdir(&root, "a/b/c");

        let listing = list_level(&root, "a").unwrap();
        assert_eq!(names(&listing), ["b"]);

        let listing = list_level(&root, "a/b").unwrap();
        assert_eq!(names(&listing), ["c"]);
    }

    #[test]
    fn tags_system_dirs_and_counts_them() {
        let root = tmp_project("Tags");
        mkdir(&root, "node_modules");
        mkdir(&root, ".git");
        mkdir(&root, ".venv");
        mkdir(&root, "venv");
        mkdir(&root, "__pycache__");
        mkdir(&root, ".cache");
        mkdir(&root, ".next");
        mkdir(&root, "coverage");
        mkdir(&root, "dist");
        mkdir(&root, "build");
        mkdir(&root, "target");
        mkdir(&root, "src");
        touch(&root, "main.py");

        let listing = list_level(&root, ".").unwrap();
        assert_eq!(listing.hidden_count, 8);
        for e in &listing.entries {
            let expect = matches!(
                e.name.as_str(),
                ".git" | "node_modules" | ".venv" | "venv" | "__pycache__" | ".cache" | ".next" | "coverage"
            );
            assert_eq!(e.system_generated, expect, "tag mismatch: {}", e.name);
        }
        // dist/build/target are visible by default (V1.5 §29).
        let dist = listing.entries.iter().find(|e| e.name == "dist").unwrap();
        assert!(!dist.system_generated);
    }

    #[test]
    fn file_named_like_hidden_dir_is_not_tagged() {
        let root = tmp_project("FileTag");
        touch(&root, "coverage");

        let listing = list_level(&root, ".").unwrap();
        let e = &listing.entries[0];
        assert_eq!(e.name, "coverage");
        assert!(!e.is_dir);
        assert!(!e.system_generated);
        assert_eq!(listing.hidden_count, 0);
    }

    #[test]
    fn system_dirs_hidden_at_any_depth() {
        let root = tmp_project("DeepHidden");
        mkdir(&root, "src/__pycache__");
        mkdir(&root, "src/keep");

        let listing = list_level(&root, "src").unwrap();
        assert_eq!(listing.hidden_count, 1);
    }

    #[test]
    fn rejects_dotdot_escape() {
        let base = tempfile::tempdir().unwrap();
        let root = base.path().join("Inside");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::create_dir_all(base.path().join("Outside")).unwrap();
        std::mem::forget(base);

        let err = list_level(&root, "..\\Outside").unwrap_err();
        assert!(err.contains("escape") || err.contains("not found"), "unexpected: {err}");
    }

    #[test]
    fn rejects_forward_slash_escape() {
        let base = tempfile::tempdir().unwrap();
        let root = base.path().join("In2");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::create_dir_all(base.path().join("Out2")).unwrap();
        std::mem::forget(base);

        let err = list_level(&root, "../Out2").unwrap_err();
        assert!(err.contains("escape") || err.contains("not found"), "unexpected: {err}");
    }

    #[test]
    fn rejects_missing_subfolder() {
        let root = tmp_project("Missing");
        assert!(list_level(&root, "nope").is_err());
    }

    #[test]
    fn rejects_file_as_listing_target() {
        let root = tmp_project("FileTarget");
        touch(&root, "f.txt");
        assert!(list_level(&root, "f.txt").is_err());
    }

    #[test]
    fn empty_dir_lists_empty() {
        let root = tmp_project("EmptyDir");
        mkdir(&root, "empty");
        let listing = list_level(&root, "empty").unwrap();
        assert!(listing.entries.is_empty());
        assert_eq!(listing.hidden_count, 0);
    }

    #[test]
    fn base_order_is_deterministic() {
        let root = tmp_project("Order");
        touch(&root, "b.txt");
        touch(&root, "a.txt");
        mkdir(&root, "Zdir");
        mkdir(&root, "adir");

        let listing = list_level(&root, ".").unwrap();
        // Base order: lowercase name compare; display order is frontend work.
        assert_eq!(names(&listing), ["a.txt", "adir", "b.txt", "Zdir"]);
    }

    // --- search_level (Quick Open by name, V1.5 §148–§149) ---

    fn search(root: &Path, q: &str) -> Vec<String> {
        search_level(root, q, false, 50, COLLECT_CAP)
            .unwrap()
            .matches
            .iter()
            .map(|m| m.rel.clone())
            .collect()
    }

    #[test]
    fn search_finds_nested_file_by_exact_name() {
        // Owner 2026-11-10 报障 verbatim: bare filename, file nested deep.
        let root = tmp_project("SearchExact");
        mkdir(&root, "docs/specs/designs");
        touch(&root, "docs/specs/designs/client-runtime-delivery-closeout.md");

        assert_eq!(
            search(&root, "client-runtime-delivery-closeout.md"),
            vec!["docs/specs/designs/client-runtime-delivery-closeout.md".to_string()]
        );
    }

    #[test]
    fn search_is_case_insensitive_and_partial() {
        let root = tmp_project("SearchCi");
        mkdir(&root, "src/deep");
        touch(&root, "src/deep/Main.Py");

        assert_eq!(search(&root, "main.PY"), vec!["src/deep/Main.Py".to_string()]);
        assert_eq!(search(&root, "main"), vec!["src/deep/Main.Py".to_string()]);
        assert_eq!(search(&root, "Ain.p"), vec!["src/deep/Main.Py".to_string()]);
    }

    #[test]
    fn search_suffix_path_matches_at_segment_boundary() {
        let root = tmp_project("SearchSuffix");
        mkdir(&root, "docs/specs/designs");
        touch(&root, "docs/specs/designs/closeout.md");

        // A relative path that does NOT resolve from the root still finds
        // the file as a path-suffix query.
        assert_eq!(
            search(&root, "specs/designs/closeout.md"),
            vec!["docs/specs/designs/closeout.md".to_string()]
        );
        // Mid-path contains also works.
        assert_eq!(
            search(&root, "designs/closeout"),
            vec!["docs/specs/designs/closeout.md".to_string()]
        );
    }

    #[test]
    fn search_skips_hidden_dirs_unless_asked() {
        let root = tmp_project("SearchHidden");
        mkdir(&root, "node_modules/pkg");
        touch(&root, "node_modules/pkg/needle.js");
        mkdir(&root, "src");
        touch(&root, "src/ok.js");

        assert_eq!(search(&root, "needle"), Vec::<String>::new());
        let with_system = search_level(&root, "needle", true, 50, COLLECT_CAP).unwrap();
        assert_eq!(
            with_system
                .matches
                .iter()
                .map(|m| m.rel.clone())
                .collect::<Vec<_>>(),
            vec!["node_modules/pkg/needle.js".to_string()]
        );
        // Same visibility list as the tree: dist/target stay searchable.
        mkdir(&root, "target");
        touch(&root, "target/artifact.js");
        assert_eq!(search(&root, "artifact"), vec!["target/artifact.js".to_string()]);
    }

    #[test]
    fn search_matches_dirs_and_flags_them() {
        let root = tmp_project("SearchDirs");
        mkdir(&root, "docs/specs/designs");

        let res = search_level(&root, "designs", false, 50, COLLECT_CAP).unwrap();
        assert_eq!(res.matches.len(), 1);
        assert_eq!(res.matches[0].rel, "docs/specs/designs");
        assert!(res.matches[0].is_dir);
    }

    #[test]
    fn search_ranks_exact_prefix_contains_then_depth() {
        let root = tmp_project("SearchRank");
        mkdir(&root, "a/b");
        mkdir(&root, "m");
        mkdir(&root, "z");
        touch(&root, "needle");           // rank 0 (name == query), depth 0
        touch(&root, "m/needle");         // rank 0, depth 1 — alpha < z
        touch(&root, "z/needle");         // rank 0, depth 1
        mkdir(&root, "a/needle-docs");    // rank 1 (prefix), depth 1
        touch(&root, "a/b/needle-x");     // rank 1, depth 2
        touch(&root, "a/oneedle");        // rank 2 (contains)

        assert_eq!(
            search(&root, "needle"),
            vec![
                "needle".to_string(),
                "m/needle".to_string(),
                "z/needle".to_string(),
                "a/needle-docs".to_string(),
                "a/b/needle-x".to_string(),
                "a/oneedle".to_string(),
            ]
        );
    }

    #[test]
    fn search_path_contains_class_catches_folder_name_queries() {
        let root = tmp_project("SearchPathClass");
        mkdir(&root, "closeout-notes");
        touch(&root, "closeout-notes/day1.md");

        // Name doesn't contain "closeout-notes"; the path does (rank 3).
        assert_eq!(
            search(&root, "closeout-notes"),
            vec!["closeout-notes".to_string(), "closeout-notes/day1.md".to_string()]
        );
    }

    #[test]
    fn search_no_match_is_clean_empty() {
        let root = tmp_project("SearchEmpty");
        touch(&root, "main.py");
        let res = search_level(&root, "zzz-nope", false, 50, COLLECT_CAP).unwrap();
        assert!(res.matches.is_empty());
        assert_eq!(res.total, 0);
        assert!(!res.truncated);
    }

    #[test]
    fn search_limit_keeps_total_and_truncates() {
        let root = tmp_project("SearchLimit");
        mkdir(&root, "d");
        for i in 0..6 {
            touch(&root, &format!("d/f{i}.log"));
        }

        let res = search_level(&root, "f", false, 3, COLLECT_CAP).unwrap();
        assert_eq!(res.matches.len(), 3);
        assert_eq!(res.total, 6);
        assert!(!res.truncated);

        // Collection cap: walk stops, truncated flagged, total == cap.
        let res = search_level(&root, "f", false, 3, 4).unwrap();
        assert_eq!(res.matches.len(), 3);
        assert_eq!(res.total, 4);
        assert!(res.truncated);
    }

    #[test]
    fn search_empty_or_blank_query_returns_empty() {
        let root = tmp_project("SearchBlank");
        touch(&root, "main.py");
        for q in ["", "   ", "\\"] {
            let res = search_level(&root, q, false, 50, COLLECT_CAP).unwrap();
            assert!(res.matches.is_empty(), "query {q:?} should match nothing");
        }
    }

    // --- 0.8.32 parallel-walk guards (owner 2026-11-17: a name search
    // over the real open set took ~30s single-threaded — ~1.28M entries).
    // The pool must be observably identical to the sequential contract. ---

    /// A wide tree (many dirs at several depths, matches sprinkled
    /// everywhere) must return EXACTLY the known match set, fully sorted,
    /// no matter how the threads interleave. (The `search` helper caps at
    /// limit 50 — use search_level with a big limit so the SET is the
    /// subject, not the row cap; the first guard draft compared against
    /// the capped helper and "failed" on 108 expected hits.)
    #[test]
    fn search_parallel_finds_every_hit_in_sorted_order() {
        let root = tmp_project("SearchParallelWide");
        let mut expected = Vec::new();
        for i in 0..24 {
            mkdir(&root, &format!("pkg{i:02}"));
            mkdir(&root, &format!("pkg{i:02}/sub"));
            for j in 0..12 {
                if j % 3 == 0 {
                    touch(&root, &format!("pkg{i:02}/sub/needle{j:02}.rs"));
                    expected.push(format!("pkg{i:02}/sub/needle{j:02}.rs"));
                } else {
                    touch(&root, &format!("pkg{i:02}/sub/other{j:02}.rs"));
                }
            }
            if i % 2 == 0 {
                touch(&root, &format!("pkg{i:02}/needle-root.md"));
                expected.push(format!("pkg{i:02}/needle-root.md"));
            }
        }
        let res = search_level(&root, "needle", false, 500, COLLECT_CAP).unwrap();
        expected.sort();
        assert_eq!(res.total as usize, expected.len());
        let mut got_sorted: Vec<String> = res.matches.iter().map(|m| m.rel.clone()).collect();
        got_sorted.sort();
        assert_eq!(got_sorted, expected, "parallel walk must not lose or invent hits");
        // And the delivered order is the deterministic rank/depth/alpha
        // contract (name-prefix beats path-contains; shallower first).
        let root_first = res
            .matches
            .iter()
            .position(|m| m.rel == "pkg00/needle-root.md")
            .expect("shallow hit present");
        let deep_idx = res
            .matches
            .iter()
            .position(|m| m.rel == "pkg00/sub/needle00.rs")
            .unwrap();
        assert!(root_first < deep_idx, "shallower hit must rank first");
    }

    /// cap semantics under concurrency: at most `cap` kept, truncated
    /// set, limit still applied on top.
    #[test]
    fn search_parallel_cap_and_limit_hold() {
        let root = tmp_project("SearchParallelCap");
        for i in 0..10 {
            mkdir(&root, &format!("d{i}"));
            for j in 0..10 {
                touch(&root, &format!("d{i}/needle{j}.md"));
            }
        }
        let res = search_level(&root, "needle", false, 7, 33).unwrap();
        assert_eq!(res.matches.len(), 7, "limit caps the rows");
        assert_eq!(res.total, 33, "cap caps the collected hits");
        assert!(res.truncated, "100 hits existed, most were discarded");
    }

    /// Exactly `cap` matches in the whole tree → NOT truncated (the
    /// sequential contract: truncated means a hit was discarded).
    #[test]
    fn search_parallel_exact_cap_is_not_truncated() {
        let root = tmp_project("SearchParallelExact");
        for i in 0..5 {
            mkdir(&root, &format!("d{i}"));
            touch(&root, &format!("d{i}/needle.md"));
        }
        let res = search_level(&root, "needle", false, 50, 5).unwrap();
        assert_eq!(res.total, 5);
        assert!(!res.truncated, "nothing was discarded");
    }

    /// Degenerate shapes must terminate: a single dir with files only,
    /// and an empty root.
    #[test]
    fn search_parallel_terminates_on_degenerate_trees() {
        let root = tmp_project("SearchParallelFlat");
        touch(&root, "needle-a.md");
        touch(&root, "needle-b.md");
        touch(&root, "other.md");
        assert_eq!(search(&root, "needle").len(), 2);

        let empty = tmp_project("SearchParallelEmpty");
        assert!(search(&empty, "needle").is_empty());
    }

    /// Manual perf evidence against the owner's REAL whale directories
    /// (the 2026-11-17 report: ~30s perceived). Not part of the suite —
    /// run explicitly for the delivery report:
    ///   cargo test search_whale_timing -- --ignored --nocapture
    #[test]
    #[ignore = "manual timing evidence against real-world dirs; see spec-017 §七"]
    fn search_whale_timing() {
        let roots = [
            r"C:\Users\wzzpk\Desktop\VibeCoding\MyProxy",
            r"C:\Users\wzzpk\Desktop\VibeCoding\QuantTrading",
            r"C:\Users\wzzpk\Desktop\VibeCoding\BayesAPP\WordsStudy",
        ];
        for r in roots {
            let root = std::path::Path::new(r);
            if !root.is_dir() {
                println!("SKIP (absent): {r}");
                continue;
            }
            let t0 = std::time::Instant::now();
            let res = search_level(root, "zzz-no-such-needle-0832", false, 50, COLLECT_CAP)
                .expect("search runs");
            println!(
                "{r}: {:?} hits={} truncated={}",
                t0.elapsed(),
                res.matches.len(),
                res.truncated
            );
        }
    }
}
