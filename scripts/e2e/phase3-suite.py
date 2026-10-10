# Regression tests for the 2026-10-01 ten-item feedback round (zero foreground).
import json
import time

from playwright.sync_api import sync_playwright

# -*- coding: utf-8 -*-
"""Phase 3 viewer regression (self-launching, zero disturbance).
Was a replay script expecting an app on :9222; formalized 2026-10-10 with
the standard launcher (AIV_HIDDEN + off-screen + CDP)."""
import atexit
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import time

EXE = os.path.join(os.path.dirname(__file__), "..", "..",
                   "src-tauri", "target", "release", "ai-project-viewer.exe")
PROJECT = os.path.expandvars(r"%USERPROFILE%\Desktop\AIV-TestProject")
STATE = os.path.expandvars(r"%TEMP%iv-p3suite.json")
CDP = 9257

if os.path.exists(STATE):
    os.remove(STATE)
subprocess.run(["powershell", "-NoProfile", "-Command",
     "Get-Process ai-project-viewer -ErrorAction SilentlyContinue | Stop-Process -Force"],
    capture_output=True)
_env = {**os.environ, "AIV_TEST_PROJECT": PROJECT, "AIV_STATE_FILE": STATE,
        "AIV_HIDDEN": "1",
        "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={CDP}"}
proc = subprocess.Popen([os.path.abspath(EXE)], env=_env)
_user32 = ctypes.windll.user32
for _ in range(40):
    if _user32.FindWindowW(None, "AI Project Viewer"):
        break
    time.sleep(0.25)
_hwnd = _user32.FindWindowW(None, "AI Project Viewer")
if _hwnd:
    _user32.SetWindowPos(_hwnd, 0, -2500, -100, 0, 0, 0x0001 | 0x0010 | 0x0004)
    _user32.ShowWindow(_hwnd, 4)

def _cleanup():
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        pass
    subprocess.run(["powershell", "-NoProfile", "-Command",
         "Get-Process ai-project-viewer -ErrorAction SilentlyContinue | Stop-Process -Force"],
        capture_output=True)

atexit.register(_cleanup)


results = {}
FAIL = []

def check(name, ok, detail=""):
    results[name] = "PASS" if ok else f"FAIL {detail}"
    if not ok:
        FAIL.append(name)

