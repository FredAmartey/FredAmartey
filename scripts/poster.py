#!/usr/bin/env python3
"""Wrap the Khazad-dum artwork in an SVG and give it a little motion.

The art carries the whole scene, so nothing is drawn over it. All this adds is
the ambient movement a still cannot have: sparks off the fire below, and a
flicker on the two torches in the arcade. Everything is inlined, so the banner
is one self-contained file that survives GitHub's image proxy.

  python3 scripts/poster.py --art art/khazad-dum.png --out .
"""
import argparse
import base64
import io
import os

import numpy as np
from PIL import Image

# where the fire actually is in the art, as fractions of its size
TORCHES = [(0.167, 0.183), (0.421, 0.216)]
CHASM = (0.20, 0.92)   # the span of the pit the sparks come off, in x
FIRE = (0.61, 0.39)    # the blaze behind him


def data_uri(img, colors):
    q = img.convert("RGB").quantize(colors=colors, method=Image.MAXCOVERAGE)
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def embers(w, h, seed=11, n=44):
    """Sparks off the fire below, carried up through the hall."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        x = float(rng.uniform(*CHASM)) * w
        drift = float(rng.uniform(-0.035, 0.035)) * w
        dur = float(rng.uniform(5.5, 12.0))
        delay = float(rng.uniform(0, 12.0))
        r = float(rng.uniform(1.0, 2.6))
        rise = float(rng.uniform(0.22, 0.62)) * h
        col = ["#ff9a3c", "#ffc763", "#f0561f"][i % 3]
        out.append(
            f'<circle cx="{x:.0f}" cy="{h - 8}" r="{r:.1f}" fill="{col}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.9;0.65;0" keyTimes="0;0.1;0.62;1" '
            f'dur="{dur:.1f}s" begin="-{delay:.1f}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{drift:.0f} -{rise:.0f}" dur="{dur:.1f}s" begin="-{delay:.1f}s" '
            f'repeatCount="indefinite"/></circle>'
        )
    return "".join(out)


def flicker(cx, cy, r, values, dur, grad="torchglow"):
    return (f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{r:.0f}" ry="{r:.0f}" '
            f'fill="url(#{grad})" style="mix-blend-mode:screen">'
            f'<animate attributeName="opacity" values="{values}" dur="{dur}s" '
            f'repeatCount="indefinite"/></ellipse>')


DEFS = """<defs>
  <radialGradient id="torchglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffcf82" stop-opacity="0.55"/>
    <stop offset="0.45" stop-color="#ff9a34" stop-opacity="0.20"/>
    <stop offset="1" stop-color="#ff8020" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="blaze" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ff8c2c" stop-opacity="0.16"/>
    <stop offset="1" stop-color="#ff6a14" stop-opacity="0"/>
  </radialGradient>
</defs>"""


def build(uri, w, h):
    torches = "".join(
        flicker(fx * w, fy * h, w * 0.075, "0.35;0.75;0.45;0.65;0.35", 3.1 + i * 0.9)
        for i, (fx, fy) in enumerate(TORCHES)
    )
    blaze = flicker(FIRE[0] * w, FIRE[1] * h, w * 0.34,
                    "0.45;0.9;0.6;0.8;0.45", 5.6, grad="blaze")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">'
        f'<title>The bridge of Khazad-dum</title>'
        f'{DEFS}'
        f'<image href="{uri}" x="0" y="0" width="{w}" height="{h}" '
        f'image-rendering="pixelated"/>'
        f'{torches}{blaze}{embers(w, h)}'
        f'</svg>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--name", default="banner.svg")
    ap.add_argument("--colors", type=int, default=192)
    args = ap.parse_args()

    art = Image.open(args.art)
    svg = build(data_uri(art, args.colors), art.width, art.height)
    path = os.path.join(args.out, args.name)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB) "
          f"{art.width}x{art.height}")


if __name__ == "__main__":
    main()
