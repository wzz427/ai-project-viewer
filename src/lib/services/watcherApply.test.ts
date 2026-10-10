import { describe, expect, it } from "vitest";
import {
  isGone,
  needsReload,
  renamedRel,
  type FsChangeBatch,
} from "$lib/services/watcherApply";

function batch(partial: Partial<FsChangeBatch>): FsChangeBatch {
  return {
    root: "R",
    changed: [],
    removed: [],
    renames: [],
    storm: false,
    ...partial,
  };
}

describe("needsReload (exact-path only)", () => {
  it("matches the file itself", () => {
    expect(needsReload("src/main.py", batch({ changed: ["src/main.py"] }))).toBe(true);
  });

  it("does not match an ancestor directory's activity", () => {
    // A new sibling file changed the dir entry, not our content.
    expect(needsReload("src/main.py", batch({ changed: ["src"] }))).toBe(false);
  });

  it("does not match a descendant", () => {
    expect(needsReload("src", batch({ changed: ["src/main.py"] }))).toBe(false);
  });
});

describe("isGone (removal covers descendants)", () => {
  it("matches the exact removed path", () => {
    expect(isGone("a.md", batch({ removed: ["a.md"] }))).toBe(true);
  });

  it("matches files under a removed directory", () => {
    expect(isGone("src/deep/main.py", batch({ removed: ["src"] }))).toBe(true);
  });

  it("matches the From side of a rename (file or ancestor)", () => {
    expect(isGone("old.md", batch({ renames: [{ from: "old.md", to: "new.md" }] }))).toBe(true);
    expect(
      isGone("old/main.py", batch({ renames: [{ from: "old", to: "new" }] })),
    ).toBe(true);
  });

  it("ignores unrelated paths", () => {
    expect(isGone("src/main.py", batch({ removed: ["docs"] }))).toBe(false);
  });
});

describe("renamedRel (file and ancestor renames)", () => {
  const renames = [
    { from: "design.md", to: "architecture.md" },
    { from: "src/old", to: "src/new" },
  ];

  it("follows an exact file rename", () => {
    expect(renamedRel("design.md", renames)).toBe("architecture.md");
  });

  it("follows an ancestor directory rename", () => {
    expect(renamedRel("src/old/deep/main.py", renames)).toBe("src/new/deep/main.py");
  });

  it("returns null when unaffected", () => {
    expect(renamedRel("other.py", renames)).toBeNull();
  });

  it("does not match name prefixes without the separator", () => {
    expect(renamedRel("src/oldish/main.py", renames)).toBeNull();
  });
});
