<script lang="ts">
  /**
   * Read-only CodeMirror host for Text/Code/JSON-Source/Markdown-Source
   * (V1.5 §100/§107): line numbers, syntax highlight, Ctrl+F (via the app
   * dispatcher + search registry), scroll restore on remount (§160.5).
   */
  import { EditorState, Compartment, type Extension } from "@codemirror/state";
  import { EditorView, lineNumbers } from "@codemirror/view";
  import { search } from "@codemirror/search";
  import { StreamLanguage, defaultHighlightStyle, syntaxHighlighting } from "@codemirror/language";
  import { oneDark } from "@codemirror/theme-one-dark";
  import * as legacy from "./codeLanguages";
  import { setActiveSearchView } from "./codeSearchRegistry";
  import ViewerToolbar from "./ViewerToolbar.svelte";
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

  // Build the editor, and REBUILD it whenever the global viewer font knob
  // (§22) turns. The knob rides a CSS variable, which CodeMirror cannot
  // see: a live A+/A− change leaves its cached line heights (and the
  // gutter elements' explicit heights, set from those measurements) stale,
  // and the line-number column drifts off the text line by line (owner
  // 2026-10-11 screenshot; probe: 14→20px = −100px on a 12-line file).
  // requestMeasure/measure re-measure paths proved unreliable offscreen
  // (RAF throttling + the gutter's flag-driven refresh), so this uses the
  // same deterministic rebuild the watcher's contentRev already uses
  // (§160.5): a fresh view measures at the current size by construction.
  // Scroll survives via the existing save/restore pair.
  $effect(() => {
    void settings.fontSize;
    const v = new EditorView({
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
              // Numbers scale with the content (VS Code behavior); heights
              // stay exact because the view is rebuilt at this size.
              fontSize: "var(--viewer-font-size)",
            },
          }),
        ],
      }),
      parent: host!,
    });
    view = v;
    v.scrollDOM.scrollTop = tab.scrollPosition ?? 0;
    setActiveSearchView(v);

    return () => {
      saveScrollPosition(rootPath, tab.relativePath, v.scrollDOM.scrollTop);
      setActiveSearchView(null);
      v.destroy();
      if (view === v) view = null;
    };
  });

  // Follow app theme changes without rebuilding the document.
  $effect(() => {
    const dark = isDark();
    view?.dispatch({ effects: themeComp.reconfigure(dark ? oneDark : []) });
  });

  // ---- toolbar find (SPEC-INFRA-003): one doc scan feeds both count and
  // jump; positions in sliceString space are doc positions (\n included).
  function scanPositions(q: string): number[] {
    if (!view || !q) return [];
    const hay = view.state.doc.sliceString(0).toLowerCase();
    const needle = q.toLowerCase();
    const out: number[] = [];
    let i = hay.indexOf(needle);
    while (i !== -1) {
      out.push(i);
      i = hay.indexOf(needle, i + Math.max(1, needle.length));
    }
    return out;
  }

  const findApi = {
    count: (q: string) => scanPositions(q).length,
    jump: (q: string, index: number) => {
      const pos = scanPositions(q)[index];
      if (pos === undefined || !view) return;
      view.dispatch({
        selection: { anchor: pos, head: pos + q.length },
        effects: EditorView.scrollIntoView(pos, { y: "center" }),
      });
      view.focus();
    },
  };
</script>

<div class="code-viewer">
  <ViewerToolbar {findApi} />
  <div class="host" bind:this={host}></div>
</div>

<style>
  .code-viewer {
    height: 100%;
    overflow: hidden;
    font-size: 12.5px;
    display: flex;
    flex-direction: column;
  }

  .host {
    flex: 1;
    min-height: 0;
  }
</style>
