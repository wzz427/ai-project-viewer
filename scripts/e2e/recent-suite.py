# -*- coding: utf-8 -*-
"""Open Recent suite (spec-010; zero disturbance).

Three isolated launches against generated %TEMP% folders — the native
folder picker is NEVER driven (undrivable + would surface on the owner's
desktop, lessons L7), so adds come from AIV_TEST_PROJECT auto-add and
pre-seeded state files instead:
  A.  seeded 9 recents + auto-add a 10th  — record/MRU order, menu
      structure, dead-folder gray + error, open / switch-to-open, Esc
  B.  restart on A's state file           — persistence across restart,
      cap eviction (the seeded dead entry falls off), row ✕ and Clear
      land in the saved state
  C.  zero projects + seeded recents      — EmptyState recent list opens a
      project from the welcome page

After Clear the recents list is empty and clicking + would open the native
picker — the suite NEVER clicks + again past that point (see D4 in the
spec). All launch/kill handling goes through aivlaunch (owner isolation).
"""
import json
import os
import shutil
import sys
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "src-tauri", "target", "release", "ai-project-viewer.exe"))
BASE = os.path.join(os.environ["TEMP"], "aiv-p10-recent")
STATE = os.path.join(os.environ["TEMP"], "aiv-p10-state.json")

results = {}
FAIL = []


def check(name, ok, detail=""):
    results[name] = "PASS" if ok else f"FAIL {detail}"
    if not ok:
        FAIL.append(name)


def connect(p, port):
    for _ in range(60):
        try:
            return p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"CDP {port}")


def seed_state(path, recents):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "projects": [], "settings": {},
                   "recentFolders": recents}, f)


def read_state():
    with open(STATE, encoding="utf-8") as f:
        return json.load(f)


def run_instance(project, port, fn, wait_sel=".file-tree"):
    # keep_state=True keeps OUR pre-seeded file (launch deletes it otherwise)
    proc = aivlaunch.launch(EXE, project, STATE, port, keep_state=True)
    _hwnd = aivlaunch.window_of(proc.pid)
    if _hwnd:
        aivlaunch.park_offscreen(_hwnd)
    try:
        with sync_playwright() as p:
            browser = connect(p, port)
            page = browser.contexts[0].pages[0]
            page.wait_for_selector(wait_sel, timeout=25000)
            fn(page)
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)


def open_add_menu(page):
    page.locator("button.add").click()
    page.wait_for_selector('[data-menu-id="add-project-menu"]', timeout=5000)
    return page.locator('[data-menu-id="add-project-menu"]')


def rows_of(menu):
    return menu.locator("div.recent-row")


def row_named(menu, name):
    """Row by folder NAME, never by path attribute — Windows paths carry
    backslashes, which CSS attribute selectors treat as escapes. Names are
    unique among the fixtures, so substring matching is unambiguous
    (probe-verified: has=+text-is never resolves, has_text does)."""
    return menu.locator("div.recent-row").filter(has_text=name).first


def toast_contains(page, sub, timeout_s=6):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if page.locator(".toast").count() and sub in page.locator(".toast").inner_text():
            return True
        time.sleep(0.2)
    return False


def active_project_tab(page):
    # spec-014 (L44): the project tab now leads with an avatar letter —
    # read the NAME span, not the whole tab's innerText ("P\np01").
    tab = page.locator(".project-tabs .tab.active")
    name = tab.locator(".tab-name")
    if name.count():
        return name.inner_text()
    return tab.inner_text() if tab.count() else ""


def read_saved():
    """Read the state file after the 800ms save debounce settles."""
    time.sleep(2.5)
    return read_state()


# --- fixtures: 12 plain folders + one path that never exists on disk ---
if os.path.exists(BASE):
    shutil.rmtree(BASE)
os.makedirs(BASE)
DIRS = {f"p{i:02d}": os.path.join(BASE, f"p{i:02d}") for i in range(12)}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)
DEAD = os.path.join(BASE, "gone")
# Seeded MRU, newest first: p00..p07 then the dead path (9 entries — the
# auto-added p11 becomes the 10th, so `dead` survives to be tested).
seed_state(STATE, [DIRS[f"p{i:02d}"] for i in range(8)] + [DEAD])


