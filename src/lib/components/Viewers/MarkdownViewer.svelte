<script module lang="ts">
  // mermaid.render ids must be unique document-wide (several markdown
  // viewers can render at once) — one counter per app, not per instance.
  let diagramSeq = 0;
</script>

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
  import { resolveDocLink } from "$lib/services/mdLinks";
  import { toast } from "$lib/stores/toastStore.svelte";
  import { t } from "$lib/i18n/t.svelte";
  import { extOf } from "$lib/services/viewerType";
  import { createMarkdownRenderer, ensureMath, mayContainMath } from "$lib/services/markdownRender";
  import ViewerToolbar from "./ViewerToolbar.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const md = createMarkdownRenderer();

  const content = $derived(cachedContent(rootPath, tab.relativePath));

  let container = $state<HTMLElement | null>(null);

  // Math engine is lazy (spec-020, memory rule): a document that may
  // contain math ($ / ```math) triggers the one-time load; bumping mathRev
  // re-renders through it. Effects created before the load resolve render
  // raw delimiters first — they re-run once `rendered` flips below.
  // Loading failures log to console only: the document stays readable
  // with literal $…$ / source.
  let mathRev = $state(0);
  $effect(() => {
    if (content?.kind !== "text" || !mayContainMath(content.text)) return;
    let live = true;
    void ensureMath(md)
      .then(() => {
        if (live) mathRev++;
      })
      .catch((e) => console.error("math engine failed to load", e));
    return () => {
      live = false;
    };
  });

  const rendered = $derived.by(() => {
    mathRev; // dependency: re-render after the engine lands
    return content?.kind === "text" ? md.render(content.text) : "";
  });

  // After render: resolve local <img> to data URLs (D3) — the src attribute
  // written by markdown-it is a project-relative path that would 404.
  // resolveDocLink canonicalizes it (spec-018): ../, %20 and root-relative
  // /paths all used to miss the cache/disk lookup.
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
      if (!src || /^[a-z]+:/i.test(src)) continue;
      const target = resolveDocLink(tab.relativePath, src);
      if (!target) continue; // anchor-only/unresolvable: leave as written
      void readMediaFile(rootPath, target)
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

  // Mermaid diagrams (spec-020): the renderer leaves escaped-source
  // placeholders; the engine (MB-scale) is dynamically imported ONLY when
  // this document actually has one (memory rule, V1.5 §6) — plain docs
  // never pay for it. Same `live` cancel semantics as the image pass: a
  // reload mid-render must not write SVG into detached old blocks.
  $effect(() => {
    rendered; // re-run whenever the source changes
    const el = container;
    if (!el) return;
    const blocks = [...el.querySelectorAll<HTMLElement>(".mermaid-block")];
    if (blocks.length === 0) return;
    let live = true;
    void renderDiagrams(blocks, () => live);
    return () => {
      live = false;
    };
  });

  async function renderDiagrams(blocks: HTMLElement[], isLive: () => boolean) {
    const mermaid = (await import("mermaid")).default;
    // Both app themes are light (paper/glacier): one stock theme fits.
    // strict = mermaid's own sanitizer on labels, no click/script hooks.
    mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "default" });
    for (const block of blocks) {
      if (!isLive()) return;
      const source = block.textContent ?? "";
      const id = `aiv-mermaid-${++diagramSeq}`;
      try {
        const { svg } = await mermaid.render(id, source);
        if (isLive() && block.isConnected) block.innerHTML = svg;
      } catch {
        // Syntax error: keep the source readable, flag the block, and drop
        // the scratch node mermaid may leave in <body> for a failed render.
        document.getElementById(`d${id}`)?.remove();
        if (isLive() && block.isConnected) block.classList.add("mermaid-error");
      }
    }
  }

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
      // Internal link: canonicalized against the document's folder
      // (spec-018 — ../, ./, %20 and root-relative / all resolve to the
      // same rel the tree produces), keeping the extension routing
      // (md → rendered, others → their viewer).
      const target = resolveDocLink(tab.relativePath, href);
      if (!target) {
        toast(t("toast.linkOutsideProject"), { kind: "error" });
        return;
      }
      void openFile(rootPath, target);
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
     AIV-MD渲染对比-demo.html): the READING surface keeps its editorial
     typography; COLORS now ride the global theme-pack tokens
     (2026-10-14): bg/text/border/muted/link all resolve per theme, and
     fence highlighting maps 1:1 onto the same --sy-* tokens the code
     viewer uses — one syntax palette app-wide. ---- */
  .rendered {
    --md-bg: var(--viewer-bg);
    --md-text: var(--text);
    --md-muted: var(--text-faint);
    --md-link: var(--accent-ink);
    --md-border: var(--viewer-border);
    /* Code surface (owner 2026-10-14 二次报障"什么色块都没有"): fences AND
       inline code ride --code-bg — a clearly visible input-family tint. The
       0.8.1 round had put raised-white here (WCAG) which is invisible
       against the paper (ΔRGB ≈ 3); the tint returns with the 2–4 failing
       syntax tokens deepened one notch app-side so AA holds on it. */
    --md-code-bg: var(--code-bg);
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
  /* Vertical rhythm tightened 2026-10-14 (owner 报障"中间空档这么大"):
     a `---` between a blockquote and a heading stacked 17+30+30+37 ≈ 138px
     of near-blank band — halves to ~85px with 0.9em hr margins + 1.35em
     h2 tops. */
  .rendered :global(h2) { font-size: 1.38em; margin: 1.35em 0 0.55em; }
  .rendered :global(h3) { font-size: 1.16em; margin: 1.2em 0 0.45em; }

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

  /* Syntax tokens (theme pack §五): the SAME --sy-* variables the
     CodeMirror viewer uses — fence code and source-mode code can never
     drift apart. Split per spec: literals (true/false/null) are the
     boolean color; plain variables fall back to document text. */
  .rendered :global(.hljs-keyword),
  .rendered :global(.hljs-selector-tag),
  .rendered :global(.hljs-meta) { color: var(--sy-keyword); }
  .rendered :global(.hljs-string),
  .rendered :global(.hljs-regexp) { color: var(--sy-string); }
  .rendered :global(.hljs-number) { color: var(--sy-number); }
  .rendered :global(.hljs-literal) { color: var(--sy-boolean); }
  .rendered :global(.hljs-comment) { color: var(--sy-comment); font-style: italic; }
  .rendered :global(.hljs-title),
  .rendered :global(.hljs-title.function_) { color: var(--sy-function); }
  .rendered :global(.hljs-attr),
  .rendered :global(.hljs-attribute),
  .rendered :global(.hljs-template-variable) { color: var(--sy-type); }
  .rendered :global(.hljs-built_in),
  .rendered :global(.hljs-type),
  .rendered :global(.hljs-title.class_) { color: var(--sy-type); }

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
    margin: 1em 0;
    padding: 0.4em 18px;
    border-left: 3px solid var(--md-link);
    color: var(--md-muted);
    font-size: 0.97em;
  }
  .rendered :global(blockquote p) { margin: 0.5em 0; color: inherit; }

  /* `---` renders as pure blank space — no glyph, no line (owner
     2026-10-16: the ❧ fleuron read as an unknown symbol). The empty
     block still gives sections breathing room via its margins. */
  .rendered :global(hr) {
    border: none;
    margin: 0.9em 0;
  }

  .rendered :global(img) { max-width: 100%; }

  /* ---- Math + diagrams (spec-020, owner 2026-11-08 "都加") ---- */
  /* KaTeX display blocks: katex.min.css centers them; this adds the
     document's vertical rhythm and keeps wide equations scrollable
     instead of overflowing the paper. */
  .rendered :global(.katex-display) {
    margin: 1.1em 0;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 2px 0;
  }

  /* Mermaid figures: framed like tables (a figure, not code) until the
     engine swaps in the SVG; until then the <pre> shows the source so
     the block is never blank while the MB-scale engine loads. */
  .rendered :global(.mermaid-block) {
    margin: 1.1em 0;
    padding: 14px 12px;
    border: 1px solid var(--md-border);
    border-radius: 6px;
    overflow-x: auto;
    text-align: center;
  }
  .rendered :global(.mermaid-block pre) {
    margin: 0;
    padding: 0;
    background: none;
    border: none;
    text-align: left;
    font-family: var(--font-mono);
    font-size: 0.86em;
  }
  .rendered :global(.mermaid-block svg) {
    max-width: 100%;
    height: auto;
  }
  .rendered :global(.mermaid-error) {
    border-style: dashed;
    text-align: left;
  }
  .rendered :global(.mermaid-error::before) {
    content: "⚠ diagram syntax error — source kept below";
    display: block;
    color: var(--md-muted);
    font-size: 0.86em;
    margin-bottom: 8px;
  }

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
