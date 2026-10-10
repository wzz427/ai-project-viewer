import { invoke } from "@tauri-apps/api/core";

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
 * Raw file bytes as one ArrayBuffer — the Tauri 2 fast channel (ipc
 * Response). PDFs ride this (spec-005 D2: bytes over the bridge, no asset
 * protocol); >100 MB refused Rust-side.
 */
export function readBinaryFile(
  rootPath: string,
  relPath: string,
): Promise<ArrayBuffer> {
  return invoke<ArrayBuffer>("read_binary_file", { rootPath, relPath });
}

/**
 * Hand a project-relative file to its OS-associated application — the
 * media player directly, never the file manager (owner 2026-10-01 item 10).
 * Rust-side since spec-006: the target is canonicalize-validated inside
 * the project first (§143/§144); the old JS string concat bypassed that.
 */
export function openWithDefaultApp(
  rootPath: string,
  relPath: string,
): Promise<void> {
  return invoke<void>("open_with_default_app", { rootPath, rel: relPath });
}

// --- External handoff (V1.5 §130–§144, spec-006) ---

/** §130 Quick Edit: open the file in Notepad. */
export function editInQuickEditor(
  rootPath: string,
  relPath: string,
): Promise<void> {
  return invoke<void>("edit_in_quick_editor", { rootPath, rel: relPath });
}

/**
 * §131/§140/§131 Full Edit in VS Code. `rel = null` hands over the whole
 * project root (§141 Open Project in VS Code). Window mode comes from the
 * persisted §134 setting — a mode arg, never an executable (§133).
 */
export function openInCodeEditor(
  rootPath: string,
  relPath: string | null,
  newWindow: boolean,
): Promise<void> {
  return invoke<void>("open_in_code_editor", {
    rootPath,
    rel: relPath,
    newWindow,
  });
}

/**
 * Show a node selected in its parent (§135). `rel = null` = the project
 * itself (§141 "Open in File Explorer"), which opens the folder window.
 */
export function revealInExplorer(
  rootPath: string,
  relPath: string | null,
): Promise<void> {
  return invoke<void>("reveal_in_explorer", { rootPath, rel: relPath });
}

/** §111/§115: .html/.htm via file URL, .url via its http(s) URL line. */
export function openInBrowser(
  rootPath: string,
  relPath: string,
): Promise<void> {
  return invoke<void>("open_in_browser", { rootPath, rel: relPath });
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

// --- Experience-channel update (SPEC-INFRA-001) ---

export interface UpdateInfo {
  available: boolean;
  note: string;
}

export function checkUpdate(): Promise<UpdateInfo> {
  return invoke<UpdateInfo>("check_update");
}

export function applyUpdate(): Promise<void> {
  return invoke<void>("apply_update");
}

/** Spawns the updated binary and exits the current process. */
export function relaunch(): Promise<void> {
  return invoke<void>("relaunch");
}

// --- Git review (V1.5 §43–§78, spec-007) ---

export type GitLetter = "M" | "A" | "D" | "R" | "C" | "T" | "?" | "U";

/** One scoped file row; `rel` is PROJECT-relative (§65 conversion in Rust). */
export interface GitChangeEntry {
  rel: string;
  letter: GitLetter;
  origRel?: string;
}

export interface GitCommit {
  hash: string;
  subject: string;
  ts: number;
}

/** §20 RuntimeGitState basis — runtime truth only, never persisted. */
export interface GitSnapshot {
  status: "ok" | "nonGit" | "gitMissing" | "error";
  error?: string;
  gitRoot?: string;
  /** "" = project root is the git root; "apps/viewer" = subdirectory mode. */
  scopeRel?: string;
  branch?: string;
  upstream?: string;
  ahead?: number;
  behind?: number;
  changes: GitChangeEntry[];
  staged: GitChangeEntry[];
  uniqueCount: number;
  commits: GitCommit[];
  refreshedAt: number;
}

export interface GitDiffResult {
  text: string;
  truncated: boolean;
  lines: number;
}

/** Full git state for one project; never rejects (failures fold into status). */
export function gitSnapshot(rootPath: string): Promise<GitSnapshot> {
  return invoke<GitSnapshot>("git_snapshot", { rootPath });
}

/** Unified diff for one file (§71); §72 caps already applied in Rust. */
export function gitDiff(
  rootPath: string,
  relPath: string,
  staged: boolean,
): Promise<GitDiffResult> {
  return invoke<GitDiffResult>("git_diff", { rootPath, rel: relPath, staged });
}
