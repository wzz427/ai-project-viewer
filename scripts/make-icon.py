# -*- coding: utf-8 -*-
"""Generate 3 icon candidates for AI Project Viewer (4096 supersample -> 1024 master)."""
import math, os
from PIL import Image, ImageDraw, ImageFont

SS = 4096          # supersample canvas
OUT = os.path.dirname(os.path.abspath(__file__))

def diag_gradient(size, c1, c2):
    tiny = Image.new("RGB", (2, 2))
    px = tiny.load()
    mid = tuple((a + b) // 2 for a, b in zip(c1, c2))
    px[0, 0] = c1; px[1, 1] = c2; px[0, 1] = mid; px[1, 0] = mid
    return tiny.resize((size, size), Image.Resampling.BICUBIC)

def icon_base(radius_frac, c1, c2):
    grad = diag_gradient(SS, c1, c2).convert("RGBA")
    mask = Image.new("L", (SS, SS), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, SS - 1, SS - 1], radius=int(SS * radius_frac), fill=255)
    out = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out

def lens_points(cx, cy, w, h, n=128):
    """Almond/lens polygon: intersection of two equal circles."""
    a, b = w / 2, h / 2
    off = (a * a - b * b) / (2 * b)
    r = off + b
    pts = []
    ang_l = math.atan2(-off, -a); ang_r = math.atan2(-off, a)
    for i in range(n + 1):  # upper lid, left -> right over the top
        t = ang_l + (ang_r - ang_l) * i / n
        pts.append((cx + r * math.cos(t), cy + off + r * math.sin(t)))
    ang_l2 = math.atan2(off, a); ang_r2 = math.atan2(off, -a)
    for i in range(n + 1):  # lower lid, right -> left under the bottom
        t = ang_l2 + (ang_r2 - ang_l2) * i / n
        pts.append((cx + r * math.cos(t), cy - off + r * math.sin(t)))
    return pts

def star4(cx, cy, s, k=0.24):
    kk = s * k
    return [(cx, cy - s), (cx + kk, cy - kk), (cx + s, cy), (cx + kk, cy + kk),
            (cx, cy + s), (cx - kk, cy + kk), (cx - s, cy), (cx - kk, cy - kk)]

def overlay(base):
    lay = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    return lay, ImageDraw.Draw(lay)

def merge(base, lay):
    return Image.alpha_composite(base, lay)

INDIGO   = (48, 56, 224)
CYAN     = (0, 176, 255)
NAVYINK  = (42, 51, 201)
DOCWHITE = (255, 255, 255, 255)

# ---------------- Candidate A: doc + eye + AI spark ----------------
def candidate_a():
    img = icon_base(0.215, (52, 60, 235), (0, 168, 242))
    lay, d = overlay(img)

    # document with folded corner
    dw, dh = 0.46 * SS, 0.58 * SS
    dx0, dy0 = (SS - dw) / 2, (SS - dh) / 2 - 0.015 * SS
    dx1, dy1 = dx0 + dw, dy0 + dh
    fold = 0.105 * SS
    rad = 0.022 * SS
    doc_mask = Image.new("L", (SS, SS), 0)
    dm = ImageDraw.Draw(doc_mask)
    dm.rounded_rectangle([dx0, dy0, dx1, dy1], radius=rad, fill=255)
    cut = Image.new("L", (SS, SS), 0)
    cm = ImageDraw.Draw(cut)
    cm.polygon([(dx1 - fold, dy0), (dx1, dy0), (dx1, dy0 + fold)], fill=255)
    doc_mask.paste(0, (0, 0), cut)
    doc_layer = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    doc_layer.paste(DOCWHITE, (0, 0), doc_mask)
    img = merge(img, doc_layer)
    lay, d = overlay(img)
    # fold flap
    d.polygon([(dx1 - fold, dy0), (dx1 - fold, dy0 + fold), (dx1, dy0 + fold)],
              fill=(214, 224, 245, 255))

    # text lines
    line_h = 0.026 * SS
    d.rounded_rectangle([dx0 + 0.09 * dw, dy0 + 0.10 * dh, dx0 + 0.62 * dw, dy0 + 0.10 * dh + line_h],
                        radius=line_h / 2, fill=(184, 198, 235, 255))
    d.rounded_rectangle([dx0 + 0.09 * dw, dy0 + 0.175 * dh, dx0 + 0.44 * dw, dy0 + 0.175 * dh + line_h],
                        radius=line_h / 2, fill=(184, 198, 235, 255))

    # eye (outline lens + iris + pupil + highlight)
    ecx, ecy = SS / 2, dy0 + 0.66 * dh
    ew, eh = 0.64 * dw, 0.30 * dw
    stroke = 0.052 * ew
    d.polygon(lens_points(ecx, ecy, ew, eh), fill=NAVYINK + (255,))
    d.polygon(lens_points(ecx, ecy, ew - 2 * stroke, eh - 2 * stroke * 0.78), fill=DOCWHITE)
    iris_r = eh * 0.62
    d.ellipse([ecx - iris_r, ecy - iris_r, ecx + iris_r, ecy + iris_r], fill=(0, 166, 255, 255))
    pup_r = iris_r * 0.46
    d.ellipse([ecx - pup_r, ecy - pup_r, ecx + pup_r, ecy + pup_r], fill=(27, 33, 112, 255))
    hl = iris_r * 0.30
    hcx, hcy = ecx + iris_r * 0.38, ecy - iris_r * 0.42
    d.ellipse([hcx - hl, hcy - hl, hcx + hl, hcy + hl], fill=DOCWHITE)

    # AI spark
    d.polygon(star4(0.815 * SS, 0.165 * SS, 0.085 * SS), fill=(255, 178, 36, 255))
    d.polygon(star4(0.815 * SS, 0.165 * SS, 0.038 * SS), fill=(255, 236, 190, 255))
    return merge(img, lay)

