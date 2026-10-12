# -*- coding: utf-8 -*-
"""spec-014 visual self-check (V1/V7/V8/V10): screenshots of the redesigned
shell in both themes, taken over CDP from a window that is SHOWN but parked
off-screen (AIV_HIDDEN alone freezes rAF/paint — L42; park_offscreen does
ShowWindow(SW_SHOWNOACTIVATE) so the window paints without ever touching
the owner's monitors).

Zero-disturbance: PID-scoped launch/kill via aivlaunch; the project under
view is this repo itself (read-only verbs only: tree list, file read,
git status/diff machinery is not triggered beyond panel render).
"""
import atexit
import ctypes
from ctypes import wintypes as wt
import os
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = os.path.join(os.path.dirname(__file__), "..", "..",
                   "src-tauri", "target", "release", "ai-project-viewer.exe")
PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE = os.path.join(os.environ["TEMP"], "aiv-p14visual.json")
CDP = 9271
OUT = os.path.join(os.environ["TEMP"], "aiv-014-shots")
TITLE = "AI Project Viewer"

os.makedirs(OUT, exist_ok=True)

proc = aivlaunch.launch(os.path.abspath(EXE), PROJECT, STATE, CDP)

_USER32 = ctypes.windll.user32
_WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


def _cleanup():
    aivlaunch.kill_tree(proc)


atexit.register(_cleanup)


def hwnd_by_title(timeout_s=15):
    """(pid, title) enum WITHOUT a visibility filter — under AIV_HIDDEN the
    main window exists but IsWindowVisible is False (L42)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        hits = []

        def cb(hwnd, _):
            buf = ctypes.create_unicode_buffer(64)
            _USER32.GetWindowTextW(hwnd, buf, 64)
            owner = wt.DWORD()
            _USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == proc.pid and buf.value == TITLE:
                hits.append(hwnd)
            return True

        _USER32.EnumWindows(_WNDENUMPROC(cb), 0)
        if hits:
            return hits[0]
        time.sleep(0.2)
    return 0


hwnd = hwnd_by_title()
if hwnd:
    aivlaunch.park_offscreen(hwnd)  # shows off-screen, no activate

with sync_playwright() as p:
    for _ in range(60):
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
            break
        except Exception:
            time.sleep(0.5)
    page = browser.contexts[0].pages[0]
    page.wait_for_selector(".file-tree", timeout=30000)

    def tree_row(name):
        return page.locator(".file-tree .row", has=page.locator(".name", has_text=name)).first

    def expand(name):
        row = tree_row(name)
        if row.get_attribute("aria-expanded") != "true":
            row.click()
            time.sleep(0.6)

    def open_file(name):
        tree_row(name).click()
        deadline = time.time() + 8
        while time.time() < deadline:
            active = page.locator(".file-tab.active .name")
            if active.count() and active.inner_text() == name:
                time.sleep(0.4)
                return
            time.sleep(0.15)
        raise TimeoutError(f"open_file({name})")

    def shot(name):
        path = os.path.join(OUT, f"{name}.png")
        page.screenshot(path=path)
        print("shot:", path)

    def set_theme(value):
        page.click('button[title="Settings"]')
        page.locator(f'input[name="theme"][value="{value}"]').check()
        page.click('.header-tab:has-text("Files")')
        time.sleep(0.5)

    # --- light theme (default via fresh state is system; force light) ---
    set_theme("light")

    # Files view: markdown doc open (viewer + toolbar + tab strip).
    expand("docs")
    open_file("how-to-report.md")
    shot("01-light-files-md")

    # Tab strip variety: json + code + image icons.
    open_file("package.json")
    expand("scripts")
    expand("e2e")
    open_file("aivlaunch.py")
    expand("public")
    open_file("favicon.png")
    shot("02-light-tabs-mixed")

    # Git panel: branch icon, pill badge, sections, entries.
    page.locator('.sidebar-header .header-tab', has_text="Git").first.click()
    time.sleep(1.5)
    shot("03-light-git-panel")

    # Context menu = floating overlay surface.
    page.locator('.sidebar-header .header-tab', has_text="Files").first.click()
    time.sleep(0.3)
    page.locator(".file-tree .row", has=page.locator(".name", has_text="docs")).first.click(button="right")
    time.sleep(0.4)
    shot("04-light-context-menu")
    page.keyboard.press("Escape")
    page.mouse.click(10, 300)

    # --- dark theme ---
    set_theme("dark")
    shot("05-dark-files-md")
    page.locator('.sidebar-header .header-tab', has_text="Git").first.click()
    time.sleep(0.8)
    shot("06-dark-git-panel")
    page.locator('.sidebar-header .header-tab', has_text="Files").first.click()
    time.sleep(0.3)

    # Selected-tree-row tint + active file tab, dark.
    open_file("how-to-report.md")
    shot("07-dark-selected-row")

print("DONE ->", OUT)
