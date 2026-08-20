#!/usr/bin/env python3
"""Build the profile banner: Gandalf holds the line against the Balrog.

Characters are composed from Universal LPC Spritesheet layers (see CREDITS.md),
recoloured, cut to their walk cycles, and written into one self-contained
animated SVG. The PNG frames are embedded as base64 so nothing depends on
external files surviving GitHub's image proxy.

  python3 scripts/build.py --src <dir of downloaded lpc layers> --out .
"""
import argparse
import base64
import io
import os

import numpy as np
from PIL import Image

F = 64                 # lpc frame size
ROW_WALK_RIGHT = 11    # ulpc row order: 8 up, 9 left, 10 down, 11 right
NFRAMES = 9

# ---------- layer helpers ----------

def load(src, name):
    return Image.open(os.path.join(src, name)).convert("RGBA")

def tint(img, mul, add=(0, 0, 0), gamma=1.0):
    """recolour a layer while keeping its shading"""
    a = np.asarray(img).astype(np.float64)
    lum = (a[:, :, :3].mean(axis=2, keepdims=True) / 255.0) ** gamma
    a[:, :, :3] = np.clip(lum * np.array(mul) + np.array(add), 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")

def drop_specks(img, min_size=44):
    """Drop small detached blobs from a layer, per animation frame.

    The large wizard hat carries a gold sparkle floating beside the brim. It is
    its own little island of pixels, so removing components below a size floor
    takes it out without touching the hat, which colour matching could not do
    (the sparkle shares tones with the hat's own shading).
    """
    a = np.asarray(img).copy()
    h, w = a.shape[:2]
    for fy in range(0, h, F):
        for fx in range(0, w, F):
            cell = a[fy:fy + F, fx:fx + F]
            solid = cell[:, :, 3] > 0
            seen = np.zeros_like(solid)
            for sy in range(F):
                for sx in range(F):
                    if not solid[sy, sx] or seen[sy, sx]:
                        continue
                    stack_, comp = [(sy, sx)], []
                    seen[sy, sx] = True
                    while stack_:
                        cy, cx = stack_.pop()
                        comp.append((cy, cx))
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                ny, nx = cy + dy, cx + dx
                                if (0 <= ny < F and 0 <= nx < F
                                        and solid[ny, nx] and not seen[ny, nx]):
                                    seen[ny, nx] = True
                                    stack_.append((ny, nx))
                    if len(comp) < min_size:
                        for cy, cx in comp:
                            cell[cy, cx, 3] = 0
    return Image.fromarray(a, "RGBA")

def stack(layers):
    base = Image.new("RGBA", (832, 2944), (0, 0, 0, 0))
    for layer in layers:
        base.alpha_composite(layer)
    return base

GREY = ((120, 124, 136), (52, 54, 64))
GREY_DARK = ((104, 108, 120), (40, 42, 50))


def build_gandalf(src):
    return stack([
        tint(load(src, "cape_behind.png"), *GREY_DARK),
        load(src, "staff_bg.png"),
        load(src, "body_male_light.png"),
        load(src, "head_elderly.png"),
        tint(load(src, "robe_skirt.png"), *GREY),
        tint(load(src, "robe_light.png"), *GREY),
        tint(load(src, "cape_front.png"), *GREY_DARK),
        tint(load(src, "boots_gray.png"), (96, 100, 112), (30, 30, 38)),
        load(src, "beard_white.png"),
        tint(drop_specks(load(src, "hat_large.png")), (112, 116, 128), (44, 46, 56)),
        load(src, "staff_fg.png"),
    ])


def build_balrog(src):
    body = stack([
        load(src, "wings_bat_bg.png"),
        load(src, "body_musc_pure_black.png"),
        load(src, "head_minotaur.png"),
    ])
    # a balrog is a shadow: keep the form almost black, let the fire do the talking
    body = tint(body, (52, 20, 12), (6, 2, 1), gamma=1.3)
    body.alpha_composite(tint(load(src, "horns_bone.png"), (228, 212, 180)))
    return body


# ---------- fire ----------
# drawn at the same pixel scale as the sprites so it sits in the same grid

FIRE = [(143, 32, 5), (211, 58, 8), (255, 139, 31), (255, 199, 74), (255, 240, 190)]

def _put(px, x, y, color, w=F, h=F):
    if 0 <= x < w and 0 <= y < h:
        px[y, x] = (*color, 255)

def tongue(px, cx, base, height, width, lean, hot=0.0):
    """one lick of flame rising from (cx, base)"""
    steps = max(1, int(height))
    for i in range(steps):
        t = i / steps                       # 0 at the base, 1 at the tip
        y = int(base - i)
        half = max(0.0, (width / 2) * (1.0 - t ** 1.35))
        x0 = cx + lean * (t ** 1.6)
        for dx in range(-int(half) - 1, int(half) + 2):
            d = abs(dx) / (half + 0.001)
            if d > 1.0:
                continue
            # bright core, cooler edges, cooler toward the tip
            level = (1.0 - d * 0.55) * (1.0 - t * 0.5) + hot
            idx = int(np.clip(level * (len(FIRE) - 1), 0, len(FIRE) - 1))
            _put(px, int(round(x0 + dx)), y, FIRE[idx])

def mane(frame, n=9):
    """the fire that rides on the balrog's shoulders, behind the body"""
    img = Image.new("RGBA", (F, F), (0, 0, 0, 0))
    px = np.asarray(img).copy()
    phase = 2 * np.pi * frame / n
    # tips have to clear the head and horns, so these run tall
    spec = [(13, 34, 20, 8), (19, 31, 27, 9), (26, 29, 32, 10),
            (33, 28, 30, 10), (40, 30, 24, 9), (45, 34, 17, 7)]
    for k, (cx, base, h, w) in enumerate(spec):
        wob = np.sin(phase + k * 1.7)
        tongue(px, cx, base, h + wob * 2.5, w, lean=wob * 3.0 - 1.0)
    for k, (cx, base, h, w) in enumerate([(22, 32, 22, 5), (30, 30, 26, 5), (37, 31, 20, 5)]):
        wob = np.sin(phase + 0.9 + k * 2.3)
        tongue(px, cx, base, h + wob * 2.0, w, lean=wob * 2.2, hot=0.2)
    return Image.fromarray(px, "RGBA")

def embers(frame, n=9):
    """eyes, lava seams and sparks, drawn over the body"""
    img = Image.new("RGBA", (F, F), (0, 0, 0, 0))
    px = np.asarray(img).copy()
    phase = 2 * np.pi * frame / n
    glow = 0.5 + 0.5 * np.sin(phase * 2)

    eye = FIRE[4] if glow > 0.55 else FIRE[3]
    for x, y in ((33, 23), (37, 22)):
        _put(px, x, y, eye)
        _put(px, x + 1, y, eye)
        _put(px, x, y + 1, FIRE[2])

    # scattered embers in the hide, never joined into a line
    seams = [(25, 37), (27, 41), (24, 45), (30, 39), (31, 44), (28, 48)]
    for i, (x, y) in enumerate(seams):
        if (i + frame) % 3:
            _put(px, x, y, FIRE[2 + ((i + frame) % 2)])

    # fire licking up the near side of the body
    for k, (cx, base, h) in enumerate([(23, 46, 9), (28, 49, 7)]):
        wob = np.sin(phase + k * 2.0)
        tongue(px, cx, base, h + wob * 1.5, 4, lean=wob * 1.5)

    for k in range(3):
        p = ((frame / n) + k / 3.0) % 1.0
        sx = int(18 + k * 9 + np.sin(phase + k) * 2)
        sy = int(24 - p * 18)
        if p < 0.85:
            _put(px, sx, sy, FIRE[3 if k % 2 else 2])
    return Image.fromarray(px, "RGBA")

def with_fire(frames):
    out = []
    n = len(frames)
    for i, fr in enumerate(frames):
        canvas = mane(i, n)
        canvas.alpha_composite(fr)
        canvas.alpha_composite(embers(i, n))
        out.append(canvas)
    return out


# ---------- frame extraction ----------

def walk_frames(sheet, row=ROW_WALK_RIGHT, n=NFRAMES):
    return [sheet.crop((i * F, row * F, (i + 1) * F, (row + 1) * F)) for i in range(n)]

def content_box(frames):
    """one shared bbox across the cycle so frames stay registered"""
    x0, y0, x1, y1 = 1e9, 1e9, -1, -1
    for fr in frames:
        bb = fr.getbbox()
        if not bb:
            continue
        x0, y0 = min(x0, bb[0]), min(y0, bb[1])
        x1, y1 = max(x1, bb[2]), max(y1, bb[3])
    return int(x0), int(y0), int(x1), int(y1)

def crop_all(frames, pad=1):
    x0, y0, x1, y1 = content_box(frames)
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(F, x1 + pad), min(F, y1 + pad)
    return [fr.crop((x0, y0, x1, y1)) for fr in frames], (x1 - x0, y1 - y0)

def data_uri(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------- scene ----------

W, H = 880, 150
DUR = 24.0
WALK = 0.62               # seconds per 9-frame cycle
GS, BS = 1.9, 2.5         # character scales: the balrog towers

T_TURN = 0.42             # gandalf plants himself and turns
T_FLASH = 0.455
T_BREAK = 0.48            # the balrog breaks
T_RESUME = 0.60
T_GONE = 0.88

def kt(*v):
    return ";".join(f"{x:g}" for x in v)

def cycle(uris, w, h, dur):
    """the walk cycle: one frame visible at a time"""
    out = []
    n = len(uris)
    keytimes = kt(*[i / n for i in range(n)], 1)
    for i, uri in enumerate(uris):
        vals = ";".join("1" if k == i else "0" for k in range(n)) + (";1" if i == 0 else ";0")
        out.append(
            f'<image href="{uri}" width="{w:g}" height="{h:g}" image-rendering="pixelated" '
            f'opacity="{1 if i == 0 else 0}">'
            f'<animate attributeName="opacity" values="{vals}" keyTimes="{keytimes}" '
            f'dur="{dur}s" repeatCount="indefinite" calcMode="discrete"/></image>'
        )
    return "".join(out)


def build_svg(g_uris, g_size, b_uris, b_size):
    gw, gh = g_size[0] * GS, g_size[1] * GS
    bw, bh = b_size[0] * BS, b_size[1] * BS
    ground = H - 22
    g_y, b_y = ground - gh, ground - bh

    g_stand = W * 0.60
    b_stand = g_stand - bw + 10
    b_break = b_stand - 30

    # movement
    walk_g = (f'<animateTransform attributeName="transform" type="translate" '
              f'values="{-gw - 30} {g_y};{g_stand} {g_y};{g_stand} {g_y};{W + gw} {g_y}" '
              f'keyTimes="{kt(0, T_TURN, T_RESUME, 1)}" dur="{DUR}s" repeatCount="indefinite" '
              f'calcMode="linear"/>')
    walk_b = (f'<animateTransform attributeName="transform" type="translate" '
              f'values="{-bw - 190} {b_y};{b_stand} {b_y};{b_stand} {b_y};{b_break} {b_y};'
              f'{b_break + 8} {b_y};{-bw - 240} {b_y};{-bw - 240} {b_y}" '
              f'keyTimes="{kt(0, T_TURN, T_FLASH, T_BREAK, T_RESUME, T_GONE, 1)}" dur="{DUR}s" '
              f'repeatCount="indefinite" calcMode="linear"/>')

    # facing. sprites are drawn facing right, so flip about their own width.
    def flip(times, scales, w):
        t = (f'<animateTransform attributeName="transform" type="translate" '
             f'values="{";".join(f"{w if s < 0 else 0:g} 0" for s in scales)}" '
             f'keyTimes="{kt(*times)}" dur="{DUR}s" repeatCount="indefinite" '
             f'calcMode="discrete" additive="sum"/>')
        s = (f'<animateTransform attributeName="transform" type="scale" '
             f'values="{";".join(f"{s:g} 1" for s in scales)}" keyTimes="{kt(*times)}" '
             f'dur="{DUR}s" repeatCount="indefinite" calcMode="discrete" additive="sum"/>')
        return t + s

    flip_g = flip([0, T_TURN, T_RESUME], [1, -1, 1], gw)
    flip_b = flip([0, T_BREAK], [1, -1], bw)

    # walking vs standing: the legs stop while they face off
    hold_walk = (f'<animate attributeName="opacity" values="1;0;1;1" '
                 f'keyTimes="{kt(0, T_TURN, T_RESUME, 1)}" dur="{DUR}s" '
                 f'repeatCount="indefinite" calcMode="discrete"/>')
    hold_stand = (f'<animate attributeName="opacity" values="0;1;0;0" '
                  f'keyTimes="{kt(0, T_TURN, T_RESUME, 1)}" dur="{DUR}s" '
                  f'repeatCount="indefinite" calcMode="discrete"/>')
    b_hold_walk = (f'<animate attributeName="opacity" values="1;0;1;1" '
                   f'keyTimes="{kt(0, T_TURN, T_BREAK, 1)}" dur="{DUR}s" '
                   f'repeatCount="indefinite" calcMode="discrete"/>')
    b_hold_stand = (f'<animate attributeName="opacity" values="0;1;0;0" '
                    f'keyTimes="{kt(0, T_TURN, T_BREAK, 1)}" dur="{DUR}s" '
                    f'repeatCount="indefinite" calcMode="discrete"/>')

    def stand_frame(uri, w, h):
        return (f'<image href="{uri}" width="{w:g}" height="{h:g}" image-rendering="pixelated"/>')

    # the staff head, in scaled sprite space, for the flare
    ox, oy = gw * 0.80, gh * 0.20

    flare = (
        f'<circle cx="{ox:g}" cy="{oy:g}" r="{gw * 0.16:g}" fill="#e0f2fe" opacity="0">'
        f'<animate attributeName="opacity" values="0;0;1;0;0" '
        f'keyTimes="{kt(0, T_FLASH - 0.012, T_FLASH, T_FLASH + 0.045, 1)}" dur="{DUR}s" '
        f'repeatCount="indefinite"/></circle>'
        f'<circle cx="{ox:g}" cy="{oy:g}" r="{gw * 0.07:g}" fill="#bae6fd" opacity="0.5">'
        f'<animate attributeName="opacity" values="0.35;0.65;0.35" dur="1.8s" '
        f'repeatCount="indefinite"/></circle>'
    )
    ring = (
        f'<circle cx="{ox:g}" cy="{oy:g}" r="8" fill="none" stroke="#93c5fd" stroke-width="3" '
        f'opacity="0">'
        f'<animate attributeName="r" values="8;8;150;150" '
        f'keyTimes="{kt(0, T_FLASH, T_FLASH + 0.055, 1)}" dur="{DUR}s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-width" values="4;4;0.6;0.6" '
        f'keyTimes="{kt(0, T_FLASH, T_FLASH + 0.055, 1)}" dur="{DUR}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;0;0.95;0;0" '
        f'keyTimes="{kt(0, T_FLASH - 0.004, T_FLASH, T_FLASH + 0.055, 1)}" dur="{DUR}s" '
        f'repeatCount="indefinite"/></circle>'
    )

    gandalf = (
        f'<g>{walk_g}<g>{flip_g}'
        f'<ellipse cx="{gw/2:g}" cy="{gh - 2:g}" rx="{gw*0.22:g}" ry="3.5" fill="#000" opacity="0.28"/>'
        f'<g opacity="1">{hold_walk}{cycle(g_uris, gw, gh, WALK)}</g>'
        f'<g opacity="0">{hold_stand}{stand_frame(g_uris[0], gw, gh)}</g>'
        f'{flare}{ring}</g></g>'
    )
    balrog = (
        f'<g>{walk_b}<g>{flip_b}'
        f'<ellipse cx="{bw/2:g}" cy="{bh - 3:g}" rx="{bw*0.24:g}" ry="4" fill="#000" opacity="0.3"/>'
        f'<g opacity="1">{b_hold_walk}{cycle(b_uris, bw, bh, WALK * 0.92)}</g>'
        f'<g opacity="0">{b_hold_stand}{stand_frame(b_uris[0], bw, bh)}</g>'
        f'</g></g>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f'<title>Gandalf holds the line against the Balrog</title>'
        f'{balrog}{gandalf}'
        f'</svg>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="directory of downloaded LPC layers")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    g_sheet = build_gandalf(args.src)
    b_sheet = build_balrog(args.src)

    g_frames, g_size = crop_all(walk_frames(g_sheet))
    b_frames, b_size = crop_all(with_fire(walk_frames(b_sheet)))

    g_uris = [data_uri(f) for f in g_frames]
    b_uris = [data_uri(f) for f in b_frames]

    svg = build_svg(g_uris, g_size, b_uris, b_size)
    path = os.path.join(args.out, "banner.svg")
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB) "
          f"gandalf {g_size} balrog {b_size}")


if __name__ == "__main__":
    main()
