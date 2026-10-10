<script lang="ts">
  import { onMount } from "svelte";
  import ProjectTabs from "$lib/components/ProjectTabs/ProjectTabs.svelte";
  import SidebarHeader from "$lib/components/SidebarHeader/SidebarHeader.svelte";
  import FilesPanel from "$lib/components/SidebarPanels/FilesPanel.svelte";
  import GitPanel from "$lib/components/SidebarPanels/GitPanel.svelte";
  import SettingsPanel from "$lib/components/SidebarPanels/SettingsPanel.svelte";
  import EmptyState from "$lib/components/EmptyState/EmptyState.svelte";
  import ToastHost from "$lib/components/Toast/ToastHost.svelte";
  import { initTheme } from "$lib/stores/settingsStore.svelte";
  import { recordStartup, recordBuildTime } from "$lib/stores/diagnosticsStore.svelte";
  import { projectState, activeProject } from "$lib/stores/projectStore.svelte";
  import { toast } from "$lib/stores/toastStore.svelte";
  import {
    installShortcutDispatcher,
    onShortcut,
  } from "$lib/services/shortcuts";
  import { startupElapsedMs } from "$lib/services/tauri";
  import { invoke } from "@tauri-apps/api/core";
  import {
    addProjectFromPath,
    setSidebarMode,
    setSidebarWidth,
  } from "$lib/stores/projectStore.svelte";
  import FileTabs from "$lib/components/ProjectTabs/FileTabs.svelte";
  import ActiveViewer from "$lib/components/Viewers/ActiveViewer.svelte";
  import {
    activeTab,
    closeFile,
    cycleTab,
    refreshActiveFile,
  } from "$lib/stores/tabsStore.svelte";
  import { refreshProject } from "$lib/stores/fileTreeStore.svelte";
  import { tabsState } from "$lib/stores/tabsStore.svelte";
  import {
    gitDiffSlot,
    gitNeedsInitialScan,
    markGitSeen,
    refreshGit,
    refreshGitNow,
  } from "$lib/stores/gitStore.svelte";
  import { badgeText } from "$lib/services/gitFormat";
  import { gitSnapshotOf } from "$lib/stores/gitStore.svelte";
  import DiffViewer from "$lib/components/Viewers/DiffViewer.svelte";
  import { getCurrentWindow } from "@tauri-apps/api/window";

  function tabsOf(rootPath: string) {
    return tabsState.byRoot[rootPath]?.openFiles ?? [];
  }

  // ↻ refreshes BOTH the tree and git (spec-007 D13): the 0.6.6 spin
  // feedback naturally covers the combined work.
  async function refreshAll(rootPath: string) {
    await Promise.all([refreshProject(rootPath), refreshGit(rootPath)]);
  }

  import { openSearchPanel } from "@codemirror/search";
  import { getActiveSearchView } from "$lib/components/Viewers/codeSearchRegistry";
  import { focusActiveFind } from "$lib/components/Viewers/activeFind";

  // §17 ProjectSession.sidebarMode — per project, persisted since Phase 4.
  const project = $derived(activeProject());
  const sidebarMode = $derived(project?.sidebarMode ?? "files");

  // The single-slot diff view (spec-007 D3) takes over the viewer body
  // while set; opening/activating a file tab closes it (tabsStore).
  const diffShowing = $derived(
    !!gitDiffSlot.current && !!project
    && gitDiffSlot.current.rootPath === project.rootPath,
  );

  // Real P0 behaviors (V1.5 §146/§147). The dispatcher claims the keydown at
  // capture phase, so these run instead of any browser default — Ctrl+R must
  // refresh the project, never reload the WebView (formal acceptance item).
  // Sidebar drag-resize (owner 2026-10-01). Plain mouse events, not HTML5
  // DnD; every move writes the per-project width and the debounced save
  // loop coalesces the stream into one disk write (V1.5 §26).
  let resizing = $state(false);

  function startResize(e: MouseEvent) {
    const proj = project;
    if (!proj) return;
    e.preventDefault();
    resizing = true;
    const startX = e.clientX;
    const startWidth = proj.sidebarWidth;
    const onMove = (ev: MouseEvent) => {
      setSidebarWidth(proj.rootPath, startWidth + ev.clientX - startX);
    };
    const onUp = () => {
      resizing = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      document.documentElement.classList.remove("col-resizing");
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    document.documentElement.classList.add("col-resizing");
  }

  // Right-click copy (owner 2026-10-02: a selection without a copy path
  // is useless). Only fires when text is actually selected inside the
  // viewer; the menu swallows mousedown so the selection survives.
  let copyMenu = $state<{ x: number; y: number } | null>(null);

  function onViewerContextMenu(e: MouseEvent) {
    const sel = window.getSelection()?.toString() ?? "";
    if (!sel.trim()) return;
    e.preventDefault();
    e.stopPropagation();
    copyMenu = { x: e.clientX, y: e.clientY };
  }

  function closeCopyMenu(e?: MouseEvent) {
    // The menu's own mousedown must not reach here before its click fires.
    const el = document.querySelector(".copy-menu");
    if (e && el && e.target instanceof Node && el.contains(e.target)) return;
    copyMenu = null;
  }

  function doCopy(e: Event) {
    e.stopPropagation();
    const n = (window.getSelection()?.toString() ?? "").length;
    if (document.execCommand("copy")) {
      toast(`✓ Copied ${n} characters`);
    }
    copyMenu = null;
  }

  // Keyboard resize: ←/→ nudges by 16px (a11y for the separator handle).
  function resizeViaKeyboard(e: KeyboardEvent) {
    const proj = project;
    if (!proj) return;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      setSidebarWidth(proj.rootPath, proj.sidebarWidth - 16);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      setSidebarWidth(proj.rootPath, proj.sidebarWidth + 16);
    }
  }

  function wireShortcuts() {
    const unsubs = [
      onShortcut("ctrl+w", () => {
        const root = project?.rootPath;
        const tab = root ? activeTab(root) : undefined;
        if (root && tab) closeFile(root, tab.relativePath);
      }),
      onShortcut("ctrl+f", () => {
        // Unified Ctrl+F (SPEC-INFRA-003): the active viewer's toolbar owns
        // the shortcut; CodeMirror's panel stays as the no-owner fallback.
        if (focusActiveFind()) return;
        const view = getActiveSearchView();
        if (view) openSearchPanel(view);
      }),
      onShortcut("ctrl+tab", () => {
        if (project) cycleTab(project.rootPath, 1);
      }),
      onShortcut("ctrl+shift+tab", () => {
        if (project) cycleTab(project.rootPath, -1);
      }),
      onShortcut("ctrl+r", () => {
        if (!project) return;
        void refreshProject(project.rootPath);
        void refreshActiveFile(project.rootPath);
        // §73 manual refresh covers git too (spec-007 D13) — one gesture,
        // one coherent state.
        void refreshGit(project.rootPath);
      }),
    ];
    return () => unsubs.forEach((u) => u());
  }

  // --- Git auto-refresh triggers (§73; spec-007 R8) ---
  // Project Open / startup: every project lacking a snapshot gets scanned
  // (project-tab indicators need all of them, §46 first layer). New tabs
  // from session restore or the picker land here too. `seen` is a plain
  // Set so this effect never re-runs off gitState's own writes.
  $effect(() => {
    void projectState.tabs.map((t) => t.rootPath).length;
    for (const t of projectState.tabs) {
      if (gitNeedsInitialScan(t.rootPath)) {
        markGitSeen(t.rootPath);
        void refreshGitNow(t.rootPath);
      }
    }
  });

  // Project Switch In: the newly active project refreshes immediately.
  $effect(() => {
    const root = project?.rootPath;
    if (root && !gitNeedsInitialScan(root)) void refreshGit(root);
  });

  // Window Regain Focus: active project only (§78).
  onMount(() => {
    let unlisten: (() => void) | undefined;
    void getCurrentWindow()
      .onFocusChanged(({ payload: focused }) => {
        if (!focused) return;
        const root = activeProject()?.rootPath;
        if (root) void refreshGit(root);
      })
      .then((u) => (unlisten = u))
      .catch(() => {});
    return () => unlisten?.();
  });

  onMount(() => {
    initTheme();
    installShortcutDispatcher();
    const unwire = wireShortcuts();

    // Test hook (testing.md §1): auto-add a project without the native
    // picker so GUI tests never surface a dialog on the owner's desktop.
    void invoke<string | null>("test_project_arg").then((path) => {
      if (path) void addProjectFromPath(path);
    });

    startupElapsedMs().then(recordStartup).catch(() => {});
    invoke<number>("build_timestamp").then(recordBuildTime).catch(() => {});

    return () => unwire();
  });
