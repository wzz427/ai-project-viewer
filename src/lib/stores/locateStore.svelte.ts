/**
 * Locate dialog slot + orchestration (spec-017): paste a path,
 * jump to the project that owns it and reveal it in the tree.
 *
 * ZERO-RESIDENT (V1.5 §6): the slot is one boolean; the walk reads one
 * cached level at a time through the tree store's own cache and drops
 * everything — nothing persists, nothing outlives the dialog.
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
  matchProject,
  normalizeInput,
  resolveRel,
} from "$lib/services/locatePath";

export const locateState = $state({ open: false });

export function openLocate() {
  locateState.open = true;
}

export function closeLocate() {
  locateState.open = false;
}

/** Ctrl+L toggles (spec-017 D9) — same muscle memory as a browser bar. */
export function toggleLocate() {
  locateState.open = !locateState.open;
}

// A deep walk is a handful of fast one-level IPCs; still, Enter mashed
// twice must not fire two walks that race each other's reveals.
let inFlight = false;

async function listLevel(rootPath: string, relDir: string) {
  await ensureDirLoaded(rootPath, relDir);
  return treeFor(rootPath).children[relDir] ?? null;
}

export async function submitLocate(raw: string) {
  const input = normalizeInput(raw);
  if (!input || inFlight) return;
  inFlight = true;
  try {
    const rawPath = raw.trim();
    const match = matchProject(
      input,
      projectState.tabs,
      projectState.activeId,
    );
    if (!match) {
      toast(tf("toast.locateNotInProject", { path: rawPath }), {
        kind: "error",
      });
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
    if (!target) {
      toast(tf("toast.locateNotFound", { path: rawPath }), {
        kind: "error",
      });
      return;
    }
    activateProject(project.id);
    setSidebarMode(project.rootPath, "files");
    if (relSegments.length === 0) {
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
  } finally {
    inFlight = false;
    closeLocate();
  }
}
