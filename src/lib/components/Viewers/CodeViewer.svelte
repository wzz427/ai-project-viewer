<script lang="ts">
  /**
   * Read-only CodeMirror host for Text/Code/JSON-Source/Markdown-Source
   * (V1.5 §100/§107): line numbers, syntax highlight, Ctrl+F (via the app
   * dispatcher + search registry), scroll restore on remount (§160.5).
   */
  import { onMount } from "svelte";
  import { EditorState, Compartment, type Extension } from "@codemirror/state";
  import { EditorView, lineNumbers } from "@codemirror/view";
  import { search } from "@codemirror/search";
  import { StreamLanguage, defaultHighlightStyle, syntaxHighlighting } from "@codemirror/language";
  import { oneDark } from "@codemirror/theme-one-dark";
  import * as legacy from "./codeLanguages";
  import { setActiveSearchView } from "./codeSearchRegistry";
  import { settings } from "$lib/stores/settingsStore.svelte";
  import { saveScrollPosition, type RuntimeTab } from "$lib/stores/tabsStore.svelte";

  let {
    rootPath,
    tab,
    text,
    language,
    fixedLanguage,
  }: {
    rootPath: string;
    tab: RuntimeTab;
    text: string;
    /** Extension-derived language name; omit for plain text. */
    language?: string;
    /** Explicit CM extension (e.g. JSON); wins over `language`. */
    fixedLanguage?: Extension;
  } = $props();

  let host = $state<HTMLElement | null>(null);
  let view: EditorView | null = null;

  const themeComp = new Compartment();

  function isDark(): boolean {
    if (settings.theme === "dark") return true;
    if (settings.theme === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function langExtensions(): Extension[] {
    if (fixedLanguage) return [fixedLanguage];
    const lang = legacy.languageFor(language ?? "");
    return lang ? [lang] : [];
  }

  onMount(() => {
    view = new EditorView({
      state: EditorState.create({
        doc: text,
        extensions: [
          lineNumbers(),
          EditorState.readOnly.of(true),
          EditorView.editable.of(false),
          syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
          search({ top: true }),
          ...langExtensions(),
          themeComp.of(isDark() ? oneDark : []),
          EditorView.theme({
            "&": { backgroundColor: "transparent", height: "100%" },
            ".cm-scroller": { fontFamily: "var(--font-mono)", overflow: "auto" },
            ".cm-content": {
              fontSize: "var(--viewer-font-size)",
              caretColor: "transparent",
            },
            ".cm-gutters": {
              backgroundColor: "transparent",
              color: "var(--text-muted)",
              border: "none",
            },
          }),
        ],
      }),
      parent: host!,
    });
    view.scrollDOM.scrollTop = tab.scrollPosition ?? 0;
    setActiveSearchView(view);

    return () => {
      if (view) saveScrollPosition(rootPath, tab.relativePath, view.scrollDOM.scrollTop);
      setActiveSearchView(null);
      view?.destroy();
      view = null;
    };
  });

  // Follow app theme changes without rebuilding the document.
  $effect(() => {
    const dark = isDark();
    view?.dispatch({ effects: themeComp.reconfigure(dark ? oneDark : []) });
  });
</script>

<div class="code-viewer" bind:this={host}></div>

<style>
  .code-viewer {
    height: 100%;
    overflow: hidden;
    font-size: 12.5px;
  }
</style>
