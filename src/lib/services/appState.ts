/**
 * AppState serialization (V1.5 §17/§21/§22/§23, spec-004) — pure functions,
 * no store imports, so they are unit-testable without Svelte.
 *
 * Shape notes:
 * - version is explicit (§23); the Rust side already validated it, parsing
 *   here re-checks (defense in depth).
 * - Everything below the project root is PROJECT-RELATIVE (§18/§19);
 *   rootPath itself is the project identity and stays absolute.
 * - openFiles persist a whitelist of FileTabState (§21): encoding/cursor/
 *   deleted/unsupportedReason/sizeBytes are runtime-only. jsonMode/pinned
 *   ride along beyond §21's literal fields — they are §197 revision
 *   behaviors whose loss across restart would be user-visible (D7).
 */

import type { Theme } from "$lib/stores/settingsStore.svelte";
import type { SidebarMode } from "$lib/stores/projectStore.svelte";

export const STATE_VERSION = 1;

const VIEWER_TYPES = new Set([
  "markdown", "pdf", "text", "code", "json", "image", "binary", "unsupported",
]);
const SIDEBAR_MODES: SidebarMode[] = ["files", "git", "settings"];
const THEMES: Theme[] = ["system", "light", "dark"];

export interface PersistedTab {
  relativePath: string;
  viewerType: string;
  markdownMode?: "rendered" | "source";
  jsonMode?: "formatted" | "source";
  pinned?: boolean;
  scrollPosition?: number;
  /** §21 pdfState (spec-005 D6: rides the persistence whitelist). */
  pdfState?: {
    page: number;
    zoom: number;
    zoomMode?: "fit-width" | "fit-page" | "custom";
    scrollPosition?: number;
  };
}

export interface PersistedProject {
  id: string;
  name: string;
  rootPath: string;
  expandedFolders: string[];
  openFiles: PersistedTab[];
  activeFileRelativePath?: string;
  sidebarMode: SidebarMode;
  sidebarWidth: number;
  trustedForExecution: boolean;
  fileTreePreferences: {
    foldersFirst: boolean;
    pinnedItems: Record<string, string[]>;
  };
}

export interface PersistedSettings {
  theme: Theme;
  viewer: { fontSize: number };
  fileTree: { showSystemGeneratedFolders: boolean };
  /** Optional since spec-006 (§134); absent in older state files = true. */
  external?: { vsCodeNewWindow: boolean };
}

export interface AppStateV1 {
  version: typeof STATE_VERSION;
  projects: PersistedProject[];
  activeProjectId?: string;
  settings: PersistedSettings;
}

/** What buildAppState needs; structural subsets of the live stores. */
export interface TreeLike {
  expandedFolders: string[];
  pinnedItems: Record<string, string[]>;
  foldersFirst: boolean;
}

export interface TabsLike {
  openFiles: {
    relativePath: string;
    viewerType: string;
    markdownMode?: "rendered" | "source";
    jsonMode?: "formatted" | "source";
    pinned?: boolean;
    scrollPosition?: number;
    pdfState?: {
      page: number;
      zoom: number;
      zoomMode?: "fit-width" | "fit-page" | "custom";
      scrollPosition?: number;
    };
    deleted?: boolean;
  }[];
  activeFileRelativePath: string | null;
}

export interface BuildInput {
  projects: {
    id: string;
    name: string;
    rootPath: string;
    sidebarMode: SidebarMode;
    sidebarWidth: number;
  }[];
  activeProjectId: string | null;
  trees: Record<string, TreeLike>;
  tabs: Record<string, TabsLike>;
  settings: PersistedSettings;
}

/** Snapshots the app state for persistence. */
export function buildAppState(input: BuildInput): AppStateV1 {
  const projects: PersistedProject[] = input.projects.map((p) => {
    const tree = input.trees[p.rootPath];
    const tabs = input.tabs[p.rootPath];
    return {
      id: p.id,
      name: p.name,
      rootPath: p.rootPath,
      expandedFolders: [...(tree?.expandedFolders ?? [])],
      openFiles: (tabs?.openFiles ?? []).map((t) => {
        const out: PersistedTab = { relativePath: t.relativePath, viewerType: t.viewerType };
        if (t.markdownMode) out.markdownMode = t.markdownMode;
        if (t.jsonMode) out.jsonMode = t.jsonMode;
        if (t.pinned) out.pinned = t.pinned;
        if (typeof t.scrollPosition === "number") out.scrollPosition = t.scrollPosition;
        if (t.pdfState) {
          out.pdfState = {
            page: t.pdfState.page,
            zoom: t.pdfState.zoom,
            ...(t.pdfState.zoomMode ? { zoomMode: t.pdfState.zoomMode } : {}),
            ...(typeof t.pdfState.scrollPosition === "number"
              ? { scrollPosition: t.pdfState.scrollPosition }
              : {}),
          };
        }
        return out;
      }),
      activeFileRelativePath: tabs?.activeFileRelativePath ?? undefined,
      sidebarMode: p.sidebarMode,
      sidebarWidth: p.sidebarWidth,
      // Phase 8 owns the trust flow; the field ships now (§17) at default.
      trustedForExecution: false,
      fileTreePreferences: {
        foldersFirst: tree?.foldersFirst ?? true,
        pinnedItems: Object.fromEntries(
          Object.entries(tree?.pinnedItems ?? {}).map(([k, v]) => [k, [...v]]),
        ),
      },
    };
  });
  const state: AppStateV1 = {
    version: STATE_VERSION,
    projects,
    settings: structuredClone(input.settings),
  };
  if (input.activeProjectId) state.activeProjectId = input.activeProjectId;
  return state;
}

