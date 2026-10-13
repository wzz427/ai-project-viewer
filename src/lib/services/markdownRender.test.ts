import { describe, expect, it } from "vitest";
import { createMarkdownRenderer } from "$lib/services/markdownRender";

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
