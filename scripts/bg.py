#!/usr/bin/env python3
"""Paint the banner background as pixel art.

Hand-drawn SVG shapes read cheap beside the character art: flat gradients and
a couple of black blobs for arches. So the scene is painted as a raster at half
the banner's size and scaled back up with nearest-neighbour. The blocky result
sits in the same register as the sprites, and noise gives stone, smoke and fire
a texture that gradients cannot.

Two plates come out of here. `back` is everything behind the figures, down to
and including the surface they stand on. `front` is the front face of the
bridge, painted after them, so a foot that overhangs the lip is occluded rather
than left dangling.
"""
import numpy as np
from PIL import Image

PIX = 2  # banner pixels per painted pixel


# ---------- noise ----------

def noise(h, w, cells, seed, aspect=1.0):
    r = np.random.default_rng(seed)
    ch = max(2, int(cells))
    cw = max(2, int(cells * w / h * aspect))
    small = (r.random((ch, cw)) * 255).astype(np.uint8)
    up = Image.fromarray(small).resize((w, h), Image.BICUBIC)
    return np.asarray(up, dtype=np.float32) / 255.0


def fbm(h, w, seed, octaves=5, cells=3, gain=0.55, aspect=1.0):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for i in range(octaves):
        out += amp * noise(h, w, cells * 2 ** i, seed + 101 * i, aspect)
        tot += amp
        amp *= gain
    return out / tot


# ---------- compositing ----------

def ramp(t, stops):
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.array([c for _, c in stops], np.float32)
    out = np.empty(t.shape + (3,), np.float32)
    for i in range(3):
        out[..., i] = np.interp(t, pos, cols[:, i])
    return out


def over(dst, src, a):
    a = np.clip(a, 0, 1)[..., None]
    return dst * (1 - a) + np.asarray(src, np.float32) * a


def add(dst, src, a):
    return np.clip(dst + np.asarray(src, np.float32) * np.clip(a, 0, 1)[..., None], 0, 1)


# ---------- stone ----------

