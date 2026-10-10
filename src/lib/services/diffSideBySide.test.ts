import { describe, expect, it } from "vitest";
import {
  diffPathOf,
  parseUnifiedDiff,
  type DiffSegment,
} from "$lib/services/diffSideBySide";

function rowsOf(seg: DiffSegment) {
  if (seg.type !== "rows") throw new Error("expected rows segment");
  return seg.rows;
}

const SAMPLE = `diff --git a/a.ts b/a.ts
index 9d..e1 100644
--- a/a.ts
+++ b/a.ts
@@ -1,4 +1,4 @@
 one
-two
+TWO
 three
 four
@@ -10,3 +10,5 @@
 ten
 eleven
+twelve
+thirteen
 fourteen`;

describe("parseUnifiedDiff", () => {
  const segs = parseUnifiedDiff(SAMPLE);

  it("no leading gap when the first hunk starts at line 1", () => {
    expect(segs[0].type).toBe("rows");
  });

  it("first hunk: context + one modified pair with both line numbers", () => {
    const rows = rowsOf(segs[0]);
    expect(rows[0]).toMatchObject({ left: "one", right: "one", leftNo: 1, rightNo: 1, kind: "ctx" });
    expect(rows[1]).toMatchObject({ left: "two", right: "TWO", leftNo: 2, rightNo: 2, kind: "mod" });
    expect(rows[2]).toMatchObject({ left: "three", right: "three", kind: "ctx" });
  });

  it("folds the region between hunks and keeps hunk context text", () => {
    const gap = segs.find((s) => s.type === "gap") as Extract<(typeof segs)[number], { type: "gap" }>;
    // lines 5..9 unchanged → 5 folded lines before the @@ -10,3 hunk
    expect(gap).toMatchObject({ type: "gap", count: 5 });
  });

  it("pure additions render with null left and shifted right numbers", () => {
    const last = segs[segs.length - 1];
    expect(rowsOf(last).map((r) => r.kind)).toEqual(["ctx", "ctx", "add", "add", "ctx"]);
    expect(rowsOf(last)[2]).toMatchObject({ left: null, right: "twelve", leftNo: null, rightNo: 12 });
    expect(rowsOf(last)[4]).toMatchObject({ leftNo: 12, rightNo: 14 });
  });
});

describe("parseUnifiedDiff deletions and empty sides", () => {
  it("pure deletions have null right side", () => {
    const segs = parseUnifiedDiff(
      "@@ -1,2 +1,1 @@\n keep\n-gone\n-was here",
    );
    const rows = rowsOf(segs[0]);
    expect(rows[1]).toMatchObject({ left: "gone", right: null, kind: "del", rightNo: null });
    expect(rows[2]).toMatchObject({ left: "was here", kind: "del" });
  });

  it("new-file diff starts with no gap and no old numbers", () => {
    const segs = parseUnifiedDiff(
      "diff --git a/new.ts b/new.ts\nnew file mode 100644\n--- /dev/null\n+++ b/new.ts\n@@ -0,0 +1,2 @@\n+hello\n+world",
    );
    expect(segs).toHaveLength(1);
    const rows = rowsOf(segs[0]);
    expect(rows.map((r) => r.kind)).toEqual(["add", "add"]);
    expect(rows[0].leftNo).toBeNull();
    expect(rows[0].rightNo).toBe(1);
  });

  it("del+add runs longer than each other zip with nulls", () => {
    const segs = parseUnifiedDiff(
      "@@ -1,3 +1,2 @@\n-a\n-b\n-c\n+x\n+y",
    );
    const rows = rowsOf(segs[0]);
    expect(rows.map((r) => r.kind)).toEqual(["mod", "mod", "del"]);
    expect(rows[2]).toMatchObject({ left: "c", right: null });
  });
});

describe("diffPathOf", () => {
  it("extracts old and new paths, handling /dev/null and a/b prefixes", () => {
    expect(diffPathOf("--- a/src/x.ts\n+++ b/src/x.ts", "old")).toBe("src/x.ts");
    expect(diffPathOf("--- /dev/null\n+++ b/new.ts", "old")).toBeNull();
    expect(diffPathOf("--- /dev/null\n+++ b/new.ts", "new")).toBe("new.ts");
  });
});
