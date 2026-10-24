# -*- coding: utf-8 -*-
"""T3 full benchmark suite (V1.5 #161-#174 + #162 Phase 1 Baseline rerun).

Owner approved the full run 2026-10-12 ("开跑" — AGENTS.md red line).
Tiers (V1.5 definitions, numbers recorded per #161 whole-process-tree):

  A  Shell / Phase 1 Baseline — 0 projects, NO CDP port (clean numbers):
     cold + warm startup, idle tree RAM (private + WS), idle CPU over 60s,
     WebView2 process count. Gates: cold start <= 2s (#164); idle CPU near
     zero (#165); RAM <=150MB is a target, not a gate (#163) - reported.
  B  Normal — 1 project (5 md + 3 py + 2 json): RAM delta of opening 10
     tabs + file-switch latency.
  C  Multi — 4 projects x 10 tabs preseeded state (1 active): session
     restore latency, RAM, project-switch latency, restart restore.
  D  Large — node_modules with >100k files: startup must NOT recursively
     scan (startup ~= small-project startup), tree lazy, idle CPU ~0 with
     watcher armed, event storm inside node_modules ignored (responsive,
     bounded CPU, no UI churn).
  E  Agent Changes — 10 files hammered for 60s: native window stays
     responsive, git.exe spawns bounded (watcher/git debounce), badge
     correct after churn settles.
  F  PDF — 10p text / 100p text / 100p scan x before/open/deep-scroll/
     switch-away/close RAM (CDP base cancels in the deltas; #98 method).
  G  Multiple PDF Tabs — 5 tabs (1 active) vs 1 tab: RAM must not grow
     linearly with inactive tabs (gate: delta5 < 3 x delta1).
  H  Large Diff — 25k-line working diff: backend truncation branch shows
     ("Diff is too large to display." + Open in VS Code offered, NOT
     clicked - zero disturbance), no diff table rendered (webview never
     receives the full payload), window responsive throughout.
  I  Git Subdirectory Scope — reruns git-suite.py in-round: the #174
     seven checks live in its BigRepo apps/viewer instance.

Zero disturbance: every launch via aivlaunch (PID/build-tree-scoped kills
only, offscreen parking, isolated AIV_STATE_FILE). RAM = psutil process-
tree sums; private bytes primary (Phase 1 Baseline convention), WS noted.

Usage:
  pywork python scripts\\e2e\\benchmark-suite.py --tiers A,B,C,D,E,F,G,H,I
Results append to %TEMP%\\aiv-bench\\results.json per tier.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

import psutil
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aivlaunch  # noqa: E402

EXE = os.path.normpath(os.path.join(
    HERE, "..", "..", "src-tauri", "target", "release", "ai-project-viewer.exe"))
BENCH = os.path.join(os.environ["TEMP"], "aiv-bench")
DESKTOP_PROJ = os.path.join(  # in-repo fixture (owner 2026-10-24)
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "AIV-TestProject")

RESULTS = {}
GATES = []


def check(tier, name, ok, detail=""):
    key = f"{tier}.{name}"
    RESULTS[key] = f"PASS {detail}" if ok else f"FAIL {detail}"
    print(f"  [{'PASS' if ok else 'FAIL'}] {key} {detail}")
    if not ok:
        GATES.append(key)


def rec(tier, name, value):
    RESULTS[f"{tier}.{name}"] = value
    print(f"  [rec ] {tier}.{name} = {value}")


def dump():
    os.makedirs(BENCH, exist_ok=True)
    path = os.path.join(BENCH, "results.json")
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except ValueError:
                data = {}
    data.update(RESULTS)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


# ---------------------------------------------------------------- helpers

_USER32 = ctypes.windll.user32
_WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
TITLE = "AI Project Viewer"


def first_window_ms(proc, timeout_s=20):
    """Popen -> main window CREATED (title match; under AIV_HIDDEN it is
    never shown, so this is the window-object timestamp, not 'visible')."""
    t0 = time.perf_counter()
    deadline = t0 + timeout_s
    while time.perf_counter() < deadline:
        hits = []

        def cb(hwnd, _):
            buf = ctypes.create_unicode_buffer(64)
            _USER32.GetWindowTextW(hwnd, buf, 64)
            owner = wt.DWORD()
            _USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == proc.pid and buf.value == TITLE:
                hits.append(hwnd)
            return True

        _USER32.EnumWindows(_WNDENUMPROC(cb), 0)
        if hits:
            return int((time.perf_counter() - t0) * 1000)
        time.sleep(0.02)
    return -1


def find_main_hwnd(proc):
    """Main window hwnd by (pid, title) — our own pid only, so this stays
    inside the zero-disturbance rules (never touches owner windows)."""
    hits = []

    def cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(64)
        _USER32.GetWindowTextW(hwnd, buf, 64)
        owner = wt.DWORD()
        _USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == proc.pid and buf.value == TITLE:
            hits.append(hwnd)
        return True

    _USER32.EnumWindows(_WNDENUMPROC(cb), 0)
    return hits[0] if hits else 0


def show_main_offscreen(proc):
    """Make the hidden main window visible-but-offscreen (SW_SHOWNOACTIVATE)
    so timers/rAF run — the realistic-idle regime for CPU measurement."""
    hwnd = find_main_hwnd(proc)
    if hwnd:
        _USER32.SetWindowPos(hwnd, 0, -2500, -100, 0, 0,
                             0x0001 | 0x0010 | 0x0004)
        _USER32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE
    return hwnd


def native_ok(hwnd):
    """WM_NULL probe on the native window thread (freeze-guard method)."""
    WM_NULL = 0x0000
    SMTO_ABORTIFHUNG = 0x0002
    res = _USER32.SendMessageTimeoutW(
        hwnd, WM_NULL, 0, 0, SMTO_ABORTIFHUNG, 400,
        ctypes.byref(ctypes.c_ulong()))
    return bool(res)


def tree_procs(proc):
    """Whole process tree (Rust + every msedgewebview2 child), #161."""
    procs = []
    try:
        root = psutil.Process(proc.pid)
        procs = [root] + root.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return procs


