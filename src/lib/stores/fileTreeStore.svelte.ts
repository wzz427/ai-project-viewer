/**
 * Per-project file-tree state (V1.5 §17/§18/§19, in-memory until Phase 4).
 *
 * Every path identity is PROJECT-RELATIVE with "." as the root key (§18/§19)
 * so persistence (Phase 4) can adopt this state with zero migration
 * (spec-002 D8). Children are cached per directory and loaded one level on
 * expand only (§27 lazy tree).
 */

import { listDirectory, type TreeEntry } from "$lib/services/tauri";

export const TREE_ROOT = ".";

export interface ProjectTreeState {
  /** Rel paths of expanded folders (project-relative, §18). */
  expandedFolders: string[];
  /** One-level listing cache per rel dir — filled on expand only. */
  children: Record<string, TreeEntry[]>;
  hiddenCounts: Record<string, number>;
  /** Rel dirs known to be empty → chevron renders faded (spec-002 D5). */
  emptyDirs: string[];
  loadErrors: Record<string, string>;
  /** Rel parent → pinned child names in manual order ("." = root, §19). */
  pinnedItems: Record<string, string[]>;
  foldersFirst: boolean;
  /** V1.5 §30: default OFF. */
  showSystemFolders: boolean;
  selectedRelPath: string | null;
}

function newState(): ProjectTreeState {
  return {
    expandedFolders: [],
    children: {},
    hiddenCounts: {},
    emptyDirs: [],
    loadErrors: {},
    pinnedItems: {},
    foldersFirst: true,
    showSystemFolders: false,
    selectedRelPath: null,
  };
}

export const treeState = $state({
  byRoot: {} as Record<string, ProjectTreeState>,
});

/** In-flight pinned-row drag (same-parent reorder only, V1.5 §38/§39). */
export const dragState = $state({
  parentRel: null as string | null,
  name: null as string | null,
});

export function treeFor(rootPath: string): ProjectTreeState {
  let st = treeState.byRoot[rootPath];
  if (!st) {
    st = newState();
    treeState.byRoot[rootPath] = st;
  }
  return st;
}

/** Drop state when a project tab is removed (call from removeProject). */
export function forgetTree(rootPath: string) {
  delete treeState.byRoot[rootPath];
}

export function joinRel(parentRel: string, name: string): string {
  return parentRel === TREE_ROOT ? name : `${parentRel}/${name}`;
}

function applyListing(
  st: ProjectTreeState,
  relDir: string,
  entries: TreeEntry[],
  hiddenCount: number,
) {
  st.children[relDir] = entries;
  st.hiddenCounts[relDir] = hiddenCount;
  delete st.loadErrors[relDir];
  const emptyIdx = st.emptyDirs.indexOf(relDir);
  if (entries.length === 0) {
    if (emptyIdx === -1) st.emptyDirs.push(relDir);
  } else if (emptyIdx !== -1) {
    st.emptyDirs.splice(emptyIdx, 1);
  }
}

/**
 * Rename/delete reconciliation (V1.5 §41/§42/§85) for one directory, run
 * when its listing is (re)fetched. A pin survives only when the rename is
 * unambiguous: exactly one pinned name vanished AND exactly one new
 * unpinned name appeared (spec-002 D7). The same function will consume
 * watcher events in Phase 9.
 */
function reconcilePins(
  st: ProjectTreeState,
  relDir: string,
  oldEntries: TreeEntry[] | undefined,
  newEntries: TreeEntry[],
) {
  const pinned = st.pinnedItems[relDir];
  if (!pinned || pinned.length === 0) return;

  const newNames = new Set(newEntries.map((e) => e.name));
  const missing = pinned.filter((n) => !newNames.has(n));
  if (missing.length === 0) return;

  if (oldEntries) {
    const oldNames = new Set(oldEntries.map((e) => e.name));
    const added = newEntries.map((e) => e.name).filter((n) => !oldNames.has(n));
    if (missing.length === 1 && added.length === 1) {
      // Reliable rename (§41): keep the pin in its position.
      pinned[pinned.indexOf(missing[0])] = added[0];
      return;
    }
  }
  // Anything less certain is delete cleanup (§42) — the new file, if any,
  // simply arrives unpinned (§40/§85).
  st.pinnedItems[relDir] = pinned.filter((n) => newNames.has(n));
}

