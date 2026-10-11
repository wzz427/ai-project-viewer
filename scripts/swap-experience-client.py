#!/usr/bin/env python3
"""Manually swap the owner's experience client binary in place.

Use ONLY when the running client cannot self-update (e.g. frozen UI makes
the Update button unclickable) and the owner has authorized a manual swap.
Method of record: docs/handoff.md, 0.7.2 entry. Steps:

  1. locate staged update at  %LOCALAPPDATA%\\AIProjectViewer\\updates\\ai-project-viewer.exe
  2. kill every process whose image path IS app\\ai-project-viewer.exe
     (path-equality filter -- never kill by bare process name)
  3. copy update -> app\\ai-project-viewer.exe.new, verify md5(update)==md5(.new)
     and assert the binary is the exp build (identifier string present)
  4. os.replace(old -> .old); os.replace(.new -> app exe)
     (.old/.new leftovers are auto-cleaned by the app at next boot)
  5. Start-Process the new exe, verify Responding=True and FileVersion

Default run is a dry-run preview; pass --yes to execute the swap.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(os.environ["LOCALAPPDATA"]) / "AIProjectViewer"
APP_EXE = BASE / "app" / "ai-project-viewer.exe"
UPDATE_EXE = BASE / "updates" / "ai-project-viewer.exe"
EXP_IDENTIFIER = b"com.aiprojectviewer.app.exp"


def psq(s: str) -> str:
    """Escape for a PowerShell single-quoted string (spec-012 L-c5): a '
    inside LOCALAPPDATA would otherwise terminate the literal early."""
    return s.replace("'", "''")


def ps(command: str) -> str:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        raise RuntimeError(f"powershell failed: {out.stderr.strip()}")
    return out.stdout.strip()


def file_version(path: Path) -> str:
    return ps(f"(Get-Item -LiteralPath '{psq(str(path))}').VersionInfo.FileVersion")


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def contains_bytes(path: Path, needle: bytes) -> bool:
    overlap = len(needle) - 1
    prev = b""
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                return False
            if needle in prev + chunk:
                return True
            prev = chunk[-overlap:] if overlap else b""


def running_pids() -> list[int]:
    # Path-equality filter only -- the kill-by-name shortcut is forbidden
    # (e2e/test instances may share the process name).
    out = ps(
        f"Get-CimInstance Win32_Process -Filter \"Name='ai-project-viewer.exe'\" | "
        f"Where-Object {{ $_.ExecutablePath -ieq '{psq(str(APP_EXE))}' }} | "
        f"ForEach-Object {{ $_.ProcessId }}"
    )
    return [int(x) for x in out.split()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--yes", action="store_true", help="execute (default: dry-run preview)")
    args = ap.parse_args()

    if not UPDATE_EXE.is_file():
        print(f"[abort] staged update not found: {UPDATE_EXE}")
        return 1
    if not APP_EXE.is_file():
        print(f"[abort] client exe not found: {APP_EXE}")
        return 1

    pids = running_pids()
    print(f"staged update : {UPDATE_EXE}  v{file_version(UPDATE_EXE)}")
    print(f"installed exe : {APP_EXE}  v{file_version(APP_EXE)}")
    print(f"running (by path): {pids or 'none'}")

    if not args.yes:
        print("\n[dry-run] re-run with --yes to: kill those pids -> swap -> relaunch.")
        return 0

    for pid in pids:
        ps(f"Stop-Process -Id {pid} -Force")
    for _ in range(20):
        if not running_pids():
            break
        time.sleep(0.5)
    if running_pids():
        print("[abort] process still alive after kill, no files touched")
        return 1

    staged = APP_EXE.with_suffix(".exe.new")
    # Streamed copy + streamed marker scan (spec-012 L-c5): whole-exe
    # read_bytes() holds the binary in RAM twice; chunked = same O(1MB)
    # footprint as the Rust updater's own swap path.
    shutil.copyfile(UPDATE_EXE, staged)
    if md5(UPDATE_EXE) != md5(staged):
        staged.unlink(missing_ok=True)
        print("[abort] md5 mismatch after copy, no files touched")
        return 1
    if not contains_bytes(staged, EXP_IDENTIFIER):
        staged.unlink(missing_ok=True)
        print("[abort] staged binary is not an exp build, no files touched")
        return 1

    os.replace(APP_EXE, APP_EXE.with_suffix(".exe.old"))
    os.replace(staged, APP_EXE)
    print(f"swapped -> v{file_version(APP_EXE)} (old exe kept as .old, auto-cleaned at next boot)")

    pid = int(ps(f"(Start-Process -FilePath '{APP_EXE}' -PassThru).Id"))
    time.sleep(4)
    responding = ps(f"(Get-Process -Id {pid}).Responding")
    print(f"relaunched pid={pid} Responding={responding} FileVersion={file_version(APP_EXE)}")
    if responding.lower() != "true":
        print("[warn] window not responding after relaunch -- investigate before walking away")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
