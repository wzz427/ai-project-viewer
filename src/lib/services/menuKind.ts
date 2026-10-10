/**
 * File → context-menu kind (the menu slice of V1.5 §142's resolver).
 * Pure and store-free so the classification is unit-testable in vitest —
 * handoffMenu.ts consumes it and owns the actions.
 */

import { extOf } from "$lib/services/viewerType";

export type MenuKind =
  | "folder"
  | "textLike"
  | "script"
  | "browserText"
  | "pdf"
  | "systemApp"
  | "exe"
  | "msi";

/** §116 Script RUN covers exactly these; §127 keeps py/js/sh off the list. */
export const SCRIPT_RUNNABLE = new Set(["ps1", "cmd", "bat"]);

export function menuKindOf(name: string, isDir: boolean): MenuKind {
  if (isDir) return "folder";
  const ext = extOf(name);
  if (ext === "pdf") return "pdf";
  if (["png", "jpg", "jpeg", "webp", "gif", "svg"].includes(ext)) return "systemApp";
  if (SCRIPT_RUNNABLE.has(ext)) return "script";
  if (ext === "exe") return "exe";
  if (ext === "msi") return "msi";
  if (ext === "html" || ext === "htm" || ext === "url") return "browserText";
  return "textLike";
}
