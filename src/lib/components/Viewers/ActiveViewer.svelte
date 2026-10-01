<script lang="ts">
  /**
   * Routes the active tab to its viewer (V1.5 §21/§158). Inactive tabs are
   * unmounted — state restoration happens inside each viewer (§160.5).
   */
  import {
    activeTab,
    cachedContent,
  } from "$lib/stores/tabsStore.svelte";
  import MarkdownViewer from "./MarkdownViewer.svelte";
  import CodeViewer from "./CodeViewer.svelte";
  import JsonViewer from "./JsonViewer.svelte";
  import ImageViewer from "./ImageViewer.svelte";
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
</script>

{#if tab}
  {#if tab.deleted || tab.viewerType === "binary" || tab.viewerType === "unsupported"}
    <UnsupportedViewer {rootPath} {tab} />
  {:else if tab.viewerType === "markdown" && text !== null}
    <MarkdownViewer {rootPath} {tab} />
  {:else if tab.viewerType === "json" && text !== null}
    <JsonViewer {rootPath} {tab} />
  {:else if tab.viewerType === "image"}
    <ImageViewer {rootPath} {tab} />
  {:else if text !== null}
    <div class="code-host">
      <CodeViewer {tab} text={text} language={extOf(tab.relativePath)} />
    </div>
  {:else}
    <div class="loading">Loading…</div>
  {/if}
{/if}

<style>
  .code-host {
    height: 100%;
    padding: 8px 0;
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
