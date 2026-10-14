import {
  DEFAULT_THEME,
  FONT_SIZE_MAX,
  FONT_SIZE_MIN,
} from "$lib/services/appState";

/**
 * App themes (owner 2026-10-14, reference/AI_Project_Viewer_Theme_Pack):
 * exactly two LIGHT skins — "glacier" (default, 冰川蓝) and "paper"
 * (暖纸书卷). system/dark/light retired; legacy persisted values heal to
 * glacier in parseSettings.
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

/** Applies the persisted theme + font knob. Called from main.ts AFTER
 * restoreAppState and BEFORE mount — the theme lands before first paint,
 * so a paper user never sees a glacier flash (app.css :root carries the
 * glacier defaults for the pre-JS frame). */
export function initTheme() {
  applyTheme();
  applyFontSize();
}
