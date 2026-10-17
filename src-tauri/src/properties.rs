//! On-demand file metadata for the Properties dialog (owner 2026-10-17:
//! "我想看到一个文件的修改日期", with the constraint that the feature
//! must not add resident memory).
//!
//! NOTHING here caches or persists: each call stats the path fresh, hands
//! a plain struct to the frontend, and forgets it (V1.5 §6 memory rule —
//! timestamps deliberately never join the tree listing data).

use std::path::{Path, PathBuf};

use serde::Serialize;

#[derive(Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct FileProperties {
    pub is_dir: bool,
    /// Bytes; meaningless for folders (no recursive scan — a big tree
    /// would stall the dialog for seconds, owner's simplicity constraint).
    pub size_bytes: u64,
    /// Millis since the UNIX epoch; None when the filesystem refuses the
    /// field (FAT has no birth time, some network shares refuse access).
    pub modified_ms: Option<u64>,
    pub created_ms: Option<u64>,
    pub accessed_ms: Option<u64>,
}

fn to_ms(t: std::io::Result<std::time::SystemTime>) -> Option<u64> {
    t.ok()?
        .duration_since(std::time::UNIX_EPOCH)
        .ok()
        .map(|d| d.as_millis() as u64)
}

/// Resolve a project-relative FILE path, fenced to the project root the
/// same way the tree resolver fences folders (spec-002 `..` rule); `.` or
/// "" is the project root itself (project-tab Properties).
fn resolve_target(root: &Path, rel: &str) -> Result<PathBuf, String> {
    let root_canon = dunce::canonicalize(root)
        .map_err(|e| format!("Project folder is not accessible: {e}"))?;

    let rel = rel.trim();
    let rel = if rel.is_empty() || rel == "." {
        PathBuf::new()
    } else {
        PathBuf::from(rel.replace('/', "\\"))
    };

    let target = root_canon.join(&rel);
    let target_canon =
        dunce::canonicalize(&target).map_err(|_| format!("Not found: {}", rel.display()))?;

    if !target_canon.starts_with(&root_canon) {
        return Err("Path escapes the project root.".into());
    }
    Ok(target_canon)
}

pub fn read_properties(root: &Path, rel: &str) -> Result<FileProperties, String> {
    let path = resolve_target(root, rel)?;
    let md = std::fs::metadata(&path).map_err(|e| format!("Cannot read file info: {e}"))?;
    Ok(FileProperties {
        is_dir: md.is_dir(),
        size_bytes: md.len(),
        modified_ms: to_ms(md.modified()),
        created_ms: to_ms(md.created()),
        accessed_ms: to_ms(md.accessed()),
    })
}

/// ASYNC on purpose (L35 family): a stat on a stalled network share must
/// never block the native main thread behind a menu click.
#[tauri::command]
pub async fn file_properties(
    root_path: String,
    rel: String,
) -> Result<FileProperties, String> {
    tauri::async_runtime::spawn_blocking(move || read_properties(Path::new(&root_path), &rel))
        .await
        .map_err(|e| format!("properties task failed: {e}"))?
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp_project(name: &str) -> PathBuf {
        let dir = tempfile::tempdir().expect("tempdir");
        let project = dir.path().join(name);
        std::fs::create_dir_all(&project).expect("create project dir");
        std::mem::forget(dir);
        project
    }

    #[test]
    fn file_properties_report_size_and_times() {
        let root = tmp_project("Props");
        std::fs::write(root.join("a.txt"), "hello").unwrap();

        let p = read_properties(&root, "a.txt").unwrap();
        assert!(!p.is_dir);
        assert_eq!(p.size_bytes, 5);
        assert!(p.modified_ms.unwrap() > 1_600_000_000_000); // after 2020
        assert!(p.created_ms.is_some());
        assert!(p.accessed_ms.is_some());
    }

    #[test]
    fn forward_slash_rel_resolves() {
        let root = tmp_project("PropsFwd");
        std::fs::create_dir_all(root.join("sub")).unwrap();
        std::fs::write(root.join("sub").join("b.md"), "x").unwrap();

        let p = read_properties(&root, "sub/b.md").unwrap();
        assert_eq!(p.size_bytes, 1);
    }

    #[test]
    fn folder_and_project_root_report_is_dir() {
        let root = tmp_project("PropsDir");
        std::fs::create_dir_all(root.join("d")).unwrap();

        assert!(read_properties(&root, "d").unwrap().is_dir);
        // "." = the project root itself (project-tab Properties).
        assert!(read_properties(&root, ".").unwrap().is_dir);
    }

    #[test]
    fn dotdot_escape_rejected() {
        let base = tempfile::tempdir().unwrap();
        let root = base.path().join("In");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::create_dir_all(base.path().join("Out")).unwrap();
        std::mem::forget(base);

        assert!(read_properties(&root, "../Out").is_err());
    }

    #[test]
    fn missing_file_rejected() {
        let root = tmp_project("PropsMiss");
        assert!(read_properties(&root, "nope.txt").is_err());
    }
}