def ram_mb(proc):
    priv = ws = 0.0
    for p in tree_procs(proc):
        try:
            ws += p.memory_info().rss
            priv += p.memory_full_info().private
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return priv / 1e6, ws / 1e6


def cpu_seconds(proc):
    total = 0.0
    for p in tree_procs(proc):
        try:
            t = p.cpu_times()
            total += t.user + t.system
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total


def cpu_window(proc, seconds, sampler=None, sample_every=0.3):
    """CPU-seconds consumed by the tree over `seconds`; optional concurrent
    callback (sampler(now)) fired every sample_every for responsiveness."""
    c0 = cpu_seconds(proc)
    t_end = time.time() + seconds
    next_sample = time.time()
    while time.time() < t_end:
        if sampler and time.time() >= next_sample:
            sampler(time.time())
            next_sample += sample_every
        time.sleep(0.05)
    if sampler and time.time() >= next_sample:
        sampler(time.time())
    return cpu_seconds(proc) - c0


def webview_count(proc):
    n = 0
    for p in tree_procs(proc):
        try:
            if p.name().lower() == "msedgewebview2.exe":
                n += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return n


def launch_bench(project, state, cdp=None, keep_state=False):
    """aivlaunch-style start, but project=None means NO AIV_TEST_PROJECT
    (tier A / preseeded tier C)."""
    aivlaunch._assert_dev_binary(EXE)
    aivlaunch.kill_strays()
    if os.path.exists(state) and not keep_state:
        os.remove(state)
    env = {**os.environ, "AIV_STATE_FILE": state, "AIV_HIDDEN": "1"}
    if project:
        env["AIV_TEST_PROJECT"] = project
    if cdp:
        env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = \
            f"--remote-debugging-port={cdp}"
    return subprocess.Popen([EXE], env=env)


def park(proc, timeout_s=12):
    hwnd = aivlaunch.window_of(proc.pid, timeout_s)
    if hwnd:
        aivlaunch.park_offscreen(hwnd)
    return hwnd


def connect(p, port):
    for _ in range(80):
        try:
            return p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"CDP {port}")


def wait_tree(page, timeout_s=25):
    page.wait_for_selector(".file-tree", timeout=timeout_s * 1000)


def tree_click(page, name):
    page.wait_for_selector(
        f"div.row[role='treeitem'] :text-is('{name}')", timeout=10000)
    page.click(f"div.row[role='treeitem'] :text-is('{name}')")


def expand(page, folder):
    row = page.locator(
        ".file-tree .row", has=page.locator(".name", has_text=folder)).first
    if row.get_attribute("aria-expanded") != "true":
        row.click()
        time.sleep(0.6)


def open_file(page, name, folder=None):
    if folder:
        expand(page, folder)
    tree_click(page, name)


def close_tab(page, name):
    page.locator(".file-tab", has_text=name).first.click(button="right")
    page.locator(".menu button", has_text="Close Tab").first.click()


def tab_count(page):
    return page.locator(".file-tab").count()


def badge_int(page, timeout_s=20):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        loc = page.locator(".sidebar-header .git-badge")
        t = loc.first.inner_text().strip() if loc.count() else ""
        if t:
            try:
                return int(t.strip("[]"))
            except ValueError:
                pass
        time.sleep(0.4)
    return -1


