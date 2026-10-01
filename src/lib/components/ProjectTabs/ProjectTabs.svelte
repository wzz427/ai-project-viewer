<script lang="ts">
  import {
    projectState,
    activateProject,
    addProjectViaPicker,
    type ProjectTab,
  } from "$lib/stores/projectStore.svelte";
  import ProjectContextMenu from "$lib/components/ContextMenu/ProjectContextMenu.svelte";

  let menuFor = $state<ProjectTab | null>(null);
  let menuX = $state(0);
  let menuY = $state(0);

  function openMenu(tab: ProjectTab, e: MouseEvent) {
    e.preventDefault();
    menuFor = tab;
    menuX = e.clientX;
    menuY = e.clientY;
  }
</script>

<div class="project-tabs" role="presentation">
  {#each projectState.tabs as tab (tab.id)}
    <button
      class="tab"
      class:active={tab.id === projectState.activeId}
      onclick={() => activateProject(tab.id)}
      oncontextmenu={(e) => openMenu(tab, e)}
      title={tab.rootPath}
    >
      {tab.name}
    </button>
  {/each}
  <button class="add" onclick={() => addProjectViaPicker()} title="Add project" aria-label="Add project">
    +
  </button>
</div>

{#if menuFor}
  <ProjectContextMenu
    project={menuFor}
    x={menuX}
    y={menuY}
    onclose={() => (menuFor = null)}
  />
{/if}

<style>
  .project-tabs {
    display: flex;
    align-items: stretch;
    height: 36px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-raised);
    overflow-x: auto;
    flex-shrink: 0;
  }

  .tab {
    padding: 0 14px;
    border-right: 1px solid var(--border);
    color: var(--text-muted);
    white-space: nowrap;
  }

  .tab:hover {
    background: var(--bg-hover);
  }

  .tab.active {
    background: var(--bg-active);
    color: var(--text);
    box-shadow: inset 0 -2px 0 var(--accent);
  }

  .add {
    padding: 0 14px;
    font-size: 16px;
    color: var(--text-muted);
  }

  .add:hover {
    background: var(--bg-hover);
    color: var(--text);
  }
</style>
