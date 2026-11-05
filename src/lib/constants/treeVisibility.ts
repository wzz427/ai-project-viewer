/**
 * Tree Visibility (V1.5 §28/§29) — which directories the user SEES.
 *
 * The authoritative default-hidden list lives in Rust
 * (`src-tauri/src/file_tree.rs::DEFAULT_HIDDEN_DIRS`, 8 names) because the
 * tagging happens at listing time; this module owns the frontend half:
 * filtering entries against the toggle. Do NOT copy the 8-name list here —
 * one list, one home, or the two ends drift.
 *
 * Visibility and watcher ignore are separate concepts (§28): the watcher
 * list lives in `services/watcherIgnore.ts` and must never be merged with
 * visibility, even though both name directories.
 */

import type { TreeEntry } from "$lib/services/tauri";

/**
 * Entries the user should see at this level (V1.5 §30 toggle, default OFF).
 * `keepNames` (spec-018 B): names of system-generated dirs that stay
 * visible because an OPEN file lives under them — derived from the tab
 * list each render, never stored, so closing the last such tab makes the
 * row disappear on the spot (owner 2026-11-05: "查看期间临时显示,关闭即消失").
 */
export function visibleEntries(
  entries: readonly TreeEntry[],
  showSystemFolders: boolean,
  keepNames?: ReadonlySet<string>,
): TreeEntry[] {
  return entries.filter(
    (e) => showSystemFolders || !e.systemGenerated || keepNames?.has(e.name),
  );
}

/** Dir rels covering every ancestor of one open file's rel (spec-018 B):
 * `a/b/c.md` → [`a`, `a/b`]. Pure input to openChainDirs — no FS access. */
export function ancestorDirsOf(rel: string): string[] {
  const out: string[] = [];
  let idx = rel.indexOf("/");
  while (idx !== -1) {
    out.push(rel.slice(0, idx));
    idx = rel.indexOf("/", idx + 1);
  }
  return out;
}

/** All ancestor dir rels of all open files (spec-018 B). Derived, never
 * persisted — the reveal walk and the row filter both read it live. */
export function openChainDirs(openRels: readonly string[]): Set<string> {
  const s = new Set<string>();
  for (const rel of openRels) {
    for (const dir of ancestorDirsOf(rel)) s.add(dir);
  }
  return s;
}

/** Names within ONE level whose rel the chain covers — the shape
 * visibleEntries wants. TREE_ROOT is "." (fileTreeStore), so the root
 * level's prefix is the empty string. */
export function keepNamesUnder(
  chain: ReadonlySet<string>,
  parentRel: string,
): Set<string> {
  const out = new Set<string>();
  const prefix = parentRel === "." ? "" : `${parentRel}/`;
  for (const dir of chain) {
    if (!dir.startsWith(prefix)) continue;
    const rest = dir.slice(prefix.length);
    if (rest && !rest.includes("/")) out.add(rest);
  }
  return out;
}
