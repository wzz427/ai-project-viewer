# -*- coding: utf-8 -*-
"""Phase 3 viewer regression (self-launching, zero disturbance).
Was a replay script expecting an app on :9222; formalized 2026-10-10 with
the standard launcher (AIV_HIDDEN + off-screen + CDP). All process/window
handling goes through aivlaunch (owner-isolation: PID-scoped only)."""
import atexit
import json
import os
import shutil
import time

from playwright.sync_api import sync_playwright

import aivlaunch

EXE = os.path.join(os.path.dirname(__file__), "..", "..",
                   "src-tauri", "target", "release", "ai-project-viewer.exe")
PROJECT = os.path.expandvars(r"%USERPROFILE%\Desktop\AIV-TestProject")
STATE = os.path.join(os.environ["TEMP"], "aiv-p3suite.json")
CDP = 9257

# --- 0.8.6 away-project fixture + state seed: a second project tab with a
# persisted-expanded subfolder, so the tail guard can prove that a write
# landing in a NON-active project becomes visible when the user switches
# back (owner 2026-10-17 staleness report — the tree used to serve the
# stale cached level until a manual collapse/re-expand). ---
AWAY_B = os.path.join(os.environ["TEMP"], "aiv-p3-away")
shutil.rmtree(AWAY_B, ignore_errors=True)
os.makedirs(os.path.join(AWAY_B, "sub"))
with open(os.path.join(AWAY_B, "sub", "seed.txt"), "w", encoding="utf-8") as f:
    f.write("seed\n")


def _seed_proj(pid, name, root, expanded):
    return {
        "id": pid, "name": name, "rootPath": root,
        "expandedFolders": expanded, "openFiles": [],
        "sidebarMode": "files", "sidebarWidth": 260,
        "trustedForExecution": False,
        "fileTreePreferences": {"foldersFirst": True, "pinnedItems": {}},
    }


with open(STATE, "w", encoding="utf-8") as f:
    json.dump({
        "version": 1,
        "projects": [
            _seed_proj("pa", "AIV-TestProject", os.path.abspath(PROJECT), []),
            _seed_proj("pb", "aiv-p3-away", AWAY_B, ["sub"]),
        ],
        "activeProjectId": "pa",
        "settings": {},
    }, f)