def stone(h, w, seed, base, block=(24, 13), grain=0.38):
    """Coursed masonry: grain, joints, and a little variation per block."""
    v = 1.0 + (fbm(h, w, seed, octaves=5, cells=4) - 0.5) * grain
    yy, xx = np.mgrid[0:h, 0:w]
    bh, bw = block
    course = yy // bh
    off = (course % 2) * (bw // 2)
    col = (xx + off) // bw
    joint = ((yy % bh) < 1) | (((xx + off) % bw) < 1)
    v = np.where(joint, v * 0.55, v)
    jit = np.random.default_rng(seed + 7).normal(0, 0.07, (course.max() + 2, col.max() + 2))
    v = v * (1 + jit[course, col])
    return np.clip(v, 0.25, 1.9)[..., None] * np.asarray(base, np.float32)


def arch(h, w, cx, hw, spring, base, apex):
    """An opening: straight jambs up to the springline, an arched head above.

    A rise taller than the half-width gives the pointed dwarvish arch (two arcs
    meeting at the apex). A shallower rise falls back to one segmental arc,
    because forcing the two-arc form on a wide low opening collapses it into a
    rectangle wearing a spike.
    """
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    a = max(2.0, spring - apex)
    if a >= hw:
        d = (a * a - hw * hw) / (2 * hw)
        r = hw + d
        head = (((x - (cx - d)) ** 2 + (y - spring) ** 2 <= r * r) &
                ((x - (cx + d)) ** 2 + (y - spring) ** 2 <= r * r) &
                (y <= spring))
    else:
        r = (hw * hw + a * a) / (2 * a)
        cy = spring - a + r
        head = ((x - cx) ** 2 + (y - cy) ** 2 <= r * r) & (y <= spring)
    body = (np.abs(x - cx) <= hw) & (y > spring) & (y <= base)
    return head | body


def outline(mask, r=2):
    m = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            m |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return m & ~mask


# ---------- the scene ----------

class Geo:
    """Banner geometry, in painted pixels."""

    def __init__(self, w, h, deck, surface, face):
        self.W, self.H = w // PIX, h // PIX
        self.deck = deck // PIX
        self.surface = surface // PIX
        self.lip = self.deck + self.surface
        self.face = face // PIX


LAVA = [(0.00, (0.05, 0.020, 0.030)),
        (0.34, (0.34, 0.055, 0.020)),
        (0.60, (0.84, 0.230, 0.030)),
        (0.83, (1.00, 0.540, 0.090)),
        (1.00, (1.00, 0.870, 0.520))]

FIRE = [(0.00, (0.20, 0.030, 0.010)),
        (0.35, (0.85, 0.180, 0.020)),
        (0.65, (1.00, 0.480, 0.060)),
        (0.88, (1.00, 0.700, 0.190)),
        (1.00, (1.00, 0.880, 0.520))]


def arcade(img, g, y, x):
    """The hall behind them: a gallery of arches, piers, and firelit stone."""
    H, W = g.H, g.W
    wall_h = g.deck

    # the far dark the arches open onto
    img = over(img, (0.030, 0.026, 0.040), (y < wall_h).astype(np.float32))

    # a smaller arcade glimpsed through the openings
    far = np.zeros((H, W), bool)
    for cx in range(40, W + 60, 96):
        far |= arch(H, W, cx, 26, wall_h - 96, wall_h, wall_h - 150)
    img = over(img, (0.075, 0.060, 0.062), far * 0.55)
    img = over(img, (0.018, 0.014, 0.024), (~far & (y < wall_h)) * 0.35)

    # the near wall, lit warm from the chasm and cool from nothing at all
    face = stone(H, W, 3, (0.088, 0.080, 0.105), block=(22, 12))
    lit = np.clip(y / max(1.0, wall_h), 0, 1) ** 2.6
    face = np.clip(face * (1 + lit[..., None] * np.array([2.1, 0.72, 0.20])), 0, 1)

    holes = np.zeros((H, W), bool)
    for cx in (58, 196, 334, 472, 610):
        holes |= arch(H, W, cx, 46, wall_h - 116, wall_h + 4, wall_h - 196)
    solid = (y < wall_h) & ~holes
    img = np.where(solid[..., None], face, img)

    # the ring of voussoirs around each opening, and a shadow inside the jamb
    band = outline(holes, 3) & (y < wall_h)
    img = np.where(band[..., None], np.clip(face * 1.55 + 0.02, 0, 1), img)
    img = over(img, (0.0, 0.0, 0.0), (outline(~holes, 2) & holes) * 0.55)

    # engaged columns on the piers, catching a highlight down one side
    for cx in (127, 265, 403, 541):
        shaft = (np.abs(x - cx) <= 9) & (y > wall_h - 240) & (y < wall_h)
        img = np.where(shaft[..., None], np.clip(face * 1.35, 0, 1), img)
        edge = (np.abs(x - (cx - 8)) <= 1.2) & shaft
        img = np.where(edge[..., None], np.clip(face * 2.3 + 0.03, 0, 1), img)
        cap = (np.abs(x - cx) <= 13) & (np.abs(y - (wall_h - 236)) <= 4)
        img = np.where(cap[..., None], np.clip(face * 1.7, 0, 1), img)
    return img


def torches(img, g, y, x, spots):
    for tx, ty in spots:
        d = np.sqrt((x - tx) ** 2 + ((y - ty) * 1.15) ** 2)
        img = add(img, (0.95, 0.52, 0.16), np.exp(-(d / 15) ** 2) * 0.45)
        img = add(img, (1.0, 0.88, 0.62), np.exp(-(d / 2.0) ** 2) * 0.9)
    return img


def firecolumn(img, g, y, x, cx, width, height, seed, strength=1.0):
    """A body of flame standing out of the chasm."""
    H, W = g.H, g.W
    f = fbm(H, W, seed, octaves=6, cells=4, aspect=3.0)
    warp = (fbm(H, W, seed + 17, octaves=3, cells=2) - 0.5) * 22
    up = np.clip(1.0 - (g.lip + 6 - y) / height, 0, 1)
    across = np.exp(-((x + warp - cx) / width) ** 2)
    v = np.clip((f * 1.30 + up * 0.75 - 1.02) * 3.4, 0, 1) * across * up ** 0.7
    img = add(img, (0.42, 0.11, 0.02), np.clip(v * 1.4, 0, 1) * 0.32 * strength)
    return over(img, ramp(np.clip(v * 1.35, 0, 1), FIRE), np.clip(v * 1.7, 0, 1) * strength)


def smoke(img, g, y, x, cx, width, seed, tone=(0.10, 0.075, 0.085), amount=0.62):
    H, W = g.H, g.W
    p = fbm(H, W, seed, octaves=6, cells=2)
    band = np.exp(-((x - cx) / width) ** 2)
    rise = np.clip((g.deck - y) / max(1.0, g.deck), 0, 1)
    a = np.clip((p - 0.44) * 2.4, 0, 1) * band * (0.22 + 0.78 * rise) * amount
    img = over(img, tone, a)
    # the underside of the cloud catches the fire below it
    low = np.clip((y - g.deck * 0.35) / (g.deck * 0.65), 0, 1)
    return add(img, (0.85, 0.34, 0.08), a * low * 0.30)


def chasm(img, g, y, x, bright=1.0):
    """The rift, and the arch that carries the span across it.

    The deck is flat on top but the stone under it is not: it springs from the
    abutments at either side and thins to almost nothing at the crown. Fire sits
    a long way down inside it, dim enough to read as distance.
    """
    H, W = g.H, g.W
    below = y > g.lip
    span = g.lip + g.face
    depth = np.clip((y - span) / max(1.0, H - span), 0, 1)

    turb = fbm(H, W, 21, octaves=6, cells=6, aspect=1.8)
    crust = fbm(H, W, 39, octaves=4, cells=3)
    deep = np.clip((depth * 1.15 - 0.52 + (turb - 0.5) * 1.55
                    - (crust - 0.5) * 0.40) * 1.35, 0, 1) * 0.74
    img = np.where(below[..., None], ramp(deep * bright, LAVA), img)

    crown = span + 4
    arc = crown + (H - crown) * np.clip((2 * x / W - 1) ** 2 * 2.0, 0, 3)
    haunch = below & (y < arc)
    tex = stone(H, W, 9, (0.052, 0.047, 0.062), block=(15, 19), grain=0.55)
    near = np.clip(1 - (arc - y) / 20, 0, 1)
    tex = np.clip(tex * (1 + (near ** 2)[..., None] * np.array([2.6, 0.80, 0.18])), 0, 1)
    img = np.where(haunch[..., None], tex, img)
    img = add(img, (1.0, 0.46, 0.12), (below & (np.abs(y - arc) < 1.6)) * 0.50 * bright)

    vein = np.clip((fbm(H, W, 63, octaves=5, cells=5) - 0.66) * 7.0, 0, 1)
    img = add(img, (1.0, 0.30, 0.05), vein * haunch * 0.55 * bright)
    return img


def deck(img, g, y, x):
    """The walking surface, seen almost edge-on."""
    H, W = g.H, g.W
    top = (y >= g.deck) & (y < g.lip)
    tex = stone(H, W, 15, (0.150, 0.145, 0.180), block=(9, 29), grain=0.30)
    depth = np.clip((y - g.deck) / max(1.0, g.surface), 0, 1)
    tex = np.clip(tex * (0.72 + 0.55 * depth)[..., None], 0, 1)
    img = np.where(top[..., None], tex, img)
    img = add(img, (0.55, 0.60, 0.72), (np.abs(y - g.deck) < 1) * 0.42)
    return img


def paint_back(g, style):
    H, W = g.H, g.W
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32) + np.array([0.024, 0.021, 0.036])

    # the whole hall sits in the updraught from the chasm
    up = np.clip((y - 24) / max(1.0, g.lip - 24), 0, 1) ** 2.3
    haze = fbm(H, W, 7, octaves=4, cells=2) * 0.55 + 0.45
    img = over(img, (0.42, 0.13, 0.03), up * 0.30 * haze)

    if style == "khazad":
        img = arcade(img, g, y, x)
        img = torches(img, g, y, x, [(127, g.deck - 150), (403, g.deck - 158)])
        img = firecolumn(img, g, y, x, 0.66 * W, 0.11 * W, 0.72 * g.deck, 44)
        img = smoke(img, g, y, x, 0.62 * W, 0.30 * W, 33)
        img = smoke(img, g, y, x, 0.20 * W, 0.22 * W, 55, amount=0.35)
    elif style == "firewall":
        img = firecolumn(img, g, y, x, 0.70 * W, 0.26 * W, 1.05 * g.deck, 44)
        img = firecolumn(img, g, y, x, 0.46 * W, 0.13 * W, 0.70 * g.deck, 71, 0.7)
        img = smoke(img, g, y, x, 0.60 * W, 0.42 * W, 33, amount=0.85)
        img = smoke(img, g, y, x, 0.18 * W, 0.26 * W, 55, amount=0.40)
    elif style == "void":
        img = smoke(img, g, y, x, 0.62 * W, 0.34 * W, 33,
                    tone=(0.055, 0.048, 0.062), amount=0.55)

    img = chasm(img, g, y, x, bright=0.72 if style == "void" else 1.0)
    img = deck(img, g, y, x)

    # the dark closes in at the edges and along the top
    img = over(img, (0.020, 0.018, 0.030),
               np.clip((np.abs(x - W / 2) / (W / 2) - 0.66) / 0.34, 0, 1) ** 1.6 * 0.95)
    img = over(img, (0.020, 0.018, 0.030), np.clip((44 - y) / 44, 0, 1) ** 1.3 * 0.92)
    return img


def paint_front(g):
    """The front face of the stone, and nothing else."""
    H, W = g.H, g.W
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    band = (y >= g.lip) & (y < g.lip + g.face)
    tex = stone(H, W, 27, (0.105, 0.100, 0.128), block=(13, 29), grain=0.42)
    warm = np.clip((y - g.lip) / max(1.0, g.face), 0, 1)
    tex = np.clip(tex * (1.05 - 0.45 * warm)[..., None]
                  * (1 + (warm ** 2)[..., None] * np.array([1.5, 0.45, 0.10])), 0, 1)
    img = np.where(band[..., None], tex, 0.0)
    img = add(img, (0.62, 0.64, 0.74), ((np.abs(y - g.lip) < 1.4) & band) * 0.70)
    a = band.astype(np.float32)
    return img, a


def render(w, h, deck_y, surface, face, style):
    g = Geo(w, h, deck_y, surface, face)
    back = Image.fromarray((np.clip(paint_back(g, style), 0, 1) * 255).astype(np.uint8))
    fimg, fa = paint_front(g)
    rgba = np.dstack([(np.clip(fimg, 0, 1) * 255).astype(np.uint8),
                      (fa * 255).astype(np.uint8)])
    return back, Image.fromarray(rgba, "RGBA")
