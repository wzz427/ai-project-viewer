/**
 * Session restore orchestration (V1.5 §178, spec-004).
 *
 * Runs once at startup, before the app mounts: adopt settings, re-validate
 * each persisted project (a moved/deleted project is skipped silently,
 * D9 — §188 leaves this open and self-healing beats a dead tab), rebuild
 * tree/tabs state from project-relative identities, and re-list exactly
 * the levels that were expanded last time (§27/§160.1: never deeper).
 */

import { loadState, resolveProject } from "$lib/services/tauri";
import { parseAppState, type PersistedProject } from "$lib/services/appState";
import { settings } from "$lib/stores/settingsStore.svelte";
import { projectState, type ProjectTab } from "$lib/stores/projectStore.svelte";
import {
  restoreExpandedFolders,
  restoreTreeState,
} from "$lib/stores/fileTreeStore.svelte";
import { restoreTabs } from "$lib/stores/tabsStore.svelte";
import type { ViewerType } from "$lib/services/viewerType";

export async function restoreAppState(): Promise<void> {
  const json = await loadState().catch(() => null);
  if (!json) return;
  const state = parseAppState(json);
  if (!state) return;

  settings.theme = state.settings.theme;
  settings.fontSize = state.settings.viewer.fontSize;
  settings.fileTree.showSystemGeneratedFolders =
    state.settings.fileTree.showSystemGeneratedFolders;
  settings.external.vsCodeNewWindow =
    state.settings.external?.vsCodeNewWindow ?? true;

  for (const persisted of state.projects) {
    const tab = await restoreProject(persisted);
    if (!tab) continue;
    restoreTreeState(tab.rootPath, persisted.fileTreePreferences);
    restoreTabs(
      tab.rootPath,
      persisted.openFiles.map((f) => ({
        ...f,
        viewerType: f.viewerType as ViewerType,
      })),
      persisted.activeFileRelativePath ?? null,
    );
    // One listing per previously-expanded level; the root listing is the
    // FileTree component's own $effect (loadRoot).
    await restoreExpandedFolders(tab.rootPath, persisted.expandedFolders);
  }

  if (
    state.activeProjectId &&
    projectState.tabs.some((t) => t.id === state.activeProjectId)
  ) {
    projectState.activeId = state.activeProjectId;
  } else if (projectState.tabs.length > 0) {
    projectState.activeId = projectState.tabs[projectState.tabs.length - 1].id;
  }
}

/** Re-resolve the persisted root (canonicalize may have changed after a
 *  move); null = project no longer on disk, skip it (D9). */
async function restoreProject(p: PersistedProject): Promise<ProjectTab | null> {
  try {
    const resolved = await resolveProject(p.rootPath);
    const tab: ProjectTab = {
      id: p.id,
      name: resolved.name,
      rootPath: resolved.rootPath,
      sidebarMode: p.sidebarMode,
      sidebarWidth: p.sidebarWidth,
    };
    projectState.tabs.push(tab);
    return tab;
  } catch {
    return null;
  }
}
