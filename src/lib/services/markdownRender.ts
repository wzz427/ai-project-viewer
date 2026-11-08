/**
 * Markdown renderer factory (V1.5 §86–§89), extracted from MarkdownViewer
 * so the pipeline is unit-testable (2026-10-13 typography round).
 *
 * Security posture is unchanged from the original inline config:
 * - html:false stays load-bearing (§88): raw HTML is escaped, never
 *   interpreted.
 * - The highlight callback only ever returns markup produced by
 *   highlight.js (which escapes its input) or "" (markdown-it then escapes
 *   the fence itself) — fenced content can never smuggle raw HTML even
 *   with an adversarial language tag.
 *
 * Syntax coloring (owner 2026-10-13): curated language subset, registered
 * on the shared core instance. Unregistered fences render as plain
 * (escaped) code — same as before the feature.
 *
 * Math + diagrams (spec-020, owner 2026-11-08 "都加"):
 * - KaTeX via VS Code's markdown-it plugin: $inline$, $$block$$ and
 *   ```math fences. LAZY: KaTeX evaluates to ~2.7 MB resident V8 heap
 *   (measured 2026-11-08, node --expose-gc: module init 2.67 MB, 2.95 MB
 *   after a first render) — unlike the hljs grammars, which nearly every
 *   document uses, it is imported only for documents that may contain
 *   math (memory rule, V1.5 §6). Its renderer emits katex markup directly
 *   (trust off by default: no \href injection surface), so html:false
 *   still holds.
 * - ```mermaid fences become escaped-source placeholders here; the
 *   MarkdownViewer lazily imports the engine ONLY for documents that
 *   actually contain one.
 */
import MarkdownIt from "markdown-it";
import taskLists from "markdown-it-task-lists";
import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import c from "highlight.js/lib/languages/c";
import cpp from "highlight.js/lib/languages/cpp";
import csharp from "highlight.js/lib/languages/csharp";
import css from "highlight.js/lib/languages/css";
import diff from "highlight.js/lib/languages/diff";
import go from "highlight.js/lib/languages/go";
import ini from "highlight.js/lib/languages/ini";
import java from "highlight.js/lib/languages/java";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import markdown from "highlight.js/lib/languages/markdown";
import powershell from "highlight.js/lib/languages/powershell";
import python from "highlight.js/lib/languages/python";
import rust from "highlight.js/lib/languages/rust";
import sql from "highlight.js/lib/languages/sql";
import typescript from "highlight.js/lib/languages/typescript";
import xml from "highlight.js/lib/languages/xml";
import yaml from "highlight.js/lib/languages/yaml";

// Registered once per app (module scope): instance + language grammars
// live in the module cache, not per-viewer — one resident copy however
// many markdown tabs are open (memory rule, V1.5 §6/2026-10-02).
const LANGS: Record<string, Parameters<typeof hljs.registerLanguage>[1]> = {
  bash,
  c,
  cpp,
  csharp,
  css,
  diff,
  go,
  ini,
  java,
  javascript,
  json,
  markdown,
  powershell,
  python,
  rust,
  sql,
  typescript,
  xml,
  yaml,
};
for (const [name, lang] of Object.entries(LANGS)) {
  hljs.registerLanguage(name, lang);
}
// Common fence aliases (```py, ```ts, ```yml … must not fall back to plain).
hljs.registerAliases(["py"], { languageName: "python" });
hljs.registerAliases(["js", "jsx"], { languageName: "javascript" });
hljs.registerAliases(["ts", "tsx"], { languageName: "typescript" });
hljs.registerAliases(["sh", "shell", "zsh"], { languageName: "bash" });
hljs.registerAliases(["yml"], { languageName: "yaml" });
hljs.registerAliases(["c++"], { languageName: "cpp" });
hljs.registerAliases(["cs"], { languageName: "csharp" });
hljs.registerAliases(["ps1"], { languageName: "powershell" });
hljs.registerAliases(["md"], { languageName: "markdown" });
hljs.registerAliases(["html", "htm"], { languageName: "xml" });

/** Auto-detect candidates for unmarked / ```text fences (owner 2026-10-14
 * "Markdown 里面没有任何着色" — his real docs mark almost every fence as
 * `text` or nothing, e.g. V1.5: text×234 + unmarked×244 vs typescript×9).
 * Structured languages with strong signals only; ambiguous grammars are
 * excluded so prose/diagram fences don't get random colors. */
const AUTO_LANGS = [
  "json", "yaml", "python", "javascript", "typescript", "bash",
  "powershell", "sql", "xml", "css", "rust", "java", "cpp", "go", "ini",
  "diff",
];
/** Below this hljs relevance the fence stays plain. Measured 2026-10-14 on
 * real samples: legit snippets score 2–6 (py/sql/json/bash/ts/yaml), while
 * flow diagrams, Chinese prose and ASCII tables score 0–1 — so 2 is the
 * separating line. `graph TD` pseudo-syntax can reach 3 (css), accepted:
 * explicit ```mermaid fences bypass auto-detect anyway. */
