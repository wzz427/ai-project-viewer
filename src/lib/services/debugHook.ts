/**
 * Read-only live probe hook (owner 2026-10-12, freeze hunt): exposes
 * `window.__aiv.snapshot()` so scripts/e2e/live-inspect.py can attach to
 * the RUNNING app over CDP and read store/DOM/log state directly — the
 * next field freeze gets dissected on the spot instead of reconstructed
 * from exports. Snapshot returns fresh plain copies; there is no write
 * path through this hook.
 */
import { tabsState } from "$lib/stores/tabsStore.svelte";
import { projectState } from "$lib/stores/projectStore.svelte";
import { diagnostics } from "$lib/stores/diagnosticsStore.svelte";

interface AivDebug {
  snapshot: () => Record<string, unknown>;
}

export function installDebugHook(): void {
  const hook: AivDebug = {
    snapshot: () => {
      const tabs: Record<string, unknown> = {};
      for (const [root, st] of Object.entries(tabsState.byRoot)) {
        tabs[root] = {
          active: st.activeFileRelativePath,
          open: st.openFiles.map((t) => t.relativePath),
        };
      }
      return {
        when: new Date().toISOString(),
        activeProjectId: projectState.activeId,
        projects: projectState.tabs.map((p) => ({
          id: p.id,
          name: p.name,
          rootPath: p.rootPath,
          sidebarMode: p.sidebarMode,
        })),
        tabs,
        dom: {
          viewerRel:
            document
              .querySelector(".viewer-body [data-rel]")
              ?.getAttribute("data-rel") ?? null,
          activeTab:
            document.querySelector(".file-tab.active .name")?.textContent
            ?? null,
          tabStrip: [...document.querySelectorAll(".file-tab")].map((e) => {
            const name = e.querySelector(".name")?.textContent ?? "?";
            return name + (e.classList.contains("active") ? "*" : "");
          }),
        },
        log: diagnostics.log.slice(),
      };
    },
  };
  (window as unknown as Record<string, unknown>).__aiv = hook;
}
