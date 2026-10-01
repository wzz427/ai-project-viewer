<script lang="ts">
  import { activeProject } from "$lib/stores/projectStore.svelte";
  import ProjectContextMenu from "$lib/components/ContextMenu/ProjectContextMenu.svelte";
  import FileTree from "$lib/components/FileTree/FileTree.svelte";

  const project = $derived(activeProject());

  // The project root is the natural place users look for project actions;
  // tree nodes have their own menu (Pin/Unpin), the ⋯ header menu holds the
  // sort/visibility toggles (V1.5 §30).
  let menu = $state<{ x: number; y: number } | null>(null);

  function openMenu(e: MouseEvent) {
    e.preventDefault();
    menu = { x: e.clientX, y: e.clientY };
  }
</script>

{#if project}
  <div class="panel">
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

  .path {
    font-size: 11px;
    padding: 4px 6px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: context-menu;
    flex-shrink: 0;
  }

  .note {
    margin: 0;
    font-size: 12px;
  }
</style>
