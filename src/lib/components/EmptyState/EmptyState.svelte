<script lang="ts">
  import { addProjectViaPicker } from "$lib/stores/projectStore.svelte";
</script>

<!-- Copy per V1.5 §151. -->
<div class="empty-state">
  <h1>AI Project Viewer</h1>
  <p class="muted">Open your first project</p>
  <button class="open-folder" onclick={() => addProjectViaPicker()}>Open Folder</button>
  <p class="tagline">Read. Review. Run. Hand off.</p>
</div>

<style>
  .empty-state {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }

  h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }

  p {
    margin: 0;
  }

  .open-folder {
    margin-top: 12px;
    padding: 7px 20px;
    background: var(--accent);
    color: var(--accent-text);
    border-radius: var(--radius);
    font-size: 13px;
  }

  .open-folder:hover {
    filter: brightness(1.1);
  }

  .tagline {
    margin-top: 10px;
    color: var(--text-muted);
    font-size: 12px;
  }
</style>
