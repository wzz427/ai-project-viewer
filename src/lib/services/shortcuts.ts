import { recordShortcutInterception } from "$lib/stores/diagnosticsStore.svelte";

/**
 * Application shortcut dispatcher (V1.5 §146/§147).
 *
 * WebView2 browser accelerators are disabled in tauri.conf.json
 * (`browserAcceleratorKeys: false`), so P0 combos reach the DOM as keydown
 * events. This capture-phase listener claims them before any page default
 * behavior, then fans out to registered handlers. Phase 1 wires placeholder
 * handlers; the real behaviors land with their features (V1.5 §177).
 */

export type Combo =
  | "ctrl+w"
  | "ctrl+f"
  | "ctrl+tab"
  | "ctrl+shift+tab"
  | "ctrl+r";

const COMBOS: readonly Combo[] = [
  "ctrl+w",
  "ctrl+f",
  "ctrl+tab",
  "ctrl+shift+tab",
  "ctrl+r",
];

type Handler = () => void;
const handlers = new Map<Combo, Set<Handler>>();

/** Register a handler for a P0 combo; returns an unsubscribe function. */
export function onShortcut(combo: Combo, handler: Handler): () => void {
  let set = handlers.get(combo);
  if (!set) {
    set = new Set();
    handlers.set(combo, set);
  }
  set.add(handler);
  return () => set!.delete(handler);
}

function comboOf(e: KeyboardEvent): Combo | null {
  if (!e.ctrlKey || e.altKey || e.metaKey) return null;
  if (e.repeat) return null; // holding a key must not machine-gun handlers
  switch (e.key.toLowerCase()) {
    case "w":
      return e.shiftKey ? null : "ctrl+w";
    case "f":
      return e.shiftKey ? null : "ctrl+f";
    case "r":
      return e.shiftKey ? null : "ctrl+r";
    case "tab":
      return e.shiftKey ? "ctrl+shift+tab" : "ctrl+tab";
    default:
      return null;
  }
}

let installed = false;

export function installShortcutDispatcher() {
  if (installed) return;
  installed = true;

  window.addEventListener(
    "keydown",
    (e) => {
      const combo = comboOf(e);
      if (!combo) return;
      e.preventDefault();
      e.stopPropagation();
      recordShortcutInterception(combo);
      for (const handler of handlers.get(combo) ?? []) {
        handler();
      }
    },
    { capture: true },
  );
}

export const knownCombos = COMBOS;
