# -*- coding: utf-8 -*-
"""spec-017 icon-alignment probe (read-only, zero disturbance).

Connects to the ALREADY-RUNNING dev instance on CDP 9322 (never launches,
never focuses — live-inspect discipline), rasterizes each sidebar-header
icon svg in-page at 4x, and reports the INK bounding box vs the 24-grid
center. Optical truth, not eyeballing (lessons L45 family).
"""
import json
from playwright.sync_api import sync_playwright

CDP = 9322

JS = """async () => {
  const svgs = [...document.querySelectorAll('.sidebar-header .header-icon svg')];
  const out = [];
  for (const svg of svgs) {
    const btn = svg.closest('button');
    const label = btn ? (btn.getAttribute('aria-label') || btn.className) : '?';
    const ser = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([ser], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.decoding = 'sync';
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });
    const S = 4, V = 24;               // 4x scale of the 24 viewBox
    const c = document.createElement('canvas');
    c.width = V * S; c.height = V * S;
    const ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0, V * S, V * S);
    const d = ctx.getImageData(0, 0, V * S, V * S).data;
    let minX = 1e9, minY = 1e9, maxX = -1, maxY = -1, n = 0;
    for (let y = 0; y < V * S; y++) {
      for (let x = 0; x < V * S; x++) {
        if (d[(y * V * S + x) * 4 + 3] > 16) {   // ink = any alpha
          n++;
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
    }
    URL.revokeObjectURL(url);
    out.push({
      label,
      inkX: [minX / S, maxX / S],
      inkY: [minY / S, maxY / S],
      inkCenterX: (minX + maxX) / 2 / S,
      inkCenterY: (minY + maxY) / 2 / S,
      px: n / S / S,
    });
  }
  // Button box centers (the css side): svg bounding rects relative to btn
  const boxes = svgs.map(s => {
    const btn = s.closest('button');
    const b = btn.getBoundingClientRect(), r = s.getBoundingClientRect();
    return { label: btn.getAttribute('aria-label'),
             svgTopInBtn: r.top - b.top, btnH: b.height, svgH: r.height };
  });
  return { ink: out, boxes };
}"""

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP}")
    page = browser.contexts[0].pages[0]
    data = page.evaluate(JS)
    print(json.dumps(data, indent=1, ensure_ascii=False))
    print("\n--- ink-center deltas vs refresh baseline (24-grid) ---")
    ink = {i["label"]: i for i in data["ink"]}
    base = ink.get("Refresh", list(ink.values())[1 if len(ink) > 1 else 0])
    for label, i in ink.items():
        print(f"{label:20s} center=({i['inkCenterX']:.2f},{i['inkCenterY']:.2f})"
              f"  d=({i['inkCenterX']-base['inkCenterX']:+.2f},{i['inkCenterY']-base['inkCenterY']:+.2f})"
              f"  inkY={i['inkY']}")
    for b in data["boxes"]:
        print(f"box {b['label']:20s} svgTopInBtn={b['svgTopInBtn']:.2f} btnH={b['btnH']:.1f} svgH={b['svgH']:.1f}")
