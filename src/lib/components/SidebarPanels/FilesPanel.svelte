<script lang="ts">
  import { activeProject } from "$lib/stores/projectStore.svelte";
  import ProjectContextMenu from "$lib/components/ContextMenu/ProjectContextMenu.svelte";

  const project = $derived(activeProject());

  // The project root is the natural place users look for project actions
  // (matches the file-tree root context menu that arrives in Phase 2).
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
    <p class="muted note">File tree arrives in Phase 2.</p>
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
    gap: 8px;
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
  }

  .note {
    margin: 0;
    font-size: 12px;
  }
</style>
