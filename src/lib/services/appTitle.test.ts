import { describe, expect, it } from "vitest";
import { titleWithVersion } from "./appTitle";

// spec-023 V2: the three title states — normal append, and both degrade
// branches that must NOT leave a dangling suffix (blank and the app_version
// command's "unknown" fallback).
describe("titleWithVersion (spec-023)", () => {
  it("appends a normal version with one space", () => {
    expect(titleWithVersion("AI Project Viewer", "0.8.34")).toBe(
      "AI Project Viewer 0.8.34",
    );
  });

  it("degrades to the bare name on blank/whitespace version", () => {
    expect(titleWithVersion("AI Project Viewer", "")).toBe("AI Project Viewer");
    expect(titleWithVersion("AI Project Viewer", "   ")).toBe(
      "AI Project Viewer",
    );
  });

  it("degrades to the bare name on the unknown fallback", () => {
    expect(titleWithVersion("AI Project Viewer", "unknown")).toBe(
      "AI Project Viewer",
    );
  });
});
