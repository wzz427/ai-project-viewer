# -*- coding: utf-8 -*-
"""Attach to a RUNNING AI Project Viewer instance (the owner's client or a
stray dev build) and dump its live state — owner 2026-10-12: "你应该有一种
机制,能够直接获取到我在本地打开的这个软件里面的信息".

READ-ONLY by construction: never launches, never kills, never focuses,
never writes. Connects to the app's fixed localhost CDP port (9322, dev &
experience builds; see lib.rs run()) and calls window.__aiv.snapshot()
(0.7.12+) plus a DOM trio read. On pre-0.7.12 builds the hook is missing
and we fall back to DOM-only.

Usage: pywork python scripts\\e2e\\live-inspect.py [--port 9322]
"""
import argparse
import json

from playwright.sync_api import sync_playwright


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9322)
    args = ap.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(
            f"http://127.0.0.1:{args.port}")
        pages = browser.contexts[0].pages
        print(f"attached: {len(pages)} page(s)")
        page = pages[0]
        snap = None
        try:
            snap = page.evaluate("() => window.__aiv && window.__aiv.snapshot()")
        except Exception as e:
            print(f"snapshot() failed: {e}")
        if snap:
            print(json.dumps(snap, indent=1, ensure_ascii=False))
        else:
            print("no __aiv hook (pre-0.7.12 build) — DOM only:")
            print(json.dumps(page.evaluate(
                "() => ({"
                " rel: document.querySelector('.viewer-body [data-rel]')"
                "?.getAttribute('data-rel') ?? null,"
                " active: document.querySelector('.file-tab.active .name')"
                "?.textContent ?? null})"), indent=1, ensure_ascii=False))
        browser.close()


if __name__ == "__main__":
    main()
