<script lang="ts">
  /**
   * §122 Executable Info: left-clicking a .exe shows this stat card
   * (name / Windows Executable / Size / Modified / Path / "This file
   * cannot be previewed."). Nothing of the file is ever read — the fields
   * ride the inspect stat call, so there is no content buffer to release.
   *
   * Launch buttons (owner 2026-10-26, reversing the 0.8.11 exception):
   * Run goes through the SAME gated path as the right-click verb
   * (runWithTrust → trust dialog on first run per project → Rust
   * runProjectExecutable) — a button adds discoverability, not a bypass.
   * Reveal matches every other stat card.
   */
  import type { RuntimeTab } from "$lib/stores/tabsStore.svelte";
  import { runWithTrust } from "$lib/services/handoffMenu";
  import { revealInExplorer, runProjectExecutable } from "$lib/services/tauri";
  import { toast } from "$lib/stores/toastStore.svelte";
  import { t, tf, rt } from "$lib/i18n/t.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const name = $derived(tab.relativePath.split("/").pop() ?? tab.relativePath);
  const sizeText = $derived(
    tab.sizeBytes === undefined
      ? null
      : tab.sizeBytes >= 1048576
        ? `${(tab.sizeBytes / 1048576).toFixed(1)} MB`
        : `${(tab.sizeBytes / 1024).toFixed(1)} KB`,
  );
  const modifiedText = $derived(
    tab.modifiedMs ? new Date(tab.modifiedMs).toLocaleString() : null,
  );

  let running = $state(false);

  async function run() {
    if (running) return;
    running = true;
    try {
      // Success = the visible window itself (§119: no toast); failures
      // surface as the centered dialog from runWithTrust.
      await runWithTrust(rootPath, tab.relativePath, () =>
        runProjectExecutable(rootPath, tab.relativePath),
      );
    } finally {
      running = false;
    }
  }

  async function reveal() {
    try {
      await revealInExplorer(rootPath, tab.relativePath);
    } catch (err) {
      toast(tf("toast.explorerFailed", { err: rt(err) }), { kind: "error" });
    }
  }
</script>

<div class="exe-info">
  <div class="card">
    <p class="exe-name">{name}</p>
    <p class="kind">{t("viewer.execKind")}</p>
    <dl>
      {#if sizeText !== null}
        <div class="row"><dt>{t("viewer.sizeLabel")}</dt><dd>{sizeText}</dd></div>
      {/if}
      {#if modifiedText !== null}
        <div class="row"><dt>{t("viewer.modifiedLabel")}</dt><dd>{modifiedText}</dd></div>
      {/if}
      <div class="row path"><dt>{t("viewer.pathLabel")}</dt><dd>{rootPath}\{tab.relativePath.replaceAll("/", "\\")}</dd></div>
    </dl>
    <p class="muted">{t("viewer.cannotPreviewPlain")}</p>
    <div class="actions">
      <button class="primary" onclick={run} disabled={running}>
        {running ? t("viewer.runningBtn") : t("menu.run")}
      </button>
      <button onclick={reveal}>{t("viewer.showExplorerBtn")}</button>
    </div>
  </div>
</div>

<style>
  .exe-info {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .card {
    text-align: center;
    padding: 24px 32px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    gap: 10px;
    align-items: center;
    min-width: 280px;
  }

  .exe-name {
    font-family: var(--font-mono);
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0;
    max-width: 480px;
    overflow-wrap: anywhere;
  }

  .kind {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  dl {
    margin: 4px 0 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .row {
    display: flex;
    gap: 8px;
    justify-content: center;
    font-size: var(--text-sm);
  }

  dt {
    color: var(--text-muted);
  }

  dd {
    margin: 0;
    font-family: var(--font-mono);
  }

  .row.path dd {
    max-width: 380px;
    overflow-wrap: anywhere;
    text-align: left;
  }

  .muted {
    margin: 6px 0 0;
    color: var(--text-muted);
    font-size: var(--text-sm);
  }

  button.primary {
    font-weight: 600;
  }

  /* The app resets buttons globally (app.css `button { background: none;
     border: none }`) — every card that ships buttons re-styles them
     locally. 0.8.15 shipped this card with ONLY the layout rules, so the
     buttons rendered as bare bold text (owner report 2026-10-26). */
  button {
    padding: 5px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-overlay);
    transition: background-color var(--transition-fast);
  }

  button:hover {
    background: var(--bg-hover);
  }

  button:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .actions {
    display: flex;
    gap: 10px;
    margin-top: 6px;
  }
</style>
