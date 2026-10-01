<script lang="ts">
  import { activeProject } from "$lib/stores/projectStore.svelte";

  const project = $derived(activeProject());
</script>

{#if project}
  <div class="panel">
    <div class="path mono" title={project.rootPath}>{project.rootPath}</div>
    <p class="muted note">File tree arrives in Phase 2.</p>
  </div>
{:else}
  <p class="muted note">No project open.</p>
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
  }

  .note {
    margin: 0;
    font-size: 12px;
  }
</style>
