#!/usr/bin/env python3
"""A tiny pixel-art engine: primitives -> material grid -> shaded sprite.

Shading is volumetric: an inner distance transform gives depth, a blurred
alpha gradient gives a surface normal, and the two drive a ramp lookup per
material. Then a dark silhouette outline and a warm rim light on the fire
side. That combination is what makes hand-drawn RPG sprites read as solid
rather than flat.
"""
import numpy as np

# ---------- materials: each is a 5-step ramp, dark -> light ----------

RAMPS = {
    "hat":    ["#20242b", "#333a45", "#4a5361", "#626c7c", "#7d8797"],
    "robe":   ["#2b313b", "#414a58", "#5b6675", "#78808f", "#949cab"],
    "robe2":  ["#232830", "#363d49", "#4c5563", "#656e7d", "#828b9a"],
    "beard":  ["#8e97a4", "#b3bcc8", "#d3dae3", "#e9eef4", "#ffffff"],
    "skin":   ["#8d5a3a", "#b57a4f", "#d79b6c", "#eebb90", "#f8d8b4"],
    "wood":   ["#31221a", "#4a3425", "#664733", "#7f5b42", "#9a7354"],
    "orb":    ["#1d6c95", "#3ea0c9", "#79cdec", "#b6e8fb", "#ffffff"],
    "steel":  ["#3d4a5c", "#5d7089", "#8399b3", "#b2c4d8", "#e6eef8"],
    "gold":   ["#6b4a13", "#9c7420", "#c99c33", "#e7bf5c", "#fbe29a"],

    "bskin":  ["#0d0503", "#1a0c07", "#2a150d", "#3b2114", "#52321f"],
    "bskin2": ["#090402", "#150903", "#221008", "#301810", "#412418"],
    "horn":   ["#544530", "#7c6845", "#a38d63", "#c4b189", "#e3d6b6"],
    "lava":   ["#7c1d05", "#b83a08", "#e8620f", "#ff9024", "#ffcf5e"],
    "fire":   ["#8f1f07", "#cf3d0a", "#f36a12", "#ff9e2c", "#ffe07a"],
    "fire2":  ["#b32b08", "#e8560d", "#ff8419", "#ffb843", "#fff0a6"],
    "eye":    ["#a35d00", "#d68a00", "#ffbe1a", "#ffe066", "#fffbe0"],
    "wing":   ["#0d0605", "#190c08", "#26130c", "#331a10", "#412114"],
    "tooth":  ["#8c7e6a", "#b3a693", "#d6cbba", "#eee6da", "#ffffff"],
    "hot":    ["#ffd27a", "#ffe6a8", "#fff3d0", "#fffaf0", "#ffffff"],
}
MATS = ["_"] + list(RAMPS)
MID = {m: i for i, m in enumerate(MATS)}

def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

RAMP_RGB = {m: [hex2rgb(c) for c in RAMPS[m]] for m in RAMPS}
OUTLINE = (14, 12, 18)

# materials that emit light: no shading darkening, no outline darkening
EMISSIVE = {"fire", "fire2", "lava", "orb", "eye", "hot"}

# per-material exposure. negative keeps a material in its dark range no matter
# how thick the form is, which is what stops a black demon turning brown.
BIAS = {
    "bskin": -0.10, "bskin2": -0.18, "wing": -0.14,
    "hat": -0.06, "robe2": -0.05,
    "beard": 0.16, "tooth": 0.12, "horn": 0.06,
}


