<script lang="ts">
  import {
    refreshProject,
    setFoldersFirst,
    setShowSystemFolders,
    setSortMode,
    treeState,
  } from "$lib/stores/fileTreeStore.svelte";

  let {
    rootPath,
    x,
    y,
    onclose,
  }: {
    rootPath: string;
    x: number;
    y: number;
    onclose: () => void;
  } = $props();

  const st = $derived(treeState.byRoot[rootPath]!);

  // Same capture-phase pattern as ProjectContextMenu: the outside-click
  // listener fires before bubbling handlers inside the menu.
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

  // Menu structure is verbatim V1.5 §30 — Sort radios, Folders First,
  // Show system/generated folders (default OFF), Refresh.
  function chooseSort(mode: "name" | "favorites") {
    setSortMode(rootPath, mode);
    onclose();
  }

  function toggleFoldersFirst() {
    setFoldersFirst(rootPath, !st.foldersFirst);
    onclose();
  }

  function toggleSystemFolders() {
    setShowSystemFolders(rootPath, !st.showSystemFolders);
    onclose();
  }

  function refresh() {
    void refreshProject(rootPath);
    onclose();
  }
</script>

<div class="menu" bind:this={el} style="left: {x}px; top: {y}px">
  <div class="menu-label">Sort</div>
  <button class="menu-item" onclick={() => chooseSort("name")}>
    <span class="glyph">{st.sortMode === "name" ? "●" : "○"}</span> Name
  </button>
  <button class="menu-item" onclick={() => chooseSort("favorites")}>
    <span class="glyph">{st.sortMode === "favorites" ? "●" : "○"}</span>
    Favorites First
  </button>
  <button class="menu-item" onclick={toggleFoldersFirst}>
    <span class="glyph">{st.foldersFirst ? "☑" : "☐"}</span> Folders First
  </button>
  <div class="sep"></div>
  <button class="menu-item" onclick={toggleSystemFolders}>
    <span class="glyph">{st.showSystemFolders ? "☑" : "☐"}</span>
    Show system/generated folders
  </button>
  <div class="sep"></div>
  <button class="menu-item" onclick={refresh}>Refresh</button>
</div>

<style>
  .menu {
    position: fixed;
    z-index: 100;
    min-width: 230px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 4px;
  }

  .menu-label {
    padding: 4px 8px 2px;
    font-size: 11px;
    color: var(--text-muted);
  }

  .menu-item {
    display: flex;
    align-items: center;
    gap: 7px;
    width: 100%;
    text-align: left;
    padding: 5px 8px;
    border-radius: var(--radius);
    font-size: 12.5px;
  }

  .menu-item:hover {
    background: var(--bg-hover);
  }

  .glyph {
    width: 14px;
    text-align: center;
    font-size: 11px;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .sep {
    height: 1px;
    background: var(--border);
    margin: 4px 6px;
  }
</style>
