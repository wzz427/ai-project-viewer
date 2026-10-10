<script lang="ts">
  /**
   * Routes the active tab to its viewer (V1.5 §21/§158). Inactive tabs are
   * unmounted — state restoration happens inside each viewer (§160.5).
   */
  import {
    activeTab,
    cachedContent,
    ensureContentLoaded,
  } from "$lib/stores/tabsStore.svelte";
  import MarkdownViewer from "./MarkdownViewer.svelte";
  import CodeViewer from "./CodeViewer.svelte";
  import JsonViewer from "./JsonViewer.svelte";
  import ImageViewer from "./ImageViewer.svelte";
  import PdfViewer from "./PdfViewer.svelte";
  import ExecutableInfoViewer from "./ExecutableInfoViewer.svelte";
  import UnsupportedViewer from "./UnsupportedViewer.svelte";
  import { extOf } from "$lib/services/viewerType";

  let { rootPath }: { rootPath: string } = $props();

  const tab = $derived(activeTab(rootPath));
  const text = $derived(textOf());
  function textOf(): string | null {
    if (!tab) return null;
    const c = cachedContent(rootPath, tab.relativePath);
    return c?.kind === "text" ? c.text : null;
  }

  // Restored tabs (session restore, spec-004 D4) arrive without cached
  // content — the previous "Loading…" dead-end becomes a lazy read here.
  // Reading the cache inside the effect makes it self-stopping: once the
  // content lands, the dependency fires, the guard fails, no refetch.
  $effect(() => {
    const t = tab;
    if (!t || t.deleted) return;
    if (t.viewerType === "binary" || t.viewerType === "unsupported") return;
    if (t.viewerType === "executable") return; // stat card, no content
    if (!cachedContent(rootPath, t.relativePath)) {
      void ensureContentLoaded(rootPath, t.relativePath);
    }
  });
</script>

{#if tab}
  <!-- Keyed by file: switching files always remounts the viewer, so content
       can never go stale (owner 2026-10-01 items 3/10 root cause). -->
  {#key tab.relativePath}
  {#if tab.deleted || tab.viewerType === "binary" || tab.viewerType === "unsupported"}
    <UnsupportedViewer {rootPath} {tab} />
  {:else if tab.viewerType === "markdown" && text !== null}
    <MarkdownViewer {rootPath} {tab} />
  {:else if tab.viewerType === "json" && text !== null}
    <JsonViewer {rootPath} {tab} />
  {:else if tab.viewerType === "image"}
    <ImageViewer {rootPath} {tab} />
  {:else if tab.viewerType === "pdf"}
    <PdfViewer {rootPath} {tab} />
  {:else if tab.viewerType === "executable"}
    <ExecutableInfoViewer {rootPath} {tab} />
  {:else if text !== null}
    <div class="code-host">
      <CodeViewer {rootPath} {tab} text={text} language={extOf(tab.relativePath)} />
    </div>
  {:else}
    <div class="loading">Loading…</div>
  {/if}
  {/key}
{/if}

<style>
  .code-host {
    height: 100%;
  }

  .loading {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 12px;
  }
</style>
