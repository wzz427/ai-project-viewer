import { describe, expect, it } from "vitest";
import { menuKindOf, SCRIPT_RUNNABLE } from "$lib/services/menuKind";

describe("menuKindOf (V1.5 §142 menu slice, spec-008)", () => {
  it("routes the three runnable script extensions to 'script'", () => {
    expect(menuKindOf("start.ps1", false)).toBe("script");
    expect(menuKindOf("build.cmd", false)).toBe("script");
    expect(menuKindOf("run.bat", false)).toBe("script");
    expect([...SCRIPT_RUNNABLE].sort()).toEqual(["bat", "cmd", "ps1"]);
  });

  it("keeps py/js/sh off the run list (§127)", () => {
    expect(menuKindOf("main.py", false)).toBe("textLike");
    expect(menuKindOf("app.js", false)).toBe("textLike");
    expect(menuKindOf("deploy.sh", false)).toBe("textLike");
  });

  it("splits exe from msi (§139 Run vs §126 System Default only)", () => {
    expect(menuKindOf("tool.exe", false)).toBe("exe");
    expect(menuKindOf("setup.msi", false)).toBe("msi");
  });

  it("extension match is case-insensitive", () => {
    expect(menuKindOf("TOOL.EXE", false)).toBe("exe");
    expect(menuKindOf("Start.PS1", false)).toBe("script");
  });

  it("folders and browser text keep their kinds", () => {
    expect(menuKindOf("anything", true)).toBe("folder");
    expect(menuKindOf("index.html", false)).toBe("browserText");
    expect(menuKindOf("link.url", false)).toBe("browserText");
  });
});
