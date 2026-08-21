#!/usr/bin/env python3
"""Build the profile banner: two cutouts standing on a ledge, on nothing else.

Earlier versions put the whole Khazad-dum painting in the README and tried to
dissolve its edges. That never worked. A painting has a background, so however
softly its border is faded there is always a patch of somebody else's darkness
sitting on the page, and a soft rectangle is still a rectangle.

There is no painting here. The only opaque things in the file are the two
figures, the stone under them and the shadows they cast on it; everything else
is transparent and the page shows through. The ledge runs out into nothing at
both ends, so it has no edge either. That also means one file serves every
GitHub theme, because there is no background colour to match.

  python3 scripts/banner.py
"""
import base64
import io
import os
import numpy as np
from PIL import Image, ImageFilter

W, H = 1200, 460
DECK, SURFACE, FACE = 384, 18, 22
LIP = DECK + SURFACE
GROUND = LIP - 2
G_H, B_H = 165, 350
G_CX, B_CX = 300, 800

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART_G = os.path.join(HERE, 'art', 'gandalf.png')
ART_B = os.path.join(HERE, 'art', 'balrog.png')
OUT = os.path.join(HERE, 'banner.svg')


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def trim(img):
    bb = img.getbbox()
    return img.crop(bb) if bb else img


def ground_row(img, thresh=0.01):
    a = np.asarray(img)
    solid = (a[:, :, 3] > 200).sum(axis=1)
    rows = np.nonzero(solid >= max(2, int(thresh * img.width)))[0]
    return int(rows.max()) + 1 if len(rows) else img.height


def foot_span(img, depth=0.03):
    a = np.asarray(img)
    gr = ground_row(img)
    sole = (a[max(0, int(gr - depth * img.height)):gr, :, 3] > 200).any(axis=0)
    cols = np.nonzero(sole)[0]
    if not len(cols):
        return 0.5, 0.3
    return cols.mean() / img.width, (cols.max() - cols.min() + 1) / img.width


def place(img, stand_h, cx):
    s = stand_h / ground_row(img)
    w, h = img.width * s, img.height * s
    fx, _ = foot_span(img)
    return round(w), round(h), round(cx - w * fx), round(GROUND - stand_h)


def noise(h, w, cells, seed):
    r = np.random.default_rng(seed)
    small = (r.random((max(2, cells), max(2, int(cells * w / h)))) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(small).resize((w, h), Image.BICUBIC), np.float32) / 255


def fbm(h, w, seed, octaves=5, cells=4):
    out, amp, tot = np.zeros((h, w), np.float32), 1.0, 0.0
    for i in range(octaves):
        out += amp * noise(h, w, cells * 2 ** i, seed + 101 * i)
        tot += amp
        amp *= 0.55
    return out / tot


