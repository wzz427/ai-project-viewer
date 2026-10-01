<script lang="ts">
  /**
   * PDF viewer (V1.5 §91–§96, spec-005). PDF.js over the bytes channel
   * (D2); the library and its worker load on first open only (§94, D1);
   * pages render as canvases in one continuous scroller, virtualized to
   * visible ± ADJACENT pages (§95); unmount destroys the document and
   * cancels render tasks (§96), leaving only tab.pdfState behind (§93).
   *
   * Search is page-navigation grade (D5): match list + next/previous;
   * character-level highlight boxes would need the full text layer and
   * are out of V1 scope.
   */
  import { onMount } from "svelte";
  import {
    cachedContent,
    savePdfState,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";
  import {
    acquireLib,
    releaseEngineIfIdle,
  } from "$lib/services/pdfEngine";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const cached = $derived(cachedContent(rootPath, tab.relativePath));
  const data = $derived(cached?.kind === "pdf" ? cached.data : null);

  type PdfDoc = import("pdfjs-dist").PDFDocumentProxy;
  type PdfPage = import("pdfjs-dist").PDFPageProxy;
  type PdfTask = import("pdfjs-dist").PDFDocumentLoadingTask;

  // Plain let on purpose: pdf.js objects must never enter the reactive
  // system — Svelte's deep proxy wraps their internals (private fields,
  // Maps) and pdf.js then dies with "getOrInsertComputed is not a
  // function". UI re-renders are driven by the $state fields below
  // (totalPages/baseW/loadError), all assigned when the document lands.
  // svelte-ignore non_reactive_update
  let doc: PdfDoc | null = null;
  let task: PdfTask | null = null;
  let loadError = $state("");
  let totalPages = $state(0);
  /** Base page size from page 1 — placeholder geometry for all slots. */
  let baseW = $state(0);
  let baseH = $state(0);

  // Seed once from the restored session state (§93); later writes flow
  // through savePdfState instead. (ignore on each line below)
  // svelte-ignore state_referenced_locally
  let scale = $state(tab.pdfState?.zoom ?? 1);
  // svelte-ignore state_referenced_locally
  let zoomMode = $state(tab.pdfState?.zoomMode ?? "fit-width");
  // svelte-ignore state_referenced_locally
  let currentPage = $state(tab.pdfState?.page ?? 1);

  let scroller = $state<HTMLElement | null>(null);
  /** page number (1-based) -> canvas holder element. */
  const slots = new Map<number, HTMLDivElement>();
  const renderedPages = new Set<number>();
  let observer: IntersectionObserver | null = null;
  const ADJACENT = 2;

  const pxW = $derived(Math.round(baseW * scale));
  const pxH = $derived(Math.round(baseH * scale));

  // ---------- load document ----------
  $effect(() => {
    const buf = data;
    if (!buf) return;
    let cancelled = false;
    void (async () => {
      try {
        const pdfjs = await acquireLib();
        // getDocument transfers/detaches its input — hand it a copy so the
        // cache copy stays reusable across tab switches.
        const t = pdfjs.getDocument({ data: buf.slice(0) });
        const d = await t.promise;
        if (cancelled) {
          void t.destroy();
          return;
        }
        task = t;
        doc = d;
        totalPages = d.numPages;
        const first = await d.getPage(1);
        if (cancelled) return;
        const vp = first.getViewport({ scale: 1 });
        baseW = vp.width;
        baseH = vp.height;
      } catch (e) {
        if (!cancelled) loadError = String(e);
      }
    })();
    return () => {
      cancelled = true;
    };
  });

  // ---------- release on unmount (§96) ----------
  onMount(() => {
    return () => {
      observer?.disconnect();
      observer = null;
      slots.clear();
      renderedPages.clear();
      persistState();
      // v6: destroy() lives on the loading task; cleanup() frees page
      // caches on the proxy. Both together = §96 release.
      void doc?.cleanup().catch(() => {});
      void task?.destroy();
      task = null;
      doc = null;
      // Owner 2026-10-02: closing the last pdf tab unloads the engine
      // (worker thread) entirely; a no-op while other pdf tabs remain.
      releaseEngineIfIdle();
    };
  });

  function persistState() {
    savePdfState(rootPath, tab.relativePath, {
      page: currentPage,
      zoom: scale,
      zoomMode,
      scrollPosition: scroller?.scrollTop,
    });
  }

  // ---------- fit modes ----------
  function refit() {
    if (!scroller || !baseW || zoomMode === "custom") return;
    const availW = scroller.clientWidth - 32;
    const availH = scroller.clientHeight - 32;
    if (zoomMode === "fit-width") {
      scale = availW / baseW;
    } else if (zoomMode === "fit-page") {
      scale = Math.min(availW / baseW, availH / baseH);
    }
  }

  // (Re)fit when geometry or viewport changes. baseW > 0 IS the
  // readiness signal: doc is a plain variable now, so guarding on it here
  // would drop baseW from the dependency set on the first (early-return)
  // run and this effect would never re-fire.
  $effect(() => {
    if (!baseW || !scroller) return;
    refit();
  });

  function setZoomMode(mode: "fit-width" | "fit-page") {
    zoomMode = mode;
    keepPageAnchored(() => refit());
  }

  function zoomBy(factor: number) {
    zoomMode = "custom";
    keepPageAnchored(() => {
      scale = Math.min(5, Math.max(0.1, scale * factor));
    });
  }

  // Keep the current page roughly in view while the layout reflows.
  let anchorTimer: ReturnType<typeof setTimeout> | undefined;
  function keepPageAnchored(apply: () => void) {
    const page = currentPage;
    apply();
    clearTimeout(anchorTimer);
    anchorTimer = setTimeout(() => {
      scrollToPage(page, "start");
      scheduleRender();
    }, 30);
  }

  // ---------- virtualized rendering (§95) ----------
  // renderedScale records the zoom each canvas was painted at: a scale
  // change does NOT wipe the set (that killed in-flight re-renders), it
  // just makes every page "stale" so the next pass re-paints it.
  const renderedScale = new Map<number, number>();

  function scheduleRender() {
    requestAnimationFrame(() => renderVisible());
  }

  function renderVisible() {
    if (!doc || !scroller) return;
    const first = Math.max(1, currentPage - ADJACENT);
    const last = Math.min(totalPages, currentPage + ADJACENT);
    for (const p of [...renderedPages]) {
      if (p < first || p > last) releasePage(p);
    }
    for (let p = first; p <= last; p++) {
      if (renderedScale.get(p) === scale) continue; // painted at current zoom
      void renderPage(p);
    }
  }

  async function renderPage(pageNo: number) {
    const d = doc;
    const host = slots.get(pageNo);
    if (!d || !host) return;
    renderedPages.add(pageNo);
    try {
      const page: PdfPage = await d.getPage(pageNo);
      // Ownership re-check after every await: releases (window move, zoom
      // reflow) delete the page from renderedPages — a render that
      // outlived its own release must not re-attach a stale canvas.
      if (doc !== d || !renderedPages.has(pageNo)) return;
      const vp = page.getViewport({ scale });
      const canvas = document.createElement("canvas");
      canvas.width = Math.floor(vp.width);
      canvas.height = Math.floor(vp.height);
      canvas.className = "pdf-canvas";
      host.replaceChildren(canvas);
      await page.render({
        canvas,
        canvasContext: canvas.getContext("2d") ?? undefined,
        viewport: vp,
      }).promise;
      if (doc !== d || !renderedPages.has(pageNo)) {
        host.replaceChildren();
        return;
      }
      renderedScale.set(pageNo, scale);
    } catch (e) {
      console.info("[aiv-pdf] STACK", pageNo, e instanceof Error && e.stack ? e.stack.split("\n").slice(0, 6).join(" | ") : String(e));
      // cancelled render (zoom churn / destroy) — clear the slot so DOM
      // stays in sync with renderedPages; the next pass re-renders it.
      if (doc === d) {
        releasePage(pageNo);
      }
    }
  }

  function releasePage(pageNo: number) {
    renderedPages.delete(pageNo);
    renderedScale.delete(pageNo);
    slots.get(pageNo)?.replaceChildren();
  }

  // Zoom changes re-paint pages at the new size (renderVisible skips
  // pages whose recorded scale still matches).
  $effect(() => {
    scale;
    if (!doc) return;
    scheduleRender();
  });

  // ---------- scroll bookkeeping ----------
  let scrollTimer: ReturnType<typeof setTimeout> | undefined;
  function onScroll() {
    if (!scroller) return;
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      persistState();
    }, 300);
    updateCurrentPageFromScroll();
  }

  function updateCurrentPageFromScroll() {
    if (!scroller || pxH === 0) return;
    currentPage = Math.min(
      totalPages,
      Math.max(1, Math.round(scroller.scrollTop / pxH) + 1),
    );
    scheduleRender();
  }

  function scrollToPage(pageNo: number, where: "start" = "start") {
    if (!scroller || pxH === 0) return;
    const clamped = Math.min(totalPages, Math.max(1, pageNo));
    scroller.scrollTo({ top: (clamped - 1) * pxH, behavior: "auto" });
    currentPage = clamped;
    persistState();
  }

  function go(delta: number) {
    scrollToPage(currentPage + delta);
  }

  function jumpTo(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const n = parseInt(input.value, 10);
    if (Number.isFinite(n)) scrollToPage(n);
    input.value = String(currentPage);
  }

  // Ctrl+wheel zoom (§92).
  function onWheel(e: WheelEvent) {
    if (!e.ctrlKey) return;
    e.preventDefault();
    zoomBy(e.deltaY < 0 ? 1.1 : 1 / 1.1);
  }

  // ---------- search (page-navigation grade, D5) ----------
  let query = $state("");
  let matches = $state<{ page: number }[]>([]);
  let matchIdx = $state(-1);
  let searching = $state(false);

  async function runSearch() {
    const q = query.trim().toLowerCase();
    matches = [];
    matchIdx = -1;
    if (!q || !doc) return;
    searching = true;
    try {
      const found: { page: number }[] = [];
      for (let p = 1; p <= doc.numPages; p++) {
        const page = await doc.getPage(p);
        const text = await page.getTextContent();
        const sheet = text.items
          .map((it) => ("str" in it ? it.str : ""))
          .join(" ")
          .toLowerCase();
        if (sheet.includes(q)) found.push({ page: p });
      }
      matches = found;
      if (found.length > 0) {
        matchIdx = 0;
        scrollToPage(found[0].page);
      }
    } finally {
      searching = false;
    }
  }

  function nextMatch(dir: 1 | -1) {
    if (matches.length === 0) return;
    matchIdx = (matchIdx + dir + matches.length) % matches.length;
    scrollToPage(matches[matchIdx].page);
  }

  // Mount the slot map + observer once pages exist.
  function registerSlot(el: HTMLDivElement, pageNo: number) {
    slots.set(pageNo, el);
    return {
      destroy() {
        slots.delete(pageNo);
      },
    };
  }

  $effect(() => {
    if (!totalPages || !scroller) return;
    observer?.disconnect();
    observer = new IntersectionObserver(
      (entries) => {
        for (const en of entries) {
          const pageNo = Number((en.target as HTMLElement).dataset.page);
          if (en.isIntersecting && renderedPages.has(pageNo) === false) {
            // Pages entering view outside the ±buffer window still render
            // only when they become the current neighborhood.
          }
        }
        updateCurrentPageFromScroll();
      },
      { root: scroller, rootMargin: "150% 0px" },
    );
    for (const el of slots.values()) observer.observe(el);
    // Restore scroll position from the session state (§93).
    if (tab.pdfState?.scrollPosition && pxH > 0) {
      scroller.scrollTop = tab.pdfState.scrollPosition;
    } else if (tab.pdfState?.page) {
      scroller.scrollTop = (tab.pdfState.page - 1) * pxH;
    }
    updateCurrentPageFromScroll();
  });

  const zoomPercent = $derived(`${Math.round(scale * 100)}%`);
