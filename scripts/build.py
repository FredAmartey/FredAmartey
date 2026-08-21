#!/usr/bin/env python3
"""Build the profile banner: the bridge of Khazad-dum.

Takes the two character pieces (in art/, cutouts with alpha) and stages them
either side of a stone span over a burning chasm. The cavern, bridge, firelight
and embers are drawn in SVG; the characters ride along as embedded PNGs so the
banner is one self-contained file.

  python3 scripts/build.py --gandalf art/gandalf.png --balrog art/balrog.png --out .
"""
import argparse
import base64
import io
import os

import numpy as np
from PIL import Image

# ---------- canvas ----------

W, H = 1200, 440
DECK = 372            # top of the bridge deck
G_H = 190             # gandalf's height on the deck
B_H = 430             # the balrog towers over him
G_CX = 330            # where each one stands
B_CX = 810


def trim(img):
    bb = img.getbbox()
    return img.crop(bb) if bb else img


def ground_row(img, thresh=0.01):
    """The row the figure actually stands on.

    A cutout's bounding box is not its feet: these pieces carry a fringe of
    near-transparent pixels (Gandalf's runs 64 rows deep), and the very lowest
    solid pixel can be a tail or a claw tip rather than the stance. So take the
    lowest row carrying a real footprint, and stand the figure on that. Aligning
    to the bounding box instead leaves them hovering above the bridge.
    """
    a = np.asarray(img)
    solid = (a[:, :, 3] > 200).sum(axis=1)
    need = max(2, int(thresh * img.width))
    rows = np.nonzero(solid >= need)[0]
    return int(rows.max()) + 1 if len(rows) else img.height


def foot_span(img, depth=0.03):
    """Where the figure actually meets the ground, as fractions of its width.

    The contact shadow has to key off this, not off the sprite box: the box
    spans wingtips and an outstretched sword, so a shadow scaled to it turns
    into a wide dark pool that reads as a figure hovering over its own drop
    shadow.
    """
    a = np.asarray(img)
    gr = ground_row(img)
    top = max(0, int(gr - depth * img.height))
    sole = (a[top:gr, :, 3] > 200).any(axis=0)
    cols = np.nonzero(sole)[0]
    if not len(cols):
        return 0.5, 0.3
    return (cols.mean() / img.width,
            (cols.max() - cols.min() + 1) / img.width)


def place(img, stand_h, cx, sink=4.0):
    """Scale so the foot plane lands on the deck; return the SVG box.

    `sink` tucks the base a few units under the deck line. Downscaling tapers
    the sprite's last rows to near-transparent, so a mathematically exact
    landing still shows daylight between the figure and its shadow; sinking it
    puts solid pixels on the stone.
    """
    scale = stand_h / ground_row(img)
    w, h = img.width * scale, img.height * scale
    # line the figure up by its feet, so it stands where we asked it to
    fx, _ = foot_span(img)
    return w, h, cx - w * fx, DECK + sink - stand_h


def fit_height(img, h):
    w = max(1, round(img.width * h / img.height))
    return img.resize((w, round(h)), Image.LANCZOS)


