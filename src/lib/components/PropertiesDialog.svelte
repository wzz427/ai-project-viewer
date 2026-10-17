<script lang="ts">
  /**
   * Properties dialog (owner 2026-10-17: "我想看到一个文件的修改日期,
   * 包括历史修改记录,但不要增加内存占用"). Rendered once at the app
   * root like ErrorDialog; the store slot decides visibility.
   *
   * MEMORY CONTRACT: everything shown is fetched the moment the dialog
   * opens and dropped the moment it closes (V1.5 §6) — no cache, no
   * persistence, nothing joins the tree data. Git history runs through
   * the git.exe subprocess, which exits after answering.
   */
  import {
    propertiesState,
    closeProperties,
  } from "$lib/stores/propertiesStore.svelte";
  import {
    fileProperties,
    gitFileHistory,
    type FileProperties,
    type GitCommit,
  } from "$lib/services/tauri";
  import { absolutePathOf } from "$lib/services/handoffMenu";

  const req = $derived(propertiesState.current);

  // "loading" | "none" (no git / folder) | the commit list.
  let info = $state<FileProperties | null>(null);
  let infoError = $state<string | null>(null);
  let history = $state<"loading" | "none" | GitCommit[]>("none");

  // Close/reopen races: only the newest open's responses may land.
  let seq = 0;

  $effect(() => {
    const r = propertiesState.current;
    if (!r) return;
    const my = ++seq;
    info = null;
    infoError = null;
    history = r.isDir ? "none" : "loading";

    void fileProperties(r.rootPath, r.rel)
      .then((p) => {
        if (my === seq) info = p;
      })
      .catch((e) => {
        if (my === seq) infoError = String(e);
      });

    // Windows keeps no per-change history; git is the only record, so a
    // non-git project just hides the section (fetch rejects → "none").
    if (!r.isDir) {
      void gitFileHistory(r.rootPath, r.rel, 20)
        .then((cs) => {
          if (my === seq) history = cs;
        })
        .catch(() => {
          if (my === seq) history = "none";
        });
    }
  });

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") closeProperties();
  }

  $effect(() => {
    if (!req) return;
    window.addEventListener("keydown", onKeydown, { capture: true });
    return () =>
      window.removeEventListener("keydown", onKeydown, { capture: true });
  });

  const dateTime = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  function fmt(ms?: number): string {
    return typeof ms === "number" ? dateTime.format(new Date(ms)) : "—";
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    const units = ["KB", "MB", "GB", "TB"];
    let v = bytes;
    let u = -1;
    do {
      v /= 1024;
      u++;
    } while (v >= 1024 && u < units.length - 1);
    return `${v >= 100 ? Math.round(v) : v.toFixed(1)} ${units[u]}`;
  }
</script>

{#if req}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="backdrop"
    role="presentation"
    onmousedown={(e) => {
      if (e.target === e.currentTarget) closeProperties();
    }}
  >
    <div
      class="dialog props-dialog"
      role="dialog"
      aria-modal="true"
      aria-label={`Properties: ${req.name}`}
    >
      <p class="title">{req.name}</p>
      <p class="path mono">{req.rel === "." ? req.rootPath : absolutePathOf(req.rootPath, req.rel)}</p>

      {#if info}
        <dl class="facts">
          {#if !info.isDir}
            <div class="fact"><dt>Size</dt><dd>{formatSize(info.sizeBytes)}</dd></div>
          {/if}
          <div class="fact"><dt>Modified</dt><dd class="prop-modified">{fmt(info.modifiedMs)}</dd></div>
          <div class="fact"><dt>Created</dt><dd>{fmt(info.createdMs)}</dd></div>
          <div class="fact"><dt>Accessed</dt><dd>{fmt(info.accessedMs)}</dd></div>
        </dl>
      {:else if infoError}
        <p class="muted">{infoError}</p>
      {:else}
        <p class="muted">Loading…</p>
      {/if}

      {#if history === "loading"}
        <p class="muted">Loading history…</p>
      {:else if Array.isArray(history)}
        <div class="props-history">
          <p class="hist-title">History <span class="muted">(git)</span></p>
          {#if history.length === 0}
            <p class="muted">No recorded changes.</p>
          {:else}
            <ul>
              {#each history as c (c.hash)}
                <li class="props-hist-row">
                  <span class="date mono">{fmt(c.ts)}</span>
                  <span class="subject">{c.subject}</span>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      {/if}

      <div class="actions">
        <button onclick={closeProperties}>Close</button>
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
    min-width: 360px;
    max-width: 560px;
    max-height: 80vh;
    overflow-y: auto;
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
    overflow-wrap: anywhere;
  }

  .path {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
    overflow-wrap: anywhere;
    /* Selectable (owner 2026-10-17): the body shell disables selection
       for the desktop feel — a path you cannot copy is a path you cannot
       paste anywhere, so the dialog re-enables it here. */
    user-select: text;
    cursor: text;
  }

  .facts {
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .fact {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    font-size: var(--text-sm);
  }

  .fact dt {
    color: var(--text-muted);
  }

  .fact dd {
    margin: 0;
  }

  .hist-title {
    margin: 4px 0 0;
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .props-history ul {
    margin: 4px 0 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .props-hist-row {
    display: flex;
    align-items: baseline;
    column-gap: 12px;
    font-size: var(--text-sm);
  }

  .props-hist-row .date {
    white-space: nowrap;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .props-hist-row .subject {
    overflow-wrap: anywhere;
  }

  .muted {
    color: var(--text-muted);
    font-size: var(--text-sm);
    margin: 0;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 4px;
  }

  button {
    padding: 5px 18px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-overlay);
    transition: background-color var(--transition-fast);
  }

  button:hover {
    background: var(--bg-hover);
  }
</style>
