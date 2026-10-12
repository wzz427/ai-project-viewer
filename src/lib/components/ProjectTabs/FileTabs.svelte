<script lang="ts">
  /**
   * File tab bar (V1.5 §46 layer 3 / §158): title = file name, click to
   * activate, × to close. Pin model (owner 2026-10-01, clarified): tabs
   * accumulate normally until one is pinned; from then on new files recycle
   * an unpinned slot. Tabs drag-reorder; the active tab scrolls into view.
   * spec-014 R1/R4: browser-style 28px strip (top hairline) — orthogonal
   * to the 40px project chrome band; each tab leads with a type icon
   * sourced from the viewer routing table.
   */
  import {
    tabsState,
    activateFile,
    closeFile,
    moveTabToEnd,
    reorderTabs,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";
  import { fileNameOf, iconFamilyOf } from "$lib/services/viewerType";
  import Icon, { FILE_ICONS } from "$lib/components/Icon.svelte";
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
  // Cursor-half drop: "before" draws the line above the tab, "after" below —
  // without "after" the rightmost slot can never be reached.
  let dropAt = $state<{ rel: string; pos: "before" | "after" } | null>(null);
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
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    dropAt = {
      rel: t.relativePath,
      pos: e.clientX < rect.left + rect.width / 2 ? "before" : "after",
    };
  }

  function onDrop(e: DragEvent, t: RuntimeTab) {
    e.preventDefault();
    const from = dragRel;
    const at = dropAt;
    dropAt = null;
    dragRel = null;
    if (from && from !== t.relativePath && at) {
      reorderTabs(rootPath, from, t.relativePath, at.pos);
    }
  }

  // Empty band after the last tab = "append at end". Without this zone the
  // owner gesture (throw to the far right) lands on the bar itself and the
  // drop is swallowed — same dead-zone family as the pinned-area top (L10).
  let bandDrop = $state(false);

  function overBar(e: DragEvent) {
    if (dragRel === null) return;
    if ((e.target as HTMLElement).closest(".file-tab")) return; // tab handles it
    e.preventDefault(); // dragenter AND dragover both (L10)
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    bandDrop = true;
  }

  function dropBar(e: DragEvent) {
    const active = bandDrop;
    bandDrop = false;
    if (!active) return;
    e.preventDefault();
    const from = dragRel;
    dragRel = null;
    if (from) moveTabToEnd(rootPath, from);
  }
</script>

{#if tabs.length > 0}
  <div
    class="file-tabs"
    class:band-drop={bandDrop}
    bind:this={bar}
    role="tablist"
    aria-label="Open files"
    tabindex="-1"
    ondragenter={overBar}
    ondragover={overBar}
    ondragleave={() => (bandDrop = false)}
    ondrop={dropBar}
  >
    {#each tabs as t (t.relativePath)}
      <div
        class="file-tab"
        class:active={t.relativePath === active}
        class:deleted={t.deleted}
        class:drop-before={dropAt?.rel === t.relativePath && dropAt.pos === "before"}
        class:drop-after={dropAt?.rel === t.relativePath && dropAt.pos === "after"}
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
        ondragleave={() => (dropAt = null)}
        ondrop={(e) => onDrop(e, t)}
      >
        {#if t.pinned}<span class="pin" title="Kept open"><Icon name="pin" size={12} /></span>{/if}
        <span class="type-icon"><Icon name={FILE_ICONS[iconFamilyOf(t.relativePath)]} size={14} /></span>
        <span class="name" title={t.relativePath}>{fileNameOf(t.relativePath)}</span>
        <button
          class="close"
          aria-label={`Close ${fileNameOf(t.relativePath)}`}
          onclick={(e) => {
            e.stopPropagation();
            closeFile(rootPath, t.relativePath);
          }}
        ><Icon name="x" size={12} /></button>
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
    background: var(--bg-raised);
    padding: 3px 6px 0;
    overflow-x: auto;
    flex-shrink: 0;
    min-height: 28px;
  }

  .file-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 6px 3px 8px;
    border-radius: var(--radius) var(--radius) 0 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;
    white-space: nowrap;
    user-select: none;
    /* Long names clamp (owner 2026-10-02): full name lives in the tab's
       title tooltip; VS Code-style ellipsis keeps one tab from eating
       the bar. */
    max-width: 160px;
    position: relative;
    flex-shrink: 0;
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast);
  }

  .file-tab:hover {
    background: var(--bg-hover);
  }

  /* Item 2: make the active tab unmistakable — it merges with the reading
     surface below and carries a 2px accent hairline on TOP (the project
     bar marks active with a BOTTOM bar — the two levels never read alike,
     spec-014 R1). */
  .file-tab.active {
    background: var(--viewer-bg);
    color: var(--text);
    font-weight: 600;
  }

  .file-tab.active::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: -3px;
    height: 2px;
    background: var(--accent);
  }

  .file-tab .name {
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .file-tab .type-icon {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    color: var(--text-muted);
  }

  .file-tab.active .type-icon {
    color: var(--accent);
  }

  .file-tab.deleted .name {
    text-decoration: line-through;
  }

  .file-tab.drop-before {
    box-shadow: inset 0 2px 0 var(--accent);
  }

  .file-tab.drop-after {
    box-shadow: inset 0 -2px 0 var(--accent);
  }

  .file-tabs.band-drop {
    box-shadow: inset -2px 0 0 var(--accent);
  }

  .pin {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    color: var(--text-muted);
  }

  .close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    /* padding: 0 — the UA gives buttons 6px side padding; a 16px box
       minus 12px leaves a 4px content area and the SVG flex item
       silently shrinks to 4×12px (owner 2026-10-12 二次报障, live-attached
       geometry). Text glyphs overflow and stay visible; SVGs squeeze. */
    padding: 0;
    /* flex-shrink: 0 — without it a clamped tab (max-width 160px, long
       file names) crushes the button with the name. The name (min-width: 0
       + ellipsis) absorbs the whole clamp; controls never shrink (same
       rule as .pin/.type-icon). */
    flex-shrink: 0;
    border-radius: var(--radius);
    color: var(--text-muted);
    /* Always visible (owner 2026-10-12 报障"×都看不到了"): the
       hover-only reveal was an unapproved 0.7.14 flourish — quiet means
       muted color, never invisible. */
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast);
  }

  .close:hover {
    background: var(--bg-hover);
    color: var(--text);
  }
</style>
