#!/usr/bin/env python3
"""Render the contribution graph as a scene: Gandalf holds the bridge against
the Balrog, walking across a year of contributions.

The characters are shaded pixel sprites (see pixart.py / chars.py) embedded in
the SVG as base64 PNGs, animated with SMIL so the file is self-contained and
survives GitHub's image proxy.

Usage:
  GITHUB_TOKEN=... python3 scripts/render.py --user FredAmartey --out dist
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

import chars
from pixart import to_png_bytes

# ---------------- contribution data ----------------

QUERY = """
query($login:String!){ user(login:$login){ contributionsCollection {
  contributionCalendar { weeks { contributionDays { date contributionLevel } } } } } }
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

def fetch_weeks(user, token):
    try:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
            headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as r:
            data = json.load(r)
    except Exception:
        import subprocess
        out = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={user}"],
            capture_output=True, text=True, check=True,
        ).stdout
        data = json.loads(out)
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[LEVELS[d["contributionLevel"]] for d in w["contributionDays"]] for w in weeks]

GITHUB_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
GITHUB_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

# ---------------- layout ----------------

CELL, GAP = 10, 2
PITCH = CELL + GAP
MARGIN = 4
SC = 1.25            # svg units per sprite pixel
HEADROOM = 92
DUR = 26             # seconds per loop
WALK = 0.52          # seconds per walk cycle

G_FEET = 65          # sprite row the feet sit on
B_FEET = 61

# choreography, as fractions of the loop
T_TURN = 0.40        # gandalf stops and turns to face the balrog
T_FLASH = 0.435      # the staff flares
T_RECOIL = 0.46
T_RESUME = 0.58      # gandalf turns back and walks on
T_GONE = 0.86        # balrog is off-screen


def data_uri(rgba):
    return "data:image/png;base64," + base64.b64encode(to_png_bytes(rgba)).decode()


def sprite_frames(fn, nframes=4):
    return [data_uri(im) for im in chars.render(fn, nframes)]


def frame_group(uris, w, h, nframes, inner=""):
    """stack the walk frames, showing one at a time"""
    out = []
    slot = WALK / nframes
    for i, uri in enumerate(uris):
        vals = ";".join("1" if k == i else "0" for k in range(nframes)) + ";1" if False else None
        keytimes = ";".join(f"{k / nframes:g}" for k in range(nframes)) + ";1"
        values = ";".join("1" if k == i else "0" for k in range(nframes)) + ";" + ("1" if i == 0 else "0")
        out.append(
            f'<image href="{uri}" x="0" y="0" width="{w:g}" height="{h:g}" '
            f'image-rendering="pixelated" opacity="{1 if i == 0 else 0}">'
            f'<animate attributeName="opacity" values="{values}" keyTimes="{keytimes}" '
            f'dur="{WALK}s" repeatCount="indefinite" calcMode="discrete"/></image>'
        )
    return "".join(out) + inner


