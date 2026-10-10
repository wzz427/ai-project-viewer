/**
 * Per-project file tabs (V1.5 §21 FileTabState + §46 tab layer).
 * In-memory until Phase 4; identities are project-relative paths (§18).
 *
 * Content cache is runtime-only (not part of the session shape): viewers
 * re-read through it on tab switch; Ctrl+R invalidates it (§82 manual slice
 * until the Phase 9 watcher).
 */

import { ask } from "@tauri-apps/plugin-dialog";
import { SvelteMap } from "svelte/reactivity";
import {
  inspectFile,
  readBinaryFile,
  readMediaFile,
  readTextFile,
  type FileEncoding,
} from "$lib/services/tauri";
import {
  fileNameOf,
  isImageName,
  isPdfName,
  viewerTypeFor,
  type ViewerType,
} from "$lib/services/viewerType";
import { toast } from "$lib/stores/toastStore.svelte";
import { revealInTree } from "$lib/stores/fileTreeStore.svelte";
import { closeDiff } from "$lib/stores/gitStore.svelte";

export type MarkdownMode = "rendered" | "source";

/** §21 FileTabState.pdfState (+ zoomMode extension, spec-005 D6 family:
 *  fit modes must survive a tab switch, not just the numeric zoom). */
export interface PdfState {
  page: number;
  zoom: number;
  zoomMode: "fit-width" | "fit-page" | "custom";
  scrollPosition?: number;
}

/** §21 FileTabState (+ runtime-only fields marked below). */
export interface RuntimeTab {
  relativePath: string;
  viewerType: ViewerType;
  markdownMode?: MarkdownMode;
  /** runtime-only: JSON viewer formatted/source toggle. */
  jsonMode?: "formatted" | "source";
  /** runtime-only: last scroll offset for restore (§160.5 unmount). */
  scrollPosition?: number;
  cursorLine?: number;
  encoding?: FileEncoding;
  pdfState?: PdfState;
  /** runtime-only: file vanished from disk (§83). */
  deleted?: boolean;
  /** runtime-only: pinned tabs are never replaced; while any tab is pinned,
   *  new files recycle an unpinned slot (owner 2026-10-01 item 8). */
  pinned?: boolean;
  /** runtime-only: why "unsupported" (binary guard verdict etc.). */
  unsupportedReason?: "binary" | "huge";
  sizeBytes?: number;
}

interface ProjectTabs {
  openFiles: RuntimeTab[];
  activeFileRelativePath: string | null;
}

export const tabsState = $state({
  byRoot: {} as Record<string, ProjectTabs>,
});

type Cached =
  | { kind: "text"; text: string; encoding: FileEncoding }
  | { kind: "media"; dataUrl: string }
  | { kind: "pdf"; data: ArrayBuffer };

// SvelteMap, NOT $state(new Map()): the $state deep proxy only wraps plain
// objects and arrays (svelte proxy.js returns other prototypes as-is), so
// a raw Map has no reactivity — writes would never re-run the viewers'
// content derivations (spec-004: restored tabs stuck on "Loading…" until
// this was switched to the official reactive container).
const contentCache = new SvelteMap<string, Cached>();

function projectTabs(rootPath: string): ProjectTabs {
  let st = tabsState.byRoot[rootPath];
  if (!st) {
    st = { openFiles: [], activeFileRelativePath: null };
    tabsState.byRoot[rootPath] = st;
  }
  return st;
}

function cacheKey(rootPath: string, rel: string) {
  return `${rootPath}\n${rel}`;
}

export function cachedContent(
  rootPath: string,
  rel: string,
): Cached | undefined {
  return contentCache.get(cacheKey(rootPath, rel));
}

/** The project's active file (relative path) — the tree highlight's
 * single source (owner 2026-10-10: tree/tab highlights had drifted). */
export function activeRelOf(rootPath: string): string | null {
  return tabsState.byRoot[rootPath]?.activeFileRelativePath ?? null;
}

export function activeTab(rootPath: string): RuntimeTab | undefined {
  const st = tabsState.byRoot[rootPath];
  if (!st?.activeFileRelativePath) return undefined;
  return st.openFiles.find(
    (t) => t.relativePath === st.activeFileRelativePath,
  );
}

