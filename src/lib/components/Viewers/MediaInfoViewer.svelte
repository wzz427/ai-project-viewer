<script lang="ts">
  /**
   * Media (video/audio) info card (owner 2026-10-24 ruling: a tree click
   * has exactly ONE meaning — show the file in the viewer pane; launching
   * the player is a deliberate act, via this card's button or the tree's
   * right-click Open). Stat-only like the .exe card: no content is ever
   * read, the fields ride the inspect call.
   */
  import type { RuntimeTab } from "$lib/stores/tabsStore.svelte";
  import {
    openWithDefaultApp,
    revealInExplorer,
  } from "$lib/services/tauri";
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

  let launching = $state(false);

  async function play() {
    if (launching) return;
    launching = true;
    toast(tf("toast.opening", { name }));
    try {
      await openWithDefaultApp(rootPath, tab.relativePath);
    } catch (err) {
      toast(tf("toast.cannotOpenMedia", { err: rt(err) }), { kind: "error" });
    } finally {
      launching = false;
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
    <p class="card-kind">{t("viewer.mediaKind")}</p>
    <dl>
      {#if sizeText !== null}
        <div class="stat-row"><dt>{t("viewer.sizeLabel")}</dt><dd>{sizeText}</dd></div>
      {/if}
      {#if modifiedText !== null}
        <div class="stat-row"><dt>{t("viewer.modifiedLabel")}</dt><dd>{modifiedText}</dd></div>
      {/if}
      <div class="stat-row path"><dt>{t("viewer.pathLabel")}</dt><dd>{rootPath}\{tab.relativePath.replaceAll("/", "\\")}</dd></div>
    </dl>
    <p class="card-note">{t("viewer.cannotPreview")}</p>
    <div class="card-actions">
      <button class="primary" onclick={play} disabled={launching}>
        {launching ? t("viewer.openingBtn") : t("viewer.openInPlayer")}
      </button>
      <button onclick={reveal}>{t("viewer.showExplorerBtn")}</button>
    </div>
  </div>
</div>
