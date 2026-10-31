/**
 * Per-project file-tree state (V1.5 §17/§18/§19).
 *
 * Every path identity is PROJECT-RELATIVE with "." as the root key (§18/§19)
 * so persistence adopts this state with zero migration (spec-002 D8).
 * Children are cached per directory and loaded one level on expand only
 * (§27 lazy tree). System-folder visibility is app-wide — see
 * settingsStore (§22 AppSettings.fileTree, spec-004 D5).
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
  /** VS Code reveal (owner 2026-10-10): path whose row the FileTree view
   *  must scroll into view; set by revealInTree, cleared once scrolled.
   *  The ACTIVE-FILE highlight is NOT stored here — TreeItem derives it
   *  from the active tab (tabsStore), one source of truth. The old
   *  click-scoped selectedRelPath drifted from the tab and was removed. */
  revealTarget: string | null;
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
    revealTarget: null,
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

/** Tree row whose context menu is OPEN or was last ACTED ON (owner
 * 2026-10-10: right-clicking a row must highlight it, not the
 * previously-active file; owner 2026-10-12: ACTING on a menu item must
 * keep the row lit afterwards — "Show in File Explorer" on notes.txt used
 * to drop the highlight back onto the previously-active file, which reads
 * as the wrong row being selected). The override vanishes on
 * dismiss-without-action and on the next file activation; the lasting
 * highlight truth otherwise stays "active tab" (0.6.3 rule, single
 * source). */
export const contextMenuTarget = $state({
  rootPath: null as string | null,
  rel: null as string | null,
});

/** A file is becoming the active one (row click / open / reveal): the
 * sticky right-click highlight steps aside for the active-tab rule. */
