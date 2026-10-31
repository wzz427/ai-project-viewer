/**
 * Locate-by-path parsing (spec-017): turn a pasted absolute or
 * project-relative path into {project + true-case rel path} against the
 * OPEN projects. Pure — filesystem access is injected so vitest covers the
 * whole matrix without Tauri.
 *
 * Tolerances (owner pastes from Explorer / terminals / our own quoted
 * "Copy Absolute Path"): surrounding double quotes, mixed \ and /, any
 * casing, trailing separator, optional \\?\ verbatim prefix.
 */

import type { TreeEntry } from "$lib/services/tauri";

export interface ParsedPath {
  kind: "abs" | "rel";
  /** Path segments, separators already unified; never empty. */
  segments: string[];
}

/** Strip the noise a real paste carries. null = nothing usable. */
export function normalizeInput(raw: string): ParsedPath | null {
  let s = raw.trim();
  // Our own Copy Absolute Path ships double quotes (0.8.4) — pasting it
  // back must work verbatim. NTFS names cannot contain `"`, so no
  // escaping is possible or needed.
  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
    s = s.slice(1, -1);
  }
  // Rust canonicalize emits \\?\ verbatim paths; tools that copy them
  // would otherwise never match a (dunce-normalized) project root.
  if (s.startsWith("\\\\?\\")) {
    s = s.slice(4);
  }
  const segments = s
    .replace(/\\/g, "/")
    .split("/")
    .filter((p) => p.length > 0);
  if (segments.length === 0) return null;
  const first = segments[0]!;
  if (/^[a-z]:$/i.test(first) || s.startsWith("//")) {
    return { kind: "abs", segments };
  }
  return { kind: "rel", segments };
}

export interface ProjectLike {
  id: string;
  rootPath: string;
}

export interface ProjectMatch {
  project: ProjectLike;
  /** Segments below the project root; [] = the root itself. */
  relSegments: string[];
}

const normRoot = (rootPath: string) =>
  rootPath.replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();

/**
 * Which open project owns this input? Absolute: longest root prefix wins
 * (nested projects — the more specific root owns the path); a path equal
 * to a root matches that project with no remainder. Relative: resolved
 * against the ACTIVE project only (spec-017 D5 — no cross-project
 * guessing). null = no open project contains it.
 */
export function matchProject(
  parsed: ParsedPath,
  projects: ProjectLike[],
  activeId: string | null,
): ProjectMatch | null {
  if (parsed.kind === "rel") {
    const active = projects.find((p) => p.id === activeId);
    return active
      ? { project: active, relSegments: [...parsed.segments] }
      : null;
  }
  // Segment-wise compare (not string slicing): keeps the user's spelling
  // in relSegments — the disk's true spelling is restored later by the
  // resolveRel walk, so lowering here would just muddy the diagnostics.
  let best: { project: ProjectLike; relSegments: string[]; depth: number } | null = null;
  for (const project of projects) {
    const rootSegs = normRoot(project.rootPath).split("/");
    if (parsed.segments.length < rootSegs.length) continue;
    const under = rootSegs.every(
      (s, i) => parsed.segments[i]!.toLowerCase() === s,
    );
    if (!under) continue;
    if (parsed.segments.length === rootSegs.length) {
      return { project, relSegments: [] };
    }
    const relSegments = parsed.segments.slice(rootSegs.length);
    if (!best || rootSegs.length > best.depth) {
      best = { project, relSegments, depth: rootSegs.length };
    }
  }
  return best ? { project: best.project, relSegments: best.relSegments } : null;
}

export interface WalkResult {
  /** True-case project-relative path ("src/Main.tsx"); never ".". */
  rel: string;
  isDir: boolean;
  /** The target or an ancestor is a system-generated folder — invisible
   *  in the tree while "show system folders" is off (spec-017 D8). */
  hiddenSystem: boolean;
}

/** One cached directory level; null = unreadable/missing. Mirrors the
 *  tree store's listing cache so the walk and the tree agree. */
export type DirLister = (relDir: string) => Promise<TreeEntry[] | null>;

/**
 * Walk the segments level by level, matching each against the listing
 * case-insensitively but keeping the DISK's spelling — tree rows are
 * keyed by the real name, so a wrong-case rel would expand invisible
 * state and never scroll (revealTarget matches row titles exactly).
 * null = the path does not exist (or a mid-path segment is a file).
 */
export async function resolveRel(
  segments: string[],
  list: DirLister,
): Promise<WalkResult | null> {
  let dir = ".";
  let hiddenSystem = false;
  for (let i = 0; i < segments.length; i++) {
    const wanted = segments[i]!;
    const entries = await list(dir);
    if (!entries) return null;
    const hit = entries.find(
      (e) => e.name.toLowerCase() === wanted.toLowerCase(),
    );
    if (!hit) return null;
    hiddenSystem ||= hit.systemGenerated;
    const rel = dir === "." ? hit.name : `${dir}/${hit.name}`;
    if (i === segments.length - 1) {
      return { rel, isDir: hit.isDir, hiddenSystem };
    }
    if (!hit.isDir) return null;
    dir = rel;
  }
  return null; // unreachable: normalizeInput guarantees >= 1 segment
}
