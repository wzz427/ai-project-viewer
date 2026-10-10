<script lang="ts">
  import { closeDiff, gitDiffSlot } from "$lib/stores/gitStore.svelte";
  import { gitDiff, openInCodeEditor, type GitDiffResult } from "$lib/services/tauri";
  import { fileNameOf } from "$lib/services/viewerType";

  const diff = $derived(gitDiffSlot.current);

  let result = $state<GitDiffResult | null>(null);
  let error = $state<string | null>(null);

  // Load per slot change; a cancelled load never overwrites the next one.
  $effect(() => {
    const cur = diff;
    result = null;
    error = null;
    if (!cur) return;
    let cancelled = false;
    gitDiff(cur.rootPath, cur.rel, cur.staged)
      .then((r) => {
        if (!cancelled) result = r;
      })
      .catch((e) => {
        if (!cancelled) error = String(e);
      });
    return () => {
      cancelled = true;
    };
  });

  // 20k lines render as 20k light rows — a plain per-line <div> is the
  // cheapest thing that stays scrollable (no virtualization for V1).
  const lines = $derived(result ? result.text.split("\n") : []);

  function lineClass(line: string): string {
    if (line.startsWith("+")) return "add";
    if (line.startsWith("-")) return "del";
    if (line.startsWith("@@")) return "hunk";
    if (line.startsWith("diff ") || line.startsWith("index ")) return "meta";
    if (line.startsWith("---") || line.startsWith("+++")) return "meta";
    return "ctx";
  }

  function handOffToVSCode() {
    if (diff) void openInCodeEditor(diff.rootPath, diff.rel, true).catch(() => {});
  }
</script>

<svelte:window onkeydown={(e) => e.key === "Escape" && closeDiff()} />

<div class="diff-viewer">
  <div class="diff-head">
    <span class="title" title={diff?.rel}>
      {diff ? fileNameOf(diff.rel) : ""}
      <span class="kind">{diff?.staged ? "(Staged)" : "(Working Tree)"}</span>
    </span>
    <span class="path mono">{diff?.rel}</span>
    <button class="close" onclick={closeDiff} title="Close diff" aria-label="Close diff">×</button>
  </div>
  <div class="diff-body">
    {#if error}
      <p class="muted pad">{error}</p>
    {:else if !result}
      <p class="muted pad">Loading…</p>
    {:else if result.truncated}
      <!-- §72: the backend stopped at 2 MB / 20k lines. -->
      <div class="too-large">
        <p>Diff is too large to display.</p>
        <button onclick={handOffToVSCode}>Open in VS Code</button>
      </div>
    {:else if result.text.trim().length === 0}
      <p class="muted pad">No textual changes.</p>
    {:else}
      <pre class="mono">{#each lines as line, i (i)}<span class="diff-line {lineClass(line)}">{line || " "}</span>{/each}</pre>
    {/if}
  </div>
</div>

<style>
  .diff-viewer {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .diff-head {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 10px;
    border-bottom: 1px solid var(--viewer-border);
    background: var(--bg-raised);
    font-size: 12.5px;
  }

  .title {
    font-weight: 600;
    white-space: nowrap;
  }

  .kind {
    font-weight: 400;
    color: var(--text-muted);
  }

  .path {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 11px;
    color: var(--text-muted);
  }

  .close {
    padding: 0 8px;
    font-size: 15px;
    color: var(--text-muted);
    border-radius: var(--radius);
  }

  .close:hover {
    background: var(--bg-hover);
    color: var(--text);
  }

  .diff-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    font-size: var(--viewer-font-size);
  }

  pre {
    margin: 0;
    display: block;
  }

  .diff-line {
    display: block;
    white-space: pre;
    min-height: 1em;
  }

  .diff-line.add {
    background: var(--git-add-bg);
  }

  .diff-line.del {
    background: var(--git-del-bg);
  }

  .diff-line.hunk {
    color: var(--text-muted);
  }

  .diff-line.meta {
    color: var(--text-muted);
    font-style: italic;
  }

  .muted.pad,
  .too-large {
    padding: 20px;
  }

  .too-large p {
    margin: 0 0 10px;
    font-weight: 600;
  }

  .too-large button {
    padding: 4px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-hover);
    cursor: pointer;
    font-size: 12.5px;
  }
</style>