def scenario_a(page):
    menu = open_add_menu(page)
    rows = rows_of(menu)
    check("recent_records_on_add", rows.count() == 10
          and rows.first.locator(".name").inner_text() == "p11",
          f"rows={rows.count()} first={rows.first.locator('.name').inner_text() if rows.count() else '-'}")

    items = menu.locator(".menu-item")
    check("recent_menu_structure",
          items.first.get_attribute("data-menu-id") == "browse-folder"
          and "Open Recent" in menu.inner_text()
          and items.last.get_attribute("data-menu-id") == "clear-recent",
          "browse/label/clear layout")

    # Dead folder: grays once the one-shot paths_exist lands, still clickable.
    dead_row = row_named(menu, "gone")
    grayed = False
    deadline = time.time() + 6
    while time.time() < deadline:
        if "missing" in (dead_row.get_attribute("class") or ""):
            grayed = True
            break
        time.sleep(0.3)
    check("recent_dead_folder_grayed", grayed, f"class={dead_row.get_attribute('class')}")

    dead_row.locator("button.recent-open").click()
    check("recent_dead_click_errors",
          toast_contains(page, "Cannot open folder")
          and page.locator('[data-menu-id="add-project-menu"]').count() == 0,
          "no error toast")

    # Open a not-yet-open project from the menu → new tab, becomes active.
    menu = open_add_menu(page)
    row_named(menu, "p03").locator("button.recent-open").click()
    time.sleep(1.0)
    check("recent_open_new_project", active_project_tab(page).startswith("p03"),
          f"active={active_project_tab(page)}")

    # Re-open one that IS open → switch + already-open toast (V1.5 §14 path).
    menu = open_add_menu(page)
    row_named(menu, "p11").locator("button.recent-open").click()
    check("recent_open_already_switches",
          toast_contains(page, "already open")
          and active_project_tab(page).startswith("p11"),
          f"active={active_project_tab(page)}")

    # Esc closes without acting. The trailing sleep lets the debounced save
    # land before the instance is force-killed (taskkill skips exit flushes).
    menu = open_add_menu(page)
    page.keyboard.press("Escape")
    check("recent_menu_esc_closes",
          page.locator('[data-menu-id="add-project-menu"]').count() == 0)
    time.sleep(2.5)


def scenario_b(page):
    menu = open_add_menu(page)
    rows = rows_of(menu)
    body = menu.inner_text()
    # Auto-add on this launch recorded p05 → front; the dead entry (oldest)
    # fell off the 10-cap. p03 (added live in A) and p11 survived the restart.
    check("recent_cap_evicts_oldest",
          rows.count() == 10
          and rows.first.locator(".name").inner_text() == "p05"
          and DEAD not in body,
          f"rows={rows.count()} first={rows.first.locator('.name').inner_text() if rows.count() else '-'}")
    check("recent_restart_persists",
          "p03" in body and "p11" in body, "live-added entries lost on restart")

    # Row ✕ removes exactly one entry and reaches the saved state.
    row_named(menu, "p03").locator("button.recent-remove").click()
    time.sleep(0.4)
    check("recent_remove_row", rows_of(page.locator('[data-menu-id="add-project-menu"]')).count() == 9
          and row_named(page.locator('[data-menu-id="add-project-menu"]'), "p03").count() == 0,
          "row not removed")
    saved = read_saved().get("recentFolders")
    check("recent_remove_persisted",
          isinstance(saved, list) and len(saved) == 9 and DIRS["p03"] not in saved,
          f"saved={saved}")

    # Clear empties the list; the saved file drops the field entirely.
    page.locator('[data-menu-id="clear-recent"]').click()
    check("recent_clear_closes_menu",
          page.locator('[data-menu-id="add-project-menu"]').count() == 0)
    saved = read_saved()
    check("recent_clear_persisted",
          isinstance(saved, dict) and "recentFolders" not in saved,
          f"saved keys={list(saved.keys()) if isinstance(saved, dict) else saved}")
    # D4: recents are empty now — clicking + would open the native picker.
    # Nothing below this line may click button.add.


def scenario_c(page):
    recent = page.locator('[data-menu-id="empty-recent"]')
    check("empty_state_recent_list",
          recent.count() == 1 and recent.locator("button.recent-item").count() == 2,
          f"count={recent.count()}")
    recent.locator("button.recent-item").filter(has_text="p01").first.click()
    gone = False
    deadline = time.time() + 6
    while time.time() < deadline:
        if page.locator(".empty-state").count() == 0:
            gone = True
            break
        time.sleep(0.3)
    check("empty_state_recent_opens",
          gone and active_project_tab(page).startswith("p01"),
          f"active={active_project_tab(page)}")


run_instance(DIRS["p11"], 9261, scenario_a)
run_instance(DIRS["p05"], 9262, scenario_b)
# Empty-recents welcome page: no AIV_TEST_PROJECT (project="" is filtered
# out Rust-side) so zero projects auto-add, and a fresh seeded state.
seed_state(STATE, [DIRS["p00"], DIRS["p01"]])
run_instance("", 9263, scenario_c, wait_sel=".empty-state")

for name, v in results.items():
    print(f"[{v}] {name}")
print(f"\nrecent-suite: {len(results) - len(FAIL)}/{len(results)} checks passed")
sys.exit(1 if FAIL else 0)
