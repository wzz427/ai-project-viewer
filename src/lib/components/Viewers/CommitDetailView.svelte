<script lang="ts">
  import { closeGitView, gitViewSlot, openDiff } from "$lib/stores/gitStore.svelte";
  import {
    gitCommitDetail,
    type GitCommitDetail,
  } from "$lib/services/tauri";
  import { fileNameOf } from "$lib/services/viewerType";
  import { letterClass } from "$lib/services/gitFormat";

  const view = $derived(
    gitViewSlot.current?.kind === "commit" ? gitViewSlot.current : null,
  );

  let detail = $state<GitCommitDetail | null>(null);
  let error = $state<string | null>(null);

  // Load per slot change; a cancelled load never overwrites the next one.
  $effect(() => {
    const cur = view;
    detail = null;
    error = null;
    if (!cur) return;
    let cancelled = false;
    gitCommitDetail(cur.rootPath, cur.hash)
      .then((d) => {
        if (!cancelled) detail = d;
      })
      .catch((e) => {
        if (!cancelled) error = String(e);
      });
    return () => {
      cancelled = true;
    };
  });

  function dirnameOf(rel: string): string {
    const i = rel.lastIndexOf("/");
    return i === -1 ? "" : rel.slice(0, i);
  }

  function clickFile(rel: string) {
    // Drill down: this file's change inside this commit, side-by-side.
    if (view) openDiff(view.rootPath, rel, false, view.hash);
  }
</script>

<svelte:window onkeydown={(e) => e.key === "Escape" && closeGitView()} />

<div class="commit-view">
  <div class="c-head">
    <span class="title"><span class="glyph">◉</span> Commit</span>
    <span class="hash mono">{detail?.hash.slice(0, 7) ?? ""}</span>
    <span class="spacer"></span>
    <button class="close" onclick={closeGitView} title="Close" aria-label="Close">×</button>
  </div>
  <div class="c-body">
    {#if error}
      <p class="muted pad">{error}</p>
    {:else if !detail}
      <p class="muted pad">Loading…</p>
    {:else}
      <div class="card">
        <pre class="message">{detail.message.trim() || "(no message)"}</pre>
        <dl class="meta">
          <div><dt>Author</dt><dd>{detail.author}</dd></div>
          <div><dt>Date</dt><dd>{detail.date}</dd></div>
          <div><dt>Hash</dt><dd class="mono">{detail.hash}</dd></div>
        </dl>
      </div>
      <h3 class="files-title">FILES CHANGED <span class="count">{detail.files.length}</span></h3>
      {#if detail.files.length === 0}
        <p class="muted pad">No files in this project's scope.</p>
      {/if}
      {#each detail.files as f (f.rel)}
        <button class="entry" title={f.origRel ? `${f.origRel} → ${f.rel}` : f.rel} onclick={() => clickFile(f.rel)}>
          <span class="letter {letterClass(f.letter)}">{f.letter}</span>
          <span class="ename">{fileNameOf(f.rel)}</span>
          <span class="edir">{dirnameOf(f.rel)}</span>
        </button>
      {/each}
    {/if}
  </div>
</div>

<style>
  .commit-view {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .c-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px;
    border-bottom: 1px solid var(--viewer-border);
    background: var(--bg-raised);
    font-size: 12.5px;
    flex-shrink: 0;
  }

  .title {
    font-weight: 600;
  }

  .glyph {
    color: var(--text-muted);
    font-weight: 400;
  }

  .hash {
    color: var(--git-m);
    font-size: 11.5px;
  }

  .spacer {
    flex: 1;
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

  .c-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 12px 16px;
  }

  .card {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 14px;
    max-width: 720px;
  }

  .message {
    margin: 0;
    font-family: var(--font-ui);
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .meta {
    margin: 10px 0 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 12px;
  }

  .meta div {
    display: flex;
    gap: 8px;
  }

  .meta dt {
    color: var(--text-muted);
    width: 52px;
    flex-shrink: 0;
  }

  .meta dd {
    margin: 0;
    word-break: break-all;
  }

  .files-title {
    margin: 18px 0 6px;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .count {
    margin-left: 4px;
  }

  .entry {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    max-width: 720px;
    padding: 2px 6px;
    border-radius: var(--radius);
    font-size: 12.5px;
    text-align: left;
    cursor: pointer;
  }

  .entry:hover {
    background: var(--bg-hover);
  }

  .letter {
    flex-shrink: 0;
    width: 10px;
    font-weight: 700;
    font-size: 11px;
  }

  .ename {
    color: var(--text);
    white-space: nowrap;
  }

  .edir {
    color: var(--text-muted);
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .muted.pad {
    padding: 20px;
  }
</style>
