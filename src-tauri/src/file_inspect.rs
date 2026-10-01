//! File inspection pipeline (V1.5 §101–§106).
//!
//! Fixed order, never reordered: stat → size guard → BOM detection →
//! binary sniff → UTF-8 strict decode → GB18030 fallback. This command
//! returns classification metadata only — file CONTENT is never returned
//! (text viewers arrive in Phase 3 and will reuse this pipeline).

use std::path::{Path, PathBuf};

use encoding_rs::{UTF_16BE, UTF_16LE, UTF_8, GB18030};
use serde::Serialize;

/// 5 MB: below this a file opens normally (V1.5 §106).
const LARGE_FILE_BYTES: u64 = 5 * 1024 * 1024;
/// 20 MB: above this a file is never sent whole to the WebView.
const HUGE_FILE_BYTES: u64 = 20 * 1024 * 1024;
/// Binary sniff reads the head only, 4–16 KB (V1.5 §104).
const SNIFF_LEN: usize = 16 * 1024;

#[derive(Serialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "snake_case")]
pub enum SizeClass {
    Normal,
    Large,
    Huge,
}

#[derive(Serialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "snake_case")]
pub enum FileEncoding {
    Utf8,
    Utf8Bom,
    Utf16LeBom,
    Utf16BeBom,
    Gb18030,
    Binary,
}

#[derive(Serialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct FileInspection {
    pub size_bytes: u64,
    pub size_class: SizeClass,
    pub encoding: FileEncoding,
    pub is_binary: bool,
}

fn classify_size(size: u64) -> SizeClass {
    if size > HUGE_FILE_BYTES {
        SizeClass::Huge
    } else if size >= LARGE_FILE_BYTES {
        SizeClass::Large
    } else {
        SizeClass::Normal
    }
}

/// Resolve a project-relative file path, rejecting escapes (shared rule with
/// the tree listing; keeps both commands honest about the same root).
fn resolve_file(root: &Path, rel_path: &str) -> Result<PathBuf, String> {
    let root_canon = dunce::canonicalize(root)
        .map_err(|e| format!("Project folder is not accessible: {e}"))?;

    let rel = rel_path.trim();
    if rel.is_empty() {
        return Err("No file specified.".into());
    }
    let target = root_canon.join(rel.replace('/', "\\"));
    let target_canon =
        dunce::canonicalize(&target).map_err(|_| format!("File not found: {rel_path}"))?;

    if !target_canon.starts_with(&root_canon) {
        return Err("Path escapes the project root.".into());
    }
    if target_canon.is_dir() {
        return Err(format!("Not a file: {rel_path}"));
    }
    Ok(target_canon)
}

/// Run the V1.5 §101 pipeline on one file. Classification samples:
/// whole file up to 5 MB for exact text verdicts, head only beyond that
/// (such files never reach the WebView whole anyway, §106).
pub fn inspect(path: &Path) -> Result<FileInspection, String> {
    let meta = std::fs::metadata(path).map_err(|e| format!("Cannot read file info: {e}"))?;
    if meta.is_dir() {
        return Err("Not a file.".into());
    }
    let size = meta.len();
    let size_class = classify_size(size);

    let sample_len = if size <= LARGE_FILE_BYTES {
        size as usize
    } else {
        SNIFF_LEN
    };
    let sample = read_head(path, sample_len)?;

    let encoding = classify_bytes(&sample);
    let is_binary = encoding == FileEncoding::Binary;

    Ok(FileInspection {
        size_bytes: size,
        size_class,
        encoding,
        is_binary,
    })
}

fn read_head(path: &Path, len: usize) -> Result<Vec<u8>, String> {
    use std::io::Read;
    let mut file =
        std::fs::File::open(path).map_err(|e| format!("Cannot open file: {e}"))?;
    let mut buf = vec![0u8; len];
    let mut filled = 0usize;
    while filled < len {
        let n = file
            .read(&mut buf[filled..])
            .map_err(|e| format!("Cannot read file: {e}"))?;
        if n == 0 {
            break;
        }
        filled += n;
    }
    buf.truncate(filled);
    Ok(buf)
}

