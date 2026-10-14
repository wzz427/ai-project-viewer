<script lang="ts">
  import { activeProject } from "$lib/stores/projectStore.svelte";
  import ProjectContextMenu from "$lib/components/ContextMenu/ProjectContextMenu.svelte";
  import FileTree from "$lib/components/FileTree/FileTree.svelte";
  import {
    dragState,
    movePinnedToTop,
    treeState,
    TREE_ROOT,
  } from "$lib/stores/fileTreeStore.svelte";

  const project = $derived(activeProject());

  // The project root is the natural place users look for project actions;
  // tree nodes have their own menu (Pin/Unpin).
  let menu = $state<{ x: number; y: number } | null>(null);

  // Top drop zone: releasing a pinned drag ABOVE the first root row (the
  // path box / gap band) means "insert at the very top" — without it that
  // ~30px band swallows throws-to-top (owner report 2026-10-01).
  let topDrop = $state(false);

  function openMenu(e: MouseEvent) {
    e.preventDefault();
    menu = { x: e.clientX, y: e.clientY };
  }

  function panelDragOver(e: DragEvent) {
    topDrop = false;
    if (!project || dragState.parentRel !== TREE_ROOT || !dragState.name) return;
    const st = treeState.byRoot[project.rootPath];
    if (!st?.pinnedItems[TREE_ROOT]?.length) return;
    const first = document.querySelector<HTMLElement>(".file-tree > .row");
    if (!first) return;
    if (e.clientY < first.getBoundingClientRect().top) {
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
      topDrop = true;
    }
  }

  function panelDrop(e: DragEvent) {
    const active = topDrop;
    topDrop = false;
    if (!active) return;
    e.preventDefault();
    if (project && dragState.name) {
      movePinnedToTop(project.rootPath, TREE_ROOT, dragState.name);
    }
    dragState.parentRel = null;
    dragState.name = null;
  }
</script>

{#if project}
  <div
    class="panel"
    class:top-drop={topDrop}
    role="presentation"
    ondragenter={panelDragOver}
    ondragover={panelDragOver}
    ondragleave={() => (topDrop = false)}
    ondrop={panelDrop}
  >
    <div class="path mono" role="presentation" title={project.rootPath} oncontextmenu={openMenu}>
      {project.rootPath}
    </div>
    <FileTree rootPath={project.rootPath} />
  </div>
{:else}
  <p class="muted note">No project open.</p>
{/if}

{#if menu && project}
  <ProjectContextMenu
    project={project}
    x={menu.x}
    y={menu.y}
    onclose={() => (menu = null)}
  />
{/if}

<style>
  .panel {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-height: 0;
  }

  .panel.top-drop :global(.file-tree) {
    box-shadow: inset 0 2px 0 var(--accent, var(--text));
  }

  .path {
    font-size: var(--text-xs);
    padding: 4px 6px;
    /* Theme pack surface.input: the path chip is an input-surface element
     (spec §四 路径与搜索框), not a band-colored one. */
    background: var(--bg-input);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: context-menu;
    flex-shrink: 0;
  }

  .note {
    margin: 0;
    font-size: var(--text-sm);
  }
</style>
