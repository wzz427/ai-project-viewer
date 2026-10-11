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

/** Single-slot git view (D3 + owner 2026-10-10 review): the main viewer
 *  shows this instead of the active file while set — a file diff OR a
 *  commit detail. Runtime-only, never session-restored (§20). Wrapped in
 *  an object because Svelte 5 forbids exporting a reassigned $state
 *  binding (state_invalid_export). */
export type GitView =
  | {
      kind: "diff";
      rootPath: string;
      rel: string;
      staged: boolean;
      /** Drill-down from a commit detail: diff of this file inside that
       *  commit (undefined = working-tree / staged diff). */
      commitHash?: string;
    }
  | { kind: "commit"; rootPath: string; hash: string };

import { diagEvent } from "$lib/stores/diagnosticsStore.svelte";

export const gitViewSlot = $state({ current: null as GitView | null });

export function openDiff(
  rootPath: string,
  rel: string,
  staged: boolean,
  commitHash?: string,
) {
  diagEvent(`git-view diff ${rel}${staged ? " (staged)" : ""}`);
  gitViewSlot.current = { kind: "diff", rootPath, rel, staged, commitHash };
}

export function openCommit(rootPath: string, hash: string) {
  diagEvent(`git-view commit ${hash}`);
  gitViewSlot.current = { kind: "commit", rootPath, hash };
}

export function closeGitView() {
  if (gitViewSlot.current) diagEvent("git-view close");
  gitViewSlot.current = null;
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
  resolve: () => void;
}

const pending = new Map<string, Pending>();
const seen = new Set<string>();

/** In-flight fetches (spec-012 M10): one fetchInto per root at a time.
 * Callers that arrive mid-flight mark `dirty` and share the same promise —
 * a follow-up round runs when the current one completes, so responses
 * always apply in request order and a slow old fetch can never overwrite a
 * newer snapshot (or mis-close a diff view off stale groups). */
interface InFlight {
  wait: Promise<void>;
  dirty: boolean;
}
const inFlight = new Map<string, InFlight>();

/** Per-root forget generation (spec-012 L-f5): bumped by forgetGit; an
 * in-flight fetch's follow-up rounds abort when the generation moved. */
const generation = new Map<string, number>();

async function fetchInto(rootPath: string) {
  const st = projectGitState(rootPath);
  st.loading = true;
  try {
    const snap = await gitSnapshot(rootPath);
    // Project removed while the fetch was in flight (L-f5): discard —
    // writing this would resurrect the forgotten project's git state and
    // pin it until exit. Identity check also catches forget+re-add (a new
    // state object exists; ours is stale).
    if (gitState.byRoot[rootPath] !== st) return;
    st.snapshot = snap;
    st.marks = marksByRel(snap);
    // A diff whose file left its group after the refresh (reverted,
    // staged, resolved) has nothing to show anymore — drop the slot.
    const slot = gitViewSlot.current;
    if (
      slot &&
      slot.kind === "diff" &&
      slot.rootPath === rootPath &&
      snap.status === "ok"
    ) {
      const group = slot.commitHash ? null : slot.staged ? snap.staged : snap.changes;
      if (group && !group.some((e) => e.rel === slot.rel)) closeGitView();
    }
  } catch (err) {
    if (gitState.byRoot[rootPath] !== st) return;
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
    if (gitState.byRoot[rootPath] === st) st.loading = false;
  }
}

/** Single-flight fetch (M10): dedupes concurrent callers per root and runs
 * follow-up rounds for requests that arrived mid-flight. */
function startFetch(rootPath: string): Promise<void> {
  const cur = inFlight.get(rootPath);
  if (cur) {
    cur.dirty = true;
    return cur.wait;
  }
  const entry: InFlight = { wait: Promise.resolve(), dirty: false };
  const gen = generation.get(rootPath) ?? 0;
  entry.wait = (async () => {
    do {
      entry.dirty = false;
      await fetchInto(rootPath);
      // forgetGit bumped the generation mid-flight → stop (L-f5).
      if ((generation.get(rootPath) ?? 0) !== gen) break;
    } while (entry.dirty);
    inFlight.delete(rootPath);
  })();
  inFlight.set(rootPath, entry);
  return entry.wait;
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
 * focus events produce one spawn set. The fetch itself rides startFetch's
 * single flight (M10).
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
    void startFetch(rootPath).finally(() => resolve());
  };
  pending.set(rootPath, { timer: setTimeout(fire, 400), promise, fire, resolve });
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
  return startFetch(rootPath);
}

/** Startup/new-project scan bookkeeping (App effect asks "anything new?"). */
export function gitNeedsInitialScan(rootPath: string): boolean {
  return !seen.has(rootPath);
}

export function markGitSeen(rootPath: string) {
  seen.add(rootPath);
}

/** Project removed → drop its state entirely (same point as forgetTabs).
 * Cancels the debounce AND disarms any in-flight fetch (L-f5): the result
 * is discarded at the identity check, follow-up rounds abort on the
 * generation bump, and awaiters are released so nothing hangs. */
export function forgetGit(rootPath: string) {
  generation.set(rootPath, (generation.get(rootPath) ?? 0) + 1);
  seen.delete(rootPath);
  const cur = pending.get(rootPath);
  if (cur) {
    clearTimeout(cur.timer);
    pending.delete(rootPath);
    cur.resolve();
  }
  delete gitState.byRoot[rootPath];
  if (gitViewSlot.current?.rootPath === rootPath) closeGitView();
}
