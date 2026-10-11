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
    /// §122 Executable Info card needs Modified; stat already has it, so it
    /// rides along (unix ms) instead of a second command/IO.
    pub modified: Option<u64>,
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
    let modified = meta
        .modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_millis() as u64);

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
        modified,
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
pub async fn inspect_file(
    root_path: String,
    rel_path: String,
) -> Result<FileInspection, String> {
    // ASYNC (L35 family, Phase 10 audit): file IO must stay off the native
    // main thread — inspect samples up to 5 MB before answering.
    tauri::async_runtime::spawn_blocking(move || inspect_file_inner(root_path, rel_path))
        .await
        .map_err(|e| format!("inspect task failed: {e}"))?
}

fn inspect_file_inner(root_path: String, rel_path: String) -> Result<FileInspection, String> {
    let path = resolve_file(Path::new(&root_path), &rel_path)?;
    inspect(&path)
}

#[derive(Debug)]
pub struct TextContent {
    pub text: String,
    pub encoding: FileEncoding,
    pub size_bytes: u64,
}

/// Decode a file to text per its detected encoding (V1.5 §101/§105).
/// Binary and >20 MB files are refused here — the guard lives in Rust so
/// the WebView can never receive them as text (§104/§106, spec-003 R3).
pub fn read_text(path: &Path) -> Result<TextContent, String> {
    let info = inspect(path)?;
    if info.encoding == FileEncoding::Binary {
        return Err("Binary file — not shown as text.".into());
    }
    if info.size_class == SizeClass::Huge {
        return Err("File is larger than 20 MB and will not be opened in the viewer.".into());
    }
    let bytes = std::fs::read(path).map_err(|e| format!("Cannot read file: {e}"))?;
    let text = decode_bytes(&bytes, info.encoding)?;
    Ok(TextContent {
        text,
        encoding: info.encoding,
        size_bytes: info.size_bytes,
    })
}

fn decode_bytes(bytes: &[u8], enc: FileEncoding) -> Result<String, String> {
    // inspect() and the fs::read in read_text re-open the file: an external
    // writer can truncate it in between, leaving fewer bytes than the BOM
    // the first sample detected. Fixed-length slices panicked exactly there
    // (release panic=abort = whole-app crash; spec-012 M5 — the watcher
    // reloadFile path sits inside that window by design). Degrade to an
    // empty tail instead.
    let after_bom = |n: usize| bytes.get(n..).unwrap_or(&[]);
    let (cow, _, _) = match enc {
        FileEncoding::Utf8 => UTF_8.decode(bytes),
        FileEncoding::Utf8Bom => UTF_8.decode(after_bom(3)),
        FileEncoding::Utf16LeBom => UTF_16LE.decode(after_bom(2)),
        FileEncoding::Utf16BeBom => UTF_16BE.decode(after_bom(2)),
        FileEncoding::Gb18030 => GB18030.decode(bytes),
        FileEncoding::Binary => return Err("Binary file.".into()),
    };
    Ok(cow.into_owned())
}

#[tauri::command]
pub async fn read_text_file(
    root_path: String,
    rel_path: String,
) -> Result<serde_json::Value, String> {
    // ASYNC (L35 family): up to 20 MB off the main thread.
    tauri::async_runtime::spawn_blocking(move || read_text_file_inner(root_path, rel_path))
        .await
        .map_err(|e| format!("read task failed: {e}"))?
}

fn read_text_file_inner(
    root_path: String,
    rel_path: String,
) -> Result<serde_json::Value, String> {
    let path = resolve_file(Path::new(&root_path), &rel_path)?;
    let content = read_text(&path)?;
    serde_json::to_value(serde_json::json!({
        "text": content.text,
        "encoding": content.encoding,
        "sizeBytes": content.size_bytes,
    }))
    .map_err(|e| format!("Serialization failed: {e}"))
}

/// Media (image) mime per extension; SVG rides the same safe `<img>` path
/// (V1.5 §110, spec-003 D3).
fn media_mime(name: &str) -> Option<&'static str> {
    let lower = name.to_lowercase();
    let ext = lower.rsplit('.').next()?;
    Some(match ext {
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "webp" => "image/webp",
        "gif" => "image/gif",
        "svg" => "image/svg+xml",
        _ => return None,
    })
}

pub struct MediaContent {
    pub data_url: String,
}

