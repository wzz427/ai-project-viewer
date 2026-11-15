<script lang="ts">
  /**
   * Image lightbox (spec-021): click an inline markdown image → centered
   * popup on a dark veil, zoomable (buttons / wheel) and pannable when
   * zoomed. Rendered once at the app root like ErrorDialog/LocateDialog;
   * the store slot decides visibility. The zoom model is the shared
   * ImageStage (D1) — identical feel to the image FILE viewer.
   *
   * All wording reuses the existing viewer.* i18n keys (D7) — no
   * lightbox-specific strings to drift out of sync.
   */
  import { lightboxState, closeLightbox } from "$lib/stores/lightboxStore.svelte";
  import { t } from "$lib/i18n/t.svelte";
  import ImageStage from "./Viewers/ImageStage.svelte";

  let stage = $state<ImageStage | null>(null);
  let view = $state<{
    mode: "fit" | "actual";
    zoom: number;
    natural: { w: number; h: number } | null;
  }>({ mode: "fit", zoom: 1, natural: null });

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") closeLightbox();
  }

  $effect(() => {
    if (!lightboxState.open) return;
    window.addEventListener("keydown", onKeydown, { capture: true });
    return () =>
      window.removeEventListener("keydown", onKeydown, { capture: true });
  });
</script>

{#if lightboxState.open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="backdrop"
    role="presentation"
    onmousedown={(e) => {
      // Only the veil ring around the panel closes (LocateDialog
      // contract): the panel itself hosts zoom-dragging, which must not
      // read as a close gesture.
      if (e.target === e.currentTarget) closeLightbox();
    }}
  >
    <div
      class="lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={t("viewer.imageControls")}
    >
      <div class="bar" role="toolbar" aria-label={t("viewer.imageControls")}>
        <div class="zoom-group">
          <button class:active={view.mode === "fit"} onclick={() => stage?.setFit()}>{t("viewer.fit")}</button>
          <button class:active={view.mode === "actual"} onclick={() => stage?.setActual()}>100%</button>
          <button onclick={() => stage?.zoomBy(1.25)} aria-label={t("viewer.zoomIn")}>+</button>
          <button onclick={() => stage?.zoomBy(1 / 1.25)} aria-label={t("viewer.zoomOut")}>−</button>
          {#if view.natural}
            <span class="readout">{view.natural.w}×{view.natural.h}{view.mode === "actual" ? ` · ${Math.round(view.zoom * 100)}%` : ""}</span>
          {/if}
        </div>
        <button class="close" onclick={closeLightbox} aria-label={t("common.close")}>×</button>
      </div>
      <ImageStage bind:this={stage} src={lightboxState.src} alt="" onview={(v) => (view = v)} />
    </div>
  </div>
{/if}

<style>
  /* Dark veil (spec-021 D3): photo-viewer convention — both app themes
     are light papers, and a light veil kills the contrast the zoomed
     image is here for. Tokens (app.css :root), not per-component hex. */
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: var(--lightbox-veil);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px; /* the clickable close ring around the panel */
  }

  .lightbox {
    width: 100%;
    height: 100%;
    background: var(--lightbox-surface);
    border: 1px solid color-mix(in srgb, var(--lightbox-ink) 25%, transparent);
    border-radius: var(--radius);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: var(--shadow);
  }

  .bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 6px 10px;
    flex-shrink: 0;
    user-select: none;
    border-bottom: 1px solid color-mix(in srgb, var(--lightbox-ink) 20%, transparent);
  }

  .zoom-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .bar button {
    padding: 2px 10px;
    border: 1px solid color-mix(in srgb, var(--lightbox-ink) 45%, transparent);
    border-radius: var(--radius);
    font-size: var(--text-sm);
    color: var(--lightbox-ink);
    background: transparent;
  }

  .bar button:hover {
    background: color-mix(in srgb, var(--lightbox-ink) 12%, transparent);
  }

  .bar button.active {
    background: color-mix(in srgb, var(--lightbox-ink) 22%, transparent);
  }

  .bar .close {
    font-size: 16px;
    line-height: 1;
    padding: 2px 9px;
  }

  .readout {
    margin-left: 8px;
    font-size: var(--text-xs);
    color: color-mix(in srgb, var(--lightbox-ink) 65%, transparent);
  }
</style>
