# -*- coding: utf-8 -*-
"""v14 selection driver verification, ZERO disturbance (off-screen window,
in-page dispatched events — drives our driver fully; the native drag never
engages, which also sidesteps the synthetic pointermove swallowing).

V1 normal drag            V2 margin exit
V3 wide right-exit        V4 OWNER'S CASE: hold + blank + up/down
V5 pad-start              V6 dblclick (trusted CDP)
V7 cross-page drag        V8 pollution (pad gesture then normal)
"""
import ctypes
import os
import subprocess
import time
import ctypes.wintypes as wt

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = r"C:\Users\wzzpk\Desktop\PyProjects\VibeCoding\ProjectViewer\src-tauri\target\release\ai-project-viewer.exe"
PROJECT = os.path.expandvars(r"%USERPROFILE%\Desktop\AIV-TestProject")
STATE = os.path.expandvars(r"%TEMP%\aiv-v14.json")
CDP = 9255


def main():
    aivlaunch.kill_strays()
    if os.path.exists(STATE):
        os.remove(STATE)
    env = {**os.environ, "AIV_TEST_PROJECT": PROJECT, "AIV_STATE_FILE": STATE,
           "AIV_HIDDEN": "1",
           "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={CDP}"}
    proc = subprocess.Popen([EXE], env=env)
    hwnd = aivlaunch.window_of(proc.pid)
    if hwnd:
        aivlaunch.park_offscreen(hwnd)
    try:
        with sync_playwright() as pw:
            for _ in range(60):
                try:
                    browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
                    break
                except Exception:
                    time.sleep(0.5)
            pg = browser.contexts[0].pages[0]
            pg.wait_for_selector(".file-tree", timeout=25000)
            pg.wait_for_timeout(600)
            pg.click("div.row[role='treeitem'] :text-is('pdf')")
            pg.wait_for_timeout(300)
            pg.click("div.row[role='treeitem'] :text-is('sample-10p-text.pdf')")
            pg.wait_for_selector(".pdf-viewer canvas", timeout=25000)
            pg.wait_for_timeout(1500)

            def dispatch_gesture(points, hold_ms=25):
                """points: [(x, y), ...] first = mousedown on the span there."""
                pg.evaluate("""(pts) => {
                  const [d0, ...rest] = pts;
                  const spanAt = (x, y) => document.elementFromPoint(x, y);
                  const target = spanAt(d0[0], d0[1]) || document.body;
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

            def read(label):
                time.sleep(0.15)
                v = pg.evaluate("window.getSelection().toString()")
                lines = [l for l in v.split("\n") if l.strip()]
                print(f"{label}: {len(v.strip())}c/{len(lines)}L | {v.strip()[:40]!r}")
                pg.evaluate("window.getSelection().removeAllRanges()")

            geo = pg.evaluate("""() => {
              const layer = document.querySelector('.pdf-text-layer');
              const lr = layer.getBoundingClientRect();
              const spans = [...layer.querySelectorAll('span')]
                .filter(s => s.textContent.trim().length > 3);
              const rows = [];
              for (const s of spans) {
                const r = s.getBoundingClientRect();
                let row = rows.find(x => Math.abs(x.y - (r.y + r.height/2)) < 10);
                if (!row) { row = { y: r.y + r.height/2, left: r.x, right: r.x + r.width }; rows.push(row); }
                else { row.left = Math.min(row.left, r.x); row.right = Math.max(row.right, r.x + r.width); }
              }
              return { lx: lr.left, rows };
            }""")
            rows = geo["rows"]
            print(f"rows: {len(rows)}, layer left={geo['lx']:.0f}")

            print("=== V1 normal drag 0.3->0.6 ===")
            r = rows[0]
            dispatch_gesture([
                (r["left"] + r["right"] - r["left"]) if False else (r["left"] + (r["right"] - r["left"]) * 0.3, r["y"]),
                (r["left"] + (r["right"] - r["left"]) * 0.45, r["y"]),
                (r["left"] + (r["right"] - r["left"]) * 0.6, r["y"]),
            ])
            read("V1")

            print("=== V2 margin exit ===")
            r = rows[0]
            dispatch_gesture([
                (r["left"] + (r["right"] - r["left"]) * 0.55, r["y"]),
                (r["left"] - 5, r["y"]),
                (geo["lx"] - 18, r["y"]),
            ])
            read("V2")

            print("=== V4 OWNER: phrase select, then blank right + up/down ===")
            r = rows[3]
            x04 = r["left"] + (r["right"] - r["left"]) * 0.4
            x06 = r["left"] + (r["right"] - r["left"]) * 0.6
            blank_x = r["right"] + 200
            dispatch_gesture([
                (x04, r["y"]),
                (x06, r["y"]),
                (blank_x, r["y"]),
                (blank_x, rows[2]["y"]),
                (blank_x, rows[1]["y"]),
                (blank_x, rows[2]["y"]),
                (blank_x, rows[3]["y"]),
            ])
            read("V4 (expect ~anchor..row3, sane)")

            print("=== V4b same but end far above anchor ===")
            r = rows[6]
            dispatch_gesture([
                (r["left"] + (r["right"] - r["left"]) * 0.5, r["y"]),
                (r["right"] + 200, r["y"]),
                (r["right"] + 200, rows[2]["y"]),
                (r["right"] + 200, rows[0]["y"]),
            ])
            read("V4b (expect anchor..row0-ish)")

            print("=== V5 pad start (text-left-14) ===")
            r = rows[2]
            dispatch_gesture([
                (r["left"] + 20 - 14, r["y"]),
                (r["left"] + (r["right"] - r["left"]) * 0.3, r["y"]),
                (r["left"] + (r["right"] - r["left"]) * 0.5, r["y"]),
            ])
            read("V5")

            print("=== V7 cross-page drag ===")
            r = rows[0]
            page2_y = pg.evaluate("""() => {
              const layers = [...document.querySelectorAll('.pdf-text-layer')];
              if (layers.length < 2) return null;
              const spans = [...layers[1].querySelectorAll('span')]
                .filter(s => s.textContent.trim().length > 3);
              return spans.length ? spans[0].getBoundingClientRect().top + 8 : null;
            }""")
            if page2_y:
                dispatch_gesture([
                    (r["left"] + (r["right"] - r["left"]) * 0.5, r["y"]),
                    (r["left"] + (r["right"] - r["left"]) * 0.6, rows[3]["y"]),
                    (r["left"] + (r["right"] - r["left"]) * 0.6, page2_y),
                ])
                read("V7 (expect crosses into page 2)")
            else:
                print("V7: page 2 not rendered, skipped")

            print("=== V8 pollution: pad gesture then normal ===")
            r = rows[2]
            dispatch_gesture([
                (r["left"] + 20 - 14, r["y"]),
                (r["left"] + (r["right"] - r["left"]) * 0.5, r["y"]),
            ])
            read("V8 pad")
            r = rows[0]
            dispatch_gesture([
                (r["left"] + (r["right"] - r["left"]) * 0.55, r["y"]),
                (geo["lx"] - 18, r["y"]),
            ])
            read("V8 after pad (expect 54c/1L)")

            print("=== V3 wide right-exit ===")
            cdp = pg.context.new_cdp_session(pg)
            cdp.send("Emulation.setDeviceMetricsOverride",
                     {"width": 1536, "height": 888, "deviceScaleFactor": 0, "mobile": False})
            pg.wait_for_timeout(1800)
            rows2 = pg.evaluate("""() => {
              const spans = [...document.querySelectorAll('.pdf-text-layer span')]
                .filter(s => s.textContent.trim().length > 3);
              const rows = [];
              for (const s of spans) {
                const r = s.getBoundingClientRect();
                let row = rows.find(x => Math.abs(x.y - (r.y + r.height/2)) < 10);
                if (!row) { row = { y: r.y + r.height/2, left: r.x, right: r.x + r.width }; rows.push(row); }
                else { row.right = Math.max(row.right, r.x + r.width); }
              }
              return rows;
            }""")
            r = rows2[3]
            dispatch_gesture([
                (r["left"] + (r["right"] - r["left"]) * 0.5, r["y"]),
                (r["right"] + 100, r["y"]),
                (r["right"] + 400, r["y"]),
            ])
            read("V3 (expect to row end, 1L)")
            cdp.send("Emulation.clearDeviceMetricsOverride")

            print("=== V6 dblclick (trusted) ===")
            pg.wait_for_timeout(1200)
            rows3 = pg.evaluate("""() => {
              const s = [...document.querySelectorAll('.pdf-text-layer span')]
                .filter(s => s.textContent.trim().length > 3)[0];
              const r = s.getBoundingClientRect();
              return { x: r.x + r.width * 0.3, y: r.y + r.height / 2 };
            }""")
            pg.mouse.dblclick(rows3["x"], rows3["y"])
            time.sleep(0.3)
            read("V6 (expect one word)")
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)


if __name__ == "__main__":
    main()
