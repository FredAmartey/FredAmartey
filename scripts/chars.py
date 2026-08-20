#!/usr/bin/env python3
"""The two characters, drawn as shaded pixel sprites."""
import math
from pixart import Sprite, shade

GW, GH = 52, 68     # gandalf grid
BW, BH = 66, 64     # balrog grid


def flame(s, cx, base, w, h, mat, lean=0.0):
    """a teardrop tongue of fire rising from (cx, base)"""
    s.blob([
        (cx - w / 2, base),
        (cx - w / 2.4 + lean * 0.3, base - h * 0.42),
        (cx - w / 6 + lean * 0.7, base - h * 0.78),
        (cx + lean, base - h),
        (cx + w / 5 + lean * 0.7, base - h * 0.72),
        (cx + w / 2.4 + lean * 0.3, base - h * 0.38),
        (cx + w / 2, base),
    ], mat)


def gandalf(frame=0, nframes=4):
    """frame 0..n-1 of a walk cycle. faces right."""
    t = frame / nframes
    step = math.sin(2 * math.pi * t)
    bob = -1 if frame in (1, 3) else 0
    cape = math.sin(2 * math.pi * t + 0.9) * 1.5

    s = Sprite(GW, GH)
    B = 65 + bob

    # ---- staff behind ----
    s.curve((41, 12), (42.5, 34), (40, B - 1), 3.0, "wood")
    s.ellipse(41.4, 31, 2.2, 1.8, "wood")

    # ---- cloak behind the body ----
    s.blob([(14 + cape, 32), (11 + cape * 1.5, 46), (10 + cape * 1.7, B - 6),
            (21, B - 4), (25, 46), (24, 32)], "robe2")

    # ---- boots, below the hem so the walk reads ----
    s.rect(18 + step * 2.6, B - 6, 25 + step * 2.6, B, "hat", r=1.8)
    s.rect(26 - step * 2.6, B - 5, 33 - step * 2.6, B, "hat", r=1.8)

    # ---- robe ----
    s.poly([(18, 32), (32, 32), (35, 46), (36, B - 7), (14, B - 7), (15, 46)], "robe")
    s.poly([(14, B - 10), (36, B - 10), (36, B - 7), (14, B - 7)], "robe2")
    s.line((25, 36), (25.5, B - 8), 1.6, "robe2")
    s.line((20, 40), (18.5, B - 8), 1.2, "robe2")
    s.line((30, 40), (32, B - 8), 1.2, "robe2")

    # ---- mantle over the shoulders ----
    s.blob([(16, 32), (25, 29), (34, 32), (35, 37), (25, 39), (15, 37)], "robe2")

    # ---- right arm to the staff ----
    s.curve((32, 35), (37, 32), (40.5, 31), 4.0, "robe")
    s.ellipse(41, 30.5, 2.4, 2.0, "skin")

    # ---- left arm down with glamdring ----
    s.curve((17, 36), (13, 42), (12, 47), 3.8, "robe")
    s.ellipse(11.6, 48, 2.2, 2.0, "skin")
    s.line((11.6, 48), (16.5, 38), 2.4, "steel")
    s.line((11.6, 49.4), (9.4, 53.5), 1.8, "gold")

    # ---- beard: narrow, hanging from the chin to a point ----
    s.blob([(20.4, 31), (19.4, 37), (20.6, 43), (23, 47), (25, 49),
            (27, 47), (29.4, 43), (30.6, 37), (29.6, 31)], "beard")
    s.line((25, 37), (25, 47), 1.0, "hat")
    s.line((22.4, 37), (23, 44), 0.9, "hat")
    s.line((27.6, 37), (27, 44), 0.9, "hat")

    # ---- face, sitting below the brim ----
    s.ellipse(25, 28.6, 6.0, 5.2, "skin")
    # brow shadow only across the top of the face
    s.blob([(19.6, 24.8), (25, 23.8), (30.4, 24.8), (30.4, 26.4), (25, 27.2), (19.6, 26.4)], "robe2")
    # eyes, just below the shadow
    s.rect(21.5, 27.2, 22.9, 28.4, "steel")
    s.rect(27.1, 27.0, 28.5, 28.2, "steel")
    s.rect(21.9, 27.4, 22.6, 28.1, "orb")
    s.rect(27.5, 27.2, 28.2, 27.9, "orb")
    # brows
    s.line((20.8, 26.4), (23.4, 26.9), 1.2, "beard")
    s.line((29.2, 26.2), (26.6, 26.7), 1.2, "beard")
    s.ellipse(25, 30.6, 1.8, 1.6, "skin")     # nose
    # moustache
    s.blob([(19, 32), (22, 34), (25, 33), (28, 34), (31, 32),
            (29, 36), (25, 35), (21, 36)], "beard")

    # ---- hat ----
    s.blob([(20, 11), (24, 4), (28, 3), (31, 8), (33, 16), (34, 21), (17, 21), (18, 16)], "hat")
    s.curve((27, 6), (25, 1), (19, 2), 3.8, "hat", taper=2.0)
    s.blob([(9, 21), (25, 16.6), (41, 21), (41, 24), (25, 25.6), (9, 24)], "hat")
    s.blob([(11, 23), (25, 21), (39, 23), (39, 24.6), (25, 25.6), (11, 24.6)], "robe2")
    s.blob([(18.5, 19), (25, 17.4), (33, 19), (33, 20.6), (25, 19.2), (18.5, 20.6)], "wood")

    # ---- crystal, cradled in the staff head ----
    s.curve((37.6, 15), (38.4, 9), (41, 7), 2.4, "wood")
    s.ellipse(41.2, 10.5, 4.4, 5.0, "orb")
    s.rect(39.6, 8.4, 40.8, 9.6, "tooth")     # specular

    return s


