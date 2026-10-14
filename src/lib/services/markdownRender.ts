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

export function createMarkdownRenderer(): InstanceType<typeof MarkdownIt> {
  return new MarkdownIt({
    html: false, // §88: raw HTML disabled — output is escaped
    linkify: true,
    typographer: true,
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value;
        } catch {
          // malformed fence content: fall through to markdown-it's escape
        }
      }
      return ""; // markdown-it HTML-escapes and wraps in <pre><code>
    },
  }).use(taskLists, { enabled: false, label: true });
}
