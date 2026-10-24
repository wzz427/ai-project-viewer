# -*- coding: utf-8 -*-
"""Round-3 acceptance fixes regression (owner 2026-10-02, four items).
1 update button at far right of the top bar; 2 pdf text selection via
text layer; 3 task-list cursor/pointer-events; 4 right-click Copy.
Run: conda pywork python %TEMP%\\aiv-r3-fix-test.py
"""
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = os.path.expandvars(r"C:\Users\wzzpk\Desktop\PyProjects\VibeCoding\ProjectViewer\src-tauri\target\debug\ai-project-viewer.exe")
PROJECT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "AIV-TestProject")  # in-repo fixture (owner 2026-10-24)
STATE = os.path.expandvars(r"%TEMP%\aiv-r3-state.json")
CDP = 9231
DEBUG = os.path.expandvars(r"%TEMP%\aiv-p4-debug.log")

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


def kill_all():
    # Owner isolation (aivlaunch): this repo's build tree only.
    aivlaunch.kill_strays()


def main():
    if os.path.exists(STATE):
        os.remove(STATE)

    kill_all()
    env = {**os.environ, "AIV_HIDDEN": "1", "AIV_TEST_PROJECT": PROJECT,
           "AIV_STATE_FILE": STATE,
           "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={CDP}"}
    proc = subprocess.Popen([EXE], env=env, stdout=open(DEBUG, "ab"),
                            stderr=subprocess.STDOUT)
    # NOTE: this older script still launches via its own Popen; process
    # termination at the end goes through aivlaunch.kill_tree (PID-scoped).
    with sync_playwright() as pw:
        for _ in range(60):
            try:
                browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
                break
            except Exception:
                time.sleep(0.5)
        pg = browser.contexts[0].pages[0]
        pg.wait_for_selector(".file-tree", timeout=25000)
        pg.wait_for_timeout(700)

        # --- 1. update button far right of the top bar ---
        bar = pg.locator(".project-tabs").bounding_box()
        btn = pg.locator(".update-btn").bounding_box()
        check("update button sits at far right of top bar",
              btn and bar and abs((btn["x"] + btn["width"]) - (bar["x"] + bar["width"])) < 4,
              f"btn right={btn and btn['x']+btn['width']}, bar right={bar and bar['x']+bar['width']}")
        add = pg.locator("button[aria-label='Add project']").bounding_box()
        check("add button stays next to tabs (left of update)",
              add and btn and add["x"] < btn["x"] - 50)

        # --- 3. task-list cursor + pointer-events ---
        pg.click("div.row[role='treeitem'] :text-is('README.md')")
        pg.wait_for_timeout(900)
        probe = pg.evaluate("""() => {
          const label = document.querySelector('.rendered label');
          const input = document.querySelector('.rendered input[type=checkbox]');
          if (!label || !input) return null;
          return {
            labelCursor: getComputedStyle(label).cursor,
            inputPe: getComputedStyle(input).pointerEvents,
          };
        }""")
        check("task-list label cursor is I-beam", probe and probe["labelCursor"] == "text", str(probe))
        check("checkbox no longer eats the pointer", probe and probe["inputPe"] == "none")

        # --- 4. right-click copy on selected text ---
        body = pg.locator(".rendered")
        box = body.bounding_box()
        pg.mouse.move(box["x"] + 40, box["y"] + 30)
        pg.mouse.down()
        pg.mouse.move(box["x"] + 260, box["y"] + 44, steps=6)
        pg.mouse.up()
        pg.mouse.click(box["x"] + 150, box["y"] + 40, button="right")
        pg.wait_for_selector(".copy-menu", timeout=4000)
        pg.locator(".copy-menu").click()
        pg.wait_for_timeout(600)
        check("right-click Copy shows success toast",
              "Copied" in pg.locator("body").inner_text())

        # --- 2. PDF text layer selection ---
        pg.click("div.row[role='treeitem'] :text-is('pdf')")
        pg.wait_for_timeout(400)
        pg.click("div.row[role='treeitem'] :text-is('sample-10p-text.pdf')")
        pg.wait_for_selector(".pdf-viewer canvas", timeout=25000)
        pg.wait_for_timeout(1800)
        spans = pg.evaluate("document.querySelectorAll('.pdf-text-layer span').length")
        check("pdf text layer present with spans", spans > 5, str(spans))
        # Drag across REAL span boxes (ratio coordinates can land in the
        # gaps between text lines and select nothing).
        boxes = pg.evaluate("""() => {
          const spans = [...document.querySelectorAll('.pdf-text-layer span')]
            .filter(s => s.textContent.trim().length > 3);
          return spans.slice(0, 3).map(s => {
            const r = s.getBoundingClientRect();
            return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
          });
        }""")
        pg.mouse.move(boxes[0]["x"], boxes[0]["y"])
        pg.mouse.down()
        pg.mouse.move(boxes[2]["x"], boxes[2]["y"] + 1, steps=8)
        pg.mouse.up()
        sel = pg.evaluate("window.getSelection().toString()")
        check("pdf glyphs are selectable via text layer", len(sel.strip()) > 0, repr(sel[:40]))

        # right-click copy works here too
        pg.mouse.click(boxes[1]["x"], boxes[1]["y"], button="right")
        pg.wait_for_selector(".copy-menu", timeout=4000)
        pg.locator(".copy-menu").click()
        pg.wait_for_timeout(500)
        check("pdf selection copies via right-click",
              "Copied" in pg.locator("body").inner_text())

        errors = pg.evaluate("window.__aivErrors || 0")
        browser.close()
    aivlaunch.kill_tree(proc)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
