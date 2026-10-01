<script lang="ts">
  import { visibleSorted } from "$lib/services/treeSort";
  import {
    loadRoot,
    treeState,
    TREE_ROOT,
  } from "$lib/stores/fileTreeStore.svelte";
  import TreeItem from "$lib/components/FileTree/TreeItem.svelte";

  let { rootPath }: { rootPath: string } = $props();

  // Read reactively (rootPath changes when the user switches project tabs);
  // loadRoot below creates the per-project state on first run.
  const st = $derived(treeState.byRoot[rootPath]);

  // Root level loads once per project — the ONLY automatic listing; deeper
  // levels load on expand (V1.5 §27 lazy tree).
  $effect(() => {
    void loadRoot(rootPath);
  });

  const rootEntries = $derived(st?.children[TREE_ROOT] ?? []);
  const sorted = $derived(
    visibleSorted(rootEntries, {
      sortMode: st?.sortMode ?? "name",
      foldersFirst: st?.foldersFirst ?? true,
      showSystemFolders: st?.showSystemFolders ?? false,
      pinned: st?.pinnedItems[TREE_ROOT],
    }),
  );
  const hiddenCount = $derived(st?.hiddenCounts[TREE_ROOT] ?? 0);
  const error = $derived(st?.loadErrors[TREE_ROOT]);
</script>

<div class="file-tree" role="tree" aria-label="Project files">
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
  {#if hiddenCount > 0 && !st.showSystemFolders}
    <div class="hint">
      {hiddenCount} system folder{hiddenCount > 1 ? "s" : ""} hidden
    </div>
  {/if}
</div>

<style>
  .file-tree {
    font-size: 12.5px;
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
    font-size: 11px;
    color: var(--text-muted);
    font-style: italic;
    user-select: none;
  }

  .hint.error {
    color: var(--danger, #d1866e);
    font-style: normal;
  }
</style>
