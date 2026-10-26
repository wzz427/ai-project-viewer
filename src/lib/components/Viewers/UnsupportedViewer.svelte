<script lang="ts">
  /**
   * Terminal viewer states: binary guard, >20 MB guard, deleted file
   * (V1.5 §83/§104/§106, spec-003 D4). Every card for a file the app
   * cannot preview carries a one-click launch to the OS default app
   * (owner 2026-10-24: "所有需要外部软件打开的文件,内容这儿应该提供
   * 可点击的按钮") — the right-click menu stays as the second path.
   */
  import { closeFile, type RuntimeTab } from "$lib/stores/tabsStore.svelte";
  import { openWithDefaultApp, revealInExplorer } from "$lib/services/tauri";
  import { toast } from "$lib/stores/toastStore.svelte";
  import { t, tf, rt } from "$lib/i18n/t.svelte";

  let { rootPath, tab }: { rootPath: string; tab: RuntimeTab } = $props();

  const sizeMb = $derived(
    tab.sizeBytes ? (tab.sizeBytes / 1048576).toFixed(1) : null,
  );

  let launching = $state(false);

  async function launchDefault() {
    if (launching) return;
    launching = true;
    const name = tab.relativePath.split("/").pop() ?? tab.relativePath;
    toast(tf("toast.opening", { name }));
    try {
      await openWithDefaultApp(rootPath, tab.relativePath);
    } catch (err) {
      toast(tf("toast.cannotOpenFile", { err: rt(err) }), { kind: "error" });
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

<div class="unsupported">
  {#if tab.deleted}
    <div class="card">
      <p class="name">{tab.relativePath}</p>
      <p>{t("viewer.deleted")}</p>
      <button onclick={() => closeFile(rootPath, tab.relativePath)}>
        {t("menu.closeTab")}
      </button>
    </div>
  {:else if tab.unsupportedReason === "binary"}
    <div class="card">
      <p class="name">{tab.relativePath}</p>
      <p>{t("viewer.binaryNote")}</p>
      <p class="muted">{sizeMb} MB</p>
      <div class="actions">
        <button class="primary" onclick={launchDefault} disabled={launching}>
          {launching ? t("viewer.openingBtn") : t("viewer.openDefaultAppBtn")}
        </button>
        <button onclick={reveal}>{t("viewer.showExplorerBtn")}</button>
      </div>
    </div>
  {:else if tab.unsupportedReason === "huge"}
    <div class="card">
      <p class="name">{tab.relativePath}</p>
      <p>{t("viewer.tooLarge")}</p>
      <p class="muted">{sizeMb} MB</p>
      <div class="actions">
        <button class="primary" onclick={launchDefault} disabled={launching}>
          {launching ? t("viewer.openingBtn") : t("viewer.openDefaultAppBtn")}
        </button>
        <button onclick={reveal}>{t("viewer.showExplorerBtn")}</button>
      </div>
    </div>
  {:else}
    <div class="card">
      <p class="name">{tab.relativePath}</p>
      <p>{t("viewer.cannotDisplay")}</p>
      <div class="actions">
        <button class="primary" onclick={launchDefault} disabled={launching}>
          {launching ? t("viewer.openingBtn") : t("viewer.openDefaultAppBtn")}
        </button>
        <button onclick={reveal}>{t("viewer.showExplorerBtn")}</button>
      </div>
    </div>
  {/if}
</div>

<style>
  .unsupported {
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
    gap: 8px;
    align-items: center;
  }

  .name {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin: 0;
    max-width: 480px;
    overflow-wrap: anywhere;
  }

  .card p {
    margin: 0;
  }

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

  button.primary {
    font-weight: 600;
  }

  .actions {
    display: flex;
    gap: 10px;
    margin-top: 6px;
  }

  .muted {
    color: var(--text-muted);
    font-size: var(--text-sm);
  }

</style>
