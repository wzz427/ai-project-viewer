<script lang="ts">
  import { activeProject } from "$lib/stores/projectStore.svelte";
  import { gitState, openCommit, openDiff, refreshGit } from "$lib/stores/gitStore.svelte";
  import { openFile } from "$lib/stores/tabsStore.svelte";
  import { letterClass, relativeTime } from "$lib/services/gitFormat";
  import { fileNameOf } from "$lib/services/viewerType";
  import type { GitChangeEntry } from "$lib/services/tauri";

  const project = $derived(activeProject());
  const st = $derived(project ? gitState.byRoot[project.rootPath] : undefined);
  const snap = $derived(st?.snapshot ?? null);
  // §50/§58: subdirectory mode surfaces the repository name + scope.
  const repoName = $derived(
    snap?.gitRoot
      ? snap.gitRoot.replace(/[\\/]+$/, "").split(/[\\/]/).pop()!
      : null,
  );

  // VS Code-style collapsible sections (owner 2026-10-10 visual review).
  let collapsed = $state<Record<string, boolean>>({});

  function toggle(key: string) {
    collapsed[key] = !collapsed[key];
  }

  function dirnameOf(rel: string): string {
    const i = rel.lastIndexOf("/");
    return i === -1 ? "" : rel.slice(0, i);
  }

  function clickEntry(e: GitChangeEntry & { stagedRow: boolean }) {
    if (!project) return;
    if (e.letter === "?") {
      // Untracked files have no diff — open the content (spec-007 D2).
      void openFile(project.rootPath, e.rel);
    } else {
      openDiff(project.rootPath, e.rel, e.stagedRow);
    }
  }

  function clickCommit(hash: string) {
    if (project) openCommit(project.rootPath, hash);
  }

  // Rows carry their group so one handler serves both lists.
  function withGroup(list: GitChangeEntry[], stagedRow: boolean) {
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
    <div class="branch-row" title={snap.upstream ? `Upstream: ${snap.upstream}` : ""}>
      <span class="glyph">⎇</span>
      <span class="branch-name">{snap.branch}</span>
      {#if snap.ahead !== undefined || snap.behind !== undefined}
        <span class="ab">↑{snap.ahead ?? 0} ↓{snap.behind ?? 0}</span>
      {/if}
    </div>
    {#if snap.scopeRel}
      <div class="scope-box">
        <div><span class="label">Repository:</span> {repoName}</div>
        <div><span class="label">Scope:</span> {snap.scopeRel}</div>
      </div>
    {/if}

    <section>
      <button class="sec-head" onclick={() => toggle("changes")} aria-expanded={!collapsed.changes}>
        <span class="chev" class:open={!collapsed.changes}>›</span>
        <span class="sec-title">Changes</span>
        {#if snap.changes.length}<span class="sec-count">{snap.changes.length}</span>{/if}
      </button>
      {#if !collapsed.changes}
        {#each withGroup(snap.changes, false) as e (e.rel)}
          <button
            class="entry"
            title={e.origRel ? `${e.origRel} → ${e.rel}` : e.rel}
            onclick={() => clickEntry(e)}
          >
            <span class="ename">{fileNameOf(e.rel)}</span>
            <span class="edir">{dirnameOf(e.rel)}</span>
            <span class="letter {letterClass(e.letter)}">{e.letter}</span>
          </button>
        {/each}
        {#if snap.changes.length === 0 && snap.staged.length === 0}
          <p class="muted note">No changes.</p>
        {/if}
      {/if}
    </section>

    {#if snap.staged.length > 0}
      <section>
        <button class="sec-head" onclick={() => toggle("staged")} aria-expanded={!collapsed.staged}>
          <span class="chev" class:open={!collapsed.staged}>›</span>
          <span class="sec-title">Staged Changes</span>
          <span class="sec-count">{snap.staged.length}</span>
        </button>
        {#if !collapsed.staged}
          {#each withGroup(snap.staged, true) as e (e.rel)}
            <button
              class="entry"
              title={e.origRel ? `${e.origRel} → ${e.rel}` : e.rel}
              onclick={() => clickEntry(e)}
            >
              <span class="ename">{fileNameOf(e.rel)}</span>
              <span class="edir">{dirnameOf(e.rel)}</span>
              <span class="letter {letterClass(e.letter)}">{e.letter}</span>
            </button>
          {/each}
        {/if}
      </section>
    {/if}

    <section>
      <button class="sec-head" onclick={() => toggle("commits")} aria-expanded={!collapsed.commits}>
        <span class="chev" class:open={!collapsed.commits}>›</span>
        <span class="sec-title">Recent Commits</span>
        {#if snap.commits.length}<span class="sec-count">{snap.commits.length}</span>{/if}
      </button>
      {#if !collapsed.commits}
        {#if snap.commits.length === 0}
          <p class="muted note">No commits yet.</p>
        {/if}
        {#each snap.commits as c, i (c.hash)}
          {@const date = new Date(c.ts).toLocaleString()}
          <button
            class="commit"
            title={`${c.subject}\n${c.author} · ${date}`}
            onclick={() => clickCommit(c.hash)}
          >
            <span class="cgraph" class:head={i === 0}><span class="cdot"></span></span>
            <span class="chash">{c.hash}</span>
            <span class="csubj">{c.subject}</span>
            {#if i === 0 && snap.branch && snap.branch !== "(detached)"}
              <span class="cbadge">{snap.branch}</span>
            {/if}
            <span class="cwhen">{relativeTime(Date.now(), c.ts)}</span>
          </button>
        {/each}
      {/if}
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
  }

  .branch-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px 8px;
    font-size: 12.5px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2px;
  }

  .glyph {
    color: var(--text-muted);
    font-size: 12px;
  }

  .branch-name {
    font-weight: 600;
  }

  .ab {
    color: var(--text-muted);
    font-size: 11.5px;
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

  .sec-head {
    display: flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    padding: 5px 4px;
    border-radius: var(--radius);
    cursor: pointer;
    user-select: none;
  }

  .sec-head:hover {
    background: var(--bg-hover);
  }

  .chev {
    display: inline-block;
    width: 14px;
    text-align: center;
    color: var(--text-muted);
    font-size: 11px;
    transition: transform 0.1s ease;
  }

  .chev.open {
    transform: rotate(90deg);
  }

  .sec-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-muted);
    flex: 1;
    text-align: left;
  }

  .sec-count {
    min-width: 18px;
    padding: 0 5px;
    border-radius: 9px;
    background: var(--bg-active);
    color: var(--text-muted);
    font-size: 10.5px;
    line-height: 16px;
    text-align: center;
  }

  /* File row (VS Code pattern): bright FILENAME, dim dirname after it,
     status letter at the far right (owner 2026-10-10 visual review). */
  .entry {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 2px 6px 2px 22px;
    border-radius: var(--radius);
    font-size: 12.5px;
    text-align: left;
    cursor: pointer;
  }

  .entry:hover {
    background: var(--bg-hover);
  }

  .ename {
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
    min-width: 0;
  }

  .edir {
    color: var(--text-muted);
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1 1 0;
    min-width: 3em;
  }

  .letter {
    flex-shrink: 0;
    margin-left: auto;
    font-weight: 700;
    font-size: 11px;
  }

  /* Commit row (VS Code Graph flavor): rail with a dot per commit, hash in
     the accent color, subject, HEAD pill, dim relative time at the right. */
  .commit {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 3px 6px 3px 8px;
    border-radius: var(--radius);
    font-size: 12px;
    text-align: left;
    cursor: pointer;
  }

  .commit:hover {
    background: var(--bg-hover);
  }

  .cgraph {
    position: relative;
    width: 12px;
    align-self: stretch;
    flex-shrink: 0;
  }

  .cgraph::before {
    content: "";
    position: absolute;
    left: 5px;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--border);
  }

  .cdot {
    position: absolute;
    left: 2.5px;
    top: 50%;
    transform: translateY(-50%);
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
  }

  .cgraph.head .cdot {
    background: transparent;
    border: 1.5px solid var(--accent);
    width: 5px;
    height: 5px;
  }

  .chash {
    flex-shrink: 0;
    color: var(--git-m);
    font-family: var(--font-mono);
    font-size: 11px;
  }

  .csubj {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex-shrink: 1;
    min-width: 0;
  }

  .cbadge {
    flex-shrink: 0;
    padding: 0 6px;
    border-radius: 8px;
    background: var(--bg-active);
    color: var(--text-muted);
    font-size: 10px;
    line-height: 15px;
  }

  .cwhen {
    margin-left: auto;
    flex-shrink: 0;
    font-size: 10.5px;
    color: var(--text-muted);
  }
</style>
