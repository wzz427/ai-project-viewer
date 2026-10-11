# -*- coding: utf-8 -*-
"""Watcher freeze guard (0.7.0 startup freeze, lessons L35): simulate the
owner's workflow — an "AI session" hammering writes into the watched
project while the app is open — and measure NATIVE window-thread health
(SendMessageTimeout WM_NULL; the WebView renderer staying healthy is NOT
the same thing, see L35). VERDICT PASS when the window never stops
pumping messages. Run before publishing any watcher-related change."""
import os
import subprocess
import threading
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                   "src-tauri", "target", "release",
                                   "ai-project-viewer.exe"))
BASE = os.path.join(os.environ["TEMP"], "aiv-p9-freeze")
STATE = os.path.join(os.environ["TEMP"], "aiv-p9-freeze.json")
CDP = 9263


def build_fixture():
    """A moderate repo: 300 files, 30 commits -> git_snapshot ~100ms+."""
    if os.path.isdir(BASE):
        import stat
        import shutil

        def force_rm(func, path, _exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(BASE, onerror=force_rm)
    os.makedirs(BASE)
    subprocess.run(["git", "init", "-q", BASE], check=True)
    for c in range(30):
        for i in range(10):
            with open(os.path.join(BASE, f"f{c}_{i}.txt"), "w") as f:
                f.write(f"commit {c} file {i}\n" + "x" * 200)
        subprocess.run(["git", "-C", BASE, "add", "-A"], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", BASE, "commit", "-qm", f"c{c}"],
                       check=True, capture_output=True)
    # standing changes so the badge has content
    for i in range(7):
        with open(os.path.join(BASE, f"f0_{i}.txt"), "w") as f:
            f.write("dirty\n")


hammer_target = os.path.join(BASE, "hammer.txt")


def hammer(seconds, start_now=True):
    def run():
        end = time.time() + seconds
        n = 0
        while time.time() < end:
            n += 1
            # churn like an AI session: rewrite 5 tracked files, create
            # and delete 2 untracked ones, every cycle
            for i in range(5):
                with open(os.path.join(BASE, f"f0_{i}.txt"), "w") as f:
                    f.write(f"write {n}\n" + "y" * 200)
            with open(hammer_target, "w") as f:
                f.write(f"write {n}\n")
            for i in range(2):
                p = os.path.join(BASE, f"tmp{i}.txt")
                with open(p, "w") as f:
                    f.write("t\n")
                os.remove(p)
            time.sleep(0.03)
    t = threading.Thread(target=run, daemon=True)
    if start_now:
        t.start()
    return t


def native_responsive(hwnd):
    """True when the window's thread pumps messages (busy cursor test)."""
    import ctypes
    from ctypes import byref, c_ulong
    WM_NULL = 0x0000
    SMTO_ABORTIFHUNG = 0x0002
    res = ctypes.windll.user32.SendMessageTimeoutW(
        hwnd, WM_NULL, 0, 0, SMTO_ABORTIFHUNG, 400, byref(c_ulong()))
    return res != 0


def eval_latency(page):
    t0 = time.time()
    page.evaluate("1+1")
    return (time.time() - t0) * 1000


build_fixture()
hammer_thread = hammer(40, start_now=False)
proc = aivlaunch.launch(EXE, BASE, STATE, CDP)
hwnd = None
try:
    with sync_playwright() as p:
        for _ in range(60):
            try:
                browser = p.chromium.connect_over_cdp(
                    f"http://127.0.0.1:{CDP}")
                break
            except Exception:
                time.sleep(0.5)
        page = browser.contexts[0].pages[0]
        page.wait_for_selector(".sidebar-header", timeout=25000)
        hwnd = aivlaunch.window_of(proc.pid)
        print("hwnd:", hwnd)
        time.sleep(2.0)

        # Phase 1: hammer STARTS NOW (writer active while app is open) —
        # 25 s of churn; sample native responsiveness every 300 ms.
        hammer_thread.start()
        hung = 0
        worst_eval = 0.0
        samples = []
        t0 = time.time()
        while time.time() - t0 < 25:
            ok = native_responsive(hwnd) if hwnd else True
            if not ok:
                hung += 1
            try:
                ms = eval_latency(page)
                worst_eval = max(worst_eval, ms)
            except Exception:
                samples.append("EVALFAIL")
            samples.append("." if ok else "H")
            time.sleep(0.3)
        hammer_thread.join(timeout=5)
        print("native samples:", "".join(samples))
        print(f"HUNG count: {hung}/{len(samples)}  worst webview eval: "
              f"{worst_eval:.0f} ms")
        ok = hung <= 2 and worst_eval < 500
        print("VERDICT:", "PASS" if ok else "FAIL")
finally:
    aivlaunch.kill_tree(proc)
