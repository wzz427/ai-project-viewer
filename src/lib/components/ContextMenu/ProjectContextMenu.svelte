<script lang="ts">
  import { ask } from "@tauri-apps/plugin-dialog";
  import {
    isProjectTrusted,
    removeProject,
    setProjectTrusted,
    type ProjectTab,
  } from "$lib/stores/projectStore.svelte";
  import { toast } from "$lib/stores/toastStore.svelte";
  import { projectHandoffGroups } from "$lib/services/handoffMenu";

  let {
    project,
    x,
    y,
    onRefreshProject,
    onclose,
  }: {
    project: ProjectTab;
    x: number;
    y: number;
    /** §141 Refresh Project — forwarded from App's refreshAll (tree+git). */
    onRefreshProject?: (rootPath: string) => Promise<void>;
    onclose: () => void;
  } = $props();

  // The close listener runs in the capture phase on window, i.e. BEFORE any
  // bubbling handler on the menu itself — closings must spare the menu.
  let el = $state<HTMLElement | null>(null);

  // Clamp inside the viewport once mounted (menu was clipped at the
  // bottom-left window edge before, owner 2026-10-10).
  let left = $state(0);
  let top = $state(0);
  $effect(() => {
    if (!el) return;
    ({ left, top } = clampMenu(el, x, y));
  });

  // §141 handoff block — built with plain-string snapshots (lessons L12).
  const handoff = $derived(projectHandoffGroups(project.rootPath));
  // §129/§141: revocable per project; label reflects the CURRENT state.
  const trusted = $derived(isProjectTrusted(project.rootPath));

  function close(e?: Event) {
    if (e && e.target instanceof Node && el?.contains(e.target)) return;
    onclose();
  }

  async function confirmRemove() {
    const tab = project;
    onclose();
    // Removing only detaches it from the viewer — never touches disk (V1.5 §15).
    const yes = await ask(
      `Remove "${tab.name}" from AI Project Viewer?\n\nThe folder on disk is not modified or deleted.`,
      { title: "Remove Project", kind: "warning" },
    );
    if (yes) {
      removeProject(tab.id);
      toast(`Removed "${tab.name}" (folder untouched on disk).`);
    }
  }
  import { clampMenu } from "$lib/components/ContextMenu/menuPosition";

  $effect(() => {
    window.addEventListener("mousedown", close, { capture: true });
    return () =>
      window.removeEventListener("mousedown", close, { capture: true });
  });
</script>

<div class="menu" bind:this={el} style="left: {left}px; top: {top}px">
  <div class="menu-path mono muted">{project.rootPath}</div>
  {#each handoff as group, gi}
    {#if gi > 0}
      <div class="sep"></div>
    {/if}
    {#each group as entry (entry.id)}
      <button
        class="menu-item"
        data-menu-id={entry.id}
        onclick={() => {
          void entry.run();
          onclose();
        }}
      >{entry.label}</button>
    {/each}
  {/each}
  <div class="sep"></div>
  {#if onRefreshProject}
    <button
      class="menu-item"
      data-menu-id="refresh-project"
      onclick={() => {
        void onRefreshProject?.(project.rootPath);
        onclose();
      }}
    >Refresh Project</button>
  {/if}
  <button
    class="menu-item"
    data-menu-id={trusted ? "untrust-project" : "trust-project"}
    onclick={() => {
      // Capture BEFORE mutating: `trusted` is a derived and re-reads the
      // NEW value synchronously, which flipped the toast text (0.6.12).
      const wasTrusted = trusted;
      setProjectTrusted(project.rootPath, !wasTrusted);
      toast(
        wasTrusted
          ? `“${project.name}” is no longer trusted for execution.`
          : `“${project.name}” is now trusted for execution.`,
      );
      onclose();
    }}
  >{trusted ? "Untrust Project" : "Trust Project for Execution"}</button>
  <div class="sep"></div>
  <button class="menu-item" onclick={confirmRemove}>Remove Project</button>
</div>

<style>
  .menu {
    position: fixed;
    z-index: 100;
    min-width: 220px;
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
