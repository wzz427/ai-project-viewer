<script lang="ts">
  /**
   * Image viewer (V1.5 §109): Fit / Actual Size / Zoom / Pan. All formats
   * — SVG included — render through a data-URL <img>, the safe image
   * context where scripts never execute (§110, spec-003 D3).
   * The zoom/pan model lives in the shared ImageStage (spec-021 D1) —
   * extracted so the markdown lightbox rides the exact same behavior.
   */
  import {
    cachedContent,
    type RuntimeTab,
  } from "$lib/stores/tabsStore.svelte";
  import { t } from "$lib/i18n/t.svelte";
  import ImageStage from "./ImageStage.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const dataUrl = $derived(urlOf());
  function urlOf(): string {
    const c = cachedContent(rootPath, tab.relativePath);
    return c?.kind === "media" ? c.dataUrl : "";
  }

  // Toolbar mirror of the stage's view state (spec-021 D1): buttons stay
  // owned by this component, the model by ImageStage.
  let stage = $state<ImageStage | null>(null);
  let view = $state<{
    mode: "fit" | "actual";
    zoom: number;
    natural: { w: number; h: number } | null;
  }>({ mode: "fit", zoom: 1, natural: null });
</script>

<div class="image-viewer">
  <div class="toolbar" role="toolbar" aria-label={t("viewer.imageControls")}>
    <button class:active={view.mode === "fit"} onclick={() => stage?.setFit()}>{t("viewer.fit")}</button>
    <button class:active={view.mode === "actual"} onclick={() => stage?.setActual()}>100%</button>
    <button onclick={() => stage?.zoomBy(1.25)} aria-label={t("viewer.zoomIn")}>+</button>
    <button onclick={() => stage?.zoomBy(1 / 1.25)} aria-label={t("viewer.zoomOut")}>−</button>
    {#if view.natural}
      <span class="muted">{view.natural.w}×{view.natural.h}{view.mode === "actual" ? ` · ${Math.round(view.zoom * 100)}%` : ""}</span>
    {/if}
  </div>

  <ImageStage bind:this={stage} src={dataUrl} alt={tab.relativePath} onview={(v) => (view = v)} />
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
    font-size: var(--text-sm);
  }

  .toolbar button.active {
    background: var(--bg-active);
  }

  .toolbar .muted {
    margin-left: 8px;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
</style>
