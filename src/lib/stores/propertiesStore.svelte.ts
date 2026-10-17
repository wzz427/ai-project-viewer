/**
 * Properties dialog slot (owner 2026-10-17: "我想看到一个文件的修改日期",
 * constrained to add no resident memory).
 *
 * ZERO-RESIDENT BY DESIGN (V1.5 §6): the slot holds null while closed; the
 * dialog fetches everything on open and drops it on close — timestamps
 * never join the tree data and never persist to the state file.
 */
export interface PropertiesRequest {
  rootPath: string;
  /** Project-relative; "." = the project root itself (project-tab menu). */
  rel: string;
  /** Dialog title — file/folder name, or the project's folder name. */
  name: string;
  /** From the menu context; folders skip the git-history fetch. */
  isDir: boolean;
}

export const propertiesState = $state({
  current: null as PropertiesRequest | null,
});

export function openProperties(req: PropertiesRequest) {
  propertiesState.current = req;
}

export function closeProperties() {
  propertiesState.current = null;
}
