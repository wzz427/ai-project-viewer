export type Theme = "system" | "light" | "dark";

/**
 * Theme only in Phase 1 (V1.5 §24). Not persisted yet — AppSettings
 * persistence is Phase 4 scope (V1.5 §178).
 */
export const settings = $state({
  theme: "system" as Theme,
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

export function initTheme() {
  media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", applyTheme);
  applyTheme();
}
