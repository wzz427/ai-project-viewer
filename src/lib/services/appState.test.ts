import { describe, expect, it } from "vitest";
import {
  buildAppState,
  parseAppState,
  STATE_VERSION,
  type BuildInput,
} from "$lib/services/appState";

function sampleInput(): BuildInput {
  return {
    projects: [
      {
        id: "p1",
        name: "Alpha",
        rootPath: "D:\\proj\\alpha",
        sidebarMode: "git",
        sidebarWidth: 260,
        trustedForExecution: false,
      },
    ],
    activeProjectId: "p1",
    trees: {
      "D:\\proj\\alpha": {
        expandedFolders: ["src", "src/components"],
        pinnedItems: { ".": ["README.md", "src"] },
        foldersFirst: false,
      },
    },
    tabs: {
      "D:\\proj\\alpha": {
        openFiles: [
          {
            relativePath: "README.md",
            viewerType: "markdown",
            markdownMode: "source",
            scrollPosition: 420,
          },
          {
            relativePath: "src/main.ts",
            viewerType: "code",
            pinned: true,
            deleted: true,
          },
          {
            relativePath: "docs/report.pdf",
            viewerType: "pdf",
            pdfState: { page: 7, zoom: 1.63, zoomMode: "fit-width", scrollPosition: 4800 },
          },
        ],
        activeFileRelativePath: "README.md",
      },
    },
    settings: {
      theme: "dark",
      viewer: { fontSize: 15 },
      fileTree: { showSystemGeneratedFolders: true },
      external: { vsCodeNewWindow: true },
    },
    recentFolders: [],
  };
}

describe("buildAppState", () => {
  it("keeps project-relative identities (V1.5 §18/§19)", () => {
    const state = buildAppState(sampleInput());
    const p = state.projects[0];
    expect(p.expandedFolders).toEqual(["src", "src/components"]);
    expect(Object.keys(p.fileTreePreferences.pinnedItems)).toEqual(["."]);
    expect(p.fileTreePreferences.pinnedItems["."]).toEqual(["README.md", "src"]);
    // The only absolute path is the project identity itself.
    const json = JSON.stringify(state);
    expect(json).toContain("D:\\\\proj\\\\alpha");
    expect(json).not.toContain("D:\\\\proj\\\\alpha\\\\src");
  });

  it("whitelists FileTabState — runtime fields never persist", () => {
    const state = buildAppState(sampleInput());
    const tabJsons = state.projects[0].openFiles.map((t) => JSON.stringify(t));
    for (const j of tabJsons) {
      expect(j).not.toContain("deleted");
      expect(j).not.toContain("encoding");
      expect(j).not.toContain("sizeBytes");
      expect(j).not.toContain("unsupportedReason");
    }
    expect(state.projects[0].openFiles[0].markdownMode).toBe("source");
    expect(state.projects[0].openFiles[1].pinned).toBe(true);
  });

  it("copies containers so later store mutations cannot leak in", () => {
    const input = sampleInput();
    const state = buildAppState(input);
    input.trees["D:\\proj\\alpha"].expandedFolders.push("docs");
    input.trees["D:\\proj\\alpha"].pinnedItems["."].push("leak.md");
    expect(state.projects[0].expandedFolders).toEqual(["src", "src/components"]);
    expect(state.projects[0].fileTreePreferences.pinnedItems["."]).toEqual([
      "README.md",
      "src",
    ]);
  });

  it("omits activeProjectId when none is active", () => {
    const input = sampleInput();
    input.activeProjectId = null;
    expect(buildAppState(input).activeProjectId).toBeUndefined();
  });

  it("persists per-project execution trust and round-trips it (§129)", () => {
    const input = sampleInput();
    input.projects[0].trustedForExecution = true;
    const state = buildAppState(input);
    expect(state.projects[0].trustedForExecution).toBe(true);
    const parsed = parseAppState(JSON.stringify(state));
    expect(parsed!.projects[0].trustedForExecution).toBe(true);
  });

  it("writes recentFolders only when non-empty (§198, spec-010 D5)", () => {
    const empty = buildAppState(sampleInput());
    expect(empty.recentFolders).toBeUndefined();

    const input = sampleInput();
    input.recentFolders = ["D:\\a", "D:\\b"];
    const state = buildAppState(input);
    expect(state.recentFolders).toEqual(["D:\\a", "D:\\b"]);
    const parsed = parseAppState(JSON.stringify(state));
    expect(parsed!.recentFolders).toEqual(["D:\\a", "D:\\b"]);
  });
});