/// BOM first (V1.5 §102: BOM must precede NULL detection), then NULL sniff
/// (§104: binary detection precedes GB18030 fallback), then UTF-8 strict,
/// then GB18030 (§105). No-BOM UTF-16 lands in Binary — accepted limitation
/// (§103).
fn classify_bytes(sample: &[u8]) -> FileEncoding {
    if sample.starts_with(&[0xEF, 0xBB, 0xBF]) {
        // UTF-8 BOM: verify the rest is strict UTF-8; a broken tail falls
        // through the GB18030 net like any other text.
        let (_, _, had_errors) = UTF_8.decode(&sample[3..]);
        if !had_errors {
            return FileEncoding::Utf8Bom;
        }
        let (_, _, gb_errors) = GB18030.decode(&sample[3..]);
        return if !gb_errors {
            FileEncoding::Gb18030
        } else {
            FileEncoding::Utf8Bom
        };
    }
    if sample.starts_with(&[0xFF, 0xFE]) {
        let _ = UTF_16LE.decode(&sample[2..]);
        return FileEncoding::Utf16LeBom;
    }
    if sample.starts_with(&[0xFE, 0xFF]) {
        let _ = UTF_16BE.decode(&sample[2..]);
        return FileEncoding::Utf16BeBom;
    }

    if sample.contains(&0x00) {
        return FileEncoding::Binary;
    }

    let (_, _, utf8_errors) = UTF_8.decode(sample);
    if !utf8_errors {
        return FileEncoding::Utf8;
    }
    let (_, _, gb_errors) = GB18030.decode(sample);
    if !gb_errors {
        return FileEncoding::Gb18030;
    }
    FileEncoding::Binary
}

