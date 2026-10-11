<script lang="ts">
  /**
   * Image viewer (V1.5 §109): Fit / Actual Size / Zoom / Pan. All formats
   * — SVG included — render through a data-URL <img>, the safe image
   * context where scripts never execute (§110, spec-003 D3).
   */
  import {
    cachedContent,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const dataUrl = $derived(urlOf());
  function urlOf(): string {
    const c = cachedContent(rootPath, tab.relativePath);
    return c?.kind === "media" ? c.dataUrl : "";
  }

  // "fit" | "actual" modes; zoom = scale multiplier under "actual".
  let mode = $state<"fit" | "actual">("fit");
  let zoom = $state(1);
  let natural = $state<{ w: number; h: number } | null>(null);

  // Pan offset in CSS pixels while zoomed beyond the viewport.
  let panX = $state(0);
  let panY = $state(0);
  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  function setFit() {
    mode = "fit";
    zoom = 1;
    panX = 0;
    panY = 0;
  }

  function setActual() {
    mode = "actual";
    zoom = 1;
    panX = 0;
    panY = 0;
  }

  function zoomBy(factor: number) {
    mode = "actual";
    zoom = Math.min(8, Math.max(0.1, +(zoom * factor).toFixed(3)));
  }

  function onWheel(e: WheelEvent) {
    e.preventDefault();
    zoomBy(e.deltaY < 0 ? 1.15 : 1 / 1.15);
  }

  function onPointerDown(e: PointerEvent) {
    if (mode !== "actual") return;
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }

  function onPointerMove(e: PointerEvent) {
    if (!dragging) return;
    panX += e.clientX - lastX;
    panY += e.clientY - lastY;
    lastX = e.clientX;
    lastY = e.clientY;
  }

  function onPointerUp() {
    dragging = false;
  }
</script>

<div class="image-viewer">
  <div class="toolbar" role="toolbar" aria-label="Image controls">
    <button class:active={mode === "fit"} onclick={setFit}>Fit</button>
    <button class:active={mode === "actual"} onclick={setActual}>100%</button>
    <button onclick={() => zoomBy(1.25)} aria-label="Zoom in">+</button>
    <button onclick={() => zoomBy(1 / 1.25)} aria-label="Zoom out">−</button>
    {#if natural}
      <span class="muted">{natural.w}×{natural.h}{mode === "actual" ? ` · ${Math.round(zoom * 100)}%` : ""}</span>
    {/if}
  </div>

  <div
    class="stage"
    role="presentation"
    onwheel={onWheel}
    onpointerdown={onPointerDown}
    onpointermove={onPointerMove}
    onpointerup={onPointerUp}
  >
    {#if dataUrl}
      <img
        src={dataUrl}
        alt={tab.relativePath}
        draggable="false"
        class:fit={mode === "fit"}
        style={mode === "actual"
          ? `width: ${natural ? natural.w * zoom : 0}px; transform: translate(${panX}px, ${panY}px);`
          : ""}
        onload={(e) => {
          const img = e.currentTarget as HTMLImageElement;
          natural = { w: img.naturalWidth, h: img.naturalHeight };
        }}
      />
    {/if}
  </div>
</div>

<style>
  .image-viewer {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    /* The size readout span is not a copy target — same L40 family as the
       0.7.7 button fix (spec-012 L-f6: double-click on the toolbar
       word-selected the readout in native blue). */
    user-select: none;
  }

  .toolbar button {
    padding: 2px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 11.5px;
  }

  .toolbar button.active {
    background: var(--bg-active);
  }

  .toolbar .muted {
    margin-left: 8px;
    font-size: 11px;
    color: var(--text-muted);
  }

  .stage {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: grab;
    user-select: none;
  }

  img.fit {
    max-width: 100%;
    max-height: 100%;
  }
</style>
