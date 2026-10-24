<script lang="ts">
  /**
   * Media (video/audio) info card (owner 2026-10-24 ruling: a tree click
   * has exactly ONE meaning — show the file in the viewer pane; launching
   * the player is a deliberate act, via this card's button or the tree's
   * right-click Open). Stat-only like the .exe card: no content is ever
   * read, the fields ride the inspect call.
   */
  import type { RuntimeTab } from "$lib/stores/tabsStore.svelte";
  import {
    openWithDefaultApp,
    revealInExplorer,
  } from "$lib/services/tauri";
  import { toast } from "$lib/stores/toastStore.svelte";

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

  let launching = $state(false);

  async function play() {
    if (launching) return;
    launching = true;
    toast(`Opening ${name}…`);
    try {
      await openWithDefaultApp(rootPath, tab.relativePath);
    } catch (err) {
      toast(`Cannot open media: ${err}`, { kind: "error" });
    } finally {
      launching = false;
    }
  }

  async function reveal() {
    try {
      await revealInExplorer(rootPath, tab.relativePath);
    } catch (err) {
      toast(`Explorer failed: ${err}`, { kind: "error" });
    }
  }
</script>

<div class="media-info">
  <div class="card">
    <p class="media-name">{name}</p>
    <p class="kind">Media file (video/audio)</p>
    <dl>
      {#if sizeText !== null}
        <div class="row"><dt>Size:</dt><dd>{sizeText}</dd></div>
      {/if}
      {#if modifiedText !== null}
        <div class="row"><dt>Modified:</dt><dd>{modifiedText}</dd></div>
      {/if}
      <div class="row path"><dt>Path:</dt><dd>{rootPath}\{tab.relativePath.replaceAll("/", "\\")}</dd></div>
    </dl>
    <p class="muted">This file cannot be previewed in the app.</p>
    <div class="actions">
      <button class="primary" onclick={play} disabled={launching}>
        {launching ? "Opening…" : "Open in Default Player"}
      </button>
      <button onclick={reveal}>Show in File Explorer</button>
    </div>
  </div>
</div>

<style>
  .media-info {
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
    gap: 8px;
    align-items: center;
  }

  .media-name {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin: 0;
    max-width: 480px;
    overflow-wrap: anywhere;
  }

  .kind {
    margin: 0;
    font-size: var(--text-base);
    font-weight: 600;
  }

  dl {
    margin: 4px 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 280px;
  }

  .row {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    font-size: var(--text-sm);
  }

  .row dt {
    color: var(--text-muted);
  }

  .row dd {
    margin: 0;
  }

  .row.path dd {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    overflow-wrap: anywhere;
    max-width: 320px;
    text-align: left;
  }

  .muted {
    color: var(--text-muted);
    font-size: var(--text-sm);
    margin: 0;
  }

  .actions {
    display: flex;
    gap: 10px;
    margin-top: 6px;
  }

  button {
    padding: 5px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-overlay);
    transition: background-color var(--transition-fast);
  }

  button:hover {
    background: var(--bg-hover);
  }

  button.primary {
    border-color: var(--border-strong, var(--border));
    font-weight: 600;
  }
</style>