/// Read an image as a base64 data URL. >20 MB is refused with the same
/// never-send-whole rule as text (§106).
pub fn read_media(path: &Path) -> Result<MediaContent, String> {
    let info = inspect(path)?;
    if info.size_class == SizeClass::Huge {
        return Err("Image is larger than 20 MB and will not be opened.".into());
    }
    let mime = media_mime(
        &path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or_default(),
    )
    .ok_or_else(|| "Not a supported image format.".to_string())?;
    let bytes = std::fs::read(path).map_err(|e| format!("Cannot read file: {e}"))?;
    use base64::Engine;
    let b64 = base64::engine::general_purpose::STANDARD.encode(&bytes);
    Ok(MediaContent {
        data_url: format!("data:{mime};base64,{b64}"),
    })
}

#[tauri::command]
pub async fn read_media_file(
    root_path: String,
    rel_path: String,
) -> Result<serde_json::Value, String> {
    // ASYNC (L35 family): up to 20 MB read + base64 off the main thread.
    tauri::async_runtime::spawn_blocking(move || read_media_file_inner(root_path, rel_path))
        .await
        .map_err(|e| format!("read media task failed: {e}"))?
}

fn read_media_file_inner(
    root_path: String,
    rel_path: String,
) -> Result<serde_json::Value, String> {
    let path = resolve_file(Path::new(&root_path), &rel_path)?;
    let content = read_media(&path)?;
    serde_json::to_value(serde_json::json!({ "dataUrl": content.data_url }))
        .map_err(|e| format!("Serialization failed: {e}"))
}

/// Hard cap for the raw-bytes channel (spec-005 D4): the page pipeline
/// renders lazily, but the document bytes still live in memory whole, so
/// pathological files must be refused somewhere. 100 MB covers every §98
/// benchmark shape (100 scanned pages land well under it).
pub const BINARY_CHANNEL_LIMIT: u64 = 100 * 1024 * 1024;

/// Raw file bytes (PDFs, spec-005 D2: bytes over the bridge, no asset
/// protocol scope). No text-pipeline guards apply — callers route by
/// extension before the binary verdict (lessons L12 family).
pub fn read_binary(path: &Path) -> Result<Vec<u8>, String> {
    let info = inspect(path)?;
    if info.size_bytes > BINARY_CHANNEL_LIMIT {
        return Err("File is larger than 100 MB and will not be opened.".into());
    }
    std::fs::read(path).map_err(|e| format!("Cannot read file: {e}"))
}

