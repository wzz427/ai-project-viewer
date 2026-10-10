# -*- coding: utf-8 -*-
"""Phase 7 Git review suite (spec-007 V5-V10; zero disturbance).

Three isolated instances against one generated fixture (V1.5 §174):
  A. BigRepo root        — normal repo mode (badge = whole-repo unique).
  B. BigRepo\\apps\\viewer — subdirectory scope (§174 seven checks).
  C. AIV-TestProject      — non-git project (§152).

The fixture is rebuilt from scratch each run under %TEMP%\\aiv-p7-gitscope
(deterministic letters/counts; nothing on the owner's desktop is touched).
All launch/kill handling goes through aivlaunch (owner isolation).
"""
import json
import os
import shutil
import subprocess
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "src-tauri", "target", "release", "ai-project-viewer.exe"))
PLAIN = os.path.expandvars(r"%USERPROFILE%\Desktop\AIV-TestProject")
SCOPE_ROOT = os.path.join(os.environ["TEMP"], "aiv-p7-gitscope")
BIG = os.path.join(SCOPE_ROOT, "BigRepo")
VIEWER = os.path.join(BIG, "apps", "viewer")

results = {}
FAIL = []


def check(name, ok, detail=""):
    results[name] = "PASS" if ok else f"FAIL {detail}"
    if not ok:
        FAIL.append(name)


