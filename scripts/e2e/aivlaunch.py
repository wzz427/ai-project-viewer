# -*- coding: utf-8 -*-
"""Shared zero-disturbance launcher for the e2e scripts (owner isolation).

Owner directive 2026-10-10: "开发代码时不敢用这个软件,感觉随时可能自动
关闭文件" — his experience client was force-killed by a test round. Two
mechanisms did that, both forbidden now:

1. NEVER kill by process NAME: the experience client runs the same exe
   name (ai-project-viewer.exe) from its own install dir. Straggler
   cleanup may only touch processes whose ExecutablePath is under THIS
   repo's src-tauri\\target tree.
2. NEVER find the test window by TITLE: the owner's client carries the
   same title. Locate the window owned by OUR pid via EnumWindows.

Test state stays separate by AIV_STATE_FILE (never the owner's state.json),
and nothing here writes outside the repo or %TEMP%.
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import time

# In-repo test fixture project (owner 2026-10-24: deleted the Desktop
# copy — "别放桌面上了,在仓库里找个地方放"). Regenerate the whole tree
# with make-fixtures.py --rebuild-project. Gitignored: the scan/huge
# PDFs (~45 MB) must never enter git or the backup pushes.
FIXTURE_PROJECT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fixtures", "AIV-TestProject")

TARGET_TREE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "src-tauri", "target"))

_USER32 = ctypes.windll.user32
_WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


def kill_strays():
    """Kill only dev/release builds from THIS repo's target tree; the
    owner's experience client (installed elsewhere) is never matched."""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"$tree = '{TARGET_TREE}'; "
         "Get-CimInstance Win32_Process -Filter \"Name='ai-project-viewer.exe'\" | "
         "Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($tree) } | "
         "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
        capture_output=True)


def kill_tree(proc):
    """Terminate our child including its WebView2 subprocesses (PID-scoped,
    never name-scoped)."""
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                   capture_output=True)


def window_of(pid, timeout_s=12):
    """First visible top-level window owned by pid (title-free match).
    Returns 0 on timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        hits = []

        def cb(hwnd, _):
            if _USER32.IsWindowVisible(hwnd):
                owner = wt.DWORD()
                _USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                if owner.value == pid:
                    hits.append(hwnd)
            return True

        _USER32.EnumWindows(_WNDENUMPROC(cb), 0)
        if hits:
            return hits[0]
        time.sleep(0.25)
    return 0


def park_offscreen(hwnd):
    """AIV_HIDDEN already keeps the window hidden; this belt-and-suspenders
    move keeps any straggler paint off the owner's monitors without
    activating it."""
    _USER32.SetWindowPos(hwnd, 0, -2500, -100, 0, 0,
                         0x0001 | 0x0010 | 0x0004)  # NOSIZE|NOZORDER|NOACTIVATE
    _USER32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE


def _assert_dev_binary(exe):
    """Refuse to launch an EXPERIENCE build (identifier .exp): publishing
    used to overwrite target\\release with the exp binary, which then
    single-instance handed off to the owner's RUNNING client and died in
    ~100ms (2026-10-10). A quick byte-scan makes that class impossible to
    miss again."""
    with open(exe, "rb") as f:
        blob = f.read()
    if b"com.aiprojectviewer.app.exp" in blob:
        raise RuntimeError(
            f"{exe} is an EXPERIENCE build (exp identifier embedded) — "
            "rebuild the dev binary (pnpm tauri build --no-bundle); "
            "publishing now outputs to src-tauri/target-exp.")


def _assert_fresh_build(exe):
    """L29 guard (4th recurrence 2026-11-05): a plain `cargo build
    --release` exe passes the exp scan above but lacks custom-protocol and
    serves a dead devUrl — every suite then burns its full timeout on a
    blank page. Any source file newer than the exe means the binary
    predates the code under test; refuse instead of timing out."""
    exe_mt = os.path.getmtime(exe)
    repo = os.path.abspath(os.path.join(os.path.dirname(exe), "..", ".."))
    newest = 0.0
    tops = ["src", "public", "src-tauri/src", "src-tauri/tauri.conf.json",
            "src-tauri/Cargo.toml", "package.json", "index.html",
            "vite.config.ts", "svelte.config.js"]
    for rel in tops:
        p = os.path.join(repo, rel)
        if os.path.isfile(p):
            newest = max(newest, os.path.getmtime(p))
        elif os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                if "target" in root or "node_modules" in root:
                    _dirs[:] = []
                    continue
                for fn in files:
                    newest = max(newest, os.path.getmtime(os.path.join(root, fn)))
    if newest > exe_mt + 2:  # 2s clock/fs skew allowance
        raise RuntimeError(
            f"stale binary: {exe} predates the repo sources (L29) — run "
            "`pnpm tauri build --no-bundle` before launching e2e")


def launch(exe, project, state, cdp, hidden=True, stdout=None,
           keep_state=False):
    """Standard test launch: straggler sweep (repo tree only), fresh state
    file, env for zero-foreground + CDP. Returns the Popen handle.
    keep_state=True preserves a pre-existing state file (restart-restore
    scenarios); the fresh-file deletion stays the default."""
    _assert_dev_binary(exe)
    _assert_fresh_build(exe)
    kill_strays()
    if os.path.exists(state) and not keep_state:
        os.remove(state)
    env = {**os.environ, "AIV_TEST_PROJECT": project, "AIV_STATE_FILE": state,
           "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS":
               f"--remote-debugging-port={cdp}"}
    if hidden:
        env["AIV_HIDDEN"] = "1"
    return subprocess.Popen(
        [exe], env=env, stdout=stdout,
        stderr=subprocess.STDOUT if stdout else None)
