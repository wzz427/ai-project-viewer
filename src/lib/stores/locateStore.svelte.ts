/**
 * Locate dialog slot + orchestration (spec-017): paste a path — or type
 * a file name — jump to the project that owns it and reveal it in the
 * tree.
 *
 * ZERO-RESIDENT (V1.5 §6): the slot is one boolean plus the transient
 * hit list of a name search; the walk reads one cached level at a time
 * through the tree store's own cache and drops everything — nothing
 * persists, nothing outlives the dialog.
 */

import { toast } from "$lib/stores/toastStore.svelte";
import { tf } from "$lib/i18n/t.svelte";
import { diagEvent } from "$lib/stores/diagnosticsStore.svelte";
import {
  activateProject,
  projectState,
  setSidebarMode,
} from "$lib/stores/projectStore.svelte";
import {
  contextMenuTarget,
  ensureDirLoaded,
  revealInTree,
  toggleExpand,
  treeFor,
} from "$lib/stores/fileTreeStore.svelte";
import { openFile } from "$lib/stores/tabsStore.svelte";
import { settings } from "$lib/stores/settingsStore.svelte";
import {
  pathsExist,
  searchProjectFiles,
} from "$lib/services/tauri";
import {
  matchProject,
  mergeProjectSearches,
  normalizeInput,
  resolveRel,
  searchFallbackQuery,
  type LocatedMatch,
  type ProjectLike,
  type SearchOrigin,
} from "$lib/services/locatePath";

/**
 * A name search that found SEVERAL candidates: the dialog stays open and
 * lists them, one click (or Enter) finishes the jump. Lives only while
 * the dialog is open — closing drops it.
 */
export interface LocateResults {
  /** The input that produced this list, trimmed — Enter on an unchanged
   *  input picks from the list instead of searching again. */
  query: string;
  matches: LocatedMatch[];
  total: number;
  truncated: boolean;
  /** Rows came from the zero-hit fallback over the OTHER open tabs —
   *  those rows say which project they live in (§六 D17). */
  crossProject: boolean;
}

export const locateState = $state<{
  open: boolean;
  /** A submit is in flight — the dialog shows its "Searching…" line for
   *  as long (§六 D20: the owner saw silence until the end-of-search
   *  toast). Transient with the dialog, not with the app. */
  searching: boolean;
  results: LocateResults | null;
}>({ open: false, searching: false, results: null });

/** Rows shown per search. More than a screenful means "type more", and
 *  the dialog says so instead of growing an endless list. */
const SEARCH_LIMIT = 50;

export function openLocate() {
  locateState.results = null;
  locateState.searching = false;
  locateState.open = true;
}

export function closeLocate() {
  locateState.open = false;
  locateState.results = null;
  locateState.searching = false;
}

/** Ctrl+L toggles (spec-017 D9) — same muscle memory as a browser bar. */
export function toggleLocate() {
  if (locateState.open) closeLocate();
  else openLocate();
}

// A deep walk is a handful of fast one-level IPCs; still, Enter mashed
// twice must not fire two walks that race each other's reveals.
let inFlight = false;

async function listLevel(rootPath: string, relDir: string) {
  await ensureDirLoaded(rootPath, relDir);
  return treeFor(rootPath).children[relDir] ?? null;
}

/**
 * Final step shared by a resolved path and a picked search hit: switch
 * to the owning project and reveal (+ open) the target.
 */
