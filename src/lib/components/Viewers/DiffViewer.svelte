<script lang="ts">
  import { closeGitView, gitViewSlot, openCommit } from "$lib/stores/gitStore.svelte";
  import {
    gitDiff,
    openInCodeEditor,
    type GitDiffResult,
  } from "$lib/services/tauri";
  import { fileNameOf } from "$lib/services/viewerType";
  import {
    diffPathOf,
    parseUnifiedDiff,
    type DiffRow,
  } from "$lib/services/diffSideBySide";

  const view = $derived(
    gitViewSlot.current?.kind === "diff" ? gitViewSlot.current : null,
  );

  let result = $state<GitDiffResult | null>(null);
  let error = $state<string | null>(null);

  // Load per slot change; a cancelled load never overwrites the next one.
  $effect(() => {
    const cur = view;
    result = null;
    error = null;
    if (!cur) return;
    let cancelled = false;
    gitDiff(cur.rootPath, cur.rel, cur.staged, cur.commitHash)
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

  const segments = $derived(result ? parseUnifiedDiff(result.text) : []);

  const kindLabel = $derived(
    view?.commitHash
      ? `(${view.commitHash.slice(0, 7)})`
      : view?.staged
        ? "(Staged)"
        : "(Working Tree)",
  );

  // Which sides carry change paint: del rows paint the old cell, add rows
  // the new cell, mod rows both; the opposite cell gets a hatch.
  function sideClass(row: DiffRow, side: "old" | "new"): string {
    if (row.kind === "ctx") return "";
    if (row.kind === "mod") return "chg";
    const painted = row.kind === "del" ? "old" : "new";
    return side === painted ? "chg" : "hole";
  }

  function handOffToVSCode() {
    if (view) void openInCodeEditor(view.rootPath, view.rel, true).catch(() => {});
  }

  function backToCommit() {
    if (view?.commitHash) openCommit(view.rootPath, view.commitHash);
  }
</script>

<svelte:window onkeydown={(e) => e.key === "Escape" && closeGitView()} />

<div class="diff-viewer">
  <div class="diff-head">
    {#if view?.commitHash}
      <button class="back" onclick={backToCommit} title="Back to commit">‹</button>
    {/if}
    <span class="title" title={view?.rel}>
      <span class="pair">⇄</span>
      {view ? fileNameOf(view.rel) : ""}
      <span class="kind">{kindLabel}</span>
    </span>
    <span class="path mono">{view?.rel}</span>
    <button class="close" onclick={closeGitView} title="Close diff" aria-label="Close diff">×</button>
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
    {:else if segments.length === 0}
      <p class="muted pad">
        No textual changes{result.text.includes("Binary files") ? " (binary file)." : "."}
      </p>
    {:else}
      <div class="table" role="table">
        <div class="thead">
          <span class="ln"></span><span class="cell">{diffPathOf(result.text, "old") ?? "(new file)"}</span>
          <span class="ln"></span><span class="cell">{diffPathOf(result.text, "new") ?? "(deleted)"}</span>
        </div>
        {#each segments as seg, si (si)}
          {#if seg.type === "gap"}
            <div class="gap">
              <span>⋯ {seg.count} unchanged line{seg.count > 1 ? "s" : ""}</span>
              {#if seg.context}<span class="ctx-info">{seg.context}</span>{/if}
            </div>
          {:else}
            {#each seg.rows as row, ri (ri)}
              <!-- One grid row = old side | new side (side-by-side like VS
                   Code, owner 2026-10-10 review). -->
              <div class="trow">
                <span class="ln">{row.leftNo ?? ""}</span>
                <span class="cell old {sideClass(row, 'old')}" class:filled={row.left !== null}>{row.left ?? ""}</span>
                <span class="ln">{row.rightNo ?? ""}</span>
                <span class="cell new {sideClass(row, 'new')}" class:filled={row.right !== null}>{row.right ?? ""}</span>
              </div>
            {/each}
          {/if}
        {/each}
      </div>
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
    gap: 8px;
    padding: 4px 10px;
    border-bottom: 1px solid var(--viewer-border);
    background: var(--bg-raised);
    font-size: 12.5px;
    flex-shrink: 0;
  }

  .title {
    font-weight: 600;
    white-space: nowrap;
  }

  .pair {
    color: var(--text-muted);
    font-weight: 400;
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

  .back,
  .close {
    padding: 0 8px;
    font-size: 15px;
    color: var(--text-muted);
    border-radius: var(--radius);
  }

  .back {
    font-size: 17px;
    line-height: 1;
  }

  .back:hover,
  .close:hover {
    background: var(--bg-hover);
    color: var(--text);
  }

  .diff-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  /* Side-by-side grid: line numbers hug their text column, sides split the
     width. Long lines wrap; a shared grid row keeps the old/new pair on
     one visual row even then. */
  .table {
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 18px;
    width: 100%;
  }

  .thead,
  .trow {
    display: grid;
    grid-template-columns: 3.2em 1fr 3.2em 1fr;
  }

  .thead {
    position: sticky;
    top: 0;
    background: var(--viewer-bg);
    border-bottom: 1px solid var(--viewer-border);
    color: var(--text-muted);
    font-size: 11px;
    z-index: 1;
  }

  .thead .cell {
    padding: 3px 8px;
    font-style: italic;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ln {
    padding-right: 6px;
    text-align: right;
    color: var(--text-muted);
    opacity: 0.7;
    font-size: 10.5px;
    user-select: none;
    border-right: 1px solid var(--viewer-border);
  }

  .cell {
    padding: 0 8px;
    white-space: pre-wrap;
    word-break: break-all;
    min-width: 0;
  }

  .cell.chg.old {
    background: var(--git-del-bg);
  }

  .cell.chg.new {
    background: var(--git-add-bg);
  }

  .cell.hole {
    background: repeating-linear-gradient(
      -45deg,
      transparent,
      transparent 6px,
      color-mix(in srgb, var(--text-muted) 10%, transparent) 6px,
      color-mix(in srgb, var(--text-muted) 10%, transparent) 12px
    );
  }

  .gap {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 2px 12px;
    background: color-mix(in srgb, var(--bg-raised) 60%, transparent);
    color: var(--text-muted);
    font-size: 10.5px;
    font-family: var(--font-ui);
    border-block: 1px solid var(--viewer-border);
    user-select: none;
  }

  .gap .ctx-info {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    opacity: 0.8;
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
