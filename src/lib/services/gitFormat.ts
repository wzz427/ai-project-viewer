/**
 * Pure display helpers for git review (spec-007 V4) — kept free of stores
 * so vitest can drive them directly.
 */

import type { GitSnapshot } from "$lib/services/tauri";

/** §9 badge text: 0 hides the badge, 1–99 shows the real count, ≥100 → 99+. */
export function badgeText(count: number): string | null {
  if (count <= 0) return null;
  if (count >= 100) return "99+";
  return String(count);
}

/**
 * §54 relative time ("2h ago", "yesterday"). Compact VS Code-ish wording;
 * the wording beyond the two §54 examples is a display default.
 */
export function relativeTime(now: number, ts: number): string {
  const s = Math.max(0, Math.floor((now - ts) / 1000));
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d === 1) return "yesterday";
  if (d < 7) return `${d}d ago`;
  const w = Math.floor(d / 7);
  if (w < 5) return `${w}w ago`;
  const mo = Math.floor(d / 30);
  if (mo < 12) return `${mo}mo ago`;
  return `${Math.floor(d / 365)}y ago`;
}

/**
 * CSS class for a git letter ('?' cannot be a class name — maps to git-q).
 * The classes live in app.css (both themes).
 */
export function letterClass(letter: string): string {
  return letter === "?" ? "git-q" : `git-${letter}`;
}

/**
 * rel → letter map for the file tree (§46 third layer). When a file sits in
 * BOTH groups the staged letter wins (spec-007 D4: the index state is what
 * would be committed). Single implementation shared by the store's cache.
 */
export function marksByRel(snapshot: GitSnapshot): Map<string, string> {
  const marks = new Map<string, string>();
  if (snapshot.status !== "ok") return marks;
  for (const e of snapshot.changes) marks.set(e.rel, e.letter);
  for (const e of snapshot.staged) marks.set(e.rel, e.letter);
  return marks;
}
