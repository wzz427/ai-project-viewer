/**
 * File-type → viewer routing (V1.5 §21/§86–§111/§142). Extension-based;
 * binary/huge verdicts come from the Rust pipeline at open time and
 * override this mapping.
 */

export type ViewerType =
  | "markdown"
  | "pdf"
  | "text"
  | "code"
  | "json"
  | "image"
  | "executable"
  | "binary"
  | "unsupported";

const MARKDOWN = new Set(["md", "markdown"]);
const TEXT = new Set(["txt", "log", "csv"]);
const IMAGE = new Set(["png", "jpg", "jpeg", "webp", "gif", "svg"]);
/** Video/audio the app has no viewer for — Open hands off to the OS
 * default player (owner 2026-10-24: an MP4's Open "没有任何反应"; his
 * expectation is the player, Explorer's double-click behavior). */
const MEDIA = new Set([
  "mp4", "m4v", "mkv", "mov", "webm", "avi", "wmv", "flv", "mpg", "mpeg",
  // NO "ts": in a code-viewing app .ts is TypeScript; MPEG-TS video is
  // covered by m2ts (caught by the iconFamily test the moment it slipped
  // in — 0.8.10).
  "m2ts", "mp3", "wav", "flac", "ogg", "m4a", "aac", "wma", "opus",
  "mid", "midi", "aif", "aiff",
]);
const CODE = new Set([
  "py", "js", "ts", "tsx", "jsx", "rs", "go", "java", "c", "cpp", "h",
  "html", "htm", "css", "scss", "yaml", "yml", "toml", "sh", "ps1",
  "cmd", "bat", "sql",
]);

export function extOf(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx === -1 ? "" : name.slice(idx + 1).toLowerCase();
}

export function viewerTypeFor(name: string): ViewerType {
  const ext = extOf(name);
  if (MARKDOWN.has(ext)) return "markdown";
  if (ext === "json") return "json";
  if (ext === "pdf") return "pdf";
  if (IMAGE.has(ext)) return "image";
  // §122: .exe left-click opens the Executable Info card (stat only).
  if (ext === "exe") return "executable";
  if (CODE.has(ext)) return "code";
  if (TEXT.has(ext)) return "text";
  // Unknown extension: open as plain text when the pipeline says it is text
  // (decided at open time) — reading is this app's main verb.
  return "text";
}

export function isPdfName(name: string): boolean {
  return extOf(name) === "pdf";
}

export type IconFamily =
  | "markdown"
  | "pdf"
  | "code"
  | "json"
  | "image"
  | "media"
  | "file";

/** Tab/tree icon family (spec-014 D4): derived from the SAME routing that
 *  decides which viewer opens — the icon is a true preview of the click,
 *  never a second classification table that could drift from the viewer
 *  mapping. */
export function iconFamilyOf(name: string): IconFamily {
  // Media is checked before viewerTypeFor: media files never become tabs,
  // so the viewerType fallback ("text") must not drive their icon.
  if (MEDIA.has(extOf(name))) return "media";
  switch (viewerTypeFor(name)) {
    case "markdown":
      return "markdown";
    case "pdf":
      return "pdf";
    case "code":
      return "code";
    case "json":
      return "json";
    case "image":
      return "image";
    default:
      return "file";
  }
}

export function isImageName(name: string): boolean {
  return IMAGE.has(extOf(name));
}

export function isMediaName(name: string): boolean {
  return MEDIA.has(extOf(name));
}

export function fileNameOf(relPath: string): string {
  const idx = relPath.lastIndexOf("/");
  return idx === -1 ? relPath : relPath.slice(idx + 1);
}
