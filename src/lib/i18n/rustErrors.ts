/**
 * Rust error-message localization (spec-016).
 *
 * The backend returns English error strings (interpolated with paths and
 * OS error text). Rather than threading a locale through every Rust
 * command, the frontend maps the KNOWN user-facing messages at display
 * time: an exact/prefix match returns the Chinese wording, anything else
 * passes through untouched (English beats a blank).
 *
 * Drift guard: each entry carries `src` — the literal fragment that must
 * exist in the Rust source (vitest greps src-tauri/src). If a Rust
 * message is reworded, the guard goes red and points here.
 *
 * Messages with a trailing interpolation (e.g. "Not found: {rel}")
 * translate the fixed part; the dynamic tail (path / OS error text)
 * stays as-is on purpose — it is data, not copy.
 */

import type { Locale } from "$lib/i18n/dict";

interface RustErrorEntry {
  /** Match against the error string: exact when no interpolation, else
   * startsWith on the prefix including its trailing separator. */
  prefix: string;
  zh: string;
  /** Fragment that must exist in src-tauri/src (drift guard). */
  src: string;
}

const ENTRIES: RustErrorEntry[] = [
  // handoff.rs — launch handoffs
  { prefix: "Cannot start Notepad:", zh: "无法启动记事本:", src: "Cannot start Notepad: {e}" },
  { prefix: "Cannot start VS Code:", zh: "无法启动 VS Code:", src: "Cannot start VS Code: {e}" },
  { prefix: "Project folder is not accessible:", zh: "项目文件夹无法访问:", src: "Project folder is not accessible: {e}" },
  { prefix: "Not found:", zh: "未找到:", src: "Not found: {rel}" },
  { prefix: "Not a file:", zh: "不是文件:", src: "Not a file: {rel}" },
  { prefix: "Not an executable:", zh: "不是可执行文件:", src: "Not an executable: {rel}" },
  { prefix: "Shortcut scheme is not allowed to auto-open:", zh: "此快捷方式协议不允许自动打开:", src: "Shortcut scheme is not allowed to auto-open: {u}" },
  { prefix: "Not a browser-openable file:", zh: "不是可在浏览器打开的文件:", src: "Not a browser-openable file: {rel}" },
  { prefix: "Cannot read shortcut:", zh: "无法读取快捷方式:", src: "Cannot read shortcut: {e}" },
  { prefix: "handoff task failed:", zh: "移交任务失败:", src: "handoff task failed: {e}" },
  { prefix: "open task failed:", zh: "打开任务失败:", src: "open task failed: {e}" },
  { prefix: "browser task failed:", zh: "浏览器任务失败:", src: "browser task failed: {e}" },
  // handoff.rs — ShellExecuteW error map (0.8.12 wording)
  { prefix: "The system is out of resources.", zh: "系统资源不足。", src: "The system is out of resources." },
  { prefix: "File not found.", zh: "找不到文件。", src: "File not found." },
  { prefix: "Path not found.", zh: "找不到路径。", src: "Path not found." },
  { prefix: "Access denied.", zh: "访问被拒绝。", src: "Access denied." },
  { prefix: "Not enough memory to launch.", zh: "内存不足,无法启动。", src: "Not enough memory to launch." },
  { prefix: "Invalid executable.", zh: "无效的可执行文件。", src: "Invalid executable." },
  { prefix: "A required dynamic-link library was not found.", zh: "找不到所需的动态链接库。", src: "A required dynamic-link library was not found." },
  { prefix: "No application is associated with this file type.", zh: "没有应用与此文件类型关联。", src: "No application is associated with this file type." },
  { prefix: "The file is in use by another program.", zh: "文件正被其他程序使用。", src: "The file is in use by another program." },
  { prefix: "The operating system refused to open it", zh: "操作系统拒绝打开它", src: "The operating system refused to open it (code {rc})" },
  // run.rs
  { prefix: "Not a runnable script", zh: "不是可运行的脚本", src: "Not a runnable script" },
  // file_inspect.rs
  { prefix: "No file specified.", zh: "未指定文件。", src: "No file specified." },
  { prefix: "Path escapes the project root.", zh: "路径超出项目根目录。", src: "Path escapes the project root." },
  { prefix: "Binary file — not shown as text.", zh: "二进制文件——不以文本显示。", src: "Binary file — not shown as text." },
  { prefix: "Binary file.", zh: "二进制文件。", src: "Binary file." },
  { prefix: "File is larger than 20 MB and will not be opened in the viewer.", zh: "文件超过 20 MB,不在查看器中打开。", src: "File is larger than 20 MB and will not be opened in the viewer." },
  { prefix: "Image is larger than 20 MB and will not be opened.", zh: "图片超过 20 MB,不打开。", src: "Image is larger than 20 MB and will not be opened." },
  { prefix: "File is larger than 100 MB and will not be opened.", zh: "文件超过 100 MB,不打开。", src: "File is larger than 100 MB and will not be opened." },
  // updater.rs
  { prefix: "Staged copy failed verification.", zh: "暂存的副本校验失败。", src: "Staged copy failed verification." },
  { prefix: "Not an experience install.", zh: "不是体验版安装。", src: "Not an experience install." },
  { prefix: "No update staged.", zh: "没有待安装的更新。", src: "No update staged." },
];

/**
 * Localize a backend error string for display. Prefix entries keep the
 * dynamic tail (everything after the matched prefix) untouched.
 */
export function translateRustError(raw: string, locale: Locale): string {
  if (locale !== "zh" || !raw) return raw;
  for (const entry of ENTRIES) {
    if (raw === entry.prefix) return entry.zh;
    if (raw.startsWith(entry.prefix)) {
      return entry.zh + raw.slice(entry.prefix.length);
    }
  }
  return raw;
}

/** Test/inspection hook: the drift-guard source anchors. */
export const RUST_ERROR_ANCHORS: readonly string[] = ENTRIES.map((e) => e.src);
