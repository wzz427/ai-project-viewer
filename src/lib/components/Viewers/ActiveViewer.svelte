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
  import { diagEvent } from "$lib/stores/diagnosticsStore.svelte";

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

  // Runtime trace (0.6.12): one line per viewer swap — the tab strip and
  // the viewer body must move together; if they ever diverge, this log
  // shows exactly where the chain broke (owner's freeze bug 2026-10-10).
  let lastViewerKey = "";
  $effect(() => {
    const t = tab;
    if (!t) return;
    const key = `${t.viewerType}:${t.relativePath}`;
    if (key !== lastViewerKey) {
      lastViewerKey = key;
      diagEvent(`viewer ${key}`);
    }
  });
</script>

{#if tab}
  <!-- Keyed by file + content revision: switching files always remounts
       the viewer (content can never go stale, owner 2026-10-01 items
       3/10), and an external reload (watcher/Ctrl+R, spec-009 D3) bumps
       contentRev so mount-built viewers (CodeMirror, PDF) pick up the
       new bytes while §160.5 restores keep the scroll position. -->
  {#key `${tab.relativePath}:${tab.contentRev ?? 0}`}
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
