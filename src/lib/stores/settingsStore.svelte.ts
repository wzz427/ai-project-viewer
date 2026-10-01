export type Theme = "system" | "light" | "dark";

/**
 * AppSettings (V1.5 §22) — application-wide, persisted with AppState since
 * Phase 4. The file-tree visibility toggle lives HERE, not per project
 * (§22 puts showSystemGeneratedFolders under AppSettings.fileTree; §17's
 * ProjectSession carries only foldersFirst + pinnedItems).
 */
export const settings = $state({
  theme: "system" as Theme,
  /** Viewer/editor font size in px (§197 revision, D8 in spec-004). */
  fontSize: 13,
  fileTree: {
    showSystemGeneratedFolders: false,
  },
});

let media: MediaQueryList | null = null;

function resolvedTheme(): "light" | "dark" {
  if (settings.theme === "system") {
    return media && media.matches ? "dark" : "light";
  }
  return settings.theme;
}

function applyTheme() {
  document.documentElement.dataset.theme = resolvedTheme();
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
  settings.fontSize = Math.min(20, Math.max(11, px));
  applyFontSize();
}

export function setShowSystemFolders(value: boolean) {
  settings.fileTree.showSystemGeneratedFolders = value;
}

export function initTheme() {
  media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", applyTheme);
  applyTheme();
  applyFontSize();
}