def ledge():
    """The stone they stand on, running out of the dark at both ends."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    rgb = np.zeros((H, W, 3), np.float32)
    a = np.zeros((H, W), np.float32)

    grain = 1.0 + (fbm(H, W, 5, cells=5) - 0.5) * 0.45
    course = ((y.astype(int) // 11) % 2) * 14
    joint = (((x.astype(int) + course) % 30) < 1.4) | ((y.astype(int) % 11) < 1)

    top = (y >= DECK) & (y < LIP)
    face = (y >= LIP) & (y < LIP + FACE)
    v = np.where(joint, 0.55, 1.0) * grain
    rgb[top] = (np.clip(v, 0.3, 1.7)[..., None] * np.array([0.17, 0.165, 0.20]))[top]
    warm = np.clip((y - LIP) / FACE, 0, 1)
    fv = np.clip(v, 0.3, 1.7)[..., None] * np.array([0.115, 0.108, 0.135])
    fv = fv * (1.05 - 0.4 * warm)[..., None] + (warm ** 2)[..., None] * np.array([0.30, 0.09, 0.02])
    rgb[face] = fv[face]
    a[top | face] = 1.0
    # the lit near edge
    lip = np.abs(y - DECK) < 1.3
    rgb[lip] = np.array([0.42, 0.43, 0.50])

    # run it out into nothing at both ends and just under the front face
    a *= smooth(x / 190) * smooth((W - 1 - x) / 190)
    a *= smooth((LIP + FACE + 6 - y) / 10)
    return rgb, a


def shadow(box, span, strength):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    w, h, bx, by = box
    fx, fw = span
    cx = bx + w * fx
    rx = max(9.0, w * fw * 0.62)
    d = ((x - cx) / rx) ** 2 + ((y - (GROUND - 1)) / max(3.0, rx * 0.10)) ** 2
    return np.clip(1.0 - d, 0, 1) ** 0.7 * strength


def over(dst_rgb, dst_a, src_rgb, src_a):
    a = src_a[..., None]
    out_a = src_a + dst_a * (1 - src_a)
    num = src_rgb * a + dst_rgb * dst_a[..., None] * (1 - a)
    return np.divide(num, np.maximum(out_a, 1e-6)[..., None]), out_a


def paste(dst_rgb, dst_a, img, box):
    w, h, x, y = box
    s = img.resize((w, h), Image.LANCZOS)
    arr = np.asarray(s, np.float32) / 255
    layer_rgb = np.zeros((H, W, 3), np.float32)
    layer_a = np.zeros((H, W), np.float32)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    sub = arr[y0 - y:y1 - y, x0 - x:x1 - x]
    layer_rgb[y0:y1, x0:x1] = sub[:, :, :3]
    layer_a[y0:y1, x0:x1] = sub[:, :, 3]
    return over(dst_rgb, dst_a, layer_rgb, layer_a)


def build():
    g = trim(Image.open(ART_G).convert('RGBA'))
    b = trim(Image.open(ART_B).convert('RGBA'))
    gb, bb = place(g, G_H, G_CX), place(b, B_H, B_CX)

    rgb, a = ledge()
    for box, src, s in ((bb, b, 0.75), (gb, g, 0.6)):
        sh = shadow(box, foot_span(src), s)
        rgb, a = over(rgb, a, np.zeros((H, W, 3), np.float32), sh)
    rgb, a = paste(rgb, a, b, bb)
    rgb, a = paste(rgb, a, g, gb)

    ys, xs = np.nonzero(a > 0.02)
    t, bm = max(0, ys.min() - 10), min(H, ys.max() + 12)
    l, r = max(0, xs.min() - 10), min(W, xs.max() + 12)
    return rgb[t:bm, l:r], a[t:bm, l:r], gb, bb, (l, t)


rgb, a, gb, bb, off = build()
h, w = a.shape
im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
im.putalpha(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)))
buf = io.BytesIO()
im.save(buf, format='WEBP', quality=92, method=6)
uri = 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()

rng = np.random.default_rng(11)
sparks = "".join(
    f'<circle cx="{rng.uniform(0.18,0.82)*w:.0f}" cy="{h-6}" r="{rng.uniform(0.9,2.3):.1f}" '
    f'fill="{["#ff9a3c","#ffc763","#f0561f"][i%3]}" opacity="0">'
    f'<animate attributeName="opacity" values="0;0.85;0.5;0" keyTimes="0;0.12;0.6;1" '
    f'dur="{(d:=rng.uniform(6,13)):.1f}s" begin="-{rng.uniform(0,13):.1f}s" repeatCount="indefinite"/>'
    f'<animateTransform attributeName="transform" type="translate" '
    f'values="0 0;{rng.uniform(-40,40):.0f} -{rng.uniform(0.3,0.9)*h:.0f}" dur="{d:.1f}s" '
    f'begin="-{rng.uniform(0,13):.1f}s" repeatCount="indefinite"/></circle>' for i in range(38))

bx = bb[2] - off[0] + bb[0] * 0.55
by = bb[3] - off[1] + bb[1] * 0.45
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
       f'<title>The bridge of Khazad-dum</title>'
       f'<defs><radialGradient id="spill" cx="0.5" cy="0.5" r="0.5">'
       f'<stop offset="0" stop-color="#ff8b2a" stop-opacity="0.26"/>'
       f'<stop offset="0.5" stop-color="#e8531a" stop-opacity="0.08"/>'
       f'<stop offset="1" stop-color="#e8531a" stop-opacity="0"/></radialGradient></defs>'
       f'<ellipse cx="{bx:.0f}" cy="{by:.0f}" rx="{w*0.55:.0f}" ry="{h*0.7:.0f}" fill="url(#spill)">'
       f'<animate attributeName="opacity" values="0.75;1;0.8;0.95;0.75" dur="5.6s" '
       f'repeatCount="indefinite"/></ellipse>'
       f'<image href="{uri}" x="0" y="0" width="{w}" height="{h}" image-rendering="pixelated"/>'
       f'{sparks}</svg>')
open(OUT, 'w').write(svg)
print(f'wrote {OUT} ({os.path.getsize(OUT) // 1024} KB) {w}x{h}')