function addOrActivate(rootPath: string, tab: RuntimeTab) {
  const st = projectTabs(rootPath);
  // A real file becoming the content closes the single-slot diff view
  // (spec-007 D3): the viewer body shows one thing at a time.
  closeDiff();
  const existing = st.openFiles.find(
    (t) => t.relativePath === tab.relativePath,
  );
  if (existing) {
    // Re-open keeps position and per-tab state, refreshes the verdicts.
    Object.assign(existing, tab, {
      markdownMode: existing.markdownMode ?? tab.markdownMode,
      jsonMode: existing.jsonMode ?? tab.jsonMode,
      scrollPosition: existing.scrollPosition,
      pinned: existing.pinned,
    });
    st.activeFileRelativePath = tab.relativePath;
    void revealInTree(rootPath, tab.relativePath);
    return;
  }
  // Pin model (owner 2026-10-01, clarified same day): with NOTHING pinned,
  // tabs accumulate normally — no preview concept, no surprise replacement.
  // Once at least one tab is pinned, new files RECYCLE an unpinned slot:
  // the active tab if unpinned, else the last unpinned one; only when every
  // tab is pinned does a new tab open.
  const activeIdx = st.openFiles.findIndex(
    (t) => t.relativePath === st.activeFileRelativePath,
  );
  const active = activeIdx === -1 ? undefined : st.openFiles[activeIdx];
  const anyPinned = st.openFiles.some((t) => t.pinned);
  let target = -1;
  if (anyPinned) {
    if (active && !active.pinned) {
      target = activeIdx;
    } else {
      for (let i = st.openFiles.length - 1; i >= 0; i--) {
        if (!st.openFiles[i].pinned) {
          target = i;
          break;
        }
      }
    }
  }
  if (target !== -1) {
    contentCache.delete(cacheKey(rootPath, st.openFiles[target].relativePath));
    st.openFiles.splice(target, 1, tab);
  } else {
    st.openFiles.push(tab);
  }
  st.activeFileRelativePath = tab.relativePath;
  void revealInTree(rootPath, tab.relativePath);
}

/** View-mode writes go through the store, never through component props —
 *  a prop reference stopped being live once its menu/viewer unmounted
 *  (owner round 2026-10-01: the first mode-toggle click was silently lost). */
export function setMarkdownMode(
  rootPath: string,
  rel: string,
  mode: MarkdownMode,
) {
  const tab = projectTabs(rootPath).openFiles.find(
    (t) => t.relativePath === rel,
  );
  if (tab) tab.markdownMode = mode;
}

export function setJsonMode(
  rootPath: string,
  rel: string,
  mode: "formatted" | "source",
) {
  const tab = projectTabs(rootPath).openFiles.find(
    (t) => t.relativePath === rel,
  );
  if (tab) tab.jsonMode = mode;
}

/** Persist scroll offsets from unmounting viewers (§160.5 restore). */
export function saveScrollPosition(
  rootPath: string,
  rel: string,
  scrollTop: number,
) {
  const tab = projectTabs(rootPath).openFiles.find(
    (t) => t.relativePath === rel,
  );
  if (tab) tab.scrollPosition = scrollTop;
}

/** Persist PDF view state (§93 page/zoom/scroll; spec-005). */
export function savePdfState(
  rootPath: string,
  rel: string,
  state: PdfState,
) {
  const tab = projectTabs(rootPath).openFiles.find(
    (t) => t.relativePath === rel,
  );
  if (tab) tab.pdfState = state;
}

/** Right-click "Keep Open" — stops this tab from being replaced (item 8). */
export function setTabPinned(rootPath: string, rel: string, pinned: boolean) {
  const tab = projectTabs(rootPath).openFiles.find(
    (t) => t.relativePath === rel,
  );
  if (tab) tab.pinned = pinned;
}

/** Drop landed in the empty band after the last tab -> append at end
 *  (owner gesture "拖到最右侧", 2026-10-01: the band swallowed drops). */
export function moveTabToEnd(rootPath: string, rel: string) {
  const st = projectTabs(rootPath);
  const idx = st.openFiles.findIndex((t) => t.relativePath === rel);
  if (idx === -1 || idx === st.openFiles.length - 1) return;
  const [moved] = st.openFiles.splice(idx, 1);
  st.openFiles.push(moved);
}

/**
 * Drag-reorder tabs (owner 2026-10-01 item 9). Cursor-half semantics:
 * before/after the target — without "after" the last slot is unreachable
 * (same bug family as the pinned-row drag, lessons L10 addendum).
 */
export function reorderTabs(
  rootPath: string,
  fromRel: string,
  toRel: string,
  position: "before" | "after" = "before",
) {
  const st = projectTabs(rootPath);
  const from = st.openFiles.findIndex((t) => t.relativePath === fromRel);
  const to = st.openFiles.findIndex((t) => t.relativePath === toRel);
  if (from === -1 || to === -1 || from === to) return;
  const [moved] = st.openFiles.splice(from, 1);
  const anchor = st.openFiles.findIndex((t) => t.relativePath === toRel);
  st.openFiles.splice(position === "before" ? anchor : anchor + 1, 0, moved);
}

