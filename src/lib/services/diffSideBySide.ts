/**
 * Unified-diff → side-by-side segments (spec-007 rework round 1, owner
 * 2026-10-10: diffs must show side-by-side like VS Code — V1.5 §71's P1
 * deferral was pulled forward by his review). Pure so vitest can drive it.
 *
 * The hunk headers of a unified diff already ARE the folding information:
 * everything between hunks is unchanged and gets folded into a `gap` bar
 * ("⋯ N unchanged lines"), hunk interiors become paired rows. Consecutive
 * del+add runs are zipped row-by-row so a modified line reads as old|new
 * on one row, like VS Code's aligned pairs.
 */

export interface DiffRow {
  left: string | null;
  right: string | null;
  leftNo: number | null;
  rightNo: number | null;
  kind: "ctx" | "del" | "add" | "mod";
}

export type DiffSegment =
  | { type: "gap"; count: number; context?: string }
  | { type: "rows"; rows: DiffRow[] };

interface PendingLine {
  text: string;
  no: number;
}

const HUNK_RE = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$/;

/** Split "the file" out of a diff path header ("a/src/x.ts" → "src/x.ts"). */
export function diffPathOf(text: string, side: "old" | "new"): string | null {
  const prefix = side === "old" ? "--- " : "+++ ";
  for (const line of text.split("\n")) {
    if (line.startsWith(prefix)) {
      let p = line.slice(prefix.length).trim();
      if (p === "/dev/null") return null;
      // timestamps after a tab, and the a/ b/ prefixes
      p = p.split("\t")[0];
      if (p.length > 2 && (p.startsWith("a/") || p.startsWith("b/"))) {
        p = p.slice(2);
      }
      return p;
    }
  }
  return null;
}

export function parseUnifiedDiff(text: string): DiffSegment[] {
  const segments: DiffSegment[] = [];
  let rows: DiffRow[] = [];
  let dels: PendingLine[] = [];
  let adds: PendingLine[] = [];
  let curOld = 0;
  let curNew = 0;

  const flushPairs = () => {
    // Zip the pending del/add runs pairwise (VS Code alignment): a deleted
    // line and the added line below it share one row.
    const n = Math.max(dels.length, adds.length);
    for (let i = 0; i < n; i++) {
      const d = dels[i];
      const a = adds[i];
      rows.push({
        left: d ? d.text : null,
        right: a ? a.text : null,
        leftNo: d ? d.no : null,
        rightNo: a ? a.no : null,
        kind: d && a ? "mod" : d ? "del" : "add",
      });
    }
    dels = [];
    adds = [];
  };

  const flushRows = () => {
    flushPairs();
    if (rows.length) {
      segments.push({ type: "rows", rows });
      rows = [];
    }
  };

  for (const line of text.split("\n")) {
    const hunk = HUNK_RE.exec(line);
    if (hunk) {
      const startOld = parseInt(hunk[1], 10);
      const startNew = parseInt(hunk[3], 10);
      const gap = curOld === 0 ? startOld - 1 : startOld - curOld - 1;
      flushRows();
      if (gap > 0) {
        segments.push({
          type: "gap",
          count: gap,
          context: hunk[5]?.trim() || undefined,
        });
      }
      curOld = startOld > 0 ? startOld - 1 : 0;
      curNew = startNew > 0 ? startNew - 1 : 0;
      continue;
    }
    if (line.startsWith("diff ") || line.startsWith("index ")) continue;
    if (line.startsWith("--- ") || line.startsWith("+++ ")) continue;
    if (line.startsWith("new file mode") || line.startsWith("deleted file mode")) continue;
    if (line.startsWith("old mode") || line.startsWith("new mode")
      || line.startsWith("similarity index") || line.startsWith("rename from")
      || line.startsWith("rename to") || line.startsWith("Binary files")
      || line.startsWith("GIT binary patch")) {
      continue;
    }
    if (line.startsWith("+")) {
      adds.push({ text: line.slice(1), no: ++curNew });
    } else if (line.startsWith("-")) {
      dels.push({ text: line.slice(1), no: ++curOld });
    } else if (line.startsWith(" ")) {
      flushPairs();
      rows.push({
        left: line.slice(1),
        right: line.slice(1),
        leftNo: ++curOld,
        rightNo: ++curNew,
        kind: "ctx",
      });
    } else if (line.startsWith("\\ No newline")) {
      // Marker for the previous line; rendering ignores it (V1).
    }
    // Empty trailing line / anything else: ignore.
  }
  flushRows();
  return segments;
}
