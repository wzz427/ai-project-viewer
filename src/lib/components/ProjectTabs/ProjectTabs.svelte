<script lang="ts">
  import {
    projectState,
    activateProject,
    addProjectViaPicker,
    reorderProjects,
    moveProjectToEnd,
    type ProjectTab,
  } from "$lib/stores/projectStore.svelte";
  import { gitDirtyOf } from "$lib/stores/gitStore.svelte";
  import { recentState } from "$lib/stores/recentStore.svelte";
  import { avatarColorOf, avatarInitialOf } from "$lib/services/avatarColor";
  import Icon from "$lib/components/Icon.svelte";
  import ProjectContextMenu from "$lib/components/ContextMenu/ProjectContextMenu.svelte";
  import UpdateButton from "$lib/components/ProjectTabs/UpdateButton.svelte";
  import AddProjectMenu from "$lib/components/ProjectTabs/AddProjectMenu.svelte";

  let {
    /** §141 Refresh Project — same refresh as the header refresh icon (tree+git). */
    onRefreshProject,
  }: { onRefreshProject?: (rootPath: string) => Promise<void> } = $props();

  let menuFor = $state<ProjectTab | null>(null);
  let menuX = $state(0);
  let menuY = $state(0);

  // §10/§46 first layer: clean (check) / dirty (filled dot) for the
  // project's own scope; non-git and not-yet-fetched projects show no
  // symbol. data-state carries the machine-readable value (e2e reads the
  // attribute, not the glyph).
  function dirtyOf(tab: ProjectTab): boolean | undefined {
    return gitDirtyOf(tab.rootPath);
  }

  function openMenu(tab: ProjectTab, e: MouseEvent) {
    e.preventDefault();
    menuFor = tab;
    menuX = e.clientX;
    menuY = e.clientY;
  }

  // --- Drag-reorder (spec-015, owner 2026-10-12) -----------------------
  // Interaction model copied 1:1 from FileTabs (lessons L10 family:
  // WebView2 needs dragenter AND dragover cancelled or drop never fires;
  // cursor-half before/after; the band past the last tab = append at end).
  let dragId = $state<string | null>(null);
  let dropAt = $state<{ id: string; pos: "before" | "after" } | null>(null);
  let bandDrop = $state(false);

  function onDragStart(e: DragEvent, tab: ProjectTab) {
    dragId = tab.id;
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", tab.rootPath);
    }
  }

  function onDragOver(e: DragEvent, tab: ProjectTab) {
    if (dragId === null || dragId === tab.id) return;
    e.preventDefault(); // enter AND over both (L10)
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    dropAt = {
      id: tab.id,
      pos: e.clientX < rect.left + rect.width / 2 ? "before" : "after",
    };
  }

  function onDrop(e: DragEvent, tab: ProjectTab) {
    e.preventDefault();
    const from = dragId;
    const at = dropAt;
    dropAt = null;
    dragId = null;
    if (from && from !== tab.id && at) {
      reorderProjects(from, tab.id, at.pos);
    }
  }

  // Band = everything on the strip that is not a tab (+ button included:
  // it lives on the strip, spec-015 D3). Dropping there = move to end.
  function overBar(e: DragEvent) {
    if (dragId === null) return;
    if ((e.target as HTMLElement).closest(".tab")) return; // tab handles it
    e.preventDefault(); // dragenter AND dragover both (L10)
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    bandDrop = true;
  }

  function dropBar(e: DragEvent) {
    const active = bandDrop;
    bandDrop = false;
    if (!active) return;
    e.preventDefault();
    const from = dragId;
    dragId = null;
    if (from) moveProjectToEnd(from);
  }

  // Open Recent (V1.5 §198-b): with any history the + opens a menu
  // (Browse first, recents beneath); with none it stays the plain picker
  // so first use is unchanged. The menu anchors under the + button.
  let addMenu = $state<{ x: number; y: number } | null>(null);

  function onAddClick(e: MouseEvent) {
    if (recentState.folders.length === 0) {
      void addProjectViaPicker();
      return;
    }
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    addMenu = { x: rect.left, y: rect.bottom + 4 };
  }
</script>

<!-- spec-014 R1: the project bar is the APP-LEVEL chrome band (40px,
     bottom accent bar, avatar-badged tabs) — deliberately orthogonal to
     the browser-style file tab strip below it (28px, top hairline). -->
<div
  class="project-tabs"
  class:band-drop={bandDrop}
  role="presentation"
  ondragenter={overBar}
  ondragover={overBar}
  ondragleave={() => (bandDrop = false)}
  ondrop={dropBar}
