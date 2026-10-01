//! State Migration Skeleton (V1.5 §23, spec-004 R5).
//!
//! AppState carries an explicit `version`. When the shape changes, a
//! migration step is added here and CURRENT_VERSION is raised — old files
//! are upgraded in place instead of being broken. V1 has a single version,
//! so the chain is empty; the routing (reject missing version, reject
//! newer-than-build) is already live and quarantines unusable files.

use serde_json::Value;

pub const CURRENT_VERSION: u64 = 1;

/// Ok(()) = the value now conforms to CURRENT_VERSION and may be handed to
/// the frontend. Err = unusable (no version field, or written by a newer
/// build) — the caller quarantines it.
pub fn migrate(value: &mut Value) -> Result<(), String> {
    let Some(version) = value.get("version").and_then(|v| v.as_u64()) else {
        return Err("state file has no version field".to_string());
    };
    if version > CURRENT_VERSION {
        return Err(format!(
            "state version {version} is newer than this build ({CURRENT_VERSION})"
        ));
    }
    // Forward chain. Today: version 1 == CURRENT_VERSION, nothing to do.
    // Future bumps add steps, e.g.:
    //   if version < 2 { /* v1 -> v2 changes */; value["version"] = 2; }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn v1_passes_untouched() {
        let mut v = json!({"version": 1, "projects": []});
        assert!(migrate(&mut v).is_ok());
        assert_eq!(v["projects"], json!([]));
    }

    #[test]
    fn missing_version_rejected() {
        let mut v = json!({"projects": []});
        assert!(migrate(&mut v).is_err());
    }

    #[test]
    fn newer_build_version_rejected() {
        let mut v = json!({"version": CURRENT_VERSION + 1});
        assert!(migrate(&mut v).is_err());
    }
}
