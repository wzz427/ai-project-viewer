/**
 * Watcher Ignore list (V1.5 §32) — directories the (future) file watcher
 * will NOT monitor in real time.
 *
 * The watcher itself lands in Phase 9 (V1.5 §183); this module exists NOW so
 * the ignore list is physically separate from tree visibility (§28): this
 * file must never import `constants/treeVisibility.ts` nor be imported by
 * it. The two lists deliberately differ — `dist`/`build`/`target` are
 * VISIBLE in the tree (§29) but not watched (§32): watching build output
 * would spam change events with no reader.
 */

/** 11 names (V1.5 §32) — a superset of the 8 visibility-hidden names. */
export const WATCHER_IGNORE_DIR_NAMES: readonly string[] = [
  ".git",
  "node_modules",
  ".venv",
  "venv",
  "__pycache__",
  ".cache",
  ".next",
  "coverage",
  "dist",
  "build",
  "target",
];

export function isWatcherIgnored(name: string): boolean {
  return WATCHER_IGNORE_DIR_NAMES.includes(name);
}
