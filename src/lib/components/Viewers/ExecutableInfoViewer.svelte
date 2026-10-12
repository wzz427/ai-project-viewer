<script lang="ts">
  /**
   * §122 Executable Info: left-clicking a .exe shows this stat card
   * (name / Windows Executable / Size / Modified / Path / "This file
   * cannot be previewed."). Nothing of the file is ever read — the fields
   * ride the inspect stat call, so there is no content buffer to release.
   */
  import type { RuntimeTab } from "$lib/stores/tabsStore.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const name = $derived(tab.relativePath.split("/").pop() ?? tab.relativePath);
  const sizeText = $derived(
    tab.sizeBytes === undefined
      ? null
      : tab.sizeBytes >= 1048576
        ? `${(tab.sizeBytes / 1048576).toFixed(1)} MB`
        : `${(tab.sizeBytes / 1024).toFixed(1)} KB`,
  );
  const modifiedText = $derived(
    tab.modifiedMs ? new Date(tab.modifiedMs).toLocaleString() : null,
  );
</script>

<div class="exe-info">
  <div class="card">
    <p class="exe-name">{name}</p>
    <p class="kind">Windows Executable</p>
    <dl>
      {#if sizeText !== null}
        <div class="row"><dt>Size:</dt><dd>{sizeText}</dd></div>
      {/if}
      {#if modifiedText !== null}
        <div class="row"><dt>Modified:</dt><dd>{modifiedText}</dd></div>
      {/if}
      <div class="row path"><dt>Path:</dt><dd>{rootPath}\{tab.relativePath.replaceAll("/", "\\")}</dd></div>
    </dl>
    <p class="muted">This file cannot be previewed.</p>
  </div>
</div>

<style>
  .exe-info {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .card {
    text-align: center;
    padding: 24px 32px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    gap: 10px;
    align-items: center;
    min-width: 280px;
  }

  .exe-name {
    font-family: var(--font-mono);
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0;
    max-width: 480px;
    overflow-wrap: anywhere;
  }

  .kind {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  dl {
    margin: 4px 0 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .row {
    display: flex;
    gap: 8px;
    justify-content: center;
    font-size: var(--text-sm);
  }

  dt {
    color: var(--text-muted);
  }

  dd {
    margin: 0;
    font-family: var(--font-mono);
  }

  .row.path dd {
    max-width: 380px;
    overflow-wrap: anywhere;
    text-align: left;
  }

  .muted {
    margin: 6px 0 0;
    color: var(--text-muted);
    font-size: var(--text-sm);
  }
</style>
