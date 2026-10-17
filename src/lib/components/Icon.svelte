<script lang="ts" module>
  /**
   * The app's single icon system (spec-014 D1 / P0): every chrome icon is
   * an inline SVG from this one table — 16px box, 2px stroke on a 24-grid
   * (≈1.5px effective), currentColor. Replaces the mixed Unicode/emoji
   * glyphs (📌⚙↻✕×▸⎇›‹⬆). Hand-written, zero dependencies, no runtime
   * parsing (memory-first rule). Geometry follows Lucide's vocabulary so
   * the set reads like a native developer tool.
   */
  import type { IconFamily } from "$lib/services/viewerType";

  export const FILE_ICONS: Record<IconFamily, IconName> = {
    markdown: "file-text",
    pdf: "book-open",
    code: "code",
    json: "braces",
    image: "image",
    file: "file",
  };

  export const PATHS = {
    plus: `<path d="M5 12h14"/><path d="M12 5v14"/>`,
    x: `<path d="M18 6 6 18"/><path d="m6 6 12 12"/>`,
    gear: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>`,
    refresh: `<path d="M21 12a9 9 0 1 1-2.64-6.36L21 8"/><path d="M21 3v5h-5"/>`,
    "chevron-right": `<path d="m9 18 6-6-6-6"/>`,
    "chevron-left": `<path d="m15 18-6-6 6-6"/>`,
    pin: `<path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1z"/>`,
    "git-branch": `<path d="M6 3v12"/><circle cx="18" cy="6" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/><circle cx="6" cy="18" r="3"/>`,
    check: `<path d="M20 6 9 17l-5-5"/>`,
    dot: `<circle cx="12" cy="12" r="5" fill="currentColor" stroke="none"/>`,
    "arrow-up": `<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>`,
    file: `<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><path d="M14 2v6h6"/>`,
    "file-text": `<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>`,
    // Symbol-only marks for structured content (owner 2026-10-17: the
    // document-outline + tiny `</>` variant was indistinguishable from the
    // MD document icon at tree size — chevrons share the braces/json
    // language: no document outline to confuse with file-text).
    code: `<path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/>`,
    braces: `<path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5c0 1.1.9 2 2 2h1"/><path d="M16 21h1a2 2 0 0 0 2-2v-5c0-1.1.9-2 2-2a2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1"/>`,
    image: `<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>`,
    "book-open": `<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>`,
  } as const;

  export type IconName = keyof typeof PATHS;
</script>

<script lang="ts">
  let {
    name,
    size = 16,
  }: {
    name: IconName;
    /** 16 is the chrome default; 12 for tree-row slots, 14 for tab icons. */
    size?: number;
  } = $props();
</script>

<!-- aria-hidden: icons here are always decorative — the hosting control
     carries its own aria-label/title. -->
<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
>
  {@html PATHS[name]}
</svg>
