//! Atomic state file IO (V1.5 §26):
//!
//!   write temporary file -> flush -> atomic replace
//!
//! `std::fs::rename` on Windows goes through MoveFileExW with
//! MOVEFILE_REPLACE_EXISTING, so the final rename replaces the old file in
//! one step — state.json can hold the complete old or the complete new
//! payload, never a half write.

use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

pub fn atomic_write(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let tmp = path.with_extension("json.tmp");
    {
        let mut f = fs::File::create(&tmp).map_err(|e| e.to_string())?;
        use std::io::Write;
        f.write_all(bytes).map_err(|e| e.to_string())?;
        f.sync_all().map_err(|e| e.to_string())?;
    }
    if let Err(e) = fs::rename(&tmp, path) {
        let _ = fs::remove_file(&tmp);
        return Err(format!("atomic replace failed: {e}"));
    }
    Ok(())
}

/// Read + validate + migrate. `Ok(None)` means "no usable state" — file
/// missing, or corrupt/future-version and quarantined aside; the caller
/// starts fresh instead of crashing (spec-004 R5).
pub fn load(path: &Path) -> Result<Option<String>, String> {
    let bytes = match fs::read(path) {
        Ok(b) => b,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(e.to_string()),
    };
    let text = String::from_utf8(bytes).map_err(|_| "state file is not UTF-8".to_string())?;
    let mut value: serde_json::Value = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(_) => return Ok(quarantine(path)),
    };
    if super::migration::migrate(&mut value).is_err() {
        return Ok(quarantine(path));
    }
    Ok(Some(value.to_string()))
}

/// Rename an unusable state file aside as evidence, then report "start
/// fresh". Best effort: failure to rename still returns None.
fn quarantine(path: &Path) -> Option<String> {
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0);
    let name = path
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_else(|| "state.json".to_string());
    let backup = path.with_file_name(format!("{name}.corrupt-{ts}"));
    let _ = fs::rename(path, backup);
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn atomic_write_roundtrip_and_no_tmp_left_behind() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("state.json");
        atomic_write(&path, b"{\"version\":1}").unwrap();
        assert_eq!(fs::read_to_string(&path).unwrap(), "{\"version\":1}");
        assert!(dir.path().join("state.json.tmp").exists() == false);

        // Replace: old payload fully gone, still no tmp residue.
        atomic_write(&path, b"{\"version\":1,\"projects\":[]}").unwrap();
        assert_eq!(
            fs::read_to_string(&path).unwrap(),
            "{\"version\":1,\"projects\":[]}"
        );
        let residue: Vec<_> = std::fs::read_dir(dir.path())
            .unwrap()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_name().to_string_lossy().contains(".tmp"))
            .collect();
        assert!(residue.is_empty(), "tmp files must not linger");
    }

    #[test]
    fn load_missing_file_is_fresh_start() {
        let dir = tempfile::tempdir().unwrap();
        assert!(load(&dir.path().join("state.json")).unwrap().is_none());
    }

    #[test]
    fn corrupt_json_is_quarantined_not_fatal() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("state.json");
        fs::write(&path, "{\"version\":1,,}").unwrap();
        assert!(load(&path).unwrap().is_none());
        assert!(!path.exists(), "corrupt file must be renamed aside");
        let leftovers: Vec<_> = std::fs::read_dir(dir.path())
            .unwrap()
            .filter_map(|e| e.ok())
            .map(|e| e.file_name().to_string_lossy().into_owned())
            .collect();
        assert!(
            leftovers.iter().any(|n| n.starts_with("state.json.corrupt-")),
            "quarantine copy kept as evidence: {leftovers:?}"
        );
    }

    #[test]
    fn missing_version_is_quarantined() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("state.json");
        fs::write(&path, "{\"projects\":[]}").unwrap();
        assert!(load(&path).unwrap().is_none());
        assert!(!path.exists());
    }

    #[test]
    fn future_version_is_quarantined() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("state.json");
        fs::write(&path, "{\"version\":99}").unwrap();
        assert!(load(&path).unwrap().is_none());
        assert!(!path.exists());
    }

    #[test]
    fn valid_v1_loads() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("state.json");
        fs::write(&path, "{\"version\":1,\"settings\":{\"theme\":\"dark\"}}").unwrap();
        let loaded = load(&path).unwrap().unwrap();
        let v: serde_json::Value = serde_json::from_str(&loaded).unwrap();
        assert_eq!(v["version"], 1);
        assert_eq!(v["settings"]["theme"], "dark");
    }
}
