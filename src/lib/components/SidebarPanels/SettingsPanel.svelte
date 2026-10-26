<script lang="ts">
  import {
    settings,
    setFontSize,
    setLocale,
    setShowSystemFolders,
    setTheme,
    setVsCodeNewWindow,
    type Theme,
  } from "$lib/stores/settingsStore.svelte";
  import { t, tf, rt, type I18nKey } from "$lib/i18n/t.svelte";
  import type { Locale } from "$lib/i18n/dict";
  import { diagnostics } from "$lib/stores/diagnosticsStore.svelte";
  import { invoke } from "@tauri-apps/api/core";
  import { activeProject, projectState } from "$lib/stores/projectStore.svelte";
  import { tabsState } from "$lib/stores/tabsStore.svelte";
  import { toast } from "$lib/stores/toastStore.svelte";
  import { diagEvent } from "$lib/stores/diagnosticsStore.svelte";
  import {
    setFoldersFirst,
    treeState,
  } from "$lib/stores/fileTreeStore.svelte";

  // Theme pack (owner 2026-10-14): exactly two light skins. zh labels are
  // the owner's own names for them (暖纸书卷/冰川蓝); default-first
  // ordering: paper is the default (owner's 2026-10-14 order, overriding
  // the pack JSON's glacier default).
  const themes: { value: Theme; key: I18nKey }[] = [
    { value: "paper", key: "settings.themePaper" },
    { value: "glacier", key: "settings.themeGlacier" },
  ];
  // Language options (spec-016): names render in their OWN language.
  const languages: { value: Locale; key: I18nKey }[] = [
    { value: "en", key: "settings.langEn" },
    { value: "zh", key: "settings.langZh" },
  ];

  const project = $derived(activeProject());
  let channel = $state("…");
  // Tree preferences are per-project (V1.5 §17); the section drives the
  // active one. Owner 2026-10-01: the old "⋯" menu content lives here now.
  const tree = $derived(project ? treeState.byRoot[project.rootPath] : undefined);

  $effect(() => {
    void invoke<string>("channel").then((c) => (channel = c)).catch(() => {});
  });

  // 0.6.12 (owner 2026-10-10: a viewer-freeze bug replicas could not
  // reproduce → "增加一个诊断的按钮…生成运行信息"). The report carries a
  // LIVE cross-check: what the tab strip says is active vs. what the
  // viewer body is actually showing at export time.
  let exporting = $state(false);

  async function exportDiagnostics() {
    exporting = true;
    try {
      const lines: string[] = [];
      const [version] = await Promise.all([
        invoke<string>("app_version").catch(() => "?"),
      ]);
      lines.push(`AI Project Viewer diagnostics`);
      lines.push(
        `version=${version} channel=${channel} startup=${diagnostics.startupMs ?? "?"}ms ` +
          `build=${diagnostics.buildTime ? new Date(diagnostics.buildTime * 1000).toISOString() : "?"} ` +
          `exported=${new Date().toISOString()}`,
      );
      const activeTabDom = document
        .querySelector(".file-tab.active")
        ?.textContent?.trim() ?? null;
      const viewerDom = document.querySelector(".markdown-viewer")
        ? "markdown-viewer"
        : document.querySelector(".code-host")
          ? "code-viewer"
          : document.querySelector(".exe-info")
            ? "exe-info"
            : document.querySelector(".diff-viewer")
              ? "diff-viewer"
              : document.querySelector(".commit-view")
                ? "commit-view"
                : document.querySelector(".unsupported")
                  ? "unsupported"
                  : "(none)";
      // data-rel (2026-10-12 field freeze): what the VIEWER thinks it is
      // rendering vs. what the store says is active — the freeze kept the
      // component class correct while the content stayed on the previous
      // file, so class alone could not name the mismatch.
      const viewerRel =
        document.querySelector(".viewer-body [data-rel]")?.getAttribute("data-rel")
        ?? "(none)";
      lines.push(
        `live-check: dom-active-tab=${activeTabDom} dom-viewer=${viewerDom} viewer-rel=${viewerRel}`,
      );
      if (project && viewerRel !== "(none)") {
        const st = tabsState.byRoot[project.rootPath];
        const storeRel = st?.activeFileRelativePath ?? "(none)";
        if (storeRel !== viewerRel) {
          lines.push(
            `MISMATCH: store-active=${storeRel} viewer-showing=${viewerRel}`,
          );
        }
      }
      for (const p of projectState.tabs) {
        const st = tabsState.byRoot[p.rootPath];
        lines.push(
          `project "${p.name}" mode=${p.sidebarMode} trusted=${p.trustedForExecution} ` +
            `active=${st?.activeFileRelativePath ?? "(none)"}`,
        );
        lines.push(
          `  tabs: ${(st?.openFiles ?? [])
            .map((t) => t.relativePath + (t.deleted ? " (deleted)" : ""))
            .join(" | ")}`,
        );
      }
      lines.push("--- runtime log (oldest first) ---");
      for (const e of diagnostics.log) {
        const ms = String(e.t % 1000).padStart(3, "0");
        lines.push(
          `${new Date(e.t).toLocaleTimeString()}.${ms} [${e.kind}] ${e.text}`,
        );
      }
      const path = await invoke<string>("write_diagnostics", {
        text: lines.join("\r\n"),
      });
      diagEvent("diagnostics exported");
      toast(tf("toast.diagExported", { path }));
    } catch (err) {
      toast(tf("toast.diagExportFailed", { err: rt(err) }), { kind: "error" });
    }
    exporting = false;
  }
