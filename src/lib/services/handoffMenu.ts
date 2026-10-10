/**
 * File handoff menu builder (V1.5 §135–§142, spec-006).
 *
 * ONE builder feeds BOTH surfaces — the tree-node context menu and the
 * file-tab context menu — so the entry set per file type cannot drift
 * between them (spec-006 D5/V10). All launch verbs go through the Rust
 * semantic commands (§133: the frontend never builds executables).
 */

import { ask } from "@tauri-apps/plugin-dialog";
import { toast } from "$lib/stores/toastStore.svelte";
import { settings } from "$lib/stores/settingsStore.svelte";
import { openFile } from "$lib/stores/tabsStore.svelte";
import { isProjectTrusted, setProjectTrusted } from "$lib/stores/projectStore.svelte";
import { extOf, fileNameOf } from "$lib/services/viewerType";
import { menuKindOf } from "$lib/services/menuKind";
import {
  editInQuickEditor,
  openInBrowser,
  openInCodeEditor,
  openWithDefaultApp,
  revealInExplorer,
  runProjectExecutable,
  runProjectScript,
  testModeActive,
} from "$lib/services/tauri";

export interface HandoffEntry {
  /** Stable id for tests and cross-surface comparison. */
  id: string;
  label: string;
  run: () => Promise<void>;
}

export type HandoffGroup = HandoffEntry[];

/** Windows absolute path for clipboard copy (rel uses `/` in the app). */
export function absolutePathOf(rootPath: string, rel: string): string {
  return `${rootPath}\\${rel.replace(/\//g, "\\")}`;
}

/** Clipboard write with a legacy fallback; always reports via toast. */
export async function copyText(text: string, what: string): Promise<void> {
  let ok = false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      ok = true;
    }
  } catch {
    ok = false;
  }
  if (!ok) {
    // Fallback for denied permission / older hosts; the textarea is
    // removed immediately (nothing stays resident).
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    ok = document.execCommand("copy");
    ta.remove();
  }
  if (ok) toast(`Copied ${what}: ${text}`);
  else toast(`Copy failed (${what})`, { kind: "error" });
}

/** Launch wrapper: every handoff verb reports failures as a toast (§188). */
function guarded(label: string, fn: () => Promise<void>): () => Promise<void> {
  return async () => {
    try {
      await fn();
    } catch (err) {
      toast(`${label} failed: ${err}`, { kind: "error" });
    }
  };
}

// --- per-type classification (menu slice of §142's resolver) ---


/**
 * §128/§129 first-run gate + §119 toasts. Trust is a per-project UX gate
 * (spec-008 D2); Rust still fences extension + path on its own. Test mode
 * auto-cancels the native dialog (L7: TaskDialogs are undrivable) so e2e
 * stays zero-disturbance — the Trust-and-Run path is owner-真机 verified.
 */
export async function runWithTrust(
  rootPath: string,
  rel: string,
  launch: () => Promise<void>,
): Promise<void> {
  if (!isProjectTrusted(rootPath)) {
    if (await testModeActive().catch(() => false)) return;
    const yes = await ask(
      "This project contains executable files.\n\nRunning scripts or programs can modify files or your system.",
      { title: "Trust Project", kind: "warning", okLabel: "Trust and Run", cancelLabel: "Cancel" },
    );
    if (!yes) return;
    setProjectTrusted(rootPath, true);
  }
  const name = fileNameOf(rel);
  try {
    await launch();
    toast(`✓ ${name} launched`);
  } catch (err) {
    console.error("launch failed:", err);
    toast(`Failed to launch ${name}`, { kind: "error" });
  }
}

interface BuildOpts {
  /** Include the in-app "Open" entry (tree menu yes, tab menu no). */
  includeOpen?: boolean;
}

/**
 * §135–§140 entry groups for one node. Group boundaries render as the
 * menu's visual separators; Pin/Close stay owned by the calling menus.
 */
