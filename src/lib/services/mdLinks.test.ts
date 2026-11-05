import { describe, expect, it } from "vitest";
import { resolveDocLink } from "$lib/services/mdLinks";

// spec-018 V1/V7: every dirty href form that used to produce a broken
// join, plus the two null paths (escape / no path).
describe("resolveDocLink", () => {
  it.each([
    // The owner's reported case: ../ link out of docs/ into a dot folder.
    ["docs/guide.md", "../.agents/skills/agent-team-workflow/SKILL.md",
      ".agents/skills/agent-team-workflow/SKILL.md"],
    // Same-directory and explicit ./ forms collapse clean.
    ["docs/guide.md", "sibling.md", "docs/sibling.md"],
    ["docs/guide.md", "./sibling.md", "docs/sibling.md"],
    ["README.md", "notes/a.md", "notes/a.md"], // doc at project root
    // Double separators (root doc + "/x", or sloppy "//").
    ["README.md", "/docs/spec.md", "docs/spec.md"], // D2: root-relative
    ["notes/guide.md", "/docs/spec.md", "docs/spec.md"],
    ["README.md", "docs//spec.md", "docs/spec.md"],
    // Up-and-back-down must not leave stale segments.
    ["a/b/c.md", "../../b2/x.md", "b2/x.md"], // a/b + ../../ = root
    ["a/b/c.md", "../b2/x.md", "a/b2/x.md"],
    ["a/b/c.md", ".././d/x.md", "a/d/x.md"],
    // Percent-encoding round-trips to the on-disk name.
    ["docs/guide.md", "my%20file.md", "docs/my file.md"],
    ["docs/guide.md", "100%25.md", "docs/100%.md"], // literal % survived
    // Fragment/query address sections, not the file.
    ["docs/guide.md", "../README.md#tasks", "README.md"],
    ["docs/guide.md", "sibling.md?v=2", "docs/sibling.md"],
    ["docs/guide.md", "/README.md#top", "README.md"],
    // Backslash separators are legal markdown hrefs on Windows.
    ["docs/guide.md", "..\\README.md", "README.md"],
  ])("%s + %s → %s", (doc, href, want) => {
    expect(resolveDocLink(doc, href)).toBe(want);
  });

  it.each([
    // Escape above the project root (D3) — caller toasts, never opens.
    ["README.md", "../outside.md"],
    ["docs/a/b.md", "../../../up.md"],
    // No path content at all.
    ["README.md", "#anchor-only"],
    ["README.md", "?q=1"],
    ["README.md", "/"], // bare root — nothing to open
    ["README.md", "./"],
    ["README.md", "."],
  ])("%s + %s → null", (doc, href) => {
    expect(resolveDocLink(doc, href)).toBeNull();
  });
});
