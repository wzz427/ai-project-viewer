/**
 * Bridge between the global Ctrl+F dispatcher and the CodeMirror instance
 * of the active tab (V1.5 §146/§147): the dispatcher claims the keydown at
 * capture phase, so CodeMirror's own keymap never sees it — the active
 * editor registers itself here instead.
 */
import type { EditorView } from "@codemirror/view";

let active: EditorView | null = null;

export function setActiveSearchView(view: EditorView | null) {
  active = view;
}

export function getActiveSearchView(): EditorView | null {
  return active;
}
