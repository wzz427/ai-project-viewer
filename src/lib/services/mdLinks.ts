/**
 * Markdown link/image href → canonical project-relative path (spec-018).
 *
 * markdown-it writes hrefs VERBATIM: `../x.md`, `./x.md`, `docs//x.md`,
 * `%20`, `#anchors`, `?query` and leading `/` all arrive raw. Joining them
 * naively used to produce dirty rels like `docs/../.agents/s/x.md`, which
 * broke tree reveal (the walk meets a `..` segment no node answers to),
 * leaked into Copy Absolute Path verbatim, and opened duplicate tabs for
 * the same file (tab dedup keys on the exact rel string).
 *
 * This module is the ONE place that turns a raw href into the same shape
 * the tree produces via joinRel. Returns null when the link escapes the
 * project root (caller toasts — spec-018 D3) or carries no path at all.
 *
 * Decisions (owner confirmed 2026-11-05, spec-018 §四):
 * - leading `/` reads as PROJECT-ROOT-relative (VS Code parity; D2);
 * - `?query` is stripped: `?` cannot occur in an NTFS name, so it can only
 *   be a web-ism riding along in the href;
 * - both `/` and `\` are separators: neither can occur inside a Windows
 *   file name, so splitting on both is unambiguous.
 */

export function resolveDocLink(docRel: string, href: string): string | null {
  // Fragment/query address a section inside the target, never the file
  // name itself.
  const cleaned = href.split("#")[0]!.split("?")[0]!;
  if (!cleaned) return null; // pure anchor (`#section`) — nothing to open
  let decoded: string;
  try {
    // markdown-it percent-encodes (space→%20, literal %→%25), so decoding
    // round-trips to the on-disk name.
    decoded = decodeURIComponent(cleaned);
  } catch {
    decoded = cleaned; // malformed % sequence: keep the raw text
  }
  // Root-relative links ignore the document's folder entirely (D2).
  const stack: string[] = [];
  if (!/^[\\/]/.test(decoded)) {
    const docDir = docRel.includes("/")
      ? docRel.slice(0, docRel.lastIndexOf("/"))
      : "";
    if (docDir) stack.push(...docDir.split("/"));
  }
  for (const seg of decoded.split(/[\\/]/)) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") {
      if (stack.length === 0) return null; // escapes the project root (D3)
      stack.pop();
    } else {
      stack.push(seg);
    }
  }
  return stack.length > 0 ? stack.join("/") : null;
}
