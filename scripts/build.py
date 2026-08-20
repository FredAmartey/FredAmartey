#!/usr/bin/env python3
"""Build the profile banner: the standoff on the bridge of Khazad-dum.

Two CC0/CC-BY pixel-art characters (see CREDITS.md) are recoloured — the wizard
to grey, the demon down into shadow so only its fire reads — and staged either
side of a stone span over a chasm. Nothing walks: the only motion is the two
idle cycles, the firelight, and the embers.

  python3 scripts/build.py --src <dir with the unpacked asset packs> --out .
"""
import argparse
import base64
import io
import os

import numpy as np
from PIL import Image

# ---------- colour ----------

def to_hsv(a):
    rgb = a[:, :, :3].astype(np.float64) / 255.0
    mx = rgb.max(axis=2)
    d = mx - rgb.min(axis=2)
    h = np.zeros_like(mx)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    m = d > 1e-6
    i = m & (mx == r); h[i] = ((g - b)[i] / d[i]) % 6
    i = m & (mx == g); h[i] = ((b - r)[i] / d[i]) + 2
    i = m & (mx == b); h[i] = ((r - g)[i] / d[i]) + 4
    h *= 60.0
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0)
    return h, s, mx


def from_hsv(h, s, v, alpha):
    c = v * s
    x = c * (1 - np.abs((h / 60.0) % 2 - 1))
    m = v - c
    z = np.zeros_like(h)
    cond = [(h < 60), (h < 120), (h < 180), (h < 240), (h < 300), (h >= 300)]
    r = np.select(cond, [c, x, z, z, x, c])
    g = np.select(cond, [x, c, c, x, z, z])
    b = np.select(cond, [z, z, x, c, c, x])
    out = np.zeros(h.shape + (4,), dtype=np.uint8)
    out[:, :, 0] = np.clip((r + m) * 255, 0, 255)
    out[:, :, 1] = np.clip((g + m) * 255, 0, 255)
    out[:, :, 2] = np.clip((b + m) * 255, 0, 255)
    out[:, :, 3] = alpha
    return out


def grey_wizard(img):
    """purple robe and gold trim -> Gandalf's grey, leaving skin and beard"""
    a = np.asarray(img).astype(np.uint8)
    h, s, v = to_hsv(a)
    robe = (s > 0.15) & (((h >= 245) & (h <= 340)) | ((h >= 200) & (h < 245) & (s > 0.25)))
    trim = (s > 0.32) & (h >= 38) & (h <= 65)
    sel = robe | trim
    h2, s2, v2 = h.copy(), s.copy(), v.copy()
    s2[sel] = 0.06
    h2[sel] = 225.0
    v2[sel] = np.clip(v[sel] * 0.60 + 0.05, 0, 1)
    return Image.fromarray(from_hsv(h2, s2, v2, a[:, :, 3]), "RGBA")


def shadow_demon(img):
    """drop the body into shadow and leave the flame and eyes burning"""
    a = np.asarray(img).astype(np.uint8)
    h, s, v = to_hsv(a)
    fire = ((h >= 35) & (h <= 70) & (v > 0.62)) | ((h <= 30) & (v > 0.85) & (s > 0.6))
    body = ~fire
    h2, s2, v2 = h.copy(), s.copy(), v.copy()
    v2[body] = v[body] * 0.46
    s2[body] = np.clip(s[body] * 0.82, 0, 1)
    return Image.fromarray(from_hsv(h2, s2, v2, a[:, :, 3]), "RGBA")


# ---------- frames ----------

