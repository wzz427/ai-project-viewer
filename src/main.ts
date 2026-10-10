import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";
import { restoreAppState } from "$lib/services/sessionRestore.svelte";
import { diagError, diagEvent } from "$lib/stores/diagnosticsStore.svelte";
import { startStateSync } from "$lib/services/stateSync.svelte";

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

async function boot() {
  diagEvent("app boot");
  // Restore first, then start tracking: mount reads the restored stores,
  // and the sync loop's first write lands after the session is back.
  await restoreAppState();
  startStateSync();
  mount(App, {
    target: document.getElementById("app")!,
  });
}

void boot();
