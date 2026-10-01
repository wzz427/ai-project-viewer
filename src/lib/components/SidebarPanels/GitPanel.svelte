<script lang="ts">
  import { activeProject } from "$lib/stores/projectStore.svelte";

  const project = $derived(activeProject());
</script>

{#if project}
  <p class="muted note">Git review arrives in Phase 7.</p>
{:else}
  <p class="muted note">No project open.</p>
{/if}

<style>
  .note {
    margin: 0;
    font-size: 12px;
  }
</style>
