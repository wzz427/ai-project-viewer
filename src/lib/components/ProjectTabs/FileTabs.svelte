<script lang="ts">
  /**
   * File tab bar (V1.5 §46 layer 3 / §158): title = file name, click to
   * activate, × to close. Pin model (owner 2026-10-01, clarified): tabs
   * accumulate normally until one is pinned; from then on new files recycle
   * an unpinned slot. Tabs drag-reorder; the active tab scrolls into view.
   */
  import {
    tabsState,
    activateFile,
    closeFile,
    reorderTabs,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";
  import { fileNameOf } from "$lib/services/viewerType";
  import TabContextMenu from "./TabContextMenu.svelte";

  let { rootPath }: { rootPath: string } = $props();

  const tabs = $derived(tabsState.byRoot[rootPath]?.openFiles ?? []);
  const active = $derived(
    tabsState.byRoot[rootPath]?.activeFileRelativePath ?? null,
  );

  // Item 1: reveal the activated tab when it sits outside the visible strip.
  let bar = $state<HTMLElement | null>(null);
  $effect(() => {
    active;
    const el = bar?.querySelector<HTMLElement>(".file-tab.active");
    el?.scrollIntoView({ inline: "nearest", block: "nearest" });
  });

  let menu = $state<{ x: number; y: number; tab: RuntimeTab } | null>(null);
  let dropTarget = $state<string | null>(null);
  let dragRel = $state<string | null>(null);

  function openMenu(e: MouseEvent, tab: RuntimeTab) {
    e.preventDefault();
    e.stopPropagation();
    menu = { x: e.clientX, y: e.clientY, tab };
  }

  function onDragStart(e: DragEvent, t: RuntimeTab) {
    dragRel = t.relativePath;
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", t.relativePath);
    }
  }

  function onDragOver(e: DragEvent, t: RuntimeTab) {
    if (dragRel === null || dragRel === t.relativePath) return;
    // Both enter and over must be cancelled or WebView2 never fires drop (L10).
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    dropTarget = t.relativePath;
  }

  function onDrop(e: DragEvent, t: RuntimeTab) {
    e.preventDefault();
    const from = dragRel;
    dropTarget = null;
    dragRel = null;
    if (from && from !== t.relativePath) {
      reorderTabs(rootPath, from, t.relativePath);
    }
  }
</script>

{#if tabs.length > 0}
  <div class="file-tabs" bind:this={bar} role="tablist" aria-label="Open files">
    {#each tabs as t (t.relativePath)}
      <div
        class="file-tab"
        class:active={t.relativePath === active}
        class:deleted={t.deleted}
        class:drop-before={dropTarget === t.relativePath}
        role="tab"
        aria-selected={t.relativePath === active}
        tabindex="-1"
        draggable="true"
        title={t.relativePath}
        onclick={() => activateFile(rootPath, t.relativePath)}
        onkeydown={(e) => {
          if (e.key === "Enter" || e.key === " ")
            activateFile(rootPath, t.relativePath);
        }}
        oncontextmenu={(e) => openMenu(e, t)}
        ondragstart={(e) => onDragStart(e, t)}
        ondragenter={(e) => onDragOver(e, t)}
        ondragover={(e) => onDragOver(e, t)}
        ondragleave={() => (dropTarget = null)}
        ondrop={(e) => onDrop(e, t)}
      >
        {#if t.pinned}<span class="pin" title="Kept open">📌</span>{/if}
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

{#if menu}
  <TabContextMenu
    {rootPath}
    tab={menu.tab}
    x={menu.x}
    y={menu.y}
    onclose={() => (menu = null)}
  />
{/if}

<style>
  .file-tabs {
    display: flex;
    align-items: stretch;
    gap: 2px;
    border-bottom: 1px solid var(--viewer-border);
    background: var(--viewer-bg);
    padding: 4px 8px 0;
    overflow-x: auto;
    flex-shrink: 0;
    min-height: 32px;
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
    position: relative;
    flex-shrink: 0;
  }

  .file-tab:hover {
    background: var(--bg-hover);
  }

  /* Item 2: make the active tab unmistakable — accent bar + full contrast. */
  .file-tab.active {
    background: var(--viewer-bg);
    border-color: var(--viewer-border);
    color: var(--text);
    font-weight: 600;
  }

  .file-tab.active::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: -1px;
    height: 2px;
    background: var(--accent);
  }

  .file-tab.deleted .name {
    text-decoration: line-through;
  }

  .file-tab.drop-before {
    box-shadow: inset 0 2px 0 var(--accent);
  }

  .pin {
    font-size: 10px;
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
