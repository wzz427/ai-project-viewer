import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";
import { restoreAppState } from "$lib/services/sessionRestore.svelte";
import { startStateSync } from "$lib/services/stateSync.svelte";

// This is a desktop app, not a browser page: the WebView's default context
// menu (Back/Reload/Print/Inspect…) must never surface. Custom menus listen
// to the same event and open their own UI.
window.addEventListener(
  "contextmenu",
  (e) => e.preventDefault(),
  { capture: true },
);

async function boot() {
  // Restore first, then start tracking: mount reads the restored stores,
  // and the sync loop's first write lands after the session is back.
  await restoreAppState();
  startStateSync();
  mount(App, {
    target: document.getElementById("app")!,
  });
}

void boot();
