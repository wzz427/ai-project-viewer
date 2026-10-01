<script lang="ts">
  /**
   * Terminal viewer states: binary guard, >20 MB guard, deleted file
   * (V1.5 §83/§104/§106, spec-003 D4). The two external actions for huge
   * files arrive with Phase 6's command set.
   */
  import { closeFile, type RuntimeTab } from "$lib/stores/tabsStore.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const sizeMb = $derived(
    tab.sizeBytes ? (tab.sizeBytes / 1048576).toFixed(1) : null,
  );
</script>

<div class="unsupported">
  {#if tab.deleted}
    <div class="card">
      <p class="name">{tab.relativePath}</p>
      <p>This file has been deleted.</p>
      <button onclick={() => closeFile(rootPath, tab.relativePath)}>
        Close Tab
      </button>
    </div>
  {:else if tab.unsupportedReason === "binary"}
    <div class="card">
      <p class="name">{tab.relativePath}</p>
      <p>Binary file — not shown as text.</p>
      <p class="muted">{sizeMb} MB</p>
    </div>
  {:else if tab.unsupportedReason === "huge"}
    <div class="card">
      <p class="name">{tab.relativePath}</p>
      <p>File is larger than 20 MB and will not be opened in the viewer.</p>
      <p class="muted">{sizeMb} MB</p>
      <p class="muted small">
        Show in File Explorer / Open with System Default App arrive in Phase 6.
      </p>
    </div>
  {:else}
    <div class="card">
      <p class="name">{tab.relativePath}</p>
      <p>Cannot display this file.</p>
    </div>
  {/if}
</div>

<style>
  .unsupported {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .card {
    text-align: center;
    padding: 24px 32px;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: center;
  }

  .name {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-muted);
    margin: 0;
    max-width: 480px;
    overflow-wrap: anywhere;
  }

  .card p {
    margin: 0;
  }

  button {
    padding: 5px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  button:hover {
    background: var(--bg-hover);
  }

  .muted {
    color: var(--text-muted);
    font-size: 12px;
  }

  .small {
    font-size: 11px;
  }
</style>
