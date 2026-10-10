/**
 * Ctrl+F target registry (owner 2026-10-10): the ACTIVE viewer's toolbar
 * registers its focus handler on mount and drops it on unmount, so the
 * global dispatcher (App.svelte) can always land Ctrl+F on the visible
 * Find box — code, markdown, json, and pdf alike. Same shape as
 * codeSearchRegistry, which stays as the CodeMirror fallback.
 */
let active: (() => void) | null = null;

export function registerFindFocus(focus: () => void) {
  active = focus;
}

export function unregisterFindFocus(focus: () => void) {
  if (active === focus) active = null;
}

/** Returns true when a viewer consumed the shortcut. */
export function focusActiveFind(): boolean {
  if (!active) return false;
  active();
  return true;
}
