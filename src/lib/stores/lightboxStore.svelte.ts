/**
 * Image lightbox slot (spec-021): the zoom popup behind clicking an
 * inline markdown image.
 *
 * ZERO-RESIDENT (V1.5 §6): one boolean plus the already-loaded data URL
 * of the clicked image (D2 — the string itself lives in the document's
 * <img>; the store only borrows the reference). Closing clears both, so
 * nothing outlives the dialog.
 */

export const lightboxState = $state<{ open: boolean; src: string }>({
  open: false,
  src: "",
});

export function openLightbox(src: string) {
  if (!src) return;
  lightboxState.src = src;
  lightboxState.open = true;
}

/** D6: closing drops the src reference too — the whole slot is empty
 *  whenever the dialog is not on screen. */
export function closeLightbox() {
  lightboxState.open = false;
  lightboxState.src = "";
}