</script>

<div class="settings-panel">
  {#if project && tree}
    <section>
      <h3>{t("settings.fileTree")}</h3>
      <label class="row">
        <input
          type="checkbox"
          checked={tree.foldersFirst}
          onchange={(e) =>
            setFoldersFirst(project.rootPath, e.currentTarget.checked)}
        />
        {t("settings.foldersFirst")}
      </label>
      <p class="muted hint">{t("settings.refreshHint")}</p>
    </section>
  {/if}

  <section>
    <h3>{t("settings.visibility")}</h3>
    <label class="row">
      <input
        type="checkbox"
        checked={settings.fileTree.showSystemGeneratedFolders}
        onchange={(e) => setShowSystemFolders(e.currentTarget.checked)}
      />
      {t("settings.showSystemFolders")}
    </label>
    <p class="muted hint">{t("settings.appliesHint")}</p>
  </section>

  <section>
    <h3>{t("settings.viewer")}</h3>
    <div class="row">
      <span>{t("settings.fontSize")}</span>
      <span class="spacer"></span>
      <button class="step" aria-label={t("settings.smallerFont")} onclick={() => setFontSize(settings.fontSize - 1)}>−</button>
      <span class="mono size">{settings.fontSize} px</span>
      <button class="step" aria-label={t("settings.largerFont")} onclick={() => setFontSize(settings.fontSize + 1)}>+</button>
    </div>
  </section>

  <section>
    <h3>{t("settings.externalEditors")}</h3>
    <div class="row">
      <span>{t("settings.openInVscode")}</span>
      <span class="spacer"></span>
      <label class="row inline">
        <input
          type="radio"
          name="vscode-mode"
          checked={settings.external.vsCodeNewWindow}
          onchange={() => setVsCodeNewWindow(true)}
        />
        {t("settings.newWindow")}
      </label>
      <label class="row inline">
        <input
          type="radio"
          name="vscode-mode"
          checked={!settings.external.vsCodeNewWindow}
          onchange={() => setVsCodeNewWindow(false)}
        />
        {t("settings.reuseWindow")}
      </label>
    </div>
  </section>

  <section>
    <h3>{t("settings.theme")}</h3>
    {#each themes as th (th.value)}
      <label class="row">
        <input
          type="radio"
          name="theme"
          value={th.value}
          checked={settings.theme === th.value}
          onchange={() => setTheme(th.value)}
        />
        {t(th.key)}
      </label>
    {/each}
  </section>

  <section>
    <h3>{t("settings.language")}</h3>
    {#each languages as lang (lang.value)}
      <label class="row">
        <input
          type="radio"
          name="language"
          value={lang.value}
          checked={settings.locale === lang.value}
          onchange={() => setLocale(lang.value)}
        />
        {t(lang.key)}
      </label>
    {/each}
  </section>

  <section>
    <h3>{t("settings.diagnostics")}</h3>
    <!-- Owner 2026-10-11: "留一个 Export 的按钮不就完了吗" — the Channel/
         Build/Startup/Shortcut readouts are gone from the panel; the
         numbers still land in the exported report where they matter. -->
    <div class="row">
      <button class="export-diag" onclick={() => void exportDiagnostics()} disabled={exporting}>
        {exporting ? t("settings.exporting") : t("settings.exportDiag")}
      </button>
    </div>
  </section>
</div>

<style>
  .settings-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  h3 {
    margin: 0 0 6px;
    font-size: var(--text-sm);
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
    font-size: var(--text-sm);
  }

  .spacer {
    flex: 1;
  }

  .row.inline {
    padding: 0;
  }

  .step {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .step:hover {
    background: var(--bg-hover);
  }

  .size {
    min-width: 40px;
    text-align: center;
    font-size: var(--text-xs);
  }

  .hint {
    font-size: var(--text-xs);
    margin: 2px 0 0;
  }

</style>
