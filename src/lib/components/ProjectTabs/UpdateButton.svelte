<script lang="ts">
  /**
   * Experience-channel update button (SPEC-INFRA-001, owner 2026-10-02):
   * grey while current, lit when a new build sits in the local updates
   * folder. Clicking the grey button re-checks on demand; clicking the lit
   * button swaps the binary (Windows rename trick) and offers a restart.
   * Dev builds have no updates folder -> permanently grey, zero cost.
   */
  import { ask } from "@tauri-apps/plugin-dialog";
  import { invoke } from "@tauri-apps/api/core";
  import { applyUpdate, checkUpdate, relaunch } from "$lib/services/tauri";
  import { toast } from "$lib/stores/toastStore.svelte";
  import Icon from "$lib/components/Icon.svelte";

  // Scripted runs pick "Later" automatically: the native dialog is a
  // TaskDialog (no clickable child HWNDs, lessons L7 addendum) and would
  // hang on the owner's desktop undriven.
  let testMode = false;
  void invoke<boolean>("test_mode_active").then((t) => (testMode = t)).catch(() => {});

  let status = $state<"idle" | "available" | "busy">("idle");
  let note = $state("");
  let started = false;

  export async function refresh() {
    if (status === "busy") return;
    try {
      const info = await checkUpdate();
      note = info.note;
      status = info.available ? "available" : "idle";
    } catch {
      status = "idle"; // dev builds or missing folder: nothing to offer
    }
  }

  $effect(() => {
    if (started) return;
    started = true;
    void refresh();
  });

  async function onClick() {
    if (status === "available") {
      status = "busy";
      try {
        await applyUpdate();
        const restart = testMode
          ? false
          : await ask(
              "Update installed. Restart AI Project Viewer now?",
              { title: "Update Ready", kind: "info", okLabel: "Restart Now", cancelLabel: "Later" },
            );
        if (restart) {
          await relaunch();
        } else {
          toast("✓ Update installed — it takes effect on next launch");
          status = "idle";
        }
      } catch (err) {
        toast(`Update failed: ${err}`, { kind: "error" });
        status = "available";
      }
    } else {
      await refresh();
      if (status === "idle") toast("You are on the latest version");
    }
  }
</script>

<button
  class="update-btn"
  class:available={status === "available"}
  class:busy={status === "busy"}
  onclick={onClick}
  title={status === "available" && note
    ? `Version ${__APP_VERSION__} — update available: ${note}`
    : `Version ${__APP_VERSION__} — you are on the latest build`}
  aria-label="Update"
>
  {#if status === "available"}<span class="btn-inner"><Icon name="arrow-up" size={12} />Update</span>{:else if status === "busy"}Updating…{:else}Up to date{/if}
</button>

<style>
  .update-btn {
    padding: 3px 10px;
    /* Far right of the whole top bar (owner 2026-10-02): the + button
       stays next to the project tabs; auto margin pushes this to the end. */
    margin-left: auto;
    align-self: center;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: var(--text-xs);
    color: var(--text-muted);
    background: var(--bg);
    cursor: default;
    white-space: nowrap;
    transition:
      background-color var(--transition-fast),
      color var(--transition-fast),
      border-color var(--transition-fast);
  }

  .btn-inner {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  /* Available: accent-tinted chip (spec-014 D5 — quiet accent, never a
     solid fill). Text sits in accent.INK (theme pack: the bright
     accent.main is for indicator lines, not small text on the soft chip). */
  .update-btn.available {
    opacity: 1;
    color: var(--accent-ink);
    border-color: var(--accent);
    background: var(--accent-soft);
    cursor: pointer;
    font-weight: 600;
  }

  .update-btn.busy {
    opacity: 0.8;
  }

  /* Dim-while-current (SPEC-INFRA-001): with only light themes left
     (2026-10-14 pack), the muted text + hairline border at full opacity
     already read as subdued — the old dark-theme-only dim is gone. */
</style>
