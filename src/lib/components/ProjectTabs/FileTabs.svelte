<script lang="ts">
  /**
   * File tab bar for the main area (V1.5 §46 layer 3 / §158 tabsStore):
   * title = file name, click to activate, × to close.
   */
  import {
    tabsState,
    activateFile,
    closeFile,
  } from "$lib/stores/tabsStore.svelte";
  import { fileNameOf } from "$lib/services/viewerType";

  let { rootPath }: { rootPath: string } = $props();

  const tabs = $derived(tabsState.byRoot[rootPath]?.openFiles ?? []);
  const active = $derived(tabsState.byRoot[rootPath]?.activeFileRelativePath ?? null);
</script>

{#if tabs.length > 0}
  <div class="file-tabs" role="tablist" aria-label="Open files">
    {#each tabs as t (t.relativePath)}
      <div
        class="file-tab"
        class:active={t.relativePath === active}
        class:deleted={t.deleted}
        role="tab"
        aria-selected={t.relativePath === active}
        tabindex="-1"
        title={t.relativePath}
        onclick={() => activateFile(rootPath, t.relativePath)}
        onkeydown={(e) => {
          if (e.key === "Enter" || e.key === " ") activateFile(rootPath, t.relativePath);
        }}
      >
        <span class="name">{fileNameOf(t.relativePath)}</span>
        <button
          class="close"
          aria-label={`Close ${fileNameOf(t.relativePath)}`}
          onclick={(e) => {
            e.stopPropagation();
            closeFile(rootPath, t.relativePath);
          }}
        >×</button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .file-tabs {
    display: flex;
    align-items: stretch;
    gap: 2px;
    border-bottom: 1px solid var(--border);
    padding: 4px 8px 0;
    overflow-x: auto;
    flex-shrink: 0;
    min-height: 30px;
  }

  .file-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px 4px 10px;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: var(--radius) var(--radius) 0 0;
    font-size: 12px;
    color: var(--text-muted);
    cursor: pointer;
    white-space: nowrap;
    user-select: none;
  }

  .file-tab:hover {
    background: var(--bg-hover);
  }

  .file-tab.active {
    background: var(--bg);
    border-color: var(--border);
    color: var(--text);
  }

  .file-tab.deleted .name {
    text-decoration: line-through;
  }

  .close {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    font-size: 13px;
    color: var(--text-muted);
  }

  .close:hover {
    background: var(--bg-hover);
    color: var(--text);
  }
</style>
