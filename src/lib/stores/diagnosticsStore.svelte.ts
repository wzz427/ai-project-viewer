/**
 * Session diagnostics shown in the Settings panel. Doubles as visible
 * evidence for Phase 1 acceptance: startup time (V1.5 §164) and that the
 * shortcut dispatcher really intercepts WebView2 accelerators (V1.5 §147).
 */
export const diagnostics = $state({
  startupMs: null as number | null,
  shortcutInterceptions: 0,
  lastShortcut: null as string | null,
  /** Exe modification time (unix seconds); shown so a stale instance is
   *  recognizable at a glance (single-instance revives old windows). */
  buildTime: null as number | null,
  /**
   * Bounded runtime trace (owner 2026-10-10: "你得有一个可以抓取运行信息
   * 的方法" after a viewer-freeze bug my replica could not reproduce).
   * Errors land here via the main.ts global hooks; key user actions land
   * via diagEvent at store chokepoints. Ring buffer — old entries drop.
   */
  log: [] as DiagEntry[],
});

export interface DiagEntry {
  t: number;
  kind: "error" | "warn" | "event";
  text: string;
}

const LOG_MAX = 600;

function diagPush(kind: DiagEntry["kind"], text: string) {
  const log = diagnostics.log;
  log.push({ t: Date.now(), kind, text: String(text).slice(0, 400) });
  if (log.length > LOG_MAX) log.splice(0, log.length - LOG_MAX);
}

export function diagEvent(text: string) {
  diagPush("event", text);
}

export function diagError(text: string) {
  diagPush("error", text);
}

export function diagWarn(text: string) {
  diagPush("warn", text);
}

export function recordStartup(ms: number) {
  diagnostics.startupMs = ms;
}

export function recordBuildTime(unixSeconds: number) {
  diagnostics.buildTime = unixSeconds;
}

export function recordShortcutInterception(combo: string) {
  diagnostics.shortcutInterceptions += 1;
  diagnostics.lastShortcut = combo;
}
