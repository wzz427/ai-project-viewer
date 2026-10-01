<script lang="ts">
  import type { TreeEntry } from "$lib/services/tauri";
  import { visibleSorted } from "$lib/services/treeSort";
  import {
    dragState,
    isPinned,
    joinRel,
    reorderPinned,
    selectNode,
    toggleExpand,
    treeState,
    TREE_ROOT,
  } from "$lib/stores/fileTreeStore.svelte";
  import NodeContextMenu from "$lib/components/FileTree/NodeContextMenu.svelte";
  // Self-import is the Svelte 5 way to recurse (`<svelte:self>` is legacy).
  import Self from "$lib/components/FileTree/TreeItem.svelte";

  let {
    rootPath,
    parentRel,
    entry,
    depth,
  }: {
    rootPath: string;
    parentRel: string;
    entry: TreeEntry;
    depth: number;
  } = $props();

  // Read reactively; the state object exists by the time an item renders
  // (its parent level was listed through the store).
  const st = $derived(treeState.byRoot[rootPath]!);

  const rel = $derived(joinRel(parentRel, entry.name));
  const pinned = $derived(
    st.sortMode === "favorites" && isPinned(st, parentRel, entry.name),
  );
  const draggable = $derived(pinned);
  const expanded = $derived(st.expandedFolders.includes(rel));
  const emptyDir = $derived(st.emptyDirs.includes(rel));
  const error = $derived(st.loadErrors[rel]);
  const children = $derived(st.children[rel] ?? []);
  const sortedChildren = $derived(
    visibleSorted(children, {
      sortMode: st.sortMode,
      foldersFirst: st.foldersFirst,
      showSystemFolders: st.showSystemFolders,
      pinned: st.pinnedItems[rel],
    }),
  );
  const hiddenCount = $derived(st.hiddenCounts[rel] ?? 0);
  const selected = $derived(st.selectedRelPath === rel);

  let menu = $state<{ x: number; y: number } | null>(null);
  let dropOver = $state(false);

  function activate() {
    if (entry.isDir) {
      void toggleExpand(rootPath, rel);
    } else {
      // Files are selectable but not openable in Phase 2 — opening a file
      // means File Tabs + viewers, which is Phase 3 scope (spec-002 D6).
      selectNode(rootPath, rel);
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      activate();
    }
  }

  function openMenu(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    menu = { x: e.clientX, y: e.clientY };
  }

  function canAcceptDrop(): boolean {
    return (
      dragState.parentRel === parentRel &&
      dragState.name !== null &&
      dragState.name !== entry.name &&
      isPinned(st, parentRel, entry.name)
    );
  }

  function onDragStart(e: DragEvent) {
    if (!draggable || !e.dataTransfer) return;
    dragState.parentRel = parentRel;
    dragState.name = entry.name;
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", entry.name);
  }

  function onDragOver(e: DragEvent) {
    if (!canAcceptDrop()) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    dropOver = true;
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    dropOver = false;
    if (canAcceptDrop() && dragState.name) {
      // Same-parent pinned reorder only (V1.5 §38/§39) — never moves files
      // on disk, only display order.
      reorderPinned(rootPath, parentRel, dragState.name, entry.name);
    }
    dragState.parentRel = null;
    dragState.name = null;
  }
</script>

<div
  class="row"
  class:selected
  class:pinned
  class:drop-over={dropOver}
  class:dir={entry.isDir}
  role="treeitem"
  tabindex="-1"
  aria-selected={selected}
  aria-expanded={entry.isDir ? expanded : undefined}
  style="padding-left: {8 + depth * 14}px"
  draggable={draggable || undefined}
  onclick={activate}
  onkeydown={onKeydown}
  oncontextmenu={openMenu}
  ondragstart={onDragStart}
  ondragover={onDragOver}
  ondragleave={() => (dropOver = false)}
  ondrop={onDrop}
  title={rel}
>
  {#if entry.isDir}
    <span class="chevron" class:faded={emptyDir} class:open={expanded}>▸</span>
  {:else}
    <span class="dot"></span>
  {/if}
  {#if pinned}<span class="star" title="Pinned">★</span>{/if}
  <span class="name" class:muted={entry.systemGenerated}>{entry.name}</span>
</div>

{#if expanded && entry.isDir}
  <div class="children" role="group">
    {#if error}
      <div class="hint error" style="padding-left: {22 + depth * 14}px">{error}</div>
    {:else if sortedChildren.length === 0 && !st.children[rel]}
      <div class="hint" style="padding-left: {22 + depth * 14}px">Loading…</div>
    {:else}
      {#each sortedChildren as child (child.name)}
        <Self rootPath={rootPath} parentRel={rel} entry={child} depth={depth + 1} />
      {/each}
      {#if hiddenCount > 0 && !st.showSystemFolders}
        <div class="hint" style="padding-left: {22 + depth * 14}px">
          {hiddenCount} system folder{hiddenCount > 1 ? "s" : ""} hidden
        </div>
      {/if}
    {/if}
  </div>
{/if}

{#if menu}
  <NodeContextMenu
    {rootPath}
    parentRel={parentRel}
    name={entry.name}
    isDir={entry.isDir}
    x={menu.x}
    y={menu.y}
    onclose={() => (menu = null)}
  />
{/if}

<style>
  .row {
    display: flex;
    align-items: center;
    gap: 5px;
    padding-right: 6px;
    height: 24px;
    border-radius: var(--radius);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
  }

  .row:hover {
    background: var(--bg-hover);
  }

  .row.selected {
    background: var(--bg-active);
  }

  .row.drop-over {
    border-top: 2px solid var(--accent, var(--text));
    margin-top: -2px;
  }

  .chevron {
    width: 12px;
    flex-shrink: 0;
    font-size: 10px;
    color: var(--text-muted);
    transition: transform 0.1s ease;
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .chevron.faded {
    opacity: 0.35;
  }

  .dot {
    width: 12px;
    flex-shrink: 0;
    height: 3px;
    border-radius: 2px;
    background: var(--text-muted);
    opacity: 0.4;
    margin: 0 1px;
  }

  .star {
    color: var(--text-muted);
    font-size: 11px;
    flex-shrink: 0;
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .name.muted {
    color: var(--text-muted);
  }

  .row.dir .name {
    font-weight: 550;
  }

  .hint {
    display: flex;
    align-items: center;
    height: 22px;
    font-size: 11px;
    color: var(--text-muted);
    font-style: italic;
    user-select: none;
  }

  .hint.error {
    color: var(--danger, #d1866e);
    font-style: normal;
  }
</style>
