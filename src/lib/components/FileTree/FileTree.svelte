<script lang="ts">
  import { untrack } from "svelte";
  import { visibleSorted } from "$lib/services/treeSort";
  import {
    refreshProject,
    treeState,
    TREE_ROOT,
  } from "$lib/stores/fileTreeStore.svelte";
  import { settings } from "$lib/stores/settingsStore.svelte";
  import TreeItem from "$lib/components/FileTree/TreeItem.svelte";

  let { rootPath }: { rootPath: string } = $props();
  let host = $state<HTMLElement | null>(null);

  // Read reactively (rootPath changes when the user switches project tabs);
  // refreshProject below creates the per-project state on first run.
  const st = $derived(treeState.byRoot[rootPath]);

  // Active project mount/switch (owner 2026-10-17 staleness report): only
  // the ACTIVE project is watched (§77), so writes landing while this
  // project sits in a background tab are invisible — switching back IS the
  // "look again" moment. Re-list the root AND every previously loaded
  // level; a first activation has nothing deeper cached, so it degenerates
  // to the old root-only load exactly, and lazy levels stay lazy (§27).
  // untrack is LOAD-BEARING: refreshProject reads the very state it writes
  // (Object.keys(st.children) vs applyListing's writes) — tracked, the
  // effect would re-trigger itself into an infinite re-list loop that
  // starves the UI thread. Only rootPath stays tracked (re-run on switch).
  $effect(() => {
    const root = rootPath;
    untrack(() => void refreshProject(root));
  });

  // VS Code reveal (owner 2026-10-10): scroll the revealed file's row into
  // view. Reads the parent level's listing + expansion so the effect
  // re-runs when revealInTree's async level loads actually land.
  $effect(() => {
    const stv = st;
    if (!stv || !host) return;
    const target = stv.revealTarget;
    if (!target) return;
    const parentRel = target.includes("/")
      ? target.slice(0, target.lastIndexOf("/"))
      : TREE_ROOT;
    const kidsLoaded = !!stv.children[parentRel];
    const expanded = stv.expandedFolders.includes(parentRel);
    if (!kidsLoaded || !expanded) return; // level still loading
    const row = host.querySelector<HTMLElement>(
      `.row[title="${CSS.escape(target)}"]`,
    );
    if (row) {
      row.scrollIntoView({ block: "nearest" });
      stv.revealTarget = null;
    }
  });

  const rootEntries = $derived(st?.children[TREE_ROOT] ?? []);
  const sorted = $derived(
    visibleSorted(rootEntries, {
      foldersFirst: st?.foldersFirst ?? true,
      showSystemFolders: settings.fileTree.showSystemGeneratedFolders,
      pinned: st?.pinnedItems[TREE_ROOT],
    }),
  );
  const hiddenCount = $derived(st?.hiddenCounts[TREE_ROOT] ?? 0);
  const error = $derived(st?.loadErrors[TREE_ROOT]);
</script>

<div class="file-tree" role="tree" aria-label="Project files" bind:this={host}>
  {#if error}
    <div class="hint error">{error}</div>
  {:else if !st || !st.children[TREE_ROOT]}
    <div class="hint">Loading…</div>
  {:else if sorted.length === 0}
    <div class="hint">Empty folder</div>
  {:else}
    {#each sorted as entry (entry.name)}
      <TreeItem {rootPath} parentRel={TREE_ROOT} {entry} depth={0} />
    {/each}
  {/if}
  {#if hiddenCount > 0 && !settings.fileTree.showSystemGeneratedFolders}
    <div class="hint">
      {hiddenCount} system folder{hiddenCount > 1 ? "s" : ""} hidden
    </div>
  {/if}
</div>

<style>
  .file-tree {
    font-size: var(--text-base);
    overflow-y: auto;
    overflow-x: hidden;
    flex: 1;
    min-height: 0;
    padding-right: 2px;
  }

  .hint {
    display: flex;
    align-items: center;
    padding-left: 8px;
    height: 22px;
    font-size: var(--text-xs);
    color: var(--text-muted);
    font-style: italic;
    user-select: none;
  }

  .hint.error {
    color: var(--danger);
    font-style: normal;
  }
</style>
