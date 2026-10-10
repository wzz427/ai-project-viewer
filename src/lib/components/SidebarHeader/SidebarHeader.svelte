<script lang="ts">
  let {
    mode,
    onModeChange,
    onRefresh,
  }: {
    mode: "files" | "git" | "settings";
    onModeChange: (mode: "files" | "git" | "settings") => void;
    /** Active-project tree reload; undefined = no project (button hidden). */
    onRefresh?: () => void;
  } = $props();

  // Owner 2026-10-01: one entry button only. Clicking ⚙ opens Settings;
  // clicking it again returns to the Files tree.
  function toggleSettings() {
    onModeChange(mode === "settings" ? "files" : "settings");
  }
</script>

<!-- V1.5 §8: Files / Git as sidebar header tabs; Settings is an entry, not a tab.
     The refresh icon (owner 2026-10-10) sits LEFT of ⚙, icon-only — the
     old text button lived buried inside Settings, unreachable when the
     tree was showing. -->
<div class="sidebar-header">
  <button
    class="header-tab"
    class:active={mode === "files"}
    onclick={() => onModeChange("files")}
  >
    Files
  </button>
  <button
    class="header-tab"
    class:active={mode === "git"}
    onclick={() => onModeChange("git")}
  >
    Git
  </button>
  <div class="spacer"></div>
  {#if onRefresh}
    <button
      class="header-icon refresh"
      onclick={onRefresh}
      title="Refresh"
      aria-label="Refresh"
    >
      ↻
    </button>
  {/if}
  <button
    class="header-icon settings"
    class:active={mode === "settings"}
    onclick={toggleSettings}
    title="Settings"
    aria-label="Settings"
  >
    ⚙
  </button>
</div>

<style>
  .sidebar-header {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 4px 6px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .header-tab {
    padding: 4px 10px;
    border-radius: var(--radius);
    color: var(--text-muted);
  }

  .header-tab:hover {
    background: var(--bg-hover);
  }

  .header-tab.active {
    background: var(--bg-active);
    color: var(--text);
  }

  .spacer {
    flex: 1;
  }

  .header-icon {
    padding: 4px 8px;
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 14px;
  }

  .header-icon:hover:not(:disabled) {
    background: var(--bg-hover);
  }

  .header-icon:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .settings.active {
    background: var(--bg-active);
    color: var(--text);
  }
</style>
