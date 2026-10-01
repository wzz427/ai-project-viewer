import { invoke } from "@tauri-apps/api/core";

export interface ResolvedProject {
  rootPath: string;
  name: string;
}

/** Canonicalize a folder into a project identity (V1.5 §14/§144). */
export function resolveProject(rawPath: string): Promise<ResolvedProject> {
  return invoke<ResolvedProject>("resolve_project", { rawPath });
}

/** Milliseconds from Rust process start to the moment this is called. */
export function startupElapsedMs(): Promise<number> {
  return invoke<number>("startup_elapsed_ms");
}
