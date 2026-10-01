/**
 * Display ordering for the file tree (V1.5 §33–§36) — a pure function so it
 * is unit-testable without a DOM. Sorting NEVER implies disk mutation: it
 * only orders the rendered list (spec-002 red line, §176).
 *
 * Rules:
 * - Name mode: everything auto-sorted; Folders First stacks dirs above files
 *   (§34).
 * - Favorites mode: Pinned Area first in the user's manual order (files and
 *   folders interleaved, Folders First does NOT apply there, §36), then the
 *   Unpinned Area auto-sorted (Folders First DOES apply there).
 * - Natural, case-insensitive compare (spec-002 D4): file2 < file10.
 */

import type { TreeEntry } from "$lib/services/tauri";
import { visibleEntries } from "$lib/constants/treeVisibility";

export type SortMode = "name" | "favorites";

export interface TreeSortPrefs {
  sortMode: SortMode;
  foldersFirst: boolean;
  showSystemFolders: boolean;
  /** Pinned child names in the user's manual order for this parent (§19). */
  pinned: string[] | undefined;
}

export function naturalCompare(a: string, b: string): number {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}

function autoSorted(entries: TreeEntry[], foldersFirst: boolean): TreeEntry[] {
  const copy = [...entries];
  copy.sort((a, b) => naturalCompare(a.name, b.name));
  if (!foldersFirst) return copy;
  return [
    ...copy.filter((e) => e.isDir),
    ...copy.filter((e) => !e.isDir),
  ];
}

export function visibleSorted(
  entries: readonly TreeEntry[],
  prefs: TreeSortPrefs,
): TreeEntry[] {
  const visible = visibleEntries(entries, prefs.showSystemFolders);

  if (prefs.sortMode === "favorites") {
    const pinnedOrder = prefs.pinned ?? [];
    const pinnedSet = new Set(pinnedOrder);
    const byName = new Map(visible.map((e) => [e.name, e]));
    // Stored order wins; pinned names that vanished from disk are skipped
    // (the store's reconciliation cleans them up separately, §42).
    const pinnedArea = pinnedOrder
      .map((n) => byName.get(n))
      .filter((e): e is TreeEntry => e !== undefined);
    const unpinned = visible.filter((e) => !pinnedSet.has(e.name));
    return [...pinnedArea, ...autoSorted(unpinned, prefs.foldersFirst)];
  }

  return autoSorted(visible, prefs.foldersFirst);
}
