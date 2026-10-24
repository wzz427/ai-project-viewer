# -*- coding: utf-8 -*-
"""spec-005 spike + functional regression (zero foreground, testing.md §1).

Validates the §97 chain (load -> worker -> render first page), the §92
toolbar, virtualized rendering (§95), release-on-switch (§96), and state
restore (§93) over CDP. RAM numbers come separately (block 5).

Run: conda pywork python %TEMP%\\aiv-p5-pdf-test.py
"""
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = Path = None
import pathlib
# release since 0.8.9: same binary phase3 drives — a debug-only EXE here
# silently tested a stale/unbuilt flavor.
EXE = pathlib.Path(r"C:\Users\wzzpk\Desktop\PyProjects\VibeCoding\ProjectViewer\src-tauri\target\release\ai-project-viewer.exe")
PROJECT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "AIV-TestProject")  # in-repo fixture (owner 2026-10-24)
STATE = os.path.expandvars(r"%TEMP%\aiv-p5-test-state.json")
CDP = 9225
DEBUG = os.path.expandvars(r"%TEMP%\aiv-p4-debug.log")

PASS, FAIL = [], []
CONSOLE = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


def kill_all():
    # Owner isolation (aivlaunch): stragglers from THIS repo's build tree
    # only — the experience client shares the exe name and must never be
    # matched. The old webview-by-commandline sweep is gone with it.
    aivlaunch.kill_strays()


def launch():
    return aivlaunch.launch(str(EXE), PROJECT, STATE, CDP,
                            stdout=open(DEBUG, "ab"))


def connect(pw):
    for _ in range(60):
        try:
            return pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("CDP never came up")


def tree_click(pg, name):
    pg.wait_for_selector(f"div.row[role='treeitem'] :text-is('{name}')", timeout=10000)
    pg.click(f"div.row[role='treeitem'] :text-is('{name}')")


def canvases(pg):
    return pg.locator(".pdf-viewer canvas").count()