const AUTO_RELEVANCE_FLOOR = 2;
/** Long text fences are almost never code (and auto-detecting them is the
 * slow path on fence-heavy docs like V1.5's 480+ blocks). */
const AUTO_MAX_CHARS = 2000;
/** Fence info strings that mean "no language" — auto-detect these. */
const PLAIN_FENCE = new Set(["", "text", "plain", "plaintext"]);

type Md = InstanceType<typeof MarkdownIt>;
type KatexPlugin = typeof import("@vscode/markdown-it-katex").default;

/** Installer for the lazily-loaded math plugin; null until first need. */
let installMath: ((md: Md) => void) | null = null;
let mathLoad: Promise<void> | null = null;
const MATH_FENCE = /^[ \t]*(?:`{3,}|~{3,})[ \t]*math\b/im;

/** Could this document contain math? Any `$`, or a ```math fence. A cheap
 * superset check: a currency-only document loads the engine for nothing
 * (output still correct — the plugin's own delimiter rules decide). */
export function mayContainMath(text: string): boolean {
  return text.includes("$") || MATH_FENCE.test(text);
}

export function mathEngineReady(): boolean {
  return installMath !== null;
}

/** Idempotent per-renderer attach (markdown-it must not get the math
 * plugin twice — rules would stack). Used by BOTH the factory (renderers
 * created after the engine landed) and ensureMath (renderers already in
 * service when it lands). */
const mathAttached = new WeakSet<Md>();
function attachMath(md: Md) {
  if (!installMath || mathAttached.has(md)) return;
  mathAttached.add(md);
  installMath(md);
}

/** Load the math engine on first need and attach it to a renderer that
 * may predate the load (first viewer of a math document does exactly
 * that). Resolving is not enough for its output — the caller re-renders
 * once attached (MarkdownViewer.mathRev). */
export function ensureMath(md: Md): Promise<void> {
  if (mathAttached.has(md)) return Promise.resolve();
  return loadMathEngine().then(() => attachMath(md));
}

/** Import KaTeX + plugin + stylesheet on first need. One shared promise:
 * several viewers asking at once trigger a single load; renderers created
 * after it resolves get math. A failed load may be retried later. */
export function loadMathEngine(): Promise<void> {
  if (!mathLoad) {
    mathLoad = Promise.all([
      import("@vscode/markdown-it-katex"),
      import("katex/dist/katex.min.css"),
    ]).then(([mod]) => {
      // CJS interop: the bundler hands over the function as `default`,
      // Node's ESM loader the whole exports object — accept both shapes.
      const d = (mod as unknown as { default: unknown }).default;
      const plugin = (typeof d === "function"
        ? d
        : (d as { default: unknown }).default) as KatexPlugin;
      installMath = (md) => {
        md.use(plugin, { enableFencedBlocks: true });
      };
    });
    mathLoad.catch(() => {
      mathLoad = null;
    });
  }
  return mathLoad;
}

export function createMarkdownRenderer(): InstanceType<typeof MarkdownIt> {
  const md: Md = new MarkdownIt({
    html: false, // §88: raw HTML disabled — output is escaped
    linkify: true,
    typographer: true,
    highlight(code, lang) {
      const name = lang.trim().toLowerCase();
      if (PLAIN_FENCE.has(name) && code.length <= AUTO_MAX_CHARS) {
        try {
          const auto = hljs.highlightAuto(code, AUTO_LANGS);
          if (auto.relevance >= AUTO_RELEVANCE_FLOOR) return auto.value;
        } catch {
          // auto-detect is best-effort: fall through to plain
        }
        return ""; // markdown-it HTML-escapes and wraps in <pre><code>
      }
      if (name && hljs.getLanguage(name)) {
        try {
          return hljs.highlight(code, { language: name, ignoreIllegals: true }).value;
        } catch {
          // malformed fence content: fall through to markdown-it's escape
        }
      }
      return ""; // markdown-it HTML-escapes and wraps in <pre><code>
    },
  })
    .use(taskLists, { enabled: false, label: true });
  attachMath(md); // no-op until the engine is loaded (spec-020)

  // ```mermaid → placeholder carrying the ESCAPED source (spec-020). Checked
  // before the katex/hljs fence path so diagram source is never colored or
  // auto-detected; the viewer swaps in the SVG once the engine is loaded.
  const baseFence = md.renderer.rules.fence;
  md.renderer.rules.fence = (tokens, idx, options, env, self) => {
    const token = tokens[idx];
    const info = token?.info.trim().toLowerCase() ?? "";
    if (token && (info === "mermaid" || info.startsWith("mermaid "))) {
      return `<div class="mermaid-block"><pre>${md.utils.escapeHtml(token.content)}</pre></div>\n`;
    }
    return baseFence
      ? baseFence(tokens, idx, options, env, self)
      : self.renderToken(tokens, idx, options);
  };
  return md;
}
