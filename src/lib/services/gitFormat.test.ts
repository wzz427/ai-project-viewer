import { describe, expect, it } from "vitest";
import {
  badgeText,
  marksByRel,
  relativeTime,
} from "$lib/services/gitFormat";
import type { GitSnapshot } from "$lib/services/tauri";

describe("badgeText (§9)", () => {
  it("hides at 0, shows real 1–99, clamps at 99+", () => {
    expect(badgeText(0)).toBeNull();
    expect(badgeText(1)).toBe("1");
    expect(badgeText(7)).toBe("7");
    expect(badgeText(99)).toBe("99");
    expect(badgeText(100)).toBe("99+");
    expect(badgeText(12345)).toBe("99+");
  });
});

describe("relativeTime (§54)", () => {
  const now = Date.UTC(2026, 9, 10, 12, 0, 0);
  const h = 3600_000;
  it("steps through the compact tiers", () => {
    expect(relativeTime(now, now - 5_000)).toBe("just now");
    expect(relativeTime(now, now - 5 * 60_000)).toBe("5m ago");
    expect(relativeTime(now, now - 2 * h)).toBe("2h ago");
    expect(relativeTime(now, now - 24 * h)).toBe("yesterday");
    expect(relativeTime(now, now - 3 * 24 * h)).toBe("3d ago");
    expect(relativeTime(now, now - 20 * 24 * h)).toBe("2w ago");
    expect(relativeTime(now, now - 100 * 24 * h)).toBe("3mo ago");
    expect(relativeTime(now, now - 400 * 24 * h)).toBe("1y ago");
  });
  it("never renders a negative interval", () => {
    expect(relativeTime(now, now + 60_000)).toBe("just now");
  });
});

describe("marksByRel (§46/D4)", () => {
  const snap: GitSnapshot = {
    status: "ok",
    changes: [
      { rel: "a.ts", letter: "M" },
      { rel: "notes.md", letter: "?" },
    ],
    staged: [
      { rel: "b.ts", letter: "A" },
      { rel: "a.ts", letter: "M" },
    ],
    uniqueCount: 3,
    commits: [],
    refreshedAt: 0,
  };
  it("maps every scoped file to its letter", () => {
    const m = marksByRel(snap);
    expect(m.get("a.ts")).toBe("M");
    expect(m.get("notes.md")).toBe("?");
    expect(m.get("b.ts")).toBe("A");
    expect(m.has("missing.ts")).toBe(false);
  });
  it("staged letter wins when a file sits in both groups (D4)", () => {
    const both: GitSnapshot = {
      ...snap,
      changes: [{ rel: "cfg.yaml", letter: "M" }],
      staged: [{ rel: "cfg.yaml", letter: "A" }],
    };
    expect(marksByRel(both).get("cfg.yaml")).toBe("A");
  });
  it("returns an empty map for non-ok snapshots", () => {
    const ng: GitSnapshot = {
      ...snap,
      status: "nonGit",
      changes: [],
      staged: [],
    };
    expect(marksByRel(ng).size).toBe(0);
  });
});