#[tauri::command]
pub fn inspect_file(
    root_path: String,
    rel_path: String,
) -> Result<FileInspection, String> {
    let path = resolve_file(Path::new(&root_path), &rel_path)?;
    inspect(&path)
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

    fn write(name: &str, bytes: &[u8]) -> (PathBuf, PathBuf) {
        let root = tmp_project(name);
        let file = root.join("sample.bin");
        std::fs::write(&file, bytes).expect("write sample");
        (root, file)
    }

    #[test]
    fn plain_utf8() {
        let (_, file) = write("Utf8", "hello 世界".as_bytes());
        let r = inspect(&file).unwrap();
        assert_eq!(r.encoding, FileEncoding::Utf8);
        assert!(!r.is_binary);
        assert_eq!(r.size_class, SizeClass::Normal);
    }

    #[test]
    fn utf8_with_bom() {
        let mut bytes = vec![0xEF, 0xBB, 0xBF];
        bytes.extend_from_slice("hello".as_bytes());
        let (_, file) = write("Utf8Bom", &bytes);
        assert_eq!(inspect(&file).unwrap().encoding, FileEncoding::Utf8Bom);
    }

    #[test]
    fn utf16_le_with_bom() {
        // "hi" in UTF-16 LE with BOM
        let bytes = [0xFF, 0xFE, b'h', 0x00, b'i', 0x00];
        let (_, file) = write("Utf16Le", &bytes);
        let r = inspect(&file).unwrap();
        assert_eq!(r.encoding, FileEncoding::Utf16LeBom);
        assert!(!r.is_binary); // BOM must rescue UTF-16 from NULL detection (§102)
    }

    #[test]
    fn utf16_be_with_bom() {
        let bytes = [0xFE, 0xFF, 0x00, b'h', 0x00, b'i'];
        let (_, file) = write("Utf16Be", &bytes);
        assert_eq!(inspect(&file).unwrap().encoding, FileEncoding::Utf16BeBom);
    }

    #[test]
    fn utf16_without_bom_is_binary_known_limitation() {
        // §103: no-BOM UTF-16 is not required to be detected; judged Binary.
        let bytes = [b'h', 0x00, b'i', 0x00];
        let (_, file) = write("Utf16NoBom", &bytes);
        let r = inspect(&file).unwrap();
        assert_eq!(r.encoding, FileEncoding::Binary);
        assert!(r.is_binary);
    }

    #[test]
    fn gb18030_fallback() {
        // "中文" in GB18030/GBK: D6 D0 CE C4 — invalid as UTF-8.
        let bytes = [0xD6, 0xD0, 0xCE, 0xC4];
        let (_, file) = write("Gb", &bytes);
        let r = inspect(&file).unwrap();
        assert_eq!(r.encoding, FileEncoding::Gb18030);
        assert!(!r.is_binary);
    }

    #[test]
    fn null_bytes_are_binary() {
        let bytes = b"ab\x00cd".to_vec();
        let (_, file) = write("Bin", &bytes);
        let r = inspect(&file).unwrap();
        assert_eq!(r.encoding, FileEncoding::Binary);
        assert!(r.is_binary);
    }

    #[test]
    fn empty_file_is_utf8() {
        let (_, file) = write("Empty", b"");
        assert_eq!(inspect(&file).unwrap().encoding, FileEncoding::Utf8);
    }

    #[test]
    fn size_boundaries() {
        let mk = |name: &str, size: u64| {
            let root = tmp_project(name);
            let file = root.join("blob.bin");
            use std::io::Write;
            let mut f = std::fs::File::create(&file).unwrap();
            // Content is zeros → also binary; size class is what we assert.
            f.write_all(&vec![0u8; size as usize]).unwrap();
            (root, file)
        };
        let cases: Vec<(&str, u64, SizeClass)> = vec![
            ("small", 5 * 1024 * 1024 - 1, SizeClass::Normal),
            ("at5", 5 * 1024 * 1024, SizeClass::Large), // inclusive lower
            ("at20", 20 * 1024 * 1024, SizeClass::Large), // inclusive upper
            ("over20", 20 * 1024 * 1024 + 1, SizeClass::Huge),
        ];
        for (name, size, expect) in cases {
            let (_, file) = mk(name, size);
            let r = inspect(&file).unwrap();
            assert_eq!(r.size_bytes, size, "{name}");
            assert_eq!(r.size_class, expect, "{name}");
        }
    }

    #[test]
    fn size_reported_even_for_huge() {
        let root = tmp_project("HugeMeta");
        let file = root.join("big.bin");
        std::fs::write(&file, vec![0u8; 21 * 1024 * 1024]).unwrap();
        let r = inspect(&file).unwrap();
        assert_eq!(r.size_class, SizeClass::Huge);
        assert_eq!(r.size_bytes, 21 * 1024 * 1024);
        assert!(r.is_binary);
    }

    #[test]
    fn command_rejects_escape() {
        let base = tempfile::tempdir().unwrap();
        let root = base.path().join("In");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(base.path().join("secret.txt"), "s").unwrap();
        std::mem::forget(base);

        let err = inspect_file(
            root.to_string_lossy().into_owned(),
            "../secret.txt".into(),
        )
        .unwrap_err();
        assert!(err.contains("escape") || err.contains("not found"), "unexpected: {err}");
    }

    #[test]
    fn command_rejects_directory() {
        let root = tmp_project("DirReject");
        std::fs::create_dir_all(root.join("sub")).unwrap();
        let err = inspect_file(root.to_string_lossy().into_owned(), "sub".into()).unwrap_err();
        assert!(err.contains("Not a file"), "unexpected: {err}");
    }

    #[test]
    fn command_accepts_forward_slash_rel_path() {
        let root = tmp_project("FwdSlash");
        std::fs::create_dir_all(root.join("docs")).unwrap();
        std::fs::write(root.join("docs/a.md"), "# hi").unwrap();
        let r = inspect_file(root.to_string_lossy().into_owned(), "docs/a.md".into()).unwrap();
        assert_eq!(r.encoding, FileEncoding::Utf8);
    }
}
