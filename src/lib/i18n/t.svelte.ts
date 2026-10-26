/**
 * Reactive i18n accessor. The locale lives in the settings store
 * ($state, persisted with AppState); calling t()/tf()/relTime() inside a
 * template or $derived tracks settings.locale, so a language switch
 * re-renders everything immediately — no restart, no remount.
 */

import { settings } from "$lib/stores/settingsStore.svelte";
import {
  relativeTimeDict,
  translate,
  type I18nKey,
  type Locale,
} from "$lib/i18n/dict";
import { translateRustError } from "$lib/i18n/rustErrors";

export type { I18nKey, Locale };

/** Plain lookup — use for static labels. */
export function t(key: I18nKey): string {
  return translate(settings.locale, key);
}

/** Lookup with {var} interpolation — use for composed messages. */
export function tf(
  key: I18nKey,
  vars: Record<string, string | number>,
): string {
  return translate(settings.locale, key, vars);
}

/** Localize a backend error string for display (exact/prefix map;
 * unknown strings pass through unchanged). */
export function rt(err: unknown): string {
  return translateRustError(String(err), settings.locale);
}

/** Locale-aware relative time ("2h ago" / "2 小时前"). */
export function relTime(ts: number): string {
  return relativeTimeDict(settings.locale, Date.now(), ts);
}