>
  {#each projectState.tabs as tab (tab.id)}
    <button
      class="tab"
      class:active={tab.id === projectState.activeId}
      class:drop-before={dropAt?.id === tab.id && dropAt.pos === "before"}
      class:drop-after={dropAt?.id === tab.id && dropAt.pos === "after"}
      onclick={() => activateProject(tab.id)}
      oncontextmenu={(e) => openMenu(tab, e)}
      title={tab.rootPath}
      draggable="true"
      ondragstart={(e) => onDragStart(e, tab)}
      ondragenter={(e) => onDragOver(e, tab)}
      ondragover={(e) => onDragOver(e, tab)}
      ondragleave={() => (dropAt = null)}
      ondrop={(e) => onDrop(e, tab)}
    >
      <span class="avatar" style="--avatar: {avatarColorOf(tab.rootPath)}">
        {avatarInitialOf(tab.name)}
      </span>
      <span class="tab-name">{tab.name}</span>
      {#if dirtyOf(tab) !== undefined}
        <span
          class="git-state"
          class:dirty={dirtyOf(tab)}
          data-state={dirtyOf(tab) ? "dirty" : "clean"}
        >
          {#if dirtyOf(tab)}<Icon name="dot" size={12} />{:else}<Icon name="check" size={12} />{/if}
        </span>
      {/if}
    </button>
  {/each}
  <button
    class="add"
    onclick={onAddClick}
    title="Add project"
    aria-label="Add project"
    aria-haspopup="menu"
  >
    <Icon name="plus" />
  </button>
  <UpdateButton />
</div>

{#if menuFor}
  <ProjectContextMenu
    project={menuFor}
    x={menuX}
    y={menuY}
    onRefreshProject={onRefreshProject}
    onclose={() => (menuFor = null)}
  />
{/if}

{#if addMenu}
  <AddProjectMenu x={addMenu.x} y={addMenu.y} onclose={() => (addMenu = null)} />
{/if}

<style>
  .project-tabs {
    display: flex;
    align-items: stretch;
    height: 40px;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
    overflow-x: auto;
    flex-shrink: 0;
  }

  .tab {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 12px;
    border-right: 1px solid var(--border);
    color: var(--text-muted);
    white-space: nowrap;
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast),
      box-shadow var(--transition-fast);
  }

  .tab:hover {
    background: var(--bg-hover);
  }

  /* Active project: fill chip (owner 0.8.0 方案 C) — the old 2px bottom
     accent bar is GONE by decision: it collided with the file tab's top
     hairline whenever the two active tabs sat near each other. Depth now
     comes from the band↔frame value ladder, the chip fill + weight. */
  .tab.active {
    background: var(--accent-soft);
    color: var(--text);
    font-weight: 600;
  }

  /* Drop indicators (spec-015, same language as file tabs): line above
     the target = insert before it, line below = after; declared AFTER
     .active so the transient indicator wins the box-shadow during drag. */
  .tab.drop-before {
    background: var(--bg-hover);
    box-shadow: inset 0 2px 0 var(--accent);
  }

  .tab.drop-after {
    background: var(--bg-hover);
    box-shadow: inset 0 -2px 0 var(--accent);
  }

  .project-tabs.band-drop {
    box-shadow: inset -2px 0 0 var(--accent);
  }

  /* Avatar badge (spec-014 D3): 15% tint of the project's identity hue,
     initial in the hue — identity without loudness. Light theme darkens
     the letter (72% hue + ink) — full-hue letters fell below 3:1 on pale
     tints for teal/amber/green (verified in specs/spec-014 §六). */
  .avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 6px;
    background: color-mix(in srgb, var(--avatar) 15%, transparent);
    color: var(--avatar);
    font-size: var(--text-xs);
    font-weight: 600;
    flex-shrink: 0;
  }

  :global([data-theme="light"]) .avatar {
    color: color-mix(in srgb, var(--avatar) 72%, #232529);
  }

  .tab-name {
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 180px;
  }

  .git-state {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
  }

  .git-state.dirty {
    color: var(--git-d);
  }

  .git-state:not(.dirty) {
    color: var(--text-muted);
  }

  .add {
    display: inline-flex;
    align-items: center;
    padding: 0 10px;
    color: var(--text-muted);
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast);
  }

  .add:hover {
    background: var(--bg-hover);
    color: var(--text);
  }
</style>
