# -*- coding: utf-8 -*-
"""Regenerate the AIV-TestProject PDF fixtures (spec of the originals):

  sample-10p-text.pdf   10 pages x 12 lines, selectable text
  sample-100p-text.pdf  100 pages, same pattern
  sample-100p-scan.pdf  100 pages, image-only (noise JPEG, ~18 MB total)
  tab-1.pdf..tab-5.pdf  2 pages each, small text

Line pattern is load-bearing: e2e scripts assert on
"Page {p} line {l}: The quick brown fox jumps over the lazy dog. ..."
and the PDF suite searches "Page 8". Keep it if you ever edit this.

Usage (pywork python):
  python make-fixtures.py [--target DIR] [--force]
Defaults to %USERPROFILE%\\Desktop\\AIV-TestProject\\pdf; refuses to
overwrite existing fixtures unless --force.
"""
import argparse
import io
import os
import random

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

LINE = ("Page {p} line {l}: The quick brown fox jumps over the lazy dog. "
        "Pack my box with five dozen liquor jugs.")
LINES_PER_PAGE = 12


def text_pdf(path, pages, header=None):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    for p in range(1, pages + 1):
        if header:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(72, h - 60, header)
        c.setFont("Helvetica", 11)
        for l in range(1, LINES_PER_PAGE + 1):
            c.drawString(72, h - 90 - (l - 1) * 22, LINE.format(p=p, l=l))
        c.showPage()
    c.save()


def scan_pdf(path, pages, seed=42):
    # Tuned to land near the original 18.4 MB spec (pure pixel noise is
    # incompressible; 2px blocks + q40 at 150dpi-ish hits the range).
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    rng = random.Random(seed)
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    W, H, B = 880, 1240, 2
    for _ in range(pages):
        img = Image.new("RGB", (W, H))
        px = img.load()
        for by in range(0, H, B):
            base = rng.randrange(220, 256)
            for bx in range(0, W, B):
                v = max(0, min(255, base + rng.randrange(-14, 15)))
                for dy in range(B):
                    for dx in range(B):
                        px[bx + dx, by + dy] = (v, v, v)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=40)
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=w, height=h)
        c.showPage()
    c.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target",
                    default=os.path.expandvars(
                        r"%USERPROFILE%\Desktop\AIV-TestProject\pdf"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.target, exist_ok=True)

    jobs = ([f"sample-{n}p-text.pdf" for n in (10, 100)]
            + [f"tab-{i}.pdf" for i in range(1, 6)])
    existing = [j for j in jobs + ["sample-100p-scan.pdf"]
                if os.path.exists(os.path.join(args.target, j))]
    if existing and not args.force:
        raise SystemExit(f"refusing to overwrite {existing}; pass --force")

    text_pdf(os.path.join(args.target, "sample-10p-text.pdf"), 10)
    text_pdf(os.path.join(args.target, "sample-100p-text.pdf"), 100)
    for i in range(1, 6):
        text_pdf(os.path.join(args.target, f"tab-{i}.pdf"), 2,
                 header=f"Tab fixture {i}")
    scan_pdf(os.path.join(args.target, "sample-100p-scan.pdf"), 100)

    from pypdf import PdfReader
    for f in sorted(os.listdir(args.target)):
        if f.endswith(".pdf"):
            path = os.path.join(args.target, f)
            print(f"{f}: {len(PdfReader(path).pages)} pages, "
                  f"{os.path.getsize(path) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
