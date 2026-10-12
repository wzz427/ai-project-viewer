<script lang="ts">
  import { clampMenu } from "$lib/components/ContextMenu/menuPosition";
  import { pathsExist } from "$lib/services/tauri";
  import { recentName, recentParent } from "$lib/services/recentList";
  import Icon from "$lib/components/Icon.svelte";
  import {
    addProjectFromPath,
    addProjectViaPicker,
  } from "$lib/stores/projectStore.svelte";
  import {
    recentState,
    removeRecentFolder,
    clearRecentFolders,
  } from "$lib/stores/recentStore.svelte";

  let {
    x,
    y,
    onclose,
  }: {
    x: number;
    y: number;
    onclose: () => void;
  } = $props();

  // Same close contract as ProjectContextMenu: the capture-phase window
  // listener runs BEFORE any bubbling handler here — closings spare the menu.
  let el = $state<HTMLElement | null>(null);

  let left = $state(0);
  let top = $state(0);
  $effect(() => {
    if (!el) return;
    ({ left, top } = clampMenu(el, x, y));
  });

  // One batch stat per open (and per list change, e.g. after a row ✕):
  // dead folders gray out. No live filesystem watching (spec-010 D3).
  // The snapshot pins flag↔path alignment even if the list mutates while
  // the stat is in flight.
  let missing = $state<Set<string>>(new Set());
  $effect(() => {
    const snapshot = [...recentState.folders];
    if (snapshot.length === 0) {
      missing = new Set();
      return;
    }
    void pathsExist(snapshot)
      .then((flags) => {
        missing = new Set(snapshot.filter((_, i) => !flags[i]));
      })
      .catch(() => {});
  });

  function open(path: string) {
    onclose();
    void addProjectFromPath(path);
  }

  function close(e?: Event) {
    if (e && e.target instanceof Node && el?.contains(e.target)) return;
    onclose();
  }

  $effect(() => {
    window.addEventListener("mousedown", close, { capture: true });
    return () =>
      window.removeEventListener("mousedown", close, { capture: true });
  });

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div
  class="menu"
  bind:this={el}
  style="left: {left}px; top: {top}px"
  data-menu-id="add-project-menu"
>
  <button
    class="menu-item"
    data-menu-id="browse-folder"
    onclick={() => {
      onclose();
      void addProjectViaPicker();
    }}
  >Browse for Folder…</button>
  {#if recentState.folders.length > 0}
    <div class="sep"></div>
    <div class="menu-label">Open Recent</div>
    {#each recentState.folders as path (path)}
      <div
        class="recent-row"
        class:missing={missing.has(path)}
        data-recent-path={path}
      >
        <button class="recent-open" title={path} onclick={() => open(path)}>
          <span class="name">{recentName(path)}</span>
          <span class="path">{recentParent(path)}</span>
        </button>
        <button
          class="recent-remove"
          aria-label="Remove from recent"
          title="Remove from recent"
          onclick={(e) => {
            e.stopPropagation();
            removeRecentFolder(path);
          }}
        ><Icon name="x" size={12} /></button>
      </div>
    {/each}
    <div class="sep"></div>
    <button
      class="menu-item"
      data-menu-id="clear-recent"
      onclick={() => {
        clearRecentFolders();
        onclose();
      }}
    >Clear Recent</button>
  {/if}
</div>

<style>
  .menu {
    position: fixed;
    z-index: 100;
    width: 340px;
    background: var(--bg-overlay);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 4px;
  }

  .menu-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 5px 8px;
    border-radius: var(--radius);
    transition: background-color var(--transition-fast);
  }

  .menu-item:hover {
    background: var(--bg-hover);
  }

  .menu-label {
    padding: 4px 8px 2px;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .sep {
    height: 1px;
    background: var(--border);
    margin: 4px 6px;
  }

  .recent-row {
    display: flex;
    align-items: stretch;
    border-radius: var(--radius);
  }

  .recent-row:hover {
    background: var(--bg-hover);
  }

  .recent-row.missing {
    opacity: 0.45;
  }

  .recent-open {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 4px 8px;
    text-align: left;
  }

  .recent-open .name {
    font-size: var(--text-base);
    color: var(--text);
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .recent-open .path {
    font-size: var(--text-xs);
    color: var(--text-muted);
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .recent-remove {
    align-self: center;
    display: inline-flex;
    align-items: center;
    margin-right: 4px;
    padding: 3px 5px;
    color: var(--text-muted);
    border-radius: var(--radius);
    opacity: 0;
  }

  .recent-row:hover .recent-remove {
    opacity: 1;
  }

  .recent-remove:hover {
    background: var(--border);
    color: var(--text);
  }
</style>
