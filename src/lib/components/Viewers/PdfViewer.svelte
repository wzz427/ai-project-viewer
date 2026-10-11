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
  import { registerFindFocus, unregisterFindFocus } from "./activeFind";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const cached = $derived(cachedContent(rootPath, tab.relativePath));
  const data = $derived(cached?.kind === "pdf" ? cached.data : null);

  type PdfLib = typeof import("pdfjs-dist/legacy/build/pdf.mjs");
  type PdfDoc = import("pdfjs-dist").PDFDocumentProxy;
  type PdfPage = import("pdfjs-dist").PDFPageProxy;
  type PdfTask = import("pdfjs-dist").PDFDocumentLoadingTask;
  type PdfRenderTask = import("pdfjs-dist").RenderTask;

  // Plain lets on purpose: pdf.js objects must never enter the reactive
  // system — Svelte's deep proxy wraps their internals (private fields,
  // Maps) and pdf.js then dies with "getOrInsertComputed is not a
  // function". UI re-renders are driven by the $state fields below
  // (totalPages/baseW/loadError), all assigned when the document lands.
  // svelte-ignore non_reactive_update
  let doc: PdfDoc | null = null;
  let task: PdfTask | null = null;
  // svelte-ignore non_reactive_update
  let lib: PdfLib | null = null;
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
  let searchInput: HTMLInputElement | undefined = $state();
  /** page number (1-based) -> canvas holder element. */
  const slots = new Map<number, HTMLDivElement>();
  const renderedPages = new Set<number>();
  /** Canvas renders still in flight (spec-012 M7): keyed by page — a
   * re-render of the same page (zoom churn) cancels the stale one instead
   * of stacking a second canvas+textLayer job, and release/unmount cancel
   * whatever is still pending. Bounded by the render window (±ADJACENT). */
  const activeRenders = new Map<number, PdfRenderTask>();
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
        lib = pdfjs;
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

  // svelte-ignore non_reactive_update
  let activeDriver: (() => void) | null = null;

  // ---------- release on unmount (§96) ----------
  onMount(() => {
    // Ctrl+F lands on this document's own search box (SPEC-INFRA-003).
    const focus = () => searchInput?.focus();
    registerFindFocus(focus);
    // Selection-shield state (see renderPage) must drop wherever the
    // gesture ends — including a release outside this window.
    const clearSelecting = () => {
      document
        .querySelectorAll(".pdf-text-layer.selecting")
        .forEach((el) => el.classList.remove("selecting"));
    };
    window.addEventListener("pointerup", clearSelecting);
    window.addEventListener("blur", clearSelecting);
    return () => {
      unregisterFindFocus(focus);
      window.removeEventListener("pointerup", clearSelecting);
      window.removeEventListener("blur", clearSelecting);
      activeDriver?.();
      observer?.disconnect();
      observer = null;
      // Late timers must not fire after teardown: a scroll scheduled <300 ms
      // before the switch used to land on a null scroller and overwrite the
      // saved scroll position with undefined (spec-012 M9); the anchor timer
      // does scrollToPage → persistState on the same torn-down path.
      clearTimeout(scrollTimer);
      clearTimeout(anchorTimer);
      // Cancel canvas renders still pending before destroying the doc (M7).
      searchGen++;
      for (const t of activeRenders.values()) t.cancel();
      activeRenders.clear();
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
      // ?? only rescues the null-scroller teardown case (M9): a live
      // scroller legitimately reads 0 at the very top.
      scrollPosition: scroller?.scrollTop ?? lastScrollTop,
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

  // Window resizes must re-run fit-width/fit-page. The DOM 'resize' event
  // never fires on elements, so an onresize attribute on the scroller is
  // dead code — watch the scroller box instead (owner 2026-10-10: PDF
  // opened in a smaller window kept its stale fit after maximizing,
  // leaving a wide blank beside the page).
  $effect(() => {
    const el = scroller;
    if (!el) return;
    const obs = new ResizeObserver(() => refit());
    obs.observe(el);
    return () => obs.disconnect();
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
    if (!d || !host || !lib) return;
    const pdfjs = lib;
    renderedPages.add(pageNo);
    // A render still in flight for this page is stale the moment a new one
    // is requested (zoom churn) — cancel it instead of painting twice (M7).
    activeRenders.get(pageNo)?.cancel();
    let renderTask: PdfRenderTask | null = null;
    try {
      const page: PdfPage = await d.getPage(pageNo);
      // Ownership re-check after every await: releases (window move, zoom
      // reflow) delete the page from renderedPages — a render that
      // outlived its own release must not re-attach a stale canvas.
      if (doc !== d || !renderedPages.has(pageNo)) return;
      const vp = page.getViewport({ scale });
      // Hi-DPI: canvas backing store = viewport × devicePixelRatio with an
      // explicit CSS size, the official viewer recipe. The text layer's
      // --total-scale-factor must equal the SAME CSS scale or every span
      // box misaligns with the painted glyphs and a one-line drag selects
      // half the page (owner 2026-10-09).
      const dpr = window.devicePixelRatio || 1;
      const canvas = document.createElement("canvas");
      canvas.width = Math.floor(vp.width * dpr);
      canvas.height = Math.floor(vp.height * dpr);
      canvas.style.width = `${Math.floor(vp.width)}px`;
      canvas.style.height = `${Math.floor(vp.height)}px`;
      canvas.className = "pdf-canvas";
      // Text layer (owner 2026-10-02: canvas text must be selectable):
      // invisible spans exactly aligned with the painted glyphs; the
      // browser selection + ::selection highlight then work on the page.
      const textLayer = document.createElement("div");
      textLayer.className = "pdf-text-layer";
      textLayer.style.setProperty("--total-scale-factor", String(scale));
      host.replaceChildren(canvas, textLayer);
      renderTask = page.render({
        canvas,
        canvasContext: canvas.getContext("2d") ?? undefined,
        viewport: vp,
        transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined,
      });
      activeRenders.set(pageNo, renderTask);
      await renderTask.promise;
      await new pdfjs.TextLayer({
        textContentSource: page.streamTextContent(),
        container: textLayer,
        viewport: vp,
      }).render();
      if (doc !== d || !renderedPages.has(pageNo)) {
        host.replaceChildren();
        return;
      }
      // Official viewer's endOfContent (pdf_viewer.mjs #bindMouse): a
      // user-select:none slab pinned at the layer bottom that covers the
      // layer (below the spans, z-index 0) while a selection drag is
      // active. Without it, a drag into blank page area lands its focus on
      // the container itself and the selection wraps around everything.
      // Chromium >= 148 skips the official endOfContent repositioning
      // dance, so class toggle + CSS is the faithful port on WebView2 155.
      const endOfContent = document.createElement("div");
      endOfContent.className = "pdf-end-of-content";
      textLayer.append(endOfContent);
      // Selection driver (owner 2026-10-09, fourth round): the native drag
      // wraps its extent — and even its ANCHOR — to the document edges
      // whenever the pointer crosses text-free blank (pdf.js spans carry no
      // line boxes; the official viewer exhibits the same wrap). So the
      // drag is ours end to end: the anchor is pinned at the press point
      // and every frame the extent is set to the caret of the nearest text
      // row, clamped into that row. Double/triple clicks and shift-extend
      // stay native.
      textLayer.addEventListener("mousedown", (e) => {
        if (e.button !== 0 || e.shiftKey || e.detail >= 2) return;
        const el = e.target;
        if (!(el instanceof HTMLElement) || el.tagName !== "SPAN") return;
        textLayer.classList.add("selecting");
        const caretAt = (x: number, y: number): Range | null => {
          const d = document as Document & {
            caretRangeFromPoint?: (x: number, y: number) => Range | null;
          };
          return d.caretRangeFromPoint?.(x, y) ?? null;
        };
        // Pin the anchor: clamp the press point into the pressed span's
        // text zone (the hit-padding strips carry no text nodes, so a
        // press beside the line must snap onto the line).
        const pr = el.getBoundingClientRect();
        const a = caretAt(
          Math.min(Math.max(e.clientX, pr.left + 22), pr.right - 22),
          Math.min(Math.max(e.clientY, pr.top + 1), pr.bottom - 1));
        if (!a) return;
        const anchorNode = a.startContainer;
        const anchorOffset = a.startOffset;
        // Rows across ALL rendered pages (span boxes include the pads), so
        // a drag that crosses a page boundary keeps extending.
        interface Row {
          top: number; bottom: number; left: number; right: number; cy: number;
        }
        const rowsNow = (): Row[] => {
          const rows: Row[] = [];
          for (const s of document.querySelectorAll<HTMLElement>(
            ".pdf-text-layer span")) {
            const r = s.getBoundingClientRect();
            if (r.width === 0) continue;
            const cy = r.top + r.height / 2;
            const row = rows.find((w) => Math.abs(w.cy - cy) < r.height * 0.6);
            if (row) {
              row.left = Math.min(row.left, r.left);
              row.right = Math.max(row.right, r.right);
              row.top = Math.min(row.top, r.top);
              row.bottom = Math.max(row.bottom, r.bottom);
            } else {
              rows.push({
                top: r.top, bottom: r.bottom,
                left: r.left, right: r.right, cy,
              });
            }
          }
          return rows;
        };
        const clampAt = (x: number, y: number) => {
          const sel = document.getSelection();
          const rows = rowsNow();
          if (!sel || rows.length === 0) return;
          let row = rows[0];
          for (const w of rows) {
            if (Math.abs(w.cy - y) < Math.abs(row.cy - y)) row = w;
          }
          const cx = Math.min(Math.max(x, row.left + 22), row.right - 22);
          const cy = Math.min(Math.max(y, row.top + 1), row.bottom - 1);
          const caret = caretAt(cx, cy);
          if (caret) {
            sel.setBaseAndExtent(anchorNode, anchorOffset,
              caret.startContainer, caret.startOffset);
          }
        };
        let dragging = true;
        let lastEv: { x: number; y: number } | null = null;
        const onMove = (ev: PointerEvent) => {
          lastEv = { x: ev.clientX, y: ev.clientY };
          clampAt(ev.clientX, ev.clientY);
        };
        const tick = () => {
          if (!dragging) return;
          if (lastEv) clampAt(lastEv.x, lastEv.y);
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
        // One live driver at a time. A zombie loop from an earlier drag
        // keeps writing selections with the NEXT gesture's pointer — the
        // wrap-after-pad-drag repro (owner 2026-10-09). Kill any survivor
        // before arming; the timeout is the belt-and-braces in case the
        // up/cancel events never arrive.
        let guard = 0;
        let kill: () => void;
        let done = false;
        const stop = (settle: boolean) => {
          if (done) return;
          done = true;
          dragging = false;
          window.removeEventListener("pointermove", onMove);
          window.removeEventListener("pointerup", onUp);
          window.removeEventListener("pointercancel", onUp);
          clearTimeout(guard);
          if (activeDriver === kill) activeDriver = null;
          if (settle && lastEv) clampAt(lastEv.x, lastEv.y); // settle after mouseup
        };
        const onUp = () => stop(true);
        kill = () => stop(false);
        guard = window.setTimeout(kill, 8000);
        activeDriver?.();
        activeDriver = kill;
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
        window.addEventListener("pointercancel", onUp);
      });
      renderedScale.set(pageNo, scale);
    } catch (e) {
      console.info("[aiv-pdf] STACK", pageNo, e instanceof Error && e.stack ? e.stack.split("\n").slice(0, 6).join(" | ") : String(e));
      // cancelled render (zoom churn / destroy) — clear the slot so DOM
      // stays in sync with renderedPages; the next pass re-renders it.
      if (doc === d) {
        releasePage(pageNo);
      }
    } finally {
      if (activeRenders.get(pageNo) === renderTask) {
        activeRenders.delete(pageNo);
      }
    }
  }

  function releasePage(pageNo: number) {
    // Cancel any render still pending for this page (M7): without this the
    // orphaned task would finish painting into a detached host.
    activeRenders.get(pageNo)?.cancel();
    activeRenders.delete(pageNo);
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
  // Last scroll offset seen while the scroller was alive (spec-012 M9):
  // Svelte nulls the bind:this BEFORE the unmount cleanup runs, so
  // cleanup-time persistState reads scroller===null and used to save
  // scrollPosition: undefined — every quick switch then restored to the
  // page top. The plain variable survives teardown.
  let lastScrollTop = 0;
  function onScroll() {
    if (!scroller) return;
    lastScrollTop = scroller.scrollTop;
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
  /** Search generation (spec-012 M8): a new run supersedes the in-flight
   *  one (Enter mash → latest query wins); unmount bumps it so a search
   *  running across a tab switch stops writing. */
  let searchGen = 0;

  async function runSearch() {
    const q = query.trim().toLowerCase();
    matches = [];
    matchIdx = -1;
    if (!q || !doc) return;
    const gen = ++searchGen;
    searching = true;
    try {
      const found: { page: number }[] = [];
      for (let p = 1; p <= doc.numPages; p++) {
        const page = await doc.getPage(p);
        const text = await page.getTextContent();
        if (gen !== searchGen) return;
        const sheet = text.items
          .map((it) => ("str" in it ? it.str : ""))
          .join(" ")
          .toLowerCase();
        if (sheet.includes(q)) found.push({ page: p });
      }
      if (gen !== searchGen) return;
      matches = found;
      if (found.length > 0) {
        matchIdx = 0;
        scrollToPage(found[0].page);
      }
    } catch {
      // doc destroyed mid-search (tab switch/unmount) or a page fetch
      // rejected — these used to reach the global unhandledrejection
      // sentinel and pollute the freeze-bug diagnostics (M8). Swallow.
    } finally {
      if (gen === searchGen) searching = false;
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
    lastScrollTop = scroller.scrollTop; // seed the teardown-survivor (M9)
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
      bind:this={searchInput}
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
    /* The whole strip is controls; double-clicks must never word-select
       labels (native blue ::selection) — inputs opt back in below. */
    user-select: none;
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
    user-select: text; /* inherited none from .toolbar would kill word selection */
  }

  .search {
    width: 180px;
    padding: 2px 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 12px;
    background: var(--bg);
    color: var(--text);
    user-select: text; /* same as .page-no */
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
    /* Official viewer structure: page blank area is NOT selectable — only
       the text-layer spans re-enable user-select on themselves. With the
       container selectable (inherited .viewer-body text), a drag into blank
       area resolves its focus to the nearest selectable ANCESTOR = the
       container, and the selection wraps around everything (owner
       2026-10-09: "dragging past the text selects all the lines"). */
    user-select: none;
  }

  .page-slot {
    background: white;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
    overflow: hidden;
    display: flex;
    justify-content: center;
    position: relative;
  }

  /* Official pdf.js textLayer rules (web/pdf_viewer.css) — the span
     font-size calc chain and transform variables are what make each span
     box match the painted glyph run; without them selection rectangles
     land on the wrong lines. */
  .page-slot :global(.pdf-text-layer) {
    position: absolute;
    inset: 0;
    overflow: clip;
    text-align: initial;
    line-height: 1;
    letter-spacing: normal;
    word-spacing: normal;
    text-size-adjust: none;
    forced-color-adjust: none;
    transform-origin: 0 0;
    caret-color: CanvasText;
    z-index: 0;
    --min-font-size: 1;
    --text-scale-factor: calc(var(--total-scale-factor) * var(--min-font-size));
    --min-font-size-inv: calc(1 / var(--min-font-size));
  }

  .page-slot :global(.pdf-text-layer :is(span, br)) {
    color: transparent;
    position: absolute;
    white-space: pre;
    cursor: text;
    transform-origin: 0% 0%;
    user-select: text;
    /* Hit padding (beyond official css): pdf.js spans carry no line box,
       so the blank columns beside the text contain NO selection quads —
       a drag into them extends straight to the page's start/end (owner
       2026-10-09: "dragging past the text selects all the lines"; the
       official viewer does the same — verified against it). Adobe/Chrome
       viewers give each line a full-width hit area instead. The padding
       extends each span's selectable box sideways; the negative margin
       cancels the layout shift, so glyphs and ::selection stay put. Also
       fixes "must click pixel-perfect at the first character". */
    padding: 0 20px;
    margin: 0 -20px;
  }

  .page-slot :global(.pdf-text-layer > :not(.markedContent)),
  .page-slot :global(.pdf-text-layer .markedContent span:not(.markedContent)) {
    z-index: 1;
    --font-height: 0;
    font-size: calc(var(--text-scale-factor) * var(--font-height));
    --scale-x: 1;
    --rotate: 0deg;
    transform: rotate(var(--rotate)) scaleX(var(--scale-x))
      scale(var(--min-font-size-inv));
  }

  .page-slot :global(.pdf-text-layer .markedContent) {
    display: contents;
  }

  .page-slot :global(.pdf-text-layer span[role="img"]) {
    user-select: none;
    cursor: default;
  }

  /* Official endOfContent geometry: zero-height strip at the layer bottom,
     inert (user-select:none); .selecting expands it to cover the layer so
     blank-area drags stop at the last text span. z-index 0 keeps it below
     the spans — the > .pdf-end-of-content compound is load-bearing: the
     span rule ("> :not(.markedContent)", z-index 1) must not outrank it,
     or the shield swallows every hit and selection dies at the anchor. */
  .page-slot :global(.pdf-text-layer > .pdf-end-of-content) {
    display: block;
    position: absolute;
    inset: 100% 0 0;
    z-index: 0;
    cursor: default;
    user-select: none;
  }

  .page-slot :global(.pdf-text-layer.selecting .pdf-end-of-content) {
    top: 0;
  }

  /* Official rule: br elements sit at the layer's static-flow origin (all
     spans are absolute), so their selection highlight would paint a phantom
     box at the top-left corner whenever a selection crosses a line break. */
  .page-slot :global(.pdf-text-layer br::selection) {
    background: transparent;
  }

  .page-slot :global(.pdf-text-layer ::selection) {
    background: rgba(76, 139, 245, 0.35);
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
