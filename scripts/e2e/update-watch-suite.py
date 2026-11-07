"""spec-019 update-watch suite: the running client must light its Update
button the moment a new build lands in updates\\ (owner 2026-11-05 "你去点
亮 update"). Fakes the experience LAYOUT with the dev exe — the updater
keys off the folder layout, not the build identifier — so the whole
watch->event->refresh chain runs for real. Layout:

  %TEMP%\\aiv-upd-watch\\app\\ai-project-viewer.exe   (copy of dev release)
  %TEMP%\\aiv-upd-watch\\updates\\{exe, update.json}

Phases: boot with a SAME-CONTENT exe staged (button stays grey) ->
atomic-publish a DIFFERENT exe + new note (button lights within 3s,
hover carries the new note) -> publish the same content back (button
returns grey). Atomic writes mimic publish-experience.ps1 (staging name
+ os.replace)."""
import json
import os
import shutil
import subprocess
import time

import psutil

import aivlaunch
from playwright.sync_api import sync_playwright

EXE = os.path.join(os.path.dirname(__file__), "..", "..",
                   "src-tauri", "target", "release", "ai-project-viewer.exe")
PROJECT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "AIV-TestProject")
ROOT = os.path.join(os.environ["TEMP"], "aiv-upd-watch")
STATE = os.path.join(os.environ["TEMP"], "aiv-upd-watch.json")
CDP = 9263

results = {}
FAIL = []


def check(name, ok, detail=""):
    results[name] = "PASS" if ok else f"FAIL {detail}"
    if not ok:
        FAIL.append(name)
    print(f"{name}: {results[name]}")


def replace_with_retry(src: str, dst: str):
    """os.replace with retry: the client's md5 stream briefly holds the
    target without FILE_SHARE_DELETE (same live catch as the publish
    script's Move-Atomic)."""
    for _ in range(20):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(0.25)
    raise PermissionError(f"rename kept being denied: {src} -> {dst}")


def stage(content: bytes, note: str):
    """Atomic publish exactly like publish-experience.ps1 (staging + rename)."""
    exe_tmp = os.path.join(ROOT, "updates", "ai-project-viewer.exe.staging")
    with open(exe_tmp, "wb") as f:
        f.write(content)
    replace_with_retry(exe_tmp, os.path.join(ROOT, "updates", "ai-project-viewer.exe"))
    json_tmp = os.path.join(ROOT, "updates", "update.json.staging")
    with open(json_tmp, "w", encoding="utf-8") as f:
        json.dump({"note": note}, f)
    replace_with_retry(json_tmp, os.path.join(ROOT, "updates", "update.json"))


# Layout + boot-time staged SAME content (md5 equal -> button must stay grey).
shutil.rmtree(ROOT, ignore_errors=True)
os.makedirs(os.path.join(ROOT, "app"))
os.makedirs(os.path.join(ROOT, "updates"))
APP_EXE = os.path.join(ROOT, "app", "ai-project-viewer.exe")
shutil.copyfile(EXE, APP_EXE)
with open(EXE, "rb") as f:
    SAME = f.read()
DIFF = SAME + b"\0spec-019-different-build"

with open(STATE, "w", encoding="utf-8") as f:
    json.dump({"version": 1, "projects": [], "settings": {}}, f)

stage(SAME, "[0.0.1 | boot] same content")

proc = aivlaunch.launch(APP_EXE, PROJECT, STATE, CDP, keep_state=True)
_hwnd = aivlaunch.window_of(proc.pid)
if _hwnd:
    aivlaunch.park_offscreen(_hwnd)

