/**
 * Watcher batch application — pure helpers (V1.5 §76–§85, spec-009).
 *
 * The Rust watcher emits one debounced FsChangeBatch per window; these
 * helpers decide which open tabs a batch touches. Pure so vitest can
 * cover the matching rules directly (the stores import them, they never
 * import stores).
 */

export interface RenamePair {
  from: string;
  to: string;
}

export interface FsChangeBatch {
  root: string;
  changed: string[];
  removed: string[];
  renames: RenamePair[];
  /** True when the window exceeded the storm limit (§80): itemized lists
   * are empty and the frontend must do one full refresh instead. */
  storm: boolean;
}

/** Exact-path change → content reload. An ancestor directory changing
 * (file added next to ours) is NOT a content change for this file. */
export function needsReload(rel: string, batch: FsChangeBatch): boolean {
  return batch.changed.some((c) => c === rel);
}

/** The path itself, or a directory above it, was removed or renamed
 * away (§83 delete handling covers descendants of removed dirs). */
export function isGone(rel: string, batch: FsChangeBatch): boolean {
  const under = (p: string) => rel === p || rel.startsWith(p + "/");
  return batch.removed.some(under) || batch.renames.some((r) => under(r.from));
}

/** New rel after renames — the file itself or an ancestor directory was
 * renamed (§84); null when unaffected. CHAINS resolve to the final name
 * (spec-012 L-f9): the same window can carry a→b then b→c, and stopping
 * at the first hop left tabs pointing at the intermediate name b — a path
 * that no longer exists, so the reload marked a live file deleted. The
 * renames.length iteration cap doubles as a cycle guard (a↔b loops are
 * malformed batches, not a hang). */
export function renamedRel(rel: string, renames: RenamePair[]): string | null {
  let cur = rel;
  for (let i = 0; i < renames.length; i++) {
    const next = oneRenameHop(cur, renames);
    if (next === null) break;
    cur = next;
  }
  return cur === rel ? null : cur;
}

function oneRenameHop(rel: string, renames: RenamePair[]): string | null {
  for (const r of renames) {
    if (rel === r.from) return r.to;
    if (rel.startsWith(r.from + "/")) return r.to + rel.slice(r.from.length);
  }
  return null;
}
