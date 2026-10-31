<script lang="ts">
  import Icon from "$lib/components/Icon.svelte";
  import { t } from "$lib/i18n/t.svelte";

  let {
    mode,
    onModeChange,
    onRefresh,
    onLocate,
    gitBadge,
  }: {
    mode: "files" | "git" | "settings";
    onModeChange: (mode: "files" | "git" | "settings") => void;
    /** Active-project tree reload; undefined = no project (button hidden).
     *  Returns the in-flight promise so the button can spin until done. */
    onRefresh?: () => Promise<void>;
    /** Locate-by-path dialog (spec-017); undefined = no project (hidden).
     *  The dialog itself lands wherever the target project lives. */
    onLocate?: () => void;
    /** §9 badge text for the Git tab ("7" / "99+"); null = no badge. */
    gitBadge?: string | null;
  } = $props();

  // Owner 2026-10-01: one entry button only. Clicking ⚙ opens Settings;
  // clicking it again returns to the Files tree.
  function toggleSettings() {
    onModeChange(mode === "settings" ? "files" : "settings");
  }

  // Owner 2026-10-10: a refresh click must ALWAYS be visible, even when
  // the tree is already current — the icon spins for at least 600ms.
  // Rapid clicks while busy are ignored.
  let spinning = $state(false);
  async function refresh() {
    if (spinning || !onRefresh) return;
    spinning = true;
    try {
      await Promise.all([
        onRefresh(),
        new Promise((r) => setTimeout(r, 600)),
      ]);
    } finally {
      spinning = false;
    }
  }
</script>

<!-- V1.5 §8: Files / Git as sidebar header tabs; Settings is an entry, not a tab.
     The refresh icon (owner 2026-10-10) sits LEFT of the gear, icon-only —
     the old text button lived buried inside Settings, unreachable when the
     tree was showing. -->
<div class="sidebar-header">
  <button
    class="header-tab"
    class:active={mode === "files"}
    onclick={() => onModeChange("files")}
  >
    {t("header.files")}
  </button>
  <button
    class="header-tab"
    class:active={mode === "git"}
    onclick={() => onModeChange("git")}
  >
    <Icon name="git-branch" size={14} /><span>{t("header.git")}</span>{#if gitBadge}<span class="git-badge">{gitBadge}</span>{/if}
  </button>
  <div class="spacer"></div>
  {#if onLocate}
    <button
      class="header-icon locate"
      onclick={onLocate}
      title="{t("header.locate")} (Ctrl+L)"
      aria-label={t("header.locate")}
      data-locate-button
    >
      <Icon name="search" size={15} />
    </button>
  {/if}
  {#if onRefresh}
    <button
      class="header-icon refresh"
      class:spinning
      onclick={refresh}
      title={t("header.refresh")}
      aria-label={t("header.refresh")}
      aria-busy={spinning}
    >
      <span class="glyph"><Icon name="refresh" size={15} /></span>
    </button>
  {/if}
  <button
    class="header-icon settings"
    class:active={mode === "settings"}
    onclick={toggleSettings}
    title={t("header.settings")}
    aria-label={t("header.settings")}
  >
    <Icon name="gear" size={15} />
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
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: var(--radius);
    color: var(--text-muted);
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast);
  }

  .header-tab:hover {
    background: var(--bg-hover);
  }

  /* Active mode: accent-soft tint + accent-ink text (spec-014 R5 + theme
     pack: small text on the soft chip uses accent.INK, not the bright
     indicator blue/brown) — the chrome's single accent carries "you are
     here". */
  .header-tab.active {
    background: var(--accent-soft);
    color: var(--accent-ink);
  }

  /* §9 badge on the Git tab: accent pill (was debug-looking "[7]"). */
  .git-badge {
    min-width: 16px;
    padding: 0 5px;
    border-radius: var(--radius-pill);
    background: var(--accent-soft);
    color: var(--accent-ink);
    font-size: var(--text-xs);
    line-height: 15px;
    text-align: center;
  }

  .header-tab:not(.active) .git-badge {
    background: var(--bg-active);
    color: var(--text-muted);
  }

  .spacer {
    flex: 1;
  }

  .header-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 7px;
    border-radius: var(--radius);
    color: var(--text-muted);
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast);
  }

  .header-icon:hover:not(:disabled) {
    background: var(--bg-hover);
    color: var(--text);
  }

  .header-icon:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .settings.active {
    background: var(--accent-soft);
    color: var(--accent);
  }

  /* inline-FLEX, not inline-block: an inline svg on a text baseline drags
     a descender gap below it, inflating this button to 26.5px while its
     neighbours stay 23px — the icon then sits ~1.75px high in the row
     (owner 2026-10-31 "三个图标的高度根本就没有对齐"; probe-measured,
     icon-align-probe.py). Flex removes the baseline line box entirely. */
  .refresh .glyph {
    display: inline-flex;
  }

  .refresh.spinning .glyph {
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