# keep_state=True keeps the seed above (launch deletes the file otherwise);
# AIV_TEST_PROJECT auto-add dedupes by rootPath, so PROJECT just activates.
proc = aivlaunch.launch(os.path.abspath(EXE), PROJECT, STATE, CDP,
                        keep_state=True)
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

    # --- 0.7.11 content-identity guard (owner 2026-10-12 field freeze:
    # tab strip AND viewer component class both stayed correct while the
    # content froze on the previous file — every suite asserted names and
    # classes, never CONTENT identity). The viewer's data-rel must equal
    # the active tab's file after every switch, and the body must carry
    # the new file's text — not the old one's. ---
    def viewer_rel():
        return page.evaluate(
            "() => document.querySelector('.viewer-body [data-rel]')"
            "?.getAttribute('data-rel') ?? null")

    open_file("main.py")
    r1 = viewer_rel()
    check("viewer_rel_matches_active",
          r1 is not None and r1.replace("\\", "/").endswith("/main.py")
          and body_contains("Entry point"),
          f"rel={r1}")
    open_file("index.html")
    r2 = viewer_rel()
    body2 = page.locator(".viewer-body").inner_text()
    check("viewer_identity_follows_switch",
          r2 is not None and r2.replace("\\", "/").endswith("/index.html")
          and "HTML viewed as Code" in body2 and "Entry point" not in body2,
          f"rel={r2}")

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

    # --- 0.7.23 paper-typography guards (owner direction C, demo-picked);
    # colors re-based 2026-10-14 onto the theme pack (paper default /
    # glacier) — bg/link assertions accept BOTH skins, the rest is skinless. ---
    m = page.evaluate("""() => {
        const r = document.querySelector('.rendered.md');
        const prose = r.querySelector('.prose');
        const h1 = r.querySelector('h1');
        const a = r.querySelector('a');
        const cb = r.querySelector('input[type="checkbox"]');
        return {
            bg: getComputedStyle(r).backgroundColor,
            size: getComputedStyle(r).fontSize,
            proseW: Math.round(prose.getBoundingClientRect().width),
            h1Font: getComputedStyle(h1).fontFamily,
            link: getComputedStyle(a).color,
            cbAppear: cb ? getComputedStyle(cb).appearance : null,
            kw: r.querySelectorAll('.hljs-keyword').length,
        };
    }""")
    check("md_paper_theme", m["bg"] in ("rgb(253, 253, 254)", "rgb(255, 252, 245)"), str(m["bg"]))
    check("md_font_uplift_15px", m["size"] == "15px", m["size"])
    check("md_measure_cap", 560 <= m["proseW"] <= 780, str(m["proseW"]))
    check("md_serif_heading", "Georgia" in m["h1Font"], m["h1Font"])
    check("md_link_accent_ink", m["link"] in ("rgb(21, 92, 204)", "rgb(139, 71, 31)"), m["link"])
    check("md_task_checkbox_drawn", m["cbAppear"] == "none", str(m["cbAppear"]))
    check("md_hljs_python_tokens", m["kw"] >= 1, str(m["kw"]))

    # --- 0.8.0 ink&paper chrome guards (owner 方案 C + 层次加强) ---
    chrome = page.evaluate("""() => {
        const band = document.querySelector('.project-tabs');
        const strip = document.querySelector('.file-tabs');
        const main = document.querySelector('.viewer-body');
        const ptA = document.querySelector('.project-tabs .tab.active');
        const ftA = document.querySelector('.file-tab.active');
        const rgb = (el) => el ? getComputedStyle(el).backgroundColor : null;
        const cs = ftA ? getComputedStyle(ftA, '::after') : null;
        return { band: rgb(band), strip: rgb(strip), paper: rgb(main),
                 ptLine: ptA ? getComputedStyle(ptA).boxShadow : null,
                 ftLineH: cs ? cs.height : null,
                 ftLineC: cs ? cs.backgroundColor : null };
    }""")
    check("chrome_ladder_three_levels",
          chrome["band"] and chrome["strip"] and chrome["paper"]
          and len({chrome["band"], chrome["strip"], chrome["paper"]}) == 3,
          str(chrome))
    check("proj_active_no_line",
          chrome["ptLine"] == "none", str(chrome["ptLine"]))
    check("file_active_single_hairline",
          chrome["ftLineH"] == "2px"
          and chrome["ftLineC"] in ("rgb(59, 142, 251)", "rgb(166, 91, 43)"),
          f"h={chrome['ftLineH']} c={chrome['ftLineC']}")

    # --- 0.8.2 fence auto-color + rhythm guards (owner 2026-10-14 报障
    # "Markdown 里面没有任何着色/中间空档这么大"): his docs mark almost all
    # fences ```text or nothing — those now hljs.auto-detect (relevance
    # floor 2, plain stays plain), and the hr band tightened 138→~83px.
    # Fixture is created here and deleted right after (watcher picks it up).
    fixture_rel = "aiv-autofence.md"
    fixture_path = os.path.join(PROJECT, fixture_rel)
    with open(fixture_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "# autofence\n\n"
            "> quote line for the band probe\n\n"
            "```\nSELECT id FROM users WHERE age > 18;\n```\n\n"
            "```text\n{\"name\": \"aiv\", \"version\": 2}\n```\n\n"
            "```text\n人 ← 编写代码\n     ↓\nAgent 接管\n```\n\n"
            "See `report.md` for the inline-code probe.\n\n"
            "---\n\n## tail heading\n"
        )
    time.sleep(1.5)  # watcher surfaces the file in the tree
    open_file(fixture_rel)
    af = page.evaluate("""() => {
        const r = document.querySelector('.rendered.md');
        const fences = [...r.querySelectorAll('pre > code')];
        const spans = fences.map(c => c.querySelectorAll('[class*=hljs-]').length);
        let maxBand = 0;
        for (const hr of r.querySelectorAll('hr')) {
          const prev = hr.previousElementSibling, next = hr.nextElementSibling;
          if (prev && next) maxBand = Math.max(maxBand,
            next.getBoundingClientRect().top - prev.getBoundingClientRect().bottom);
        }
        const hrEl = r.querySelector('hr');
        const hrAfter = hrEl ? getComputedStyle(hrEl, '::after').content : null;
        const hrBorder = hrEl ? getComputedStyle(hrEl).borderTopWidth : null;
        const delta = (a, b) => {
          const n = (s) => s.match(/\\d+/g).map(Number);
          const [r1,g1,b1] = n(a), [r2,g2,b2] = n(b);
          return Math.abs(r1-r2)+Math.abs(g1-g2)+Math.abs(b1-b2);
        };
        const paper = getComputedStyle(r).backgroundColor;
        const pre = r.querySelector('pre');
        const inline = r.querySelector('p code');
        return { fenceCount: fences.length, spans, maxBandPx: Math.round(maxBand),
                 hrAfter, hrBorder,
                 paper, preBg: pre ? getComputedStyle(pre).backgroundColor : null,
                 preDelta: pre ? delta(getComputedStyle(pre).backgroundColor, paper) : 0,
                 inlineBg: inline ? getComputedStyle(inline).backgroundColor : null,
                 inlineDelta: inline ? delta(getComputedStyle(inline).backgroundColor, paper) : 0 };
    }""")
    os.remove(fixture_path)
    check("fence_autocolor_unmarked",
          af["fenceCount"] == 3 and af["spans"][0] > 0, str(af))
    check("fence_autocolor_text_json", af["spans"][1] > 0, str(af))
    check("fence_diagram_stays_plain", af["spans"][2] == 0, str(af))
    check("hr_band_tight", 0 < af["maxBandPx"] <= 95, str(af))
    # 0.8.5 guard (owner 2026-10-16 "不显示"): `---` must render as pure
    # blank space — no ornament glyph, no line. ("none"/"normal" = no
    # ::after rule; any glyph like '"❧"' fails, any border fails.)
    check("hr_renders_invisible",
          af["hrAfter"] in ("none", "normal", '""') and af["hrBorder"] == "0px",
          f"after={af['hrAfter']} border={af['hrBorder']}")
    # 0.8.3 regression guard (owner "什么色块都没有"): the 0.8.1 round put
    # raised-white under code (ΔRGB≈3 vs paper = invisible); fences AND
    # inline code must now carry a clearly visible tinted block.
    check("code_block_bg_visible", af["preDelta"] >= 20,
          f"pre={af['preBg']} paper={af['paper']} Δ={af['preDelta']}")
    check("inline_code_bg_visible", af["inlineDelta"] >= 20,
          f"inline={af['inlineBg']} paper={af['paper']} Δ={af['inlineDelta']}")
    open_file("README.md")

    # --- batch closes via tab menu (owner 2026-10-13): left/right/others,
    # pinned tabs protected, anchor survives and takes over activation ---
    while tab_count() > 0:  # deterministic scene: clear, then five known tabs
        page.locator(".file-tab .close").first.click()
        time.sleep(0.12)
    open_file("notes.txt")
    expand("data")
    open_file("sample.csv")
    open_file("server.log")
    open_file("metrics.json")
    open_file("README.md")
    anchor = page.locator(".file-tab", has_text="server.log")
    # pin sample.csv (left of anchor): bulk closes must never touch it
    page.locator(".file-tab", has_text="sample.csv").click(button="right")
    page.locator(".menu button", has_text="Pin Tab").click()
    time.sleep(0.2)
    anchor.click(button="right")  # right-click does NOT activate the anchor
    page.locator(".menu button", has_text="Close to the Left").click()
    time.sleep(0.3)
    names_left = page.locator(".file-tab .name").all_inner_texts()
    check("close_left_drops_unpinned_left",
          "notes.txt" not in names_left
          and all(n in names_left for n in
                  ("sample.csv", "server.log", "metrics.json", "README.md")),
          str(names_left))
    check("close_left_keeps_active",
          page.locator(".file-tab.active .name").inner_text() == "README.md")
    # active tab (README.md) sits right of the anchor: closing the right
    # side must promote the anchor, and the pinned tab must survive again
    anchor.click(button="right")
    page.locator(".menu button", has_text="Close to the Right").click()
    time.sleep(0.3)
    names_right = page.locator(".file-tab .name").all_inner_texts()
    check("close_right_drops_right",
          all(n not in names_right for n in ("metrics.json", "README.md")),
          str(names_right))
    check("close_right_promotes_anchor",
          page.locator(".file-tab.active .name").inner_text() == "server.log")
    check("close_right_keeps_pinned", page.locator(".file-tab .pin").count() == 1)
    # others: rebuild to four tabs, keep only anchor + one pinned
    page.locator(".file-tab", has_text="sample.csv").click(button="right")
    page.locator(".menu button", has_text="Unpin Tab").click()
    time.sleep(0.2)
    open_file("notes.txt")      # nothing pinned now -> tabs accumulate
    open_file("metrics.json")
    page.locator(".file-tab", has_text="sample.csv").click(button="right")
    page.locator(".menu button", has_text="Pin Tab").click()
    time.sleep(0.2)
    anchor.click(button="right")
    page.locator(".menu button", has_text="Close Others").click()
    time.sleep(0.3)
    names_others = page.locator(".file-tab .name").all_inner_texts()
    check("close_others_keeps_anchor_and_pinned",
          set(names_others) == {"server.log", "sample.csv"}, str(names_others))
    check("close_others_promotes_anchor",
          page.locator(".file-tab.active .name").inner_text() == "server.log")
    # dead look when a side holds nothing eligible (only a pinned tab left)
    anchor.click(button="right")
    check("close_left_disabled_when_only_pinned_left",
          page.locator(".menu button", has_text="Close to the Left").is_disabled())
    page.mouse.click(400, 250)  # outside-mousedown closes (capture)
    time.sleep(0.25)

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

    # --- #7: theme pack (owner 2026-10-14) — paper/glacier switch LIVE ---
    # Both are light skins (system/dark/light retired; default = paper by
    # owner's order, overriding the pack JSON's glacier default). The
    # switch must apply instantly (pure CSS repaint) AND leave the session
    # untouched: same open tabs, same active file (spec §二 no-reset).
    open_file("README.md")
    tabs_before_theme = page.locator(".file-tab .name").all_inner_texts()
    active_before_theme = page.locator(".file-tab.active .name").inner_text()
    page.click('button[title="Settings"]')
    time.sleep(0.3)
    page.locator('input[name="theme"][value="paper"]').check()
    time.sleep(0.3)
    page.click('button[title="Settings"]')
    bg_paper = page.evaluate("() => getComputedStyle(document.querySelector('.viewer')).backgroundColor")
    check("theme_paper_viewer", bg_paper in ("rgb(255, 252, 245)", "#fffcf5"), bg_paper)
    band_paper = page.evaluate("() => getComputedStyle(document.querySelector('.project-tabs')).backgroundColor")
    check("theme_paper_band", band_paper in ("rgb(242, 233, 218)", "#f2e9da"), band_paper)
    check("theme_switch_keeps_session",
          page.locator(".file-tab .name").all_inner_texts() == tabs_before_theme
          and page.locator(".file-tab.active .name").inner_text() == active_before_theme,
          f"tabs={page.locator('.file-tab .name').all_inner_texts()}")
    page.click('button[title="Settings"]')
    time.sleep(0.2)
    page.locator('input[name="theme"][value="glacier"]').check()
    time.sleep(0.3)
    page.click('button[title="Settings"]')
    bg_glacier = page.evaluate("() => getComputedStyle(document.querySelector('.viewer')).backgroundColor")
    check("theme_glacier_viewer", bg_glacier in ("rgb(253, 253, 254)", "#fdfdfe"), bg_glacier)
    # steady state = product default (paper, owner 2026-10-14 order) so the
    # next suite run boots on the same skin a fresh user gets
    page.click('button[title="Settings"]')
    time.sleep(0.2)
    page.locator('input[name="theme"][value="paper"]').check()
    time.sleep(0.3)
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

    # --- gutter alignment across LIVE font changes (owner 2026-10-11
    # screenshot: line numbers drifted off the text). CodeMirror cannot see
    # the CSS-variable font change on :root, so its cached heights went
    # stale (probe: 13->20px = -168px by line 31; first scroll healed it).
    # requestMeasure on every knob turn must keep the gutter on the lines
    # with NO scroll, and the gutter font must follow the content scale.
    gutter_gauge = """() => {
      const lines = [...document.querySelectorAll('.cm-content .cm-line')];
      const gutters = [...document.querySelectorAll('.cm-lineNumbers .cm-gutterElement')];
      const g = new Map(gutters.map(e => [e.textContent.trim(), e]));
      let maxAbs = 0;
      lines.forEach((l, i) => {
        const ge = g.get(String(i + 1));
        if (ge) maxAbs = Math.max(maxAbs,
          Math.abs(ge.getBoundingClientRect().top - l.getBoundingClientRect().top));
      });
      const cs = getComputedStyle(document.querySelector('.cm-content')).fontSize;
      const gs = getComputedStyle(document.querySelector('.cm-gutters')).fontSize;
      return { maxAbs: Math.round(maxAbs * 10) / 10, cs, gs };
    }"""
    gutter_before = page.evaluate(gutter_gauge)
    for _ in range(6):
        page.locator('.code-viewer .vtb button[aria-label="Larger text"]').click()
        time.sleep(0.2)
    time.sleep(0.8)
    gutter_bumped = page.evaluate(gutter_gauge)
    for _ in range(6):
        page.locator('.code-viewer .vtb button[aria-label="Smaller text"]').click()
        time.sleep(0.15)
    check("gutter_aligned_across_font_changes",
          gutter_before["maxAbs"] < 1 and gutter_bumped["maxAbs"] < 1
          and gutter_bumped["cs"] == gutter_bumped["gs"],
          f"before={gutter_before} bumped={gutter_bumped}")

    # 0.7.7 blue-button guard (owner 2026-10-11 "点击字体放大缩小…按钮显示蓝
    # 色"): a fast double-/triple-click on the zoom buttons used to word-select
    # the label ("A+"/"+") and paint it in the native blue ::selection —
    # controls are user-select:none now; the selection must stay empty.
    zoom_btn = page.locator('.code-viewer .vtb button[aria-label="Larger text"]')
    zoom_btn.dblclick()
    time.sleep(0.2)
    sel_after_dbl = page.evaluate("() => window.getSelection().toString()")
    box = zoom_btn.bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2,
                     click_count=3)
    time.sleep(0.2)
    sel_after_tri = page.evaluate("() => window.getSelection().toString()")
    check("toolbar_buttons_not_selectable",
          sel_after_dbl == "" and sel_after_tri == "",
          f"dbl={sel_after_dbl!r} tri={sel_after_tri!r}")

    # centered reading column + resize guard (owner 2026-10-10 bug class;
    # contract REVERSED 2026-10-13 with owner via demo AIV-MD渲染对比: the
    # reading column is capped at 88ch and centered, and the blank beside it
    # is the SAME warm paper as the column — no cold band can exist. Assert
    # the paper fills the pane, the column is capped + centered, and a long
    # paragraph fills the capped column.)
    open_file("README.md")
    cdp = page.context.new_cdp_session(page)
    cdp.send("Emulation.setDeviceMetricsOverride",
             {"width": 1600, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(0.8)
    fills = page.evaluate(r"""() => {
      const el = document.querySelector('.markdown-viewer .rendered');
      if (!el) return { ok: false, why: 'no .rendered' };
      const prose = el.querySelector('.prose');
      if (!prose) return { ok: false, why: 'no .prose' };
      const bg = getComputedStyle(el).backgroundColor;
      const paper = bg === 'rgb(253, 253, 254)' || bg === 'rgb(255, 252, 245)';
      // ch scales with the font knob (A+/A−) and getComputedStyle keeps
      // min() unevaluated — measure the cap with an in-page 88ch probe
      // instead, then assert the CONTRACT: column = min(cap, available),
      // centered, on full-bleed paper.
      const probe = document.createElement('div');
      probe.style.cssText = 'position:absolute;visibility:hidden;width:88ch';
      prose.appendChild(probe);
      const capPx = Math.round(probe.getBoundingClientRect().width);
      probe.remove();
      const capped = capPx > 0;
      const pr = prose.getBoundingClientRect();
      const er = el.getBoundingClientRect();
      const proseW = Math.round(pr.width);
      const avail = Math.round(er.width
          - parseFloat(getComputedStyle(el).paddingLeft)
          - parseFloat(getComputedStyle(el).paddingRight));
      const gapL = Math.round(pr.left - er.left);
      const gapR = Math.round(er.right - pr.right);
      const blocks = [...prose.querySelectorAll('p, li, h1, h2, h3, h4, pre')]
        .filter(x => (x.innerText || '').trim().length > 30);
      const pw = blocks.length
        ? Math.round(Math.max(...blocks.map(b => b.getBoundingClientRect().width)))
        : -1;
      const expectW = capped ? Math.min(capPx, avail) : avail;
      return { bg, capPx, proseW, avail, gapL, gapR, pw,
               ok: paper && capped && Math.abs(proseW - expectW) <= 2
                   && Math.abs(gapL - gapR) <= 40 && pw >= proseW - 4 };
    }""")
    check("md_text_fills_area", bool(fills["ok"]),
          f"bg={fills.get('bg')} cap={fills.get('capPx')} proseW={fills.get('proseW')} "
          f"avail={fills.get('avail')} gaps={fills.get('gapL')}/{fills.get('gapR')} "
          f"paraW={fills.get('pw')}")
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
    # spec-008 (§139): +Open(info card) +Run, still no editors
    check("handoff_tree_exe", m_exe == {"open", "run", "reveal", "copy-abs",
          "copy-rel"}, str(sorted(m_exe)))
    m_html = menu_ids_of(tree_menu("index.html"))
    m_url = menu_ids_of(tree_menu("example.url"))
    check("handoff_tree_browser", "browser" in m_html and "browser" in m_url
          and m_html >= {"notepad", "vscode"} and m_url >= {"notepad", "vscode"},
          f"html={sorted(m_html)} url={sorted(m_url)}")

    # 0.8.6 guard (owner 2026-10-17 "HTML 图标跟 MD 过于接近"): the
    # code-family icon must differ from the MD icon. Identical glyphs
    # render identical SVG markup, so markup inequality is the check
    # (chevrons-only vs document-with-lines have nothing in common).
    icons = page.evaluate("""() => {
        const ficon = (name) => {
            const row = [...document.querySelectorAll('.file-tree .row')]
                .find(r => r.querySelector('.name')?.textContent === name);
            return row ? row.querySelector('.ficon svg')?.innerHTML ?? null : null;
        };
        return { html: ficon('index.html'), md: ficon('README.md') };
    }""")
    check("code_icon_distinct_from_md",
          bool(icons["html"]) and bool(icons["md"])
          and icons["html"] != icons["md"], str(icons))

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
    # spec-008: §141 full set — +Refresh Project +Trust Project (untrusted
    # default flips the label to Untrust Project once trusted)
    check("handoff_project_menu", m_proj == {"project-explorer",
          "copy-project-path", "project-vscode", "refresh-project",
          "trust-project"}, str(sorted(m_proj)))
    page.locator(".project-tabs .tab.active").click(button="right")
    has_remove = page.locator(".menu button", has_text="Remove Project").count() == 1
    page.mouse.click(400, 250)
    check("handoff_project_remove_kept", has_remove, "Remove Project missing")

    # Copy feedback (V6): the toast names what landed on the clipboard.
    # (No clipboard readback here: WebView2 may raise a native permission
    #  prompt that blocks the evaluate call — the toast IS the oracle.)
    # 0.8.4: copied paths are quote-wrapped (owner 2026-10-15) so pastes
    # with spaces survive terminals — the quotes are part of the contract.
    tree_row("chinese-gb18030.txt").click(button="right")
    # dispatch_event, not click(): this suite earlier used CDP viewport
    # emulation (resize test) and Playwright's cached viewport then
    # misjudges position:fixed menu items as "outside of the viewport"
    # even when the DOM rect is inside. Menu logic is the test target,
    # not pointer hit-testing.
    page.locator(".menu [data-menu-id='copy-rel']").dispatch_event("click")
    rel_toast = page.wait_for_selector(".toast").inner_text().strip()
    check("copy_rel_feedback",
          rel_toast.count('"') == 2 and rel_toast.endswith('"')
          and "edge-cases/chinese-gb18030.txt" in rel_toast, repr(rel_toast))
    time.sleep(1.0)  # let the toast clear
    # A top row: the menu opens AT the click point, so a bottom row would
    # place its items below the viewport (unclickable).
    tree_row("README.md").click(button="right")
    page.locator(".menu [data-menu-id='copy-abs']").dispatch_event("click")
    abs_toast = page.wait_for_selector(".toast").inner_text().strip()
    check("copy_abs_feedback",
          abs_toast.count('"') == 2 and abs_toast.endswith('"')
          and "AIV-TestProject\\README.md" in abs_toast, abs_toast)
    time.sleep(1.0)  # let the toast clear
    page.locator(".project-tabs .tab.active").click(button="right")
    page.locator(".menu [data-menu-id='copy-project-path']").dispatch_event(
        "click")
    proj_toast = page.wait_for_selector(".toast").inner_text().strip()
    check("copy_project_path_quoted",
          proj_toast.count('"') == 2 and proj_toast.endswith('"')
          and "AIV-TestProject" in proj_toast, proj_toast)

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
    # --- 0.6.12 diagnostics export (owner: viewer-freeze bug needed a
    # client-side trace): Settings -> Export Diagnostics writes a file and
    # shows its path; the report must include the live cross-check line. ---
    page.locator('.sidebar-header .settings').click()
    page.wait_for_selector(".export-diag", timeout=4000)
    page.locator(".export-diag").click()
    exp_path = None
    deadline = time.time() + 8
    while time.time() < deadline:
        t = page.locator(".toast").count() and page.locator(".toast").inner_text()
        if t and t.startswith("Diagnostics exported: "):
            exp_path = t[len("Diagnostics exported: "):].strip()
            break
        time.sleep(0.3)
    exported_ok = False
    if exp_path and os.path.isfile(exp_path):
        body = open(exp_path, encoding="utf-8", errors="replace").read()
        exported_ok = ("live-check:" in body and "runtime log" in body
                       and "version=" in body)
    check("diagnostics_export_writes_report",
          bool(exp_path) and exported_ok, f"path={exp_path}")
    page.locator('.sidebar-header .header-tab', has_text="Files").first.click()

    # --- 0.6.12 bug (owner: "右键 example.url,Example 没有高显,之前的
    # styles.css 反而高显"): while a row's context menu is open, THAT row
    # owns the tree highlight exclusively; closing reverts to active tab. ---
    hl = page.evaluate(r"""() => {
      const row = [...document.querySelectorAll('.file-tree .row')]
        .find(r => r.title === 'sample.msi');
      if (!row) return { ok: false, why: 'row not in DOM' };
      row.dispatchEvent(new MouseEvent('contextmenu', {
        clientX: 200, clientY: 200, bubbles: true, cancelable: true }));
      return new Promise(res => setTimeout(() => {
        const lit = [...document.querySelectorAll('.file-tree .row.selected')]
          .map(r => r.getAttribute('title'));
        const msiLit = row.classList.contains('selected');
        document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        setTimeout(() => {
          const after = [...document.querySelectorAll('.file-tree .row.selected')]
            .map(r => r.getAttribute('title'));
          res({ msiLit, lit, after,
                ok: msiLit && lit.length === 1 && !after.includes('sample.msi') });
        }, 400);
      }, 350));
    }""")
    check("right_click_row_owns_highlight", bool(hl.get("ok")), str(hl))

    # --- 0.7.9 (owner 2026-10-12: "右键 Notes.txt → Show in File Explorer,
    # 高亮跑到 pyproject.toml 上"): ACTING on a context-menu item keeps the
    # acted row lit until the next file activation; dismissing without acting
    # still reverts (guard above). Copy-Path stands in for the reveal verb so
    # the probe never opens a desktop window. ---
    hl2 = page.evaluate(r"""() => {
      const row = [...document.querySelectorAll('.file-tree .row')]
        .find(r => r.getAttribute('title') === 'sample.msi');
      if (!row) return { ok: false, why: 'row not in DOM' };
      row.dispatchEvent(new MouseEvent('contextmenu', {
        clientX: 200, clientY: 200, bubbles: true, cancelable: true }));
      return new Promise(res => setTimeout(() => {
        const btn = document.querySelector(".menu [data-menu-id='copy-abs']");
        if (!btn) { res({ ok: false, why: 'menu item missing' }); return; }
        btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        setTimeout(() => {
          const after = [...document.querySelectorAll('.file-tree .row.selected')]
            .map(r => r.getAttribute('title'));
          const okAfterAction = after.includes('sample.msi') && after.length === 1;
          // Next activation (re-clicking the already-active tab) hands the
          // highlight back without disturbing any other state.
          const activeTabBtn = document.querySelector('.file-tabs .file-tab.active');
          if (activeTabBtn)
            activeTabBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          setTimeout(() => {
            const final = [...document.querySelectorAll('.file-tree .row.selected')]
              .map(r => r.getAttribute('title'));
            res({ after, final,
                  ok: okAfterAction && !final.includes('sample.msi') && final.length === 1 });
          }, 500);
        }, 400);
      }, 350));
    }""")
    check("context_action_keeps_row_highlight", bool(hl2.get("ok")), str(hl2))

    # --- Phase 8 growth guard (owner 2026-10-10 晚: "新菜单项加了以后,
    # 底部右键出来的列表还是一定能够全部显示") — the clamp must adapt to
    # the TALLER menus; assert EVERY button is inside the viewport, not
    # just the menu container. ---
    def bottom_menu_probe(sel):
        return page.evaluate("""(sel) => {
          const row = document.querySelector(sel);
          row.dispatchEvent(new MouseEvent('contextmenu', {
            clientX: 12, clientY: innerHeight - 6, bubbles: true, cancelable: true }));
          return new Promise(res => setTimeout(() => {
            const m = document.querySelector('.menu');
            if (!m) { res(null); return; }
            const bad = [...m.querySelectorAll('button')].filter((b) => {
              const r = b.getBoundingClientRect();
              return r.top < 0 || r.bottom > innerHeight - 2
                  || r.left < 0 || r.right > innerWidth - 2;
            }).map((b) => b.textContent.trim());
            res({ count: m.querySelectorAll('button').length, bad });
            document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
          }, 350));
        }""", sel)

    for _name, _sel in [
        ("script", '.file-tree .row[title="hello.ps1"]'),
        ("exe", '.file-tree .row[title="demo.exe"]'),
        ("project", '.project-tabs .tab'),
    ]:
        _r = bottom_menu_probe(_sel)
        time.sleep(0.25)
        check(f"menu_clamped_bottom_{_name}",
              bool(_r) and _r["count"] > 0 and not _r["bad"],
              f"r={_r}")

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

        # --- 0.6.6: clicking refresh must be VISIBLY acknowledged (owner:
        # "点击的时候应该有一个明显的效果") — icon spins, then settles. ---
        page.locator('.sidebar-header .refresh').click()
        spin = page.evaluate("""() => {
          const b = document.querySelector('.sidebar-header .refresh');
          const g = b && b.querySelector('.glyph');
          if (!b || !g) return { ok: false, why: 'missing' };
          const anim = getComputedStyle(g).animationName !== 'none';
          const dur = getComputedStyle(g).animationDuration;
          return { ok: anim && b.getAttribute('aria-busy') === 'true',
                   anim, dur, busy: b.getAttribute('aria-busy') };
        }""")
        time.sleep(1.2)
        settled = page.evaluate("""() => {
          const b = document.querySelector('.sidebar-header .refresh');
          const g = b.querySelector('.glyph');
          return { anim: getComputedStyle(g).animationName !== 'none',
                   busy: b.getAttribute('aria-busy') };
        }""")
        check("refresh_click_feedback",
              bool(spin.get("ok")) and not settled["anim"]
              and settled["busy"] != "true",
              f"during={spin} after={settled}")
    finally:
        if os.path.exists(probe):
            os.remove(probe)

    # --- spec-008 (Phase 8 RUN/Trust): menus, info card, trust gate ---
    # .ps1/.cmd/.bat get Run Script; py/js/sh do not (§116/§127)
    m_ps1 = menu_ids_of(tree_menu("hello.ps1"))
    check("p8_script_menu_has_run",
          m_ps1 >= {"open", "run-script", "notepad", "vscode",
                    "reveal", "copy-abs", "copy-rel"}, str(sorted(m_ps1)))
    expand("src")
    def row_by_title(t):
        return page.locator(f'.file-tree .row[title="{t}"]')
    m_py = menu_ids_of(lambda: row_by_title("src/main.py").first.click(button="right"))
    check("p8_python_no_run_entry", "run-script" not in m_py, str(sorted(m_py)))

    # §139 exe: Open(info)+Run, no editors; §126 msi: System Default, no Run
    m_exe = menu_ids_of(tree_menu("demo.exe"))
    check("p8_exe_menu",
          m_exe == {"open", "run", "reveal", "copy-abs", "copy-rel"},
          str(sorted(m_exe)))
    m_msi = menu_ids_of(tree_menu("sample.msi"))
    check("p8_msi_menu_no_run",
          m_msi == {"default-app", "reveal", "copy-abs", "copy-rel"},
          str(sorted(m_msi)))

    # §122: left-click .exe -> stat card (no content read)
    tree_row("demo.exe").click()
    page.wait_for_selector(".exe-info .kind", timeout=4000)
    info_txt = page.locator(".exe-info").inner_text()
    low = info_txt.lower()
    check("p8_exe_info_viewer",
          "windows executable" in low
          and "this file cannot be previewed." in low
          and "size:" in low and "modified:" in low
          and "path:" in low,
          repr(info_txt[:200]))

    # §128 untrusted + test mode: Run Script auto-cancels — nothing launches
    tree_row("hello.bat").click(button="right")
    page.wait_for_selector(".menu [data-menu-id='run-script']", timeout=4000)
    page.locator(".menu [data-menu-id='run-script']").dispatch_event("click")
    time.sleep(1.5)
    launched_toast = page.evaluate(
        "() => { const t = document.querySelector('.toast');"
        " return t ? t.innerText : null; }")
    check("p8_untrusted_run_auto_cancel", launched_toast is None,
          f"toast={launched_toast!r}")

    # §141 project menu: Refresh Project + Trust/Untrust, toggling per state
    page.locator(".project-tabs .tab").first.click(button="right")
    page.wait_for_selector(".menu [data-menu-id='trust-project']", timeout=4000)
    page.locator(".menu [data-menu-id='trust-project']").dispatch_event("click")
    time.sleep(0.6)
    trust_toast = page.locator(".toast").inner_text()
    check("p8_trust_toggle",
          "is now trusted for execution." in trust_toast, trust_toast)
    page.locator(".project-tabs .tab").first.click(button="right")
    page.wait_for_selector(".menu [data-menu-id='untrust-project']", timeout=4000)
    untrust_ids = page.eval_on_selector_all(
        ".menu [data-menu-id]", "els => els.map(e => e.dataset.menuId)")
    page.mouse.click(400, 250)  # close without toggling (state restored below)
    check("p8_project_menu_refresh_entry",
          "refresh-project" in untrust_ids and "untrust-project" in untrust_ids,
          str(untrust_ids))

    # §119 failure toast: trusted project + vanished target -> loud failure
    fail_bat = os.path.join(PROJECT, "data", "tmp-fail.bat")
    with open(fail_bat, "w", newline="") as f:
        f.write("@echo off\r\necho x\r\n")
    tree_row("data").click()          # collapse
    time.sleep(0.3)
    tree_row("data").click()          # re-expand re-lists (0.6.4 behavior)
    time.sleep(0.8)
    row_by_title("data/tmp-fail.bat").first.click(button="right")
    page.wait_for_selector(".menu [data-menu-id='run-script']", timeout=4000)
    os.remove(fail_bat)               # target vanishes before launch
    page.locator(".menu [data-menu-id='run-script']").dispatch_event("click")
    # Owner 2026-10-11: failure = CENTERED modal dialog stating the reason
    # (not a toast); success stays silent (the console is the feedback).
    # let the earlier trust-toggle toast auto-hide so "no toast" is honest
    t_toast = time.time()
    while time.time() - t_toast < 5 and page.locator(".toast").count():
        time.sleep(0.3)
    dlg = page.wait_for_selector(".dialog", timeout=5000)
    dlg_txt = dlg.inner_text()
    ok_geom = page.evaluate("""() => {
      const d = document.querySelector('.dialog').getBoundingClientRect();
      return Math.abs((d.left + d.right) / 2 - innerWidth / 2) < 4
          && Math.abs((d.top + d.bottom) / 2 - innerHeight / 2) < 4;
    }""")
    no_toast = page.locator(".toast").count() == 0
    page.keyboard.press("Escape")
    time.sleep(0.3)
    gone = page.locator(".dialog").count() == 0
    check("p8_launch_failure_dialog",
          "Failed to launch" in dlg_txt and "Not found" in dlg_txt
          and ok_geom and no_toast and gone,
          f"txt={dlg_txt!r} centered={ok_geom} toast={no_toast} closed={gone}")
    time.sleep(0.6)

    # restore: untrust (leave the temp project state as it started)
    page.locator(".project-tabs .tab").first.click(button="right")
    page.wait_for_selector(".menu [data-menu-id='untrust-project']", timeout=4000)
    page.locator(".menu [data-menu-id='untrust-project']").dispatch_event("click")
    time.sleep(0.6)

    # --- spec-009 (Phase 9 Watcher): external disk changes refresh the app
    # with NO manual gesture — tree rows appear/vanish (V1), the open viewer
    # swaps content + §82 toast coalescing a burst (V2/V9), a deleted file
    # keeps its §83 card with Close Tab (V3), a rename follows the tab and
    # its pin (V4). Probes live under data/ (already expanded). ---
    def wait_row(title, present, timeout_s=6):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if (page.locator(f'.file-tree .row[title="{title}"]').count() > 0) == present:
                time.sleep(0.3)  # let follow-up rendering settle
                return True
            time.sleep(0.15)
        return False

    w_probe = os.path.join(PROJECT, "data", "zz-watch-me.txt")
    w_renamed = os.path.join(PROJECT, "data", "zz-renamed.txt")
    for p in (w_probe, w_renamed):
        if os.path.exists(p):
            os.remove(p)

    # V1: file appears in the tree with no click at all.
    with open(w_probe, "w") as f:
        f.write("watch marker A\n")
    check("watcher_tree_auto_add", wait_row("data/zz-watch-me.txt", True))

    # V2 + V9: open it, then TWO writes inside one debounce window ->
    # one reload to the final content, exactly one "✓ ... updated" toast.
    row_by_title("data/zz-watch-me.txt").first.click()
    body_contains("watch marker A")
    time.sleep(0.5)
    with open(w_probe, "w") as f:
        f.write("watch marker B1\n")
    time.sleep(0.12)
    with open(w_probe, "w") as f:
        f.write("watch marker B2\n")
    reloaded = body_contains("watch marker B2", timeout_s=6)
    toasts_seen, first_txt, was = 0, "", False
    t0 = time.time()
    while time.time() - t0 < 3.5:
        has_toast = page.locator(".toast").count() > 0
        if has_toast and not was:
            toasts_seen += 1
            if not first_txt:
                first_txt = page.locator(".toast").inner_text()
        was = has_toast
        time.sleep(0.1)
    check("watcher_active_file_auto_reload",
          reloaded and toasts_seen == 1 and "zz-watch-me.txt updated" in first_txt,
          f"reloaded={reloaded} toasts={toasts_seen} txt={first_txt!r}")

    # V3: delete externally -> tree row vanishes, tab keeps its §83 card,
    # Close Tab really closes it.
    os.remove(w_probe)
    deleted_card = body_contains("This file has been deleted.", timeout_s=6)
    row_gone = wait_row("data/zz-watch-me.txt", False)
    close_btn = page.locator(".unsupported button", has_text="Close Tab")
    has_close = close_btn.count() == 1
    n_before = tab_count()
    if has_close:
        close_btn.first.click()
        time.sleep(0.4)
    check("watcher_deleted_tab_state",
          deleted_card and row_gone and has_close and tab_count() == n_before - 1,
          f"card={deleted_card} row={row_gone} close={has_close} "
          f"tabs={n_before}->{tab_count()}")

    # V4: recreate, open, PIN, rename externally -> same tab follows the
    # new name (title + active + pin), content survives the retarget.
    with open(w_probe, "w") as f:
        f.write("rename me\n")
    if not wait_row("data/zz-watch-me.txt", True):
        row_by_title("data").first.click(); time.sleep(0.3)
        row_by_title("data").first.click(); time.sleep(0.8)  # manual fallback
        wait_row("data/zz-watch-me.txt", True)
    row_by_title("data/zz-watch-me.txt").first.click()
    body_contains("rename me")
    time.sleep(0.4)
    page.locator(".file-tab.active").click(button="right")
    page.locator(".menu button", has_text="Pin Tab").click()
    time.sleep(0.3)
    os.rename(w_probe, w_renamed)
    renamed_ok, pinned_kept, content_kept = False, False, False
    deadline = time.time() + 6
    while time.time() < deadline:
        active = page.locator(".file-tab.active")
        if active.count() and "zz-renamed.txt" in active.inner_text():
            renamed_ok = True
            pinned_kept = page.locator(".file-tab.active .pin").count() == 1
            content_kept = "rename me" in page.locator(".viewer-body").inner_text()
            break
        time.sleep(0.15)
    check("watcher_rename_follows_tab",
          renamed_ok and pinned_kept and content_kept,
          f"renamed={renamed_ok} pin={pinned_kept} content={content_kept}")

    # cleanup: close the pinned probe tab, remove the renamed file, let the
    # watcher take the row away on its own (second auto-remove sighting).
    press("w")
    time.sleep(0.4)
    os.remove(w_renamed)
    check("watcher_tree_auto_remove", wait_row("data/zz-renamed.txt", False))

    # --- Phase 10 opener-scope fence (spec-011 S2): the renderer must NOT
    # hold a direct "open any path / any URL" capability — only http(s)
    # open_url survives (MarkdownViewer links). Both probes assert the
    # REJECTION (nothing may open on the desktop).
    denied = page.evaluate("""async () => {
        const invoke = window.__TAURI_INTERNALS__.invoke;
        const out = { path: false, fileUrl: false };
        try {
            await invoke('plugin:opener|open_path',
                { path: 'C:\\\\Windows', with: null });
        } catch (e) { out.path = String(e).length > 0; }
        try {
            await invoke('plugin:opener|open_url',
                { url: 'file:///C:/Windows/notepad.exe', with: null });
        } catch (e) { out.fileUrl = String(e).length > 0; }
        return out;
    }""")
    check("p10_opener_open_path_denied", bool(denied and denied.get("path")),
          "open_path unexpectedly allowed (capability leak)")
    check("p10_opener_file_url_denied", bool(denied and denied.get("fileUrl")),
          "open_url file:// unexpectedly allowed (scope leak)")

    # --- 0.8.6 guard (owner 2026-10-17): a write into a NON-active project
    # (the away fixture seeded at launch) must be visible right after
    # switching back — with NO expand gesture. On the old build the tree
    # served the stale cached level; the file only appeared after a manual
    # collapse/re-expand. ---
    with open(os.path.join(AWAY_B, "sub", "away-write.md"), "w",
              encoding="utf-8") as f:
        f.write("# written while away\n")
    time.sleep(1.5)  # debounce + margin; only the ACTIVE project is watched
    page.locator(".project-tabs .tab", has_text="aiv-p3-away").first.click()
    time.sleep(1.5)  # switch-in refresh lane
    seed_n = page.locator(".file-tree .row .name", has_text="seed.txt").count()
    away_n = page.locator(
        ".file-tree .row .name", has_text="away-write.md").count()
    check("away_write_visible_on_switch_back",
          seed_n == 1 and away_n == 1, f"seed={seed_n} away={away_n}")
    # Back to the main fixture: leave the suite's world as it found it.
    page.locator(".project-tabs .tab", has_text="AIV-TestProject").first.click()
    time.sleep(0.5)

print(json.dumps(results, indent=1, ensure_ascii=False))
print("VERDICT:", "PASS" if not FAIL else f"FAIL ({len(FAIL)}): {FAIL}")
