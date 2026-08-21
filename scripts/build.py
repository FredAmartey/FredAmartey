#!/usr/bin/env python3
"""Build the profile banner: the bridge of Khazad-dum.

Takes the two character pieces (in art/, cutouts with alpha) and stages them
either side of a stone span over a burning chasm. The scene itself is painted
by bg.py as pixel art; the characters ride along as embedded PNGs. Everything
is inlined, so the banner is one self-contained file that survives GitHub's
image proxy.

  python3 scripts/build.py --gandalf art/gandalf.png --balrog art/balrog.png --out .
"""
import argparse
import base64
import io
import os

import numpy as np
from PIL import Image

import bg

# ---------- canvas ----------

W, H = 1200, 520
DECK = 372            # far edge of the bridge, where the stone starts
SURFACE = 22          # depth of the walking surface before the front face
FACE = 26             # height of the front face of the stone
LIP = DECK + SURFACE  # front edge of the stone
GROUND = LIP - 2      # where the lowest foot lands
G_H = 180             # gandalf's height, measured to his feet
B_H = 386             # the balrog towers over him
G_CX = 280            # where each one stands
B_CX = 800


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


def place(img, stand_h, cx):
    """Scale so the lowest foot lands on the stone; return the SVG box.

    These poses are wide stances and the two feet are not level: the Balrog's
    right claw sits 25px below his left. Landing the lowest one on the front lip
    puts the other on the walking surface behind it, and the front face of the
    stone is painted afterwards so anything that overhangs is occluded rather
    than left dangling.
    """
    scale = stand_h / ground_row(img)
    w, h = img.width * scale, img.height * scale
    fx, _ = foot_span(img)
    return w, h, cx - w * fx, GROUND - stand_h


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


def data_uri(img, colors=None):
    if colors:
        img = quantize(img, colors) if img.mode == "RGBA" else \
            img.quantize(colors=colors, method=Image.MAXCOVERAGE)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------- motion ----------

def embers(seed=11, n=30):
    """Sparks off the fire below, carried up past the bridge."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        x = float(rng.uniform(80, W - 80))
        drift = float(rng.uniform(-26, 26))
        dur = float(rng.uniform(5.0, 11.0))
        delay = float(rng.uniform(0, 11.0))
        r = float(rng.uniform(0.9, 2.2))
        rise = float(rng.uniform(170, 380))
        col = ["#ff9a3c", "#ffc763", "#f0561f"][i % 3]
        out.append(
            f'<circle cx="{x:g}" cy="{H - 6:g}" r="{r:g}" fill="{col}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.95;0.7;0" keyTimes="0;0.12;0.6;1" '
            f'dur="{dur:g}s" begin="-{delay:g}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{drift:g} -{rise:g}" dur="{dur:g}s" begin="-{delay:g}s" '
            f'repeatCount="indefinite"/></circle>'
        )
    return "".join(out)


def flicker(cx, cy, rx, ry, fill, values, dur, opacity=1.0):
    """The painted fire is a still frame; this breathes over the top of it."""
    return (f'<ellipse cx="{cx:g}" cy="{cy:g}" rx="{rx:g}" ry="{ry:g}" fill="{fill}" '
            f'opacity="{opacity}" style="mix-blend-mode:screen">'
            f'<animate attributeName="opacity" values="{values}" dur="{dur}s" '
            f'repeatCount="indefinite"/></ellipse>')


DEFS = """<defs>
  <radialGradient id="staffglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffe9b8" stop-opacity="0.85"/>
    <stop offset="0.4" stop-color="#ffb648" stop-opacity="0.35"/>
    <stop offset="1" stop-color="#ff9a2b" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="hellglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ff7a24" stop-opacity="0.5"/>
    <stop offset="0.55" stop-color="#e0431a" stop-opacity="0.2"/>
    <stop offset="1" stop-color="#e0431a" stop-opacity="0"/>
  </radialGradient>
