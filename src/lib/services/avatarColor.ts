/**
 * Project avatar identity colors (spec-014 D3 / P0): each project's tab
 * badge is tinted with a stable color derived from hash(rootPath) into a
 * fixed 8-hue, low-saturation palette. Deterministic across sessions —
 * the color is learnable identity ("which project is this"), not
 * decoration. Rendered as tinted background + colored initial (never a
 * solid fill — quiet-professional direction, works on both themes).
 * Both themes share one palette; letters sit on a ~15% tint of their own
 * hue (≥3:1 verified, specs/spec-014 §六).
 */
export const AVATAR_PALETTE = [
  "#3d7fc4", // blue
  "#2e9c8a", // teal
  "#4a9455", // green
  "#b0832a", // amber
  "#c26a30", // orange
  "#c0504d", // red
  "#8a67c9", // purple
  "#5f7d9e", // slate
] as const satisfies readonly string[];

/** FNV-1a 32-bit: small, stable, no collision worries at 8 buckets. */
function hashPath(path: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < path.length; i++) {
    h ^= path.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

export function avatarColorOf(rootPath: string): string {
  const idx = hashPath(rootPath) % AVATAR_PALETTE.length;
  // uint32 % positive const is always in range; the ?? only satisfies
  // noUncheckedIndexedAccess (spec-013 discipline).
  return AVATAR_PALETTE[idx] ?? "#3d7fc4";
}

/** First grapheme of the project name, uppercased, for the tab badge. */
export function avatarInitialOf(name: string): string {
  const first = [...name.trim()][0] ?? "?";
  return first.toUpperCase();
}