def wizard_idle(src):
    sheet = Image.open(os.path.join(src, "wizard", "Wizard Pack", "Idle.png")).convert("RGBA")
    fw = 231
    return [sheet.crop((i * fw, 0, (i + 1) * fw, sheet.height)) for i in range(sheet.width // fw)]


def demon_idle(src):
    base = os.path.join(src, "demon", "boss_demon_slime_FREE_v1.0",
                        "individual sprites", "01_demon_idle")
    names = sorted(os.listdir(base),
                   key=lambda n: int("".join(c for c in n if c.isdigit()) or 0))
    return [Image.open(os.path.join(base, n)).convert("RGBA")
            for n in names if n.endswith(".png")]


def shared_crop(frames, pad=1):
    """one bbox across a cycle so the sprite does not jitter"""
    x0 = y0 = 10 ** 6
    x1 = y1 = -1
    for f in frames:
        bb = f.getbbox()
        if not bb:
            continue
        x0, y0 = min(x0, bb[0]), min(y0, bb[1])
        x1, y1 = max(x1, bb[2]), max(y1, bb[3])
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1 = min(frames[0].width, x1 + pad)
    y1 = min(frames[0].height, y1 + pad)
    return [f.crop((x0, y0, x1, y1)) for f in frames], (x1 - x0, y1 - y0)


def mirror(frames):
    return [f.transpose(Image.FLIP_LEFT_RIGHT) for f in frames]


def data_uri(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------- scene ----------

W, H = 900, 300
GROUND = 258          # top of the bridge deck
G_SCALE = 1.75        # gandalf
B_SCALE = 2.35        # the balrog towers over him


def cycle(uris, w, h, dur, x, y):
    """an idle loop: one frame visible at a time"""
    n = len(uris)
    keytimes = ";".join(f"{i / n:g}" for i in range(n)) + ";1"
    out = []
    for i, uri in enumerate(uris):
        vals = ";".join("1" if k == i else "0" for k in range(n)) + (";1" if i == 0 else ";0")
        out.append(
            f'<image href="{uri}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
            f'image-rendering="pixelated" opacity="{1 if i == 0 else 0}">'
            f'<animate attributeName="opacity" values="{vals}" keyTimes="{keytimes}" '
            f'dur="{dur}s" repeatCount="indefinite" calcMode="discrete"/></image>'
        )
    return "".join(out)


def embers(seed=7):
    """sparks drifting up out of the chasm"""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(26):
        x = float(rng.uniform(40, W - 40))
        drift = float(rng.uniform(-14, 14))
        dur = float(rng.uniform(4.5, 9.0))
        delay = float(rng.uniform(0, 9.0))
        r = float(rng.uniform(0.8, 1.8))
        rise = float(rng.uniform(120, 210))
        col = ["#ff9a3c", "#ffbf5e", "#f2662a"][i % 3]
        out.append(
            f'<circle cx="{x:g}" cy="{H - 6:g}" r="{r:g}" fill="{col}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.9;0.7;0" keyTimes="0;0.15;0.6;1" '
            f'dur="{dur:g}s" begin="-{delay:g}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{drift:g} -{rise:g}" dur="{dur:g}s" begin="-{delay:g}s" '
            f'repeatCount="indefinite"/></circle>'
        )
    return "".join(out)


def build_svg(g_uris, g_size, b_uris, b_size):
    gw, gh = g_size[0] * G_SCALE, g_size[1] * G_SCALE
    bw, bh = b_size[0] * B_SCALE, b_size[1] * B_SCALE
    gx, gy = W * 0.30 - gw / 2, GROUND - gh + 2
    bx, by = W * 0.68 - bw / 2, GROUND - bh + 4

    defs = f"""<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#07070d"/>
    <stop offset="0.55" stop-color="#0d0a12"/>
    <stop offset="1" stop-color="#1a0e10"/>
  </linearGradient>
  <linearGradient id="chasm" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff7a1e" stop-opacity="0"/>
    <stop offset="0.6" stop-color="#ff6a14" stop-opacity="0.22"/>
    <stop offset="1" stop-color="#ffa63a" stop-opacity="0.40"/>
  </linearGradient>
  <radialGradient id="firelight" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ff8a2b" stop-opacity="0.42"/>
    <stop offset="1" stop-color="#ff8a2b" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="staffglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#cbeaff" stop-opacity="0.75"/>
    <stop offset="1" stop-color="#7fc4ef" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="deck" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#23242e"/>
    <stop offset="0.62" stop-color="#2b2630"/>
    <stop offset="1" stop-color="#3a2a26"/>
  </linearGradient>
  <linearGradient id="vign" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#07070d" stop-opacity="0.85"/>
    <stop offset="0.16" stop-color="#07070d" stop-opacity="0"/>
    <stop offset="0.84" stop-color="#07070d" stop-opacity="0"/>
    <stop offset="1" stop-color="#07070d" stop-opacity="0.85"/>
  </linearGradient>
</defs>"""

    pillars = "".join(
        f'<rect x="{x}" y="0" width="{w}" height="{GROUND - 6}" fill="#101018" opacity="{op}"/>'
        for x, w, op in [(70, 26, 0.55), (196, 18, 0.4), (410, 22, 0.45),
                         (600, 16, 0.35), (790, 28, 0.5)]
    )
    # a suggestion of arches behind the pillars
    arches = "".join(
        f'<path d="M{x} {GROUND - 6} L{x} {y} Q{x + w / 2} {y - 34} {x + w} {y} L{x + w} {GROUND - 6} Z" '
        f'fill="#0c0c14" opacity="0.75"/>'
        for x, w, y in [(40, 120, 120), (320, 150, 96), (620, 140, 110)]
    )

    scene = f"""
  <rect width="{W}" height="{H}" fill="url(#sky)"/>
  {arches}{pillars}
  <rect x="0" y="{GROUND}" width="{W}" height="{H - GROUND}" fill="url(#chasm)"/>
  <ellipse cx="{bx + bw * 0.5:g}" cy="{GROUND - 40:g}" rx="300" ry="150" fill="url(#firelight)">
    <animate attributeName="opacity" values="0.85;1;0.9;1;0.85" dur="4.3s" repeatCount="indefinite"/>
  </ellipse>
  <ellipse cx="{W * 0.5:g}" cy="{H:g}" rx="{W * 0.55:g}" ry="70" fill="url(#firelight)">
    <animate attributeName="opacity" values="1;0.8;1" dur="6.1s" repeatCount="indefinite"/>
  </ellipse>
"""

    bridge = f"""
  <path d="M0 {GROUND + 14} L{W} {GROUND + 14} L{W} {GROUND} Q{W / 2} {GROUND - 10} 0 {GROUND} Z"
        fill="url(#deck)"/>
  <path d="M0 {GROUND} Q{W / 2} {GROUND - 10} {W} {GROUND}" fill="none"
        stroke="#4b4a58" stroke-width="1.6" opacity="0.85"/>
  <path d="M0 {GROUND + 14} Q{W / 2} {GROUND + 30} {W} {GROUND + 14} L{W} {GROUND + 40}
           Q{W / 2} {GROUND + 20} 0 {GROUND + 40} Z" fill="#0b0a11" opacity="0.9"/>
"""

    staff_x = gx + gw * (0.10 if True else 0)
    glow = (
        f'<ellipse cx="{gx + gw * 0.09:g}" cy="{gy + gh * 0.10:g}" rx="46" ry="42" '
        f'fill="url(#staffglow)" opacity="0.5">'
        f'<animate attributeName="opacity" values="0.4;0.62;0.4" dur="3.7s" '
        f'repeatCount="indefinite"/></ellipse>'
    )

    shadows = (
        f'<ellipse cx="{gx + gw / 2:g}" cy="{GROUND + 3:g}" rx="{gw * 0.26:g}" ry="4" '
        f'fill="#000" opacity="0.45"/>'
        f'<ellipse cx="{bx + bw / 2:g}" cy="{GROUND + 5:g}" rx="{bw * 0.28:g}" ry="6" '
        f'fill="#000" opacity="0.5"/>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f'<title>The bridge of Khazad-dum: a grey wizard stands against a demon of shadow and flame</title>'
        f'{defs}{scene}{bridge}{shadows}{glow}'
        f'{cycle(b_uris, bw, bh, 0.95, bx, by)}'
        f'{cycle(g_uris, gw, gh, 1.15, gx, gy)}'
        f'{embers()}'
        f'<rect width="{W}" height="{H}" fill="url(#vign)"/>'
        f'</svg>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    g_frames, g_size = shared_crop([grey_wizard(f) for f in wizard_idle(args.src)])
    # the demon ships facing right; turn it to face the wizard
    d_frames, d_size = shared_crop([shadow_demon(f) for f in demon_idle(args.src)])
    d_frames = mirror(d_frames)

    svg = build_svg([data_uri(f) for f in g_frames], g_size,
                    [data_uri(f) for f in d_frames], d_size)
    path = os.path.join(args.out, "banner.svg")
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB) "
          f"gandalf {g_size} balrog {d_size}")


if __name__ == "__main__":
    main()