</script>

<div class="pdf-viewer">
  <div class="toolbar">
    <button class="tb" onclick={() => go(-1)} disabled={currentPage <= 1} aria-label="Previous page">‹</button>
    <input
      class="page-no"
      type="number"
      min="1"
      max={totalPages}
      value={currentPage}
      onchange={jumpTo}
      aria-label="Page number"
    />
    <span class="tb-label">/ {totalPages}</span>
    <button class="tb" onclick={() => go(1)} disabled={currentPage >= totalPages} aria-label="Next page">›</button>

    <span class="sep"></span>
    <button class="tb" onclick={() => zoomBy(1 / 1.2)} aria-label="Zoom out">−</button>
    <span class="tb-label mono">{zoomPercent}</span>
    <button class="tb" onclick={() => zoomBy(1.2)} aria-label="Zoom in">+</button>
    <button class="tb" class:on={zoomMode === "fit-width"} onclick={() => setZoomMode("fit-width")}>Fit Width</button>
    <button class="tb" class:on={zoomMode === "fit-page"} onclick={() => setZoomMode("fit-page")}>Fit Page</button>

    <span class="grow"></span>
    <input
      class="search"
      type="search"
      placeholder="Find in document…"
      bind:value={query}
      onkeydown={(e) => e.key === "Enter" && runSearch()}
      aria-label="Search document"
    />
    {#if searching}
      <span class="tb-label">…</span>
    {:else if matches.length > 0}
      <span class="tb-label">{matchIdx + 1} / {matches.length}</span>
      <button class="tb" onclick={() => nextMatch(-1)} aria-label="Previous match">‹</button>
      <button class="tb" onclick={() => nextMatch(1)} aria-label="Next match">›</button>
    {:else if query.trim() && !searching}
      <span class="tb-label">0 results</span>
    {/if}
  </div>

  <div
    class="scroller"
    bind:this={scroller}
    onscroll={onScroll}
    onwheel={onWheel}
    onresize={() => refit()}
  >
    {#if loadError}
      <div class="message error">Cannot render PDF: {loadError}</div>
    {:else if totalPages === 0}
      <!-- totalPages ($state) is the branch driver: `doc` is a plain
           variable now, so it alone could never flip this branch. -->
      <div class="message">Loading…</div>
    {:else}
      <div class="pages" style:width={`${pxW}px`}>
        {#each Array(totalPages) as _, i (i)}
          <div
            class="page-slot"
            data-page={i + 1}
            style:height={`${pxH}px`}
            use:registerSlot={i + 1}
          ></div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .pdf-viewer {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--viewer-bg);
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .tb {
    padding: 2px 8px;
    border-radius: var(--radius);
    font-size: 12px;
    color: var(--text-muted);
  }

  .tb:hover:not(:disabled) {
    background: var(--bg-hover);
  }

  .tb:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .tb.on {
    background: var(--bg-active);
    color: var(--text);
  }

  .tb-label {
    font-size: 12px;
    color: var(--text-muted);
    padding: 0 2px;
  }

  .page-no {
    width: 44px;
    padding: 2px 4px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 12px;
    text-align: center;
    background: var(--bg);
    color: var(--text);
  }

  .search {
    width: 180px;
    padding: 2px 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 12px;
    background: var(--bg);
    color: var(--text);
  }

  .sep {
    width: 1px;
    height: 16px;
    background: var(--border);
    margin: 0 4px;
  }

  .grow {
    flex: 1;
  }

  .scroller {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }

  .pages {
    margin: 16px auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .page-slot {
    background: white;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
    overflow: hidden;
    display: flex;
    justify-content: center;
  }

  .pages :global(.pdf-canvas) {
    display: block;
  }

  .message {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 12px;
  }

  .message.error {
    color: var(--danger, #e5484d);
  }
</style>
