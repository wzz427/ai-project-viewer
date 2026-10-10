# -*- coding: utf-8 -*-
"""REAL-INPUT verification harness (owner 2026-10-09: "解决验证问题").

CDP synthetic mouse events in a hidden window are NOT equivalent to a real
mouse on a real window (the PDF selection bug passed all synthetic tests
and still failed on the owner's screen). This harness shows the app as a
real (non-activating) window and drives the OS-level mouse via Win32
mouse_event — the same trusted path used for the drag tests (lessons L10).
CDP is used read-only (geometry + selection result).

Run: conda pywork python %TEMP%\\aiv-real-input-test.py
"""
import ctypes
import os
import subprocess
import sys
import time

import ctypes.wintypes as wt
from playwright.sync_api import sync_playwright

user32 = ctypes.windll.user32
EXE = r"C:\Users\wzzpk\Desktop\PyProjects\VibeCoding\ProjectViewer\src-tauri\target\release\ai-project-viewer.exe"
PROJECT = os.path.expandvars(r"%USERPROFILE%\Desktop\AIV-TestProject")
STATE = os.path.expandvars(r"%TEMP%\aiv-real-input.json")
CDP = 9240

def real_click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP


def real_drag(x0, y0, x1, y1, steps=12):
    user32.SetCursorPos(int(x0), int(y0))
    time.sleep(0.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    for i in range(1, steps + 1):
        user32.SetCursorPos(int(x0 + (x1 - x0) * i / steps),
                            int(y0 + (y1 - y0) * i / steps))
        time.sleep(0.02)
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def main():
    if os.path.exists(STATE):
        os.remove(STATE)
    subprocess.run(["powershell", "-NoProfile", "-Command",
         "Get-Process ai-project-viewer -ErrorAction SilentlyContinue | Stop-Process -Force; "
         "Get-CimInstance Win32_Process -Filter \"Name='msedgewebview2.exe'\" | "
         "Where-Object { $_.CommandLine -match 'aiprojectviewer' } | "
         "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"], capture_output=True)
    env = {**os.environ, "AIV_TEST_PROJECT": PROJECT, "AIV_STATE_FILE": STATE,
           "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={CDP}"}
    proc = subprocess.Popen([EXE], env=env)
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
            print("real dpr:", pg.evaluate("window.devicePixelRatio"))
            print("UA:", pg.evaluate("navigator.userAgent"))

            pg.click("div.row[role='treeitem'] :text-is('pdf')")
            pg.wait_for_timeout(400)
            pg.click("div.row[role='treeitem'] :text-is('sample-10p-text.pdf')")
            pg.wait_for_selector(".pdf-viewer canvas", timeout=25000)
            pg.wait_for_timeout(2000)

            # real window rect -> screen coordinates for span centers
            hwnd = None
            for _ in range(30):
                hwnd = user32.FindWindowW(None, "AI Project Viewer")
                if hwnd:
                    break
                time.sleep(0.3)
            rect = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            # page origin: canvas box in page coords + window origin
            canv = pg.evaluate("""() => {
              const c = document.querySelector('.pdf-canvas');
              const r = c.getBoundingClientRect();
              return { x: r.x, y: r.y };
            }""")
            # page -> screen: exact client origin (physical px) + css*dpr.
            # Physical = CSS x devicePixelRatio at 125% scaling — mixing
            # them shifts every click by 1.25x and invalidates the verdict.
            cr = wt.RECT()
            pt = wt.POINT(0, 0)
            user32.GetClientRect(hwnd, ctypes.byref(cr))
            user32.ClientToScreen(hwnd, ctypes.byref(pt))
            # self-calibrating scale: virtual client size vs page CSS viewport —
            # immune to DPI-virtualization mismatch between processes (the
            # css*dpr formula was off by exactly one 1.25 factor here)
            inner_w = pg.evaluate("window.innerWidth")
            inner_h = pg.evaluate("window.innerHeight")
            sx_scale = cr.right / inner_w
            sy_scale = cr.bottom / inner_h
            ox = pt.x + canv["x"] * sx_scale
            oy = pt.y + canv["y"] * sy_scale
            print(f"client virtual=({cr.right},{cr.bottom}) inner=({inner_w},{inner_h}) "
                  f"scale=({sx_scale:.4f},{sy_scale:.4f})")

            spans = pg.evaluate("""() => {
              const spans = [...document.querySelectorAll('.pdf-text-layer span')]
                .filter(s => s.textContent.trim().length > 3);
              return spans.slice(0, 3).map(s => {
                const r = s.getBoundingClientRect();
                return { x: r.x + r.width * 0.3, y: r.y + r.height / 2 };
              });
            }""")

            # 1) owner's gesture: single real click on a line of text
            real_click(ox + spans[0]["x"] * sx_scale, oy + spans[0]["y"] * sy_scale)
            time.sleep(0.6)
            sel_click = pg.evaluate("window.getSelection().toString()")
            pg.evaluate("window.getSelection().removeAllRanges()")

            # 2) one-line real drag along the same line
            same = pg.evaluate("""() => {
              const s = [...document.querySelectorAll('.pdf-text-layer span')]
                .filter(s => s.textContent.trim().length > 3)[0];
              const r = s.getBoundingClientRect();
              return { x0: r.x + r.width * 0.25, x1: r.x + r.width * 0.75, y: r.y + r.height / 2 };
            }""")
            real_drag(ox + same["x0"] * sx_scale, oy + same["y"] * sy_scale, ox + same["x1"] * sx_scale, oy + same["y"] * sy_scale)
            time.sleep(0.6)
            sel_line = pg.evaluate("window.getSelection().toString()")
            lines = [l for l in sel_line.split("\n") if l.strip()]
            pg.evaluate("window.getSelection().removeAllRanges()")

            print(f"real click selection: {len(sel_click.strip())} chars")
            print(f"real one-line drag: {len(sel_line.strip())} chars, {len(lines)} lines")

            # hypothesis: the long REAL drag triggers native drag&drop
            pg.evaluate("window.__dragStarted = 0; document.addEventListener('dragstart', () => window.__dragStarted++)")
            # bisect the drag span: where does it start over-selecting?
            for a, b in [(0.3, 0.5), (0.3, 0.6), (0.25, 0.75), (0.75, 0.25), (0.4, 0.6)]:
                seg = pg.evaluate("""(f) => {
                  const s = [...document.querySelectorAll('.pdf-text-layer span')]
                    .filter(s => s.textContent.trim().length > 3)[0];
                  const r = s.getBoundingClientRect();
                  return { x0: r.x + r.width * f[0], x1: r.x + r.width * f[1], y: r.y + r.height / 2 };
                }""", [a, b])
                real_drag(ox + seg["x0"] * sx_scale, oy + seg["y"] * sy_scale, ox + seg["x1"] * sx_scale, oy + seg["y"] * sy_scale)
                time.sleep(0.4)
                sv = pg.evaluate("window.getSelection().toString()")
                pg.evaluate("window.getSelection().removeAllRanges()")
                drg = pg.evaluate("window.__dragStarted")
                print(f"drag {a}->{b}: {len(sv.strip())} chars | dragstart={drg} | {sv.strip()[:40]!r}")

            # tiny drag (a few words on the same line)
            tiny = pg.evaluate("""() => {
              const s = [...document.querySelectorAll('.pdf-text-layer span')]
                .filter(s => s.textContent.trim().length > 3)[0];
              const r = s.getBoundingClientRect();
              return { x0: r.x + r.width * 0.3, x1: r.x + r.width * 0.42, y: r.y + r.height / 2 };
            }""")
            real_drag(ox + tiny["x0"] * sx_scale, oy + tiny["y"] * sy_scale, ox + tiny["x1"] * sx_scale, oy + tiny["y"] * sy_scale)
            time.sleep(0.5)
            sel_tiny = pg.evaluate("window.getSelection().toString()")
            pg.evaluate("window.getSelection().removeAllRanges()")
            print(f"tiny drag (0.12 line width): {len(sel_tiny.strip())} chars | {sel_tiny.strip()[:60]!r}")

            # native double-click word selection
            real_click(ox + same["x0"] * sx_scale, oy + same["y"] * sy_scale)
            real_click(ox + same["x0"] * sx_scale, oy + same["y"] * sy_scale)
            time.sleep(0.5)
            sel_dbl = pg.evaluate("window.getSelection().toString()")
            pg.evaluate("window.getSelection().removeAllRanges()")
            print(f"double-click word: {len(sel_dbl.strip())} chars | {sel_dbl.strip()[:60]!r}")
            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        subprocess.run(["powershell", "-NoProfile", "-Command",
             "Get-Process ai-project-viewer -ErrorAction SilentlyContinue | Stop-Process -Force"],
            capture_output=True)


if __name__ == "__main__":
    main()
