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


DEMO_EXE_SRC = """// demo.exe fixture — a REAL tiny console program so the owner's
// right-click "Run" verification actually runs something (0.6.11: the old
// fixture was a fake PE header and the OS rightly refused to launch it).
fn main() {
    println!("Hello from demo.exe - AI Project Viewer run test.");
    println!("This window stays open until you press Enter.");
    let mut line = String::new();
    std::io::stdin().read_line(&mut line).ok();
}
"""


def handoff_fixtures(project_root):
    """spec-006 menu fixtures — created only when absent (static, tiny):
    example.url (http(s) InternetShortcut) and demo.exe (a real, tiny
    rustc-compiled console app: prints two lines, waits for Enter)."""
    url = os.path.join(project_root, "example.url")
    if not os.path.exists(url):
        with open(url, "w", encoding="ascii", newline="\r\n") as f:
            f.write("[InternetShortcut]\r\n"
                    "URL=https://example.com/aiv-handoff\r\n"
                    "IconIndex=1\r\n")
    exe = os.path.join(project_root, "demo.exe")
    if not os.path.exists(exe):
        import shutil
        import subprocess
        import tempfile
        rustc = shutil.which("rustc") or os.path.expandvars(
            r"%USERPROFILE%\.cargo\bin\rustc.exe")
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "demo_exe.rs")
            with open(src, "w", encoding="utf-8") as f:
                f.write(DEMO_EXE_SRC)
            subprocess.run([rustc, "-O", "-o", exe, src], check=True)


