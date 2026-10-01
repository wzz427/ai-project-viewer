export type Theme = "system" | "light" | "dark";

/**
 * Theme + viewer font size (V1.5 §24; font size added 2026-10-01 owner
 * feedback). Not persisted yet — AppSettings persistence is Phase 4 scope.
 */
export const settings = $state({
  theme: "system" as Theme,
  /** Viewer/editor font size in px (code, text, json source, markdown). */
  fontSize: 13,
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

export function initTheme() {
  media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", applyTheme);
  applyTheme();
  applyFontSize();
}
