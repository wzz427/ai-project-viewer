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

#[tauri::command]
pub fn list_directory(
    root_path: String,
    rel_dir: String,
) -> Result<DirectoryListing, String> {
    list_level(Path::new(&root_path), &rel_dir)
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
}
