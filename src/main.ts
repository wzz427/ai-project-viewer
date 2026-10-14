import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";
import { restoreAppState } from "$lib/services/sessionRestore.svelte";
import { diagError, diagEvent, diagWarn } from "$lib/stores/diagnosticsStore.svelte";
import { startStateSync } from "$lib/services/stateSync.svelte";
import { installDebugHook } from "$lib/services/debugHook";
import { initTheme } from "$lib/stores/settingsStore.svelte";

// This is a desktop app, not a browser page: the WebView's default context
// menu (Back/Reload/Print/Inspect…) must never surface. Custom menus listen
// to the same event and open their own UI.
window.addEventListener(
  "contextmenu",
  (e) => e.preventDefault(),
  { capture: true },
);

// Global error trap (2026-10-10): a one-off "blank content after maximize +
// tab switch" wedge never reproduced under CDP monitoring; if it ever comes
// back, these lines make the culprit name itself in the console.
window.addEventListener("error", (e) => {
  console.error("[aiv-global] error:", e.message, `@${e.filename}:${e.lineno}`);
  diagError(`window error: ${e.message} @${e.filename}:${e.lineno}`);
});
window.addEventListener("unhandledrejection", (e) => {
  console.error("[aiv-global] unhandled rejection:", e.reason);
  diagError(`unhandled rejection: ${e.reason}`);
});

// Console capture (2026-10-12 field freeze, aiv-diagnostics-1791785427):
// the ring stayed clean through the freeze — window hooks alone miss
// anything a library logs and swallows (Svelte flush, pdf.js). Errors go
// straight into the ring; warns are deduped so chatty libs (pdf.js) can't
// push the ring over. Deferred a tick so a console call from inside an
// effect flush never mutates state mid-flush; guarded against re-entry.
{
  const nativeError = console.error.bind(console);
  const nativeWarn = console.warn.bind(console);
  const seenWarns = new Set<string>();
  let inDiag = false;
  const text = (args: unknown[]) =>
    args.map((a) => String(a)).join(" ").slice(0, 300);
  console.error = (...args: unknown[]) => {
    if (!inDiag) {
      inDiag = true;
      try {
        setTimeout(() => diagError(`console.error: ${text(args)}`), 0);
      } catch {
        /* dev-only state guard */
      } finally {
        inDiag = false;
      }
    }
    nativeError(...args);
  };
  console.warn = (...args: unknown[]) => {
    const t = text(args);
    if (!inDiag && !seenWarns.has(t) && seenWarns.size < 40) {
      seenWarns.add(t);
      inDiag = true;
      try {
        setTimeout(() => diagWarn(`console.warn: ${t}`), 0);
      } catch {
        /* dev-only state guard */
      } finally {
        inDiag = false;
      }
    }
    nativeWarn(...args);
  };
}

async function boot() {
  diagEvent("app boot");
  installDebugHook();
  // Restore first, then start tracking: mount reads the restored stores,
  // and the sync loop's first write lands after the session is back.
  // Theme applies here — BEFORE mount/first paint — so a paper user never
  // flashes glacier (owner theme pack 2026-10-14).
  await restoreAppState();
  initTheme();
  startStateSync();
  mount(App, {
    target: document.getElementById("app")!,
  });
}

void boot();
