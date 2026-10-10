# -*- coding: utf-8 -*-
"""Phase 3 viewer regression (self-launching, zero disturbance).
Was a replay script expecting an app on :9222; formalized 2026-10-10 with
the standard launcher (AIV_HIDDEN + off-screen + CDP). All process/window
handling goes through aivlaunch (owner-isolation: PID-scoped only)."""
import atexit
import json
import os
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = os.path.join(os.path.dirname(__file__), "..", "..",
                   "src-tauri", "target", "release", "ai-project-viewer.exe")
PROJECT = os.path.expandvars(r"%USERPROFILE%\Desktop\AIV-TestProject")
STATE = os.path.join(os.environ["TEMP"], "aiv-p3suite.json")
CDP = 9257

proc = aivlaunch.launch(os.path.abspath(EXE), PROJECT, STATE, CDP)
_hwnd = aivlaunch.window_of(proc.pid)
if _hwnd:
    aivlaunch.park_offscreen(_hwnd)

def _cleanup():
    aivlaunch.kill_tree(proc)

atexit.register(_cleanup)


results = {}
FAIL = []

def check(name, ok, detail=""):
    results[name] = "PASS" if ok else f"FAIL {detail}"
    if not ok:
        FAIL.append(name)

with sync_playwright() as p:
    for _ in range(60):
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
            break
        except Exception:
            time.sleep(0.5)
    page = browser.contexts[0].pages[0]
    page.wait_for_selector(".file-tree", timeout=25000)

    def tree_row(name):
        return page.locator(".file-tree .row", has=page.locator(".name", has_text=name)).first

    def expand(rel_name):
        row = tree_row(rel_name)
        if row.get_attribute("aria-expanded") != "true":
            row.click()
            time.sleep(0.5)

    def open_file(name):
        tree_row(name).click()
        deadline = time.time() + 6
        while time.time() < deadline:
            if page.locator(".file-tab.active .name").count() and page.locator(".file-tab.active .name").inner_text() == name:
                time.sleep(0.35)
                return
            time.sleep(0.15)
        raise TimeoutError(f"open_file({name})")

    def body_contains(sub, timeout_s=6):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if sub in page.locator(".viewer-body").inner_text():
                return True
            time.sleep(0.2)
        return False

    def press(key, shift=False):
        page.evaluate(
            """(o) => window.dispatchEvent(new KeyboardEvent('keydown',
               { key: o.k, ctrlKey: true, shiftKey: o.s, bubbles: true, cancelable: true }))""",
            {"k": key, "s": shift})

    def tab_count():
        return page.locator(".file-tab").count()

    # --- #3 regression: text -> text switch must show the NEW content ---
    expand("edge-cases")
    open_file("chinese-gb18030.txt")
    check("gb18030_shows", body_contains("编码兜底正确"))
    expand("src")
    open_file("main.py")
    check("text_to_text_switch", body_contains("Entry point"))
    open_file("utils.py")
    check("text_to_text_switch_2", body_contains("return a + b"))
    # html after text (owner's screenshot case)
    open_file("index.html")
    check("html_after_text", body_contains("<h1>HTML viewed as Code</h1>") or body_contains("HTML viewed as Code"))

    # --- #10 regression: image -> image switch shows the NEW image ---
    expand("assets")
    open_file("logo.svg")
    src1 = page.locator(".image-viewer img").get_attribute("src")
    open_file("photo.jpg")
    time.sleep(0.6)
    src2 = page.locator(".image-viewer img").get_attribute("src")
    check("image_to_image_switch", src2 is not None and src1 is not None and src2 != src1 and "image/jpeg" in src2)
    open_file("icon.gif")
    gif_src = page.locator(".image-viewer img").get_attribute("src") or ""
    check("gif_renders", gif_src.startswith("data:image/gif"), gif_src[:30])

    # --- #8 pin model (clarified): accumulate until pinned, then recycle ---
    n0 = tab_count()
    open_file("notes.txt")
    expand("data")
    open_file("sample.csv")
    n_after_two = tab_count()
    check("accumulate_when_unpinned", n_after_two >= 2, f"{n0} -> {n_after_two}")
    # pin the current tab; further opens must recycle unpinned slots
    page.locator(".file-tab.active").click(button="right")
    page.locator(".menu button", has_text="Pin Tab").click()
    time.sleep(0.2)
    open_file("server.log")
    open_file("metrics.json")
    check("recycle_after_pin", tab_count() == n_after_two, f"{n_after_two} -> {tab_count()}")
    check("pinned_survives", page.locator(".file-tab .pin").count() == 1)
    check("pinned_still_open", page.locator(".file-tab", has_text="sample.csv").count() == 1)

    # --- #5: md mode via tab menu ---
    open_file("README.md")
    page.locator(".file-tab.active").click(button="right")
    page.locator(".menu button", has_text="View Source").click()
    time.sleep(0.3)
    check("md_source_via_menu", page.locator(".code-viewer").count() == 1)
    page.locator(".file-tab.active").click(button="right")
    page.locator(".menu button", has_text="View Rendered").click()
    time.sleep(0.3)
    check("md_rendered_via_menu", page.locator(".markdown-viewer .rendered").count() == 1)

    # --- #1: tab strip auto-reveals active tab ---
    page.evaluate("""() => {
      const bar = document.querySelector('.file-tabs');
      if (bar) bar.scrollLeft = 0;
    }""")
    open_file("README.md")
    time.sleep(0.4)
    vis = page.evaluate("""() => {
      const el = document.querySelector('.file-tab.active');
      if (!el) return false;
      const r = el.getBoundingClientRect();
      const bar = document.querySelector('.file-tabs').getBoundingClientRect();
      return r.right <= bar.right + 1 && r.left >= bar.left - 1;
    }""")
    check("active_tab_scrolled_into_view", bool(vis))

    # --- #9: drag reorder tabs ---
    titles_before = page.locator(".file-tab .name").all_inner_texts()
    if len(titles_before) >= 2:
        a = page.locator(".file-tab").nth(0)
        b = page.locator(".file-tab").nth(1)
        ab = a.bounding_box(); bb = b.bounding_box()
        # aim at the RIGHT half of tab[1]: drop-after semantics swap them
        tx = bb["x"] + bb["width"] * 0.75
        page.mouse.move(ab["x"] + 20, ab["y"] + ab["height"] / 2)
        page.mouse.down()
        for i in range(1, 11):
            page.mouse.move(ab["x"] + 20 + (tx - ab["x"] - 20) * i / 10, ab["y"] + ab["height"] / 2, steps=1)
            time.sleep(0.02)
        page.mouse.up()
        time.sleep(0.3)
        titles_after = page.locator(".file-tab .name").all_inner_texts()
        check("tab_drag_reorder", titles_before != titles_after, f"{titles_before} -> {titles_after}")
    else:
        check("tab_drag_reorder", False, "not enough tabs")

    # --- #4: font size setting applies ---
    page.click('button[title="Settings"]')
    time.sleep(0.3)
    before = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--viewer-font-size')")
    page.locator('button[aria-label="Larger font"]').click()
    time.sleep(0.2)
    after = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--viewer-font-size')")
    page.click('button[title="Settings"]')
    check("font_size_setting", before.strip() != after.strip(), f"{before} -> {after}")

    # --- #7: light theme viewer surface is white ---
    page.click('button[title="Settings"]')
    time.sleep(0.3)
    page.locator('input[name="theme"][value="light"]').check()
    time.sleep(0.3)
    page.click('button[title="Settings"]')
    bg = page.evaluate("() => getComputedStyle(document.querySelector('.viewer')).backgroundColor")
    check("light_viewer_white", bg in ("rgb(255, 255, 255)", "#ffffff"), bg)
    # back to system
    page.click('button[title="Settings"]')
    page.locator('input[name="theme"][value="system"]').check()
    page.click('button[title="Settings"]')

    # --- #2: active tab has accent styling ---
    open_file("README.md")
    styled = page.evaluate("""() => {
      const el = document.querySelector('.file-tab.active');
      return el && getComputedStyle(el, '::after').content !== 'none';
    }""")
    check("active_tab_accent", bool(styled))

    # --- SPEC-INFRA-003: unified viewer toolbar (font + find) + centered MD ---
    check("md_toolbar_present", page.locator(".markdown-viewer .vtb").count() == 1)
    before = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--viewer-font-size')")
    page.locator('.markdown-viewer .vtb button[aria-label="Larger text"]').click()
    time.sleep(0.2)
    after = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--viewer-font-size')")
    check("toolbar_font_grows", before.strip() != after.strip(), f"{before} -> {after}")
    page.locator('.markdown-viewer .vtb button[aria-label="Smaller text"]').click()
    time.sleep(0.2)

    word = page.evaluate(r"""() => {
      const words = (document.querySelector('.markdown-viewer .rendered').innerText || '')
        .split(/\s+/).filter(w => w.length >= 5);
      return words[0] || '';
    }""")
    md_find = page.evaluate(r"""async (w) => {
      const inp = document.querySelector('.markdown-viewer .vtb .search');
      const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      set.call(inp, w);
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise(r => setTimeout(r, 250));
      const labels = [...document.querySelectorAll('.markdown-viewer .vtb .tb-label')]
        .map(e => e.textContent.trim());
      inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      await new Promise(r => setTimeout(r, 250));
      return { labels, sel: (document.getSelection() || '').toString() };
    }""", word)
    check("md_find_counts_and_jumps",
          any("/" in t for t in md_find["labels"]) and md_find["sel"] == word,
          f"word={word!r} labels={md_find['labels']} sel={md_find['sel']!r}")

    # owner 2026-10-10: toolbars must sit at the SAME height in every viewer
    # (the old .code-host/.host/.source-host 8px paddings pushed code/json
    # toolbars down — MD's was flush). Measure MD's BEFORE switching away
    # (inactive viewers unmount), then compare against the code viewer's.
    md_tb = page.evaluate(r"""() => {
      const el = document.querySelector('.markdown-viewer .vtb');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { y: Math.round(r.y), h: Math.round(r.height) };
    }""")
    open_file("main.py")
    check("code_toolbar_present", page.locator(".code-viewer .vtb").count() == 1)
    code_tb = page.evaluate(r"""() => {
      const el = document.querySelector('.code-viewer .vtb');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { y: Math.round(r.y), h: Math.round(r.height) };
    }""")
    check("toolbar_aligned_md_vs_code",
          md_tb and code_tb and abs(md_tb["y"] - code_tb["y"]) <= 1
          and abs(md_tb["h"] - code_tb["h"]) <= 1,
          f"md={md_tb} code={code_tb}")
    code_find = page.evaluate(r"""async () => {
      const inp = document.querySelector('.code-viewer .vtb .search');
      const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      set.call(inp, 'Entry');
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise(r => setTimeout(r, 300));
      const labels = [...document.querySelectorAll('.code-viewer .vtb .tb-label')]
        .map(e => e.textContent.trim());
      return labels;
    }""")
    check("code_find_counts", any("/" in t for t in code_find), str(code_find))

    # centered reading column + resize guard (owner 2026-10-10 bug class)
    open_file("README.md")
    cdp = page.context.new_cdp_session(page)
    cdp.send("Emulation.setDeviceMetricsOverride",
             {"width": 1600, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(0.8)
    # owner 2026-10-10 round 2: "MD 右侧空白还是很明显" — assert against the
    # OWNER's words (no big blank band), not against a fix's own invention:
    # the reading column must have no max-width cap and a long paragraph
    # must reach across the text area.
    fills = page.evaluate(r"""() => {
      const el = document.querySelector('.markdown-viewer .rendered');
      if (!el) return { ok: false, why: 'no .rendered' };
      const cap = getComputedStyle(el).maxWidth;
      const parentW = el.parentElement.getBoundingClientRect().width;
      const blocks = [...el.querySelectorAll('p, li, h1, h2, h3, h4, pre')]
        .filter(x => (x.innerText || '').trim().length > 30);
      const pw = blocks.length
        ? Math.round(Math.max(...blocks.map(b => b.getBoundingClientRect().width)))
        : -1;
      return { cap, pw, parentW: Math.round(parentW),
               ok: cap === 'none' && pw >= parentW - 80 };
    }""")
    check("md_text_fills_area", bool(fills["ok"]),
          f"cap={fills['cap']} paraW={fills['pw']} parentW={fills['parentW']}")
    open_file("metrics.json")
    ok_json = page.locator(".code-viewer").count() == 1
    open_file("README.md")
    ok_md = page.locator(".markdown-viewer .rendered").count() == 1
    check("resize_then_cross_type_switch", ok_json and ok_md,
          f"json={ok_json} md={ok_md}")
    cdp.send("Emulation.clearDeviceMetricsOverride")

    # --- spec-006 (Phase 6 HANDOFF): typed context menus + copy feedback ---
    def menu_ids_of(open_fn):
        open_fn()
        page.wait_for_selector(".menu [data-menu-id]", timeout=4000)
        ids = page.eval_on_selector_all(
            ".menu [data-menu-id]", "els => els.map(e => e.dataset.menuId)")
        page.mouse.click(400, 250)  # outside-mousedown closes (capture)
        time.sleep(0.25)
        return set(ids)

    def tree_menu(row_name):
        return lambda: tree_row(row_name).click(button="right")

    expand("pdf")
    expand("edge-cases")

    m_md = menu_ids_of(tree_menu("README.md"))
    check("handoff_tree_textlike", m_md >= {"open", "notepad", "vscode",
          "reveal", "copy-abs", "copy-rel"} and "default-app" not in m_md,
          str(sorted(m_md)))
    m_dir = menu_ids_of(tree_menu("src"))
    check("handoff_tree_folder", m_dir == {"open", "reveal", "copy-abs",
          "copy-rel", "vscode-folder"}, str(sorted(m_dir)))
    m_pdf = menu_ids_of(tree_menu("tab-1.pdf"))
    check("handoff_tree_pdf", m_pdf == {"open", "pdf-app", "reveal",
          "copy-abs", "copy-rel"}, str(sorted(m_pdf)))
    m_img = menu_ids_of(tree_menu("photo.jpg"))
    check("handoff_tree_image", m_img == {"open", "default-app", "reveal",
          "copy-abs", "copy-rel"}, str(sorted(m_img)))
    m_exe = menu_ids_of(tree_menu("demo.exe"))
    check("handoff_tree_exe", m_exe == {"reveal", "copy-abs", "copy-rel"},
          str(sorted(m_exe)))
    m_html = menu_ids_of(tree_menu("index.html"))
    m_url = menu_ids_of(tree_menu("example.url"))
    check("handoff_tree_browser", "browser" in m_html and "browser" in m_url
          and m_html >= {"notepad", "vscode"} and m_url >= {"notepad", "vscode"},
          f"html={sorted(m_html)} url={sorted(m_url)}")

    # V10: the tab menu is fed by the SAME builder — entry sets must match
    # (tab never carries the in-app "open").
    open_file("README.md")
    m_tab = menu_ids_of(
        lambda: page.locator(".file-tab.active").click(button="right"))
    check("handoff_tab_same_as_tree", m_tab == (m_md - {"open"}),
          f"tree={sorted(m_md)} tab={sorted(m_tab)}")
    page.locator(".file-tab.active").click(button="right")
    # README is in rendered mode here, so the toggle reads "View Source"
    # ("View Rendered" only appears while in source mode).
    legacy = (page.locator(".menu button", has_text="View Source").count() == 1
              and page.locator(".menu button", has_text="Pin Tab").count() == 1
              and page.locator(".menu button", has_text="Close Tab").count() == 1)
    page.mouse.click(400, 250)
    check("handoff_tab_legacy_kept", legacy, "View Source/Pin Tab/Close Tab missing")

    # Project tab menu (§141)
    m_proj = menu_ids_of(
        lambda: page.locator(".project-tabs .tab.active").click(button="right"))
    check("handoff_project_menu", m_proj == {"project-explorer",
          "copy-project-path", "project-vscode"}, str(sorted(m_proj)))
    page.locator(".project-tabs .tab.active").click(button="right")
    has_remove = page.locator(".menu button", has_text="Remove Project").count() == 1
    page.mouse.click(400, 250)
    check("handoff_project_remove_kept", has_remove, "Remove Project missing")

    # Copy feedback (V6): the toast names what landed on the clipboard.
    # (No clipboard readback here: WebView2 may raise a native permission
    #  prompt that blocks the evaluate call — the toast IS the oracle.)
    tree_row("chinese-gb18030.txt").click(button="right")
    # dispatch_event, not click(): this suite earlier used CDP viewport
    # emulation (resize test) and Playwright's cached viewport then
    # misjudges position:fixed menu items as "outside of the viewport"
    # even when the DOM rect is inside. Menu logic is the test target,
    # not pointer hit-testing.
    page.locator(".menu [data-menu-id='copy-rel']").dispatch_event("click")
    rel_toast = page.wait_for_selector(".toast").inner_text()
    check("copy_rel_feedback",
          "edge-cases/chinese-gb18030.txt" in rel_toast, repr(rel_toast))
    time.sleep(1.0)  # let the toast clear
    # A top row: the menu opens AT the click point, so a bottom row would
    # place its items below the viewport (unclickable).
    tree_row("README.md").click(button="right")
    page.locator(".menu [data-menu-id='copy-abs']").dispatch_event("click")
    abs_toast = page.wait_for_selector(".toast").inner_text()
    check("copy_abs_feedback", "AIV-TestProject" in abs_toast
          and "\\README.md" in abs_toast, abs_toast)

    # §134 VS Code Mode: default New Window + persisted on toggle (V5)
    page.click('button[title="Settings"]')
    time.sleep(0.3)
    radios = page.locator('input[name="vscode-mode"]')
    default_new = radios.nth(0).is_checked()
    radios.nth(1).check()
    time.sleep(1.4)  # save debounce is 800ms
    with open(STATE, encoding="utf-8") as f:
        persisted = json.load(f)
    page.click('button[title="Settings"]')
    check("vscode_mode_setting",
          default_new
          and persisted["settings"]["external"]["vsCodeNewWindow"] is False,
          f"default_new={default_new} persisted={persisted.get('settings', {}).get('external')}")

    # --- 0.6.3 rework: tree highlight must BE the active tab; opening a
    # file in a collapsed folder must expand the chain and reveal the row
    # (owner: "左侧文件树高亮显示的文件和文件区高亮显示的文件不一致"). ---

    def active_tree_names():
        return page.eval_on_selector_all(
            ".file-tree .row.selected .name",
            "els => els.map(e => e.textContent.trim())")

    # open a DEEP file once (expand by hand; open_file waits for the tab).
    # NOTE: sample.csv is PINNED (earlier pin-model test) and survives the
    # unpinned-slot recycling — it is the stable "other" tab here; README's
    # tab was recycled away by design, so don't look for it.
    expand("deep")
    expand("migrations")
    open_file("001_init.sql")

    # activate via the TAB STRIP — the tree must follow, not the reverse
    page.locator(".file-tab", has_text="sample.csv").first.click()
    time.sleep(0.4)
    hl_csv = active_tree_names() == ["sample.csv"]
    page.locator(".file-tab", has_text="001_init.sql").first.click()
    time.sleep(0.8)
    hl_deep = active_tree_names() == ["001_init.sql"]
    check("tree_highlight_follows_active_tab", hl_csv and hl_deep,
          f"csv={hl_csv} deep={hl_deep} got={active_tree_names()}")

    # reveal: collapse the whole chain, then re-activate the deep tab —
    # the chain must re-expand and the row land INSIDE the scroll viewport
    for folder in ("migrations", "deep", "src"):
        row = tree_row(folder)
        if row.get_attribute("aria-expanded") == "true":
            row.click()
            time.sleep(0.25)
    collapsed = tree_row("src").get_attribute("aria-expanded") != "true"
    page.locator(".file-tab", has_text="001_init.sql").first.click()
    time.sleep(1.2)
    vis = page.evaluate(r"""() => {
      const rows = [...document.querySelectorAll('.file-tree .row')];
      const row = rows.find(r => r.title === 'src/deep/migrations/001_init.sql');
      if (!row) return { ok: false, why: 'row not in DOM' };
      const t = row.getBoundingClientRect();
      const tree = document.querySelector('.file-tree').getBoundingClientRect();
      return { ok: t.top >= tree.top && t.bottom <= tree.bottom, why: '' };
    }""")
    exp = all(
        tree_row(f).get_attribute("aria-expanded") == "true"
        for f in ("src", "deep", "migrations")
    )
    check("tab_activation_reveals_in_tree",
          collapsed and exp and bool(vis["ok"]),
          f"collapsed_first={collapsed} expanded_after={exp} visible={vis}")

    # --- menu clamp (owner: "左下角文件右键菜单显示不完整") ---
    clamped = page.evaluate(r"""() => {
      const row = [...document.querySelectorAll('.file-tree .row')]
        .find(r => r.title === 'notes.txt');
      if (!row) return { ok: false, why: 'no row' };
      row.dispatchEvent(new MouseEvent('contextmenu', {
        clientX: 10, clientY: innerHeight - 15, bubbles: true, cancelable: true }));
      return new Promise(res => setTimeout(() => {
        const m = document.querySelector('.menu');
        if (!m) { res({ ok: false, why: 'no menu' }); return; }
        const r = m.getBoundingClientRect();
        document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        res({ ok: r.bottom <= innerHeight - 2 && r.right <= innerWidth - 2
                   && r.top >= 0 && r.left >= 0,
              why: `rect=${Math.round(r.top)},${Math.round(r.bottom)} vh=${innerHeight}` });
      }, 350));
    }""")
    check("menu_clamped_to_viewport", bool(clamped.get("ok")), str(clamped))

    # --- 0.6.4: re-expand re-lists (owner: "文件夹里增加了文件,仍然是空的") ---
    # The old cache short-circuit made collapse+re-expand serve the stale
    # listing forever. Uses the EXISTING data/ folder (expanded earlier in
    # this run) — a folder created mid-session wouldn't be in the root
    # listing at all (that's Refresh/Phase-9-watcher territory).
    probe = os.path.join(PROJECT, "data", "zz-probe-late.txt")
    try:
        before = page.eval_on_selector_all(
            ".file-tree .row", "els => els.map(e => e.getAttribute('title') || '').filter(t => t.startsWith('data/'))")
        open(probe, "w").write("late")
        tree_row("data").click()   # collapse
        time.sleep(0.3)
        tree_row("data").click()   # re-expand — must re-list from disk
        time.sleep(1.0)
        after = page.eval_on_selector_all(
            ".file-tree .row", "els => els.map(e => e.getAttribute('title') || '').filter(t => t.startsWith('data/'))")
        check("reexpand_relisa_after_disk_add",
              "data/zz-probe-late.txt" not in before
              and "data/zz-probe-late.txt" in after,
              f"before={before} after={after}")

        # --- 0.6.5: header refresh icon (owner: "Refresh 放到 Settings 的
        # 左侧,不显示单词") — icon-only, LEFT of ⚙, one click re-lists. ---
        geo = page.evaluate("""() => {
          const r = document.querySelector('.sidebar-header .refresh');
          const s = document.querySelector('.sidebar-header .settings');
          if (!r || !s) return { ok: false, why: 'button(s) missing' };
          const a = r.getBoundingClientRect(), b = s.getBoundingClientRect();
          return { ok: a.right <= b.left + 1 && r.textContent.trim().length <= 2,
                   x: Math.round(a.right), sx: Math.round(b.left),
                   glyph: r.textContent.trim() };
        }""")
        os.remove(probe)   # disk change WITHOUT touching the folder
        page.locator('.sidebar-header .refresh').click()
        time.sleep(1.2)
        gone = page.eval_on_selector_all(
            ".file-tree .row", "els => els.map(e => e.getAttribute('title') || '').filter(t => t.startsWith('data/'))")
        check("header_refresh_icon",
              bool(geo.get("ok")) and "data/zz-probe-late.txt" not in gone,
              f"geo={geo} after={gone}")
    finally:
        if os.path.exists(probe):
            os.remove(probe)

print(json.dumps(results, indent=1, ensure_ascii=False))
print("VERDICT:", "PASS" if not FAIL else f"FAIL ({len(FAIL)}): {FAIL}")
