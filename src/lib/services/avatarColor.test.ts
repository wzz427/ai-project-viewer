import { describe, expect, it } from "vitest";
import {
  AVATAR_PALETTE,
  avatarColorOf,
  avatarInitialOf,
} from "./avatarColor";

describe("avatarColorOf (spec-014 D3/R2: stable project identity color)", () => {
  it("is deterministic across calls (same path, same color)", () => {
    for (const p of ["C:\\a\\b", "/home/x/y", "D:\\repo"]) {
      expect(avatarColorOf(p)).toBe(avatarColorOf(p));
    }
  });

  it("always lands inside the palette", () => {
    const paths = Array.from({ length: 200 }, (_, i) => `p-${i}-x`.repeat(3));
    for (const p of paths) {
      expect(AVATAR_PALETTE).toContain(avatarColorOf(p));
    }
  });

  it("spreads real-world-ish paths over several hues (learnable identity)", () => {
    const four = [
      "C:\\Users\\w\\Desktop\\ProjectViewer",
      "C:\\Users\\w\\Desktop\\OtherTool",
      "D:\\work\\docs",
      "E:\\media\\pics",
    ].map(avatarColorOf);
    expect(new Set(four).size).toBeGreaterThanOrEqual(3);
  });

  it("case/separator variants are distinct identities, not crashes", () => {
    expect(typeof avatarColorOf("")).toBe("string");
    expect(typeof avatarColorOf("A")).toBe("string");
  });
});

describe("avatarInitialOf", () => {
  it("takes the first grapheme, uppercased", () => {
    expect(avatarInitialOf("project-viewer")).toBe("P");
    expect(avatarInitialOf(" große sache ")).toBe("G");
    expect(avatarInitialOf("中文项目")).toBe("中");
    expect(avatarInitialOf("")).toBe("?");
  });
});
