<script lang="ts">
  /**
   * File-tab context menu: view-mode toggles for Markdown/JSON (owner
   * 2026-10-01, §197 revision), Keep Open (pin), and the spec-006 handoff
   * block (Notepad / VS Code / Explorer / Copy paths — same shared builder
   * as the tree menu so the two surfaces cannot drift).
   */
  import {
    closeFile,
    setJsonMode,
    setMarkdownMode,
    setTabPinned,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";
  import { fileHandoffGroups } from "$lib/services/handoffMenu";
  import { fileNameOf } from "$lib/services/viewerType";

  let {
    rootPath,
    tab,
    x,
    y,
    onclose,
  }: {
    rootPath: string;
    tab: RuntimeTab;
    x: number;
    y: number;
    onclose: () => void;
  } = $props();

  // Snapshot semantics (lessons L12): the built groups carry plain strings,
  // so entries keep running safely after onclose unmounts this menu.
  const groups = $derived(
    fileHandoffGroups(
      rootPath,
      tab.relativePath,
      fileNameOf(tab.relativePath),
      false,
      { includeOpen: false },
    ),
  );

  let el = $state<HTMLElement | null>(null);

  // Clamp inside the viewport once mounted (menu was clipped at the
  // bottom-left window edge before, owner 2026-10-10).
  let left = $state(0);
  let top = $state(0);
  $effect(() => {
    if (!el) return;
    ({ left, top } = clampMenu(el, x, y));
  });

  function close(e?: Event) {
    if (e && e.target instanceof Node && el?.contains(e.target)) return;
    onclose();
  }

  $effect(() => {
    window.addEventListener("mousedown", close, { capture: true });
    return () =>
      window.removeEventListener("mousedown", close, { capture: true });
  });
  import { clampMenu } from "$lib/components/ContextMenu/menuPosition";

  function act(fn: () => void) {
    // Run BEFORE onclose(): closing unmounts this menu, and reading props
    // (tab.markdownMode…) from an unmounted component throws — the original
    // order silently swallowed every mode-toggle click (2026-10-01 round).
    fn();
    onclose();
  }
</script>

<div class="menu" bind:this={el} style="left: {left}px; top: {top}px">
  {#if tab.viewerType === "markdown"}
    <button
      class="menu-item"
      onclick={() =>
        act(() =>
          setMarkdownMode(
            rootPath,
            tab.relativePath,
            tab.markdownMode === "source" ? "rendered" : "source",
          ))}
    >
      {tab.markdownMode === "source" ? "View Rendered" : "View Source"}
    </button>
  {/if}
  {#if tab.viewerType === "json"}
    <button
      class="menu-item"
      onclick={() =>
        act(() =>
          setJsonMode(
            rootPath,
            tab.relativePath,
            tab.jsonMode === "source" ? "formatted" : "source",
          ))}
    >
      {tab.jsonMode === "source" ? "View Formatted" : "View Source"}
    </button>
  {/if}
  {#if tab.viewerType === "markdown" || tab.viewerType === "json"}
    <div class="sep"></div>
  {/if}
  <button class="menu-item" onclick={() => act(() => setTabPinned(rootPath, tab.relativePath, !tab.pinned))}>
    {tab.pinned ? "Unpin Tab" : "Pin Tab"}
  </button>
  {#each groups as group, gi}
    <div class="sep"></div>
    {#each group as entry (entry.id)}
      <button
        class="menu-item"
        data-menu-id={entry.id}
        onclick={() => {
          void entry.run();
          onclose();
        }}
      >{entry.label}</button>
    {/each}
  {/each}
  <div class="sep"></div>
  <button class="menu-item" onclick={() => act(() => closeFile(rootPath, tab.relativePath))}>
    Close Tab
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

  .sep {
    height: 1px;
    background: var(--border);
    margin: 4px 6px;
  }
</style>
