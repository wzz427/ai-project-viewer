<script lang="ts">
  import { activeProject } from "$lib/stores/projectStore.svelte";
  import {
    gitState,
    openDiff,
    refreshGit,
  } from "$lib/stores/gitStore.svelte";
  import { openFile } from "$lib/stores/tabsStore.svelte";
  import { letterClass, relativeTime } from "$lib/services/gitFormat";
  import type { GitChangeEntry } from "$lib/services/tauri";

  const project = $derived(activeProject());
  const st = $derived(
    project ? gitState.byRoot[project.rootPath] : undefined,
  );
  const snap = $derived(st?.snapshot ?? null);
  // §50: subdirectory mode surfaces the repository name + scope (§58).
  const repoName = $derived(
    snap?.gitRoot
      ? snap.gitRoot.replace(/[\\/]+$/, "").split(/[\\/]/).pop()!
      : null,
  );
  const now = $derived(Date.now());

  type Row = GitChangeEntry & { stagedRow: boolean };

  function clickEntry(e: Row) {
    if (!project) return;
    if (e.letter === "?") {
      // Untracked files have no diff — open the content (spec-007 D2).
      void openFile(project.rootPath, e.rel);
    } else {
      openDiff(project.rootPath, e.rel, e.stagedRow);
    }
  }

  // Rows carry their group so one handler serves both lists.
  function withGroup(list: GitChangeEntry[], stagedRow: boolean): Row[] {
    return list.map((e) => ({ ...e, stagedRow }));
  }
</script>

{#if !project}
  <p class="muted note">No project open.</p>
{:else if !snap && st?.loading}
  <p class="muted note">Loading…</p>
{:else if snap?.status === "gitMissing"}
  <div class="state">
    <p class="strong">Git is not installed or cannot be found.</p>
    <p>Git review is unavailable.</p>
    <p>File browsing remains available.</p>
  </div>
{:else if snap?.status === "nonGit"}
  <div class="state">
    <p class="strong">This folder is not a Git repository.</p>
  </div>
{:else if snap?.status === "error"}
  <div class="state">
    <p class="strong">Git state could not be read.</p>
    <p class="mono small break">{snap.error}</p>
    <button class="retry" onclick={() => void refreshGit(project.rootPath)}>
      Retry
    </button>
  </div>
{:else if snap}
  <div class="git-panel">
    <!-- §50 branch row: name + §67 ahead/behind (omitted without upstream). -->
    <div class="branch-row mono" title={snap.upstream ? `Upstream: ${snap.upstream}` : ""}>
      <span class="branch-name">{snap.branch}</span>
      {#if snap.ahead !== undefined || snap.behind !== undefined}
        <span class="ab"> ↑{snap.ahead ?? 0} ↓{snap.behind ?? 0}</span>
      {/if}
    </div>
    {#if snap.scopeRel}
      <div class="scope-box">
        <div><span class="label">Repository:</span> {repoName}</div>
        <div><span class="label">Scope:</span> {snap.scopeRel}</div>
      </div>
    {/if}

    <section>
      <h3>CHANGES {#if snap.changes.length}<span class="count">{snap.changes.length}</span>{/if}</h3>
      {#each withGroup(snap.changes, false) as e (e.rel)}
        <button
          class="entry"
          title={e.origRel ? `${e.origRel} → ${e.rel}` : e.rel}
          onclick={() => clickEntry(e)}
        >
          <span class="letter {letterClass(e.letter)}">{e.letter}</span>
          <span class="path">{e.rel}</span>
        </button>
      {/each}
      {#if snap.changes.length === 0 && snap.staged.length === 0}
        <p class="muted note">No changes.</p>
      {/if}
    </section>

    {#if snap.staged.length > 0}
      <section>
        <h3>STAGED CHANGES <span class="count">{snap.staged.length}</span></h3>
        {#each withGroup(snap.staged, true) as e (e.rel)}
          <button
            class="entry"
            title={e.origRel ? `${e.origRel} → ${e.rel}` : e.rel}
            onclick={() => clickEntry(e)}
          >
            <span class="letter {letterClass(e.letter)}">{e.letter}</span>
            <span class="path">{e.rel}</span>
          </button>
        {/each}
      </section>
    {/if}

    <section>
      <h3>RECENT COMMITS</h3>
      {#if snap.commits.length === 0}
        <p class="muted note">No commits yet.</p>
      {/if}
      {#each snap.commits as c (c.hash)}
        <div class="commit" title={c.subject}>
          <span class="hash mono">{c.hash}</span>
          <span class="subject">{c.subject}</span>
          <span class="when muted">{relativeTime(now, c.ts)}</span>
        </div>
      {/each}
    </section>
  </div>
{:else}
  <p class="muted note">Loading…</p>
{/if}

<style>
  .note {
    margin: 4px 2px;
    font-size: 12px;
  }

  .state {
    padding: 16px 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 12.5px;
  }

  .state p {
    margin: 0;
  }

  .strong {
    font-weight: 600;
  }

  .small {
    font-size: 11px;
    opacity: 0.8;
  }

  .break {
    word-break: break-all;
  }

  .retry {
    align-self: flex-start;
    margin-top: 4px;
    padding: 3px 12px;
    font-size: 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-hover);
    cursor: pointer;
  }

  .git-panel {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .branch-row {
    padding: 2px 4px 6px;
    font-size: 12.5px;
    border-bottom: 1px solid var(--border);
  }

  .branch-name {
    font-weight: 600;
  }

  .ab {
    color: var(--text-muted);
  }

  /* §58: lightweight subdirectory-mode explainer. */
  .scope-box {
    margin: 6px 0 2px;
    padding: 6px 8px;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    font-size: 11.5px;
  }

  .scope-box .label {
    color: var(--text-muted);
  }

  section h3 {
    margin: 10px 2px 4px;
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
    padding: 2px 4px;
    border-radius: var(--radius);
    font-size: 12px;
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

  .path {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .commit {
    display: flex;
    align-items: baseline;
    gap: 6px;
    padding: 2px 4px;
    font-size: 12px;
    border-radius: var(--radius);
  }

  .commit:hover {
    background: var(--bg-hover);
  }

  .hash {
    flex-shrink: 0;
    color: var(--text-muted);
    font-size: 11px;
  }

  .subject {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .when {
    margin-left: auto;
    flex-shrink: 0;
    font-size: 10.5px;
  }
</style>
