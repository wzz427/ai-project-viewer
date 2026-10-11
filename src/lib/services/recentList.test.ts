import { describe, expect, it } from "vitest";
import {
  insertRecent,
  recentName,
  recentParent,
  RECENT_CAP,
} from "$lib/services/recentList";

describe("insertRecent (V1.5 §198-a)", () => {
  it("puts a new folder at the front", () => {
    expect(insertRecent(["B", "A"], "C")).toEqual(["C", "B", "A"]);
  });

  it("re-opening an existing folder moves it to the front without duplicating", () => {
    expect(insertRecent(["C", "B", "A"], "B")).toEqual(["B", "C", "A"]);
  });

  it("evicts the oldest beyond the cap", () => {
    // Front = newest: p0 newest … p9 oldest.
    const ten = Array.from({ length: RECENT_CAP }, (_, i) => `p${i}`);
    const next = insertRecent(ten, "new");
    expect(next).toHaveLength(RECENT_CAP);
    expect(next[0]).toBe("new");
    expect(next).not.toContain("p9"); // oldest evicted
    expect(next).toContain("p0"); // rest survive
  });

  it("does not evict when re-opening the newest of a full list", () => {
    const ten = Array.from({ length: RECENT_CAP }, (_, i) => `p${i}`);
    const next = insertRecent(ten, "p0"); // already the newest
    expect(next).toEqual(ten);
  });

  it("handles an empty list", () => {
    expect(insertRecent([], "A")).toEqual(["A"]);
  });
});

describe("recentName / recentParent", () => {
  it("splits folder name from parent path", () => {
    expect(recentName("D:\\proj\\VibeCoding\\ProjectViewer")).toBe("ProjectViewer");
    expect(recentParent("D:\\proj\\VibeCoding\\ProjectViewer")).toBe(
      "D:\\proj\\VibeCoding",
    );
  });

  it("tolerates trailing separators (resolve output never has them)", () => {
    expect(recentName("C:\\a\\b\\")).toBe("b");
    expect(recentParent("C:\\a\\b\\")).toBe("C:\\a");
  });

  it("falls back to the whole path when no separator remains", () => {
    expect(recentName("folder")).toBe("folder");
    expect(recentParent("folder")).toBe("folder");
  });
});