with sync_playwright() as p:
    for _ in range(60):
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
            break
        except Exception:
            time.sleep(0.5)
    page = browser.contexts[0].pages[0]
    page.wait_for_selector(".file-tree", timeout=25000)

    def tree_row(name):
        return page.locator(".file-tree .row", has=page.locator(".name", has_text=name)).first

    def expand(rel_name):
        row = tree_row(rel_name)
        if row.get_attribute("aria-expanded") != "true":
            row.click()
            time.sleep(0.5)

    def open_file(name):
        tree_row(name).click()
        deadline = time.time() + 6
        while time.time() < deadline:
            if page.locator(".file-tab.active .name").count() and page.locator(".file-tab.active .name").inner_text() == name:
                time.sleep(0.35)
                return
            time.sleep(0.15)
        raise TimeoutError(f"open_file({name})")

    def body_contains(sub, timeout_s=6):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if sub in page.locator(".viewer-body").inner_text():
                return True
            time.sleep(0.2)
        return False

    def press(key, shift=False):
        page.evaluate(
            """(o) => window.dispatchEvent(new KeyboardEvent('keydown',
               { key: o.k, ctrlKey: true, shiftKey: o.s, bubbles: true, cancelable: true }))""",
            {"k": key, "s": shift})

    def tab_count():
        return page.locator(".file-tab").count()

    # --- #3 regression: text -> text switch must show the NEW content ---
    expand("edge-cases")
    open_file("chinese-gb18030.txt")
    check("gb18030_shows", body_contains("编码兜底正确"))
    expand("src")
    open_file("main.py")
    check("text_to_text_switch", body_contains("Entry point"))
    open_file("utils.py")
    check("text_to_text_switch_2", body_contains("return a + b"))
    # html after text (owner's screenshot case)
    open_file("index.html")
    check("html_after_text", body_contains("<h1>HTML viewed as Code</h1>") or body_contains("HTML viewed as Code"))

    # --- #10 regression: image -> image switch shows the NEW image ---
    expand("assets")
    open_file("logo.svg")
    src1 = page.locator(".image-viewer img").get_attribute("src")
    open_file("photo.jpg")
    time.sleep(0.6)
    src2 = page.locator(".image-viewer img").get_attribute("src")
    check("image_to_image_switch", src2 is not None and src1 is not None and src2 != src1 and "image/jpeg" in src2)
    open_file("icon.gif")
    gif_src = page.locator(".image-viewer img").get_attribute("src") or ""
    check("gif_renders", gif_src.startswith("data:image/gif"), gif_src[:30])

    # --- #8 pin model (clarified): accumulate until pinned, then recycle ---
    n0 = tab_count()
    open_file("notes.txt")
    expand("data")
    open_file("sample.csv")
    n_after_two = tab_count()
    check("accumulate_when_unpinned", n_after_two >= 2, f"{n0} -> {n_after_two}")
    # pin the current tab; further opens must recycle unpinned slots
    page.locator(".file-tab.active").click(button="right")
    page.locator(".menu button", has_text="Pin Tab").click()
    time.sleep(0.2)
    open_file("server.log")
    open_file("metrics.json")
    check("recycle_after_pin", tab_count() == n_after_two, f"{n_after_two} -> {tab_count()}")
    check("pinned_survives", page.locator(".file-tab .pin").count() == 1)
    check("pinned_still_open", page.locator(".file-tab", has_text="sample.csv").count() == 1)

    # --- #5: md mode via tab menu ---
    open_file("README.md")
    page.locator(".file-tab.active").click(button="right")
    page.locator(".menu button", has_text="View Source").click()
    time.sleep(0.3)
    check("md_source_via_menu", page.locator(".code-viewer").count() == 1)
    page.locator(".file-tab.active").click(button="right")
    page.locator(".menu button", has_text="View Rendered").click()
    time.sleep(0.3)
    check("md_rendered_via_menu", page.locator(".markdown-viewer .rendered").count() == 1)

    # --- #1: tab strip auto-reveals active tab ---
    page.evaluate("""() => {
      const bar = document.querySelector('.file-tabs');
      if (bar) bar.scrollLeft = 0;
    }""")
    open_file("README.md")
    time.sleep(0.4)
    vis = page.evaluate("""() => {
      const el = document.querySelector('.file-tab.active');
      if (!el) return false;
      const r = el.getBoundingClientRect();
      const bar = document.querySelector('.file-tabs').getBoundingClientRect();
      return r.right <= bar.right + 1 && r.left >= bar.left - 1;
    }""")
    check("active_tab_scrolled_into_view", bool(vis))

    # --- #9: drag reorder tabs ---
    titles_before = page.locator(".file-tab .name").all_inner_texts()
    if len(titles_before) >= 2:
        a = page.locator(".file-tab").nth(0)
        b = page.locator(".file-tab").nth(1)
        ab = a.bounding_box(); bb = b.bounding_box()
        # aim at the RIGHT half of tab[1]: drop-after semantics swap them
        tx = bb["x"] + bb["width"] * 0.75
        page.mouse.move(ab["x"] + 20, ab["y"] + ab["height"] / 2)
        page.mouse.down()
        for i in range(1, 11):
            page.mouse.move(ab["x"] + 20 + (tx - ab["x"] - 20) * i / 10, ab["y"] + ab["height"] / 2, steps=1)
            time.sleep(0.02)
        page.mouse.up()
        time.sleep(0.3)
        titles_after = page.locator(".file-tab .name").all_inner_texts()
        check("tab_drag_reorder", titles_before != titles_after, f"{titles_before} -> {titles_after}")
    else:
        check("tab_drag_reorder", False, "not enough tabs")

    # --- #4: font size setting applies ---
    page.click('button[title="Settings"]')
    time.sleep(0.3)
    before = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--viewer-font-size')")
    page.locator('button[aria-label="Larger font"]').click()
    time.sleep(0.2)
    after = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--viewer-font-size')")
    page.click('button[title="Settings"]')
    check("font_size_setting", before.strip() != after.strip(), f"{before} -> {after}")

    # --- #7: light theme viewer surface is white ---
    page.click('button[title="Settings"]')
    time.sleep(0.3)
    page.locator('input[name="theme"][value="light"]').check()
    time.sleep(0.3)
    page.click('button[title="Settings"]')
    bg = page.evaluate("() => getComputedStyle(document.querySelector('.viewer')).backgroundColor")
    check("light_viewer_white", bg in ("rgb(255, 255, 255)", "#ffffff"), bg)
    # back to system
    page.click('button[title="Settings"]')
    page.locator('input[name="theme"][value="system"]').check()
    page.click('button[title="Settings"]')

    # --- #2: active tab has accent styling ---
    open_file("README.md")
    styled = page.evaluate("""() => {
      const el = document.querySelector('.file-tab.active');
      return el && getComputedStyle(el, '::after').content !== 'none';
    }""")
    check("active_tab_accent", bool(styled))

print(json.dumps(results, indent=1, ensure_ascii=False))
print("VERDICT:", "PASS" if not FAIL else f"FAIL ({len(FAIL)}): {FAIL}")
