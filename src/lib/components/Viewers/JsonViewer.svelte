<script lang="ts">
  /**
   * JSON viewer (V1.5 §108): default Formatted (pretty + highlight), can
   * switch to Source. Invalid JSON falls back to Source with a note.
   */
  import { json } from "@codemirror/lang-json";
  import CodeViewer from "./CodeViewer.svelte";
  import { t } from "$lib/i18n/t.svelte";
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

</script>

<div class="json-viewer">
  <!-- View mode toggles via the file tab's right-click menu (owner item 5). -->
  <div class="host">
    {#if mode === "formatted" && formatted.ok}
      <CodeViewer {rootPath} {tab} text={formatted.text} fixedLanguage={json()} />
    {:else}
      <CodeViewer {rootPath} {tab} text={raw} language="json" />
    {/if}
  </div>
  {#if !formatted.ok}
    <div class="note">{t("viewer.invalidJson")}</div>
  {/if}
</div>

<style>
  .json-viewer {
    height: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .host {
    flex: 1;
    min-height: 0;
  }

  .note {
    position: absolute;
    bottom: 8px;
    left: 16px;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
</style>