def balrog(frame=0, nframes=4):
    """frame 0..n-1. faces left, toward gandalf.

    chibi proportions: the head and horns carry the silhouette, the body is
    small under it. values step darker from head to body to limbs to wings so
    the planes stay separate at this size.
    """
    t = frame / nframes
    step = math.sin(2 * math.pi * t)
    bob = -1 if frame in (1, 3) else 0
    fl = math.sin(2 * math.pi * t)
    fl2 = math.sin(2 * math.pi * t + 2.1)

    s = Sprite(BW, BH)
    B = 61 + bob

    # ---- fire mane rising behind everything ----
    for i, (cx, w, h) in enumerate([(18, 9, 13), (25, 11, 18), (33, 13, 23),
                                    (41, 11, 18), (48, 9, 13)]):
        lean = (fl if i % 2 else fl2) * 2.4
        flame(s, cx, 26, w, h, "fire", lean)
    for i, (cx, w, h) in enumerate([(23, 6, 12), (32, 8, 17), (40, 6, 12)]):
        lean = (fl2 if i % 2 else fl) * 2.6
        flame(s, cx, 25, w, h, "fire2", lean)

    # ---- wings, small and swept back ----
    for sgn, x0 in ((-1, 26), (1, 40)):
        s.blob([
            (x0, 40),
            (x0 + sgn * 5, 32),
            (x0 + sgn * 14, 24),
            (x0 + sgn * 21, 18),
            (x0 + sgn * 18, 27),
            (x0 + sgn * 20, 32),
            (x0 + sgn * 13, 31),
            (x0 + sgn * 13, 38),
            (x0 + sgn * 7, 36),
        ], "wing")
        s.line((x0 + sgn * 2, 37), (x0 + sgn * 19, 20), 1.0, "bskin2")
        s.line((x0 + sgn * 2, 38), (x0 + sgn * 17, 29), 1.0, "bskin2")

    # ---- legs ----
    s.curve((29, 45), (27 + step * 2, 52), (26 + step * 2.6, B - 3), 8.0, "bskin2", taper=6.0)
    s.curve((39, 45), (41 - step * 2, 52), (42 - step * 2.6, B - 3), 8.0, "bskin2", taper=6.0)
    s.blob([(21 + step * 2.6, B - 4), (30 + step * 2.6, B - 5),
            (31 + step * 2.6, B), (20 + step * 2.6, B)], "bskin2")
    s.blob([(38 - step * 2.6, B - 5), (47 - step * 2.6, B - 4),
            (48 - step * 2.6, B), (37 - step * 2.6, B)], "bskin2")

    # ---- body, with a shadow band under the head so the planes separate ----
    s.blob([(25, 38), (34, 34), (43, 38), (45, 44), (42, 49),
            (34, 51), (26, 49), (23, 44)], "bskin2")
    s.blob([(25, 36), (34, 33.4), (43, 36), (43, 38.4), (34, 36.4), (25, 38.4)], "wing")
    s.line((29, 46), (31, 42), 1.3, "lava")
    s.line((39, 47), (37, 43), 1.3, "lava")
    s.line((34, 47), (34.6, 43), 1.2, "lava")

    # ---- arms ----
    s.curve((26, 40), (19, 44), (15 - step, 49), 5.6, "bskin2", taper=3.6)
    s.ellipse(14.4 - step, 50.4, 2.8, 2.6, "bskin2")
    for ang in (2.5, 2.9, 3.3):
        s.line((14.4 - step, 50.4),
               (14.4 - step + 4.2 * math.cos(ang), 50.4 + 4.2 * math.sin(ang)), 1.2, "horn")
    s.curve((42, 40), (49, 43), (52 + step, 48), 5.2, "bskin2", taper=3.2)
    s.ellipse(52.6 + step, 49.2, 2.5, 2.3, "bskin2")

    # ---- head: the big shape ----
    s.blob([(22, 22), (27, 14), (34, 12), (41, 14), (46, 22),
            (45, 30), (39, 34), (29, 34), (23, 30)], "bskin")
    # muzzle thrust toward gandalf
    s.blob([(24, 24), (17, 25), (13, 29), (16, 34), (24, 34)], "bskin")
    # brow ridge
    s.blob([(20, 21), (34, 17), (47, 21), (46, 24), (34, 20), (20, 24)], "bskin2")

    # ---- horns: bone, the readable contrast ----
    s.curve((25, 19), (18, 10), (11, 4), 5.0, "horn", taper=1.2)
    s.curve((43, 19), (50, 10), (57, 3), 5.2, "horn", taper=1.2)

    # ---- eyes: narrow slits, angled into a scowl ----
    s.poly([(20.5, 26.6), (25.5, 23.6), (29.5, 24.6), (24.5, 27.6)], "bskin2")
    s.poly([(34.5, 25.4), (39.5, 22.4), (43.5, 23.4), (38.5, 26.4)], "bskin2")
    s.poly([(21.8, 26.3), (25.4, 24.4), (28.2, 25.1), (24.6, 27.0)], "eye")
    s.poly([(35.8, 25.1), (39.4, 23.2), (42.2, 23.9), (38.6, 25.8)], "eye")
    s.rect(24.4, 25.2, 25.4, 26.2, "hot")
    s.rect(38.4, 24.0, 39.4, 25.0, "hot")

    # ---- jaw, open, lit from inside ----
    s.blob([(14, 30), (20, 29), (25, 30.4), (24, 34.6), (18, 35.4), (13.4, 33)], "bskin2")
    s.blob([(15.4, 31.4), (20, 30.8), (23.4, 31.6), (22.6, 33.8), (18, 34.4), (14.8, 32.8)], "lava")
    for x in (15.6, 18.2, 20.8):
        s.poly([(x, 30.6), (x + 1.6, 30.6), (x + 0.8, 33.2)], "tooth")
    for x in (16.8, 19.4):
        s.poly([(x, 34.6), (x + 1.5, 34.6), (x + 0.75, 32.4)], "tooth")
    s.ellipse(15.6, 27.6, 1.0, 0.8, "bskin2")     # nostril

    # ---- flame guttering in the near claw ----
    flame(s, 13.6 - step, 49, 6, 9 + fl, "fire2", fl * 1.5)

    return s