</defs>"""


def contact_shadow(box, span, opacity=0.55):
    """A tight smudge right under the feet, not a pool the figure hovers over."""
    w, h, x, y = box
    fx, fw = span
    cx = x + w * fx
    rx = max(7.0, w * fw * 0.62)
    cy = GROUND - 1
    return (
        f'<ellipse cx="{cx:g}" cy="{cy:g}" rx="{rx:g}" ry="{max(2.5, rx * 0.08):g}" '
        f'fill="#05040a" opacity="{opacity}"/>'
        f'<ellipse cx="{cx:g}" cy="{cy:g}" rx="{rx * 0.5:g}" ry="{max(1.8, rx * 0.05):g}" '
        f'fill="#000" opacity="{min(0.9, opacity + 0.2):g}"/>'
    )


def build_svg(back, front, g_uri, g_box, b_uri, b_box, g_span, b_span, style,
              staff_x=0.15):
    g_w, g_h, gx, gy = g_box
    b_w, b_h, bx, by = b_box
    fire = (flicker(W * 0.66, DECK - 60, 120, 130, "url(#hellglow)",
                    "0.55;0.85;0.5;0.75;0.55", 4.7)
            + flicker(W * 0.5, H - 20, W * 0.42, 70, "url(#hellglow)",
                      "0.7;0.45;0.7", 6.9)) if style != "void" else \
        flicker(W * 0.5, H - 20, W * 0.4, 60, "url(#hellglow)",
                "0.45;0.3;0.45", 7.4)
    torch = "".join(
        flicker(x, y, 26, 26, "url(#staffglow)", "0.3;0.55;0.34;0.5;0.3", 3.1 + i * 0.7)
        for i, (x, y) in enumerate([(254, DECK - 300), (806, DECK - 316)])
    ) if style == "khazad" else ""

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">'
        f'<title>The bridge of Khazad-dum</title>'
        f'{DEFS}'
        f'<image href="{back}" x="0" y="0" width="{W}" height="{H}" '
        f'image-rendering="pixelated"/>'
        f'{torch}{fire}'
        f'{contact_shadow(g_box, g_span, 0.5)}'
        f'{contact_shadow(b_box, b_span, 0.6)}'
        f'<image href="{b_uri}" x="{bx:g}" y="{by:g}" width="{b_w:g}" height="{b_h:g}" '
        f'image-rendering="pixelated"/>'
        # the staff carries its own light in the art; this only spills it onto the dark
        f'<ellipse cx="{gx + g_w * staff_x:g}" cy="{gy + g_h * 0.07:g}" rx="34" ry="32" '
        f'fill="url(#staffglow)" opacity="0.34">'
        f'<animate attributeName="opacity" values="0.26;0.42;0.3;0.4;0.26" dur="4.1s" '
        f'repeatCount="indefinite"/></ellipse>'
        f'<image href="{g_uri}" x="{gx:g}" y="{gy:g}" width="{g_w:g}" height="{g_h:g}" '
        f'image-rendering="pixelated"/>'
        # the lip goes over their feet, so nothing hangs off the edge
        f'<image href="{front}" x="0" y="0" width="{W}" height="{H}" '
        f'image-rendering="pixelated"/>'
        f'{embers()}'
        f'</svg>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gandalf", required=True)
    ap.add_argument("--balrog", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--name", default="banner.svg")
    ap.add_argument("--style", default="khazad",
                    choices=["khazad", "firewall", "void"])
    ap.add_argument("--colors", type=int, default=128)
    ap.add_argument("--flip", action="store_true", help="mirror gandalf")
    ap.add_argument("--scale", type=float, default=1.5,
                    help="supersample factor for the embedded art")
    args = ap.parse_args()

    k = args.scale
    g_src = trim(Image.open(args.gandalf).convert("RGBA"))
    b_src = trim(Image.open(args.balrog).convert("RGBA"))

    # stand each figure on its foot plane, not on the bottom of its bounding box
    g_box = place(g_src, G_H, G_CX)
    b_box = place(b_src, B_H, B_CX)

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

    back, front = bg.render(W, H, DECK, SURFACE, FACE, args.style)

    svg = build_svg(data_uri(back, 200), data_uri(front, 96),
                    data_uri(g), g_box, data_uri(b), b_box, g_span, b_span,
                    args.style, staff_x=0.85 if args.flip else 0.15)
    path = os.path.join(args.out, args.name)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB, {args.style}) "
          f"gandalf {g_box[0]:.0f}x{g_box[1]:.0f} at y={g_box[3]:.0f} "
          f"balrog {b_box[0]:.0f}x{b_box[1]:.0f} at y={b_box[3]:.0f}")


if __name__ == "__main__":
    main()
