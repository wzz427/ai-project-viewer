/**
 * Locate store supersede guards (spec-017 §七 D22, owner 2026-11-17:
 * over the real open set a name search walks ~1.3M entries — an
 * inFlight-style gate made Enter during a flight do NOTHING silently,
 * compounding "半分钟没反馈"). A new submit/close must SUPERSEDE: stale
 * results arrive unheard, newer submits always run.
 *
 * Filesystem access is mocked; locatePath stays real (pure).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

// vi.mock factories hoist above every const — the tabs must come from
// vi.hoisted or the factory reads them before initialization.
const { tabA, tabB } = vi.hoisted(() => ({
  tabA: { id: "a", name: "Alpha", rootPath: "C:\\Alpha" },
  tabB: { id: "b", name: "Beta", rootPath: "C:\\Beta" },
}));

vi.mock("$lib/services/tauri", () => ({
  pathsExist: vi.fn(async () => [true]),
  // Every call parks on a fresh deferred the test resolves by hand.
  searchProjectFiles: vi.fn(),
}));
vi.mock("$lib/stores/toastStore.svelte", () => ({
  toast: vi.fn(),
}));
vi.mock("$lib/i18n/t.svelte", () => ({
  t: (k: string) => k,
  tf: (k: string, params: Record<string, string>) =>
    k + ":" + (params.query ?? params.path ?? ""),
}));
vi.mock("$lib/stores/diagnosticsStore.svelte", () => ({
  diagEvent: vi.fn(),
}));
vi.mock("$lib/stores/projectStore.svelte", () => ({
  activateProject: vi.fn(),
  setSidebarMode: vi.fn(),
  projectState: { tabs: [tabA, tabB], activeId: "a" },
}));
vi.mock("$lib/stores/fileTreeStore.svelte", () => ({
  contextMenuTarget: { rootPath: "", rel: "" },
  // The path-walk must FAIL so the flow reaches the name search.
  ensureDirLoaded: vi.fn(async () => {}),
  revealInTree: vi.fn(async () => {}),
  toggleExpand: vi.fn(async () => {}),
  treeFor: () => ({ children: {}, expandedFolders: [] }),
}));
vi.mock("$lib/stores/tabsStore.svelte", () => ({
  openFile: vi.fn(),
}));
vi.mock("$lib/stores/settingsStore.svelte", () => ({
  settings: { fileTree: { showSystemGeneratedFolders: false } },
}));

import { searchProjectFiles } from "$lib/services/tauri";
import {
  closeLocate,
  locateState,
  openLocate,
  submitLocate,
} from "$lib/stores/locateStore.svelte";

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

interface SearchResultLike {
  matches: { rel: string; isDir: boolean }[];
  total: number;
  truncated: boolean;
}

const pending: {
  resolve: (v: SearchResultLike) => void;
  promise: Promise<SearchResultLike>;
}[] = [];

const searchMock = vi.mocked(searchProjectFiles);
searchMock.mockImplementation((() => {
  const d = deferred<SearchResultLike>();
  pending.push(d);
  return d.promise;
}) as never);

/** Let parked promises/microtasks settle up to the mocked search await. */
const flush = () => new Promise((r) => setTimeout(r, 0));

beforeEach(() => {
  pending.length = 0;
  openLocate();
});

describe("locateStore supersede (§七 D22)", () => {
  it("a second Enter during a flight SUPERSEDES it — stale results arrive unheard", async () => {
    const p1 = submitLocate("alpha");
    await flush();
    expect(locateState.searching).toBe(true);
    expect(searchMock).toHaveBeenCalledTimes(1);

    const p2 = submitLocate("beta");
    await flush();
    expect(searchMock).toHaveBeenCalledTimes(2); // NOT swallowed by a gate

    // The superseded flight resolves first with a single hit (which
    // would have jumped) — it must be discarded unheard.
    pending[0]!.resolve({
      matches: [{ rel: "x/alpha.md", isDir: false }],
      total: 1,
      truncated: false,
    });
    await p1;
    expect(locateState.results).toBeNull();
    expect(locateState.searching).toBe(true); // gen-2 still owns the flags

    pending[1]!.resolve({
      matches: [
        { rel: "y/beta-1.md", isDir: false },
        { rel: "y/beta-2.md", isDir: false },
      ],
      total: 2,
      truncated: false,
    });
    await p2;
    expect(locateState.results?.query).toBe("beta");
    expect(locateState.searching).toBe(false);
    expect(locateState.open).toBe(true); // multi-hit list stays up
  });

  it("closing the dialog cancels the flight — late results die quietly", async () => {
    const p = submitLocate("alpha");
    await flush();
    closeLocate();
    pending[0]!.resolve({
      matches: [{ rel: "x/alpha.md", isDir: false }],
      total: 1,
      truncated: false,
    });
    await p;
    expect(locateState.results).toBeNull();
    expect(locateState.open).toBe(false);
    expect(locateState.searching).toBe(false);
  });

  it("announces the sweep plan and counts finished tabs (§七 D23)", async () => {
    const p = submitLocate("alpha");
    await flush();
    // Current project (Alpha) answered: zero hits → sweep over Beta.
    pending[0]!.resolve({ matches: [], total: 0, truncated: false });
    await flush();
    expect(locateState.totalTabs).toBe(2);
    expect(locateState.searchedTabs).toBe(1);
    expect(locateState.searching).toBe(true);

    pending[1]!.resolve({
      matches: [{ rel: "deep/alpha.md", isDir: false }],
      total: 1,
      truncated: false,
    });
    await p;
    // Unique cross hit → landed (mocked), dialog closed, state reset.
    expect(locateState.open).toBe(false);
    expect(locateState.totalTabs).toBe(1);
    expect(locateState.searching).toBe(false);
  });
});
