<script lang="ts">
  /**
   * JSON viewer (V1.5 §108): default Formatted (pretty + highlight), can
   * switch to Source. Invalid JSON falls back to Source with a note.
   */
  import { json } from "@codemirror/lang-json";
  import CodeViewer from "./CodeViewer.svelte";
  import { cachedContent, type RuntimeTab } from "$lib/stores/tabsStore.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const raw = $derived(contentOf());
  function contentOf(): string {
    const c = cachedContent(rootPath, tab.relativePath);
    return c?.kind === "text" ? c.text : "";
  }

  const formatted = $derived(pretty());
  function pretty(): { ok: true; text: string } | { ok: false } {
    try {
      return { ok: true, text: JSON.stringify(JSON.parse(raw), null, 2) };
    } catch {
      return { ok: false };
    }
  }

  const mode = $derived(formatted.ok ? (tab.jsonMode ?? "formatted") : "source");

  function setMode(next: "formatted" | "source") {
    tab.jsonMode = next;
  }
</script>

<div class="json-viewer">
  <div class="mode-switch" role="toolbar" aria-label="View mode">
    <button class:active={mode === "formatted"} disabled={!formatted.ok} onclick={() => setMode("formatted")}>
      Formatted
    </button>
    <button class:active={mode === "source"} onclick={() => setMode("source")}>
      Source
    </button>
  </div>
  <div class="host">
    {#if mode === "formatted" && formatted.ok}
      <CodeViewer {tab} text={formatted.text} fixedLanguage={json()} />
    {:else}
      <CodeViewer {tab} text={raw} language="json" />
    {/if}
  </div>
  {#if !formatted.ok}
    <div class="note">Invalid JSON — showing source.</div>
  {/if}
</div>

<style>
  .json-viewer {
    height: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .mode-switch {
    position: absolute;
    top: 8px;
    right: 16px;
    z-index: 5;
    display: flex;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    background: var(--bg-raised);
  }

  .mode-switch button {
    padding: 3px 10px;
    font-size: 11.5px;
    color: var(--text-muted);
  }

  .mode-switch button.active {
    background: var(--bg-active);
    color: var(--text);
  }

  .mode-switch button:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .host {
    flex: 1;
    min-height: 0;
    padding-top: 8px;
  }

  .note {
    position: absolute;
    bottom: 8px;
    left: 16px;
    font-size: 11px;
    color: var(--text-muted);
  }
</style>