# ---------------- Candidate B: folder + magnifier ----------------
def candidate_b():
    img = icon_base(0.215, (255, 138, 0), (255, 78, 58))
    lay, d = overlay(img)

    # folder (tab + body)
    bw, bh = 0.60 * SS, 0.40 * SS
    bx0, by0 = (SS - bw) / 2 - 0.03 * SS, (SS - bh) / 2 + 0.06 * SS
    bx1, by1 = bx0 + bw, by0 + bh
    tab_w, tab_h = 0.30 * bw, 0.13 * bh
    d.rounded_rectangle([bx0, by0 - tab_h + 0.02 * SS, bx0 + tab_w, by0 + 0.06 * SS],
                        radius=0.02 * SS, fill=(255, 236, 214, 255))
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=0.028 * SS, fill=DOCWHITE)
    img = merge(img, lay)
    lay, d = overlay(img)
    # subtle divider under tab
    d.rounded_rectangle([bx0 + 0.02 * SS, by0 + 0.004 * SS, bx0 + tab_w - 0.01 * SS, by0 + 0.022 * SS],
                        radius=0.009 * SS, fill=(255, 214, 178, 255))

    # magnifier (handle first, ring on top)
    mcx, mcy = 0.645 * SS, 0.575 * SS
    ring_r, stroke = 0.175 * SS, 0.055 * SS
    hx0 = mcx + ring_r * 0.72
    hy0 = mcy + ring_r * 0.72
    hx1, hy1 = hx0 + 0.145 * SS, hy0 + 0.145 * SS
    NAVY = (35, 41, 107, 255)
    d.line([hx0, hy0, hx1, hy1], fill=NAVY, width=int(stroke))
    for (px, py) in [(hx0, hy0), (hx1, hy1)]:
        d.ellipse([px - stroke / 2, py - stroke / 2, px + stroke / 2, py + stroke / 2], fill=NAVY)
    d.ellipse([mcx - ring_r, mcy - ring_r, mcx + ring_r, mcy + ring_r], fill=NAVY)
    d.ellipse([mcx - ring_r + stroke, mcy - ring_r + stroke, mcx + ring_r - stroke, mcy + ring_r - stroke],
              fill=(234, 244, 255, 255))
    gl = ring_r * 0.28
    gcx, gcy = mcx - ring_r * 0.34, mcy - ring_r * 0.38
    d.ellipse([gcx - gl / 2, gcy - gl / 2, gcx + gl / 2, gcy + gl / 2], fill=(178, 205, 240, 255))
    return merge(img, lay)

