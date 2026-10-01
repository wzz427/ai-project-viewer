<script lang="ts">
  /**
   * File-tab context menu (owner 2026-10-01 items 5/8/10): view-mode toggle
   * for Markdown/JSON lives here instead of a floating overlay; Keep Open
   * (pin) stops preview replacement; Open with Default App hands media (or
   * anything not viewable in-app) to the OS-associated player directly —
   * never the file manager.
   */
  import {
    closeFile,
    setJsonMode,
    setMarkdownMode,
    setTabPinned,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";
  import { openWithDefaultApp } from "$lib/services/tauri";
  import { toast } from "$lib/stores/toastStore.svelte";

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

  function act(fn: () => void) {
    // Run BEFORE onclose(): closing unmounts this menu, and reading props
    // (tab.markdownMode…) from an unmounted component throws — the original
    // order silently swallowed every mode-toggle click (2026-10-01 round).
    fn();
    onclose();
  }

  function openDefault() {
    openWithDefaultApp(rootPath, tab.relativePath).catch((err) =>
      toast(`Cannot open: ${err}`, { kind: "error" }),
    );
  }
</script>

<div class="menu" bind:this={el} style="left: {x}px; top: {y}px">
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
    {tab.pinned ? "Unpin Tab" : "Keep Tab Open"}
  </button>
  <button class="menu-item" onclick={() => act(openDefault)}>
    Open with Default App
  </button>
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
