//! Project root resolution (V1.5 §13/§14/§144).
//!
//! Adding a project canonicalizes the chosen folder so that duplicate checks
//! compare true identities, not raw strings. `dunce::canonicalize` resolves
//! symlinks and 8.3 short names like `std::fs::canonicalize`, but strips the
//! `\\?\` extended-length prefix when the path does not need it, keeping
//! paths displayable and comparable (V1.5 §144).

use std::path::{Path, PathBuf};

use serde::Serialize;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ResolvedProject {
    pub root_path: String,
    pub name: String,
}

/// Canonicalize a user-chosen folder into a project root identity.
///
/// Errors (shown in the UI as-is):
/// - not a directory / not found
/// - drive roots (`C:\`) — almost certainly a misclick and would make the
///   Phase 2 watcher scan an entire drive
pub fn resolve_root(raw: &str) -> Result<(PathBuf, String), String> {
    let raw_path = raw.trim();
    if raw_path.is_empty() {
        return Err("No folder selected.".into());
    }

    let path = Path::new(raw_path);
    if !path.is_dir() {
        return Err(format!("Not a folder: {raw_path}"));
    }

    let canonical = dunce::canonicalize(path)
        .map_err(|e| format!("Cannot resolve folder {raw_path}: {e}"))?;

    if canonical.parent().is_none() {
        return Err("A drive root cannot be added as a project.".into());
    }

    let name = canonical
        .file_name()
        .and_then(|n| n.to_str())
        .map(|n| n.to_string())
        .expect("non-drive-root canonical path always has a file_name");

    Ok((canonical, name))
}

#[tauri::command]
pub fn resolve_project(raw_path: String) -> Result<ResolvedProject, String> {
    let (root, name) = resolve_root(&raw_path)?;
    Ok(ResolvedProject {
        root_path: root.to_string_lossy().into_owned(),
        name,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp_project(name: &str) -> PathBuf {
        let dir = tempfile::tempdir().expect("tempdir");
        let project = dir.path().join(name);
        std::fs::create_dir_all(&project).expect("create project dir");
        // Leak is fine for tests: keep the tempdir alive for the process.
        std::mem::forget(dir);
        project
    }

    #[test]
    fn resolves_trailing_slash_to_same_identity() {
        let project = tmp_project("Alpha");
        let plain = resolve_root(project.to_str().unwrap()).unwrap().0;
        let with_slash = resolve_root(&format!("{}\\", project.to_str().unwrap()))
            .unwrap()
            .0;
        assert_eq!(plain, with_slash);
    }

    #[test]
    fn resolves_wrong_letter_case_to_same_identity() {
        let project = tmp_project("Beta");
        let plain = resolve_root(project.to_str().unwrap()).unwrap().0;
        let lower = project.to_string_lossy().to_lowercase();
        let cased = resolve_root(&lower).unwrap().0;
        assert_eq!(plain, cased);
    }

    #[test]
    fn name_is_folder_basename() {
        let project = tmp_project("Gamma");
        let (_, name) = resolve_root(project.to_str().unwrap()).unwrap();
        assert_eq!(name, "Gamma");
    }

    #[test]
    fn rejects_missing_path() {
        assert!(resolve_root("Z:\\definitely\\not\\here").is_err());
    }

    #[test]
    fn rejects_file_not_folder() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("f.txt");
        std::fs::write(&file, "x").unwrap();
        assert!(resolve_root(file.to_str().unwrap()).is_err());
    }

    #[test]
    fn rejects_drive_root() {
        let err = resolve_root("C:\\").expect_err("drive root must be rejected");
        assert!(err.contains("drive root"), "unexpected error: {err}");
    }

    #[test]
    fn canonical_path_has_no_extended_prefix() {
        let project = tmp_project("Prefix");
        let (root, _) = resolve_root(project.to_str().unwrap()).unwrap();
        let s = root.to_string_lossy();
        assert!(!s.contains("\\\\?\\"), "extended prefix leaked: {s}");
    }

    #[test]
    fn rejects_empty() {
        assert!(resolve_root("   ").is_err());
    }
}