def wf(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def sh(cwd, *args):
    r = subprocess.run(["git", "-C", str(cwd), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {args} failed: {r.stderr.strip()}")


def rmrf(path):
    """rmtree that clears git's read-only object files first (git-suite)."""
    def onexc(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)
    if os.path.exists(path):
        shutil.rmtree(path, onexc=onexc)


# ------------------------------------------------------------------ tiers

def tier_a():
    """Shell (0 projects) == Phase 1 Baseline rerun (#162).

    口径 (zero-disturbance constraints, stated honestly):
      - RAM / WebView2 count / idle CPU come from a CLEAN launch (no CDP).
        Idle CPU measured twice: hidden window (timers frozen = lower
        bound) and window shown offscreen without activation (realistic
        idle, rAF/compositor live).
      - Startup = window-created ms (title enum) + frontend-ready ms (CDP,
        body mounted). The Phase 1 'visible window' 口径 (MainWindowHandle)
        cannot be reproduced without showing a window on the owner's
        desktop — noted as such in the report.
    """
    print("== A Shell / Phase 1 Baseline (0 projects)")
    state = os.path.join(BENCH, "a.json")

    # --- clean instance: RAM + idle CPU in both regimes ---
    proc = launch_bench(None, state)
    time.sleep(8)  # settle: webview init + first paint done
    n_wv = webview_count(proc)
    priv, ws = ram_mb(proc)
    rust_priv = 0.0
    for p in tree_procs(proc):
        try:
            if p.name().lower() != "msedgewebview2.exe":
                rust_priv += p.memory_full_info().private / 1e6
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    rec("A", "webview_process_count", n_wv)
    rec("A", "idle_ram_private_mb", round(priv, 1))
    rec("A", "idle_ram_rust_private_mb", round(rust_priv, 1))
    rec("A", "idle_ram_webview_private_mb", round(priv - rust_priv, 1))
    rec("A", "idle_ram_ws_mb", round(ws, 1))
    check("A", "webview_procs_sane", 2 <= n_wv <= 12, f"{n_wv}")
    cpu_hidden = cpu_window(proc, 60)
    rec("A", "idle_cpu_hidden_s_per_60s", round(cpu_hidden, 2))
    show_main_offscreen(proc)
    time.sleep(2)
    cpu_visible = cpu_window(proc, 60)
    rec("A", "idle_cpu_offscreen_visible_s_per_60s", round(cpu_visible, 2))
    check("A", "idle_cpu_near_zero", cpu_visible < 1.2,
          f"{cpu_visible:.2f} CPU-s/60s, offscreen-visible regime (#165)")
    aivlaunch.kill_tree(proc)
    time.sleep(1.0)

    # --- startup x3 with CDP: window-created + frontend-ready ---
    win_ms, rdy_ms = [], []
    with sync_playwright() as pw:
        for i in range(3):
            port = 9330 + i
            t0 = time.perf_counter()
            proc = launch_bench(None, state, cdp=port)
            win_ms.append(first_window_ms(proc))
            rdy = -1
            deadline = time.time() + 40
            browser = None
            while time.time() < deadline:
                try:
                    browser = pw.chromium.connect_over_cdp(
                        f"http://127.0.0.1:{port}")
                    break
                except Exception:
                    time.sleep(0.05)
            if browser:
                try:
                    page = browser.contexts[0].pages[0]
                    while time.time() < deadline:
                        try:
                            if page.evaluate(
                                    "() => document.body.children.length"):
                                rdy = int((time.perf_counter() - t0) * 1000)
                                break
                        except Exception:
                            pass
                        time.sleep(0.03)
                finally:
                    browser.close()
            rdy_ms.append(rdy)
            aivlaunch.kill_tree(proc)
            time.sleep(1.0)
    rec("A", "window_created_ms", win_ms)
    rec("A", "frontend_ready_ms", rdy_ms)
    check("A", "cold_start_le_2s", 0 < rdy_ms[0] <= 2000,
          f"frontend-ready {rdy_ms[0]}ms, window-created {win_ms[0]}ms "
          "(#164; 口径:CDP 前端就绪,零打扰下不可复刻可见窗口径)")
    ram = RESULTS["A.idle_ram_private_mb"]
    check("A", "ram_target_150_reported", True,
          f"private {ram}MB vs #163 target 150MB — target 非 gate,判读见报告")


def tier_b():
    """Normal project: 5 md + 3 py + 2 json (#167)."""
    print("== B Normal (1 project, 10 tabs)")
    fix = os.path.join(BENCH, "normal")
    if not os.path.isdir(fix):
        os.makedirs(fix)
        for i in range(1, 6):
            wf(os.path.join(fix, f"note{i}.md"), f"# note {i}\n" + "text\n" * 40)
        for i in range(1, 4):
            wf(os.path.join(fix, f"mod{i}.py"), "x = 1\n" + "y = [i for i in range(40)]\n" * 20)
        for i in range(1, 3):
            wf(os.path.join(fix, f"cfg{i}.json"), json.dumps({"k": list(range(50))}, indent=1))
    state = os.path.join(BENCH, "b.json")
    port = 9333
    proc = launch_bench(fix, state, port)
    hwnd = park(proc)
    startup = first_window_ms(proc)
    rec("B", "startup_ms_cdp", startup)
    try:
        with sync_playwright() as p:
            browser = connect(p, port)
            page = browser.contexts[0].pages[0]
            wait_tree(page)
            time.sleep(3)
            priv0, ws0 = ram_mb(proc)
            rec("B", "ram_before_tabs_private_mb", round(priv0, 1))
            names = [f"note{i}.md" for i in range(1, 6)] + \
                    [f"mod{i}.py" for i in range(1, 4)] + \
                    [f"cfg{i}.json" for i in range(1, 3)]
            for n in names:
                tree_click(page, n)
                page.wait_for_selector(".file-tab.active .name", timeout=8000)
            deadline = time.time() + 15
            while tab_count(page) < 10 and time.time() < deadline:
                time.sleep(0.3)
            check("B", "ten_tabs_open", tab_count(page) == 10, f"{tab_count(page)}")
            time.sleep(3)
            priv1, ws1 = ram_mb(proc)
            rec("B", "ram_after_tabs_private_mb", round(priv1, 1))
            rec("B", "ram_delta_tabs_private_mb", round(priv1 - priv0, 1))
            lat = []
            for i in range(20):
                target = names[i % 10]
                t0 = time.perf_counter()
                page.locator(".file-tab", has_text=target).first.click()
                page.wait_for_selector(f".file-tab.active :text-is('{target}')",
                                       timeout=5000)
                lat.append((time.perf_counter() - t0) * 1000)
            p50 = statistics.median(lat)
            rec("B", "file_switch_p50_ms", round(p50))
            rec("B", "file_switch_max_ms", round(max(lat)))
            check("B", "file_switch_snappy", p50 < 500, f"p50 {p50:.0f}ms")
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)


VT = {".md": "markdown", ".py": "code", ".json": "json", ".txt": "text"}


def vtype(name):
    ext = os.path.splitext(name)[1]
    return VT.get(ext, "text")


def tier_c():
    """4 projects x 10 tabs preseeded, 1 active (#168)."""
    print("== C Multi (4 projects x 10 tabs)")
    root = os.path.join(BENCH, "multi")
    if not os.path.isdir(root):
        proj_files = {}
        for pi in range(1, 5):
            d = os.path.join(root, f"p{pi}")
            os.makedirs(d)
            files = [f"m{i}.md" for i in range(1, 7)] + \
                    [f"s{i}.py" for i in range(1, 4)] + \
                    [f"j{i}.json" for i in range(1, 4)]  # 12, open 10
            for n in files:
                wf(os.path.join(d, n), f"# {n}\n" + "line\n" * 30)
            proj_files[f"p{pi}"] = files
    state = os.path.join(BENCH, "c.json")
    projects = []
    for pi in range(1, 5):
        name = f"p{pi}"
        files = ([f"m{i}.md" for i in range(1, 7)] +
                 [f"s{i}.py" for i in range(1, 4)] +
                 [f"j{i}.json" for i in range(1, 4)])[:10]
        projects.append({
            "id": f"bench-{name}", "name": name,
            "rootPath": os.path.join(root, name),
            "expandedFolders": [],
            "openFiles": [{"relativePath": n, "viewerType": vtype(n)}
                          for n in files],
            "activeFileRelativePath": files[0],
            "sidebarMode": "files", "sidebarWidth": 260,
            "trustedForExecution": False,
            "fileTreePreferences": {"foldersFirst": True, "pinnedItems": {}},
        })
    seeded = {"version": 1, "projects": projects,
              "activeProjectId": "bench-p1",
              "settings": {"theme": "system", "viewer": {"fontSize": 13},
                           "fileTree": {"showSystemGeneratedFolders": False}},
              "recentFolders": []}
    os.makedirs(BENCH, exist_ok=True)
    with open(state, "w", encoding="utf-8") as f:
        json.dump(seeded, f)

    port = 9334
    proc = launch_bench(None, state, port, keep_state=True)
    t_launch = time.perf_counter()
    hwnd = park(proc)
    try:
        with sync_playwright() as p:
            browser = connect(p, port)
            page = browser.contexts[0].pages[0]
            # session-restore latency: launch -> 10 tabs + active content
            deadline = time.time() + 40
            restored = -1
            while time.time() < deadline:
                try:
                    n = page.evaluate(
                        "() => document.querySelectorAll('.file-tab').length")
                    body = page.evaluate(
                        "() => (document.querySelector('.viewer-body')||{})"
                        ".innerText?.length > 0")
                    if n >= 10 and body:
                        restored = int((time.perf_counter() - t_launch) * 1000)
                        break
                except Exception:
                    pass
                time.sleep(0.1)
            rec("C", "session_restore_ms", restored)
            check("C", "session_restore_fast", 0 < restored <= 5000,
                  f"{restored}ms")
            check("C", "ten_tabs_restored",
                  tab_count(page) == 10, f"{tab_count(page)}")
            time.sleep(4)
            priv, ws = ram_mb(proc)
            rec("C", "ram_4x10_tabs_private_mb", round(priv, 1))
            lat = []
            for name in ["p2", "p3", "p4", "p1"]:
                t0 = time.perf_counter()
                page.locator(".project-tabs .tab", has_text=name).first.click()
                deadline = time.time() + 10
                ok = False
                while time.time() < deadline:
                    try:
                        n = page.evaluate(
                            "() => document.querySelectorAll('.file-tab').length")
                        if n >= 10:
                            ok = True
                            break
                    except Exception:
                        pass
                    time.sleep(0.1)
                if not ok:
                    break
                lat.append((time.perf_counter() - t0) * 1000)
            p50 = statistics.median(lat) if lat else -1
            rec("C", "project_switch_p50_ms", round(p50))
            check("C", "project_switch_ok", len(lat) == 4 and p50 < 1500,
                  f"{len(lat)}/4 switches, p50 {p50:.0f}ms")
            browser.close()
        # restart: state flushed by debounce, force kill, relaunch
        time.sleep(2.5)
        aivlaunch.kill_tree(proc)
        time.sleep(1.0)
        proc = launch_bench(None, state, port, keep_state=True)
        t_launch = time.perf_counter()
        park(proc)
        with sync_playwright() as p:
            browser = connect(p, port)
            page = browser.contexts[0].pages[0]
            deadline = time.time() + 40
            restored = -1
            while time.time() < deadline:
                try:
                    n = page.evaluate(
                        "() => document.querySelectorAll('.file-tab').length")
                    if n >= 10:
                        restored = int((time.perf_counter() - t_launch) * 1000)
                        break
                except Exception:
                    pass
                time.sleep(0.1)
            rec("C", "restart_restore_ms", restored)
            check("C", "restart_restore_fast", 0 < restored <= 5000,
                  f"{restored}ms")
            page.locator(".project-tabs .tab", has_text="p4").first.click()
            time.sleep(2)
            check("C", "p4_tabs_survive_restart", tab_count(page) == 10,
                  f"{tab_count(page)}")
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)


def tier_d():
    """node_modules >100k files (#169)."""
    print("== D Large (node_modules >100k files)")
    fix = os.path.join(BENCH, "large")
    nm = os.path.join(fix, "node_modules")
    if not os.path.isdir(nm):
        t0 = time.time()
        os.makedirs(fix)
        wf(os.path.join(fix, "package.json"), '{"name":"bench-large"}\n')
        for i in range(1, 6):
            wf(os.path.join(fix, f"doc{i}.md"), f"# doc {i}\n")
        os.makedirs(nm)
        # one real file per package, then hardlinks (fast, NTFS same volume):
        # 250 packages x 420 files = 105,000 files inside node_modules.
        tmpl = os.path.join(BENCH, "d-link-src")
        wf(tmpl, "module.exports = {};\n")
        for pi in range(250):
            pkg = os.path.join(nm, f"pkg-{pi:03d}")
            os.makedirs(pkg)
            src = os.path.join(pkg, "index.js")
            shutil.copyfile(tmpl, src)
            for fi in range(1, 420):
                os.link(src, os.path.join(pkg, f"m{fi:03d}.js"))
        n_files = sum(len(files) for _, _, files in os.walk(nm))
        rec("D", "fixture_files_in_node_modules", n_files)
        check("D", "fixture_over_100k", n_files > 100000, f"{n_files}")
        rec("D", "fixture_build_seconds", round(time.time() - t0, 1))
    else:
        n_files = sum(len(files) for _, _, files in os.walk(nm))
        rec("D", "fixture_files_in_node_modules(reused)", n_files)

    state = os.path.join(BENCH, "d.json")
    port = 9335
    proc = launch_bench(fix, state, port)
    hwnd = park(proc)
    startup = first_window_ms(proc)
    rec("D", "startup_ms_cdp", startup)
    b_startup = RESULTS.get("B.startup_ms_cdp", startup)
    check("D", "startup_no_recursive_scan",
          abs(startup - b_startup) <= 1500,
          f"large {startup}ms vs normal {b_startup}ms (#169: 启动不递归扫描)")
    try:
        with sync_playwright() as p:
            browser = connect(p, port)
            page = browser.contexts[0].pages[0]
            t0 = time.time()
            wait_tree(page, timeout_s=30)
            tree_ms = int((time.time() - t0) * 1000)
            rec("D", "file_tree_visible_ms", tree_ms)
            rows = page.locator(".file-tree .row").count()
            rec("D", "root_rows", rows)
            nm_rows = page.locator(
                ".file-tree .row", has_text="node_modules").count()
            check("D", "node_modules_hidden_by_default", nm_rows == 0,
                  f"{nm_rows} rows")
            time.sleep(3)
            priv, ws = ram_mb(proc)
            rec("D", "ram_idle_private_mb", round(priv, 1))
            cpu = cpu_window(proc, 30)
            rec("D", "idle_cpu_seconds_per_30s", round(cpu, 2))
            check("D", "watcher_idle_cpu_low", cpu < 1.5,
                  f"{cpu:.2f} CPU-s/30s with watcher armed")
            browser.close()
        # event storm inside node_modules: 300 writes in ~3s + 5s observe
        unresp = []

        def sample(_now=None):
            if hwnd and not native_ok(hwnd):
                unresp.append(1)

        c0 = cpu_seconds(proc)
        storm_dir = os.path.join(nm, "pkg-000")
        for i in range(300):
            wf(os.path.join(storm_dir, f"storm-{i:04d}.js"), f"// churn {i}\n")
            if i % 30 == 29:
                sample()
                time.sleep(0.05)
        t_end = time.time() + 5
        while time.time() < t_end:
            sample()
            time.sleep(0.3)
        cpu_storm = cpu_seconds(proc) - c0
        rec("D", "storm_cpu_seconds_over_8s", round(cpu_storm, 2))
        check("D", "storm_cpu_bounded", cpu_storm < 8.0,
              f"{cpu_storm:.1f} CPU-s (ignored dirs must not be watched)")
        check("D", "storm_native_responsive", not unresp,
              f"{len(unresp)} unresponsive samples")
    finally:
        aivlaunch.kill_tree(proc)


def tier_e():
    """Agent continuously modifies 10 files (#170)."""
    print("== E Agent Changes (10 files, 60s hammer)")
    fix = os.path.join(BENCH, "agent")
    if not os.path.isdir(fix):
        os.makedirs(fix)
        wf(os.path.join(fix, "README.md"), "# agent bench\n")
        for i in range(1, 11):
            wf(os.path.join(fix, f"f{i}.py"),
               "# auto-gen\n" + "x = 1\n" * 60)
        sh(fix, "init", "-q", "-b", "main")
        sh(fix, "config", "user.email", "bench@example.com")
        sh(fix, "config", "user.name", "Bench")
        sh(fix, "add", "-A")
        sh(fix, "commit", "-q", "-m", "seed")
    state = os.path.join(BENCH, "e.json")
    port = 9336
    proc = launch_bench(fix, state, port)
    hwnd = park(proc)
    try:
        with sync_playwright() as p:
            browser = connect(p, port)
            page = browser.contexts[0].pages[0]
            wait_tree(page)
            b0 = badge_int(page, timeout_s=25)
            rec("E", "badge_before", b0)
            # -1 = no badge rendered: a clean repo shows none by design.
            check("E", "starts_clean", b0 in (0, -1), f"badge {b0}")

            unresp = []
            git_pids = set()

            def poll(_now):
                if hwnd and not native_ok(hwnd):
                    unresp.append(1)
                for pr in tree_procs(proc):
                    try:
                        if pr.name().lower() == "git.exe":
                            git_pids.add(pr.pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            t_end = time.time() + 60
            i = 0
            next_poll = 0.0
            while time.time() < t_end:
                n = i % 10 + 1
                wf(os.path.join(fix, f"f{n}.py"),
                   f"# v{i}\n" + "x = 2\n" * 60)
                i += 1
                if time.time() >= next_poll:
                    poll(time.time())
                    next_poll += 0.1
                time.sleep(0.2)
            rec("E", "hammer_writes", i)
            rec("E", "git_exe_distinct_spawns", len(git_pids))
            check("E", "native_responsive", len(unresp) <= 2,
                  f"{len(unresp)} unresponsive samples (freeze-guard bar)")
            check("E", "git_processes_bounded", len(git_pids) <= 150,
                  f"{len(git_pids)} distinct git.exe in 60s for {i} writes "
                  "(400ms 防抖理论顶≈150;口径:100ms 轮询采样,为下限)")
            time.sleep(8)  # refreshGitNow settle after last write
            b1 = badge_int(page, timeout_s=20)
            rec("E", "badge_after", b1)
            check("E", "git_state_correct", b1 == 10,
                  f"badge {b1}, expect 10 modified")
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)


def pdf_scenario(proc, page, pdf_name, tag):
    """One F row: before/open/deep-scroll/switch-away/close RAM (#171)."""
    time.sleep(3)
    priv0, _ = ram_mb(proc)
    open_file(page, pdf_name, folder="pdf")
    page.wait_for_selector(".pdf-viewer canvas", timeout=30000)
    time.sleep(2.5)
    priv1, _ = ram_mb(proc)
    for _ in range(5):
        page.evaluate(
            "() => { const s = document.querySelector('.pdf-viewer .scroller');"
            " if (s) s.scrollTop = s.scrollHeight; }")
        time.sleep(0.4)
    time.sleep(2)
    priv2, _ = ram_mb(proc)
    open_file(page, "README.md")
    page.wait_for_selector(".markdown-viewer", timeout=10000)
    time.sleep(2.5)
    priv3, _ = ram_mb(proc)
    close_tab(page, pdf_name)
    time.sleep(2.5)
    priv4, _ = ram_mb(proc)
    deltas = {tag: {
        "before": round(priv0, 1), "open": round(priv1 - priv0, 1),
        "deep_scroll": round(priv2 - priv0, 1),
        "switch_away": round(priv3 - priv0, 1),
        "close": round(priv4 - priv0, 1)}}
    for k, v in deltas[tag].items():
        rec("F", f"{tag}.{k}", v)
    check("F", f"{tag}_virtualization", priv2 - priv0 < 600,
          f"deep-scroll +{priv2 - priv0:.0f}MB")


def tier_f():
    """PDF RAM: 10p/100p text, 100p scan (#171; #98 method)."""
    print("== F PDF RAM")
    state = os.path.join(BENCH, "f.json")
    port = 9337
    for name, tag in [("sample-10p-text.pdf", "text10"),
                      ("sample-100p-text.pdf", "text100"),
                      ("sample-100p-scan.pdf", "scan100")]:
        proc = launch_bench(DESKTOP_PROJ, state, port)
        park(proc)
        try:
            with sync_playwright() as p:
                browser = connect(p, port)
                page = browser.contexts[0].pages[0]
                wait_tree(page)
                pdf_scenario(proc, page, name, tag)
                browser.close()
        finally:
            aivlaunch.kill_tree(proc)
        time.sleep(1)


def tier_g():
    """5 PDF tabs (1 active) vs 1 PDF tab (#172)."""
    print("== G Multiple PDF Tabs")
    state = os.path.join(BENCH, "g.json")
    port = 9338
    priv = {}
    for tag, files in [("one", ["tab-1.pdf"]),
                       ("five", [f"tab-{i}.pdf" for i in range(1, 6)])]:
        proc = launch_bench(DESKTOP_PROJ, state, port)
        park(proc)
        try:
            with sync_playwright() as p:
                browser = connect(p, port)
                page = browser.contexts[0].pages[0]
                wait_tree(page)
                time.sleep(3)
                p0, _ = ram_mb(proc)
                for n in files:
                    open_file(page, n, folder="pdf")
                    page.wait_for_selector(".pdf-viewer canvas", timeout=20000)
                time.sleep(5)
                p1, _ = ram_mb(proc)
                priv[tag] = {"base": p0, "after": p1, "delta": p1 - p0}
                browser.close()
        finally:
            aivlaunch.kill_tree(proc)
        time.sleep(1)
    d1, d5 = priv["one"]["delta"], priv["five"]["delta"]
    rec("G", "one_tab_delta_mb", round(d1, 1))
    rec("G", "five_tabs_delta_mb", round(d5, 1))
    check("G", "non_linear_ram", d5 < 3 * d1,
          f"5-tab +{d5:.0f}MB vs 1-tab +{d1:.0f}MB (linear would be "
      f"+{5 * d1:.0f}MB)")


def tier_h():
    """>20k-line diff: backend truncation (#173)."""
    print("== H Large Diff (25k lines)")
    fix = os.path.join(BENCH, "bigdiff")
    if not os.path.isdir(fix):
        os.makedirs(fix)
        big = os.path.join(fix, "big.ts")
        wf(big, "".join(f"line {i}\n" for i in range(25_000)))
        wf(os.path.join(fix, "small.ts"), "one\ntwo\n")
        sh(fix, "init", "-q", "-b", "main")
        sh(fix, "config", "user.email", "bench@example.com")
        sh(fix, "config", "user.name", "Bench")
        sh(fix, "add", "-A")
        sh(fix, "commit", "-q", "-m", "seed")
        wf(big, "".join(f"changed {i}\n" for i in range(25_000)))
        wf(os.path.join(fix, "small.ts"), "one\nTWO\n")
    state = os.path.join(BENCH, "h.json")
    port = 9339
    proc = launch_bench(fix, state, port)
    hwnd = park(proc)
    try:
        with sync_playwright() as p:
            browser = connect(p, port)
            page = browser.contexts[0].pages[0]
            wait_tree(page)
            badge_int(page, timeout_s=25)
            page.locator('.sidebar-header .header-tab',
                         has_text="Git").first.click()
            page.wait_for_selector(".git-panel .entry", timeout=15000)
            unresp = []

            def open_and_measure(entry_text, expect_truncated):
                t0 = time.perf_counter()
                page.locator(".git-panel .entry",
                             has_text=entry_text).first.click()
                deadline = time.time() + 15
                while time.time() < deadline:
                    if hwnd and not native_ok(hwnd):
                        unresp.append(1)
                    if expect_truncated:
                        if page.locator(".too-large").count():
                            return int((time.perf_counter() - t0) * 1000)
                    else:
                        if page.locator(".diff-viewer .table").count():
                            return int((time.perf_counter() - t0) * 1000)
                    time.sleep(0.15)
                return -1

            ms_big = open_and_measure("big.ts", True)
            rec("H", "big_diff_truncated_ui_ms", ms_big)
            check("H", "truncation_branch_shown", ms_big > 0,
                  f"{ms_big}ms to 'Diff is too large to display.'")
            check("H", "no_full_table_rendered",
                  page.locator(".diff-viewer .table").count() == 0,
                  "webview never rendered the 25k-line payload")
            check("H", "vscode_handoff_offered",
                  page.locator(".too-large button",
                               has_text="Open in VS Code").count() == 1)
            ms_small = open_and_measure("small.ts", False)
            rec("H", "small_diff_table_ms", ms_small)
            check("H", "small_diff_renders", ms_small > 0,
                  f"{ms_small}ms")
            check("H", "native_responsive", not unresp,
                  f"{len(unresp)} unresponsive samples")
            browser.close()
    finally:
        aivlaunch.kill_tree(proc)


def tier_i():
    """Git subdirectory scope (#174) — rerun git-suite.py in-round."""
    print("== I Git Subdirectory Scope (rerun git-suite.py)")
    r = subprocess.run([sys.executable, os.path.join(HERE, "git-suite.py")],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    fails = [ln for ln in out.splitlines() if ln.startswith("FAILED")]
    ok = r.returncode == 0 and not fails
    rec("I", "git_suite_exit_code", r.returncode)
    check("I", "scope_checks_pass", ok,
          f"git-suite.py exit {r.returncode}; {fails or 'all PASS'}")


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="A,B,C,D,E,F,G,H,I")
    args = ap.parse_args()
    os.makedirs(BENCH, exist_ok=True)
    # Global preflight: dev binary at the version tauri.conf.json declares.
    with open(os.path.normpath(os.path.join(
            HERE, "..", "..", "src-tauri", "tauri.conf.json")),
            encoding="utf-8") as f:
        version = json.load(f)["version"]
    with open(EXE, "rb") as f:
        blob = f.read()
    assert version.encode("utf-16-le") in blob, f"dev exe is not {version}"
    aivlaunch._assert_dev_binary(EXE)
    print(f"binary OK: {version} dev ({len(blob)//1024//1024}MB)")
    t0 = time.time()
    for t in args.tiers.split(","):
        t = t.strip().upper()
        if t == "A":
            tier_a()
        elif t == "B":
            tier_b()
        elif t == "C":
            tier_c()
        elif t == "D":
            tier_d()
        elif t == "E":
            tier_e()
        elif t == "F":
            tier_f()
        elif t == "G":
            tier_g()
        elif t == "H":
            tier_h()
        elif t == "I":
            tier_i()
        else:
            print(f"unknown tier {t}")
        dump()
        print(f"-- tier {t} done ({time.time() - t0:.0f}s elapsed)")
    print("\n==== GATES ====")
    print("ALL PASS" if not GATES else f"FAILED: {GATES}")
    dump()


if __name__ == "__main__":
    main()
