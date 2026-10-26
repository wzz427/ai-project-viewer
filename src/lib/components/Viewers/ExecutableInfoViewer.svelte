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

<div class="stat-host">
  <div class="stat-card">
    <p class="card-title">{name}</p>
    <p class="card-kind">{t("viewer.execKind")}</p>
    <dl>
      {#if sizeText !== null}
        <div class="stat-row"><dt>{t("viewer.sizeLabel")}</dt><dd>{sizeText}</dd></div>
      {/if}
      {#if modifiedText !== null}
        <div class="stat-row"><dt>{t("viewer.modifiedLabel")}</dt><dd>{modifiedText}</dd></div>
      {/if}
      <div class="stat-row path"><dt>{t("viewer.pathLabel")}</dt><dd>{rootPath}\{tab.relativePath.replaceAll("/", "\\")}</dd></div>
    </dl>
    <p class="card-note">{t("viewer.cannotPreviewPlain")}</p>
    <div class="card-actions">
      <button class="primary" onclick={run} disabled={running}>
        {running ? t("viewer.runningBtn") : t("menu.run")}
      </button>
      <button onclick={reveal}>{t("viewer.showExplorerBtn")}</button>
    </div>
  </div>
</div>
