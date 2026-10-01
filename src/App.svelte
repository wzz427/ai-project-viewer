<script lang="ts">
  import { onMount } from "svelte";
  import ProjectTabs from "$lib/components/ProjectTabs/ProjectTabs.svelte";
  import SidebarHeader from "$lib/components/SidebarHeader/SidebarHeader.svelte";
  import FilesPanel from "$lib/components/SidebarPanels/FilesPanel.svelte";
  import GitPanel from "$lib/components/SidebarPanels/GitPanel.svelte";
  import SettingsPanel from "$lib/components/SidebarPanels/SettingsPanel.svelte";
  import EmptyState from "$lib/components/EmptyState/EmptyState.svelte";
  import ToastHost from "$lib/components/Toast/ToastHost.svelte";
  import { initTheme } from "$lib/stores/settingsStore.svelte";
  import { recordStartup } from "$lib/stores/diagnosticsStore.svelte";
  import { projectState, activeProject } from "$lib/stores/projectStore.svelte";
  import { toast } from "$lib/stores/toastStore.svelte";
  import {
    installShortcutDispatcher,
    onShortcut,
  } from "$lib/services/shortcuts";
  import { startupElapsedMs } from "$lib/services/tauri";
  import FileTabs from "$lib/components/ProjectTabs/FileTabs.svelte";
  import ActiveViewer from "$lib/components/Viewers/ActiveViewer.svelte";
  import {
    activeTab,
    closeFile,
    cycleTab,
    refreshActiveFile,
  } from "$lib/stores/tabsStore.svelte";
  import { refreshProject } from "$lib/stores/fileTreeStore.svelte";
  import { tabsState } from "$lib/stores/tabsStore.svelte";

  function tabsOf(rootPath: string) {
    return tabsState.byRoot[rootPath]?.openFiles ?? [];
  }
  import { openSearchPanel } from "@codemirror/search";
  import { getActiveSearchView } from "$lib/components/Viewers/codeSearchRegistry";

  type SidebarMode = "files" | "git" | "settings";

  let sidebarMode = $state<SidebarMode>("files");

  const project = $derived(activeProject());

  // Real P0 behaviors (V1.5 §146/§147). The dispatcher claims the keydown at
  // capture phase, so these run instead of any browser default — Ctrl+R must
  // refresh the project, never reload the WebView (formal acceptance item).
  function wireShortcuts() {
    const unsubs = [
      onShortcut("ctrl+w", () => {
        const root = project?.rootPath;
        const tab = root ? activeTab(root) : undefined;
        if (root && tab) closeFile(root, tab.relativePath);
      }),
      onShortcut("ctrl+f", () => {
        const view = getActiveSearchView();
        if (view) openSearchPanel(view);
      }),
      onShortcut("ctrl+tab", () => {
        if (project) cycleTab(project.rootPath, 1);
      }),
      onShortcut("ctrl+shift+tab", () => {
        if (project) cycleTab(project.rootPath, -1);
      }),
      onShortcut("ctrl+r", () => {
        if (!project) return;
        void refreshProject(project.rootPath);
        void refreshActiveFile(project.rootPath);
      }),
    ];
    return () => unsubs.forEach((u) => u());
  }

  onMount(() => {
    initTheme();
    installShortcutDispatcher();
    const unwire = wireShortcuts();

    startupElapsedMs().then(recordStartup).catch(() => {});

    return () => unwire();
  });
</script>

<div class="shell">
  <ProjectTabs />
  <div class="body">
    <aside class="sidebar">
      <SidebarHeader mode={sidebarMode} onModeChange={(m) => (sidebarMode = m)} />
      <div class="sidebar-panel">
        {#if sidebarMode === "files"}
          <FilesPanel />
        {:else if sidebarMode === "git"}
          <GitPanel />
        {:else}
          <SettingsPanel />
        {/if}
      </div>
    </aside>
    <main class="viewer">
      {#if projectState.tabs.length === 0}
        <EmptyState />
      {:else if project}
        <div class="viewer-stack">
          <FileTabs rootPath={project.rootPath} />
          {#if tabsOf(project.rootPath).length > 0}
            <div class="viewer-body">
              <ActiveViewer rootPath={project.rootPath} />
            </div>
          {:else}
            <div class="viewer-placeholder">
              <div class="placeholder-card">
                <h2>{project.name}</h2>
                <p class="mono muted">{project.rootPath}</p>
                <p class="muted">Open a file from the tree to view it.</p>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </main>
  </div>
  <ToastHost />
</div>

<style>
  .shell {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .body {
    flex: 1;
    display: flex;
    min-height: 0;
  }

  .sidebar {
    width: 260px;
    min-width: 200px;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border);
    background: var(--bg-raised);
  }

  .sidebar-panel {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    min-height: 0;
  }

  .viewer {
    flex: 1;
    min-width: 0;
    background: var(--bg);
  }

  .viewer-stack {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .viewer-body {
    flex: 1;
    min-height: 0;
  }

  .viewer-placeholder {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .placeholder-card {
    text-align: center;
    padding: 24px 32px;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
  }

  .placeholder-card h2 {
    margin: 0 0 8px;
    font-size: 15px;
  }

  .placeholder-card p {
    margin: 4px 0;
  }
</style>
