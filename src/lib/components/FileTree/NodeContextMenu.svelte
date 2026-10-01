<script lang="ts">
  import {
    pin,
    unpin,
    treeState,
  } from "$lib/stores/fileTreeStore.svelte";

  let {
    rootPath,
    parentRel,
    name,
    isDir,
    x,
    y,
    onclose,
  }: {
    rootPath: string;
    parentRel: string;
    name: string;
    isDir: boolean;
    x: number;
    y: number;
    onclose: () => void;
  } = $props();

  const st = $derived(treeState.byRoot[rootPath]!);
  const pinned = $derived(st.pinnedItems[parentRel]?.includes(name) ?? false);

  let el = $state<HTMLElement | null>(null);

  function close(e?: Event) {
    if (e && e.target instanceof Node && el?.contains(e.target)) return;
    onclose();
  }

  $effect(() => {
    window.addEventListener("mousedown", close, { capture: true });
    return () =>
      window.removeEventListener("mousedown", close, { capture: true });
  });

  function togglePin() {
    // Pin changes sibling DISPLAY order only — never the path on disk
    // (V1.5 §37/§38; files and folders are both pinnable).
    if (pinned) unpin(rootPath, parentRel, name);
    else pin(rootPath, parentRel, name);
    onclose();
  }
</script>

<div class="menu" bind:this={el} style="left: {x}px; top: {y}px">
  <div class="menu-path mono muted">
    {isDir ? "folder" : "file"} · {name}
  </div>
  <button class="menu-item" onclick={togglePin}>
    {pinned ? "Unpin" : "Pin to Top"}
  </button>
</div>

<style>
  .menu {
    position: fixed;
    z-index: 100;
    min-width: 200px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 4px;
  }

  .menu-path {
    padding: 4px 8px;
    font-size: 11px;
    max-width: 360px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .menu-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 5px 8px;
    border-radius: var(--radius);
  }

  .menu-item:hover {
    background: var(--bg-hover);
  }
</style>
