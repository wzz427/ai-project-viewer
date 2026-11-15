<script lang="ts">
  /**
   * Shared zoom/pan stage (spec-021 D1, extracted 2026-11-15): the SAME
   * fit/actual + wheel-zoom + drag-pan model behind both the image FILE
   * viewer (spec-003) and the markdown lightbox — one model, two chrome
   * jobs, so the two surfaces can never drift apart.
   *
   * Owners mount this component and drive it through the exported
   * functions (setFit/setActual/zoomBy) while mirroring the view state
   * they need for their toolbar via the `onview` callback.
   */
  let {
    src,
    alt,
    onview,
  }: {
    src: string;
    alt: string;
    onview?: (v: {
      mode: "fit" | "actual";
      zoom: number;
      natural: { w: number; h: number } | null;
    }) => void;
  } = $props();

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

  // Toolbar mirror: every view change reports out once.
  $effect(() => {
    onview?.({ mode, zoom, natural });
  });

  // A new src is a new picture — old zoom/pan are meaningless (spec-021
  // D8; same semantics as switching files remounts the file viewer).
  // natural re-arrives via onload below.
  $effect(() => {
    src;
    mode = "fit";
    zoom = 1;
    panX = 0;
    panY = 0;
    natural = null;
  });

  export function setFit() {
    mode = "fit";
    zoom = 1;
    panX = 0;
    panY = 0;
  }

  export function setActual() {
    mode = "actual";
    zoom = 1;
    panX = 0;
    panY = 0;
  }

  export function zoomBy(factor: number) {
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

<div
  class="stage"
  role="presentation"
  onwheel={onWheel}
  onpointerdown={onPointerDown}
  onpointermove={onPointerMove}
  onpointerup={onPointerUp}
>
  {#if src}
    <img
      {src}
      {alt}
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

<style>
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
