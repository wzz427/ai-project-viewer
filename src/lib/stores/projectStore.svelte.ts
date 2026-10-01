import { open } from "@tauri-apps/plugin-dialog";
import { resolveProject } from "$lib/services/tauri";
import { toast } from "$lib/stores/toastStore.svelte";
import { forgetTree } from "$lib/stores/fileTreeStore.svelte";
import { forgetTabs } from "$lib/stores/tabsStore.svelte";

/** §17: "files" | "git"; "settings" is the third state since the §30
 *  revision made ⚙ a sidebar entry (spec-004 D6). */
export type SidebarMode = "files" | "git" | "settings";

export interface ProjectTab {
  id: string;
  name: string;
  /** Canonical absolute path — the project identity for dedup (V1.5 §14). */
  rootPath: string;
  /** §17 ProjectSession.sidebarMode — restored per project. */
  sidebarMode: SidebarMode;
  /** §17 ProjectSession.sidebarWidth — persisted; no drag UI yet (D6). */
  sidebarWidth: number;
}

/**
 * Projects live in projectState; session persistence (AppState) lands with
 * Phase 4 in services/appState.ts + services/sessionRestore — this store
 * keeps only the tab identities and per-project shell fields.
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

export function setSidebarMode(rootPath: string, mode: SidebarMode) {
  const tab = projectState.tabs.find((t) => t.rootPath === rootPath);
  if (tab) tab.sidebarMode = mode;
}

/** Drag-resize write (owner 2026-10-01); clamped to the same 200–600 range
 *  the state parser enforces, and picked up by the debounced save loop. */
export function setSidebarWidth(rootPath: string, width: number) {
  const tab = projectState.tabs.find((t) => t.rootPath === rootPath);
  if (tab) tab.sidebarWidth = Math.min(600, Math.max(200, Math.round(width)));
}

/** Add (or switch to) a project by raw path — shared by picker and test hook. */
export async function addProjectFromPath(rawPath: string) {
  try {
    const resolved = await resolveProject(rawPath);

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
      sidebarMode: "files",
      sidebarWidth: 260,
    };
    projectState.tabs.push(tab);
    projectState.activeId = tab.id;
  } catch (err) {
    toast(`Cannot open folder: ${err}`, { kind: "error" });
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
  await addProjectFromPath(picked);
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
