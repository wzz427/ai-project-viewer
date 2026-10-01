import { invoke } from "@tauri-apps/api/core";
import { openPath } from "@tauri-apps/plugin-opener";

export interface ResolvedProject {
  rootPath: string;
  name: string;
}

export interface TreeEntry {
  name: string;
  isDir: boolean;
  /** Tagged by Rust against the default visibility list (V1.5 §29). */
  systemGenerated: boolean;
}

export interface DirectoryListing {
  entries: TreeEntry[];
  hiddenCount: number;
}

export type SizeClass = "normal" | "large" | "huge";

export type FileEncoding =
  | "utf8"
  | "utf8_bom"
  | "utf16_le_bom"
  | "utf16_be_bom"
  | "gb18030"
  | "binary";

export interface FileInspection {
  sizeBytes: number;
  sizeClass: SizeClass;
  encoding: FileEncoding;
  isBinary: boolean;
}

/** Canonicalize a folder into a project identity (V1.5 §14/§144). */
export function resolveProject(rawPath: string): Promise<ResolvedProject> {
  return invoke<ResolvedProject>("resolve_project", { rawPath });
}

/**
 * One directory level for the lazy tree (V1.5 §27). Never recursive;
 * visibility filtering happens in the frontend (spec-002 D1).
 */
export function listDirectory(
  rootPath: string,
  relDir: string,
): Promise<DirectoryListing> {
  return invoke<DirectoryListing>("list_directory", { rootPath, relDir });
}

/** Classification metadata only — content never crosses the bridge (§101). */
export function inspectFile(
  rootPath: string,
  relPath: string,
): Promise<FileInspection> {
  return invoke<FileInspection>("inspect_file", { rootPath, relPath });
}

export interface TextFileContent {
  text: string;
  encoding: FileEncoding;
  sizeBytes: number;
}

/** Decoded text (guards already passed in Rust, §104/§106). */
export function readTextFile(
  rootPath: string,
  relPath: string,
): Promise<TextFileContent> {
  return invoke<TextFileContent>("read_text_file", { rootPath, relPath });
}

export interface MediaFileContent {
  dataUrl: string;
}

/** Image bytes as a base64 data URL (SVG rides the same safe path, §110). */
export function readMediaFile(
  rootPath: string,
  relPath: string,
): Promise<MediaFileContent> {
  return invoke<MediaFileContent>("read_media_file", { rootPath, relPath });
}

/**
 * Hand a project-relative file to its OS-associated application — the
 * media player directly, never the file manager (owner 2026-10-01 item 10).
 */
export function openWithDefaultApp(
  rootPath: string,
  relPath: string,
): Promise<void> {
  const abs = `${rootPath}\\${relPath.replace(/\//g, "\\")}`;
  return openPath(abs).then(() => undefined);
}

/** Milliseconds from Rust process start to the moment this is called. */
export function startupElapsedMs(): Promise<number> {
  return invoke<number>("startup_elapsed_ms");
}

/** Persisted AppState JSON, or null when starting fresh (spec-004). */
export function loadState(): Promise<string | null> {
  return invoke<string | null>("load_state");
}

/** Debounced/atomic state write; the Rust side also flushes on exit (§26). */
export function saveState(json: string): Promise<void> {
  return invoke<void>("save_state", { json });
}
