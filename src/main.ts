import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";

// This is a desktop app, not a browser page: the WebView's default context
// menu (Back/Reload/Print/Inspect…) must never surface. Custom menus listen
// to the same event and open their own UI.
window.addEventListener(
  "contextmenu",
  (e) => e.preventDefault(),
  { capture: true },
);

const app = mount(App, {
  target: document.getElementById("app")!,
});

export default app;