def build_svg(weeks, cell_colors, g_uris, b_uris):
    n = len(weeks)
    width = MARGIN * 2 + n * PITCH - GAP
    grid_h = 7 * PITCH - GAP
    height = HEADROOM + grid_h + MARGIN
    baseline = HEADROOM - 2

    cells = []
    for wx, week in enumerate(weeks):
        for dy, level in enumerate(week):
            x = MARGIN + wx * PITCH
            y = HEADROOM + dy * PITCH
            cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                         f'rx="2" fill="{cell_colors[level]}"/>')

    gw, gh = chars.GW * SC, chars.GH * SC
    bw, bh = chars.BW * SC, chars.BH * SC
    g_y = baseline - G_FEET * SC
    b_y = baseline - B_FEET * SC

    # x positions of the sprite boxes over the loop
    g_stand = width * 0.46
    b_stand = g_stand - bw + 6      # right up in gandalf's face
    b_recoil = b_stand - 26

    def kt(*vals):
        return ";".join(f"{v:g}" for v in vals)

    walk_g = (f'<animateTransform attributeName="transform" type="translate" '
              f'values="{-gw - 20} {g_y};{g_stand} {g_y};{g_stand} {g_y};{width + gw} {g_y}" '
              f'keyTimes="{kt(0, T_TURN, T_RESUME, 1)}" dur="{DUR}s" '
              f'repeatCount="indefinite" calcMode="linear"/>')
    # facing: 1 = right, -1 = left. flip about the sprite's own centre.
    flip_g = (f'<animateTransform attributeName="transform" type="translate" '
              f'values="0 0;{gw} 0;0 0" keyTimes="{kt(0, T_TURN, T_RESUME)}" dur="{DUR}s" '
              f'repeatCount="indefinite" calcMode="discrete" additive="sum"/>'
              f'<animateTransform attributeName="transform" type="scale" '
              f'values="1 1;-1 1;1 1" keyTimes="{kt(0, T_TURN, T_RESUME)}" dur="{DUR}s" '
              f'repeatCount="indefinite" calcMode="discrete" additive="sum"/>')

    walk_b = (f'<animateTransform attributeName="transform" type="translate" '
              f'values="{-bw - 140} {b_y};{b_stand} {b_y};{b_stand} {b_y};{b_recoil} {b_y};'
              f'{b_recoil + 6} {b_y};{-bw - 200} {b_y};{-bw - 200} {b_y}" '
              f'keyTimes="{kt(0, T_TURN, T_FLASH, T_RECOIL + 0.02, T_RESUME, T_GONE, 1)}" '
              f'dur="{DUR}s" repeatCount="indefinite" calcMode="linear"/>')
    # the balrog chases facing right, then turns to flee facing left
    flip_b = (f'<animateTransform attributeName="transform" type="translate" '
              f'values="{bw} 0;{bw} 0;0 0" keyTimes="{kt(0, T_FLASH, T_RECOIL + 0.02)}" '
              f'dur="{DUR}s" repeatCount="indefinite" calcMode="discrete" additive="sum"/>'
              f'<animateTransform attributeName="transform" type="scale" '
              f'values="-1 1;-1 1;1 1" keyTimes="{kt(0, T_FLASH, T_RECOIL + 0.02)}" '
              f'dur="{DUR}s" repeatCount="indefinite" calcMode="discrete" additive="sum"/>')

    # staff crystal, in sprite coords, scaled
    ox, oy = 41.2 * SC, 10.5 * SC
    flash = (f'<circle cx="{ox:g}" cy="{oy:g}" r="{7 * SC:g}" fill="#dbeafe" opacity="0">'
             f'<animate attributeName="opacity" values="0;0;1;0;0" '
             f'keyTimes="{kt(0, T_FLASH - 0.012, T_FLASH, T_FLASH + 0.05, 1)}" dur="{DUR}s" '
             f'repeatCount="indefinite"/></circle>')
    ring = (f'<circle cx="{ox:g}" cy="{oy:g}" r="6" fill="none" stroke="#bfdbfe" '
            f'stroke-width="2.5" opacity="0">'
            f'<animate attributeName="r" values="6;6;{width * 0.16:g};{width * 0.16:g}" '
            f'keyTimes="{kt(0, T_FLASH, T_FLASH + 0.06, 1)}" dur="{DUR}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0;0.95;0;0" '
            f'keyTimes="{kt(0, T_FLASH - 0.004, T_FLASH, T_FLASH + 0.06, 1)}" dur="{DUR}s" '
            f'repeatCount="indefinite"/></circle>')
    glow = (f'<circle cx="{ox:g}" cy="{oy:g}" r="{3.2 * SC:g}" fill="#93c5fd" opacity="0.35">'
            f'<animate attributeName="opacity" values="0.3;0.55;0.3" dur="1.7s" '
            f'repeatCount="indefinite"/></circle>')

    gandalf = (f'<g>{walk_g}<g>{flip_g}{glow}'
               f'{frame_group(g_uris, gw, gh, len(g_uris))}{flash}{ring}</g></g>')
    balrog = f'<g>{walk_b}<g>{flip_b}{frame_group(b_uris, bw, bh, len(b_uris))}</g></g>'

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">\n'
            f'{"".join(cells)}\n{gandalf}\n{balrog}\n</svg>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="FredAmartey")
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("set GITHUB_TOKEN")
    weeks = fetch_weeks(args.user, token)

    g_uris = sprite_frames(chars.gandalf)
    b_uris = sprite_frames(chars.balrog)

    for name, colors in (("light", GITHUB_LIGHT), ("dark", GITHUB_DARK)):
        path = os.path.join(args.out, f"khazad-graph-{name}.svg")
        with open(path, "w") as f:
            f.write(build_svg(weeks, colors, g_uris, b_uris))
        print("wrote", path, os.path.getsize(path) // 1024, "KB")


if __name__ == "__main__":
    main()