class Sprite:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.mat = np.zeros((h, w), dtype=np.int16)
        ys, xs = np.mgrid[0:h, 0:w]
        self.px = xs + 0.5
        self.py = ys + 0.5

    # ---- primitives ----
    def ellipse(self, cx, cy, rx, ry, mat, rot=0.0):
        dx, dy = self.px - cx, self.py - cy
        if rot:
            c, s = np.cos(-rot), np.sin(-rot)
            dx, dy = dx * c - dy * s, dx * s + dy * c
        self._put((dx / rx) ** 2 + (dy / ry) ** 2 <= 1.0, mat)

    def rect(self, x0, y0, x1, y1, mat, r=0.0):
        inside = (self.px >= x0) & (self.px <= x1) & (self.py >= y0) & (self.py <= y1)
        if r > 0:
            cx = np.clip(self.px, x0 + r, x1 - r)
            cy = np.clip(self.py, y0 + r, y1 - r)
            inside &= ((self.px - cx) ** 2 + (self.py - cy) ** 2) <= r * r + 0.25
        self._put(inside, mat)

    def poly(self, pts, mat):
        n = len(pts)
        inside = np.zeros_like(self.px, dtype=bool)
        j = n - 1
        for i in range(n):
            xi, yi = pts[i]
            xj, yj = pts[j]
            cond = ((yi > self.py) != (yj > self.py))
            with np.errstate(divide="ignore", invalid="ignore"):
                xint = (xj - xi) * (self.py - yi) / (yj - yi + 1e-12) + xi
            inside ^= cond & (self.px < xint)
            j = i
        self._put(inside, mat)

    def line(self, p0, p1, width, mat):
        x0, y0 = p0
        x1, y1 = p1
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-9
        t = np.clip(((self.px - x0) * vx + (self.py - y0) * vy) / L2, 0, 1)
        dx = self.px - (x0 + t * vx)
        dy = self.py - (y0 + t * vy)
        self._put(dx * dx + dy * dy <= (width / 2) ** 2 + 0.1, mat)

    def curve(self, p0, p1, p2, width, mat, taper=None, n=40):
        for i in range(n):
            t = i / (n - 1)
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
            w = width if taper is None else width + (taper - width) * t
            self.ellipse(x, y, w / 2, w / 2, mat)

    def blob(self, pts, mat):
        """closed catmull-rom-ish blob through points, filled"""
        dense = []
        n = len(pts)
        for i in range(n):
            p0 = pts[(i - 1) % n]
            p1 = pts[i]
            p2 = pts[(i + 1) % n]
            p3 = pts[(i + 2) % n]
            for k in range(10):
                t = k / 10
                t2, t3 = t * t, t * t * t
                x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                           (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                           (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
                y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                           (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                           (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
                dense.append((x, y))
        self.poly(dense, mat)

    def _put(self, mask, mat):
        self.mat[mask] = MID[mat]

    def erase(self, mask_fn):
        self.mat[mask_fn(self.px, self.py)] = 0


# ---------- shading ----------

def _box_blur(a, r=1, passes=2):
    out = a.astype(np.float64)
    for _ in range(passes):
        p = np.pad(out, r, mode="edge")
        acc = np.zeros_like(out)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                acc += p[r + dy:r + dy + out.shape[0], r + dx:r + dx + out.shape[1]]
        out = acc / ((2 * r + 1) ** 2)
    return out

def _inner_distance(alpha):
    """chamfer distance to the nearest empty pixel"""
    INF = 1e6
    d = np.where(alpha, INF, 0.0)
    h, w = d.shape
    for y in range(h):
        for x in range(w):
            if d[y, x] == 0:
                continue
            best = d[y, x]
            if y > 0:
                best = min(best, d[y - 1, x] + 1)
                if x > 0:
                    best = min(best, d[y - 1, x - 1] + 1.414)
                if x < w - 1:
                    best = min(best, d[y - 1, x + 1] + 1.414)
            if x > 0:
                best = min(best, d[y, x - 1] + 1)
            d[y, x] = best
    for y in range(h - 1, -1, -1):
        for x in range(w - 1, -1, -1):
            if d[y, x] == 0:
                continue
            best = d[y, x]
            if y < h - 1:
                best = min(best, d[y + 1, x] + 1)
                if x > 0:
                    best = min(best, d[y + 1, x - 1] + 1.414)
                if x < w - 1:
                    best = min(best, d[y + 1, x + 1] + 1.414)
            if x < w - 1:
                best = min(best, d[y, x + 1] + 1)
            d[y, x] = best
    return d

def shade(sp, light=(-0.6, -0.8), rim=(0.85, -0.4), rim_color=(255, 140, 50), rim_strength=0.5):
    """material grid -> RGBA uint8"""
    mat = sp.mat
    h, w = mat.shape
    alpha = mat > 0

    # normals from a blurred alpha field
    sm = _box_blur(alpha.astype(np.float64), r=2, passes=2)
    gy, gx = np.gradient(sm)
    n = np.sqrt(gx * gx + gy * gy) + 1e-6
    nx, ny = -gx / n, -gy / n

    lx, ly = light
    ln = np.hypot(lx, ly)
    lam = np.clip(nx * (lx / ln) + ny * (ly / ln), -1, 1)

    dist = _inner_distance(alpha)
    depth = np.clip(dist / 4.5, 0, 1)

    # per-material tone, then ramp lookup
    out = np.zeros((h, w, 4), dtype=np.uint8)
    tone = np.clip(0.40 + 0.34 * lam + 0.26 * depth, 0, 1)

    for m, mid in MID.items():
        if m == "_":
            continue
        sel = mat == mid
        if not sel.any():
            continue
        ramp = RAMP_RGB[m]
        if m in EMISSIVE:
            # emissive: bright core, mild falloff, never dark
            t = np.clip(0.55 + 0.45 * depth, 0, 1)[sel]
            idx = np.clip((t * (len(ramp) - 1)).round().astype(int), 1, len(ramp) - 1)
        else:
            tt = np.clip(tone[sel] + BIAS.get(m, 0.0), 0, 1)
            idx = np.clip((tt * (len(ramp) - 1)).round().astype(int), 0, len(ramp) - 1)
        cols = np.array(ramp, dtype=np.uint8)[idx]
        out[sel, :3] = cols
        out[sel, 3] = 255

    # internal edges: a darker line where two materials meet, which is what
    # gives hand-drawn sprites their readability at small sizes
    diff = np.zeros_like(alpha)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sh = np.roll(np.roll(mat, dy, axis=0), dx, axis=1)
        diff |= alpha & (sh > 0) & (sh != mat)
    emis = np.zeros_like(alpha)
    for m in EMISSIVE:
        emis |= mat == MID[m]
    inner = diff & ~emis
    if inner.any():
        out[inner, :3] = (out[inner, :3].astype(np.float64) * 0.66).astype(np.uint8)

    # rim light: one side only, one pixel deep
    rx, ry = rim
    rn = np.hypot(rx, ry)
    rimlam = np.clip(nx * (rx / rn) + ny * (ry / rn), 0, 1)
    rmask = alpha & (dist <= 1.4) & (rimlam > 0.62) & ~emis
    if rmask.any():
        k = (rim_strength * rimlam[rmask])[:, None]
        base = out[rmask, :3].astype(np.float64)
        out[rmask, :3] = np.clip(base * (1 - k) + np.array(rim_color) * k, 0, 255).astype(np.uint8)

    # dark outline just outside the silhouette
    pad = np.pad(alpha, 1)
    neigh = np.zeros_like(alpha)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            neigh |= pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    edge = neigh & ~alpha
    out[edge, :3] = OUTLINE
    out[edge, 3] = 255

    return out


def to_png_bytes(rgba):
    """encode RGBA uint8 -> png bytes (stdlib only)"""
    import struct, zlib
    h, w, _ = rgba.shape
    raw = b"".join(b"\x00" + rgba[y].tobytes() for y in range(h))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))
