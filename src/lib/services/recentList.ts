/**
 * Open Recent pure helpers (V1.5 §198, spec-010). The list identity is the
 * resolved canonical path — the same truth project dedup uses — so these
 * functions never need path normalization of their own.
 */

export const RECENT_CAP = 10;

/**
 * MRU insert (spec-010 D5: the cap is enforced on BOTH ends — here on
 * write, and in appState's parse on read — so a hand-edited state file can
 * never leave an over-long list behind).
 */
export function insertRecent(
  list: readonly string[],
  path: string,
  cap: number = RECENT_CAP,
): string[] {
  return [path, ...list.filter((p) => p !== path)].slice(0, cap);
}

/** Folder basename for the row's first line ("ProjectViewer"). */
export function recentName(path: string): string {
  const parts = path.replace(/[\\/]+$/, "").split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

/** Parent directory for the row's dim second line ("…\VibeCoding"). */
export function recentParent(path: string): string {
  const trimmed = path.replace(/[\\/]+$/, "");
  const idx = Math.max(trimmed.lastIndexOf("\\"), trimmed.lastIndexOf("/"));
  return idx > 0 ? trimmed.slice(0, idx) : trimmed;
}
