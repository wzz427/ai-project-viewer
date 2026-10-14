/**
 * Project avatar identity colors (spec-014 D3 / P0 → theme pack
 * avatar.* tokens, 2026-10-14): each project's tab badge is tinted with a
 * stable hue derived from hash(rootPath) into the pack's 6-hue palette.
 * Deterministic across sessions — the color is learnable identity ("which
 * project is this"), not decoration. Rendered as tinted background +
 * colored initial (never a solid fill).
 *
 * The hue VALUE is a CSS variable reference (var(--av-blue) …) defined per
 * theme in app.css — glacier and paper each carry their own pre-tuned
 * foreground set, so this module stays theme-agnostic and no color lives
 * outside the managed token set.
 */
export const AVATAR_HUES = [
  "blue",
  "green",
  "orange",
  "rose",
  "lavender",
  "purple",
] as const satisfies readonly string[];

export type AvatarHue = (typeof AVATAR_HUES)[number];

/** FNV-1a 32-bit: small, stable, no collision worries at 6 buckets. */
function hashPath(path: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < path.length; i++) {
    h ^= path.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

export function avatarHueOf(rootPath: string): AvatarHue {
  const idx = hashPath(rootPath) % AVATAR_HUES.length;
  // uint32 % positive const is always in range; the ?? only satisfies
  // noUncheckedIndexedAccess (spec-013 discipline).
  return AVATAR_HUES[idx] ?? "blue";
}

/** CSS variable reference for the project's identity hue (per-theme). */
export function avatarColorOf(rootPath: string): string {
  return `var(--av-${avatarHueOf(rootPath)})`;
}

/** First grapheme of the project name, uppercased, for the tab badge. */
export function avatarInitialOf(name: string): string {
  const first = [...name.trim()][0] ?? "?";
  return first.toUpperCase();
}
