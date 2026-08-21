#!/usr/bin/env python3
"""Build the profile banner out of the Khazad-dum artwork.

The art is portrait and the README box is wide, so pasting it in leaves a
rectangle sitting on the page. Instead the scene is dissolved into the box: it
is cropped to the fight, faded out inside its own edges (its outer columns are
nearly black already, so the boundary disappears before anyone finds it), and
the firelight is thrown out into the dark either side. The frame itself fades to
transparent, so the banner has no edge of its own and picks up whatever
background GitHub is using.

Motion is ambient only: sparks off the fire and a slow breath on the blaze.

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

W, H = 1200, 500
CROP = (0, 320, 736, 1140)   # the fight, without the empty ceiling or the lava foot
FEATHER = 92                 # how far inside its own edge the art dissolves


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def compose(src):
    """Lay the art into a wide dark frame and let the two meet in the middle."""
    art_img = src.crop(CROP)
    aw = round(art_img.width * H / art_img.height)
    art = np.asarray(art_img.resize((aw, H), Image.LANCZOS), np.float32)
    x0 = (W - aw) // 2

    y, x = np.mgrid[0:H, 0:W].astype(np.float32)

    # firelight thrown past the edges of the picture into the dark
    spill = np.zeros((H, W, 3), np.float32)
    spill[:, :x0] = art[:, :4].mean(axis=1, keepdims=True)
    spill[:, x0 + aw:] = art[:, -4:].mean(axis=1, keepdims=True)
    spill = np.asarray(Image.fromarray(spill.astype(np.uint8))
                       .filter(ImageFilter.GaussianBlur(90)), np.float32)
    reach = np.clip(1.0 - (np.abs(x - W / 2) - aw / 2) / 300.0, 0, 1)[..., None] ** 1.5
    canvas = np.clip(spill * reach * 1.25, 0, 255)

    inner = np.zeros((H, W, 3), np.float32)
    inner[:, x0:x0 + aw] = art

    hold = smooth(np.clip((x - x0) / FEATHER, 0, 1)
                  * np.clip((x0 + aw - 1 - x) / FEATHER, 0, 1)
                  * np.clip(y / 58, 0, 1) * np.clip((H - 1 - y) / 50, 0, 1))[..., None]
    rgb = canvas * (1 - hold) + inner * hold

    # the banner ends where its light ends, not on a rectangle
    frame = (np.clip(x / 110, 0, 1) ** 1.3 * np.clip((W - 1 - x) / 110, 0, 1) ** 1.3
             * np.clip(y / 34, 0, 1) ** 1.1 * np.clip((H - 1 - y) / 26, 0, 1) ** 1.1)
    lit = np.clip(rgb.max(axis=2) / 255.0 * 2.6, 0, 1)
    alpha = np.clip(np.maximum(hold[..., 0], lit), 0, 1) * frame
    return rgb, alpha, x0, aw


def plate(rgb, alpha, colour):
    """Flatten onto an opaque backing.

    Fading to transparent only works where the page behind is dark. On a light
    theme the same file reads as a smudge with a halo, so that variant gets its
    own dark backing and becomes a full-bleed band instead.
    """
    bg = np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    a = np.clip(alpha, 0, 1)[..., None]
    return rgb * a + bg * (1 - a), np.ones_like(alpha)


def data_uri(rgb, alpha, colors):
    q = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)) \
        .quantize(colors=colors, method=Image.MAXCOVERAGE).convert("RGBA")
    q.putalpha(Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8)))
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def embers(seed=11, n=52):
    """Sparks off the fire below, drifting out across the whole frame."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        x = float(rng.uniform(0.14, 0.86)) * W
        drift = float(rng.uniform(-46, 46))
        dur = float(rng.uniform(6.0, 13.0))
        delay = float(rng.uniform(0, 13.0))
        r = float(rng.uniform(0.9, 2.4))
        rise = float(rng.uniform(0.30, 0.85)) * H
        col = ["#ff9a3c", "#ffc763", "#f0561f"][i % 3]
        out.append(
            f'<circle cx="{x:.0f}" cy="{H - 10}" r="{r:.1f}" fill="{col}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.85;0.55;0" '
            f'keyTimes="0;0.12;0.6;1" dur="{dur:.1f}s" begin="-{delay:.1f}s" '
            f'repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{drift:.0f} -{rise:.0f}" dur="{dur:.1f}s" '
            f'begin="-{delay:.1f}s" repeatCount="indefinite"/></circle>'
        )
    return "".join(out)


DEFS = """<defs>
  <radialGradient id="blaze" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ff8c2c" stop-opacity="0.15"/>
    <stop offset="1" stop-color="#ff6a14" stop-opacity="0"/>
  </radialGradient>
</defs>"""


def build(uri, x0, aw, rounded=False):
    blaze = (f'<ellipse cx="{x0 + aw * 0.58:.0f}" cy="{H * 0.34:.0f}" '
             f'rx="{aw * 0.85:.0f}" ry="{H * 0.5:.0f}" fill="url(#blaze)" '
             f'style="mix-blend-mode:screen">'
             f'<animate attributeName="opacity" values="0.45;0.95;0.6;0.85;0.45" '
             f'dur="5.6s" repeatCount="indefinite"/></ellipse>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">'
        f'<title>The bridge of Khazad-dum</title>'
        f'{DEFS}'
        + (f'<clipPath id="round"><rect width="{W}" height="{H}" rx="12"/></clipPath>'
           if rounded else "")
        + (f'<g clip-path="url(#round)">' if rounded else "")
        + f'<image href="{uri}" x="0" y="0" width="{W}" height="{H}" '
          f'image-rendering="pixelated"/>'
        + f'{blaze}{embers()}'
        + (f'</g>' if rounded else "")
        + f'</svg>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--name", default="banner.svg")
    ap.add_argument("--colors", type=int, default=192)
    ap.add_argument("--plate", help="flatten onto this colour instead of alpha")
    args = ap.parse_args()

    rgb, alpha, x0, aw = compose(Image.open(args.art).convert("RGB"))
    if args.plate:
        rgb, alpha = plate(rgb, alpha, args.plate)
    svg = build(data_uri(rgb, alpha, args.colors), x0, aw, rounded=bool(args.plate))
    path = os.path.join(args.out, args.name)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB) "
          f"{W}x{H}, art {aw} wide at x={x0}")


if __name__ == "__main__":
    main()
