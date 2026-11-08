import { beforeAll, describe, expect, it } from "vitest";
import {
  createMarkdownRenderer,
  loadMathEngine,
  mathEngineReady,
  mayContainMath,
} from "$lib/services/markdownRender";

function render(src: string): string {
  return createMarkdownRenderer().render(src);
}

describe("createMarkdownRenderer", () => {
  it("escapes raw HTML (§88 — html:false is load-bearing)", () => {
    const out = render('<script>alert("x")</script>\n\n<img src=x onerror=alert(1)>');
    expect(out).not.toContain("<script>");
    expect(out).not.toContain("<img");
    expect(out).toContain("&lt;script&gt;");
  });

  it("highlights a python fence with hljs token spans", () => {
    const out = render('```python\ndef hello():\n    return "hi"\n```');
    expect(out).toContain('<span class="hljs-keyword">def</span>');
    expect(out).toContain('<span class="hljs-string">&quot;hi&quot;</span>');
  });

  it("resolves common fence aliases (py/js/ts/sh/yml)", () => {
    // Content chosen to actually tokenize in each grammar — a JS snippet
    // inside ```sh legitimately yields no spans (bash sees no keywords).
    const cases: [string, string][] = [
      ["py", "x = 1"],
      ["js", "let x = 1"],
      ["ts", "let x = 1"],
      ["sh", "if true; then echo 1; fi"],
      ["yml", "name: test"],
    ];
    for (const [fence, snippet] of cases) {
      const out = render("```" + fence + "\n" + snippet + "\n```");
      expect(out, fence).toMatch(/hljs-(keyword|built_in|literal|number|attr|string)/);
    }
  });

  it("renders an unknown fence language as escaped plain code, no spans", () => {
    const out = render("```brainfuck\n+++<script>\n```");
    expect(out).not.toContain("hljs-");
    expect(out).toContain("&lt;script&gt;");
  });

  // 2026-10-14 (owner "Markdown 里面没有任何着色"): unmarked and ```text
  // fences — the overwhelming majority in his real docs (V1.5 alone:
  // text×234 + unmarked×244) — auto-detect over a structured-language
  // subset with a relevance floor.
  it("auto-colors an UNMARKED fence holding obvious code", () => {
    const out = render("```\nSELECT id FROM users WHERE age > 18;\n```");
    expect(out).toMatch(/hljs-keyword/);
  });

  it("auto-colors a ```text fence holding JSON", () => {
    const out = render('```text\n{"name": "aiv", "version": 2}\n```');
    expect(out).toMatch(/hljs-(attr|number|string)/);
  });

  it("keeps a pseudo-code flow diagram plain (no false-positive colors)", () => {
    const out = render("```text\n人 ← 编写代码\n     ↓\nIDE 辅助\n     ↓\nAgent 接管\n```");
    expect(out).not.toContain("hljs-");
    // content still escaped, never dropped
    expect(out).toContain("编写代码");
  });

  it("keeps an unknown explicit language plain even though it looks like code", () => {
    // mermaid-style fence: explicit unknown languages stay untouched —
    // auto-detect is only for fences that DECLARE no language. (spec-020:
    // ```mermaid now has its own placeholder, asserted separately below.)
    const out = render("```someunknownlang\nSELECT 1;\n```");
    expect(out).not.toContain("hljs-");
  });

  it("keeps task lists non-interactive with labels", () => {
    const out = render("- [x] done thing\n- [ ] todo thing");
    expect(out).toContain('type="checkbox"');
    expect(out).toContain("disabled");
    expect(out).toContain("<label");
    expect(out).toContain("checked");
  });

  it("linkifies bare URLs but leaves plain text untouched", () => {
    const out = render("see https://example.com/x now");
    expect(out).toContain('href="https://example.com/x"');
    expect(render("no links here")).not.toContain("<a ");
  });
});

// ---- spec-020 (owner 2026-11-08 "都加"): math + mermaid ----
// Runs AFTER the block above so the FIRST tests still see the unloaded
// world (mathEngineReady() false, $…$ literal) — the lazy-load seam is
// itself under test, so file order is load-bearing.
describe("spec-020 lazy math engine", () => {
  it("leaves $…$ literal while the engine is not loaded", () => {
    expect(mathEngineReady()).toBe(false);
    const out = render("Mass–energy: $E = mc^2$ holds.");
    expect(out).not.toContain('class="katex"');
    expect(out).toContain("$E = mc^2$");
  });

  it("mayContainMath is a cheap superset of the real documents", () => {
    expect(mayContainMath("价格 $50，费用 $70。")).toBe(true); // currency: superset, ok
    expect(mayContainMath("no math at all")).toBe(false);
    expect(mayContainMath("```math\n\\pi\n```")).toBe(true);
    expect(mayContainMath("plain `text` fences only")).toBe(false);
  });

  it("loads once, then new renderers render math", async () => {
    await loadMathEngine();
    expect(mathEngineReady()).toBe(true);
    const out = render("Mass–energy: $E = mc^2$ holds.");
    expect(out).toContain('class="katex"');
    expect(out).not.toContain("$E"); // delimiters consumed
  });
});

describe("spec-020 math rendering (engine loaded)", () => {
  beforeAll(() => loadMathEngine());

  it("renders $$…$$ display math centered", () => {
    const out = render("$$\\int_{-\\infty}^{\\infty} e^{-x^2}\\,dx = \\sqrt{\\pi}$$");
    expect(out).toContain("katex-display");
  });

  it("renders a ```math fence as display math", () => {
    const out = render("```math\n\\frac{a}{b}\n```");
    expect(out).toContain("katex-display");
  });

  it("does NOT turn adjacent currency dollars into math", () => {
    // VS Code plugin rules: opening $ must not be followed by a space,
    // closing $ must not be PRECEDED by one — "费用 " fails, so both
    // dollars stay literal. Owner docs carry prices; this is the
    // false-positive guard.
    const out = render("价格 $50，费用 $70。");
    expect(out).not.toContain('class="katex"');
    expect(out).toContain("$50");
    expect(out).toContain("$70");
  });

  it("keeps \\$ escaped dollars literal", () => {
    const out = render("成本是 \\$100 整。");
    expect(out).not.toContain('class="katex"');
    expect(out).toContain("$100");
  });

  it("turns a ```mermaid fence into an escaped-source placeholder", () => {
    const out = render("```mermaid\ngraph TD; A-->B;\n```");
    expect(out).toContain('<div class="mermaid-block"><pre>');
    expect(out).toContain("graph TD; A--&gt;B;");
    expect(out).not.toContain("hljs-"); // never colored, never auto-detected
  });

  it("escapes hostile markup inside a mermaid placeholder (§88 posture)", () => {
    const out = render("```mermaid\ngraph TD; A--><script>alert(1)</script>;\n```");
    expect(out).toContain("&lt;script&gt;");
    expect(out).not.toContain("<script>");
  });

  it("leaves a normal python fence untouched by the mermaid wrapper", () => {
    const out = render("```python\ndef f():\n    pass\n```");
    expect(out).toContain('<span class="hljs-keyword">def</span>');
    expect(out).not.toContain("mermaid-block");
  });
});
