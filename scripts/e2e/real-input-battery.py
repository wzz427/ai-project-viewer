# -*- coding: utf-8 -*-
"""Final differential: EXACT same gesture battery (incl. preceding click and
timing) on mintest control page vs app PDF viewer, with a foreground guard.

Foreground guard: before each real gesture, if the app window lost OS
foreground (owner reading chat etc.), re-activate it by a real click on its
own title bar — the same thing a user does; no SetForegroundWindow tricks.
Usage: python aiv-battery-replica.py mintest|app
"""
import ctypes
import os
import subprocess
import sys
import time

import ctypes.wintypes as wt
from playwright.sync_api import sync_playwright

import aivlaunch

user32 = ctypes.windll.user32
EXE = r"C:\Users\wzzpk\Desktop\PyProjects\VibeCoding\ProjectViewer\src-tauri\target\release\ai-project-viewer.exe"
PROJECT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "AIV-TestProject")  # in-repo fixture (owner 2026-10-24)
CDP = 9245
MODE = sys.argv[1] if len(sys.argv) > 1 else "app"
STATE = os.path.expandvars(rf"%TEMP%\aiv-battery-{MODE}.json")
URL = "http://127.0.0.1:8899/mintest.html"


def real_click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


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
    aivlaunch.kill_strays()
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
            # Owner isolation: window by OUR pid, never by title.
            hwnd = aivlaunch.window_of(proc.pid, timeout_s=12)

            if MODE == "mintest":
                pg.goto(URL, timeout=30000)
                pg.wait_for_selector(".textLayer span", timeout=30000)
            else:
                pg.click("div.row[role='treeitem'] :text-is('pdf')")
                pg.wait_for_timeout(400)
                pg.click("div.row[role='treeitem'] :text-is('sample-10p-text.pdf')")
                pg.wait_for_selector(".pdf-viewer canvas", timeout=25000)
            pg.wait_for_timeout(2000)

            cr = wt.RECT(); pt = wt.POINT(0, 0); wr = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(wr))
            user32.GetClientRect(hwnd, ctypes.byref(cr))
            user32.ClientToScreen(hwnd, ctypes.byref(pt))
            kx = cr.right / pg.evaluate("window.innerWidth")
            ky = cr.bottom / pg.evaluate("window.innerHeight")

            SEL = ".textLayer span" if MODE == "mintest" else ".pdf-text-layer span"

            def span0():
                return pg.evaluate("""(sel) => {
                  const s = [...document.querySelectorAll(sel)]
                    .filter(s => s.textContent.trim().length > 3)[0];
                  const r = s.getBoundingClientRect();
                  return { x: r.x, y: r.y + r.height / 2, w: r.width };
                }""", SEL)

            def ensure_fg():
                for _ in range(10):
                    if user32.GetForegroundWindow() == hwnd:
                        return True
                    # user-like reactivation: click the app's own title bar
                    real_click((wr.left + wr.right) / 2, wr.top + 15)
                    time.sleep(0.4)
                return user32.GetForegroundWindow() == hwnd

            def do_click():
                ok = ensure_fg()
                s = span0()
                real_click(pt.x + (s["x"] + s["w"] * 0.3) * kx,
                           pt.y + s["y"] * ky)
                time.sleep(0.6)
                v = pg.evaluate("window.getSelection().toString()")
                pg.evaluate("window.getSelection().removeAllRanges()")
                print(f"click (fg={ok}): {len(v.strip())}c")

            def do_drag(a, b):
                ok = ensure_fg()
                s = span0()
                y = pt.y + s["y"] * ky
                real_drag(pt.x + (s["x"] + s["w"] * a) * kx, y,
                          pt.x + (s["x"] + s["w"] * b) * kx, y)
                time.sleep(0.6)
                v = pg.evaluate("window.getSelection().toString()")
                pg.evaluate("window.getSelection().removeAllRanges()")
                lines = [l for l in v.split("\n") if l.strip()]
                print(f"drag {a}->{b} (fg={ok}): {len(v.strip())}c/{len(lines)}L | {v.strip()[:36]!r}")

            print(f"=== battery on {MODE} ===")
            do_click()                      # the battery's leading click
            do_drag(0.25, 0.75)             # the "one-line drag"
            do_drag(0.3, 0.5)
            do_drag(0.3, 0.6)
            do_drag(0.25, 0.75)
            do_drag(0.75, 0.25)
            do_drag(0.4, 0.6)
            do_drag(0.3, 0.42)
            # double-click
            ok = ensure_fg()
            s = span0()
            x, y = pt.x + (s["x"] + s["w"] * 0.3) * kx, pt.y + s["y"] * ky
            real_click(x, y); real_click(x, y)
            time.sleep(0.5)
            v = pg.evaluate("window.getSelection().toString()")
            pg.evaluate("window.getSelection().removeAllRanges()")
            print(f"dblclick (fg={ok}): {len(v.strip())}c | {v.strip()[:36]!r}")
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)


if __name__ == "__main__":
    main()