def quantize(img, colors=200):
    """pixel art survives a small palette, and the file gets much smaller"""
    alpha = img.getchannel("A")
    rgb = img.convert("RGB").quantize(colors=colors, method=Image.MAXCOVERAGE)
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def data_uri(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------- scene ----------

def embers(seed=11, n=34):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        x = float(rng.uniform(20, W - 20))
        drift = float(rng.uniform(-22, 22))
        dur = float(rng.uniform(5.0, 11.0))
        delay = float(rng.uniform(0, 11.0))
        r = float(rng.uniform(0.9, 2.3))
        rise = float(rng.uniform(150, 330))
        col = ["#ff9a3c", "#ffc763", "#f0561f"][i % 3]
        out.append(
            f'<circle cx="{x:g}" cy="{H - 4:g}" r="{r:g}" fill="{col}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.95;0.75;0" keyTimes="0;0.12;0.6;1" '
            f'dur="{dur:g}s" begin="-{delay:g}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{drift:g} -{rise:g}" dur="{dur:g}s" begin="-{delay:g}s" '
            f'repeatCount="indefinite"/></circle>'
        )
    return "".join(out)


DEFS = f"""<defs>
  <linearGradient id="air" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#08070c"/>
    <stop offset="0.5" stop-color="#100a10"/>
    <stop offset="1" stop-color="#25100e"/>
  </linearGradient>
  <linearGradient id="pit" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff6a14" stop-opacity="0"/>
    <stop offset="0.35" stop-color="#ff6a14" stop-opacity="0.18"/>
    <stop offset="0.72" stop-color="#ff8420" stop-opacity="0.50"/>
    <stop offset="1" stop-color="#ffc25c" stop-opacity="0.80"/>
  </linearGradient>
  <radialGradient id="hellglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ff7a24" stop-opacity="0.55"/>
    <stop offset="0.55" stop-color="#e0431a" stop-opacity="0.22"/>
    <stop offset="1" stop-color="#e0431a" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="staffglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffe9b8" stop-opacity="0.85"/>
    <stop offset="0.4" stop-color="#ffb648" stop-opacity="0.35"/>
    <stop offset="1" stop-color="#ff9a2b" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="stone" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#3a3944"/>
    <stop offset="0.35" stop-color="#26242e"/>
    <stop offset="1" stop-color="#141219"/>
  </linearGradient>
  <linearGradient id="edges" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#08070c" stop-opacity="0.95"/>
    <stop offset="0.12" stop-color="#08070c" stop-opacity="0"/>
    <stop offset="0.88" stop-color="#08070c" stop-opacity="0"/>
    <stop offset="1" stop-color="#08070c" stop-opacity="0.95"/>
  </linearGradient>
  <linearGradient id="topfade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#08070c" stop-opacity="0.9"/>
    <stop offset="1" stop-color="#08070c" stop-opacity="0"/>
  </linearGradient>
</defs>"""


def cavern():
    """arches and columns receding into the dark"""
    parts = []
    for x, w, top, op in [(30, 150, 150, 0.85), (250, 130, 120, 0.7),
                          (470, 165, 165, 0.8), (720, 140, 128, 0.65),
                          (960, 175, 155, 0.8)]:
        parts.append(
            f'<path d="M{x} {DECK} L{x} {top} Q{x + w / 2} {top - 62} {x + w} {top} '
            f'L{x + w} {DECK} Z" fill="#0b0a11" opacity="{op}"/>'
        )
    for x, w, op in [(96, 30, 0.75), (318, 22, 0.6), (556, 34, 0.7),
                     (792, 24, 0.55), (1052, 32, 0.7)]:
        parts.append(f'<rect x="{x}" y="0" width="{w}" height="{DECK}" '
                     f'fill="#0e0d15" opacity="{op}"/>')
    # a couple of distant torches
    for tx, ty in [(112, 150), (566, 168)]:
        parts.append(
            f'<circle cx="{tx}" cy="{ty}" r="16" fill="url(#staffglow)" opacity="0.5">'
            f'<animate attributeName="opacity" values="0.35;0.6;0.4;0.55;0.35" dur="3.1s" '
            f'repeatCount="indefinite"/></circle>'
            f'<circle cx="{tx}" cy="{ty}" r="2.4" fill="#ffd08a"/>'
        )
    return "".join(parts)


def bridge():
    return f"""
  <path d="M0 {DECK} L{W} {DECK} L{W} {DECK + 26} L0 {DECK + 26} Z" fill="url(#stone)"/>
  <path d="M0 {DECK} L{W} {DECK}" stroke="#5b5a6b" stroke-width="2" opacity="0.9"/>
  <path d="M0 {DECK + 26} L{W} {DECK + 26} L{W} {DECK + 44} Q{W * 0.5} {DECK + 66} 0 {DECK + 44} Z"
        fill="#100e16"/>
  <path d="M0 {DECK + 26} L{W} {DECK + 26}" stroke="#191822" stroke-width="3" opacity="0.9"/>
  {''.join(f'<rect x="{x}" y="{DECK + 2}" width="2" height="22" fill="#0e0d14" opacity="0.55"/>' for x in range(0, W, 46))}
"""


def contact_shadow(box, span, opacity=0.55):
    """A tight smudge right under the feet, not a pool the figure hovers over."""
    w, h, x, y = box
    fx, fw = span
    cx = x + w * fx
    rx = max(7.0, w * fw * 0.62)
    return (
        f'<ellipse cx="{cx:g}" cy="{DECK + 2}" rx="{rx:g}" ry="{max(2.5, rx * 0.09):g}" '
        f'fill="#05040a" opacity="{opacity}"/>'
        f'<ellipse cx="{cx:g}" cy="{DECK + 1.5}" rx="{rx * 0.55:g}" ry="{max(1.8, rx * 0.06):g}" '
        f'fill="#000" opacity="{min(0.9, opacity + 0.2):g}"/>'
    )


def build_svg(g_uri, g_box, b_uri, b_box, g_span, b_span, STAFF_X=0.15):
    g_w, g_h, gx, gy = g_box
    b_w, b_h, bx, by = b_box

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f'<title>The bridge of Khazad-dum</title>'
        f'{DEFS}'
        f'<rect width="{W}" height="{H}" fill="url(#air)"/>'
        f'{cavern()}'
        f'<rect x="0" y="{DECK}" width="{W}" height="{H - DECK}" fill="url(#pit)"/>'
        # the fire behind the balrog
        f'<ellipse cx="{B_CX}" cy="{DECK - 150}" rx="420" ry="250" fill="url(#hellglow)">'
        f'<animate attributeName="opacity" values="0.9;1;0.86;1;0.9" dur="5.2s" '
        f'repeatCount="indefinite"/></ellipse>'
        f'<ellipse cx="{W * 0.5}" cy="{H}" rx="{W * 0.6}" ry="110" fill="url(#hellglow)">'
        f'<animate attributeName="opacity" values="1;0.82;1" dur="7.3s" repeatCount="indefinite"/>'
        f'</ellipse>'
        f'{bridge()}'
        # shadows they cast on the deck
        f'{contact_shadow(g_box, g_span, 0.5)}'
        f'{contact_shadow(b_box, b_span, 0.6)}'
        # the balrog, then gandalf in front of the light
        f'<image href="{b_uri}" x="{bx:g}" y="{by:g}" width="{b_w:g}" height="{b_h:g}" '
        f'image-rendering="pixelated"/>'
        # the staff carries its own light in the art; this only spills it onto the dark
        f'<ellipse cx="{gx + g_w * STAFF_X:g}" cy="{gy + g_h * 0.07:g}" rx="34" ry="32" '
        f'fill="url(#staffglow)" opacity="0.34">'
        f'<animate attributeName="opacity" values="0.26;0.42;0.3;0.4;0.26" dur="4.1s" '
        f'repeatCount="indefinite"/></ellipse>'
        f'<image href="{g_uri}" x="{gx:g}" y="{gy:g}" width="{g_w:g}" height="{g_h:g}" '
        f'image-rendering="pixelated"/>'
        f'{embers()}'
        f'<rect width="{W}" height="{H}" fill="url(#edges)"/>'
        f'<rect width="{W}" height="120" fill="url(#topfade)"/>'
        f'</svg>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gandalf", required=True)
    ap.add_argument("--balrog", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--colors", type=int, default=128)
    ap.add_argument("--flip", action="store_true", help="mirror gandalf")
    ap.add_argument("--sink", type=float, default=4.0,
                    help="units to tuck the figures under the deck line")
    ap.add_argument("--scale", type=float, default=1.5,
                    help="supersample factor for the embedded art")
    args = ap.parse_args()

    k = args.scale
    g_src = trim(Image.open(args.gandalf).convert("RGBA"))
    b_src = trim(Image.open(args.balrog).convert("RGBA"))

    # stand each figure on its foot plane, not on the bottom of its bounding box
    g_box = place(g_src, G_H, G_CX, sink=args.sink)
    b_box = place(b_src, B_H, B_CX, sink=args.sink + 1)

    # render above the layout size so the art stays crisp on high-dpi screens,
    # but not so far above that the banner turns into a megabyte
    g = quantize(fit_height(g_src, g_box[1] * k), args.colors)
    b = quantize(fit_height(b_src, b_box[1] * k), args.colors)

    # the pose is front-on, so the sword is what reads as direction: leave the
    # art alone and his blade points at the balrog
    if args.flip:
        g = g.transpose(Image.FLIP_LEFT_RIGHT)

    g_span, b_span = foot_span(g_src), foot_span(b_src)
    if args.flip:
        g_span = (1 - g_span[0], g_span[1])

    svg = build_svg(data_uri(g), g_box, data_uri(b), b_box, g_span, b_span,
                    STAFF_X=0.85 if args.flip else 0.15)
    path = os.path.join(args.out, "banner.svg")
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB) "
          f"gandalf {g_box[0]:.0f}x{g_box[1]:.0f} at y={g_box[3]:.0f} "
          f"balrog {b_box[0]:.0f}x{b_box[1]:.0f} at y={b_box[3]:.0f} (deck {DECK})")


if __name__ == "__main__":
    main()
