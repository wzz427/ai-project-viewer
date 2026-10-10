<script lang="ts">
  import {
    projectState,
    activateProject,
    addProjectViaPicker,
    type ProjectTab,
  } from "$lib/stores/projectStore.svelte";
  import { gitDirtyOf } from "$lib/stores/gitStore.svelte";
  import ProjectContextMenu from "$lib/components/ContextMenu/ProjectContextMenu.svelte";
  import UpdateButton from "$lib/components/ProjectTabs/UpdateButton.svelte";

  let menuFor = $state<ProjectTab | null>(null);
  let menuX = $state(0);
  let menuY = $state(0);

  // §10/§46 first layer: ✓ clean / ● dirty for the project's own scope;
  // non-git and not-yet-fetched projects show no symbol.
  function indicatorOf(tab: ProjectTab): string | null {
    const dirty = gitDirtyOf(tab.rootPath);
    if (dirty === undefined) return null;
    return dirty ? "●" : "✓";
  }

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
      {tab.name}{#if indicatorOf(tab)}<span class="git-state {indicatorOf(tab) === "●" ? "dirty" : "clean"}">{indicatorOf(tab)}</span>{/if}
    </button>
  {/each}
  <button class="add" onclick={() => addProjectViaPicker()} title="Add project" aria-label="Add project">
    +
  </button>
  <UpdateButton />
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

  .git-state {
    margin-left: 5px;
    font-size: 10px;
  }

  .git-state.dirty {
    color: var(--git-d);
  }

  .git-state.clean {
    color: var(--text-muted);
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
