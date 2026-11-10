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
    let mut hits: Vec<Hit> = Vec::new();
    let mut truncated = false;
    // Iterative walk, symlinks/junctions never descended (file_type on
    // Windows reports reparse points as non-dirs) — no cycles, same
    // entry taxonomy as list_level so search and tree agree.
    let mut stack: Vec<(PathBuf, String)> = vec![(root_canon, String::new())];
    while let Some((dir, prefix)) = stack.pop() {
        if truncated {
            break;
        }
        let reader = match std::fs::read_dir(&dir) {
            Ok(r) => r,
            Err(_) => continue, // unreadable folder: skip, don't kill the search
        };
        for entry in reader.flatten() {
            let is_dir = entry.file_type().map(|t| t.is_dir()).unwrap_or(false);
            let name = entry.file_name().to_string_lossy().into_owned();
            // Same visibility list as the tree (§29): hidden dirs are
            // skipped entirely — a result the tree refuses to render
            // would reveal nowhere.
            if is_dir && DEFAULT_HIDDEN_DIRS.contains(&name.as_str()) && !include_system {
                continue;
            }
            let rel = if prefix.is_empty() { name.clone() } else { format!("{prefix}/{name}") };
            if is_dir {
                stack.push((entry.path(), rel.clone()));
            }
            let rel_lower = rel.to_lowercase();
            let Some(rank) = match_rank(&query, by_name, &name.to_lowercase(), &rel_lower)
            else {
                continue;
            };
            if hits.len() >= cap {
                truncated = true;
                break;
            }
            hits.push(Hit {
                rank,
                depth: rel.matches('/').count() as u16,
                rel_lower,
                rel,
                is_dir,
            });
        }
    }

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
}