export function activateFile(rootPath: string, rel: string) {
  const st = projectTabs(rootPath);
  if (st.openFiles.some((t) => t.relativePath === rel)) {
    closeDiff();
    st.activeFileRelativePath = rel;
    void revealInTree(rootPath, rel);
    void recheckDeleted(rootPath, rel);
  }
}

export function closeFile(rootPath: string, rel: string) {
  const st = projectTabs(rootPath);
  const idx = st.openFiles.findIndex((t) => t.relativePath === rel);
  if (idx === -1) return;
  st.openFiles.splice(idx, 1);
  contentCache.delete(cacheKey(rootPath, rel));
  if (st.activeFileRelativePath === rel) {
    const next = st.openFiles[Math.min(idx, st.openFiles.length - 1)];
    st.activeFileRelativePath = next ? next.relativePath : null;
  }
}

export function cycleTab(rootPath: string, direction: 1 | -1) {
  const st = projectTabs(rootPath);
  if (st.openFiles.length < 2) return;
  const idx = st.openFiles.findIndex(
    (t) => t.relativePath === st.activeFileRelativePath,
  );
  const next =
    st.openFiles[(idx + direction + st.openFiles.length) % st.openFiles.length];
  closeDiff();
  st.activeFileRelativePath = next.relativePath;
  void revealInTree(rootPath, next.relativePath);
}

/** §83 detection point: tab activation and Ctrl+R (spec-003 D5). */
async function recheckDeleted(rootPath: string, rel: string) {
  try {
    await inspectFile(rootPath, rel);
    const tab = projectTabs(rootPath).openFiles.find(
      (t) => t.relativePath === rel,
    );
    if (tab) tab.deleted = false;
  } catch {
    const tab = projectTabs(rootPath).openFiles.find(
      (t) => t.relativePath === rel,
    );
    if (tab) tab.deleted = true;
  }
}

/**
 * Open a file from the tree through the §101 pipeline (spec-003 R3):
 * binary → binary placeholder; >20 MB → huge placeholder; 5–20 MB text →
 * confirm dialog first (§106); images ride the media channel.
 */
export async function openFile(rootPath: string, rel: string) {
  let info;
  try {
    info = await inspectFile(rootPath, rel);
  } catch (err) {
    toast(`Cannot open file: ${err}`, { kind: "error" });
    return;
  }

  // Routing order matters (owner 2026-10-01 item 10 + spec-005 D4):
  // JPEG/PNG/GIF bytes legitimately contain NULLs and PDFs are binary by
  // design, so extension-based channels must be routed BEFORE the binary
  // verdict. PDFs skip the text-size dialogs entirely (§95 page pipeline).
  if (isPdfName(rel)) {
    try {
      const data = await readBinaryFile(rootPath, rel);
      contentCache.set(cacheKey(rootPath, rel), { kind: "pdf", data });
      addOrActivate(rootPath, {
        relativePath: rel,
        viewerType: "pdf",
        pdfState: { page: 1, zoom: 1, zoomMode: "fit-width" },
        sizeBytes: info.sizeBytes,
      });
    } catch (err) {
      toast(`Cannot open PDF: ${err}`, { kind: "error" });
    }
    return;
  }

  if (info.sizeClass === "huge") {
    addOrActivate(rootPath, {
      relativePath: rel,
      viewerType: "unsupported",
      unsupportedReason: "huge",
      sizeBytes: info.sizeBytes,
    });
    return;
  }

  if (isImageName(rel)) {
    try {
      const media = await readMediaFile(rootPath, rel);
      contentCache.set(cacheKey(rootPath, rel), {
        kind: "media",
        dataUrl: media.dataUrl,
      });
      addOrActivate(rootPath, {
        relativePath: rel,
        viewerType: "image",
        sizeBytes: info.sizeBytes,
      });
    } catch (err) {
      toast(`Cannot open image: ${err}`, { kind: "error" });
    }
    return;
  }

  if (info.isBinary) {
    addOrActivate(rootPath, {
      relativePath: rel,
      viewerType: "binary",
      unsupportedReason: "binary",
      sizeBytes: info.sizeBytes,
    });
    return;
  }

  if (info.sizeClass === "large") {
    const yes = await ask(
      `${fileNameOf(rel)} is ${(info.sizeBytes / 1048576).toFixed(1)} MB.\n\nOpening this file may affect performance.`,
      { title: "Large File", kind: "warning", okLabel: "Open Anyway", cancelLabel: "Cancel" },
    );
    if (!yes) return;
  }

  try {
    const content = await readTextFile(rootPath, rel);
    contentCache.set(cacheKey(rootPath, rel), {
      kind: "text",
      text: content.text,
      encoding: content.encoding,
    });
    addOrActivate(rootPath, {
      relativePath: rel,
      viewerType: viewerTypeFor(rel),
      markdownMode: "rendered",
      jsonMode: "formatted",
      encoding: content.encoding,
      sizeBytes: info.sizeBytes,
      scrollPosition: 0,
    });
  } catch (err) {
    toast(`Cannot open file: ${err}`, { kind: "error" });
  }
}