export function fileHandoffGroups(
  rootPath: string,
  rel: string,
  name: string,
  isDir: boolean,
  opts: BuildOpts = {},
): HandoffGroup[] {
  const kind = menuKindOf(name, isDir);
  const abs = absolutePathOf(rootPath, rel);
  const newWindow = () => settings.external.vsCodeNewWindow;

  const open: HandoffEntry = {
    id: "open",
    label: "Open",
    run: isDir
      ? guarded("Open", () => openWithDefaultApp(rootPath, rel))
      : () => openFile(rootPath, rel).then(() => undefined),
  };
  const notepad: HandoffEntry = {
    id: "notepad",
    label: "Edit in Notepad",
    run: guarded("Edit in Notepad", () => editInQuickEditor(rootPath, rel)),
  };
  const vscode: HandoffEntry = {
    id: "vscode",
    label: "Open in VS Code",
    run: guarded("VS Code", () => openInCodeEditor(rootPath, rel, newWindow())),
  };
  const vscodeFolder: HandoffEntry = {
    id: "vscode-folder",
    label: "Open Folder in VS Code",
    run: guarded("VS Code", () => openInCodeEditor(rootPath, rel, newWindow())),
  };
  const browser: HandoffEntry = {
    id: "browser",
    label: "Open in Browser",
    run: guarded("Browser", () => openInBrowser(rootPath, rel)),
  };
  const defaultApp: HandoffEntry = {
    id: "default-app",
    label: "Open with Default App",
    run: guarded("Open", () => openWithDefaultApp(rootPath, rel)),
  };
  const pdfApp: HandoffEntry = {
    id: "pdf-app",
    label: "Open with Default PDF App",
    run: guarded("Open", () => openWithDefaultApp(rootPath, rel)),
  };
  const runScript: HandoffEntry = {
    id: "run-script",
    label: "Run Script",
    run: () => runWithTrust(rootPath, rel, () => runProjectScript(rootPath, rel)),
  };
  const runExe: HandoffEntry = {
    id: "run",
    label: "Run",
    run: () => runWithTrust(rootPath, rel, () => runProjectExecutable(rootPath, rel)),
  };
  const reveal: HandoffEntry = {
    id: "reveal",
    label: "Show in File Explorer",
    run: guarded("Explorer", () => revealInExplorer(rootPath, rel)),
  };
  const copyAbs: HandoffEntry = {
    id: "copy-abs",
    label: "Copy Absolute Path",
    run: () => copyText(abs, "absolute path"),
  };
  const copyRel: HandoffEntry = {
    id: "copy-rel",
    label: "Copy Relative Path",
    run: () => copyText(rel, "relative path"),
  };

  switch (kind) {
    case "folder": // §140
      return [
        ...(opts.includeOpen ? [[open]] : []),
        [reveal, copyAbs, copyRel, vscodeFolder],
      ];
    case "textLike": // §135
      return [
        ...(opts.includeOpen ? [[open]] : []),
        [notepad, vscode],
        [reveal, copyAbs, copyRel],
      ];
    case "script": // §137: Run Script in its own group
      return [
        ...(opts.includeOpen ? [[open]] : []),
        [runScript],
        [notepad, vscode],
        [reveal, copyAbs, copyRel],
      ];
    case "browserText": // §136
      return [
        ...(opts.includeOpen ? [[open]] : []),
        [browser],
        [notepad, vscode],
        [reveal, copyAbs, copyRel],
      ];
    case "pdf": // §138
      return [
        ...(opts.includeOpen ? [[open]] : []),
        [pdfApp],
        [reveal, copyAbs, copyRel],
      ];
    case "systemApp": // §142 System App rows (§197 generalized entry)
      return [
        ...(opts.includeOpen ? [[open]] : []),
        [defaultApp],
        [reveal, copyAbs, copyRel],
      ];
    case "exe": // §139: Open (info card) / Run / path verbs
      return [
        ...(opts.includeOpen ? [[open]] : []),
        [runExe],
        [reveal, copyAbs, copyRel],
      ];
    case "msi": // §126: System Default only — no Run, no in-app Open
      return [
        [defaultApp],
        [reveal, copyAbs, copyRel],
      ];
  }
}

/** §141 groups for the project tab itself (Pin/Refresh/Trust not here). */
export function projectHandoffGroups(rootPath: string): HandoffGroup[] {
  return [
    [
      {
        id: "project-explorer",
        label: "Open in File Explorer",
        run: guarded("Explorer", () => revealInExplorer(rootPath, null)),
      },
      {
        id: "copy-project-path",
        label: "Copy Project Path",
        run: () => copyText(rootPath, "project path"),
      },
      {
        id: "project-vscode",
        label: "Open Project in VS Code",
        run: guarded("VS Code", () =>
          openInCodeEditor(rootPath, null, settings.external.vsCodeNewWindow),
        ),
      },
    ],
  ];
}
