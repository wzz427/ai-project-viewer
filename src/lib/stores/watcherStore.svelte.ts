/**
 * Watcher orchestration (V1.5 §76/§183, spec-009): consumes the Rust
 * side's debounced "fs-changed" batches for the ACTIVE project and drives
 * the EXISTING refresh pipeline — tree (refreshProject, same path as ↻),
 * open tabs (reloadFile: content + deleted state + rename retargeting),
 * git (refreshGitNow) — then toasts per §82 for the active tab only
 * (spec-009 D4: background tabs update silently).
 *
 * 0.7.1 rework (owner startup-freeze, lessons L35): sustained writes make
 * batches arrive faster than a cycle can complete. Consequences here —
 * ① ONE lane per root: at most one processBatch() in flight; batches that
 * arrive meanwhile MERGE into a pending batch (path unions, last rename
 * per source wins) and one trailing cycle picks them up (work is never
 * dropped, never piled up — the lane itself is the rate limiter).
 * ② NO setTimeout anywhere in the lane (L34: hidden WebView2 freezes the
 * timer queue — a pacing sleep would stall the lane until a wake; Rust's
 * 400 ms debounce already bounds batch rate). refreshGitNow stays a
 * direct call: git_snapshot became an async command (off the main
 * thread) in the same fix — that, not frontend pacing, is the cure.
 *
 * All debouncing is still Rust-side (D1); ordering inside a cycle matters:
 * renames apply FIRST (§84) so their From side never looks like a delete,
 * then removals are pruned, then the tree re-lists, then open tabs reload.
 */

import { listen } from "@tauri-apps/api/event";
import { activeProject } from "$lib/stores/projectStore.svelte";
import { tf } from "$lib/i18n/t.svelte";
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

interface Lane {
  pending: FsChangeBatch | null;
  running: boolean;
}

const lanes = new Map<string, Lane>();

let initialized = false;

/** Idempotent; called once from App mount. */
export function initWatcher() {
  if (initialized) return;
  initialized = true;
  void listen<FsChangeBatch>("fs-changed", (e) => {
    enqueue(e.payload);
  });
}

/** Union-merge two windows into one logical batch (§81 coalescing). */
function mergeBatches(a: FsChangeBatch, b: FsChangeBatch): FsChangeBatch {
  const uniq = (xs: string[]) => [...new Set(xs)];
  const renames = new Map(a.renames.map((r) => [r.from, r]));
  for (const r of b.renames) renames.set(r.from, r); // last rename wins
  return {
    root: a.root,
    changed: uniq([...a.changed, ...b.changed]),
    removed: uniq([...a.removed, ...b.removed]),
    renames: [...renames.values()],
    storm: a.storm || b.storm,
  };
}

function enqueue(batch: FsChangeBatch) {
  const lane = lanes.get(batch.root) ?? { pending: null, running: false };
  lane.pending = lane.pending ? mergeBatches(lane.pending, batch) : batch;
  lanes.set(batch.root, lane);
  if (!lane.running) {
    lane.running = true;
    void drain(batch.root);
  }
}

async function drain(root: string) {
  const lane = lanes.get(root);
  if (!lane) return;
  try {
    while (lane.pending) {
      const batch = lane.pending;
      lane.pending = null;
      await processBatch(batch);
    }
  } finally {
    lane.running = false;
  }
}

/** Root paths from two origins (frontend state vs canonicalized Rust)
 * must compare equal regardless of case and separator flavor. */
function sameRoot(a: string, b: string): boolean {
  const norm = (p: string) =>
    p.replace(/[\\/]+/g, "/").replace(/\/+$/, "").toLowerCase();
  return norm(a) === norm(b);
}

async function processBatch(batch: FsChangeBatch) {
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
  // window woke. The lane's pacing already bounds the rate, and
  // git_snapshot itself is an async command (off the main thread, L35).
  void refreshGitNow(root);
  if (activeUpdatedName) toast(tf("toast.fileUpdated", { name: activeUpdatedName }));
}