# ---------------- Candidate C: bold eye ----------------
def candidate_c():
    img = icon_base(0.215, (25, 27, 79), (75, 46, 217))
    lay, d = overlay(img)

    ecx, ecy = 0.50 * SS, 0.535 * SS
    ew, eh = 0.76 * SS, 0.415 * SS
    d.polygon(lens_points(ecx, ecy, ew, eh), fill=DOCWHITE)
    iris_r = 0.152 * SS
    d.ellipse([ecx - iris_r, ecy - iris_r, ecx + iris_r, ecy + iris_r], fill=(0, 196, 255, 255))
    pup_r = iris_r * 0.44
    d.ellipse([ecx - pup_r, ecy - pup_r, ecx + pup_r, ecy + pup_r], fill=(16, 18, 56, 255))
    hl = iris_r * 0.30
    hcx, hcy = ecx + iris_r * 0.40, ecy - iris_r * 0.42
    d.ellipse([hcx - hl, hcy - hl, hcx + hl, hcy + hl], fill=DOCWHITE)

    d.polygon(star4(0.825 * SS, 0.16 * SS, 0.078 * SS), fill=(125, 227, 255, 255))
    d.polygon(star4(0.825 * SS, 0.16 * SS, 0.034 * SS), fill=(236, 250, 255, 255))
    return merge(img, lay)

# ---------------- render masters + contact sheet ----------------
def render(fn, name):
    big = fn().resize((1024, 1024), Image.Resampling.LANCZOS)
    big.save(os.path.join(OUT, f"aiv-icon-{name}-1024.png"))
    small = big.resize((256, 256), Image.Resampling.LANCZOS)
    small.save(os.path.join(OUT, f"aiv-icon-{name}-256.png"))
    return big

masters = {
    "A": (render(candidate_a, "A"), "文档之眼", "文档+眼睛+AI星标 · 蓝→青"),
    "B": (render(candidate_b, "B"), "项目检视", "文件夹+放大镜 · 橙→红"),
    "C": (render(candidate_c, "C"), "大眼睛", "极简大眼睛+AI星标 · 深蓝→紫"),
}

# Font fallback chain (spec-012 L-c4): msyh is not guaranteed on every
# machine; any CJK-capable system font keeps the contact sheet readable.
def load_cjk_font() -> str:
    for cand in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ):
        if os.path.exists(cand):
            return cand
    raise SystemExit("[abort] no CJK-capable system font found (msyh/simhei/simsun)")

FONT = load_cjk_font()
f_title = ImageFont.truetype(FONT, 40)
f_row   = ImageFont.truetype(FONT, 32)
f_small = ImageFont.truetype(FONT, 22)

PAD, CELL, GAP = 50, 96, 34
sizes = [48, 32, 24, 16]
strip_w = sum(sizes) + GAP * (len(sizes) - 1)
BIG = 256
LBL_W = 250
row_h = BIG + 2 * 26
W = PAD + LBL_W + BIG + 90 + strip_w + PAD
H = PAD + 70 + 3 * row_h + 40
sheet = Image.new("RGB", (W, H), (58, 62, 70))
d = ImageDraw.Draw(sheet)
d.text((PAD, PAD - 6), "AI Project Viewer 图标候选 — 看大图和小尺寸(16/24px 模拟任务栏),回一个字母即可",
       font=f_title, fill=(240, 243, 248))

y = PAD + 70
for key in ("A", "B", "C"):
    img, name, desc = masters[key]
    d.text((PAD, y + 60), key, font=ImageFont.truetype(FONT, 88), fill=(255, 208, 80))
    d.text((PAD + 8, y + 170), name, font=f_row, fill=(240, 243, 248))
    d.text((PAD + 8, y + 212), desc, font=f_small, fill=(168, 175, 188))
    big = img.resize((BIG, BIG), Image.Resampling.LANCZOS)
    sheet.paste(big, (PAD + LBL_W, y + 13), big)
    x = PAD + LBL_W + BIG + 90
    for s in sizes:
        ic = img.resize((s, s), Image.Resampling.LANCZOS)
        sheet.paste(ic, (x, y + BIG - s + 20), ic)
        d.text((x + s // 2 - 14, y + BIG + 34), f"{s}px", font=f_small, fill=(150, 158, 170))
        x += s + GAP
    y += row_h

sheet.save(os.path.join(OUT, "aiv-icon-candidates.png"))
print("OK ->", OUT)
for f in sorted(os.listdir(OUT)):
    print(" ", f)
