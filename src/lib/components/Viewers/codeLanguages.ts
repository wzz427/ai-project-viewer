/**
 * Extension → CodeMirror language mapping (V1.5 §107 list).
 * .cmd/.bat view as plain text ("viewable", not highlighted — §188 row).
 */
import type { Extension } from "@codemirror/state";
import { StreamLanguage } from "@codemirror/language";
import { python } from "@codemirror/legacy-modes/mode/python";
import { javascript } from "@codemirror/legacy-modes/mode/javascript";
import { rust } from "@codemirror/legacy-modes/mode/rust";
import { go } from "@codemirror/legacy-modes/mode/go";
import { c, cpp, java } from "@codemirror/legacy-modes/mode/clike";
import { css } from "@codemirror/legacy-modes/mode/css";
import { sass } from "@codemirror/legacy-modes/mode/sass";
import { sql } from "@codemirror/legacy-modes/mode/sql";
import { yaml } from "@codemirror/legacy-modes/mode/yaml";
import { toml } from "@codemirror/legacy-modes/mode/toml";
import { shell } from "@codemirror/legacy-modes/mode/shell";
import { powerShell } from "@codemirror/legacy-modes/mode/powershell";
import { html as htmlLang } from "@codemirror/lang-html";
import { markdown as markdownLang } from "@codemirror/lang-markdown";

const jsLike = StreamLanguage.define(javascript);

const MAP: Record<string, Extension> = {
  py: StreamLanguage.define(python),
  js: jsLike,
  ts: jsLike,
  tsx: jsLike,
  jsx: jsLike,
  rs: StreamLanguage.define(rust),
  go: StreamLanguage.define(go),
  java: StreamLanguage.define(java),
  c: StreamLanguage.define(c),
  cpp: StreamLanguage.define(cpp),
  h: StreamLanguage.define(cpp),
  html: htmlLang(),
  htm: htmlLang(),
  css: StreamLanguage.define(css),
  scss: StreamLanguage.define(sass),
  yaml: StreamLanguage.define(yaml),
  yml: StreamLanguage.define(yaml),
  toml: StreamLanguage.define(toml),
  sh: StreamLanguage.define(shell),
  ps1: StreamLanguage.define(powerShell),
  sql: StreamLanguage.define(sql({})),
  md: markdownLang(),
  markdown: markdownLang(),
};

export function languageFor(languageName: string): Extension | undefined {
  return MAP[languageName.toLowerCase()];
}
