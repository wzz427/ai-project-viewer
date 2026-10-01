<script lang="ts">
  import {
    settings,
    setTheme,
    type Theme,
  } from "$lib/stores/settingsStore.svelte";
  import { diagnostics } from "$lib/stores/diagnosticsStore.svelte";

  const themes: { value: Theme; label: string }[] = [
    { value: "system", label: "System" },
    { value: "dark", label: "Dark" },
    { value: "light", label: "Light" },
  ];
</script>

<div class="settings-panel">
  <section>
    <h3>Theme</h3>
    {#each themes as t (t.value)}
      <label class="row">
        <input
          type="radio"
          name="theme"
          value={t.value}
          checked={settings.theme === t.value}
          onchange={() => setTheme(t.value)}
        />
        {t.label}
      </label>
    {/each}
  </section>

  <section>
    <h3>Diagnostics</h3>
    <div class="row muted">
      Startup time:
      {#if diagnostics.startupMs !== null}
        <span class="mono">{diagnostics.startupMs} ms</span>
      {:else}
        measuring…
      {/if}
    </div>
    <div class="row muted">
      Shortcut interceptions: <span class="mono">{diagnostics.shortcutInterceptions}</span>
    </div>
    {#if diagnostics.lastShortcut}
      <div class="row muted">
        Last shortcut: <span class="mono">{diagnostics.lastShortcut}</span>
      </div>
    {/if}
  </section>

  <p class="muted note">More settings arrive in Phase 4 (V1.5 §178).</p>
</div>

<style>
  .settings-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  h3 {
    margin: 0 0 6px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 0;
    font-size: 12px;
  }

  .note {
    margin: 0;
    font-size: 12px;
  }
</style>
