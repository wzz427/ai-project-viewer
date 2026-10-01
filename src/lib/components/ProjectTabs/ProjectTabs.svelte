<script lang="ts">
  import { ask } from "@tauri-apps/plugin-dialog";
  import {
    projectState,
    activateProject,
    addProjectViaPicker,
    removeProject,
    type ProjectTab,
  } from "$lib/stores/projectStore.svelte";
  import { toast } from "$lib/stores/toastStore.svelte";

  let menuFor = $state<ProjectTab | null>(null);
  let menuX = $state(0);
  let menuY = $state(0);
  // The close listener runs in the capture phase on window, i.e. BEFORE any
  // bubbling handler on the menu itself — so closings must spare the menu.
  let menuEl = $state<HTMLElement | null>(null);

  function openMenu(tab: ProjectTab, e: MouseEvent) {
    e.preventDefault();
    menuFor = tab;
    menuX = e.clientX;
    menuY = e.clientY;
  }

  function closeMenu(e?: Event) {
    if (e && e.target instanceof Node && menuEl?.contains(e.target)) return;
    menuFor = null;
  }

  async function confirmRemove() {
    const tab = menuFor;
    closeMenu();
    if (!tab) return;
    // Removing only detaches it from the viewer — never touches disk (V1.5 §15).
    const yes = await ask(
      `Remove "${tab.name}" from AI Project Viewer?\n\nThe folder on disk is not modified or deleted.`,
      { title: "Remove Project", kind: "warning" },
    );
    if (yes) {
      removeProject(tab.id);
      toast(`Removed "${tab.name}" (folder untouched on disk).`);
    }
  }

  $effect(() => {
    if (!menuFor) return;
    window.addEventListener("mousedown", closeMenu, { capture: true });
    return () =>
      window.removeEventListener("mousedown", closeMenu, { capture: true });
  });
</script>

<div class="project-tabs" role="presentation" oncontextmenu={(e) => e.preventDefault()}>
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
  <div
    class="menu"
    bind:this={menuEl}
    style="left: {menuX}px; top: {menuY}px"
  >
    <div class="menu-path mono muted">{menuFor.rootPath}</div>
    <button class="menu-item" onclick={confirmRemove}>Remove Project</button>
  </div>
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

  .menu {
    position: fixed;
    z-index: 100;
    min-width: 220px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 4px;
  }

  .menu-path {
    padding: 4px 8px;
    font-size: 11px;
    max-width: 360px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .menu-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 5px 8px;
    border-radius: var(--radius);
  }

  .menu-item:hover {
    background: var(--bg-hover);
  }
</style>
