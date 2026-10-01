/**
 * Tree Visibility (V1.5 §28/§29) — which directories the user SEES.
 *
 * The authoritative default-hidden list lives in Rust
 * (`src-tauri/src/file_tree.rs::DEFAULT_HIDDEN_DIRS`, 8 names) because the
 * tagging happens at listing time; this module owns the frontend half:
 * filtering entries against the toggle. Do NOT copy the 8-name list here —
 * one list, one home, or the two ends drift.
 *
 * Visibility and watcher ignore are separate concepts (§28): the watcher
 * list lives in `services/watcherIgnore.ts` and must never be merged with
 * visibility, even though both name directories.
 */

import type { TreeEntry } from "$lib/services/tauri";

/** Entries the user should see at this level (V1.5 §30 toggle, default OFF). */
export function visibleEntries(
  entries: readonly TreeEntry[],
  showSystemFolders: boolean,
): TreeEntry[] {
  return entries.filter((e) => showSystemFolders || !e.systemGenerated);
}
