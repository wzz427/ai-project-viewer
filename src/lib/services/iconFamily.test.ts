import { describe, expect, it } from "vitest";
import { iconFamilyOf } from "./viewerType";

// spec-014 D4/R4: the icon family must ride the SAME routing that picks
// the viewer — the icon previews the click.
describe("iconFamilyOf (viewer-routing-sourced icon family)", () => {
  const cases: Array<[string, ReturnType<typeof iconFamilyOf>]> = [
    ["README.md", "markdown"],
    ["docs/guide.markdown", "markdown"],
    ["paper.pdf", "pdf"],
    ["main.ts", "code"],
    ["src/lib/app.rs", "code"],
    ["package.json", "json"],
    ["tsconfig.json", "json"],
    ["logo.png", "image"],
    ["icon.svg", "image"],
    ["Notes.txt", "file"],
    ["run.bat", "code"],
    ["sample.csv", "file"],
    ["no-extension", "file"],
    ["app.exe", "file"],
    // 0.8.10: media hands off to the OS player — film icon, never the
    // text fallback that a viewer-less extension used to draw.
    ["demo.mp4", "media"],
    ["clip.MKV", "media"],
    ["song.mp3", "media"],
    ["podcast.m4a", "media"],
  ];
  it.each(cases)("%s -> %s", (name, expected) => {
    expect(iconFamilyOf(name)).toBe(expected);
  });

  it("agrees with the viewer that actually opens (spot-check routing table)", () => {
    // Anything routed to a dedicated viewer must show that family, and
    // anything text/executable/binary falls to the generic file.
    expect(iconFamilyOf("x.md")).not.toBe("file");
    expect(iconFamilyOf("x.json")).not.toBe("file");
    expect(iconFamilyOf("x.py")).not.toBe("file");
    expect(iconFamilyOf("setup.exe")).toBe("file");
  });
});
