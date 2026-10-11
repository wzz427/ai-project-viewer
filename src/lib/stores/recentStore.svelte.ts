/**
 * Open Recent list state (V1.5 §198, spec-010). At most RECENT_CAP
 * canonical paths, newest first. Persistence rides the existing stateSync
 * debounce via appState's recentFolders field — no timers or listeners of
 * its own (memory-minimization rule).
 *
 * Recording happens ONLY in projectStore.addProjectFromPath's success
 * path (user-initiated opens); session restore adopts via
 * restoreRecentFolders but never records (spec-010 D1 — restart replay
 * must not launder the MRU order).
 */

import { insertRecent, RECENT_CAP } from "$lib/services/recentList";

export const recentState = $state({
  folders: [] as string[],
});

/** A folder was successfully opened (added OR switched-to) → MRU front. */
export function recordRecentFolder(rootPath: string) {
  recentState.folders = insertRecent(recentState.folders, rootPath);
}

/** Row ✕ — drops one history entry; never touches any open project. */
export function removeRecentFolder(rootPath: string) {
  recentState.folders = recentState.folders.filter((p) => p !== rootPath);
}

export function clearRecentFolders() {
  recentState.folders = [];
}

/** Session-restore adoption; healed+capped by the appState parser. */
export function restoreRecentFolders(list: string[]) {
  recentState.folders = list.slice(0, RECENT_CAP);
}
