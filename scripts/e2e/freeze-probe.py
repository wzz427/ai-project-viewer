# -*- coding: utf-8 -*-
"""Loop the field recipe until the freeze manifests, then dissect the LIVE
frozen instance (console capture, DOM dumps, JS dispatch click, project
round-trip = store truth probe). The recipe is nondeterministic (race) —
v3 round 0 froze, an identical probe round lived.

Run: pywork python scripts\\e2e\\freeze-probe.py [--attempts 20]
"""
import argparse
import importlib.util
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aivlaunch  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "freeze_repro", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "freeze-repro.py"))
fr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fr)

PORT = 9381

# A/B knobs: --exe launches a specific binary (default = the repo's current
# dev build); --fast amplifies the race (tighter switch/click cadence).
APEX = os.environ.get("FREEZE_PROBE_EXE")
FAST = os.environ.get("FREEZE_PROBE_FAST") == "1"


def attempt(page):
    """One field recipe; returns True if FROZEN at the guide click."""
    gap = 0.35 if FAST else 1.3
    idle = 2.0 if FAST else 10.0
    cadence = 0.5 if FAST else 0.8

    def dom():
        return page.evaluate(
            "() => ({"
            " rel: document.querySelector('.viewer-body [data-rel]')"
            "?.getAttribute('data-rel') ?? null,"
            " active: document.querySelector('.file-tab.active .name')"
            "?.innerText ?? null,"
            " tabs: [...document.querySelectorAll('.file-tab')]"
            ".map(e => e.querySelector('.name')?.innerText"
            " + (e.classList.contains('active') ? '*' : ''))})")

    page.wait_for_selector(".file-tree", timeout=25000)
    time.sleep(4)
    page.locator(".file-tab", has_text="01-environment.md").first.click()
    time.sleep(0.9)
    page.locator(".file-tab", has_text="README.md").first.click()
    time.sleep(0.9)
    for name in ("tinker", "factory", "pv"):
        page.locator(".project-tabs .tab",
                     has_text=name).first.click()
        time.sleep(gap)
    time.sleep(idle)
    page.locator(".project-tabs .tab", has_text="guide").first.click()
    time.sleep(1.5)
    pre = dom()
    # field cadence: burst clicks across the four tabs
    for name in ("01.md", "03.md", "02.md", "04.md"):
        page.locator(".file-tab", has_text=name).first.click()
        time.sleep(cadence)
    post = dom()
    frozen = post["rel"] != "advanced/04.md"
    return frozen, pre, post


def dissect(page):
    def dom(label):
        d = page.evaluate(
            "() => ({"
            " rel: document.querySelector('.viewer-body [data-rel]')"
            "?.getAttribute('data-rel') ?? null,"
            " active: document.querySelector('.file-tab.active .name')"
            "?.innerText ?? null,"
            " tabs: [...document.querySelectorAll('.file-tab')]"
            ".map(e => e.querySelector('.name')?.innerText"
            " + (e.classList.contains('active') ? '*' : ''))})")
        print(f"{label:38} {d}")
        return d

    frozen_state = dom("FROZEN state")
    # B1: raw JS click on 03.md — is the handler/store alive?
    page.evaluate(
        "() => { const els=[...document.querySelectorAll('.file-tab')];"
        " const el=els.find(e=>e.innerText.includes('03.md'));"
        " el && el.dispatchEvent(new MouseEvent('click',"
        " {bubbles:true, cancelable:true})); }")
    time.sleep(1.0)
    dom("after JS dispatch click 03.md")
    # B2: Playwright click 04.md
    page.locator(".file-tab", has_text="04.md").first.click()
    time.sleep(1.0)
    dom("after Playwright click 04.md")
    # C: project round trip — returning render shows the STORE truth
    page.locator(".project-tabs .tab", has_text="pv").first.click()
    time.sleep(1.5)
    dom("switch to pv")
    page.locator(".project-tabs .tab", has_text="guide").first.click()
    time.sleep(1.5)
    dom("back to guide (store truth)")
    # D: post-round-trip click
    page.locator(".file-tab", has_text="01.md").first.click()
    time.sleep(1.0)
    return dom("click 01.md after round trip")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempts", type=int, default=20)
    args = ap.parse_args()
    fr.build_fixtures()
    state = fr.seed_state()
    for i in range(args.attempts):
        exe = APEX or fr.EXE
        proc = aivlaunch.launch(exe, fr.FACTORY, state, PORT,
                                keep_state=True)
        _hwnd = aivlaunch.window_of(proc.pid)
        if _hwnd:
            aivlaunch.park_offscreen(_hwnd)
        console_msgs = []
        try:
            with sync_playwright() as p:
                browser = None
                for _ in range(80):
                    try:
                        browser = p.chromium.connect_over_cdp(
                            f"http://127.0.0.1:{PORT}")
                        break
                    except Exception:
                        time.sleep(0.5)
                page = browser.contexts[0].pages[0]
                page.on("console", lambda m: console_msgs.append(
                    f"[{m.type}] {m.text[:300]}"))
                page.on("pageerror", lambda e: console_msgs.append(
                    f"[pageerror] {str(e)[:300]}"))
                frozen, pre, post = attempt(page)
                if frozen:
                    print(f"\n=== FROZEN at attempt {i} ===")
                    print(f"pre-click : {pre}")
                    print(f"post-click: {post}")
                    dissect(page)
                    browser.close()
                    print("\nconsole messages this attempt:")
                    for m in console_msgs or ["(none)"]:
                        print(" ", m)
                    raise SystemExit(f"FROZEN at attempt {i}")
                browser.close()
            print(f"attempt {i}: alive")
        finally:
            aivlaunch.kill_tree(proc)
            time.sleep(0.5)
    print(f"no freeze in {args.attempts} attempts")


if __name__ == "__main__":
    main()
