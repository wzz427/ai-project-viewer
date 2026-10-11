<script lang="ts">
  import { pin, unpin, treeState, joinRel, contextMenuTarget } from "$lib/stores/fileTreeStore.svelte";
  import { fileHandoffGroups } from "$lib/services/handoffMenu";

  let {
    rootPath,
    parentRel,
    name,
    isDir,
    x,
    y,
    onclose,
  }: {
    rootPath: string;
    parentRel: string;
    name: string;
    isDir: boolean;
    x: number;
    y: number;
    onclose: () => void;
  } = $props();

  const st = $derived(treeState.byRoot[rootPath]!);
  const pinned = $derived(st.pinnedItems[parentRel]?.includes(name) ?? false);

  // Entry.run() may still be settling after onclose unmounts this menu —
  // the built groups carry plain-string snapshots, never live props
  // (lessons L12). Derived for lint-cleanliness; props are fixed per open.
  const groups = $derived(
    fileHandoffGroups(rootPath, joinRel(parentRel, name), name, isDir, {
      includeOpen: true,
    }),
  );

  let el = $state<HTMLElement | null>(null);

  // Clamp inside the viewport once mounted (menu was clipped at the
  // bottom-left window edge before, owner 2026-10-10).
  let left = $state(0);
  let top = $state(0);
  $effect(() => {
    if (!el) return;
    ({ left, top } = clampMenu(el, x, y));
  });

  // While this menu is open, its row owns the tree highlight (owner
  // 2026-10-10). Owner 2026-10-12: ACTING on an item must KEEP the row lit
  // after close — "Show in File Explorer" on notes.txt used to drop the
  // highlight back onto the previously-active file, which reads as the
  // wrong row being selected. Dismissing without acting still clears it;
  // the next file activation (row click / open) hands the highlight back.
  let acted = false;
  $effect(() => {
    contextMenuTarget.rootPath = rootPath;
    contextMenuTarget.rel = joinRel(parentRel, name);
    return () => {
      if (!acted) {
        contextMenuTarget.rootPath = null;
        contextMenuTarget.rel = null;
      }
    };
  });

  function close(e?: Event) {
    if (e && e.target instanceof Node && el?.contains(e.target)) return;
    onclose();
  }

  $effect(() => {
    window.addEventListener("mousedown", close, { capture: true });
    return () =>
      window.removeEventListener("mousedown", close, { capture: true });
  });
  import { clampMenu } from "$lib/components/ContextMenu/menuPosition";

  function togglePin() {
    // Pin changes sibling DISPLAY order only — never the path on disk
    // (V1.5 §37/§38; files and folders are both pinnable).
    acted = true;
    if (pinned) unpin(rootPath, parentRel, name);
    else pin(rootPath, parentRel, name);
    onclose();
  }
</script>

<div class="menu" bind:this={el} style="left: {left}px; top: {top}px">
  <div class="menu-path mono muted">
    {isDir ? "folder" : "file"} · {name}
  </div>
  {#each groups as group, gi}
    {#if gi > 0}
      <div class="sep"></div>
    {/if}
    {#each group as entry (entry.id)}
      <button
        class="menu-item"
        data-menu-id={entry.id}
        onclick={() => {
          acted = true;
          void entry.run();
          onclose();
        }}
      >{entry.label}</button>
    {/each}
  {/each}
  <div class="sep"></div>
  <button class="menu-item" onclick={togglePin}>
    {pinned ? "Unpin" : "Pin to Top"}
  </button>
</div>

<style>
  .menu {
    position: fixed;
    z-index: 100;
    min-width: 200px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 4px;
  }

  .menu-path {
    padding: 4px 8px;
    font-size: 11px;
    max-width: 360px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .menu-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 5px 8px;
    border-radius: var(--radius);
  }

  .menu-item:hover {
    background: var(--bg-hover);
  }

  .sep {
    height: 1px;
    background: var(--border);
    margin: 4px 6px;
  }
</style>
