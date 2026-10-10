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
    subprocess.run(["powershell", "-NoProfile", "-Command",
         "Get-Process ai-project-viewer -ErrorAction SilentlyContinue | Stop-Process -Force; "
         "Get-CimInstance Win32_Process -Filter \"Name='msedgewebview2.exe'\" | "
         "Where-Object { $_.CommandLine -match 'aiprojectviewer' } | "
         "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"], capture_output=True)


def launch():
    kill_all()
    env = {**os.environ,
           "AIV_HIDDEN": "1",
           "AIV_TEST_PROJECT": PROJECT,
           "AIV_STATE_FILE": STATE,
           "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={CDP}"}
    return subprocess.Popen([str(EXE)], env=env, stdout=open(DEBUG, "ab"),
                            stderr=subprocess.STDOUT)


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

        # 18.4 MB scanned pdf loads through the bytes channel.
        tree_click(pg, "sample-100p-scan.pdf")
        pg.wait_for_selector(".pdf-viewer canvas", timeout=30000)
        pg.wait_for_timeout(800)
        check("100-page scanned pdf renders", canvases(pg) >= 1)

        errors = [c for c in CONSOLE if c.startswith("PAGEERROR") or c.startswith("error")]
        check("no page errors", len(errors) == 0, "\n".join(errors[:3]))

        browser.close()
        proc.terminate()
        proc.wait(timeout=10)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
