<script lang="ts">
  import {
    settings,
    setFontSize,
    setShowSystemFolders,
    setTheme,
    setVsCodeNewWindow,
    type Theme,
  } from "$lib/stores/settingsStore.svelte";
  import { diagnostics } from "$lib/stores/diagnosticsStore.svelte";
  import { invoke } from "@tauri-apps/api/core";
  import { activeProject } from "$lib/stores/projectStore.svelte";
  import {
    refreshProject,
    setFoldersFirst,
    treeState,
  } from "$lib/stores/fileTreeStore.svelte";

  const themes: { value: Theme; label: string }[] = [
    { value: "system", label: "System" },
    { value: "dark", label: "Dark" },
    { value: "light", label: "Light" },
  ];

  const project = $derived(activeProject());
  let channel = $state("…");
  // Tree preferences are per-project (V1.5 §17); the section drives the
  // active one. Owner 2026-10-01: the old "⋯" menu content lives here now.
  const tree = $derived(project ? treeState.byRoot[project.rootPath] : undefined);

  $effect(() => {
    void invoke<string>("channel").then((c) => (channel = c)).catch(() => {});
  });
</script>

<div class="settings-panel">
  {#if project && tree}
    <section>
      <h3>File Tree</h3>
      <label class="row">
        <input
          type="checkbox"
          checked={tree.foldersFirst}
          onchange={(e) =>
            setFoldersFirst(project.rootPath, e.currentTarget.checked)}
        />
        Folders First
      </label>
      <div class="row">
        <button class="refresh" onclick={() => void refreshProject(project.rootPath)}>
          Refresh
        </button>
        <span class="muted hint">Re-read the folders shown in the tree</span>
      </div>
    </section>
  {/if}

  <section>
    <h3>Visibility</h3>
    <label class="row">
      <input
        type="checkbox"
        checked={settings.fileTree.showSystemGeneratedFolders}
        onchange={(e) => setShowSystemFolders(e.currentTarget.checked)}
      />
      Show system/generated folders
    </label>
    <p class="muted hint">Applies to every project (V1.5 §22 AppSettings).</p>
  </section>

  <section>
    <h3>Viewer</h3>
    <div class="row">
      <span>Font size</span>
      <span class="spacer"></span>
      <button class="step" aria-label="Smaller font" onclick={() => setFontSize(settings.fontSize - 1)}>−</button>
      <span class="mono size">{settings.fontSize} px</span>
      <button class="step" aria-label="Larger font" onclick={() => setFontSize(settings.fontSize + 1)}>+</button>
    </div>
  </section>

  <section>
    <h3>External Editors</h3>
    <div class="row">
      <span>Open in VS Code</span>
      <span class="spacer"></span>
      <label class="row inline">
        <input
          type="radio"
          name="vscode-mode"
          checked={settings.external.vsCodeNewWindow}
          onchange={() => setVsCodeNewWindow(true)}
        />
        New Window
      </label>
      <label class="row inline">
        <input
          type="radio"
          name="vscode-mode"
          checked={!settings.external.vsCodeNewWindow}
          onchange={() => setVsCodeNewWindow(false)}
        />
        Reuse Existing Window
      </label>
    </div>
  </section>

  <section>
    <h3>Theme</h3>
    {#each themes as t (t.value)}
      <label class="row">
        <input
          type="radio"
          name="theme"
          value={t.value}
          checked={settings.theme === t.value}
          onchange={() => setTheme(t.value)}
        />
        {t.label}
      </label>
    {/each}
  </section>

  <section>
    <h3>Diagnostics</h3>
    <div class="row muted">
      Channel:
      <span class="mono">{channel}</span>
      <span class="hint">(experience=体验版客户端;dev=开发构建)</span>
    </div>
    <div class="row muted">
      Build:
      {#if diagnostics.buildTime}
        <span class="mono">{new Date(diagnostics.buildTime * 1000).toLocaleString()}</span>
      {:else}
        …
      {/if}
    </div>
    <div class="row muted">
      Startup time:
      {#if diagnostics.startupMs !== null}
        <span class="mono">{diagnostics.startupMs} ms</span>
      {:else}
        measuring…
      {/if}
    </div>
    <div class="row muted">
      Shortcut interceptions: <span class="mono">{diagnostics.shortcutInterceptions}</span>
    </div>
    {#if diagnostics.lastShortcut}
      <div class="row muted">
        Last shortcut: <span class="mono">{diagnostics.lastShortcut}</span>
      </div>
    {/if}
  </section>

  <p class="muted note">Git settings arrive with their feature (Phase 7).</p>
</div>

<style>
  .settings-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  h3 {
    margin: 0 0 6px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 0;
    font-size: 12px;
  }

  .refresh {
    padding: 3px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 12px;
  }

  .refresh:hover {
    background: var(--bg-hover);
  }

  .spacer {
    flex: 1;
  }

  .row.inline {
    padding: 0;
  }

  .step {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .step:hover {
    background: var(--bg-hover);
  }

  .size {
    min-width: 40px;
    text-align: center;
    font-size: 11px;
  }

  .hint {
    font-size: 11px;
    margin: 2px 0 0;
  }

  .note {
    margin: 0;
    font-size: 12px;
  }
</style>