def main():
    if os.path.exists(STATE):
        os.remove(STATE)

    with sync_playwright() as pw:
        proc = launch()
        browser = connect(pw)
        pg = browser.contexts[0].pages[0]
        pg.on("console", lambda m: CONSOLE.append(f"{m.type}: {m.text}"))
        pg.on("pageerror", lambda e: CONSOLE.append(f"PAGEERROR: {e}"))
        pg.wait_for_selector(".file-tree", timeout=20000)

        # --- §97: load -> worker -> render one page ---
        tree_click(pg, "pdf")  # expand the pdf folder
        pg.wait_for_timeout(300)
        tree_click(pg, "sample-10p-text.pdf")
        pg.wait_for_selector(".pdf-viewer canvas", timeout=20000)
        check("PDF tab opens and renders first page", canvases(pg) >= 1)
        check("total pages shown", pg.locator(".toolbar").inner_text().find("/ 10") != -1,
              pg.locator(".toolbar").inner_text())

        no_fake_worker = not any("fake worker" in c.lower() for c in CONSOLE)
        check("real worker thread (no fake-worker fallback)", no_fake_worker,
              "\n".join(CONSOLE[-5:]))

        # --- §92 toolbar ---
        pg.click("button[aria-label='Next page']")
        pg.wait_for_timeout(400)
        check("next page -> current 2", pg.locator("input.page-no").input_value() == "2",
              pg.locator("input.page-no").input_value())
        pg.click("button[aria-label='Previous page']")
        pg.wait_for_timeout(300)

        pg.fill("input.page-no", "7")
        pg.press("input.page-no", "Enter")
        pg.wait_for_timeout(400)
        check("page jump -> 7", pg.locator("input.page-no").input_value() == "7")

        zoom_before = pg.locator(".toolbar .mono").inner_text()
        pg.click("button[aria-label='Zoom in']")
        pg.wait_for_timeout(400)
        zoom_after = pg.locator(".toolbar .mono").inner_text()
        check("zoom in changes percent", zoom_before != zoom_after, f"{zoom_before} -> {zoom_after}")
        check("custom zoom label off fit modes",
              pg.locator("button.tb.on").count() == 0)

        pg.click("button:has-text('Fit Page')")
        pg.wait_for_timeout(400)
        check("fit page engaged", pg.locator("button:has-text('Fit Page').on").count() == 1)
        pg.click("button:has-text('Fit Width')")
        pg.wait_for_timeout(400)
        check("fit width engaged", pg.locator("button:has-text('Fit Width').on").count() == 1)

        # Ctrl+wheel over the scroller.
        box = pg.locator(".pdf-viewer .scroller").bounding_box()
        pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        pg.keyboard.down("Control")
        pg.mouse.wheel(0, -240)
        pg.keyboard.up("Control")
        pg.wait_for_timeout(500)
        check("ctrl+wheel switches to custom zoom",
              pg.locator("button.tb.on").count() == 0)

        # --- search (0.8.9: character-level highlights) ---
        pg.fill("input.search", "Page 8 line")
        pg.press("input.search", "Enter")
        try:
            pg.wait_for_selector(".toolbar:has-text('1 /')", timeout=15000)
            check("search finds matches", True)
            check("search jumped to page 8",
                  pg.locator("input.page-no").input_value() == "8",
                  pg.locator("input.page-no").input_value())
            # Owner 2026-10-18: found words must be visibly marked. Marks
            # must exist, carry a real background (invisible-highlight
            # regressions are a color bug, not an absence bug — 0.8.3
            # lesson), exactly one is .current, and — since every
            # occurrence of this query lives on rendered page 8 — the
            # counter total must EQUAL the box count (the counter counts
            # occurrences, not pages).
            hl_n = pg.locator("mark.pdf-find-hl").count()
            cur_n = pg.locator("mark.pdf-find-hl.current").count()
            bg = pg.evaluate("""() => {
                const m = document.querySelector('mark.pdf-find-hl');
                return m ? getComputedStyle(m).backgroundColor : null;
            }""")
            counter = pg.locator(".toolbar").inner_text()
            import re as _re
            m_total = _re.search(r"1 / (\d+)", counter)
            total = int(m_total.group(1)) if m_total else -1
            check("pdf_search_highlights_words",
                  hl_n >= 1 and cur_n == 1
                  and bool(bg) and bg not in ("rgba(0, 0, 0, 0)", "transparent")
                  and total == hl_n,
                  f"marks={hl_n} current={cur_n} bg={bg} total={total}")
        except Exception as e:
            check("search finds matches", False, str(e))

        # Clearing the box must drop marks AND counter together — a stale
        # "1/7" beside an empty input read as a stuck search (owner
        # 2026-10-18, same report).
        pg.fill("input.search", "")
        pg.wait_for_timeout(300)
        check("pdf_search_clear_drops_marks_and_counter",
              pg.locator("mark.pdf-find-hl").count() == 0
              and pg.locator(".toolbar:has-text('1 /')").count() == 0,
              f"marks={pg.locator('mark.pdf-find-hl').count()}")

        pg.fill("input.search", "zzzz-not-there")
        pg.press("input.search", "Enter")
        pg.wait_for_timeout(1500)
        check("no-result feedback", pg.locator(".toolbar").inner_text().find("0 results") != -1)

        # --- 0.8.9 selection guards (owner 2026-10-18 double report on a
        # real arXiv-style doc): (a) the rotated left spine + author
        # whitespace band must not defeat the row clamp — dragging UP
        # through the band extends line by line instead of freezing/
        # ballooning into select-everything; (b) the selection tint must
        # be TRANSLUCENT — an opaque editor-sel paints over the canvas
        # glyphs it marks (0.8.1 theme-pack regression, "把文字全遮了"). ---
        pg.click("div.row[role='treeitem'] :text-is('sample-spine.pdf')")
        pg.wait_for_selector(".pdf-viewer canvas", timeout=20000)
        pg.wait_for_timeout(1800)

        def drag_pts(points):
            pg.evaluate(r"""(pts) => {
              const [d0, ...rest] = pts;
              const target = document.elementFromPoint(d0[0], d0[1]) || document.body;
              target.dispatchEvent(new MouseEvent('mousedown', {
                clientX: d0[0], clientY: d0[1], bubbles: true, button: 0, detail: 1}));
              for (const [x, y] of rest) {
                window.dispatchEvent(new PointerEvent('pointermove', {
                  clientX: x, clientY: y, bubbles: true, button: 0, buttons: 1}));
              }
              const last = pts[pts.length - 1];
              window.dispatchEvent(new PointerEvent('pointerup', {
                clientX: last[0], clientY: last[1], bubbles: true, button: 0}));
            }""", [[int(x), int(y)] for x, y in points])

        lines = pg.evaluate(r"""() => {
          const rows = [];
          for (const s of document.querySelectorAll('.pdf-text-layer span')) {
            const r = s.getBoundingClientRect();
            if (r.width === 0 || r.height > r.width) continue;
            const t = s.textContent || '';
            if (t.includes('Bottom line 1:') || t.includes('Top line 8:')) {
              rows.push({ tag: t.includes('Bottom') ? 'bottom' : 'top',
                          cx: r.left + r.width / 2, cy: r.top + r.height / 2 });
            }
          }
          return rows;
        }""")
        bl = next(r for r in lines if r["tag"] == "bottom")
        tp = next(r for r in lines if r["tag"] == "top")
        drag_pts([(bl["cx"], bl["cy"]),
                  (bl["cx"], (bl["cy"] + tp["cy"]) / 2),
                  (tp["cx"], tp["cy"])])
        pg.wait_for_timeout(300)
        sel_txt = pg.evaluate("window.getSelection().toString()")
        # Extent lands MID-line (the drag target is the line's center), so
        # assert on line CONTENT, not the line prefixes.
        check("pdf_spine_drag_up_clamps_lines",
              "fox jumps over the lazy dog" in sel_txt
              and "Bottom line 1" in sel_txt
              and len(sel_txt) >= 80
              and "SPINE TRAP" not in sel_txt,
              f"{len(sel_txt)}c | {sel_txt[:60]!r}")

        # (b) translucency, pixel-level (0.8.3 lesson: color regressions
        # need pixel guards, not computed-style guesses — ::selection
        # cannot be read via getComputedStyle at all).
        try:
            from PIL import Image
            import io as _io
            rect = pg.evaluate(r"""() => {
              const sel = window.getSelection();
              if (sel.rangeCount === 0) return null;
              const rs = sel.getRangeAt(0).getClientRects();
              return rs.length ? { x: rs[0].x, y: rs[0].y,
                                   w: rs[0].width, h: rs[0].height } : null;
            }""")
            img = Image.open(_io.BytesIO(pg.screenshot(
                clip={"x": rect["x"], "y": rect["y"],
                      "width": max(8, rect["w"]), "height": max(4, rect["h"])})))
            cy = img.height // 2
            lightest = max(
                (img.getpixel((x, cy)) for x in range(2, img.width - 2, 2)),
                key=lambda p: sum(p[:3]))
            def dist(a, b):
                return sum(abs(x - y) for x, y in zip(a[:3], b))
            d_opaque = dist(lightest, (234, 212, 183))  # paper --editor-sel
            d_white = dist(lightest, (255, 255, 255))
            check("pdf_selection_tint_translucent",
                  d_opaque > 25 and d_white > 18,
                  f"px={lightest} dOpaque={d_opaque} dWhite={d_white}")
        except Exception as e:
            check("pdf_selection_tint_translucent", False, str(e))
        pg.evaluate("window.getSelection().removeAllRanges()")

        # --- §95 virtualization on the 100-page pdf ---
        pg.locator(".file-tabs .file-tab.active").click()
        tree_click(pg, "sample-100p-text.pdf")
        pg.wait_for_selector(".pdf-viewer canvas", timeout=20000)
        pg.wait_for_timeout(600)
        scroller = pg.locator(".pdf-viewer .scroller")
        scroller.evaluate("el => el.scrollTop = 60 * el.scrollHeight / 100")
        pg.wait_for_timeout(1200)
        n_deep = canvases(pg)
        check("deep scroll renders only the window (<=6 canvases)", 0 < n_deep <= 6, str(n_deep))
        check("current page tracks scroll (~61)",
              abs(int(pg.locator("input.page-no").input_value()) - 61) <= 3,
              pg.locator("input.page-no").input_value())

        # --- §96 release on switch away + §93 restore ---
        deep_page = pg.locator("input.page-no").input_value()
        tree_click(pg, "README.md")
        pg.wait_for_timeout(600)
        check("pdf canvases released after switch", canvases(pg) == 0)
        pg.locator(".file-tabs .file-tab:has-text('sample-100p-text.pdf')").click()
        pg.wait_for_selector(".pdf-viewer canvas", timeout=20000)
        pg.wait_for_timeout(600)
        restored = pg.locator("input.page-no").input_value()
        check("pdf state restored on return (page)", abs(int(restored) - int(deep_page)) <= 1,
              f"left {deep_page}, back {restored}")

        # --- spec-012 M8: aborting a running search by switching tabs must
        # not raise (getPage rejections on the destroyed doc used to land in
        # the global unhandledrejection sentinel) ---
        err_before = len([c for c in CONSOLE if c.startswith("PAGEERROR")])
        pg.fill("input.search", "Page")
        pg.press("input.search", "Enter")
        # switch away IMMEDIATELY, mid-walk over 100 pages
        pg.locator(".file-tabs .file-tab:has-text('README.md')").click()
        pg.wait_for_timeout(2500)
        new_errors = [c for c in CONSOLE[err_before:] if c.startswith("PAGEERROR")]
        check("mid-search tab switch raises no page errors (M8)", len(new_errors) == 0,
              "\n".join(new_errors[:3]))
        # ...and the engine still searches cleanly after the aborted run
        pg.locator(".file-tabs .file-tab:has-text('sample-100p-text.pdf')").click()
        pg.wait_for_selector(".pdf-viewer canvas", timeout=20000)
        pg.fill("input.search", "Page")
        pg.press("input.search", "Enter")
        try:
            pg.wait_for_selector(".toolbar:has-text('1 /')", timeout=15000)
            check("search works again after aborted run (M8)", True)
        except Exception as e:
            check("search works again after aborted run (M8)", False, str(e))

        # --- spec-012 M9: switching tabs <300ms after a scroll must keep the
        # mid-page position (a late scroll timer used to overwrite the saved
        # scrollPosition with undefined -> restore degraded to page top) ---
        scroller.evaluate("el => el.scrollTop = 0.65 * el.scrollHeight")
        # no wait: the 300ms scroll debounce is still pending right now
        pg.locator(".file-tabs .file-tab:has-text('README.md')").click()
        pg.wait_for_timeout(900)
        pg.locator(".file-tabs .file-tab:has-text('sample-100p-text.pdf')").click()
        pg.wait_for_selector(".pdf-viewer canvas", timeout=20000)
        pg.wait_for_timeout(700)
        pos = pg.evaluate("""() => {
            const sc = document.querySelector('.pdf-viewer .scroller');
            return { top: sc.scrollTop, sh: sc.scrollHeight };
        }""")
        frac = (pos["top"] / pos["sh"]) if pos["sh"] else 0.0
        # 0.65 = where we scrolled to; the restored position must land back
        # at that fraction of the document (page gaps make per-page math
        # unreliable — slots are 16px apart).
        check("quick switch after scroll keeps mid-page position (M9)",
              abs(frac - 0.65) < 0.02, str(pos))

        # --- spec-012 M7: a zoom storm must settle with exactly one canvas
        # per visible page, all painted at the same (final) scale ---
        for _ in range(10):
            pg.click("button[aria-label='Zoom in']")
        pg.wait_for_timeout(1800)
        storm = pg.evaluate("""() => {
            const slots = [...document.querySelectorAll('.pdf-viewer .page-slot')];
            const painted = slots.filter(s => s.querySelector('canvas'));
            const widths = [...new Set(painted.map(s => s.querySelector('canvas').style.width))];
            const stacked = painted.filter(s => s.querySelectorAll('canvas').length !== 1).length;
            return { painted: painted.length, widths, stacked };
        }""")
        check("zoom storm settles: one canvas per page at one scale (M7)",
              storm["stacked"] == 0 and len(storm["widths"]) == 1 and 0 < storm["painted"] <= 6,
              str(storm))

        # 18.4 MB scanned pdf loads through the bytes channel.
        tree_click(pg, "sample-100p-scan.pdf")
        pg.wait_for_selector(".pdf-viewer canvas", timeout=30000)
        pg.wait_for_timeout(800)
        check("100-page scanned pdf renders", canvases(pg) >= 1)

        errors = [c for c in CONSOLE if c.startswith("PAGEERROR") or c.startswith("error")]
        check("no page errors", len(errors) == 0, "\n".join(errors[:3]))

        browser.close()
        aivlaunch.kill_tree(proc)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