export function clearTreeHighlight(rootPath: string) {
  if (contextMenuTarget.rootPath === rootPath) {
    contextMenuTarget.rootPath = null;
    contextMenuTarget.rel = null;
  }
}

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
  clearTreeHighlight(rootPath);
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
    const [miss] = missing;
    const [add] = added;
    if (miss !== undefined && add !== undefined) {
      // Reliable rename (§41): keep the pin in its position.
      const pos = pinned.indexOf(miss);
      if (pos !== -1) pinned[pos] = add;
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

/**
 * Session restore (Phase 4): adopt persisted expanded folders — fetch
 * exactly those levels (one listing each, never deeper, §27/§160.1) and
 * mark them expanded. Levels that no longer exist simply stay collapsed.
 */
export async function restoreExpandedFolders(
  rootPath: string,
  relDirs: string[],
) {
  const st = treeFor(rootPath);
  for (const rel of relDirs) {
    if (rel === TREE_ROOT) continue;
    await loadDir(rootPath, rel, false);
    if (!st.loadErrors[rel] && !st.expandedFolders.includes(rel)) {
      st.expandedFolders.push(rel);
    }
  }
}

/** Session restore (Phase 4): adopt persisted pins and preferences. */
export function restoreTreeState(
  rootPath: string,
  prefs: { foldersFirst: boolean; pinnedItems: Record<string, string[]> },
) {
  const st = treeFor(rootPath);
  st.foldersFirst = prefs.foldersFirst;
  st.pinnedItems = Object.fromEntries(
    Object.entries(prefs.pinnedItems).map(([k, v]) => [k, [...v]]),
  );
}

export async function toggleExpand(rootPath: string, relDir: string) {
  const st = treeFor(rootPath);
  const idx = st.expandedFolders.indexOf(relDir);
  if (idx !== -1) {
    st.expandedFolders.splice(idx, 1);
    return;
  }
  // FORCED re-list on every expand (owner 2026-10-10 "folder still empty"):
  // the cache short-circuit made collapse+re-expand serve a stale listing
  // forever — an empty folder could never recover within a session. One
  // IPC per expand is the same price as the first expand; the Phase 9
  // watcher will replace these "look again" reloads with push updates.
  await loadDir(rootPath, relDir, true);
  if (!st.loadErrors[relDir]) {
    st.expandedFolders.push(relDir);
  }
}

/** Fill one level into the shared cache if missing (no force, no
 *  expansion) — spec-017 locate walks through this so the levels it
 *  touches land in the SAME cache the tree reads; revealInTree right
 *  after then costs no extra IPC. */
export async function ensureDirLoaded(rootPath: string, relDir: string) {
  await loadDir(rootPath, relDir, false);
}

/**
 * Refresh: re-list the project root AND every previously loaded level
 * (anything cached, expanded or not), reconciling pins per directory
 * against the prior snapshot. Runs on project mount/switch-in (owner
 * 2026-10-17 staleness report: only the ACTIVE project is watched, §77 —
 * switching back is the "look again" moment for background-tab writes),
 * on ↻/Ctrl+R, and once per watcher batch. Collapsed-but-never-loaded
 * levels are untouched — lazy stays lazy (§27); they load on first expand.
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

/**
 * Reveal a file VS Code-style (owner 2026-10-10): expand every ancestor
 * (lazily loading each level), then mark the path for the FileTree view to
 * scroll its row into view. Aborts at a missing level (nothing to show).
 */
export async function revealInTree(rootPath: string, relPath: string) {
  // A file is being activated — the sticky right-click highlight yields
  // (owner 2026-10-12 highlight bug: both rules must hand over cleanly).
  clearTreeHighlight(rootPath);
  const st = treeFor(rootPath);
  const parts = relPath.split("/");
  for (let i = 1; i < parts.length; i++) {
    const dir = parts.slice(0, i).join("/");
    if (st.expandedFolders.includes(dir)) continue;
    await loadDir(rootPath, dir, false);
    if (st.loadErrors[dir]) return;
    st.expandedFolders.push(dir);
  }
  st.revealTarget = relPath;
}

/**
 * §84 rename synchronization for the tree (watcher-driven, runs BEFORE
 * refreshProject): rewrite the path-keyed state (children cache, expanded
 * folders, pin parents, reveal target) and swap renamed entry names out
 * of pin lists — a rename must not collapse expansions or drop pins.
 */
export function applyTreeRenames(
  rootPath: string,
  renames: { from: string; to: string }[],
): void {
  const st = treeFor(rootPath);
  if (renames.length === 0) return;
  // Fixpoint, not first hop (spec-012 L-f9): one window can carry a→b
  // then b→c; the iteration cap doubles as a cycle guard.
  const mapPath = (p: string): string => {
    let cur = p;
    for (let i = 0; i < renames.length; i++) {
      const hop = renames.find(
        (r) => cur === r.from || cur.startsWith(r.from + "/"),
      );
      if (!hop) break;
      cur = hop.to + cur.slice(hop.from.length);
    }
    return cur;
  };
  const lastName = (p: string) => p.slice(p.lastIndexOf("/") + 1);
  // Rides mapPath's fixpoint by mapping the full pin path (M14/L-f9).
  const mapName = (parentRel: string, name: string): string =>
    lastName(mapPath(parentRel === TREE_ROOT ? name : parentRel + "/" + name));

  st.children = Object.fromEntries(
    Object.entries(st.children).map(([k, v]) => [mapPath(k), v]),
  );
  st.expandedFolders = st.expandedFolders.map(mapPath);
  const pins: Record<string, string[]> = {};
  for (const [parent, names] of Object.entries(st.pinnedItems)) {
    const mappedParent = mapPath(parent);
    // A rename target colliding with an existing pin (or a chain folding
    // two names onto one) must not leave duplicate rows (spec-012 M14).
    const acc = pins[mappedParent] ?? [];
    for (const n of names.map((n) => mapName(parent, n))) {
      if (!acc.includes(n)) acc.push(n);
    }
    pins[mappedParent] = acc;
  }
  st.pinnedItems = pins;
  if (st.revealTarget) st.revealTarget = mapPath(st.revealTarget);
}

/**
 * §83/§42 removal cleanup (watcher-driven): drop tree state keyed under
 * removed paths so refreshProject never re-lists dead directories, and
 * pins inside removed dirs go away (§42).
 */
export function pruneRemovedDirs(rootPath: string, removed: string[]): void {
  if (removed.length === 0) return;
  const st = treeFor(rootPath);
  const isUnder = (p: string) =>
    removed.some((r) => p === r || p.startsWith(r + "/"));
  for (const key of Object.keys(st.children)) {
    if (isUnder(key)) delete st.children[key];
  }
  st.expandedFolders = st.expandedFolders.filter((p) => !isUnder(p));
  st.emptyDirs = st.emptyDirs.filter((p) => !isUnder(p));
  for (const key of Object.keys(st.loadErrors)) {
    if (isUnder(key)) delete st.loadErrors[key];
  }
  for (const key of Object.keys(st.pinnedItems)) {
    if (isUnder(key)) delete st.pinnedItems[key];
  }
  if (st.revealTarget && isUnder(st.revealTarget)) st.revealTarget = null;
}
