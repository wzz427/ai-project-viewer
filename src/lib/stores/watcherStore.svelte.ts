/**
 * Watcher orchestration (V1.5 §76/§183, spec-009): consumes the Rust
 * side's debounced "fs-changed" batches for the ACTIVE project and drives
 * the EXISTING refresh pipeline — tree (refreshProject, same path as ↻),
 * open tabs (reloadFile: content + deleted state + rename retargeting),
 * git (refreshGit) — then toasts per §82 for the active tab only
 * (spec-009 D4: background tabs update silently).
 *
 * All debouncing is Rust-side (D1); this handler runs straight through
 * per batch. Ordering matters: renames apply FIRST (§84) so their From
 * side never looks like a delete, then removals are pruned, then the tree
 * re-lists, then open tabs reload.
 */

import { listen } from "@tauri-apps/api/event";
import { activeProject } from "$lib/stores/projectStore.svelte";
import { applyTabRenames, reloadFile, tabsState } from "$lib/stores/tabsStore.svelte";
import {
  applyTreeRenames,
  pruneRemovedDirs,
  refreshProject,
} from "$lib/stores/fileTreeStore.svelte";
import { refreshGitNow } from "$lib/stores/gitStore.svelte";
import { toast } from "$lib/stores/toastStore.svelte";
import { diagEvent } from "$lib/stores/diagnosticsStore.svelte";
import { fileNameOf } from "$lib/services/viewerType";
import { isGone, needsReload, type FsChangeBatch } from "$lib/services/watcherApply";

let initialized = false;

/** Idempotent; called once from App mount. */
export function initWatcher() {
  if (initialized) return;
  initialized = true;
  void listen<FsChangeBatch>("fs-changed", (e) => {
    void handleBatch(e.payload);
  });
}

/** Root paths from two origins (frontend state vs canonicalized Rust)
 * must compare equal regardless of case and separator flavor. */
function sameRoot(a: string, b: string): boolean {
  const norm = (p: string) =>
    p.replace(/[\\/]+/g, "/").replace(/\/+$/, "").toLowerCase();
  return norm(a) === norm(b);
}

async function handleBatch(batch: FsChangeBatch) {
  const proj = activeProject();
  if (!proj || !sameRoot(proj.rootPath, batch.root)) return;
  const root = proj.rootPath;
  const itemized = batch.changed.length + batch.removed.length + batch.renames.length;
  diagEvent(`fs-change ${itemized} paths${batch.storm ? " storm" : ""}`);

  applyTabRenames(root, batch.renames);
  applyTreeRenames(root, batch.renames);
  pruneRemovedDirs(root, batch.removed);

  // Snapshot AFTER renames so tabs retargeted above reload under their
  // new names; storm mode re-checks everything (lists are empty, §80).
  const openRels = (tabsState.byRoot[root]?.openFiles ?? []).map(
    (t) => t.relativePath,
  );
  const activeRel = tabsState.byRoot[root]?.activeFileRelativePath ?? null;

  await refreshProject(root);

  let activeUpdatedName: string | null = null;
  for (const rel of openRels) {
    if (batch.storm || needsReload(rel, batch) || isGone(rel, batch)) {
      const changed = await reloadFile(root, rel);
      if (changed && rel === activeRel) activeUpdatedName = fileNameOf(rel);
    }
  }

  // NOT debounced refreshGit: watcher events often arrive while the
  // window is hidden (tray), and hidden WebView2 pages FREEZE the timer
  // queue (lessons L28/L34) — the debounce would never fire until the
  // window woke. Rust already coalesced events into this batch, so one
  // git spawn set per batch is the intended rate (§75's debounce stays
  // on the visible-window paths: focus/manual/switch).
  void refreshGitNow(root);
  if (activeUpdatedName) toast(`✓ ${activeUpdatedName} updated`);
}