/**
 * Fetch one level (bypassing the cache when `force`) and reconcile pins
 * against the previous snapshot before replacing it.
 */
async function loadDir(rootPath: string, relDir: string, force: boolean) {
  const st = treeFor(rootPath);
  if (!force && st.children[relDir]) return;
  try {
    const listing = await listDirectory(rootPath, relDir);
    reconcilePins(st, relDir, st.children[relDir], listing.entries);
    applyListing(st, relDir, listing.entries, listing.hiddenCount);
  } catch (err) {
    st.loadErrors[relDir] = String(err);
  }
}

/** Initial load of the project root (the only automatic listing, §27). */
export async function loadRoot(rootPath: string) {
  await loadDir(rootPath, TREE_ROOT, false);
}

export async function toggleExpand(rootPath: string, relDir: string) {
  const st = treeFor(rootPath);
  const idx = st.expandedFolders.indexOf(relDir);
  if (idx !== -1) {
    st.expandedFolders.splice(idx, 1);
    return;
  }
  await loadDir(rootPath, relDir, false);
  if (!st.loadErrors[relDir]) {
    st.expandedFolders.push(relDir);
  }
}

/**
 * Refresh: re-list every previously loaded level (root + anything cached,
 * expanded or not), reconciling pins per directory against the prior
 * snapshot. Collapsed-but-never-loaded levels are untouched — lazy stays
 * lazy (§27); they load on first expand.
 */
export async function refreshProject(rootPath: string) {
  const st = treeFor(rootPath);
  const dirs = Object.keys(st.children);
  if (!dirs.includes(TREE_ROOT)) dirs.unshift(TREE_ROOT);
  for (const d of dirs) {
    await loadDir(rootPath, d, true);
  }
}

export function pin(rootPath: string, parentRel: string, name: string) {
  const st = treeFor(rootPath);
  const list = st.pinnedItems[parentRel] ?? [];
  if (!list.includes(name)) list.push(name);
  st.pinnedItems[parentRel] = list;
}

export function unpin(rootPath: string, parentRel: string, name: string) {
  const st = treeFor(rootPath);
  const list = st.pinnedItems[parentRel];
  if (!list) return;
  const next = list.filter((n) => n !== name);
  if (next.length === 0) delete st.pinnedItems[parentRel];
  else st.pinnedItems[parentRel] = next;
}

export function isPinned(
  st: ProjectTreeState,
  parentRel: string,
  name: string,
): boolean {
  return st.pinnedItems[parentRel]?.includes(name) ?? false;
}

/**
 * Move `fromName` to sit before/after `toName` (same parent only, §38/§39).
 * Cursor-half semantics: top half of a row = before, bottom half = after —
 * without "after" there is no way to reach the last slot, and without the
 * top zone (FilesPanel) no way to reach the first (owner 2026-10-01).
 */
export function reorderPinned(
  rootPath: string,
  parentRel: string,
  fromName: string,
  toName: string,
  position: "before" | "after" = "before",
) {
  const st = treeFor(rootPath);
  const list = st.pinnedItems[parentRel];
  if (!list) return;
  const from = list.indexOf(fromName);
  const to = list.indexOf(toName);
  if (from === -1 || to === -1 || from === to) return;
  list.splice(from, 1);
  const anchor = list.indexOf(toName);
  list.splice(position === "before" ? anchor : anchor + 1, 0, fromName);
}

/** Drop target was above the whole pinned area → first slot. */
export function movePinnedToTop(rootPath: string, parentRel: string, name: string) {
  const st = treeFor(rootPath);
  const list = st.pinnedItems[parentRel];
  if (!list) return;
  const idx = list.indexOf(name);
  if (idx <= 0) return;
  list.splice(idx, 1);
  list.unshift(name);
}

export function setFoldersFirst(rootPath: string, value: boolean) {
  treeFor(rootPath).foldersFirst = value;
}

export function setShowSystemFolders(rootPath: string, value: boolean) {
  treeFor(rootPath).showSystemFolders = value;
}

export function selectNode(rootPath: string, relPath: string | null) {
  treeFor(rootPath).selectedRelPath = relPath;
}