with sync_playwright() as p:
    for _ in range(60):
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
            break
        except Exception:
            time.sleep(0.5)
    page = browser.contexts[0].pages[0]
    try:
        page.wait_for_selector(".update-btn", timeout=25000)
    except Exception:
        # L29: a bare `cargo build --release` exe has no embedded frontend
        # (ERR_CONNECTION_REFUSED on about:blank). If that was the last
        # build step before this suite, rebuild properly and rerun.
        print("HINT: page never became ready — if the last build was a bare "
              "`cargo build --release`, run `pnpm tauri build --no-bundle` "
              "first (lessons L29, sixth sighting 2026-11-07).")
        raise

    def btn_class():
        return page.locator(".update-btn").get_attribute("class") or ""

    def wait_for(pred, timeout_s, step=0.2):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if pred():
                return True
            time.sleep(step)
        return False

    # V2/V4 half: same-content staged at boot -> grey, hover shows note.
    time.sleep(1.0)  # mount check settles
    check("boot_same_content_stays_grey",
          "available" not in btn_class() and "busy" not in btn_class(),
          btn_class())

    # V1: publish (atomic) a DIFFERENT build while the app runs -> lights.
    stage(DIFF, "[0.0.2 | live] fresh build")
    lit = wait_for(lambda: "available" in btn_class(), timeout_s=8)
    title = page.locator(".update-btn").get_attribute("title") or ""
    check("live_publish_lights_button",
          lit and "0.0.2" in title and "fresh build" in title,
          f"lit={lit} title={title!r}")

    # Same content published back -> grey again (md5 gate, not mere events).
    stage(SAME, "[0.0.1 | boot] same content")
    grey = wait_for(lambda: "available" not in btn_class(), timeout_s=8)
    check("same_content_republish_goes_grey", grey, btn_class())

# --- 0.8.23 guard (owner 2026-11-07: "点完 update 没有自动重启,软件自己
# 关了"): the relaunched child used to race the single-instance lock while
# the dying parent still held it — the plugin retired the child quietly
# and both generations were gone. Fix: updater::relaunch stamps the parent
# PID into the env; the child waits on that PROCESS HANDLE before any
# plugin initializes. The handoff window is artificially widened (parent
# killed 400ms after the child spawns). BOTH arms must hold — control
# (no flag) proves the scenario still kills, treatment (flag) proves the
# wait structurally rescues the child. ---
def handoff_arm(with_flag: bool) -> bool:
    # 9298: the main instance above still owns CDP; the arms never talk CDP
    # anyway (fate is judged by PID aliveness).
    parent = aivlaunch.launch(APP_EXE, PROJECT, STATE, 9298, keep_state=True)
    time.sleep(2.5)  # parent fully owns the single-instance lock
    child_env = {**os.environ, "AIV_TEST_PROJECT": PROJECT,
                 "AIV_STATE_FILE": STATE,
                 "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS":
                     "--remote-debugging-port=9299",
                 "AIV_HIDDEN": "1"}
    if with_flag:
        child_env["AIV_RELAUNCH_PARENT"] = str(parent.pid)
    child = subprocess.Popen([APP_EXE], env=child_env,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    time.sleep(0.4)   # parent still alive: the widened race window
    aivlaunch.kill_tree(parent)
    time.sleep(3.0)   # let the child's fate settle (wait ≤2s + init)
    alive = psutil.pid_exists(child.pid)
    aivlaunch.kill_tree(child)
    time.sleep(0.5)
    return alive

# The MAIN instance must be gone BEFORE the arms run: it owns the
# single-instance lock, so every arm parent would be retired by IT (not by
# the handoff race the guard is pinning).
aivlaunch.kill_tree(proc)
time.sleep(1.0)

ctrl_alive = handoff_arm(with_flag=False)
treat_alive = handoff_arm(with_flag=True)
check("relaunch_handoff_flag_waits_for_parent",
      (not ctrl_alive) and treat_alive,
      f"control_alive={ctrl_alive} treatment_alive={treat_alive}")
time.sleep(1.0)  # exe handles release before the layout teardown below

shutil.rmtree(ROOT, ignore_errors=True)

print(json.dumps(results, indent=1, ensure_ascii=False))
print("VERDICT:", "PASS" if not FAIL else f"FAIL ({len(FAIL)}): {FAIL}")
raise SystemExit(1 if FAIL else 0)
