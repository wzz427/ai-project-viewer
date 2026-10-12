<script lang="ts">
  /**
   * Markdown viewer (V1.5 §86–§89): default Rendered, Source toggle
   * (read-only). Security: markdown-it runs with html:false so raw HTML is
   * escaped, never interpreted (§88, spec-003 D6); internal links open in
   * the app, http(s) go to the default browser (§89); local images are
   * swapped to cached data URLs after render (D3).
   */
  import { untrack } from "svelte";
  import MarkdownIt from "markdown-it";
  import taskLists from "markdown-it-task-lists";
  import { openUrl } from "@tauri-apps/plugin-opener";
  import CodeViewer from "./CodeViewer.svelte";
  import {
    cachedContent,
    openFile,
    saveScrollPosition,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";
  import { readMediaFile } from "$lib/services/tauri";
  import { joinRel, TREE_ROOT } from "$lib/stores/fileTreeStore.svelte";
  import { extOf } from "$lib/services/viewerType";
  import ViewerToolbar from "./ViewerToolbar.svelte";

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
    // Cancel semantics (spec-012 L-f8): a watcher reload re-runs this
    // effect while the previous round's readMediaFile promises may still be
    // in flight; without the flag their callbacks kept writing to detached
    // old <img> elements (wasted IPC, stale bitmaps).
    let live = true;
    for (const img of [...el.querySelectorAll<HTMLImageElement>("img")]) {
      const src = img.getAttribute("src");
      if (!src || /^[a-z]+:/i.test(src) || src.startsWith("/")) continue;
      const dir = tab.relativePath.includes("/")
        ? tab.relativePath.slice(0, tab.relativePath.lastIndexOf("/"))
        : TREE_ROOT;
      void readMediaFile(rootPath, joinRel(dir, src))
        .then((m) => {
          if (live) img.setAttribute("src", m.dataUrl);
        })
        .catch(() => {
          if (live) img.setAttribute("alt", `[missing image: ${src}]`);
        });
    }
    return () => {
      live = false;
    };
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

  // Scroll save/restore for the RENDERED pane (spec-012 M3). It must live
  // in an effect keyed on markdownMode+container: a mode switch rebinds a
  // NEW element (the old onMount closure kept the first one forever), so
  // Rendered→Source→back restored nothing — and switching away while in
  // Source mode wrote the dead element's scrollTop 0 over the position
  // CodeViewer had just saved. Source mode saves its own via CodeViewer.
  $effect(() => {
    if (tab.markdownMode !== "rendered") return;
    const el = container;
    if (!el) return;
    el.scrollTop = untrack(() => tab.scrollPosition) ?? 0;
    return () => {
      saveScrollPosition(rootPath, tab.relativePath, el.scrollTop);
    };
  });

  // ---- toolbar find over the RENDERED text (SPEC-INFRA-003): TreeWalker
  // collects matches as text-node offsets; jump selects the hit and scrolls
  // its containing block into view (page-navigation grade, like the PDF).
  function collectMatches(q: string): { node: Text; start: number }[] {
    const el = container;
    if (!el || !q) return [];
    const needle = q.toLowerCase();
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const out: { node: Text; start: number }[] = [];
    let n: Node | null = walker.nextNode();
    while (n) {
      const text = n.nodeValue?.toLowerCase() ?? "";
      let i = text.indexOf(needle);
      while (i !== -1) {
        out.push({ node: n as Text, start: i });
        i = text.indexOf(needle, i + Math.max(1, needle.length));
      }
      n = walker.nextNode();
    }
    return out;
  }

  const findApi = {
    count: (q: string) => collectMatches(q).length,
    jump: (q: string, index: number) => {
      const hit = collectMatches(q)[index];
      if (!hit) return;
      const range = document.createRange();
      range.setStart(hit.node, hit.start);
      range.setEnd(hit.node, hit.start + q.length);
      const block = hit.node.parentElement?.closest(
        "p, li, h1, h2, h3, h4, pre, blockquote, td, th",
      );
      (block ?? hit.node.parentElement)?.scrollIntoView({ block: "center" });
      const sel = document.getSelection();
      sel?.removeAllRanges();
      sel?.addRange(range);
    },
  };

</script>

<div class="markdown-viewer">
  <!-- View mode toggles via the file tab's right-click menu (owner item 5);
       no floating overlay. Source mode gets its toolbar from the embedded
       CodeViewer, rendered mode mounts its own. -->
  {#if tab.markdownMode === "source"}
    <div class="source-host">
      {#if content?.kind === "text"}
        <CodeViewer {rootPath} {tab} text={content.text} language={extOf(tab.relativePath)} />
      {/if}
    </div>
  {:else}
    <ViewerToolbar {findApi} />
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


  .source-host {
    flex: 1;
    min-height: 0;
  }

  .rendered {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 16px 24px 48px 24px;
    /* No max-width cap (owner 2026-10-10 round 2): an 860px column leaves
       an obviously blank band beside the text on a wide window — centered
       or not. The text area fills the viewer; readability is the reader's
       call via the toolbar font size. */
    line-height: 1.65;
    font-size: var(--viewer-font-size);
  }

  .rendered :global(h1) { font-size: 1.6em; margin: 0.6em 0 0.4em; }
  .rendered :global(h2) { font-size: 1.3em; margin: 0.8em 0 0.4em; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  .rendered :global(h3) { font-size: 1.12em; margin: 0.8em 0 0.3em; }
  .rendered :global(p) { margin: 0.5em 0; }
  .rendered :global(code) {
    font-family: var(--font-mono);
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
  /* Task lists (owner 2026-10-02): label/input are form controls — the
     browser gives them a default arrow cursor that does NOT inherit, and
     pressing a label focuses the checkbox and kills the selection. */
  .rendered :global(label) {
    cursor: text;
  }

  .rendered :global(input[type="checkbox"]) {
    pointer-events: none;
  }

  .rendered :global(blockquote) {
    margin: 0.6em 0;
    padding: 2px 12px;
    border-left: 3px solid var(--border);
    color: var(--text-muted);
  }
  .rendered :global(img) { max-width: 100%; }
  .rendered :global(input[type="checkbox"]) { pointer-events: none; }
</style>
