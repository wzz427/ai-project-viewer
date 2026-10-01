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
    knownCombos,
  } from "$lib/services/shortcuts";
  import { startupElapsedMs } from "$lib/services/tauri";

  type SidebarMode = "files" | "git" | "settings";

  let sidebarMode = $state<SidebarMode>("files");

  const project = $derived(activeProject());

  onMount(() => {
    initTheme();
    installShortcutDispatcher();

    // Phase 1 placeholder handlers: prove interception; real behaviors arrive
    // with their features (V1.5 §177 — Phase 3 wires file-tab actions).
    const message: Record<string, string> = {
      "ctrl+w": "Ctrl+W — close file tab (file tabs arrive in Phase 3)",
      "ctrl+f": "Ctrl+F — find in viewer (viewers arrive in Phase 3)",
      "ctrl+tab": "Ctrl+Tab — next file tab (file tabs arrive in Phase 3)",
      "ctrl+shift+tab": "Ctrl+Shift+Tab — previous file tab (file tabs arrive in Phase 3)",
      "ctrl+r": "Ctrl+R — refresh active project (file tree arrives in Phase 2)",
    };
    const unsubscribers = knownCombos.map((combo) =>
      onShortcut(combo, () => toast(message[combo])),
    );

    startupElapsedMs().then(recordStartup).catch(() => {});

    return () => unsubscribers.forEach((u) => u());
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
        <div class="viewer-placeholder">
          <div class="placeholder-card">
            <h2>{project.name}</h2>
            <p class="mono muted">{project.rootPath}</p>
            <p class="muted">Viewers (Markdown, code, PDF, …) arrive in Phase 3.</p>
          </div>
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
