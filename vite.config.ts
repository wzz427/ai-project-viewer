import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { fileURLToPath, URL } from "node:url";

// App version for the UI (UpdateButton tooltip): stamped at build time
// from package.json — keep it in sync with tauri.conf.json when bumping.
const version = JSON.parse(
  readFileSync(fileURLToPath(new URL("./package.json", import.meta.url)), "utf8"),
).version;

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  resolve: {
    alias: {
      $lib: fileURLToPath(new URL("./src/lib", import.meta.url)),
    },
  },
  // Tauri reads the dev server port from tauri.conf.json; keep them in sync.
  server: {
    port: 1420,
    strictPort: true,
  },
  build: {
    outDir: "dist",
  },
  clearScreen: false,
});
