<script lang="ts">
  /**
   * Locate dialog (spec-017): one input, paste-and-Enter.
   * Rendered once at the app root like ErrorDialog/PropertiesDialog; the
   * store slot decides visibility. Transient by contract — the input
   * resets on every open and nothing survives the close.
   */
  import { locateState, closeLocate, submitLocate } from "$lib/stores/locateStore.svelte";
  import { t } from "$lib/i18n/t.svelte";

  let input = $state("");
  let inputEl = $state<HTMLInputElement | null>(null);

  // Fresh field + focus + select-all on every open — the whole flow is
  // Ctrl+L, Ctrl+V, Enter.
  $effect(() => {
    if (locateState.open) {
      input = "";
      inputEl?.focus();
      inputEl?.select();
    }
  });

  function submit() {
    if (!input.trim()) return;
    void submitLocate(input);
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") closeLocate();
  }

  $effect(() => {
    if (!locateState.open) return;
    window.addEventListener("keydown", onKeydown, { capture: true });
    return () =>
      window.removeEventListener("keydown", onKeydown, { capture: true });
  });
</script>

{#if locateState.open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="backdrop"
    role="presentation"
    onmousedown={(e) => {
      if (e.target === e.currentTarget) closeLocate();
    }}
  >
    <div
      class="dialog locate-dialog"
      role="dialog"
      aria-modal="true"
      aria-label={t("locate.title")}
    >
      <p class="title">{t("locate.title")}</p>
      <input
        class="mono"
        bind:this={inputEl}
        bind:value={input}
        placeholder={t("locate.placeholder")}
        spellcheck="false"
        autocomplete="off"
        data-locate-input
        onkeydown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            submit();
          }
        }}
      />
      <p class="hint">{t("locate.hint")}</p>
      <div class="card-actions">
        <button onclick={closeLocate}>{t("common.cancel")}</button>
        <button class="primary" onclick={submit} disabled={!input.trim()}>
          {t("locate.go")}
        </button>
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
    min-width: 420px;
    max-width: 560px;
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

  input {
    width: 100%;
    padding: 8px 10px;
    font-size: var(--text-sm);
    color: var(--text);
    background: var(--bg-input);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    outline: none;
  }

  input:focus {
    border-color: var(--accent);
  }

  .hint {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
</style>