async function land(
  project: ProjectLike,
  target: { rel: string; isDir: boolean; hiddenSystem: boolean },
) {
  activateProject(project.id);
  setSidebarMode(project.rootPath, "files");
  if (target.rel === "") {
    diagEvent(`locate root ${project.rootPath}`);
    return; // the path WAS the project root: the switch is the whole job
  }
  if (target.hiddenSystem && !settings.fileTree.showSystemGeneratedFolders) {
    // Revealing would scroll to a row the tree refuses to render —
    // say why and where the switch lives instead of failing silently
    // (spec-017 D8: never flip the user's persisted setting as a side
    // effect).
    toast(tf("toast.locateHidden", { name: target.rel }), {
      kind: "error",
    });
    return;
  }
  if (target.isDir) {
    await revealInTree(project.rootPath, target.rel);
    const st = treeFor(project.rootPath);
    if (!st.expandedFolders.includes(target.rel)) {
      await toggleExpand(project.rootPath, target.rel);
    }
    // A folder can never become the ACTIVE TAB (highlight truth for
    // files), so the located row borrows the right-click "last acted
    // on" highlight — same one-source rule, cleared by the next file
    // activation exactly like a menu action.
    contextMenuTarget.rootPath = project.rootPath;
    contextMenuTarget.rel = target.rel;
    diagEvent(`locate dir ${target.rel} ${project.rootPath}`);
  } else {
    // Reveal FIRST so the tree moves even if openFile stops at the
    // 5–20 MB confirm dialog and the user cancels (spec-017 D2).
    await revealInTree(project.rootPath, target.rel);
    void openFile(project.rootPath, target.rel);
    diagEvent(`locate file ${target.rel} ${project.rootPath}`);
  }
}

