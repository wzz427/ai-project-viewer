<script lang="ts">
  import { onMount } from "svelte";
  import {
    addProjectViaPicker,
    addProjectFromPath,
  } from "$lib/stores/projectStore.svelte";
  import { recentState } from "$lib/stores/recentStore.svelte";
  import { pathsExist } from "$lib/services/tauri";
  import { recentName, recentParent } from "$lib/services/recentList";

  // Same one-shot staleness check as the + menu's Open Recent list
  // (V1.5 §198-b): a dead folder grays out but stays clickable into the
  // standard "Cannot open folder" error. This page is read-only — the ✕
  // and Clear management live in the + menu only (spec-010 D6).
  let missing = $state<Set<string>>(new Set());

  onMount(() => {
    const snapshot = [...recentState.folders];
    if (snapshot.length === 0) return;
    void pathsExist(snapshot)
      .then((flags) => {
        missing = new Set(snapshot.filter((_, i) => !flags[i]));
      })
      .catch(() => {});
  });
</script>

<!-- Copy per V1.5 §151; recent list per §198-b. -->
<div class="empty-state">
  <h1>AI Project Viewer</h1>
  <p class="muted">Open your first project</p>
  <button class="open-folder" onclick={() => addProjectViaPicker()}>Open Folder</button>
  {#if recentState.folders.length > 0}
    <div class="recent" data-menu-id="empty-recent">
      <div class="recent-title">Recent</div>
      {#each recentState.folders as path (path)}
        <button
          class="recent-item"
          class:missing={missing.has(path)}
          title={path}
          data-recent-path={path}
          onclick={() => void addProjectFromPath(path)}
        >
          <span class="name">{recentName(path)}</span>
          <span class="path">{recentParent(path)}</span>
        </button>
      {/each}
    </div>
  {/if}
  <p class="tagline">Read. Review. Run. Hand off.</p>
</div>

<style>
  .empty-state {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }

  h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }

  p {
    margin: 0;
  }

  .open-folder {
    margin-top: 12px;
    padding: 7px 20px;
    background: var(--accent);
    color: var(--accent-text);
    border-radius: var(--radius);
    font-size: 13px;
  }

  .open-folder:hover {
    filter: brightness(1.1);
  }

  .recent {
    margin-top: 18px;
    width: 380px;
    max-width: 80vw;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .recent-title {
    font-size: 11px;
    color: var(--text-muted);
    padding: 0 8px 4px;
  }

  .recent-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 5px 8px;
    border-radius: var(--radius);
    text-align: left;
  }

  .recent-item:hover {
    background: var(--bg-hover);
  }

  .recent-item.missing {
    opacity: 0.45;
  }

  .recent-item .name {
    font-size: 13px;
    color: var(--text);
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .recent-item .path {
    font-size: 11px;
    color: var(--text-muted);
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tagline {
    margin-top: 10px;
    color: var(--text-muted);
    font-size: 12px;
  }
</style>
