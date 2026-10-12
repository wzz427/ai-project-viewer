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

    # history: seed -> viewer change -> backend change (a.ts keeps 20 lines
    # so the later working diff folds a gap bar in the middle)
    w("apps/viewer/a.ts", "".join(f"line {i}\n" for i in range(1, 21)))
    w("apps/viewer/both.ts", "base\n")
    w("apps/viewer/big-change.ts",
      "".join(f"line {i}\n" for i in range(30_000)))
    w("apps/backend/b.ts", "1\n")
    w("packages/c.ts", "1\n")
    sh(BIG, "add", "-A")
    sh(BIG, "commit", "-q", "-m", "seed")
    w("apps/viewer/a.ts", "CHANGED 1\n" + "".join(f"line {i}\n" for i in range(2, 21)))
    sh(BIG, "add", "-A")
    sh(BIG, "commit", "-q", "-m", "viewer change")
    w("apps/backend/b.ts", "2\n")
    sh(BIG, "add", "-A")
    sh(BIG, "commit", "-q", "-m", "backend change")

    # working-tree state (what the suite asserts against):
    #   viewer scope = a.ts(M) staged.ts(A staged) both.ts(M+M)
    #                  untracked.ts(?) big-change.ts(M)   -> 5 unique
    #   outside scope = b.ts(M) c.ts(M)                   -> +2 at repo root
    w("apps/viewer/a.ts", "CHANGED 1\n" + "".join(
        ("EDITED 15\n" if i == 15 else f"line {i}\n") for i in range(2, 21)))
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
    _hwnd = aivlaunch.window_of(proc.pid)
    if _hwnd:
        aivlaunch.park_offscreen(_hwnd)
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
    """Visible entry paths (row title carries the full project-relative rel)."""
    return page.eval_on_selector_all(
        ".git-panel .entry", "els => els.map(e => e.title)")


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
    # spec-014: badge is an accent pill showing the bare count (was "[7]").
    check("git_badge_whole_repo", badge == "7", f"badge={badge!r}")

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
    # §53: both.ts sits in BOTH groups (row titles carry the full rel).
    staged_titles = page.locator(
        ".git-panel section", has_text="Staged Changes").first \
        .locator(".entry").evaluate_all("els => els.map(e => e.title)")
    changes_titles = page.locator(
        ".git-panel section", has_text="Changes").filter(has_not_text="Staged").first \
        .locator(".entry").evaluate_all("els => els.map(e => e.title)")
    check("git_same_file_two_groups",
          "apps/viewer/both.ts" in staged_titles
          and "apps/viewer/both.ts" in changes_titles
          and badge == "7",  # counted ONCE (not 8)
          f"staged={staged_titles} changes={changes_titles}")

    # V6/D2: untracked row opens the FILE, not a diff.
    page.locator('.git-panel .entry[title="apps/viewer/untracked.ts"]').first.click()
    deadline = time.time() + 6
    ok = False
    while time.time() < deadline:
        if page.locator(".file-tab.active", has_text="untracked.ts").count():
            ok = page.locator(".diff-viewer").count() == 0
            break
        time.sleep(0.2)
    check("git_untracked_opens_file", ok)

    # Rework V6 (owner 2026-10-10): side-by-side, and the file-tab strip
    # must not show a stale tab while the diff owns the viewer.
    page.locator('.git-panel .entry[title="apps/viewer/a.ts"]').first.click()
    time.sleep(1.0)
    head = page.locator(".diff-viewer .diff-head").inner_text()
    adds = page.locator(".diff-viewer .cell.chg.new").count()
    dels = page.locator(".diff-viewer .cell.chg.old").count()
    gap = page.locator(".diff-viewer .gap").first.inner_text()         if page.locator(".diff-viewer .gap").count() else ""
    check("git_click_changes_opens_side_by_side_diff",
          page.locator(".diff-viewer").count() == 1
          and "Working Tree" in head and adds > 0 and dels > 0
          and "unchanged" in gap,
          f"head={head!r} +{adds} -{dels} gap={gap!r}")
    check("git_diff_hides_file_tabs",
          page.locator(".file-tab").count() == 0,
          f"file tabs visible: {page.locator('.file-tab').count()}")

    # V6: STAGED row -> staged diff for the same file (scope the locator to
    # the staged section — both.ts also exists in CHANGES).
    staged_section = page.locator(
        ".git-panel section", has_text="Staged Changes").first
    staged_section.locator('.entry[title="apps/viewer/both.ts"]').click()
    time.sleep(1.0)
    head = page.locator(".diff-viewer .diff-head").inner_text()
    check("git_click_staged_opens_staged_diff",
          "Staged" in head
          and page.locator(".diff-viewer .cell.chg.new").count() > 0,
          head)

    # V6: close restores the file-tab strip and the previous viewer.
    page.locator(".diff-viewer .close").click()
    time.sleep(0.4)
    check("git_diff_close_returns",
          page.locator(".diff-viewer").count() == 0
          and page.locator(".file-tab").count() > 0)

    # 0.6.11 bug (owner 2026-10-10: "切回 Files 后页签全都丢了,显示的
    # 还是 Git 的内容"): leaving the Git panel must close the git view and
    # hand the viewer body back to the file tabs.
    page.locator('.git-panel .entry[title="apps/viewer/a.ts"]').first.click()
    time.sleep(1.0)
    diff_was_up = page.locator(".diff-viewer").count() == 1
    open_files_panel(page)
    time.sleep(0.4)
    check("git_return_to_files_restores_tabs",
          diff_was_up
          and page.locator(".diff-viewer").count() == 0
          and page.locator(".file-tab").count() > 0
          and page.locator(".file-tab.active").count() == 1
          and page.locator(".code-host").count() >= 1)
    open_git_panel(page)  # re-entry keeps working for the checks below

    # V8: oversized diff -> §72 message + hand-off button (never clicked).
    page.locator('.git-panel .entry[title="apps/viewer/big-change.ts"]').first.click()
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

    # Rework V10: rows show bright filename + dim dirname (VS Code pattern).
    open_git_panel(page)
    row = page.locator('.git-panel .entry[title="apps/viewer/a.ts"]').first
    nm = row.locator(".ename").inner_text()
    dr = row.locator(".edir").inner_text()
    lt = row.locator(".letter").inner_text()
    check("git_entry_name_dir_letter_split",
          nm == "a.ts" and dr == "apps/viewer" and lt == "M",
          f"name={nm!r} dir={dr!r} letter={lt!r}")

    # Rework V2: clicking a commit opens the detail view (author/date/
    # message/files); a file there drills into that commit's diff with a
    # back arrow.
    when = page.locator(".git-panel .commit .cwhen").first.inner_text()
    check("git_commit_time_unit_fixed", "56y" not in when, when)
    # Second row = "viewer change" (the newest commit only touched backend).
    page.locator(".git-panel .commit").nth(1).click()
    time.sleep(1.2)
    cv = page.locator(".commit-view").count() == 1
    body = page.locator(".commit-view .c-body").inner_text()
    check("git_commit_click_opens_detail",
          cv and "Author" in body and "Hash" in body
          and "FILES CHANGED" in body and "viewer change" in body
          and page.locator(".file-tab").count() == 0,
          body[:120])
    page.locator('.commit-view .entry[title="apps/viewer/a.ts"]').first.click()
    time.sleep(1.2)
    head = page.locator(".diff-viewer .diff-head").inner_text()
    check("git_commit_file_drills_into_diff",
          page.locator(".diff-viewer").count() == 1
          and page.locator(".diff-viewer .cell.chg.new").count() > 0,
          head)
    page.locator(".diff-viewer .back").click()
    time.sleep(0.6)
    check("git_commit_diff_back_returns",
          page.locator(".commit-view").count() == 1)
    page.locator(".commit-view .close").click()
    time.sleep(0.4)
    check("git_commit_view_closes",
          page.locator(".commit-view").count() == 0
          and page.locator(".file-tab").count() > 0)

    # V9/V10: manual refresh — disk change lands after refresh (and reverts).
    probe = os.path.join(BIG, "zz-git-probe.txt")
    try:
        wf(probe, "probe\n")
        page.locator(".sidebar-header .refresh").click()
        ok_add = badge_becomes(page, "8")
        check("git_manual_refresh_updates_badge", ok_add,
              f"badge after probe={badge_text(page, timeout_s=2)!r}")
        os.remove(probe)
        page.locator(".sidebar-header .refresh").click()
        check("git_manual_refresh_reverts", badge_becomes(page, "7"),
              f"badge after revert={badge_text(page, timeout_s=2)!r}")
    finally:
        if os.path.exists(probe):
            os.remove(probe)

    # spec-009 V5: the WATCHER refreshes git with no gesture at all —
    # external write -> badge climbs to 8 on its own, delete -> 7.
    try:
        wf(probe, "watched probe\n")
        ok_auto = badge_becomes(page, "8")
        os.remove(probe)
        ok_back = badge_becomes(page, "7")
        check("git_watcher_auto_refresh_updates_badge", ok_auto and ok_back,
              f"auto={ok_auto} back={ok_back} "
              f"badge={badge_text(page, timeout_s=2)!r}")
    finally:
        if os.path.exists(probe):
            os.remove(probe)


# --------------------------------------------------------------------------
# Instance B: BigRepo\apps\viewer — subdirectory scope (§174).

def instance_b(page):
    badge = badge_text(page)
    check("git_scope_badge_counts_scope_only", badge == "5",
          f"badge={badge!r}")

    # spec-014: the dirty indicator is an SVG glyph now — the machine-
    # readable state lives in data-state (decoupled from the drawing).
    tab_state = page.locator(".project-tabs .tab .git-state").first \
        .get_attribute("data-state")
    check("git_scope_tab_indicator_dirty", tab_state == "dirty", str(tab_state))

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
