<script lang="ts">
  /**
   * Centered modal error dialog (owner 2026-10-11). Rendered once at the
   * app root; the store slot decides visibility. Escape and the OK button
   * both close it.
   */
  import { errorDialog, closeErrorDialog } from "$lib/stores/errorDialogStore.svelte";
  import { t } from "$lib/i18n/t.svelte";

  const current = $derived(errorDialog.current);

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") closeErrorDialog();
  }

  $effect(() => {
    if (!current) return;
    window.addEventListener("keydown", onKeydown, { capture: true });
    return () =>
      window.removeEventListener("keydown", onKeydown, { capture: true });
  });
</script>

{#if current}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="backdrop"
    role="presentation"
    onmousedown={(e) => {
      if (e.target === e.currentTarget) closeErrorDialog();
    }}
  >
    <div class="dialog" role="alertdialog" aria-modal="true" aria-label={current.title}>
      <p class="title">{current.title}</p>
      <p class="message">{current.message}</p>
      <div class="actions">
        <button onclick={closeErrorDialog}>{t("common.ok")}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: color-mix(in srgb, var(--bg) 55%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .dialog {
    min-width: 320px;
    max-width: 520px;
    background: var(--bg-overlay);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 18px 20px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .title {
    margin: 0;
    font-size: var(--text-base);
    font-weight: 600;
  }

  .message {
    margin: 0;
    font-size: var(--text-sm);
    font-family: var(--font-mono);
    color: var(--text-muted);
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 4px;
  }

  button {
    padding: 8px 18px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-overlay);
    transition: background-color var(--transition-fast);
  }

  button:hover {
    background: var(--bg-hover);
  }
</style>
