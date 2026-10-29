"""Turn a photo into coloured ASCII art for the terminal card.

Writes assets/portrait.json (characters + colours only; the photo itself is not stored).
Run locally whenever you want a new picture:

    pip install pillow
    python3 scripts/make_portrait.py path/to/photo.png [--crop L,T,R,B] [--cols 56]
    python3 scripts/make_terminal.py

--crop is in pixels of the original photo (left, top, right, bottom).
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

# light -> dense; brighter pixels get "heavier" glyphs so their colour reads well on the dark card
RAMP = "-:+gitGIT#@"  # git letters in the middle of the ramp; every cell is visible, colour carries the picture
CHAR_ASPECT = 4.8 / 8.7  # glyph width / line height of the portrait font in make_terminal.py


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--crop", help="left,top,right,bottom in pixels")
    ap.add_argument("--cols", type=int, default=56)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "assets" / "portrait.json"))
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGB")
    if a.crop:
        im = im.crop(tuple(int(v) for v in a.crop.split(",")))
    im = ImageEnhance.Contrast(im).enhance(1.25)
    im = ImageEnhance.Color(im).enhance(1.2)

    cols = a.cols
    rows = max(1, round(cols * im.height / im.width * CHAR_ASPECT))
    small = im.resize((cols, rows), Image.LANCZOS)
    gray = ImageOps.autocontrast(small.convert("L"), cutoff=2)

    lines = []
    for y in range(rows):
        row = []
        for x in range(cols):
            lum = gray.getpixel((x, y)) / 255
            ch = RAMP[min(len(RAMP) - 1, int(lum * (len(RAMP) - 1) + 0.5))]
            r, g, b = small.getpixel((x, y))
            # lift shadows so dark hair/skin still shows on the dark card background
            r, g, b = (int(28 + c * 0.9) for c in (r, g, b))
            # quantise colours a little to keep the SVG small
            r, g, b = (min(255, (c // 12) * 12 + 6) for c in (r, g, b))
            row.append([ch, f"#{r:02x}{g:02x}{b:02x}"])
        lines.append(row)

    Path(a.out).parent.mkdir(exist_ok=True)
    Path(a.out).write_text(json.dumps({"cols": cols, "rows": rows, "cells": lines}), encoding="utf-8")
    print(f"wrote {a.out} ({cols}x{rows})")


if __name__ == "__main__":
    main()
