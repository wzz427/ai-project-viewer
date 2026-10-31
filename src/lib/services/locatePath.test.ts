import { describe, expect, it } from "vitest";

import type { TreeEntry } from "$lib/services/tauri";
import {
  matchProject,
  normalizeInput,
  resolveRel,
} from "$lib/services/locatePath";

function dir(name: string, systemGenerated = false): TreeEntry {
  return { name, isDir: true, systemGenerated };
}

function file(name: string): TreeEntry {
  return { name, isDir: false, systemGenerated: false };
}

const PROJECTS = [
  { id: "a", rootPath: "C:\\Work\\Alpha" },
  { id: "b", rootPath: "C:\\work\\beta" },
  // Nested inside Alpha — the more specific root must own its paths.
  { id: "c", rootPath: "C:\\Work\\Alpha\\packages\\inner" },
];

describe("normalizeInput (spec-017 tolerances)", () => {
  it("strips the quotes our own Copy Absolute Path adds", () => {
    expect(normalizeInput('"C:\\Work\\Alpha\\notes.md"')).toEqual({
      kind: "abs",
      segments: ["C:", "Work", "Alpha", "notes.md"],
    });
  });

  it("unifies separators and drops trailing slashes", () => {
    expect(normalizeInput("C:/Work/Alpha/src/")).toEqual({
      kind: "abs",
      segments: ["C:", "Work", "Alpha", "src"],
    });
  });

  it("strips the \\\\?\\ verbatim prefix canonicalize tools emit", () => {
    expect(normalizeInput("\\\\?\\C:\\Work\\Alpha")).toEqual({
      kind: "abs",
      segments: ["C:", "Work", "Alpha"],
    });
  });

  it("classifies drive-less input as relative and keeps segments", () => {
    expect(normalizeInput("src/main.py")).toEqual({
      kind: "rel",
      segments: ["src", "main.py"],
    });
    expect(normalizeInput("\\src\\main.py")).toEqual({
      kind: "rel",
      segments: ["src", "main.py"],
    });
  });

  it("rejects empty / quote-only / separator-only input", () => {
    expect(normalizeInput("")).toBeNull();
    expect(normalizeInput("   ")).toBeNull();
    expect(normalizeInput('""')).toBeNull();
    expect(normalizeInput("\\")).toBeNull();
  });
});

describe("matchProject (longest root wins, case-insensitive)", () => {
  it("matches under a root ignoring case and slash direction", () => {
    const m = matchProject(
      normalizeInput("c:\\WORK\\alpha\\SRC\\Main.Py")!,
      PROJECTS,
      null,
    );
    expect(m?.project.id).toBe("a");
    expect(m?.relSegments).toEqual(["SRC", "Main.Py"]);
  });

  it("prefers the nested (longer) root", () => {
    const m = matchProject(
      normalizeInput("C:\\Work\\Alpha\\packages\\inner\\lib.ts")!,
      PROJECTS,
      null,
    );
    expect(m?.project.id).toBe("c");
    expect(m?.relSegments).toEqual(["lib.ts"]);
  });

  it("a path equal to a root matches with no remainder", () => {
    const m = matchProject(normalizeInput("C:\\work\\Beta\\")!, PROJECTS, null);
    expect(m?.project.id).toBe("b");
    expect(m?.relSegments).toEqual([]);
  });

  it("rejects sibling prefixes that are not the root itself", () => {
    expect(
      matchProject(normalizeInput("C:\\Work\\Alphabet\\x")!, PROJECTS, null),
    ).toBeNull();
  });

  it("relative input resolves against the ACTIVE project only", () => {
    const m = matchProject(normalizeInput("src/main.py")!, PROJECTS, "b");
    expect(m?.project.id).toBe("b");
    expect(m?.relSegments).toEqual(["src", "main.py"]);
    expect(matchProject(normalizeInput("src")!, PROJECTS, null)).toBeNull();
  });
});

describe("resolveRel (true-case walk)", () => {
  const listing: Record<string, TreeEntry[]> = {
    ".": [dir("Src"), dir("node_modules", true), file("README.md")],
    Src: [dir("Deep"), file("Main.Py")],
    "Src/Deep": [file("leaf.txt")],
    node_modules: [dir("pkg")],
  };
  const list = async (relDir: string) => listing[relDir] ?? null;

  it("returns the DISK spelling even for wrong-case input", async () => {
    const r = await resolveRel(["SRC", "main.PY"], list);
    expect(r).toEqual({ rel: "Src/Main.Py", isDir: false, hiddenSystem: false });
  });

  it("flags targets inside a system-generated folder", async () => {
    const r = await resolveRel(["node_modules", "pkg"], list);
    expect(r?.hiddenSystem).toBe(true);
  });

  it("flags the system folder itself as hidden", async () => {
    const r = await resolveRel(["Node_Modules"], list);
    expect(r).toMatchObject({ rel: "node_modules", isDir: true, hiddenSystem: true });
  });

  it("null on a missing segment and on a file used mid-path", async () => {
    expect(await resolveRel(["nope"], list)).toBeNull();
    expect(await resolveRel(["Src", "Main.Py", "leaf.txt"], list)).toBeNull();
    expect(await resolveRel(["README.md", "x"], list)).toBeNull();
  });

  it("null when a level is unreadable", async () => {
    expect(await resolveRel(["Src", "Deep"], () => Promise.resolve(null))).toBeNull();
  });
});