// --- Parsing with self-healing (bad fields fall back, bad tabs drop) ---

function asString(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}

function asBool(v: unknown, fallback: boolean): boolean {
  return typeof v === "boolean" ? v : fallback;
}

function asNum(v: unknown, fallback: number): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

function asStrArray(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

function parseTab(v: unknown): PersistedTab | null {
  if (typeof v !== "object" || v === null) return null;
  const t = v as Record<string, unknown>;
  const relativePath = asString(t.relativePath);
  const viewerType = asString(t.viewerType);
  if (!relativePath || !VIEWER_TYPES.has(viewerType)) return null;
  const out: PersistedTab = { relativePath, viewerType };
  if (t.markdownMode === "rendered" || t.markdownMode === "source") {
    out.markdownMode = t.markdownMode;
  }
  if (t.jsonMode === "formatted" || t.jsonMode === "source") {
    out.jsonMode = t.jsonMode;
  }
  if (typeof t.pinned === "boolean") out.pinned = t.pinned;
  if (typeof t.scrollPosition === "number" && Number.isFinite(t.scrollPosition)) {
    out.scrollPosition = t.scrollPosition;
  }
  const ps = t.pdfState;
  if (typeof ps === "object" && ps !== null) {
    const p = ps as Record<string, unknown>;
    const page = Math.max(1, Math.round(asNum(p.page, 1)));
    const zoom = Math.min(5, Math.max(0.1, asNum(p.zoom, 1)));
    const healed: NonNullable<PersistedTab["pdfState"]> = { page, zoom };
    if (p.zoomMode === "fit-width" || p.zoomMode === "fit-page" || p.zoomMode === "custom") {
      healed.zoomMode = p.zoomMode;
    }
    if (typeof p.scrollPosition === "number" && Number.isFinite(p.scrollPosition)) {
      healed.scrollPosition = p.scrollPosition;
    }
    out.pdfState = healed;
  }
  return out;
}

function parseProject(v: unknown): PersistedProject | null {
  if (typeof v !== "object" || v === null) return null;
  const p = v as Record<string, unknown>;
  const id = asString(p.id);
  const rootPath = asString(p.rootPath);
  if (!id || !rootPath) return null;
  const prefsRaw = p.fileTreePreferences;
  const prefs =
    typeof prefsRaw === "object" && prefsRaw !== null
      ? (prefsRaw as Record<string, unknown>)
      : {};
  const pinnedItems: Record<string, string[]> = {};
  if (typeof prefs.pinnedItems === "object" && prefs.pinnedItems !== null) {
    for (const [k, val] of Object.entries(prefs.pinnedItems as Record<string, unknown>)) {
      const list = asStrArray(val);
      if (list.length > 0) pinnedItems[k] = list;
    }
  }
  const sidebarModeRaw = asString(p.sidebarMode, "files");
  const sidebarMode = SIDEBAR_MODES.includes(sidebarModeRaw as SidebarMode)
    ? (sidebarModeRaw as SidebarMode)
    : "files";
  return {
    id,
    name: asString(p.name, rootPath),
    rootPath,
    expandedFolders: asStrArray(p.expandedFolders),
    openFiles: Array.isArray(p.openFiles)
      ? p.openFiles.map(parseTab).filter((t): t is PersistedTab => t !== null)
      : [],
    activeFileRelativePath: asString(p.activeFileRelativePath) || undefined,
    sidebarMode,
    sidebarWidth: Math.min(600, Math.max(180, asNum(p.sidebarWidth, 260))),
    trustedForExecution: asBool(p.trustedForExecution, false),
    fileTreePreferences: {
      foldersFirst: asBool(prefs.foldersFirst, true),
      pinnedItems,
    },
  };
}

function parseSettings(v: unknown): PersistedSettings {
  const s =
    typeof v === "object" && v !== null ? (v as Record<string, unknown>) : {};
  const viewer =
    typeof s.viewer === "object" && s.viewer !== null
      ? (s.viewer as Record<string, unknown>)
      : {};
  const fileTree =
    typeof s.fileTree === "object" && s.fileTree !== null
      ? (s.fileTree as Record<string, unknown>)
      : {};
  const external =
    typeof s.external === "object" && s.external !== null
      ? (s.external as Record<string, unknown>)
      : {};
  const themeRaw = asString(s.theme, "system");
  return {
    theme: THEMES.includes(themeRaw as Theme) ? (themeRaw as Theme) : "system",
    viewer: { fontSize: Math.min(20, Math.max(11, asNum(viewer.fontSize, 13))) },
    fileTree: {
      showSystemGeneratedFolders: asBool(fileTree.showSystemGeneratedFolders, false),
    },
    external: {
      vsCodeNewWindow: asBool(external.vsCodeNewWindow, true),
    },
  };
}

/**
 * Parses state JSON saved by a previous run. Returns null when the payload
 * is unusable (not JSON, wrong version) — the caller then starts fresh;
 * individually malformed pieces heal to defaults instead of failing load.
 */
export function parseAppState(json: string): AppStateV1 | null {
  let raw: unknown;
  try {
    raw = JSON.parse(json);
  } catch {
    return null;
  }
  if (typeof raw !== "object" || raw === null) return null;
  const v = raw as Record<string, unknown>;
  if (v.version !== STATE_VERSION) return null;
  const state: AppStateV1 = {
    version: STATE_VERSION,
    projects: Array.isArray(v.projects)
      ? v.projects.map(parseProject).filter((p): p is PersistedProject => p !== null)
      : [],
    settings: parseSettings(v.settings),
  };
  const active = asString(v.activeProjectId);
  if (active) state.activeProjectId = active;
  return state;
}