def spine_pdf(path):
    """arXiv-style page: rotated left-spine text + dense text above and
    below a sparse author band (0.8.9 select-everything trap: the spine's
    tall bbox gave it a page-scale row-merge radius, and the whitespace
    band had no real rows to clamp onto)."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.saveState()
    c.translate(30, h - 50)
    c.rotate(-90)
    c.setFont("Helvetica", 10)
    c.drawString(0, 0, "arXiv:0000.0000v1 [q-fin.CP] 1 Jan 2026 SPINE TRAP")
    c.restoreState()
    c.setFont("Helvetica", 11)
    for i in range(1, 9):
        c.drawString(70, h - 70 - 18 * i,
                     f"Top line {i}: the quick brown fox jumps over the lazy dog.")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(70, h - 280, "Author Band Whitespace")
    c.setFont("Helvetica", 10)
    c.drawString(70, h - 305, "Somewhere University")
    for i in range(1, 9):
        c.drawString(70, h - 380 - 18 * i,
                     f"Bottom line {i}: pack my box with five dozen liquor jugs.")
    c.showPage()
    c.save()


def _w(root, rel, text, encoding="utf-8", bom=False):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        if bom:
            f.write(b"\xef\xbb\xbf")
        if isinstance(text, bytes):
            f.write(text)
        else:
            f.write(text.encode(encoding))


def rebuild_project(root):
    """Recreate the FULL AIV-TestProject fixture IN-REPO (owner 2026-10-24:
    deleted the Desktop copy — "别放桌面,仓库里找个地方放"). Content is
    pinned to what the e2e suites assert (phase3/pdf-suite/git-suite…),
    not a byte-for-byte clone of the lost original. Tree stays NON-git
    (git-suite's third instance)."""
    import shutil as _sh

    _sh.rmtree(root, ignore_errors=True)
    os.makedirs(os.path.join(root, "data"))
    os.makedirs(os.path.join(root, "assets"))

    _w(root, "README.md", "\n".join([
        "# AI Project Viewer Fixture",
        "",
        "Sample markdown with a [link](https://example.com/aiv) and prose "
        "for the paper-typography guards.",
        "",
        "## Tasks",
        "",
        "- [x] fixture lives in the repo now",
        "- [ ] keep the desktop clean",
        "",
        "## Code",
        "",
        "```python",
        "def main() -> None:",
        "    print('fixture')",
        "```",
        "",
    ]) + "\n")
    _w(root, "config.yaml", "name: aiv-fixture\nversion: 2\n")
    _w(root, "notes.txt", "fixture notes\nsecond line\n")
    _w(root, "sample.csv", "id,name,score\n1,alpha,10\n2,beta,20\n")
    _w(root, "server.log",
       "2026-10-24 10:00:00 INFO boot ok\n2026-10-24 10:00:01 WARN warm\n")
    _w(root, "metrics.json",
       '{"project": "aiv", "files": 31, "ok": true}\n')
    _w(root, "main.py", '# Entry point\nprint("AIV fixture")\n')
    _w(root, "utils.py", "def add(a, b):\n    return a + b\n")
    # Lives under src/ like the original fixture: phase3's identity guard
    # asserts data-rel ENDS WITH "/index.html" (a slash-carrying rel).
    _w(root, "src/index.html",
       "<!doctype html>\n<h1>HTML viewed as Code</h1>\n<p>fixture</p>\n")
    _w(root, "hello.bat", "@echo off\necho fixture\n")
    _w(root, "hello.ps1", "Write-Host fixture\n")
    _w(root, "sample.msi", b"MSI fixture stub " + b"\0" * 512)
    _w(root, "demo.mp4",
       b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
       + b"\x00\x00\x00\x08free")
    # NOTE: tree_row("main.py") matches this row first when src/ is
    # expanded (src's children precede root files in DOM) — it must carry
    # the "Entry point" string phase3 asserts.
    _w(root, "src/main.py", '# Entry point (src copy)\nfrom utils import add\n')
    _w(root, "src/deep/migrations/001_init.sql",
       "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);\n")

    # edge-cases: encodings + size guards (manifest per testing.md §1.5)
    _w(root, "edge-cases/chinese-gb18030.txt",
       "编码兜底正确:GB18030 fixture\n", encoding="gb18030")
    _w(root, "edge-cases/utf8-bom.txt", "BOM fixture\n", bom=True)
    _w(root, "edge-cases/utf16.txt", "UTF-16 fixture\n", encoding="utf-16")
    _w(root, "edge-cases/binary-blob.bin",
       bytes(range(256)) * 16)
    _w(root, "edge-cases/large-5mb.txt",
       "".join(f"line {i:07d} filler text for size guard\n"
               for i in range(60000)))
    with open(os.path.join(root, "edge-cases", "huge-21mb.bin"), "wb") as f:
        chunk = bytes(range(256)) * 4096
        for _ in range(21):
            f.write(chunk)

    # assets: five image formats; the SVG deliberately carries script
    # payloads (rendered as <img> they must never execute — acceptance §1.5)
    from PIL import Image
    img = Image.new("RGB", (480, 320))
    px = img.load()
    for y in range(320):
        for x in range(480):
            px[x, y] = (x * 255 // 480, y * 255 // 320, 128)
    img.save(os.path.join(root, "assets", "photo.jpg"), quality=85)
    img.save(os.path.join(root, "assets", "picture.png"))
    img.save(os.path.join(root, "assets", "banner.webp"))
    pal = Image.new("P", (16, 16))
    pal.putpalette([i // 3 % 256 for i in range(768)])
    pal.save(os.path.join(root, "assets", "icon.gif"))
    _w(root, "assets/logo.svg",
       '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40" '
       'onload="window.__svgOnloadRan=1">'
       "<script>alert(1)</script>"
       '<rect width="120" height="40" fill="#3b8efb"/>'
       '<text x="8" y="26" font-size="14" fill="#fff">AIV</text></svg>\n')

    handoff_fixtures(root)

    # pdf/ via the same jobs as main()
    pdf_dir = os.path.join(root, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    text_pdf(os.path.join(pdf_dir, "sample-10p-text.pdf"), 10)
    text_pdf(os.path.join(pdf_dir, "sample-100p-text.pdf"), 100)
    for i in range(1, 6):
        text_pdf(os.path.join(pdf_dir, f"tab-{i}.pdf"), 2,
                 header=f"Tab fixture {i}")
    spine_pdf(os.path.join(pdf_dir, "sample-spine.pdf"))
    scan_pdf(os.path.join(pdf_dir, "sample-100p-scan.pdf"), 100)
    print(f"project rebuilt at {root}")


FIXTURE_PROJECT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "fixtures", "AIV-TestProject")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target",
                    default=os.path.join(FIXTURE_PROJECT, "pdf"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--rebuild-project", action="store_true",
                    help="regenerate the FULL in-repo AIV-TestProject tree")
    args = ap.parse_args()
    os.makedirs(args.target, exist_ok=True)

    if args.rebuild_project:
        rebuild_project(FIXTURE_PROJECT)
        return

    handoff_fixtures(os.path.dirname(args.target.rstrip("\\/")))

    jobs = ([f"sample-{n}p-text.pdf" for n in (10, 100)]
            + [f"tab-{i}.pdf" for i in range(1, 6)]
            + ["sample-spine.pdf"])
    existing = [j for j in jobs + ["sample-100p-scan.pdf"]
                if os.path.exists(os.path.join(args.target, j))]
    if existing and not args.force:
        raise SystemExit(f"refusing to overwrite {existing}; pass --force")

    text_pdf(os.path.join(args.target, "sample-10p-text.pdf"), 10)
    text_pdf(os.path.join(args.target, "sample-100p-text.pdf"), 100)
    spine_pdf(os.path.join(args.target, "sample-spine.pdf"))
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