/// Returns tauri::ipc::Response so the bytes cross as one ArrayBuffer
/// instead of a JSON number array (Tauri 2 fast channel).
#[tauri::command]
pub async fn read_binary_file(
    root_path: String,
    rel_path: String,
) -> Result<tauri::ipc::Response, String> {
    // ASYNC (L35 family): the PDF channel carries up to 100 MB — reading it
    // on the main thread would stall the window on a cold cache.
    tauri::async_runtime::spawn_blocking(move || {
        let path = resolve_file(Path::new(&root_path), &rel_path)?;
        let bytes = read_binary(&path)?;
        Ok(tauri::ipc::Response::new(bytes))
    })
    .await
    .map_err(|e| format!("read binary task failed: {e}"))?
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
    fn binary_channel_reads_bytes_and_rejects_escape() {
        let (root, file) = write("Bin", b"%PDF-1.7 fake bytes");
        assert_eq!(read_binary(&file).unwrap(), b"%PDF-1.7 fake bytes".to_vec());
        let escaped = read_binary(&Path::new(&root).join("..").join("nope.pdf"));
        assert!(escaped.is_err());
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

        let err = inspect_file_inner(
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
        let err = inspect_file_inner(root.to_string_lossy().into_owned(), "sub".into()).unwrap_err();
        assert!(err.contains("Not a file"), "unexpected: {err}");
    }

    #[test]
    fn command_accepts_forward_slash_rel_path() {
        let root = tmp_project("FwdSlash");
        std::fs::create_dir_all(root.join("docs")).unwrap();
        std::fs::write(root.join("docs/a.md"), "# hi").unwrap();
        let r = inspect_file_inner(root.to_string_lossy().into_owned(), "docs/a.md".into()).unwrap();
        assert_eq!(r.encoding, FileEncoding::Utf8);
    }
}

#[cfg(test)]
mod read_tests {
    use super::*;

    fn tmp_project(name: &str) -> PathBuf {
        let dir = tempfile::tempdir().expect("tempdir");
        let project = dir.path().join(name);
        std::fs::create_dir_all(&project).expect("create project dir");
        std::mem::forget(dir);
        project
    }

    fn write_bytes(root: &Path, rel: &str, bytes: &[u8]) {
        let p = root.join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, bytes).unwrap();
    }

    #[test]
    fn read_text_decodes_all_supported_encodings() {
        let root = tmp_project("ReadEnc");
        write_bytes(&root, "a.txt", "plain 中文".as_bytes());
        let mut bom = vec![0xEF, 0xBB, 0xBF];
        bom.extend_from_slice(b"bom text");
        write_bytes(&root, "b.txt", &bom);
        write_bytes(&root, "c.txt", &[0xFF, 0xFE, b'h', 0x00, b'i', 0x00]);
        write_bytes(&root, "d.txt", &[0xFE, 0xFF, 0x00, b'h', 0x00, b'i']);
        write_bytes(&root, "e.txt", &[0xD6, 0xD0, 0xCE, 0xC4]); // GB18030 中文

        assert_eq!(read_text(&root.join("a.txt")).unwrap().text, "plain 中文");
        assert_eq!(read_text(&root.join("b.txt")).unwrap().text, "bom text");
        assert_eq!(read_text(&root.join("c.txt")).unwrap().text, "hi");
        assert_eq!(read_text(&root.join("d.txt")).unwrap().text, "hi");
        assert_eq!(read_text(&root.join("e.txt")).unwrap().text, "中文");
    }

    #[test]
    fn read_text_refuses_binary() {
        let root = tmp_project("ReadBin");
        write_bytes(&root, "x.bin", b"ab\x00cd");
        assert!(read_text(&root.join("x.bin")).is_err());
    }

    #[test]
    fn read_text_refuses_huge_but_allows_large() {
        let root = tmp_project("ReadSize");
        write_bytes(&root, "large.log", &vec![b'x'; 6 * 1024 * 1024]);
        write_bytes(&root, "huge.log", &vec![b'x'; 21 * 1024 * 1024]);
        assert!(read_text(&root.join("large.log")).is_ok()); // 5–20 MB: allowed, gated by UI confirm
        let err = read_text(&root.join("huge.log")).unwrap_err();
        assert!(err.contains("20 MB"), "unexpected: {err}");
    }

    #[test]
    fn read_command_rejects_escape_and_dir() {
        let base = tempfile::tempdir().unwrap();
        let root = base.path().join("In");
        std::fs::create_dir_all(root.join("sub")).unwrap();
        std::mem::forget(base);
        assert!(read_text_file_inner(root.to_string_lossy().into_owned(), "../x".into()).is_err());
        assert!(read_text_file_inner(root.to_string_lossy().into_owned(), "sub".into()).is_err());
    }

    #[test]
    fn read_media_returns_data_url_for_all_formats() {
        let root = tmp_project("ReadMedia");
        // Minimal PNG header is enough — the reader does not parse the image.
        write_bytes(&root, "a.png", &[0x89, b'P', b'N', b'G', 0x0D, 0x0A, 0x1A, 0x0A, 1, 2, 3]);
        write_bytes(&root, "b.svg", b"<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>");
        let png = read_media(&root.join("a.png")).unwrap();
        assert!(png.data_url.starts_with("data:image/png;base64,"));
        let svg = read_media(&root.join("b.svg")).unwrap();
        assert!(svg.data_url.starts_with("data:image/svg+xml;base64,"));
    }

    #[test]
    fn read_media_rejects_non_image_and_huge() {
        let root = tmp_project("ReadMediaBad");
        write_bytes(&root, "a.txt", b"not an image");
        write_bytes(&root, "big.png", &vec![0u8; 21 * 1024 * 1024]);
        assert!(read_media(&root.join("a.txt")).is_err());
        assert!(read_media(&root.join("big.png")).is_err());
    }

    /// spec-012 M5: the file was BOM'd text when inspected but truncated by
    /// an external writer before read_text's second open — decoding must
    /// degrade instead of slicing past the end.
    #[test]
    fn decode_bytes_survives_truncated_bom_sample() {
        assert_eq!(decode_bytes(&[0xEF, 0xBB], FileEncoding::Utf8Bom).unwrap(), "");
        assert_eq!(decode_bytes(&[0xFF], FileEncoding::Utf16LeBom).unwrap(), "");
        assert_eq!(decode_bytes(&[0xFE], FileEncoding::Utf16BeBom).unwrap(), "");
        assert_eq!(decode_bytes(&[0xEF, 0xBB, 0xBF], FileEncoding::Utf8Bom).unwrap(), "");
        assert_eq!(decode_bytes(&[0xEF, 0xBB, 0xBF, b'x'], FileEncoding::Utf8Bom).unwrap(), "x");
        assert_eq!(
            decode_bytes(&[0xFF, 0xFE, b'h', 0x00], FileEncoding::Utf16LeBom).unwrap(),
            "h"
        );
    }
}
