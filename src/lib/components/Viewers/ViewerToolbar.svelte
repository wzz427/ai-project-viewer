<script lang="ts">
  /**
   * Shared text-viewer toolbar (SPEC-INFRA-003, owner 2026-10-10): font
   * size controls + Find-in-document, patterned after the PDF viewer's
   * toolbar. The font buttons turn the GLOBAL viewer font knob (V1.5 §22 —
   * the same setting the Settings panel exposes), not a per-document zoom.
   * Find is page-navigation grade like the PDF's: count + jump, no
   * character-level highlight decoration.
   */
  import { onMount } from "svelte";
  import { settings, setFontSize } from "$lib/stores/settingsStore.svelte";
  import Icon from "$lib/components/Icon.svelte";
  import { registerFindFocus, unregisterFindFocus } from "./activeFind";
  import { t } from "$lib/i18n/t.svelte";

  let {
    findApi,
  }: {
    /** Viewer-side search: count(q) = total matches; jump(q, i) = move to
     *  the 0-based i-th match. Omit for viewers without searchable text. */
    findApi?: {
      count: (q: string) => number;
      jump: (q: string, index: number) => void;
    };
  } = $props();

  let query = $state("");
  let total = $state(0);
  let idx = $state(-1);
  let input: HTMLInputElement | undefined = $state();

  function recompute() {
    const q = query.trim();
    total = q && findApi ? findApi.count(q) : 0;
    idx = -1;
  }

  function step(dir: 1 | -1) {
    if (total === 0 || !findApi) return;
    idx = idx === -1 ? (dir === 1 ? 0 : total - 1) : (idx + dir + total) % total;
    findApi.jump(query.trim(), idx);
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      step(e.shiftKey ? -1 : 1);
    } else if (e.key === "Escape") {
      query = "";
      recompute();
    }
  }

  onMount(() => {
    const focus = () => input?.focus();
    registerFindFocus(focus);
    return () => unregisterFindFocus(focus);
  });
</script>

<div class="vtb">
  <button class="tb" onclick={() => setFontSize(settings.fontSize - 1)} aria-label={t("viewer.smallerText")}>A−</button>
  <span class="tb-label mono">{settings.fontSize}px</span>
  <button class="tb" onclick={() => setFontSize(settings.fontSize + 1)} aria-label={t("viewer.largerText")}>A+</button>

  <span class="grow"></span>

  {#if findApi}
    <input
      class="search"
      type="search"
      placeholder={t("viewer.findPlaceholder")}
      bind:this={input}
      bind:value={query}
      oninput={recompute}
      onkeydown={onKey}
      aria-label={t("viewer.searchDoc")}
    />
    {#if query.trim() && total > 0}
      <span class="tb-label">{idx + 1} / {total}</span>
      <button class="tb" onclick={() => step(-1)} aria-label="Previous match"><Icon name="chevron-left" size={14} /></button>
      <button class="tb" onclick={() => step(1)} aria-label="Next match"><Icon name="chevron-right" size={14} /></button>
    {:else if query.trim()}
      <span class="tb-label">{t("viewer.findNoResults")}</span>
    {/if}
  {/if}
</div>

<style>
  .vtb {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-bottom: 1px solid var(--border);
    background: var(--toolbar-bg);
    flex-shrink: 0;
    /* The whole strip is controls; double-clicks must never word-select
       the "15px" label (native blue ::selection) — inputs opt back in. */
    user-select: none;
  }

  .tb {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 2px 8px;
    border-radius: var(--radius);
    font-size: var(--text-sm);
    color: var(--text-muted);
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast);
  }

  .tb:hover {
    background: var(--bg-hover);
    color: var(--text);
  }

  .tb-label {
    font-size: var(--text-sm);
    color: var(--text-muted);
    padding: 0 2px;
  }

  .search {
    width: 180px;
    padding: 2px 8px;
    /* Theme pack surface.input + border.default (spec §四 搜索框): inputs
       get their own recessed surface with a proper bound edge. */
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    font-size: var(--text-sm);
    background: var(--bg-input);
    color: var(--text);
    user-select: text; /* inherited none from .vtb would kill double-click word selection */
  }

  .grow {
    flex: 1;
  }

  .mono {
    font-family: var(--font-mono);
  }
</style>
