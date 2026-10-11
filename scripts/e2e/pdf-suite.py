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
EXE = pathlib.Path(r"C:\Users\wzzpk\Desktop\PyProjects\VibeCoding\ProjectViewer\src-tauri\target\debug\ai-project-viewer.exe")
PROJECT = os.path.expandvars(r"%USERPROFILE%\Desktop\AIV-TestProject")
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

        # --- search (D5: page navigation grade) ---
        pg.fill("input.search", "Page 8 line")
        pg.press("input.search", "Enter")
        try:
            pg.wait_for_selector(".toolbar:has-text('1 /')", timeout=15000)
            check("search finds matches", True)
            check("search jumped to page 8",
                  pg.locator("input.page-no").input_value() == "8",
                  pg.locator("input.page-no").input_value())
        except Exception as e:
            check("search finds matches", False, str(e))

        pg.fill("input.search", "zzzz-not-there")
        pg.press("input.search", "Enter")
        pg.wait_for_timeout(1500)
        check("no-result feedback", pg.locator(".toolbar").inner_text().find("0 results") != -1)

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
