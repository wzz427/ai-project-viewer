<script lang="ts">
  /**
   * Markdown viewer (V1.5 §86–§89): default Rendered, Source toggle
   * (read-only). Security: markdown-it runs with html:false so raw HTML is
   * escaped, never interpreted (§88, spec-003 D6); internal links open in
   * the app, http(s) go to the default browser (§89); local images are
   * swapped to cached data URLs after render (D3).
   */
  import { onMount } from "svelte";
  import MarkdownIt from "markdown-it";
  import taskLists from "markdown-it-task-lists";
  import { openUrl } from "@tauri-apps/plugin-opener";
  import CodeViewer from "./CodeViewer.svelte";
  import {
    cachedContent,
    openFile,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";
  import { readMediaFile } from "$lib/services/tauri";
  import { joinRel, TREE_ROOT } from "$lib/stores/fileTreeStore.svelte";
  import { extOf } from "$lib/services/viewerType";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const md = new MarkdownIt({
    html: false, // §88: raw HTML disabled — output is escaped
    linkify: true,
    typographer: true,
  }).use(taskLists, { enabled: false, label: true });

  const content = $derived(cachedContent(rootPath, tab.relativePath));
  const rendered = $derived(
    content?.kind === "text" ? md.render(content.text) : "",
  );

  let container = $state<HTMLElement | null>(null);

  // After render: resolve local <img> to data URLs (D3) — the src attribute
  // written by markdown-it is a project-relative path that would 404.
  $effect(() => {
    rendered; // re-run whenever the source changes
    const el = container;
    if (!el) return;
    for (const img of [...el.querySelectorAll<HTMLImageElement>("img")]) {
      const src = img.getAttribute("src");
      if (!src || /^[a-z]+:/i.test(src) || src.startsWith("/")) continue;
      const dir = tab.relativePath.includes("/")
        ? tab.relativePath.slice(0, tab.relativePath.lastIndexOf("/"))
        : TREE_ROOT;
      void readMediaFile(rootPath, joinRel(dir, src))
        .then((m) => img.setAttribute("src", m.dataUrl))
        .catch(() => img.setAttribute("alt", `[missing image: ${src}]`));
    }
  });

  function onLinkClick(e: MouseEvent) {
    const a = (e.target as HTMLElement).closest("a");
    if (!a) return;
    const href = a.getAttribute("href") ?? "";
    if (/^https?:/i.test(href)) {
      e.preventDefault();
      void openUrl(href); // default browser (§89)
      return;
    }
    if (href && !href.startsWith("#") && !/^[a-z]+:/i.test(href)) {
      e.preventDefault();
      // Internal link: resolve relative to the markdown file's folder,
      // keeping the extension routing (md → rendered, others → their viewer).
      const dir = tab.relativePath.includes("/")
        ? tab.relativePath.slice(0, tab.relativePath.lastIndexOf("/"))
        : TREE_ROOT;
      void openFile(rootPath, joinRel(dir, href));
    }
  }

  onMount(() => {
    const el = container;
    if (el) el.scrollTop = tab.scrollPosition ?? 0;
    return () => {
      if (el) tab.scrollPosition = el.scrollTop;
    };
  });

  function setMode(mode: "rendered" | "source") {
    tab.markdownMode = mode;
  }
</script>

<div class="markdown-viewer">
  <div class="mode-switch" role="toolbar" aria-label="View mode">
    <button
      class:active={tab.markdownMode !== "source"}
      onclick={() => setMode("rendered")}
    >
      Rendered
    </button>
    <button
      class:active={tab.markdownMode === "source"}
      onclick={() => setMode("source")}
    >
      Source
    </button>
  </div>

  {#if tab.markdownMode === "source"}
    <div class="source-host">
      {#if content?.kind === "text"}
        <CodeViewer {tab} text={content.text} language={extOf(tab.relativePath)} />
      {/if}
    </div>
  {:else}
    <!-- eslint-disable-next-line svelte/no-at-html-tags — markdown-it html:false output is escaped (§88) -->
    <div
      class="rendered md"
      role="presentation"
      bind:this={container}
      onclick={onLinkClick}
      onkeydown={() => {
        /* links are native <a>: Enter works; interception only reroutes the
           mouse-flow click target, keyboard activation reuses it */
      }}
    >{@html rendered}</div>
  {/if}
</div>

<style>
  .markdown-viewer {
    height: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .mode-switch {
    position: absolute;
    top: 8px;
    right: 16px;
    z-index: 5;
    display: flex;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    background: var(--bg-raised);
  }

  .mode-switch button {
    padding: 3px 10px;
    font-size: 11.5px;
    color: var(--text-muted);
  }

  .mode-switch button.active {
    background: var(--bg-active);
    color: var(--text);
  }

  .source-host {
    flex: 1;
    min-height: 0;
    padding-top: 8px;
  }

  .rendered {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 16px 24px 48px 24px;
    max-width: 860px;
    line-height: 1.65;
    font-size: 13.5px;
  }

  .rendered :global(h1) { font-size: 1.6em; margin: 0.6em 0 0.4em; }
  .rendered :global(h2) { font-size: 1.3em; margin: 0.8em 0 0.4em; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  .rendered :global(h3) { font-size: 1.12em; margin: 0.8em 0 0.3em; }
  .rendered :global(p) { margin: 0.5em 0; }
  .rendered :global(code) {
    font-family: var(--mono);
    font-size: 0.9em;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1px 5px;
  }
  .rendered :global(pre) {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
    overflow-x: auto;
  }
  .rendered :global(pre code) { background: none; border: none; padding: 0; }
  .rendered :global(table) { border-collapse: collapse; margin: 0.6em 0; }
  .rendered :global(th),
  .rendered :global(td) { border: 1px solid var(--border); padding: 4px 10px; font-size: 0.95em; }
  .rendered :global(th) { background: var(--bg); }
  .rendered :global(blockquote) {
    margin: 0.6em 0;
    padding: 2px 12px;
    border-left: 3px solid var(--border);
    color: var(--text-muted);
  }
  .rendered :global(img) { max-width: 100%; }
  .rendered :global(input[type="checkbox"]) { pointer-events: none; }
</style>
