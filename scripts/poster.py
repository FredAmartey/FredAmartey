#!/usr/bin/env python3
"""Build the profile banner out of the Khazad-dum artwork.

The art is a rectangle and a README is a page, so dropping one into the other
leaves a picture sitting on top of the writing. This cuts the rectangle off it
instead. The scene is its own matte: a key built from how lit each part of the
frame is, blurred so it follows whole regions rather than single pixels, keeps
the fight and drops the cave around it. What is left has an organic edge, so it
reads as something on the page rather than a photograph pasted onto it.

The banner then carries its own light: a warm glow spills past the figures onto
the page, sparks drift up through it, and the blaze breathes.

  python3 scripts/poster.py --art art/khazad-dum.jpg --out .
  python3 scripts/poster.py --art art/khazad-dum.jpg --out . \
      --name banner-light.svg --plate '#0d1117'
"""
import argparse
import base64
import io
import os

import numpy as np
from PIL import Image, ImageFilter

WORK_W, WORK_H = 1200, 560
LO, HI = 0.055, 0.190   # where the cave ends and the fight begins
MARGIN = 96             # room left around the matte for the glow to spill into


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def blur(a, r):
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def matte(rgb):
    """Keep what the fire lights, drop the rest.

    Three passes at different scales. The broad one decides which regions of the
    frame survive, so dark armour inside a lit body is not punched out. The
    middle one tightens the silhouette. The sharp one rescues small bright
    things, a torch or a spark, that sit on their own in the dark.
    """
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    k = smooth((blur(lum, 22) - LO) / (HI - LO))
    k = np.maximum(k, smooth((blur(lum, 8) - LO * 1.5) / (HI - LO)) * 0.92)
    return np.clip(np.maximum(k, smooth((lum - 0.16) / 0.22)), 0, 1)


def compose(src):
    aw = round(src.width * WORK_H / src.height)
    art = np.asarray(src.resize((aw, WORK_H), Image.LANCZOS), np.float32) / 255.0
    x0 = (WORK_W - aw) // 2

    rgb = np.zeros((WORK_H, WORK_W, 3), np.float32)
    rgb[:, x0:x0 + aw] = art

    y, x = np.mgrid[0:WORK_H, 0:WORK_W].astype(np.float32)
    frame = (np.clip(x / 80, 0, 1) ** 1.2 * np.clip((WORK_W - 1 - x) / 80, 0, 1) ** 1.2
             * np.clip(y / 46, 0, 1) ** 1.1
             * np.clip((WORK_H - 1 - y) / 90, 0, 1) ** 1.3)
    alpha = matte(rgb) * frame

    # trim to what actually survived, leaving room for the light to spill
    cols = np.nonzero(alpha.max(axis=0) > 0.02)[0]
    rows = np.nonzero(alpha.max(axis=1) > 0.02)[0]
    l = max(0, cols.min() - MARGIN)
    r = min(WORK_W, cols.max() + MARGIN)
    t = max(0, rows.min() - MARGIN // 2)
    b = min(WORK_H, rows.max() + MARGIN // 2)
    return rgb[t:b, l:r], alpha[t:b, l:r]


def plate(rgb, alpha, colour):
    """Flatten onto an opaque backing.

    Keying to transparent only works where the page behind is dark. On a light
    theme the same file reads as a smudge with a halo, so that variant gets its
    own dark backing and becomes a band instead.
    """
    bg = np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255.0
    a = alpha[..., None]
    return rgb * a + bg * (1 - a), np.ones_like(alpha)


def data_uri(rgb, alpha, colors):
    q = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)) \
        .quantize(colors=colors, method=Image.MAXCOVERAGE).convert("RGBA")
    q.putalpha(Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8)))
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def embers(w, h, seed=11, n=46):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        x = float(rng.uniform(0.16, 0.84)) * w
        drift = float(rng.uniform(-0.05, 0.05)) * w
        dur = float(rng.uniform(6.0, 13.0))
        delay = float(rng.uniform(0, 13.0))
        r = float(rng.uniform(0.9, 2.3))
        rise = float(rng.uniform(0.35, 0.9)) * h
        col = ["#ff9a3c", "#ffc763", "#f0561f"][i % 3]
        out.append(
            f'<circle cx="{x:.0f}" cy="{h - 8}" r="{r:.1f}" fill="{col}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.85;0.5;0" '
            f'keyTimes="0;0.12;0.6;1" dur="{dur:.1f}s" begin="-{delay:.1f}s" '
            f'repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{drift:.0f} -{rise:.0f}" dur="{dur:.1f}s" '
            f'begin="-{delay:.1f}s" repeatCount="indefinite"/></circle>'
        )
    return "".join(out)


DEFS = """<defs>
  <radialGradient id="spill" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ff8b2a" stop-opacity="0.22"/>
    <stop offset="0.55" stop-color="#e8531a" stop-opacity="0.07"/>
    <stop offset="1" stop-color="#e8531a" stop-opacity="0"/>
  </radialGradient>
</defs>"""


def build(uri, w, h, rounded=False):
    # the fire lights the page around it, not just the picture
    glow = (f'<ellipse cx="{w * 0.52:.0f}" cy="{h * 0.42:.0f}" rx="{w * 0.62:.0f}" '
            f'ry="{h * 0.56:.0f}" fill="url(#spill)">'
            f'<animate attributeName="opacity" values="0.75;1;0.8;0.95;0.75" '
            f'dur="5.6s" repeatCount="indefinite"/></ellipse>')
    clip = (f'<clipPath id="round"><rect width="{w}" height="{h}" rx="12"/></clipPath>'
            if rounded else "")
    open_g = '<g clip-path="url(#round)">' if rounded else ""
    close_g = "</g>" if rounded else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">'
        f'<title>The bridge of Khazad-dum</title>{DEFS}{clip}{open_g}'
        f'{glow}'
        f'<image href="{uri}" x="0" y="0" width="{w}" height="{h}" '
        f'image-rendering="pixelated"/>'
        f'{embers(w, h)}{close_g}</svg>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--name", default="banner.svg")
    ap.add_argument("--colors", type=int, default=192)
    ap.add_argument("--plate", help="flatten onto this colour instead of alpha")
    args = ap.parse_args()

    rgb, alpha = compose(Image.open(args.art).convert("RGB"))
    if args.plate:
        rgb, alpha = plate(rgb, alpha, args.plate)
    h, w = alpha.shape
    svg = build(data_uri(rgb, alpha, args.colors), w, h, rounded=bool(args.plate))
    path = os.path.join(args.out, args.name)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB) {w}x{h}")


if __name__ == "__main__":
    main()