</script>

<div class="shell">
  <ProjectTabs />
  <div class="body">
    <aside class="sidebar" style:width={`${project?.sidebarWidth ?? 260}px`}>
      <SidebarHeader
        mode={sidebarMode}
        onModeChange={(m) => project && setSidebarMode(project.rootPath, m)}
        onRefresh={project ? () => refreshAll(project.rootPath) : undefined}
        gitBadge={project ? badgeText(gitSnapshotOf(project.rootPath)?.uniqueCount ?? 0) : null}
      />
      <div class="sidebar-panel">
        {#if sidebarMode === "files"}
          <FilesPanel />
        {:else if sidebarMode === "git"}
          <GitPanel />
        {:else}
          <SettingsPanel />
        {/if}
      </div>
    </aside>
    <!-- role=slider (not separator): a width-adjusting handle with arrow-key
         control; Svelte's a11y rules don't recognize focusable separators. -->
    <div
      class="sidebar-resizer"
      class:active={resizing}
      onmousedown={startResize}
      onkeydown={resizeViaKeyboard}
      role="slider"
      aria-orientation="vertical"
      aria-label="Sidebar width"
      aria-valuemin={200}
      aria-valuemax={600}
      aria-valuenow={project?.sidebarWidth ?? 260}
      tabindex="0"
    ></div>
    <main class="viewer">
      {#if projectState.tabs.length === 0}
        <EmptyState />
      {:else if project}
        <div class="viewer-stack">
          <FileTabs rootPath={project.rootPath} />
          {#if tabsOf(project.rootPath).length > 0 || diffShowing}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="viewer-body"
                role="region"
                aria-label="File content"
                oncontextmenu={onViewerContextMenu}
              >
                {#if diffShowing}
                  <DiffViewer />
                {:else}
                  <ActiveViewer rootPath={project.rootPath} />
                {/if}
              </div>
          {:else}
            <div class="viewer-placeholder">
              <div class="placeholder-card">
                <h2>{project.name}</h2>
                <p class="mono muted">{project.rootPath}</p>
                <p class="muted">Open a file from the tree to view it.</p>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </main>
  </div>
  {#if copyMenu}
    <button
      class="copy-menu"
      style="left: {copyMenu.x}px; top: {copyMenu.y}px"
      onmousedown={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
      onclick={doCopy}
      oncontextmenu={(e) => e.preventDefault()}
    >Copy</button>
  {/if}
  <ToastHost />
</div>

<svelte:window onmousedown={closeCopyMenu} />

<style>
  .shell {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .body {
    flex: 1;
    display: flex;
    min-height: 0;
  }

  .sidebar {
    min-width: 200px;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border);
    background: var(--bg-raised);
  }

  .sidebar-resizer {
    width: 4px;
    flex-shrink: 0;
    margin-left: -2px;
    z-index: 5;
    cursor: col-resize;
    background: transparent;
  }

  .sidebar-resizer:hover,
  .sidebar-resizer.active {
    background: var(--border);
  }

  .sidebar-panel {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    min-height: 0;
  }

  .viewer {
    flex: 1;
    min-width: 0;
    background: var(--viewer-bg);
  }

  .viewer-stack {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .viewer-body {
    flex: 1;
    min-height: 0;
  }

  .viewer-placeholder {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .placeholder-card {
    text-align: center;
    padding: 24px 32px;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
  }

  .copy-menu {
    position: fixed;
    z-index: 200;
    padding: 5px 14px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    font-size: 12px;
    cursor: pointer;
  }

  .copy-menu:hover {
    background: var(--bg-hover);
  }

  .placeholder-card h2 {
    margin: 0 0 8px;
    font-size: 15px;
  }

  .placeholder-card p {
    margin: 4px 0;
  }
</style>
