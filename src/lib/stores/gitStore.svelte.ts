/**
 * Runtime git state (V1.5 §20, spec-007) — per-project snapshots that are
 * NEVER persisted: git truth is re-read on every launch and refresh.
 *
 * Refresh wiring (§73 Phase 7 triggers) happens in App.svelte effects;
 * this module only owns the state, the ~400 ms debounce (§75) and the
 * single-slot diff view (spec-007 D3: one ≤2 MB buffer, released on
 * close/switch — diffs are not tabs).
 */

import { gitSnapshot, type GitSnapshot } from "$lib/services/tauri";
import { marksByRel } from "$lib/services/gitFormat";

interface ProjectGitState {
  snapshot: GitSnapshot | null;
  loading: boolean;
  /** Cached marks map (built from snapshot; tree rows read it O(1)). */
  marks: Map<string, string>;
}

export const gitState = $state({
  byRoot: {} as Record<string, ProjectGitState>,
});

/** Single-slot diff view (D3): the main viewer shows this instead of the
 *  active file while set. Runtime-only — never session-restored (§20).
 *  Wrapped in an object because Svelte 5 forbids exporting a reassigned
 *  $state binding (state_invalid_export). */
export const gitDiffSlot = $state({
  current: null as { rootPath: string; rel: string; staged: boolean } | null,
});

export function openDiff(rootPath: string, rel: string, staged: boolean) {
  gitDiffSlot.current = { rootPath, rel, staged };
}

export function closeDiff() {
  gitDiffSlot.current = null;
}

export function gitSnapshotOf(rootPath: string): GitSnapshot | null {
  return gitState.byRoot[rootPath]?.snapshot ?? null;
}

export function gitMarkOf(rootPath: string, rel: string): string | null {
  return gitState.byRoot[rootPath]?.marks.get(rel) ?? null;
}

/** Project-tab indicator (§10): ● dirty / ✓ clean; undefined = no symbol
 *  (non-git, git missing, or nothing fetched yet). */
export function gitDirtyOf(rootPath: string): boolean | undefined {
  const snap = gitState.byRoot[rootPath]?.snapshot;
  if (!snap || snap.status !== "ok") return undefined;
  return snap.uniqueCount > 0;
}

// --- debounced refresh (§75 ~400 ms) --------------------------------------

interface Pending {
  timer: ReturnType<typeof setTimeout>;
  promise: Promise<void>;
  fire: () => void;
}

const pending = new Map<string, Pending>();
const seen = new Set<string>();

async function fetchInto(rootPath: string) {
  const st = projectGitState(rootPath);
  st.loading = true;
  try {
    const snap = await gitSnapshot(rootPath);
    st.snapshot = snap;
    st.marks = marksByRel(snap);
    // A diff whose file left its group after the refresh (reverted,
    // staged, resolved) has nothing to show anymore — drop the slot.
    const slot = gitDiffSlot.current;
    if (slot && slot.rootPath === rootPath && snap.status === "ok") {
      const group = slot.staged ? snap.staged : snap.changes;
      if (!group.some((e) => e.rel === slot.rel)) closeDiff();
    }
  } catch (err) {
    st.snapshot = {
      status: "error",
      error: String(err),
      changes: [],
      staged: [],
      uniqueCount: 0,
      commits: [],
      refreshedAt: Date.now(),
    };
    st.marks = new Map();
  } finally {
    st.loading = false;
  }
}

function projectGitState(rootPath: string): ProjectGitState {
  let st = gitState.byRoot[rootPath];
  if (!st) {
    st = { snapshot: null, loading: false, marks: new Map() };
    gitState.byRoot[rootPath] = st;
  }
  return st;
}

/**
 * Debounced refresh. Callers within the window coalesce onto one promise
 * (the ↻ spinner awaits it); the timer resets on each call so bursts of
 * focus events produce one spawn set.
 */
export function refreshGit(rootPath: string): Promise<void> {
  const cur = pending.get(rootPath);
  if (cur) {
    clearTimeout(cur.timer);
    cur.timer = setTimeout(cur.fire, 400);
    return cur.promise;
  }
  let resolve!: () => void;
  const promise = new Promise<void>((r) => (resolve = r));
  const fire = () => {
    pending.delete(rootPath);
    void fetchInto(rootPath).finally(() => resolve());
  };
  pending.set(rootPath, { timer: setTimeout(fire, 400), promise, fire });
  return promise;
}

/**
 * Immediate refresh (no debounce): the startup/new-project scan. Timer
 * queues in a hidden WebView2 window are frozen until an input event
 * (probe-verified), so the launch path must not depend on setTimeout —
 * and skipping the wait puts the badge up sooner anyway. Focus/manual/
 * switch keep the §75 debounce (those paths only run while visible).
 */
export function refreshGitNow(rootPath: string): Promise<void> {
  const cur = pending.get(rootPath);
  if (cur) {
    clearTimeout(cur.timer);
    cur.fire();
    return cur.promise;
  }
  return fetchInto(rootPath);
}

/** Startup/new-project scan bookkeeping (App effect asks "anything new?"). */
export function gitNeedsInitialScan(rootPath: string): boolean {
  return !seen.has(rootPath);
}

export function markGitSeen(rootPath: string) {
  seen.add(rootPath);
}

/** Project removed → drop its state entirely (same point as forgetTabs). */
export function forgetGit(rootPath: string) {
  seen.delete(rootPath);
  delete gitState.byRoot[rootPath];
  if (gitDiffSlot.current?.rootPath === rootPath) closeDiff();
}
