import { open } from "@tauri-apps/plugin-dialog";
import { resolveProject } from "$lib/services/tauri";
import { toast } from "$lib/stores/toastStore.svelte";
import { forgetTree } from "$lib/stores/fileTreeStore.svelte";
import { forgetTabs } from "$lib/stores/tabsStore.svelte";

export interface ProjectTab {
  id: string;
  name: string;
  /** Canonical absolute path — the project identity for dedup (V1.5 §14). */
  rootPath: string;
}

/**
 * Phase 1 keeps projects in memory only; persistence (AppState, session
 * restore) is Phase 4 scope (V1.5 §178).
 */
export const projectState = $state({
  tabs: [] as ProjectTab[],
  activeId: null as string | null,
});

export function activeProject(): ProjectTab | undefined {
  return projectState.tabs.find((t) => t.id === projectState.activeId);
}

export function activateProject(id: string) {
  if (projectState.tabs.some((t) => t.id === id)) {
    projectState.activeId = id;
  }
}

/** "+" flow: folder picker → canonicalize → dedup → add or switch (V1.5 §13/§14). */
export async function addProjectViaPicker() {
  let picked: string | null;
  try {
    picked = await open({
      directory: true,
      multiple: false,
      title: "Open Folder",
    });
  } catch (err) {
    toast(`Cannot open folder picker: ${err}`, { kind: "error" });
    return;
  }
  if (typeof picked !== "string" || picked.length === 0) return;

  try {
    const resolved = await resolveProject(picked);

    const existing = projectState.tabs.find((t) => t.rootPath === resolved.rootPath);
    if (existing) {
      projectState.activeId = existing.id;
      toast(`"${resolved.name}" is already open — switched to its tab.`);
      return;
    }

    const tab: ProjectTab = {
      id: crypto.randomUUID(),
      name: resolved.name,
      rootPath: resolved.rootPath,
    };
    projectState.tabs.push(tab);
    projectState.activeId = tab.id;
  } catch (err) {
    toast(`Cannot open folder: ${err}`, { kind: "error" });
  }
}

/** Remove from the viewer only — never touches the directory on disk (V1.5 §15). */
export function removeProject(id: string) {
  const idx = projectState.tabs.findIndex((t) => t.id === id);
  if (idx === -1) return;

  forgetTree(projectState.tabs[idx].rootPath);
  forgetTabs(projectState.tabs[idx].rootPath);
  projectState.tabs.splice(idx, 1);
  if (projectState.activeId === id) {
    const next = projectState.tabs[Math.min(idx, projectState.tabs.length - 1)];
    projectState.activeId = next ? next.id : null;
  }
}
