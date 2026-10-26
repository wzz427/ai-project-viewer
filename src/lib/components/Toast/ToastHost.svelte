<script lang="ts">
  import {
    toastState,
    dismissToast,
  } from "$lib/stores/toastStore.svelte";
  import { t } from "$lib/i18n/t.svelte";
</script>

{#if toastState.current}
  <div class="toast-row">
    <button
      class="toast {toastState.current.kind}"
      onclick={() => dismissToast(toastState.current!.id)}
      title={t("common.dismiss")}
    >
      {toastState.current.text}
    </button>
  </div>
{/if}

<style>
  .toast-row {
    position: fixed;
    bottom: 20px;
    left: 0;
    right: 0;
    display: flex;
    justify-content: center;
    pointer-events: none;
    z-index: 200;
  }

  .toast {
    pointer-events: auto;
    max-width: 70%;
    padding: 8px 14px;
    background: var(--bg-overlay);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    cursor: pointer;
    font-size: var(--text-sm);
    text-align: left;
  }

  .toast.error {
    border-left-color: var(--danger);
  }
</style>
