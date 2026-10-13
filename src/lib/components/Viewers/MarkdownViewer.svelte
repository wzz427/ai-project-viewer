<script lang="ts">
  /**
   * Markdown viewer (V1.5 §86–§89): default Rendered, Source toggle
   * (read-only). Security: markdown-it runs with html:false so raw HTML is
   * escaped, never interpreted (§88, spec-003 D6); internal links open in
   * the app, http(s) go to the default browser (§89); local images are
   * swapped to cached data URLs after render (D3).
   */
  import { untrack } from "svelte";
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
  import { createMarkdownRenderer } from "$lib/services/markdownRender";
  import ViewerToolbar from "./ViewerToolbar.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const md = createMarkdownRenderer();

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
    ><div class="prose">{@html rendered}</div></div>
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

  /* ---- 纸感编辑部 (owner 2026-10-13, direction C of the demo
     AIV-MD渲染对比-demo.html): the READING surface gets its own warm
     paper world — scoped here, not in app.css, because the shell and the
     code/text viewers keep the cool professional surface (spec-014).
     Contrast pairs verified ≥4.5:1 (WCAG AA) by script, recorded in
     docs/testing.md 0.7.23 row. ---- */
  .rendered {
    /* light paper */
    --md-bg: #faf8f4;
    --md-text: #2b2620;
    --md-muted: #6b6356;
    --md-link: #9a4722;
    --md-border: #e5dfd2;
    --md-code-bg: #f0ece2;
    --hl-kw: #a0431f;
    --hl-str: #566d16;
    --hl-num: #93522a;
    --hl-com: #6d6558;
    --hl-fn: #1f6b5c;
    --hl-attr: #6b5d3f;
    --hl-bi: #2e6288;
  }

  :global([data-theme="dark"]) .rendered {
    /* warm charcoal */
    --md-bg: #211f1c;
    --md-text: #ddd6cb;
    --md-muted: #a39a8b;
    --md-link: #d08c5f;
    --md-border: #3a352e;
    --md-code-bg: #1a1815;
    --hl-kw: #e89a6f;
    --hl-str: #b3c77e;
    --hl-num: #d9a05b;
    --hl-com: #8a7f6d;
    --hl-fn: #7fc4b0;
    --hl-attr: #c9b790;
    --hl-bi: #8fb8d8;
  }

  .rendered {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    background: var(--md-bg);
    color: var(--md-text);
    padding: 24px 32px 64px;
    /* +2px reading uplift: the knob keeps its 13px default for code/text
       surfaces; documents read at the demo-approved 15px and A+/A− still
       moves this in lockstep (owner 2026-13-10 demo round). */
    font-size: calc(var(--viewer-font-size) + 2px);
    line-height: 1.85;
  }

  /* Measure cap (owner 2026-10-13, revisiting the 2026-10-10 "no 860px
     column" call): 88ch centered for readable long-line rhythm — the
     paper BACKGROUND still fills the pane, so there is no blank band
     beside the text; the rejection reason is gone, not overridden. */
  .prose {
    max-width: min(88ch, 100%);
    margin: 0 auto;
  }

  /* Headings: Latin serif + CJK sans (editorial mix); hierarchy from
     family, weight and size together — never size alone. */
  .rendered :global(h1),
  .rendered :global(h2),
  .rendered :global(h3) {
    font-family: Georgia, "Times New Roman", "Segoe UI Variable Text",
      "Segoe UI", sans-serif;
    font-weight: 700;
    letter-spacing: 0.01em;
    line-height: 1.25;
  }
  .rendered :global(h1) { font-size: 1.85em; margin: 1em 0 0.6em; }
  .rendered :global(h2) { font-size: 1.38em; margin: 1.8em 0 0.6em; }
  .rendered :global(h3) { font-size: 1.16em; margin: 1.5em 0 0.45em; }

  .rendered :global(p) { margin: 0.85em 0; }
  .rendered :global(ul),
  .rendered :global(ol) { padding-left: 1.6em; margin: 0.7em 0; }
  .rendered :global(li) { margin: 0.34em 0; }

  .rendered :global(a) {
    color: var(--md-link);
    text-decoration: underline;
    text-decoration-color: color-mix(in srgb, var(--md-link) 45%, transparent);
    text-underline-offset: 3px;
  }
  .rendered :global(a:hover) { text-decoration-color: var(--md-link); }

  .rendered :global(code) {
    font-family: var(--font-mono);
    font-size: 0.88em;
    background: var(--md-code-bg);
    border-radius: 4px;
    padding: 0.15em 0.45em;
  }
  .rendered :global(pre) {
    background: var(--md-code-bg);
    border: 1px solid var(--md-border);
    border-radius: 6px;
    padding: 13px 15px;
    overflow-x: auto;
    line-height: 1.6;
  }
  .rendered :global(pre code) { background: none; padding: 0; font-size: 0.86em; }

  /* Syntax tokens (owner 2026-10-13): warm-editorial palette, contrast
     verified on --md-code-bg (see 0.7.23 row). */
  .rendered :global(.hljs-keyword),
  .rendered :global(.hljs-selector-tag),
  .rendered :global(.hljs-meta) { color: var(--hl-kw); }
  .rendered :global(.hljs-string),
  .rendered :global(.hljs-regexp) { color: var(--hl-str); }
  .rendered :global(.hljs-number),
  .rendered :global(.hljs-literal) { color: var(--hl-num); }
  .rendered :global(.hljs-comment) { color: var(--hl-com); font-style: italic; }
  .rendered :global(.hljs-title),
  .rendered :global(.hljs-title.function_) { color: var(--hl-fn); }
  .rendered :global(.hljs-attr),
  .rendered :global(.hljs-attribute),
  .rendered :global(.hljs-variable),
  .rendered :global(.hljs-template-variable) { color: var(--hl-attr); }
  .rendered :global(.hljs-built_in),
  .rendered :global(.hljs-type),
  .rendered :global(.hljs-title.class_) { color: var(--hl-bi); }

  /* Editorial tables: strong horizontal rules, no vertical cages, quiet
     zebra — books, not spreadsheets. */
  .rendered :global(table) {
    border-collapse: collapse;
    margin: 1.1em 0;
    width: auto;
  }
  .rendered :global(th),
  .rendered :global(td) {
    padding: 7px 13px;
    font-size: 0.94em;
    border: none;
    border-bottom: 1px solid var(--md-border);
    text-align: left;
  }
  .rendered :global(th) {
    font-weight: 700;
    border-top: 2px solid var(--md-text);
    border-bottom: 2px solid var(--md-text);
    background: none;
  }
  .rendered :global(tbody tr:last-child td) { border-bottom: none; }
  .rendered :global(tbody tr:nth-child(even) td) {
    background: color-mix(in srgb, var(--md-text) 3%, transparent);
  }

  .rendered :global(blockquote) {
    margin: 1.2em 0;
    padding: 0.4em 18px;
    border-left: 3px solid var(--md-link);
    color: var(--md-muted);
    font-size: 0.97em;
  }
  .rendered :global(blockquote p) { margin: 0.5em 0; color: inherit; }

  .rendered :global(hr) {
    border: none;
    text-align: center;
    margin: 2em 0;
  }
  .rendered :global(hr::after) {
    content: "❧";
    color: var(--md-muted);
    font-size: 1.2em;
  }

  .rendered :global(img) { max-width: 100%; }

  /* Task lists (owner 2026-10-02 behavior: label cursor text, checkbox
     pointer-events none — kept verbatim below); drawn checkboxes replace
     the native control, checked rows step back like a finished entry. */
  .rendered :global(label) {
    cursor: text;
  }

  .rendered :global(input[type="checkbox"]) {
    pointer-events: none;
  }

  .rendered :global(.task-list-item) {
    list-style: none;
    margin-left: -1.4em;
  }
  .rendered :global(.task-list-item label) {
    display: flex;
    gap: 8px;
    align-items: baseline;
  }
  .rendered :global(.task-list-item input[type="checkbox"]) {
    appearance: none;
    width: 15px;
    height: 15px;
    border: 1.5px solid var(--md-muted);
    border-radius: 2px;
    flex: none;
    transform: translateY(2px);
    background: transparent;
  }
  .rendered :global(.task-list-item input[type="checkbox"]:checked) {
    background: var(--md-link);
    border-color: var(--md-link);
  }
  .rendered :global(.task-list-item input[type="checkbox"]:checked::after) {
    content: "✓";
    color: var(--md-bg);
    font-size: 12px;
    display: block;
    margin: -2px 0 0 1px;
  }
  .rendered :global(.task-list-item:has(input:checked)) {
    color: var(--md-muted);
  }
</style>
