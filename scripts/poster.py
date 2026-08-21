#!/usr/bin/env python3
"""Build the profile banner out of the Khazad-dum artwork.

The art is a rectangle and a README is a page, so dropping one into the other
leaves a picture sitting on top of the writing. Fading the rectangle's edges is
not enough either: the hall inside it stays faintly lit, and a soft rectangle is
still a rectangle.

So the hall is cut away and only the fight is kept. A mask of soft shapes covers
what the picture is actually about (the wingspan, the torso, the legs, the whip
of flame, Gandalf, the span they stand on, the chasm under it) and everything
outside it goes. Inside, the edge is decided by how lit the art is, so the
silhouette follows the painting rather than the shapes. The span tapers off at
both ends and the chasm falls away at the foot, so nothing stops on a straight
cut. What is left has an organic outline and carries its own firelight onto the
page.

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

# what the picture is about, in fractions of the source
BLOBS = [
    (0.575, 0.400, 0.505, 0.215),   # wingspan
    (0.575, 0.520, 0.275, 0.235),   # torso and head
    (0.620, 0.680, 0.235, 0.165),   # legs and tail
    (0.580, 0.345, 0.150, 0.115),   # the fire off his crown
    (0.285, 0.560, 0.165, 0.135),   # the whip of flame in his left hand
    (0.215, 0.780, 0.085, 0.080),   # gandalf and his torch
    (0.630, 0.895, 0.270, 0.130),   # the chasm under the span
]
SPAN = ((0.02, 0.835), (1.02, 0.735), 0.062)   # the bridge, running up to the right
BLAZE = (0.58, 0.36)                            # where the light comes from
LO, HI = 0.045, 0.150                           # the lit/unlit boundary
CONTRACT = (0.45, 0.80)                         # squeeze the soft tail off the edge


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def blur(a, r):
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def shape_mask(h, w):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = x / w, y / h
    m = np.zeros((h, w), np.float32)
    for cu, cv, ru, rv in BLOBS:
        m = np.maximum(m, np.clip(1.2 - (((u - cu) / ru) ** 2
                                         + ((v - cv) / rv) ** 2), 0, 1))

    (ax, ay), (bx, by), th = SPAN
    t = np.clip(((u - ax) * (bx - ax) + (v - ay) * (by - ay))
                / ((bx - ax) ** 2 + (by - ay) ** 2), 0, 1)
    d = np.hypot(u - (ax + t * (bx - ax)), v - (ay + t * (by - ay)))
    # the span thins at both ends so it runs off into the dark instead of
    # stopping on a straight cut
    taper = th * (0.20 + 0.80 * np.clip(np.sin(np.pi * t), 0, 1) ** 0.6)
    m = np.maximum(m, np.clip(1.0 - d / np.maximum(taper, 1e-4), 0, 1))
    # nothing may touch the border of the source, or the painting's own edge
    # becomes the cutout's edge and the straight line is back
    m *= np.clip(u / 0.055, 0, 1) ** 0.8 * np.clip((1.0 - u) / 0.055, 0, 1) ** 0.8
    m *= np.clip(v / 0.045, 0, 1) ** 0.8
    # and the fire below falls away toward the foot of the frame
    return m * np.clip((1.0 - v) / 0.14, 0, 1) ** 0.9


def compose(src):
    rgb = np.asarray(src, np.float32) / 255.0
    h, w = rgb.shape[:2]

    m = smooth((blur(shape_mask(h, w), 0.030 * min(h, w)) - 0.18) / 0.42)

    # inside the shapes, the art's own light decides the edge
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    key = smooth((blur(lum, 14) - LO) / (HI - LO))
    key = np.maximum(key, smooth((lum - 0.14) / 0.20))
    # Squeeze the long low-alpha tail off the edge. Left in, it puts a soft dark
    # halo around everything, and a soft halo still reads as a panel.
    alpha = smooth((np.clip(m * key, 0, 1) - CONTRACT[0]) / (CONTRACT[1] - CONTRACT[0]))

    ys, xs = np.nonzero(alpha > 0.02)
    t, b, l, r = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    blaze = ((BLAZE[0] * w - l) / (r - l), (BLAZE[1] * h - t) / (b - t))
    return rgb[t:b, l:r], alpha[t:b, l:r], blaze


def plate(rgb, alpha, colour):
    """Flatten onto an opaque backing.

    Cutting to transparent only works where the page behind is dark. On a light
    theme the soft edges read as grey haze, so that variant gets its own dark
    backing and becomes a card instead.
    """
    bg = np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255.0
    a = alpha[..., None]
    return rgb * a + bg * (1 - a), np.ones_like(alpha)


def data_uri(rgb, alpha, quality, width):
    """WebP, not PNG.

    A soft alpha channel is what costs here: the same cutout is 733KB as a
    palettised PNG and 234KB as WebP, for no visible difference at the size it
    is ever drawn. The plate is also kept to roughly twice its width on the page
    rather than the source's full resolution.
    """
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    am = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8))
    if width and width < im.width:
        size = (width, round(im.height * width / im.width))
        im, am = im.resize(size, Image.LANCZOS), am.resize(size, Image.LANCZOS)
    out = im.convert("RGBA")
    out.putalpha(am)
    buf = io.BytesIO()
    out.save(buf, format="WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def embers(w, h, seed=11, n=40):
    """Sparks off the chasm, drifting up past the fight."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        x = float(rng.uniform(0.22, 0.80)) * w
        drift = float(rng.uniform(-0.07, 0.07)) * w
        dur = float(rng.uniform(6.0, 13.0))
        delay = float(rng.uniform(0, 13.0))
        r = float(rng.uniform(1.0, 2.8))
        rise = float(rng.uniform(0.35, 0.92)) * h
        col = ["#ff9a3c", "#ffc763", "#f0561f"][i % 3]
        out.append(
            f'<circle cx="{x:.0f}" cy="{h - 6}" r="{r:.1f}" fill="{col}" opacity="0">'
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
    <stop offset="0" stop-color="#ff8b2a" stop-opacity="0.26"/>
    <stop offset="0.5" stop-color="#e8531a" stop-opacity="0.08"/>
    <stop offset="1" stop-color="#e8531a" stop-opacity="0"/>
  </radialGradient>
</defs>"""


def build(uri, w, h, blaze, rounded=False):
    # the fire lights the page around it, not just the picture
    glow = (f'<ellipse cx="{blaze[0] * w:.0f}" cy="{blaze[1] * h:.0f}" '
            f'rx="{w * 0.78:.0f}" ry="{h * 0.62:.0f}" fill="url(#spill)">'
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
    ap.add_argument("--quality", type=int, default=88)
    ap.add_argument("--width", type=int, default=620)
    ap.add_argument("--plate", help="flatten onto this colour instead of alpha")
    args = ap.parse_args()

    rgb, alpha, blaze = compose(Image.open(args.art).convert("RGB"))
    if args.plate:
        rgb, alpha = plate(rgb, alpha, args.plate)
    h, w = alpha.shape
    if args.width and args.width < w:
        h, w = round(h * args.width / w), args.width
    svg = build(data_uri(rgb, alpha, args.quality, args.width), w, h, blaze,
                rounded=bool(args.plate))
    path = os.path.join(args.out, args.name)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB) {w}x{h}")


if __name__ == "__main__":
    main()
