# -*- coding: utf-8 -*-
"""MANUAL-ONLY live check for Phase 8 Run (spec-008 D9, V2 visibility).

Unlike the zero-disturbance suites, this one deliberately opens a REAL,
VISIBLE console window on this machine via the shipped product path:
  fresh launch -> project menu "Trust Project for Execution" ->
  tree right-click -> Run Script -> Rust spawn_visible(cmd /K hello.bat,
  CREATE_NEW_CONSOLE). It verifies the §117 contract end-to-end (console
  window exists, script body runs, host stays alive = output readable),
  plus the §129 trust-menu toggle, then kills ITS OWN instance tree
  (PID-scoped, aivlaunch) — the owner's client is never touched.
Run by hand when touching run.rs; never wire into routine rounds.

  pywork python scripts/e2e/run-live-check.py
"""
import json
import os
import subprocess
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = os.path.join(os.path.dirname(__file__), "..", "..",
                   "src-tauri", "target", "release", "ai-project-viewer.exe")
PROJECT = os.path.expandvars(r"%USERPROFILE%\Desktop\AIV-TestProject")
STATE = os.path.join(os.environ["TEMP"], "aiv-p8-live.json")
MARKER = os.path.join(os.environ["TEMP"], "aiv-p8-live-marker.txt")
CDP = 9269
SCRIPT_REL = "hello.bat"  # echo-only fixture at the project root

if os.path.exists(MARKER):
    os.remove(MARKER)

# The fixture script must write the marker so "body finished" is provable.
with open(os.path.join(PROJECT, SCRIPT_REL), "w", newline="") as f:
    f.write("@echo off\r\n")
    f.write("echo [run-live-check] hello.bat running\r\n")
    f.write("echo done> \"%s\"\r\n" % MARKER)


def top_windows():
    """All processes with a visible top-level window (id, name, title)."""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
         "Get-Process | Where-Object {$_.MainWindowHandle -ne 0} | "
         "Select-Object Id,ProcessName,MainWindowTitle | ConvertTo-Json -Compress"],
        capture_output=True)
    arr = json.loads(r.stdout.decode("utf-8", "replace"))
    if isinstance(arr, dict):
        arr = [arr]
    return {(p_["Id"], p_["ProcessName"], p_["MainWindowTitle"]) for p_ in arr}


def console_delta(before, after):
    """New terminal-host windows among the before/after delta."""
    hosts = {"WindowsTerminal", "conhost", "OpenConsole"}
    return {w for w in after - before if w[1] in hosts}


proc = aivlaunch.launch(os.path.abspath(EXE), PROJECT, STATE, CDP)
try:
    with sync_playwright() as p:
        for _ in range(60):
            try:
                browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
                break
            except Exception:
                time.sleep(0.5)
        page = browser.contexts[0].pages[0]
        page.wait_for_selector(".file-tree", timeout=25000)

        # §129: trust via the project menu (the real owner flow — no
        # pre-seeded state; aivlaunch guarantees a fresh one anyway).
        page.locator(".project-tabs .tab").first.click(button="right")
        page.wait_for_selector(".menu [data-menu-id='trust-project']", timeout=4000)
        page.locator(".menu [data-menu-id='trust-project']").dispatch_event("click")
        time.sleep(0.8)
        # ground truth: the label must flip to the untrust form
        page.locator(".project-tabs .tab").first.click(button="right")
        page.wait_for_selector(".menu [data-menu-id]", timeout=4000)
        ids = page.eval_on_selector_all(
            ".menu [data-menu-id]", "els => els.map(e => e.dataset.menuId)")
        page.mouse.click(400, 250)
        trusted_ok = "untrust-project" in ids

        # §116/§137: right-click Run Script on the echo-only fixture.
        # Window attribution = system-wide before/after delta: with Windows
        # Terminal as the default console host, the visible console belongs
        # to WindowsTerminal.exe, which is NOT a descendant of the app.
        before = top_windows()
        page.locator(f'.file-tree .row[title="{SCRIPT_REL}"]').first \
            .click(button="right")
        page.wait_for_selector(".menu [data-menu-id='run-script']", timeout=4000)
        page.locator(".menu [data-menu-id='run-script']").dispatch_event("click")

        # Console must appear, body must finish, console must STAY open.
        t0 = time.time()
        console = []
        while time.time() - t0 < 8 and not console:
            console = console_delta(before, top_windows())
            time.sleep(0.4)
        while time.time() - t0 < 15 and not os.path.exists(MARKER):
            time.sleep(0.4)
        time.sleep(2.5)  # body long done — is the console still open?
        alive_after = console_delta(before, top_windows())

        ok = trusted_ok and bool(console) and os.path.exists(MARKER) \
            and bool(alive_after)
        print("trust menu flipped to Untrust:", trusted_ok)
        print("console window appeared:", sorted(c[1] for c in console))
        print("marker (script body finished):", os.path.exists(MARKER))
        print("console still open after body:", bool(alive_after))
        print("VERDICT:", "PASS" if ok else "FAIL")
finally:
    aivlaunch.kill_tree(proc)
    if os.path.exists(MARKER):
        os.remove(MARKER)
