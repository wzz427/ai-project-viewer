/**
 * Debounced state persistence loop (V1.5 §26, spec-004 D2/D3).
 *
 * Lives in a .svelte.ts module because the tracking relies on Svelte
 * runes: the $effect re-serializes whenever ANY field the snapshot reads
 * changes, so a new store field is picked up the moment it joins the
 * snapshot — no manual dirty flags to forget. 800ms sits mid-range of the
 * §26 recommendation. pagehide fires one last save; the Rust RunEvent::Exit
 * flush is the reliable layer when the WebView is already tearing down.
 */

import { buildAppState, type BuildInput } from "$lib/services/appState";
import { saveState } from "$lib/services/tauri";
import { projectState } from "$lib/stores/projectStore.svelte";
import { treeState } from "$lib/stores/fileTreeStore.svelte";
import { tabsState } from "$lib/stores/tabsStore.svelte";
import { settings } from "$lib/stores/settingsStore.svelte";

const SAVE_DEBOUNCE_MS = 800;
let saveTimer: ReturnType<typeof setTimeout> | undefined;
let latestJson = "";

function snapshotStores(): BuildInput {
  return {
    projects: projectState.tabs,
    activeProjectId: projectState.activeId,
    trees: Object.fromEntries(
      Object.entries(treeState.byRoot).map(([root, st]) => [
        root,
        {
          expandedFolders: st.expandedFolders,
          pinnedItems: st.pinnedItems,
          foldersFirst: st.foldersFirst,
        },
      ]),
    ),
    tabs: Object.fromEntries(
      Object.entries(tabsState.byRoot).map(([root, st]) => [
        root,
        {
          openFiles: st.openFiles,
          activeFileRelativePath: st.activeFileRelativePath,
        },
      ]),
    ),
    settings: {
      theme: settings.theme,
      viewer: { fontSize: settings.fontSize },
      fileTree: {
        showSystemGeneratedFolders:
          settings.fileTree.showSystemGeneratedFolders,
      },
      external: { vsCodeNewWindow: settings.external.vsCodeNewWindow },
    },
  };
}

function scheduleSave(json: string) {
  latestJson = json;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    void saveState(latestJson).catch((err) =>
      console.error("state save failed:", err),
    );
  }, SAVE_DEBOUNCE_MS);
}

export function startStateSync() {
  window.addEventListener("pagehide", () => {
    if (!latestJson) return;
    clearTimeout(saveTimer);
    void saveState(latestJson).catch(() => {});
  });

  $effect.root(() => {
    $effect(() => {
      scheduleSave(JSON.stringify(buildAppState(snapshotStores())));
    });
  });
}
