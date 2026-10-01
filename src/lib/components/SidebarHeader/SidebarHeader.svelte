<script lang="ts">
  import { activeProject } from "$lib/stores/projectStore.svelte";
  import FilesMenu from "$lib/components/FileTree/FilesMenu.svelte";

  let {
    mode,
    onModeChange,
  }: {
    mode: "files" | "git" | "settings";
    onModeChange: (mode: "files" | "git" | "settings") => void;
  } = $props();

  const project = $derived(activeProject());

  // V1.5 §30: the Files row carries the "⋯" menu (sort / visibility /
  // refresh). Only meaningful in Files mode with a project open.
  let filesMenu = $state<{ x: number; y: number } | null>(null);

  function openFilesMenu(e: MouseEvent) {
    if (!project) return;
    filesMenu = { x: e.clientX, y: e.clientY };
  }
</script>

<!-- V1.5 §8: Files / Git as sidebar header tabs; Settings is an entry, not a tab. -->
<div class="sidebar-header">
  <button
    class="header-tab"
    class:active={mode === "files"}
    onclick={() => onModeChange("files")}
  >
    Files
  </button>
  <button
    class="header-tab"
    class:active={mode === "git"}
    onclick={() => onModeChange("git")}
  >
    Git
  </button>
  <div class="spacer"></div>
  {#if mode === "files"}
    <button
      class="header-icon"
      onclick={openFilesMenu}
      disabled={!project}
      title="Files options"
      aria-label="Files options"
    >
      ⋯
    </button>
  {/if}
  <button
    class="header-icon settings"
    class:active={mode === "settings"}
    onclick={() => onModeChange("settings")}
    title="Settings"
    aria-label="Settings"
  >
    ⚙
  </button>
</div>

{#if filesMenu && project}
  <FilesMenu
    rootPath={project.rootPath}
    x={filesMenu.x}
    y={filesMenu.y}
    onclose={() => (filesMenu = null)}
  />
{/if}

<style>
  .sidebar-header {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 4px 6px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .header-tab {
    padding: 4px 10px;
    border-radius: var(--radius);
    color: var(--text-muted);
  }

  .header-tab:hover {
    background: var(--bg-hover);
  }

  .header-tab.active {
    background: var(--bg-active);
    color: var(--text);
  }

  .spacer {
    flex: 1;
  }

  .header-icon {
    padding: 4px 8px;
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 14px;
  }

  .header-icon:hover:not(:disabled) {
    background: var(--bg-hover);
  }

  .header-icon:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .settings.active {
    background: var(--bg-active);
    color: var(--text);
  }
</style>
