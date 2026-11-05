import { describe, expect, it } from "vitest";
import {
  ancestorDirsOf,
  keepNamesUnder,
  openChainDirs,
  visibleEntries,
} from "$lib/constants/treeVisibility";
import type { TreeEntry } from "$lib/services/tauri";

const dir = (name: string, system = false): TreeEntry => ({
  name,
  isDir: true,
  systemGenerated: system,
});
const file = (name: string): TreeEntry => ({
  name,
  isDir: false,
  systemGenerated: false,
});

// spec-018 V5: the derived temp-display chain — what shows, what doesn't.
describe("openChainDirs / keepNamesUnder (spec-018 B)", () => {
  it("ancestorDirsOf walks every dir hop", () => {
    expect(ancestorDirsOf("a/b/c/d.md")).toEqual(["a", "a/b", "a/b/c"]);
    expect(ancestorDirsOf("root.md")).toEqual([]);
  });

  it("chain covers all open files, deduped", () => {
    const chain = openChainDirs([
      "node_modules/dep/a.md",
      "node_modules/dep/sub/b.md",
      "docs/x.md",
    ]);
    expect([...chain].sort()).toEqual(
      ["docs", "node_modules", "node_modules/dep", "node_modules/dep/sub"].sort(),
    );
  });

  it("keepNamesUnder picks one level of names (root = '.')", () => {
    const chain = openChainDirs(["node_modules/dep/sub/b.md"]);
    expect(keepNamesUnder(chain, ".")).toEqual(new Set(["node_modules"]));
    expect(keepNamesUnder(chain, "node_modules")).toEqual(new Set(["dep"]));
    expect(keepNamesUnder(chain, "node_modules/dep")).toEqual(
      new Set(["sub"]),
    );
    expect(keepNamesUnder(chain, "docs")).toEqual(new Set());
  });
});

describe("visibleEntries keepNames override", () => {
  it("toggle off: hidden dir kept only when its name is in keepNames", () => {
    const entries = [dir("node_modules", true), dir("docs"), file("a.md")];
    const noKeep = visibleEntries(entries, false);
    expect(noKeep.map((e) => e.name)).toEqual(["docs", "a.md"]);
    const kept = visibleEntries(entries, false, new Set(["node_modules"]));
    expect(kept.map((e) => e.name)).toEqual(["node_modules", "docs", "a.md"]);
  });

  it("toggle on: keepNames is a no-op", () => {
    const entries = [dir("node_modules", true)];
    expect(visibleEntries(entries, true, new Set())).toHaveLength(1);
  });
});