def _balrog_old(frame=0, nframes=4):
    t = frame / nframes
    step = math.sin(2 * math.pi * t)
    bob = -1 if frame in (1, 3) else 0
    fl = math.sin(2 * math.pi * t)
    fl2 = math.sin(2 * math.pi * t + 2.1)

    s = Sprite(BW, BH)
    B = 60 + bob

    # ---- wings: two spans sweeping up and back ----
    for sgn, x0 in ((-1, 29), (1, 37)):
        s.blob([
            (x0, 32),
            (x0 + sgn * 6, 22),
            (x0 + sgn * 16, 12),
            (x0 + sgn * 26, 4),
            (x0 + sgn * 22, 14),
            (x0 + sgn * 24, 20),
            (x0 + sgn * 16, 20),
            (x0 + sgn * 17, 27),
            (x0 + sgn * 10, 25),
            (x0 + sgn * 9, 32),
        ], "wing")
        s.line((x0 + sgn * 3, 28), (x0 + sgn * 24, 6), 1.1, "bskin2")
        s.line((x0 + sgn * 3, 28), (x0 + sgn * 21, 17), 1.0, "bskin2")
        s.line((x0 + sgn * 3, 29), (x0 + sgn * 15, 24), 1.0, "bskin2")

    # ---- mane of fire, spiky ----
    for i, (cx, w, h) in enumerate([(20, 9, 12), (27, 11, 17), (34, 12, 21),
                                    (41, 11, 17), (47, 9, 12)]):
        lean = (fl if i % 2 else fl2) * 2.2
        flame(s, cx, 22, w, h, "fire", lean)
    for i, (cx, w, h) in enumerate([(25, 6, 11), (33, 7, 15), (40, 6, 11)]):
        lean = (fl2 if i % 2 else fl) * 2.4
        flame(s, cx, 21, w, h, "fire2", lean)

    # ---- legs ----
    s.curve((26, 44), (24 + step * 2, 50), (23 + step * 3, B - 3), 9.0, "bskin2", taper=6.5)
    s.curve((41, 44), (43 - step * 2, 50), (44 - step * 3, B - 3), 9.0, "bskin2", taper=6.5)
    s.blob([(17 + step * 3, B - 4), (27 + step * 3, B - 5), (28 + step * 3, B),
            (16 + step * 3, B)], "bskin2")
    s.blob([(39 - step * 3, B - 5), (50 - step * 3, B - 4), (51 - step * 3, B),
            (38 - step * 3, B)], "bskin2")

    # ---- hunched torso, broad at the shoulders ----
    s.blob([(21, 26), (34, 21), (47, 26), (49, 35), (46, 45), (34, 48),
            (22, 45), (19, 35)], "bskin")
    s.ellipse(28, 32, 5.4, 4.2, "bskin2")
    s.ellipse(40, 32, 5.4, 4.2, "bskin2")
    # lava seams
    s.line((25, 40), (28, 36), 1.4, "lava")
    s.line((28, 36), (27, 32), 1.3, "lava")
    s.line((43, 41), (41, 37), 1.4, "lava")
    s.line((34, 44), (36, 39), 1.3, "lava")
    s.ellipse(34, 37, 3.0, 2.2, "lava")

    # ---- arms: compact, ending in claws ----
    s.curve((23, 30), (16, 34), (13 - step, 41), 6.0, "bskin", taper=3.8)
    s.ellipse(12.4 - step, 42.4, 2.9, 2.7, "bskin")
    for k, ang in enumerate((2.5, 2.9, 3.3)):
        s.line((12.4 - step, 42.4),
               (12.4 - step + 4.4 * math.cos(ang), 42.4 + 4.4 * math.sin(ang)), 1.2, "horn")
    s.curve((45, 30), (52, 33), (55 + step, 39), 5.4, "bskin2", taper=3.4)
    s.ellipse(55.6 + step, 40.4, 2.6, 2.4, "bskin2")

    # ---- head, thrust forward ----
    s.blob([(25, 17), (34, 13), (43, 17), (45, 24), (41, 29), (34, 30),
            (27, 29), (23, 24)], "bskin")
    # muzzle
    s.blob([(27, 22), (20, 23), (16, 26), (18, 30), (27, 30)], "bskin")
    # brow
    s.blob([(23, 20), (34, 17), (44, 20), (44, 22.4), (34, 20), (23, 22.4)], "bskin2")

    # ---- horns ----
    s.curve((26, 18), (20, 10), (13, 5), 4.6, "horn", taper=1.2)
    s.curve((42, 18), (49, 10), (56, 4), 4.8, "horn", taper=1.2)
    s.curve((28, 27), (23, 30), (18, 29), 2.8, "horn", taper=0.9)
    s.curve((41, 27), (46, 30), (51, 29), 2.6, "horn", taper=0.9)

    # ---- eyes: narrow, furious, sunk in dark sockets ----
    s.blob([(23, 23), (27.5, 20.4), (32, 23), (27.5, 25.6)], "bskin2")
    s.blob([(35, 22.4), (39.5, 19.8), (44, 22.4), (39.5, 25)], "bskin2")
    s.blob([(24.2, 23), (27.5, 21.2), (30.8, 23), (27.5, 24.8)], "eye")
    s.blob([(36.2, 22.4), (39.5, 20.6), (42.8, 22.4), (39.5, 24.2)], "eye")
    s.rect(26.9, 22.4, 28.1, 23.6, "tooth")
    s.rect(38.9, 21.8, 40.1, 23.0, "tooth")

    # ---- jaw ----
    s.blob([(17, 26.6), (24, 25.4), (30, 26.6), (28, 30.4), (21, 31), (16.4, 28.6)], "bskin2")
    for x in (18.6, 21.4, 24.2, 27.0):
        s.poly([(x, 26.2), (x + 1.5, 26.2), (x + 0.75, 29.0)], "tooth")
    s.line((18, 29.8), (28, 28.8), 1.5, "lava")

    # ---- whip of flame ----
    s.curve((6 - step, 44), (2, 48 + fl * 2), (1, 56), 2.8, "fire2", taper=1.2)

    return s


def render(fn, frames=4):
    return [shade(fn(i, frames)) for i in range(frames)]


if __name__ == "__main__":
    from pixart import to_png_bytes
    import numpy as np

    gs = render(gandalf)
    bs = render(balrog)
    scale = 4
    cols = 4
    cell_w = max(GW, BW)
    sheet = np.zeros(((GH + BH) * scale, cell_w * cols * scale, 4), dtype=np.uint8)
    sheet[:, :, :3] = 60
    sheet[:, :, 3] = 255

    def paste(img, ox, oy):
        h, w, _ = img.shape
        big = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)
        region = sheet[oy * scale:oy * scale + h * scale, ox * scale:ox * scale + w * scale]
        a = (big[:, :, 3:4] / 255.0)
        region[:, :, :3] = (region[:, :, :3] * (1 - a) + big[:, :, :3] * a).astype(np.uint8)

    for i, im in enumerate(gs):
        paste(im, i * cell_w, 0)
    for i, im in enumerate(bs):
        paste(im, i * cell_w, GH)

    open("sheet.png", "wb").write(to_png_bytes(sheet))
    print("wrote sheet.png")