/** Ctrl+R slice (§82 manual): reload the active file, toast if it changed. */
export async function refreshActiveFile(rootPath: string) {
  const st = projectTabs(rootPath);
  const rel = st.activeFileRelativePath;
  if (!rel) return;
  const tab = st.openFiles.find((t) => t.relativePath === rel);
  if (!tab) return;

  let info;
  try {
    info = await inspectFile(rootPath, rel);
  } catch {
    tab.deleted = true;
    return;
  }
  tab.deleted = false;

  if (tab.viewerType === "image") {
    const media = await readMediaFile(rootPath, rel).catch(() => null);
    if (media) {
      contentCache.set(cacheKey(rootPath, rel), {
        kind: "media",
        dataUrl: media.dataUrl,
      });
    }
    return;
  }
  if (tab.viewerType === "binary" || tab.viewerType === "unsupported") return;

  const fresh = await readTextFile(rootPath, rel).catch(() => null);
  if (!fresh) return;
  const prev = contentCache.get(cacheKey(rootPath, rel));
  if (prev?.kind === "text" && prev.text !== fresh.text) {
    toast(`✓ ${fileNameOf(rel)} updated`);
  }
  contentCache.set(cacheKey(rootPath, rel), {
    kind: "text",
    text: fresh.text,
    encoding: fresh.encoding,
  });
  tab.encoding = fresh.encoding;
}

export function forgetTabs(rootPath: string) {
  for (const key of [...contentCache.keys()]) {
    if (key.startsWith(`${rootPath}\n`)) contentCache.delete(key);
  }
  delete tabsState.byRoot[rootPath];
}

/** Session restore (Phase 4): adopt persisted tabs — identities and modes
 *  only; content is read lazily when a viewer mounts (ensureContentLoaded). */
export function restoreTabs(
  rootPath: string,
  files: {
    relativePath: string;
    viewerType: ViewerType;
    markdownMode?: MarkdownMode;
    jsonMode?: "formatted" | "source";
    pinned?: boolean;
    scrollPosition?: number;
  }[],
  activeRel: string | null,
) {
  tabsState.byRoot[rootPath] = {
    openFiles: files.map((f) => ({ ...f })),
    activeFileRelativePath: activeRel,
  };
}

/**
 * Session-restore companion (spec-004 D4): a restored tab carries identity
 * and modes but no cached content — viewers call this on mount when the
 * cache is empty. Mirrors openFile's routing without dialogs: restoring is
 * automatic, so the 5–20MB confirmation (§106) does not re-apply, and
 * binary/unsupported verdicts from the previous run stand as-is.
 */
export async function ensureContentLoaded(rootPath: string, rel: string) {
  const tab = projectTabs(rootPath).openFiles.find(
    (t) => t.relativePath === rel,
  );
  if (!tab || tab.deleted) return;
  if (tab.viewerType === "binary" || tab.viewerType === "unsupported") return;
  if (contentCache.has(cacheKey(rootPath, rel))) return;

  if (tab.viewerType === "image") {
    const media = await readMediaFile(rootPath, rel).catch(() => null);
    if (media) {
      contentCache.set(cacheKey(rootPath, rel), {
        kind: "media",
        dataUrl: media.dataUrl,
      });
    } else {
      tab.deleted = true;
    }
    return;
  }

  if (tab.viewerType === "pdf") {
    const data = await readBinaryFile(rootPath, rel).catch(() => null);
    if (data) {
      contentCache.set(cacheKey(rootPath, rel), { kind: "pdf", data });
    } else {
      tab.deleted = true;
    }
    return;
  }

  const content = await readTextFile(rootPath, rel).catch(() => null);
  if (!content) {
    // Vanished since the last run — same deleted-state contract as §83.
    tab.deleted = true;
    return;
  }
  contentCache.set(cacheKey(rootPath, rel), {
    kind: "text",
    text: content.text,
    encoding: content.encoding,
  });
  tab.encoding = content.encoding;
}
