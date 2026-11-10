<script lang="ts">
  /**
   * Locate dialog (spec-017): one input, paste-and-Enter. Rendered once
   * at the app root like ErrorDialog/PropertiesDialog; the store slot
   * decides visibility. Transient by contract — the input and any name
   * search's hit list reset on every open and die on close.
   */
  import { tick } from "svelte";
  import {
    locateState,
    closeLocate,
    submitLocate,
    pickLocateResult,
  } from "$lib/stores/locateStore.svelte";
  import { t, tf } from "$lib/i18n/t.svelte";

  let input = $state("");
  let inputEl = $state<HTMLInputElement | null>(null);
  let listEl = $state<HTMLDivElement | null>(null);
  // Highlighted row of a multi-hit name search; Enter / Go picks it.
  let activeIndex = $state(0);

  // Fresh field + focus + select-all on every open — the whole flow is
  // Ctrl+L, Ctrl+V, Enter.
  $effect(() => {
    if (locateState.open) {
      input = "";
      inputEl?.focus();
      inputEl?.select();
    }
  });

  // A fresh hit list starts at its best-ranked row; focus returns to the
  // field (a Go-button click moved it, and Enter must keep working).
  $effect(() => {
    if (locateState.results) {
      activeIndex = 0;
      inputEl?.focus();
    }
  });

  // Enter / Go: an UNCHANGED input with a list on screen means "take the
  // highlighted row" (VS Code quick-open contract); anything else is a
  // (new) lookup.
  function go() {
    const text = input.trim();
    if (!text) return;
    const res = locateState.results;
    if (res && res.query === text) {
      const row = res.matches[activeIndex];
      if (row) void pickLocateResult(row.rel);
      return;
    }
    void submitLocate(input);
  }

  function move(delta: number) {
    const n = locateState.results?.matches.length ?? 0;
    if (!n) return;
    activeIndex = (activeIndex + delta + n) % n;
    void tick().then(() =>
      listEl
        ?.querySelector<HTMLElement>(".result-row.active")
        ?.scrollIntoView({ block: "nearest" }),
    );
  }

  /** Display split: the file name always readable, its folder muted. */
  function splitRel(rel: string) {
    const i = rel.lastIndexOf("/");
    return i < 0
      ? { base: rel, dir: "" }
      : { base: rel.slice(i + 1), dir: rel.slice(0, i) };
  }

  function onInputKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      go();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      move(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      move(-1);
    }
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
        onkeydown={onInputKeydown}
      />
      {#if locateState.results}
        {@const res = locateState.results}
        <div class="results" data-locate-results>
          <p class="results-head">
            {#if res.truncated || res.total > res.matches.length}
              {tf("locate.resultsCapped", { n: res.matches.length })}
            {:else}
              {tf("locate.results", { n: res.matches.length })}
            {/if}
          </p>
          <div
            class="results-list"
            role="listbox"
            aria-label={t("locate.title")}
            bind:this={listEl}
          >
            {#each res.matches as row, i (row.rel)}
              {@const parts = splitRel(row.rel)}
              <button
                class="result-row"
                class:active={i === activeIndex}
                role="option"
                aria-selected={i === activeIndex}
                title={row.rel}
                data-locate-result={row.rel}
                onclick={() => void pickLocateResult(row.rel)}
                onmousemove={() => (activeIndex = i)}
              >
                <span class="base">{parts.base}{row.isDir ? "/" : ""}</span>
                {#if parts.dir}<span class="dir">{parts.dir}</span>{/if}
              </button>
            {/each}
          </div>
        </div>
      {/if}
      <p class="hint">{t("locate.hint")}</p>
      <div class="card-actions">
        <button onclick={closeLocate}>{t("common.cancel")}</button>
        <button class="primary" onclick={go} disabled={!input.trim()}>
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

  /* Multi-hit name search: a compact picker, capped so a broad query
     ("docs") can never grow an endless list — the head line tells the
     user to type more instead. Rows lead with the file NAME (what was
     searched for) and mute the folder behind it, so long paths never
     push the match out of view. The highlighted row carries the accent
     chip (same "you are here" language as tree selection). */
  .results {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-height: 0;
  }

  .results-head {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .results-list {
    max-height: 264px;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-input);
    padding: 3px;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .result-row {
    display: flex;
    align-items: baseline;
    gap: 10px;
    width: 100%;
    min-width: 0;
    padding: 5px 8px;
    border-radius: var(--radius);
    text-align: left;
    font-size: var(--text-sm);
    color: var(--text);
    white-space: nowrap;
  }

  .result-row.active {
    background: var(--accent-soft);
    color: var(--accent-ink);
    /* The chip alone reads faint on glacier's cold white (vision pass
       2026-11-10: "对比度处于下限") — a left accent edge keeps the
       highlighted row unambiguous on any skin, inset so it costs no
       layout. */
    box-shadow: inset 2px 0 0 var(--accent);
  }

  .result-row .base {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-row .dir {
    flex: 1;
    min-width: 24px;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-muted);
    font-size: var(--text-xs);
  }

  .result-row.active .dir {
    color: var(--accent-ink);
    opacity: 0.75;
  }
</style>