describe("parseAppState", () => {
  it("round-trips a built state", () => {
    const state = buildAppState(sampleInput());
    const parsed = parseAppState(JSON.stringify(state));
    expect(parsed).toEqual(state);
  });

  it("rejects non-JSON and wrong versions", () => {
    expect(parseAppState("{nope")).toBeNull();
    expect(parseAppState('{"version":99}')).toBeNull();
    expect(parseAppState('{"projects":[]}')).toBeNull();
  });

  it("heals malformed pieces instead of failing the whole load", () => {
    const parsed = parseAppState(
      JSON.stringify({
        version: STATE_VERSION,
        projects: [
          {
            id: "p1",
            rootPath: "D:\\x",
            sidebarMode: "bogus",
            sidebarWidth: 99999,
            expandedFolders: ["src", 42, null],
            openFiles: [
              { relativePath: "a.md", viewerType: "markdown" },
              { relativePath: "b.md", viewerType: "hologram" },
              { viewerType: "markdown" },
            ],
            fileTreePreferences: {
              foldersFirst: "yes please",
              pinnedItems: { ".": ["ok.md", 7] },
            },
          },
          { id: "", rootPath: "" },
        ],
        settings: {},
      }),
    );
    expect(parsed).not.toBeNull();
    expect(parsed!.projects).toHaveLength(1);
    const p = parsed!.projects[0];
    expect(p.sidebarMode).toBe("files");
    expect(p.sidebarWidth).toBe(600);
    expect(p.expandedFolders).toEqual(["src"]);
    expect(p.openFiles).toHaveLength(1);
    expect(p.openFiles[0].relativePath).toBe("a.md");
    expect(p.fileTreePreferences.foldersFirst).toBe(true);
    // pre-Phase-8 state files carry no trust field — heals to untrusted (§128)
    expect(p.trustedForExecution).toBe(false);
    expect(p.fileTreePreferences.pinnedItems["."]).toEqual(["ok.md"]);
    expect(parsed!.settings).toEqual({
      theme: "system",
      viewer: { fontSize: 13 },
      fileTree: { showSystemGeneratedFolders: false },
      // Absent in older state files → §134 default (New Window).
      external: { vsCodeNewWindow: true },
    });
  });

  it("clamps viewer font size into the UI range", () => {
    const parsed = parseAppState(
      JSON.stringify({
        version: STATE_VERSION,
        projects: [],
        settings: { viewer: { fontSize: 99 } },
      }),
    );
    expect(parsed!.settings.viewer.fontSize).toBe(20);
  });

  it("heals recentFolders: drops non-strings, caps at 10, absent stays absent (§198)", () => {
    const twelve = Array.from({ length: 12 }, (_, i) => `D:\\p${i}`);
    const parsed = parseAppState(
      JSON.stringify({
        version: STATE_VERSION,
        projects: [],
        settings: {},
        recentFolders: [...twelve, 42, null],
      }),
    );
    expect(parsed!.recentFolders).toEqual(twelve.slice(0, 10));

    // Pre-spec-010 state files carry no field at all — heals to absent.
    const old = parseAppState(
      JSON.stringify({ version: STATE_VERSION, projects: [], settings: {} }),
    );
    expect(old!.recentFolders).toBeUndefined();
  });

  it("persists and heals pdfState (spec-005 D6)", () => {
    const state = buildAppState(sampleInput());
    const pdfTab = state.projects[0].openFiles.find(
      (t) => t.viewerType === "pdf",
    );
    expect(pdfTab?.pdfState).toEqual({
      page: 7,
      zoom: 1.63,
      zoomMode: "fit-width",
      scrollPosition: 4800,
    });

    const healed = parseAppState(
      JSON.stringify({
        version: STATE_VERSION,
        projects: [
          {
            id: "p1",
            rootPath: "D:\\x",
            openFiles: [
              {
                relativePath: "a.pdf",
                viewerType: "pdf",
                pdfState: { page: 0, zoom: 99, zoomMode: "bogus" },
              },
            ],
          },
        ],
      }),
    );
    expect(healed!.projects[0].openFiles[0].pdfState).toEqual({
      page: 1,
      zoom: 5,
    });
  });
});
