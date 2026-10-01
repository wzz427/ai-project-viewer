<script lang="ts">
  let {
    mode,
    onModeChange,
  }: {
    mode: "files" | "git" | "settings";
    onModeChange: (mode: "files" | "git" | "settings") => void;
  } = $props();
</script>

<!-- V1.5 §8: Files / Git as sidebar header tabs; Settings is an entry, not a tab. -->
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
  <button
    class="settings"
    class:active={mode === "settings"}
    onclick={() => onModeChange("settings")}
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

  .settings {
    padding: 4px 8px;
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 14px;
  }

  .settings:hover {
    background: var(--bg-hover);
  }

  .settings.active {
    background: var(--bg-active);
    color: var(--text);
  }
</style>
