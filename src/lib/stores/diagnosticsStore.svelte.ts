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
});

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
