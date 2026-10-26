import {
  DEFAULT_LOCALE,
  DEFAULT_THEME,
  FONT_SIZE_MAX,
  FONT_SIZE_MIN,
} from "$lib/services/appState";
import type { Locale } from "$lib/i18n/dict";
import { invoke } from "@tauri-apps/api/core";

/**
 * App themes (owner 2026-10-14, reference/AI_Project_Viewer_Theme_Pack):
 * exactly two LIGHT skins — "paper" (default 暖纸书卷, owner's explicit
 * order 2026-10-14) and "glacier" (冰川蓝). system/dark/light retired;
 * legacy persisted values heal to the default in parseSettings.
 */
export type Theme = "glacier" | "paper";

/**
 * AppSettings (V1.5 §22) — application-wide, persisted with AppState since
 * Phase 4. The file-tree visibility toggle lives HERE, not per project
 * (§22 puts showSystemGeneratedFolders under AppSettings.fileTree; §17's
 * ProjectSession carries only foldersFirst + pinnedItems).
 */
export const settings = $state({
  theme: DEFAULT_THEME as Theme,
  /** Viewer/editor font size in px (§197 revision, D8 in spec-004). */
  fontSize: 13,
  /** UI language (spec-016): "en" default; switching is instant because
   * every label reads through t() which tracks this field. */
  locale: DEFAULT_LOCALE as Locale,
  fileTree: {
    showSystemGeneratedFolders: false,
  },
  external: {
    /** §134 VS Code Mode — window behavior when handing off. */
    vsCodeNewWindow: true,
  },
});

function applyTheme() {
  document.documentElement.dataset.theme = settings.theme;
}

export function setTheme(theme: Theme) {
  settings.theme = theme;
  applyTheme();
}

function applyFontSize() {
  document.documentElement.style.setProperty(
    "--viewer-font-size",
    `${settings.fontSize}px`,
  );
}

export function setFontSize(px: number) {
  settings.fontSize = Math.min(FONT_SIZE_MAX, Math.max(FONT_SIZE_MIN, px));
  applyFontSize();
}

export function setShowSystemFolders(value: boolean) {
  settings.fileTree.showSystemGeneratedFolders = value;
}

export function setVsCodeNewWindow(value: boolean) {
  settings.external.vsCodeNewWindow = value;
}

/** The tray menu is built in Rust (English at boot); a language switch or
 * a restored zh preference rebuilds it in place. Fire-and-forget: a failed
 * rebuild keeps the English menu, never blocks the switch. */
function syncTrayLanguage() {
  void invoke("set_tray_language", { locale: settings.locale }).catch(() => {});
}

export function setLocale(locale: Locale) {
  settings.locale = locale;
  document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  syncTrayLanguage();
}

/** Applies the persisted theme + font knob. Called from main.ts AFTER
 * restoreAppState and BEFORE mount — the theme lands before first paint,
 * so a glacier user never sees a paper flash (app.css :root carries the
 * paper/DEFAULT-theme values for the pre-JS frame). */
export function initTheme() {
  applyTheme();
  applyFontSize();
  // Restored locale (spec-016): the tray menu was built English at boot;
  // a zh user gets it rebuilt before first paint matters, plus the lang
  // attribute for accessibility.
  document.documentElement.lang = settings.locale === "zh" ? "zh-CN" : "en";
  if (settings.locale !== "en") syncTrayLanguage();
}
