/**
 * Context-menu viewport clamp (owner 2026-10-10: bottom-left menus were
 * clipped by the window edge — menus opened AT the click point and their
 * lower items fell outside). Call once the menu element is mounted so its
 * real size is measurable; keeps an 8px margin on every edge.
 */
export function clampMenu(
  el: HTMLElement,
  x: number,
  y: number,
): { left: number; top: number } {
  const w = el.offsetWidth;
  const h = el.offsetHeight;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  return {
    left: Math.max(8, Math.min(x, vw - w - 8)),
    top: Math.max(8, Math.min(y, vh - h - 8)),
  };
}