export async function submitLocate(raw: string) {
  const input = normalizeInput(raw);
  if (!input || inFlight) return;
  inFlight = true;
  locateState.searching = true;
  // Only a multi-hit name search keeps the dialog up (its list needs a
  // click); every other outcome — jump or error toast — closes it.
  let keepOpen = false;
  try {
    const rawPath = raw.trim();
    const match = matchProject(
      input,
      projectState.tabs,
      projectState.activeId,
    );
    if (!match) {
      // Split the failure so the toast names the missing step (owner
      // 2026-11-08: "the message must say the folder isn't open yet and
      // has to be opened first"): a path that EXISTS on disk outside all
      // open projects gets the "open its folder first" instruction, a
      // path that doesn't exist anywhere gets plain not-found — sending
      // the user to open a folder for a typo'd path would be a wrong
      // errand. Relative inputs only reach here with NO project open at
      // all, where the same "open a folder first" wording is the truth.
      let onDisk = true;
      if (input.kind === "abs") {
        // Probe the CONTAINING FOLDER, not the file itself: paths_exist is
        // a directory check (Open Recent semantics — files read false),
        // and the message is about the folder anyway. Folder on disk but
        // no open project owns it → "open it first"; folder itself gone
        // → plain not-found. A bare drive root ("C:\") has no parent —
        // treat as on-disk (the actionable wording stays truthful).
        const parent = input.segments.slice(0, -1).join("\\");
        try {
          onDisk = parent === "" || (await pathsExist([parent]))[0] === true;
        } catch {
          onDisk = true; // check itself failed: keep the actionable wording
        }
      }
      toast(
        tf(onDisk ? "toast.locateNotInProject" : "toast.locateNotFound", {
          path: rawPath,
        }),
        { kind: "error" },
      );
      return;
    }
    const { project, relSegments } = match;
    // Prove the path BEFORE switching tabs — a dead input must not yank
    // the user to another project (spec-017 §一).
    const target =
      relSegments.length === 0
        ? { rel: "", isDir: true, hiddenSystem: false }
        : await resolveRel(relSegments, (dir) =>
            listLevel(project.rootPath, dir),
          );
    if (target) {
      await land(project, target);
      return;
    }
    // Not a path that walks from the root. A relative input is then a
    // NAME (or path fragment) to search for in this project — the owner's
    // 2026-11-10 report: typing `client-runtime-delivery-closeout.md`
    // found nothing until the whole docs/specs/designs/… path was typed,
    // because a bare name was only ever looked up in the project root.
    const query = searchFallbackQuery(input);
    if (query === null) {
      toast(tf("toast.locateNotFound", { path: rawPath }), {
        kind: "error",
      });
      return;
    }
    let found;
    try {
      found = await searchProjectFiles(
        project.rootPath,
        query,
        // Same visibility as the tree: a hit inside a hidden system
        // folder would reveal nowhere.
        settings.fileTree.showSystemGeneratedFolders,
        SEARCH_LIMIT,
      );
    } catch (e) {
      toast(String(e), { kind: "error" });
      return;
    }
    diagEvent(
      `locate search "${query}" hits=${found.total}${found.truncated ? "+" : ""} ${project.rootPath}`,
    );
    if (found.matches.length === 0) {
      // §六 D16: zero hits HERE is not the end — the file may live in
      // one of the OTHER open tabs (owner 2026-11-16: `docs/skills/
      // wrap.md` exists, but only in CodeAudit while QuantTrading was
      // active — and the old toast never said WHICH project had been
      // searched). Sweep the other tabs with the same visibility rules
      // and caps, keeping tab order (D17); a root that fails to read
      // (folder deleted under a still-open tab) is skipped, not fatal.
      const others = projectState.tabs.filter((t) => t.id !== project.id);
      const settled = await Promise.allSettled(
        others.map((t) =>
          searchProjectFiles(
            t.rootPath,
            query,
            settings.fileTree.showSystemGeneratedFolders,
            SEARCH_LIMIT,
          ),
        ),
      );
      const lists = settled.flatMap((s, i) => {
        if (s.status === "rejected") {
          diagEvent(
            `locate search failed ${others[i]?.rootPath}: ${String(s.reason)}`,
          );
          return [];
        }
        const tab = others[i]!;
        return [
          {
            origin: {
              id: tab.id,
              name: tab.name,
              rootPath: tab.rootPath,
            } satisfies SearchOrigin,
            result: s.value,
          },
        ];
      });
      const merged = mergeProjectSearches(lists, SEARCH_LIMIT);
      diagEvent(
        `locate cross "${query}" hits=${merged.total}${merged.truncated ? "+" : ""} tabs=${lists.length}/${others.length}`,
      );
      if (merged.matches.length === 0) {
        toast(tf("toast.locateNoMatch", { query: rawPath }), {
          kind: "error",
        });
        return;
      }
      if (merged.matches.length === 1) {
        // Unambiguous across all tabs — finish the jump (which switches
        // the tab) without making the user click a one-row list.
        const only = merged.matches[0]!;
        await land(only.project, {
          rel: only.rel,
          isDir: only.isDir,
          hiddenSystem: false,
        });
        return;
      }
      locateState.results = {
        query: rawPath,
        matches: merged.matches,
        total: merged.total,
        truncated: merged.truncated,
        crossProject: true,
      };
      keepOpen = true;
      return;
    }
    // In-project hits: same behavior as 0.8.28, rows merely tagged with
    // the active tab now so both list kinds share one row shape.
    const tab = projectState.tabs.find((t) => t.id === project.id);
    const activeOrigin: SearchOrigin = {
      id: project.id,
      name: tab?.name ?? project.id,
      rootPath: project.rootPath,
    };
    const tagged: LocatedMatch[] = found.matches.map((m) => ({
      ...m,
      project: activeOrigin,
    }));
    if (tagged.length === 1) {
      // Unambiguous — finish the jump without making the user click a
      // one-row list.
      const only = tagged[0]!;
      await land(project, { ...only, hiddenSystem: false });
      return;
    }
    locateState.results = {
      query: rawPath,
      matches: tagged,
      total: found.total,
      truncated: found.truncated,
      crossProject: false,
    };
    keepOpen = true;
  } finally {
    inFlight = false;
    locateState.searching = false;
    if (!keepOpen) closeLocate();
  }
}

/**
 * Finish a multi-hit search with the chosen row. The row carries its
 * owning tab and a true-case rel (Rust output — the same contract as
 * resolveRel's), so it lands directly; re-submitting the rel as a
 * RELATIVE PATH would resolve it against the ACTIVE project and land in
 * the wrong one (§六 D18).
 */
export async function pickLocateResult(row: LocatedMatch) {
  if (inFlight) return;
  inFlight = true;
  locateState.searching = true;
  try {
    await land(row.project, {
      rel: row.rel,
      isDir: row.isDir,
      hiddenSystem: false,
    });
  } finally {
    inFlight = false;
    locateState.searching = false;
    closeLocate();
  }
}
