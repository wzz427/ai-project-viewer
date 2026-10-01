/**
 * Shared pdf.js engine lifecycle (V1.5 §94/§96, spec-005).
 *
 * The library loads on first open only. Each document gets its OWN worker:
 * pdf.js `loadingTask.destroy()` destroys the worker it used
 * unconditionally — sharing one workerPort across documents lets the first
 * closed document kill the engine for the rest (found the hard way,
 * spec-005 acceptance round). A per-document worker makes destroy() clean
 * up exactly its own thread.
 *
 * Owner 2026-10-02: closing the LAST pdf tab must also unload what
 * remains — the worker thread is terminated there so an idle app costs
 * nothing; the next open reloads everything.
 */

import { tabsState } from "$lib/stores/tabsStore.svelte";

type PdfLib = typeof import("pdfjs-dist/legacy/build/pdf.mjs");

let lib: PdfLib | null = null;
let worker: Worker | null = null;

/**
 * Ensures the library is loaded and installs a FRESH worker for the
 * document that is about to open. Call once per document load.
 */
export async function acquireLib(): Promise<PdfLib> {
  if (!lib) {
    lib = await import("pdfjs-dist/legacy/build/pdf.mjs");
  }
  const WorkerCtor = (
    await import("pdfjs-dist/legacy/build/pdf.worker.min.mjs?worker")
  ).default;
  try {
    worker?.terminate();
  } catch {
    // previous document's destroy() already took it down
  }
  worker = new WorkerCtor();
  lib.GlobalWorkerOptions.workerPort = worker;
  return lib;
}

/** Any pdf tabs left anywhere (all projects)? */
function pdfTabsRemain(): boolean {
  for (const st of Object.values(tabsState.byRoot)) {
    if (st.openFiles.some((t) => t.viewerType === "pdf")) return true;
  }
  return false;
}

/**
 * Called from PdfViewer cleanup: when the last pdf tab is gone, kill the
 * worker thread and drop the library; the next open reloads everything.
 */
export function releaseEngineIfIdle() {
  if (pdfTabsRemain()) return;
  try {
    worker?.terminate();
  } catch {
    // already dead — nothing to do
  }
  worker = null;
  lib = null;
}
