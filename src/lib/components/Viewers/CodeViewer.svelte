<script lang="ts">
  /**
   * Read-only CodeMirror host for Text/Code/JSON-Source/Markdown-Source
   * (V1.5 §100/§107): line numbers, syntax highlight, Ctrl+F (via the app
   * dispatcher + search registry), scroll restore on remount (§160.5).
   */
  import { untrack } from "svelte";
  import { EditorState, Compartment, type Extension } from "@codemirror/state";
  import { EditorView, lineNumbers } from "@codemirror/view";
  import { search } from "@codemirror/search";
  import {
    HighlightStyle,
    StreamLanguage,
    syntaxHighlighting,
  } from "@codemirror/language";
  import { tags as t } from "@lezer/highlight";
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

  // Theme pack (owner 2026-10-14, spec §五): every editor color rides the
  // app.css tokens (--sy-*/--editor-*) instead of a packaged theme, so BOTH
  // light skins come from one static extension set — a theme switch is a
  // pure CSS repaint with zero CodeMirror reconfiguration (spec §二: no
  // scroll/selection reset on switch). One keyword/string/… token per
  // category mirrors the pack's palette; analysis capability (which token
  // CM emits) is untouched.
  const aivHighlight = HighlightStyle.define([
    { tag: [t.keyword, t.controlKeyword, t.moduleKeyword, t.definitionKeyword, t.self], color: "var(--sy-keyword)" },
    { tag: [t.operator, t.operatorKeyword], color: "var(--sy-operator)" },
    { tag: [t.punctuation, t.bracket, t.separator], color: "var(--sy-punctuation)" },
    { tag: [t.string, t.special(t.string), t.regexp, t.escape], color: "var(--sy-string)" },
    { tag: [t.number, t.integer, t.float], color: "var(--sy-number)" },
    { tag: [t.bool, t.atom, t.null], color: "var(--sy-boolean)" },
    { tag: [t.comment, t.meta], color: "var(--sy-comment)", fontStyle: "italic" },
    { tag: [t.function(t.variableName), t.macroName], color: "var(--sy-function)" },
    { tag: [t.typeName, t.className, t.namespace, t.propertyName], color: "var(--sy-type)" },
    { tag: t.variableName, color: "var(--editor-text)" },
    { tag: t.heading, color: "var(--accent-ink)", fontWeight: "600" },
    { tag: [t.link], color: "var(--accent-ink)", textDecoration: "underline" },
    { tag: [t.url], color: "var(--sy-string)" },
    { tag: [t.strong], fontWeight: "bold" },
    { tag: [t.emphasis], fontStyle: "italic" },
    { tag: [t.strikethrough], textDecoration: "line-through" },
    { tag: [t.inserted], color: "var(--git-a)" },
    { tag: [t.deleted], color: "var(--git-d)" },
    { tag: [t.invalid], color: "var(--danger)" },
    { tag: [t.monospace], fontFamily: "var(--font-mono)" },
  ]);

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
          // Soft-wrap: this is a reader — a minified HTML/report line must
          // not become a mile-long horizontal scroll (owner 2026-10-12).
          // Short code lines are untouched; only lines wider than the
          // viewport fold, so normal files render identically.
          EditorView.lineWrapping,
          EditorState.readOnly.of(true),
          EditorView.editable.of(false),
          syntaxHighlighting(aivHighlight),
          search({ top: true }),
          ...langExtensions(),
          EditorView.theme({
            "&": {
              backgroundColor: "transparent",
              height: "100%",
              color: "var(--editor-text)",
            },
            ".cm-scroller": { fontFamily: "var(--font-mono)", overflow: "auto" },
            ".cm-content": {
              fontSize: "var(--viewer-font-size)",
              caretColor: "transparent",
            },
            ".cm-gutters": {
              backgroundColor: "transparent",
              color: "var(--editor-linenum)",
              border: "none",
              // Numbers scale with the content (VS Code behavior); heights
              // stay exact because the view is rebuilt at this size.
              fontSize: "var(--viewer-font-size)",
            },
            // Toolbar-Find selections paint natively (::selection token in
            // app.css); the CM search panel's match layer draws its own
            // boxes — theme both to editor.match* (spec §四 搜索命中), with
            // the current hit carrying the heavier border.
            ".cm-searchMatch": {
              backgroundColor: "var(--editor-match-bg)",
              outline: "1px solid var(--editor-match-border)",
            },
            ".cm-searchMatch.cm-searchMatch-selected": {
              backgroundColor: "var(--editor-match-bg)",
              outline: "2px solid var(--editor-match-border)",
            },
          }),
        ],
      }),
      parent: host!,
    });
    view = v;
    // Restoring reads tab.scrollPosition OUTSIDE the dependency set (M13):
    // the cleanup below writes that very field, and a tracked read turned
    // every mount into a save→re-run→rebuild chain.
    v.scrollDOM.scrollTop = untrack(() => tab.scrollPosition) ?? 0;
    setActiveSearchView(v);

    return () => {
      saveScrollPosition(rootPath, tab.relativePath, v.scrollDOM.scrollTop);
      setActiveSearchView(null);
      v.destroy();
      if (view === v) view = null;
    };
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
    font-size: var(--text-base);
    display: flex;
    flex-direction: column;
  }

  .host {
    flex: 1;
    min-height: 0;
  }
</style>
