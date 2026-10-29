"""Turn a photo into coloured ASCII art for the terminal card.

Writes assets/portrait.json (characters + colours only; the photo itself is not stored).
Run locally whenever you want a new picture:

    pip install pillow numpy scikit-image "rembg[cpu]"
    python3 scripts/make_portrait.py path/to/photo.png [--crop L,T,R,B] [--cols 80]
    python3 scripts/make_terminal.py

--crop is in pixels of the original photo (left, top, right, bottom); aim for head and shoulders.
The background is removed automatically (rembg); pass --keep-background to skip that.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from skimage import color as skcolor
from skimage import exposure, transform

RAMP = ".:-=+itgIGT#%@"   # dark -> bright; the git letters sit in the middle
CELL_W, CELL_H = 3.0, 3.0  # must match P_CW / P_LH in make_terminal.py


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--crop", help="left,top,right,bottom in pixels")
    ap.add_argument("--cols", type=int, default=80)
    ap.add_argument("--keep-background", action="store_true")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "assets" / "portrait.json"))
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGB")
    if a.keep_background:
        im = im.convert("RGBA")
    else:
        from rembg import new_session, remove
        im = remove(im, session=new_session("u2net_human_seg")).convert("RGBA")
    if a.crop:
        im = im.crop(tuple(int(v) for v in a.crop.split(",")))

    px = np.asarray(im).astype(float) / 255
    rgb, alpha = px[..., :3], px[..., 3]
    # local contrast so eyes, smile and hair detail survive the downscale
    lum = exposure.equalize_adapthist(skcolor.rgb2gray(rgb), clip_limit=0.02, kernel_size=24)

    cols = a.cols
    rows = round(cols * lum.shape[0] / lum.shape[1] * CELL_W / CELL_H)
    L = transform.resize(lum, (rows, cols), anti_aliasing=True)
    A = transform.resize(alpha, (rows, cols), anti_aliasing=True)
    C = transform.resize(rgb, (rows, cols, 3), anti_aliasing=True)

    cells = []
    for y in range(rows):
        row = []
        for x in range(cols):
            if A[y, x] < 0.45:
                row.append([" ", None])  # background: leave empty
                continue
            v = float(np.clip(L[y, x], 0, 1))
            ch = RAMP[int(v * (len(RAMP) - 1) + 0.5)]
            # lift shadows a little so dark hair still shows on the dark card, then quantise
            r, g, b = (min(255, int((30 + c * 255 * 0.95) * 1.12)) for c in C[y, x])
            r, g, b = (min(255, (c // 10) * 10 + 5) for c in (r, g, b))
            row.append([ch, f"#{r:02x}{g:02x}{b:02x}"])
        cells.append(row)

    # trim empty rows left above/below the cut-out
    filled = [i for i, row in enumerate(cells) if any(c is not None for _, c in row)]
    cells = cells[filled[0]:filled[-1] + 1]
    rows = len(cells)

    Path(a.out).parent.mkdir(exist_ok=True)
    Path(a.out).write_text(json.dumps({"cols": cols, "rows": rows, "cells": cells},
                                      separators=(",", ":")), encoding="utf-8")
    print(f"wrote {a.out} ({cols}x{rows})")


if __name__ == "__main__":
    main()
