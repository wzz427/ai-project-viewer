import { describe, expect, it } from "vitest";

import type { TreeEntry } from "$lib/services/tauri";
import { naturalCompare, visibleSorted } from "$lib/services/treeSort";

function dir(name: string, systemGenerated = false): TreeEntry {
  return { name, isDir: true, systemGenerated };
}

function file(name: string): TreeEntry {
  return { name, isDir: false, systemGenerated: false };
}

function names(entries: TreeEntry[]): string[] {
  return entries.map((e) => e.name);
}

const basePrefs = {
  sortMode: "name" as const,
  foldersFirst: true,
  showSystemFolders: false,
  pinned: undefined,
};

describe("visibility filter (V1.5 §29/§30)", () => {
  it("hides system-generated dirs by default and shows them when toggled", () => {
    const entries = [dir(".git", true), dir("node_modules", true), dir("dist"), file("a.txt")];

    expect(names(visibleSorted(entries, { ...basePrefs }))).toEqual([
      "dist",
      "a.txt",
    ]);
    expect(
      names(visibleSorted(entries, { ...basePrefs, showSystemFolders: true })),
    ).toEqual([".git", "dist", "node_modules", "a.txt"]);
  });

  it("never hides dist/build/target (visible by default, §29)", () => {
    const entries = [dir("dist"), dir("build"), dir("target")];
    expect(names(visibleSorted(entries, { ...basePrefs }))).toEqual([
      "build",
      "dist",
      "target",
    ]);
  });
});

describe("name mode (V1.5 §34)", () => {
  it("folders first when enabled", () => {
    const entries = [file("a.txt"), dir("zeta"), dir("beta"), file("b.txt")];
    expect(names(visibleSorted(entries, { ...basePrefs }))).toEqual([
      "beta",
      "zeta",
      "a.txt",
      "b.txt",
    ]);
  });

  it("mixed by name when folders first is off", () => {
    const entries = [file("b.txt"), dir("alpha"), file("a.txt")];
    expect(
      names(visibleSorted(entries, { ...basePrefs, foldersFirst: false })),
    ).toEqual(["a.txt", "alpha", "b.txt"]);
  });

  it("natural and case-insensitive: file2 < file10, a ≈ A", () => {
    expect(naturalCompare("file2", "file10")).toBeLessThan(0);
    expect(naturalCompare("Beta", "alpha")).toBeGreaterThan(0); // b > a
    expect(naturalCompare("same", "SAME")).toBe(0);
    const entries = [file("file10"), file("File2")];
    expect(names(visibleSorted(entries, { ...basePrefs, foldersFirst: false }))).toEqual([
      "File2",
      "file10",
    ]);
  });
});

describe("favorites mode (V1.5 §35/§36)", () => {
  const entries = [
    file("config.yaml"),
    dir("docs"),
    file("architecture.md"),
    dir("src"),
    file("README.md"),
  ];

  it("pinned area keeps manual order with files and folders interleaved", () => {
    const pinned = ["architecture.md", "README.md", "src", "config.yaml"];
    expect(
      names(
        visibleSorted(entries, {
          ...basePrefs,
          sortMode: "favorites",
          pinned,
        }),
      ),
    ).toEqual([
      "architecture.md",
      "README.md",
      "src",
      "config.yaml",
      "docs",
    ]);
  });

  it("folders first does NOT apply inside the pinned area but does in unpinned", () => {
    const pinned = ["README.md", "src"];
    const got = names(
      visibleSorted(entries, {
        ...basePrefs,
        sortMode: "favorites",
        foldersFirst: true,
        pinned,
      }),
    );
    // Pinned: file (README.md) before folder (src) — manual order wins (§36).
    // Unpinned: docs (dir) above architecture.md/config.yaml (files).
    expect(got).toEqual(["README.md", "src", "docs", "architecture.md", "config.yaml"]);
  });

  it("pinned names missing from disk are skipped (cleanup is the store's job, §42)", () => {
    const pinned = ["gone.txt", "README.md"];
    expect(
      names(
        visibleSorted(entries, {
          ...basePrefs,
          sortMode: "favorites",
          pinned,
        }),
      )[0],
    ).toBe("README.md");
  });

  it("a brand-new unpinned file lands auto-sorted (§40)", () => {
    const withNew = [...entries, file("zzz-new.log")];
    const pinned = ["README.md"];
    expect(
      names(
        visibleSorted(withNew, {
          ...basePrefs,
          sortMode: "favorites",
          pinned,
        }),
      ),
    ).toEqual([
      "README.md",
      "docs",
      "src",
      "architecture.md",
      "config.yaml",
      "zzz-new.log",
    ]);
  });
});
