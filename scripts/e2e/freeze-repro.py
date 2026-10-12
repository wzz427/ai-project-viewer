# -*- coding: utf-8 -*-
"""Repro attempt v2 for the owner's content-freeze bug (2026-10-12 field).

Field recipe (diagnostics aiv-diagnostics-1791785427): rapid project
switches (~1.2s apart) -> within ~3s open/activate tabs in the final
project -> tab strip moves, viewer content NEVER changes again.

v2 adds the field discriminators v1 lacked:
  - NESTED project roots (his AI-Project-Guide lives INSIDE the
    ProjectViewer repo -> watcher roots overlap and cross-fire),
  - git repos (badge/watcher refresh load),
  - fs churn DURING the rapid switches (watcher batches interleaved with
    rootPath retargeting),
  - boot-restored tabs for a project first activated much later.

Guard gap this exercises (why every suite stayed green while his client
froze): suites assert active-tab name + viewer class; the freeze keeps
both correct while CONTENT stays the last-rendered file. Every activation
here asserts CONTENT IDENTITY via unique marker lines.

Zero disturbance: aivlaunch launch, PID-scoped kills, offscreen parking.
Run:  pywork python scripts\\e2e\\freeze-repro.py [--rounds 30]
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aivlaunch  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

EXE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "src-tauri", "target", "release", "ai-project-viewer.exe"))
BENCH = os.path.join(os.environ["TEMP"], "aiv-freeze2")
OUTER = os.path.join(BENCH, "fix", "outer")          # project A (git)
INNER = os.path.join(OUTER, "sub", "inner")          # project B, NESTED in A
P3 = os.path.join(BENCH, "fix", "p3")                # project C (git)


def wf(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def sh(cwd, *args):
    r = subprocess.run(["git", "-C", str(cwd), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {args}: {r.stderr.strip()}")


def build_fixtures():
    if os.path.isdir(BENCH):
        return
    for name, files in [(OUTER, ["o1.md", "o2.md", "o3.md"]),
                        (INNER, ["i1.md", "i2.md", "i3.md"]),
                        (P3, ["c1.md", "c2.md", "c3.md"])]:
        os.makedirs(name, exist_ok=True)
        tag = os.path.basename(name) if name != INNER else "inner"
        for fn in files:
            n = fn[1]
            wf(os.path.join(name, fn),
               f"# {tag}{n} marker-{tag}-{n}\n\n" + f"body {tag} {n}\n" * 30)
    for repo in (OUTER, P3):
        sh(repo, "init", "-q", "-b", "main")
        sh(repo, "config", "user.email", "b@example.com")
        sh(repo, "config", "user.name", "B")
        sh(repo, "add", "-A")
        sh(repo, "commit", "-q", "-m", "seed")


def seed_state():
    projects = []
    for pid, root, tabs in [("fr-A", OUTER, ("o1.md", "o2.md")),
                            ("fr-B", INNER, ("i1.md", "i2.md")),
                            ("fr-C", P3, ("c1.md", "c2.md"))]:
        projects.append({
            "id": pid, "name": os.path.basename(root), "rootPath": root,
            "expandedFolders": [], "sidebarMode": "files",
            "sidebarWidth": 260, "trustedForExecution": False,
            "fileTreePreferences": {"foldersFirst": True, "pinnedItems": {}},
            "openFiles": [{"relativePath": t, "viewerType": "markdown"}
                          for t in tabs],
            "activeFileRelativePath": tabs[0],
        })
    state = {"version": 1, "projects": projects, "activeProjectId": "fr-A",
             "settings": {"theme": "system", "viewer": {"fontSize": 13},
                          "fileTree": {"showSystemGeneratedFolders": False}},
             "recentFolders": []}
    path = os.path.join(BENCH, "state.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f)
    return path


def viewer_state(page):
    return page.evaluate(
        "() => ({"
        "  active: document.querySelector('.file-tab.active .name')?.innerText ?? null,"
        "  body: (document.querySelector('.viewer-body')?.innerText ?? '').slice(0, 300)"
        "})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=30)
    args = ap.parse_args()
    build_fixtures()
    state = seed_state()
    port = 9378
    proc = aivlaunch.launch(EXE, OUTER, state, port, keep_state=True)
    _hwnd = aivlaunch.window_of(proc.pid)
    if _hwnd:
        aivlaunch.park_offscreen(_hwnd)
    frozen = None
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
            time.sleep(2)
            assert "marker-outer-1" in viewer_state(page)["body"], "baseline"
            print("baseline OK (outer/o1 visible)")

            def assert_content(label, marker):
                nonlocal frozen
                st = viewer_state(page)
                if marker not in st["body"]:
                    frozen = (label, marker, st)
                    print(f"FROZEN [{label}]: want {marker}, "
                          f"active={st['active']!r}, body={st['body'][:90]!r}")
                    return False
                return True

            for rnd in range(args.rounds):
                # fs churn interleaved with the rapid switches (every 2nd
                # round): writes inside the nested root while outer is
                # (in)active -> overlapping watcher roots cross-fire.
                churn = rnd % 2 == 0
                # rapid switches mirroring the field: A -> C -> B (~1.2s)
                for pid, name in (("fr-C", "p3"), ("fr-B", "inner")):
                    page.locator(".project-tabs .tab",
                                 has_text=name).first.click()
                    time.sleep(1.2)
                    if churn and pid == "fr-C":
                        with open(os.path.join(INNER, "i2.md"), "a",
                                  encoding="utf-8") as f:
                            f.write(f"\nchurn {rnd}\n")
                        with open(os.path.join(OUTER, "o2.md"), "a",
                                  encoding="utf-8") as f:
                            f.write(f"\nchurn {rnd}\n")
                # final project = B (nested); owner waited ~2s
                time.sleep(2)
                new_f = "i3.md" if rnd % 2 == 0 else "i1.md"
                page.wait_for_selector(
                    f"div.row[role='treeitem'] :text-is('{new_f}')")
                page.click(f"div.row[role='treeitem'] :text-is('{new_f}')")
                time.sleep(1.0)
                if not assert_content(f"r{rnd} open {new_f}",
                                      f"marker-inner-{new_f[1]}"):
                    break
                other = "i1.md" if new_f == "i3.md" else "i2.md"
                page.locator(".file-tab", has_text=other).first.click()
                time.sleep(1.0)
                if not assert_content(f"r{rnd} act {other}",
                                      f"marker-inner-{other[1]}"):
                    break
                print(f"round {rnd}: OK ({'churn ' if churn else ''}"
                      f"{new_f} + {other})")
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)
    if frozen:
        raise SystemExit("REPRODUCED — see output above")
    print(f"\nNo freeze in {args.rounds} rounds "
          "(nested roots + git + churn + rapid switches)")


if __name__ == "__main__":
    main()
