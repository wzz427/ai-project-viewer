<script lang="ts">
  import type { TreeEntry } from "$lib/services/tauri";
  import { visibleSorted } from "$lib/services/treeSort";
  import {
    contextMenuTarget,
    dragState,
    isPinned,
    joinRel,
    reorderPinned,
    toggleExpand,
    treeState,
    TREE_ROOT,
  } from "$lib/stores/fileTreeStore.svelte";
  import { activeRelOf, openFile } from "$lib/stores/tabsStore.svelte";
  import { settings } from "$lib/stores/settingsStore.svelte";
  import { gitMarkOf } from "$lib/stores/gitStore.svelte";
  import { letterClass } from "$lib/services/gitFormat";
  import { iconFamilyOf } from "$lib/services/viewerType";
  import Icon, { FILE_ICONS } from "$lib/components/Icon.svelte";
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
  const pinned = $derived(isPinned(st, parentRel, entry.name));
  const draggable = $derived(pinned);
  const expanded = $derived(st.expandedFolders.includes(rel));
  const emptyDir = $derived(st.emptyDirs.includes(rel));
  const error = $derived(st.loadErrors[rel]);
  const children = $derived(st.children[rel] ?? []);
  const sortedChildren = $derived(
    visibleSorted(children, {
      foldersFirst: st.foldersFirst,
      showSystemFolders: settings.fileTree.showSystemGeneratedFolders,
      pinned: st.pinnedItems[rel],
    }),
  );
  const hiddenCount = $derived(st.hiddenCounts[rel] ?? 0);
  // Highlight derives from the ACTIVE TAB (owner 2026-10-10: the old
  // click-scoped selection drifted from the tab strip — tree and file area
  // ended up highlighting different files).
  // While a context menu is open on some row of THIS project — or was
  // ACTED ON and not yet superseded (owner 2026-10-12) — that row OWNS the
  // highlight; the override clears on dismiss-without-action and on the
  // next file activation (clearTreeHighlight / revealInTree).
  const selected = $derived(
    contextMenuTarget.rootPath === rootPath
      ? contextMenuTarget.rel === rel
      : activeRelOf(rootPath) === rel,
  );
  // §46 third layer: single git letter on FILE rows only — folders never
  // aggregate (§47/§48); collapsed-folder blind spots are accepted (§49).
  const gitMark = $derived(entry.isDir ? null : gitMarkOf(rootPath, rel));

  let menu = $state<{ x: number; y: number } | null>(null);
  // Cursor-half drop: "before" draws the line above the row, "after" below.
  let dropAt = $state<"before" | "after" | null>(null);

  function activate() {
    if (entry.isDir) {
      void toggleExpand(rootPath, rel);
    } else {
      // Single click opens the file (spec-003 D1) — reading is this app's
      // main verb. The row highlights because openFile makes it the ACTIVE
      // tab (derived above), not via a click-scoped selection.
      void openFile(rootPath, rel);
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

  // WebView2 requires canceling dragenter as well as dragover for the drop
  // to fire (lessons L10 addendum); same body serves both events.
  function onDragOver(e: DragEvent) {
    if (!canAcceptDrop()) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    dropAt = e.clientY < rect.top + rect.height / 2 ? "before" : "after";
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    const position = dropAt;
    dropAt = null;
    if (canAcceptDrop() && dragState.name && position) {
      // Same-parent pinned reorder only (V1.5 §38/§39) — never moves files
      // on disk, only display order.
      reorderPinned(rootPath, parentRel, dragState.name, entry.name, position);
    }
    dragState.parentRel = null;
    dragState.name = null;
  }
</script>

<div
  class="row"
  class:selected
  class:pinned
  class:drop-before={dropAt === "before"}
  class:drop-after={dropAt === "after"}
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
  ondragenter={onDragOver}
  ondragover={onDragOver}
  ondragleave={() => (dropAt = null)}
  ondrop={onDrop}
  title={rel}
>
  <!-- VS Code-style indent guides: one vertical line per ancestor level,
       aligned with that level's chevron — without them file depth is
       only guessable by eye (owner 2026-10-10). -->
  {#each Array(depth) as _, i (i)}
    <span class="indent-guide" style="left: {8 + i * 14 + 6}px"></span>
  {/each}
  {#if entry.isDir}
    <span class="chevron" class:faded={emptyDir} class:open={expanded}><Icon name="chevron-right" size={12} /></span>
  {:else}
    <!-- spec-014 R4: the old 12px "dot bar" marker becomes a type icon in
         the SAME 12px slot — geometry unchanged, wayfinding gained. -->
    <span class="ficon"><Icon name={FILE_ICONS[iconFamilyOf(entry.name)]} size={12} /></span>
  {/if}
  <span class="name" class:muted={entry.systemGenerated}>{entry.name}</span>
  {#if gitMark}<span class="git-mark {letterClass(gitMark)}">{gitMark}</span>{/if}
  <!-- Pin marker trails at the row's far RIGHT (owner 2026-10-12): the old
       leading star occupied the column where the children's indent lands —
       a pinned folder's name and its children aligned and the hierarchy
       became unreadable. A trailing pushpin (same glyph as tab pins) keeps
       every name column depth-true. -->
  {#if pinned}<span class="pin" title="Pinned"><Icon name="pin" size={12} /></span>{/if}
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
      {#if hiddenCount > 0 && !settings.fileTree.showSystemGeneratedFolders}
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
    position: relative;
    transition: background-color var(--transition-fast);
  }

  .indent-guide {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--border);
    pointer-events: none;
  }

  .row:hover {
    background: var(--bg-hover);
  }

  /* Selected row (spec-014 R5 + theme pack selection.*): accent-soft fill
     (= selection.bg) + selection.fg text + 2px accent guide on the left —
     "which file am I on" survives at a glance. */
  .row.selected {
    background: var(--accent-soft);
    color: var(--sel-fg);
    box-shadow: inset 2px 0 0 var(--accent);
  }

  .row.drop-before {
    box-shadow: inset 0 2px 0 var(--accent);
  }

  .row.drop-after {
    box-shadow: inset 0 -2px 0 var(--accent);
  }

  .chevron {
    width: 12px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    color: var(--text-muted);
    transition: transform var(--transition-fast);
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .chevron.faded {
    opacity: 0.35;
  }

  .ficon {
    width: 12px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    color: var(--text-muted);
  }

  .pin {
    margin-left: auto;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    color: var(--text-muted);
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .name.muted {
    color: var(--text-muted);
  }

  /* Git letter marks (§46; colors from app.css theme tokens). */
  .git-mark {
    flex-shrink: 0;
    margin-left: auto;
    font-size: var(--text-xs);
    font-weight: 700;
    padding-left: 6px;
  }

  .row.dir .name {
    font-weight: 600;
  }

  .hint {
    display: flex;
    align-items: center;
    height: 22px;
    font-size: var(--text-xs);
    color: var(--text-muted);
    font-style: italic;
    user-select: none;
  }

  .hint.error {
    color: var(--danger);
    font-style: normal;
  }
</style>