def sh(cwd, *args):
    r = subprocess.run(["git", "-C", str(cwd), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {args} failed: {r.stderr.strip()}")


def wf(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def rmrf(path):
    """rmtree that clears git's read-only object files first."""
    def onexc(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)
    if os.path.exists(path):
        shutil.rmtree(path, onexc=onexc)


def build_fixture():
    rmrf(SCOPE_ROOT)
    os.makedirs(os.path.join(BIG, "apps", "viewer"))
    os.makedirs(os.path.join(BIG, "apps", "backend"))
    os.makedirs(os.path.join(BIG, "packages"))
    sh(BIG, "init", "-q", "-b", "main")
    sh(BIG, "config", "user.email", "t@example.com")
    sh(BIG, "config", "user.name", "T")

    def w(rel, content):
        wf(os.path.join(BIG, *rel.split("/")), content)

    # history: seed -> viewer change -> backend change
    w("apps/viewer/a.ts", "1\n")
    w("apps/viewer/both.ts", "base\n")
    w("apps/viewer/big-change.ts",
      "".join(f"line {i}\n" for i in range(30_000)))
    w("apps/backend/b.ts", "1\n")
    w("packages/c.ts", "1\n")
    sh(BIG, "add", "-A")
    sh(BIG, "commit", "-q", "-m", "seed")
    w("apps/viewer/a.ts", "2\n")
    sh(BIG, "add", "-A")
    sh(BIG, "commit", "-q", "-m", "viewer change")
    w("apps/backend/b.ts", "2\n")
    sh(BIG, "add", "-A")
    sh(BIG, "commit", "-q", "-m", "backend change")

    # working-tree state (what the suite asserts against):
    #   viewer scope = a.ts(M) staged.ts(A staged) both.ts(M+M)
    #                  untracked.ts(?) big-change.ts(M)   -> 5 unique
    #   outside scope = b.ts(M) c.ts(M)                   -> +2 at repo root
    w("apps/viewer/a.ts", "3\n")
    w("apps/backend/b.ts", "3\n")
    w("packages/c.ts", "3\n")
    w("apps/viewer/staged.ts", "staged content\n")
    sh(BIG, "add", "apps/viewer/staged.ts")
    w("apps/viewer/both.ts", "staged edit\n")
    sh(BIG, "add", "apps/viewer/both.ts")
    w("apps/viewer/both.ts", "staged edit\nworktree edit\n")
    w("apps/viewer/untracked.ts", "untracked\n")
    w("apps/viewer/big-change.ts",
      "".join(f"changed {i}\n" for i in range(30_000)))


def connect(p, port):
    for _ in range(60):
        try:
            return p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"CDP {port}")


def run_instance(project, state, port, fn):
    proc = aivlaunch.launch(EXE, project, state, port)
    try:
        with sync_playwright() as p:
            browser = connect(p, port)
            page = browser.contexts[0].pages[0]
            page.wait_for_selector(".file-tree", timeout=25000)
            fn(page)
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)


def open_git_panel(page):
    page.locator('.sidebar-header .header-tab', has_text="Git").first.click()
    time.sleep(0.3)


def open_files_panel(page):
    page.locator('.sidebar-header .header-tab', has_text="Files").first.click()
    time.sleep(0.3)


def badge_text(page, timeout_s=15):
    """Poll the sidebar badge into existence (startup scan is async)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        t = page.locator(".sidebar-header .git-badge").first.inner_text() \
            if page.locator(".sidebar-header .git-badge").count() else ""
        if t.strip():
            return t.strip()
        time.sleep(0.4)
    return ""


def badge_becomes(page, expect, timeout_s=10):
    """Wait until the badge shows `expect` (post-refresh assertions must
    not read the pre-refresh value)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        loc = page.locator(".sidebar-header .git-badge")
        t = loc.first.inner_text().strip() if loc.count() else ""
        if t == expect:
            return True
        time.sleep(0.4)
    return False


def entry_paths(page, section_hint):
    """Visible entry paths in the panel (all sections; hint only for logs)."""
    return [e.strip() for e in page.locator(".git-panel .entry .path")
            .all_inner_texts()]


def wait_git_panel(page, timeout_s=15):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        txt = page.locator(".sidebar-panel").inner_text()
        if "CHANGES" in txt or "not a Git repository" in txt \
                or "not installed" in txt:
            return txt
        time.sleep(0.4)
    return page.locator(".sidebar-panel").inner_text()


def expand(page, folder):
    row = page.locator(
        ".file-tree .row",
        has=page.locator(".name", has_text=folder)).first
    if row.get_attribute("aria-expanded") != "true":
        row.click()
        time.sleep(0.6)


# --------------------------------------------------------------------------
# Instance A: BigRepo root — normal repo mode.

def instance_a(page):
    # V9 startup/Project-Open trigger is proven by the badge appearing.
    badge = badge_text(page)
    check("git_badge_whole_repo", badge == "[7]", f"badge={badge!r}")

    open_git_panel(page)
    panel = wait_git_panel(page)
    check("git_branch_row", "main" in panel, panel[:80])
    check("git_no_upstream_arrows", "↑" not in panel and "↓" not in panel)
    check("git_normal_mode_no_scope_box",
          page.locator(".git-panel .scope-box").count() == 0)

    paths = entry_paths(page, "A")
    check("git_changes_rows_root",
          all(p in paths for p in (
              "apps/viewer/a.ts", "apps/backend/b.ts",
              "packages/c.ts", "apps/viewer/untracked.ts")),
          str(paths))
    # §53: both.ts sits in BOTH groups.
    staged_txt = page.locator(".git-panel section", has_text="STAGED") \
        .first.inner_text()
    changes_txt = page.locator(".git-panel section", has_text="CHANGES") \
        .filter(has_not_text="STAGED").first.inner_text()
    check("git_same_file_two_groups",
          "apps/viewer/both.ts" in staged_txt
          and "apps/viewer/both.ts" in changes_txt
          and badge == "[7]",  # counted ONCE (not 8)
          f"staged={staged_txt!r} changes={changes_txt!r}")

    # V6: clicking a CHANGES row opens the working-tree diff in the viewer.
    page.locator(".git-panel .entry", has_text="apps/viewer/a.ts").first.click()
    time.sleep(1.0)
    head = page.locator(".diff-viewer .diff-head").inner_text()
    adds = page.locator(".diff-viewer .diff-line.add").count()
    dels = page.locator(".diff-viewer .diff-line.del").count()
    check("git_click_changes_opens_wt_diff",
          page.locator(".diff-viewer").count() == 1
          and "Working Tree" in head and adds > 0 and dels > 0,
          f"head={head!r} +{adds} -{dels}")

    # V6: STAGED row -> staged diff for the same file (scope the locator to
    # the staged section — both.ts also exists in CHANGES).
    staged_section = page.locator(
        ".git-panel section", has_text="STAGED").first
    staged_section.locator(".entry", has_text="apps/viewer/both.ts").click()
    time.sleep(1.0)
    head = page.locator(".diff-viewer .diff-head").inner_text()
    check("git_click_staged_opens_staged_diff",
          "Staged" in head
          and page.locator(".diff-viewer .diff-line.add").count() > 0,
          head)

    # V6: close returns to the previous viewer.
    page.locator(".diff-viewer .close").click()
    time.sleep(0.4)
    check("git_diff_close_returns",
          page.locator(".diff-viewer").count() == 0)

    # V6/D2: untracked row opens the FILE, not a diff.
    page.locator(".git-panel .entry",
                 has_text="apps/viewer/untracked.ts").first.click()
    deadline = time.time() + 6
    ok = False
    while time.time() < deadline:
        if page.locator(".file-tab.active", has_text="untracked.ts").count():
            ok = page.locator(".diff-viewer").count() == 0
            break
        time.sleep(0.2)
    check("git_untracked_opens_file", ok)

    # V8: oversized diff -> §72 message + hand-off button (never clicked).
    page.locator(".git-panel .entry",
                 has_text="apps/viewer/big-change.ts").first.click()
    time.sleep(1.5)
    too = page.locator(".diff-viewer .too-large")
    check("git_diff_guard_too_large",
          too.count() == 1 and "too large" in too.inner_text().lower()
          and page.locator(".diff-viewer .too-large button",
                           has_text="Open in VS Code").count() == 1)
    page.locator(".diff-viewer .close").click()

    # V10: letters on FILE rows only (folders never aggregate, §47/§48).
    open_files_panel(page)
    expand(page, "apps")
    expand(page, "viewer")
    mark = page.evaluate(r"""() => {
      const rows = [...document.querySelectorAll('.file-tree .row')];
      const file = rows.find(r => r.title === 'apps/viewer/a.ts');
      const folder = rows.find(r => r.title === 'apps');
      const mark = el => el ? (el.querySelector('.git-mark')||{}).textContent : null;
      return { file: mark(file), folder: mark(folder) };
    }""")
    check("git_tree_marks_files_only",
          mark["file"] == "M" and mark["folder"] is None, str(mark))

    # V9/V10: manual refresh — disk change lands after ↻ (and reverts).
    probe = os.path.join(BIG, "zz-git-probe.txt")
    try:
        wf(probe, "probe\n")
        page.locator(".sidebar-header .refresh").click()
        ok_add = badge_becomes(page, "[8]")
        check("git_manual_refresh_updates_badge", ok_add,
              f"badge after probe={badge_text(page, timeout_s=2)!r}")
        os.remove(probe)
        page.locator(".sidebar-header .refresh").click()
        check("git_manual_refresh_reverts", badge_becomes(page, "[7]"),
              f"badge after revert={badge_text(page, timeout_s=2)!r}")
    finally:
        if os.path.exists(probe):
            os.remove(probe)


# --------------------------------------------------------------------------
# Instance B: BigRepo\apps\viewer — subdirectory scope (§174).

def instance_b(page):
    badge = badge_text(page)
    check("git_scope_badge_counts_scope_only", badge == "[5]",
          f"badge={badge!r}")

    tab_state = page.locator(".project-tabs .tab .git-state").first \
        .inner_text().strip()
    check("git_scope_tab_indicator_dirty", tab_state == "●", tab_state)

    open_git_panel(page)
    panel = wait_git_panel(page)
    box = page.locator(".git-panel .scope-box").inner_text()
    check("git_scope_box_shows_repo_and_scope",
          "BigRepo" in box and "apps/viewer" in box, box)
    check("git_scope_branch_repo_wide", "main" in panel, panel[:60])

    paths = entry_paths(page, "B")
    check("git_scope_changes_excluded_outside",
          "a.ts" in paths and "untracked.ts" in paths
          and not any("backend" in p or "packages" in p for p in paths),
          str(paths))

    commits = page.locator(".git-panel .commit").all_inner_texts()
    check("git_scope_commits_scoped",
          any("viewer change" in c for c in commits)
          and any("seed" in c for c in commits)
          and not any("backend change" in c for c in commits),
          " | ".join(commits[:5]))

    open_files_panel(page)
    mark = page.evaluate(r"""() => {
      const rows = [...document.querySelectorAll('.file-tree .row')];
      const file = rows.find(r => r.title === 'a.ts');
      return file ? (file.querySelector('.git-mark')||{}).textContent : null;
    }""")
    check("git_scope_tree_marks", mark == "M", str(mark))


# --------------------------------------------------------------------------
# Instance C: AIV-TestProject — non-git project (§152).

def instance_c(page):
    open_git_panel(page)
    txt = wait_git_panel(page)
    check("git_non_git_message",
          "This folder is not a Git repository." in txt, txt[:80])
    time.sleep(1.5)  # beyond the debounce: nothing should ever appear
    check("git_non_git_no_badge",
          page.locator(".sidebar-header .git-badge").count() == 0)
    check("git_non_git_no_tab_indicator",
          page.locator(".project-tabs .tab .git-state").count() == 0)


def main():
    build_fixture()
    run_instance(BIG, os.path.join(os.environ["TEMP"], "aiv-p7git-a.json"),
                 9261, instance_a)
    run_instance(VIEWER, os.path.join(os.environ["TEMP"], "aiv-p7git-b.json"),
                 9262, instance_b)
    if os.path.isdir(PLAIN):
        run_instance(PLAIN, os.path.join(os.environ["TEMP"], "aiv-p7git-c.json"),
                     9263, instance_c)
    else:
        check("git_non_git_message", False, f"{PLAIN} missing")
    print(json.dumps(results, indent=1, ensure_ascii=False))
    if FAIL:
        raise SystemExit(f"FAILED: {FAIL}")


if __name__ == "__main__":
    main()
