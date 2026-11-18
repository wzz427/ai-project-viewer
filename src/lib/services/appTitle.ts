/**
 * Title-bar text (spec-023, owner 2026-11-18:「左上角的名字旁边加一个
 * 版本号」). The app name lives ONLY in the native title bar (tauri.conf
 * `windows.title`); the version is appended at runtime so every future
 * release updates it automatically — the version truth is the same
 * tauri.conf `version` the publish script stamps (via the `app_version`
 * command), never a fourth hand-bumped copy.
 *
 * D3: a missing/blank/"unknown" version degrades to the bare name — a
 * dangling space or a literal "unknown" on the title bar is worse than no
 * suffix. Pure so vitest owns the three states.
 */
export function titleWithVersion(base: string, version: string): string {
  const v = version.trim();
  return v && v !== "unknown" ? `${base} ${v}` : base;
}
