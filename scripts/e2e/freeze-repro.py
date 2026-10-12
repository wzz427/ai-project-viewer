# -*- coding: utf-8 -*-
"""Repro attempt v3 for the owner's content-freeze bug (2026-10-12).

v3 mirrors the THIRD field capture (aiv-diagnostics-1791788362) exactly —
that session died 21 SECONDS after boot, so the recipe is fully observed:

  boot: 4 projects restored; boot-ACTIVE project = "factory" (NOT the
        first project in the tab list; first = the nested "guide" target)
  +5s:  two healthy tab-activations inside factory (viewer follows)
  +6s:  rapid project switches: tinker -> factory -> pv (~1.3s apart)
  +10s: idle
  then: switch to guide (nested INSIDE pv's tree) -> render -> click its
        tabs: FIRST click already dead in the field (viewer-rel frozen,
        store + tab strip keep following every click)
  then: spread phase — tab opens/activations in tinker/pv/factory, all
        dead in the field

Assertion after EVERY click/open: the DOM trio must agree —
  .file-tab.active (strip) == expected AND .viewer-body [data-rel] ==
  expected rel AND body text contains the new file's unique marker.
The STRIP moving while data-rel stays is the exact field signature.

Zero disturbance: aivlaunch launch, PID-scoped kills, offscreen parking.
Run:  pywork python scripts\\e2e\\freeze-repro.py [--rounds 10]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aivlaunch  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

EXE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "src-tauri", "target", "release", "ai-project-viewer.exe"))
BENCH = os.path.join(os.environ["TEMP"], "aiv-freeze3")
PV = os.path.join(BENCH, "pv")                    # outer project (parent)
GUIDE = os.path.join(PV, "docs", "guide")         # nested target project
FACTORY = os.path.join(BENCH, "factory")          # boot-active
TINKER = os.path.join(BENCH, "tinker")


def wf(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def build_fixtures():
    if os.path.isdir(BENCH):
        return
    import subprocess

    def sh(cwd, *args):
        r = subprocess.run(["git", "-C", str(cwd), *args],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"git {args}: {r.stderr.strip()}")
    # guide: 3 root md + 1 in advanced/ (field shape), marker g1..g4
    for i, rel in enumerate(["01.md", "02.md", "03.md",
                             "advanced/04.md"], start=1):
        wf(os.path.join(GUIDE, rel),
           f"# G{i} marker-g{i}\n\n" + f"guide file {i}\n" * 25)
    # pv: docs/* md tabs incl one under docs/ (parent project)
    for i, rel in enumerate(["pyproject.toml", "ARCHITECTURE.md",
                             "docs/revision.md", "docs/testing.md"], start=1):
        wf(os.path.join(PV, rel),
           f"# P{i} marker-p{i}\n\n" + f"pv file {i}\n" * 25)
    # factory: boot-active, two tabs
    for i, rel in enumerate(["README.md", "01-environment.md"], start=1):
        wf(os.path.join(FACTORY, rel),
           f"# F{i} marker-f{i}\n\n" + f"factory file {i}\n" * 25)
    # tinker: two tabs
    for i, rel in enumerate(["list.md", "steps.md"], start=1):
        wf(os.path.join(TINKER, rel),
           f"# T{i} marker-t{i}\n\n" + f"tinker file {i}\n" * 25)
    # v4: the field projects are ALL git repos — every project switch fires
    # refreshGit + badge work (App's project-active effect). v3 had no git
    # and never froze in 21 attempts; the field froze 3-for-3.
    for repo in (PV, GUIDE, FACTORY, TINKER):
        sh(repo, "init", "-q", "-b", "main")
        sh(repo, "config", "user.email", "b@example.com")
        sh(repo, "config", "user.name", "B")
        sh(repo, "add", "-A")
        sh(repo, "commit", "-q", "-m", "seed")


def proj(pid, root, name, tabs, active):
    return {
        "id": pid, "name": name, "rootPath": root,
        "expandedFolders": [], "sidebarMode": "files",
        "sidebarWidth": 260, "trustedForExecution": False,
        "fileTreePreferences": {"foldersFirst": True, "pinnedItems": {}},
        "openFiles": [{"relativePath": t, "viewerType": "markdown"}
                      for t in tabs],
        "activeFileRelativePath": active,
    }


def seed_state():
    # Field order: guide(FIRST, nested), pv(its parent), factory(boot-active
    # — NO, boot active is factory which sits THIRD), tinker.
    state = {
        "version": 1,
        "projects": [
            proj("p-guide", GUIDE, "guide", ["01.md", "02.md", "03.md",
                                             "advanced/04.md"], "02.md"),
            proj("p-pv", PV, "pv", ["pyproject.toml", "ARCHITECTURE.md",
                                    "docs/revision.md", "docs/testing.md"],
                 "docs/testing.md"),
            proj("p-factory", FACTORY, "factory",
                 ["README.md", "01-environment.md"], "README.md"),
            proj("p-tinker", TINKER, "tinker", ["list.md", "steps.md"],
                 "list.md"),
        ],
        "activeProjectId": "p-factory",
        "settings": {"theme": "system", "viewer": {"fontSize": 13},
                     "fileTree": {"showSystemGeneratedFolders": False}},
        "recentFolders": [],
    }
    path = os.path.join(BENCH, "state.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=10)
    args = ap.parse_args()
    build_fixtures()
    state = seed_state()
    port = 9379
    results = []
    for rnd in range(args.rounds):
        r = run_round(rnd, state, port)
        results.append(r)
        if r == "FROZEN":
            break
        print(f"round {rnd}: alive")
    frozen = [i for i, r in enumerate(results) if r == "FROZEN"]
    if frozen:
        raise SystemExit(f"REPRODUCED at round {frozen[0]}")
    print(f"\nNo freeze in {len(results)} full-recipe rounds")


def run_round(rnd, state, port):
    proc = aivlaunch.launch(EXE, FACTORY, state, port, keep_state=True)
    _hwnd = aivlaunch.window_of(proc.pid)
    if _hwnd:
        aivlaunch.park_offscreen(_hwnd)
    try:
        with sync_playwright() as p:
            browser = None
            for _ in range(80):
                try:
                    browser = p.chromium.connect_over_cdp(
                        f"http://127.0.0.1:{port}")
                    break
                except Exception:
                    time.sleep(0.5)
            page = browser.contexts[0].pages[0]
            page.wait_for_selector(".file-tree", timeout=25000)

            def dom():
                return page.evaluate(
                    "() => ({"
                    " rel: document.querySelector('.viewer-body [data-rel]')"
                    "?.getAttribute('data-rel') ?? null,"
                    " active: document.querySelector('.file-tab.active .name')"
                    "?.innerText ?? null,"
                    " body: (document.querySelector('.viewer-body')"
                    "?.innerText ?? '').slice(0, 120)})")

            def click_tab(name):
                page.locator(".file-tab", has_text=name).first.click()

            def switch_project(name):
                page.locator(".project-tabs .tab",
                             has_text=name).first.click()

            def check(label, rel, marker, wait=0.9):
                time.sleep(wait)
                d = dom()
                ok = (d["rel"] == rel and marker in d["body"])
                if not ok:
                    print(f"FROZEN [{label}]: want rel={rel} marker={marker}"
                          f" | got rel={d['rel']!r} active={d['active']!r}"
                          f" body={d['body']!r}")
                return ok

            # --- field sequence ---
            time.sleep(4)                                  # boot settle
            assert check("boot factory", "README.md", "marker-f1"), "boot"
            click_tab("01-environment.md")                  # healthy phase
            assert check("factory healthy", "01-environment.md",
                         "marker-f2"), "healthy1"
            click_tab("README.md")
            assert check("factory healthy 2", "README.md", "marker-f1")
            # rapid switches: tinker -> factory -> pv
            switch_project("tinker"); time.sleep(1.3)
            switch_project("factory"); time.sleep(1.3)
            switch_project("pv");     time.sleep(1.3)
            time.sleep(10)                                  # idle gap
            # switch to the nested target
            switch_project("guide")
            assert check("guide render", "02.md", "marker-g2", wait=1.5)
            # the first post-switch click was already dead in the field
            if not check("guide click1", "01.md", "marker-g1"):
                browser.close()
                return "FROZEN"
            click_tab("03.md")
            if not check("guide click2", "03.md", "marker-g3"):
                browser.close()
                return "FROZEN"
            click_tab("04.md")          # the advanced/ subfolder tab
            if not check("guide click3", "advanced/04.md", "marker-g4"):
                browser.close()
                return "FROZEN"
            # --- spread phase: other projects must keep working ---
            switch_project("tinker")
            if not check("spread tinker", "list.md", "marker-t1"):
                browser.close()
                return "FROZEN(spread-tinker)"
            click_tab("steps.md")
            if not check("spread tinker click", "steps.md", "marker-t2"):
                browser.close()
                return "FROZEN(spread-tinker-click)"
            switch_project("pv")
            click_tab("ARCHITECTURE.md")
            if not check("spread pv click", "ARCHITECTURE.md", "marker-p2"):
                browser.close()
                return "FROZEN(spread-pv)"
            browser.close()
            return "alive"
    finally:
        aivlaunch.kill_tree(proc)


if __name__ == "__main__":
    main()
