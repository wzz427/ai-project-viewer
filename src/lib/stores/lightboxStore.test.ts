/**
 * Lightbox store (spec-021): the slot must be EMPTY whenever the dialog
 * is not on screen — zero-residency is the contract (D6), so closing has
 * to drop the src reference, not just hide the dialog.
 */
import { beforeEach, describe, expect, it } from "vitest";
import {
  closeLightbox,
  lightboxState,
  openLightbox,
} from "$lib/stores/lightboxStore.svelte";

describe("lightboxStore", () => {
  // Module-level singleton: each case starts from the closed/empty slot.
  beforeEach(() => closeLightbox());

  it("opens with the clicked image's src", () => {
    openLightbox("data:image/png;base64,AAA");
    expect(lightboxState.open).toBe(true);
    expect(lightboxState.src).toBe("data:image/png;base64,AAA");
  });

  it("ignores an empty src (nothing loaded → nothing to show)", () => {
    openLightbox("");
    expect(lightboxState.open).toBe(false);
  });

  it("closing clears BOTH fields — nothing outlives the dialog", () => {
    openLightbox("data:image/png;base64,AAA");
    closeLightbox();
    expect(lightboxState.open).toBe(false);
    expect(lightboxState.src).toBe("");
  });
});
