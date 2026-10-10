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
  import { registerFindFocus, unregisterFindFocus } from "./activeFind";

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
  <button class="tb" onclick={() => setFontSize(settings.fontSize - 1)} aria-label="Smaller text">A−</button>
  <span class="tb-label mono">{settings.fontSize}px</span>
  <button class="tb" onclick={() => setFontSize(settings.fontSize + 1)} aria-label="Larger text">A+</button>

  <span class="grow"></span>

  {#if findApi}
    <input
      class="search"
      type="search"
      placeholder="Find in document…"
      bind:this={input}
      bind:value={query}
      oninput={recompute}
      onkeydown={onKey}
      aria-label="Search document"
    />
    {#if query.trim() && total > 0}
      <span class="tb-label">{idx + 1} / {total}</span>
      <button class="tb" onclick={() => step(-1)} aria-label="Previous match">‹</button>
      <button class="tb" onclick={() => step(1)} aria-label="Next match">›</button>
    {:else if query.trim()}
      <span class="tb-label">0 results</span>
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
    flex-shrink: 0;
  }

  .tb {
    padding: 2px 8px;
    border-radius: var(--radius);
    font-size: 12px;
    color: var(--text-muted);
  }

  .tb:hover {
    background: var(--bg-hover);
  }

  .tb-label {
    font-size: 12px;
    color: var(--text-muted);
    padding: 0 2px;
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

  .grow {
    flex: 1;
  }

  .mono {
    font-family: var(--mono, monospace);
  }
</style>
