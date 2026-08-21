#!/usr/bin/env python3
"""Build the cinematic profile banner.

The source scene is deliberately reduced to a transparent collage rather than
embedded as a rectangular painting. Dark architecture dissolves into GitHub's
page background while the bridge, fire and two figures stay legible in either
theme. The SVG adds a restrained layer of embers around the raster artwork.

Run from anywhere with:

    python3 scripts/banner.py
"""

from __future__ import annotations

import base64
import io
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


W, H = 1600, 700
TRAVELER_HEIGHT = 176
DEMON_HEIGHT = 470
TRAVELER_X, TRAVELER_GROUND = 370, 486
DEMON_X, DEMON_GROUND = 1160, 426

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "art")
SCENE_PATH = os.path.join(ART, "bridge-background.png")
TRAVELER_PATH = os.path.join(ART, "traveler.png")
DEMON_PATH = os.path.join(ART, "fire-demon.png")
OUT = os.path.join(ROOT, "banner.svg")


def smoothstep(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def trim(image: Image.Image) -> Image.Image:
    box = image.getbbox()
    return image.crop(box) if box else image


def cover(image: Image.Image) -> Image.Image:
    """Resize and crop around the bridge, not the geometric centre."""
    scale = max(W / image.width, H / image.height)
    size = (round(image.width * scale), round(image.height * scale))
    resized = image.resize(size, Image.Resampling.LANCZOS)
    left = max(0, (resized.width - W) // 2)
    overflow = max(0, resized.height - H)
    top = round(overflow * 0.48)
    return resized.crop((left, top, left + W, top + H))


def scene_layer() -> Image.Image:
    scene = cover(Image.open(SCENE_PATH).convert("RGB"))
    rgb = np.asarray(scene, dtype=np.float32) / 255
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)

    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    fire = np.clip((rgb[:, :, 0] - rgb[:, :, 1] * 0.72 - 0.05) * 3.2, 0, 1)
    detail = smoothstep((luminance - 0.018) / 0.18)

    edge = (
        smoothstep(x / 128)
        * smoothstep((W - 1 - x) / 128)
        * smoothstep(y / 72)
        * smoothstep((H - 1 - y) / 118)
    )

    # Keep the story line of the bridge intact while allowing the surrounding
    # black stone to disappear into the page.
    bridge_y = 526 - 0.12 * x
    bridge = np.exp(-((y - bridge_y) / 92) ** 2)
    atmosphere = np.maximum(detail, fire)
    alpha = edge * np.maximum(0.18 + atmosphere * 0.78, bridge * 0.84)

    rgba = np.dstack((rgb, np.clip(alpha, 0, 0.98)))
    return Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")


def ground_row(image: Image.Image) -> int:
    alpha = np.asarray(image)[:, :, 3]
    solid = (alpha > 180).sum(axis=1)
    rows = np.nonzero(solid >= max(2, int(image.width * 0.012)))[0]
    return int(rows.max()) + 1 if len(rows) else image.height


def foot_anchor(image: Image.Image) -> float:
    alpha = np.asarray(image)[:, :, 3]
    ground = ground_row(image)
    depth = max(2, round(image.height * 0.035))
    sole = (alpha[max(0, ground - depth) : ground] > 180).any(axis=0)
    columns = np.nonzero(sole)[0]
    return float(columns.mean() / image.width) if len(columns) else 0.5


def place(image: Image.Image, height: int, x: int, ground: int) -> tuple[Image.Image, int, int]:
    scale = height / ground_row(image)
    size = (round(image.width * scale), round(image.height * scale))
    resized = image.resize(size, Image.Resampling.LANCZOS)
    left = round(x - size[0] * foot_anchor(image))
    top = round(ground - height)
    return resized, left, top


def shadow(canvas: Image.Image, x: int, y: int, width: int, opacity: int) -> None:
    layer = Image.new("RGBA", canvas.size)
    draw = ImageDraw.Draw(layer)
    draw.ellipse((x - width, y - 11, x + width, y + 9), fill=(0, 0, 0, opacity))
    layer = layer.filter(ImageFilter.GaussianBlur(9))
    canvas.alpha_composite(layer)


def build_raster() -> Image.Image:
    canvas = scene_layer()
    traveler = trim(Image.open(TRAVELER_PATH).convert("RGBA"))
    demon = trim(Image.open(DEMON_PATH).convert("RGBA"))

    traveler, tx, ty = place(traveler, TRAVELER_HEIGHT, TRAVELER_X, TRAVELER_GROUND)
    demon, dx, dy = place(demon, DEMON_HEIGHT, DEMON_X, DEMON_GROUND)

    shadow(canvas, TRAVELER_X, TRAVELER_GROUND, 58, 108)
    shadow(canvas, DEMON_X, DEMON_GROUND, 172, 146)
    canvas.alpha_composite(demon, (dx, dy))
    canvas.alpha_composite(traveler, (tx, ty))
    return canvas


def webp_uri(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=91, method=6)
    return "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode()


def spark_markup() -> str:
    rng = np.random.default_rng(28)
    colors = ["#ff9a3c", "#ffc763", "#f0561f"]
    sparks: list[str] = []
    for index in range(34):
        start_x = rng.uniform(0.43, 0.92) * W
        start_y = rng.uniform(0.72, 0.98) * H
        radius = rng.uniform(1.0, 2.8)
        drift = rng.uniform(-58, 42)
        rise = rng.uniform(180, 560)
        duration = rng.uniform(7.0, 14.0)
        delay = rng.uniform(0, 14)
        sparks.append(
            f'<circle cx="{start_x:.0f}" cy="{start_y:.0f}" r="{radius:.1f}" '
            f'fill="{colors[index % len(colors)]}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.9;0.45;0" '
            f'keyTimes="0;0.14;0.65;1" dur="{duration:.1f}s" '
            f'begin="-{delay:.1f}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{drift:.0f} -{rise:.0f}" dur="{duration:.1f}s" '
            f'begin="-{delay:.1f}s" repeatCount="indefinite"/>'
            "</circle>"
        )
    return "".join(sparks)


def build_svg() -> str:
    uri = webp_uri(build_raster())
    sparks = spark_markup()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-labelledby="title description">'
        '<title id="title">A confrontation on a narrow bridge</title>'
        '<desc id="description">A lone traveler faces a towering fire demon above a burning abyss.</desc>'
        '<style>@media (prefers-reduced-motion: reduce){.motion{display:none}}</style>'
        '<defs><radialGradient id="fire-spill" cx="50%" cy="50%" r="50%">'
        '<stop offset="0" stop-color="#ff8b2a" stop-opacity="0.24"/>'
        '<stop offset="0.48" stop-color="#e8531a" stop-opacity="0.08"/>'
        '<stop offset="1" stop-color="#e8531a" stop-opacity="0"/>'
        '</radialGradient></defs>'
        '<g class="motion"><ellipse cx="1160" cy="326" rx="410" ry="314" fill="url(#fire-spill)">'
        '<animate attributeName="opacity" values="0.72;1;0.8;0.94;0.72" dur="6.4s" '
        'repeatCount="indefinite"/></ellipse></g>'
        f'<image href="{uri}" x="0" y="0" width="{W}" height="{H}" image-rendering="pixelated"/>'
        f'<g class="motion">{sparks}</g>'
        '</svg>'
    )


with open(OUT, "w", encoding="utf-8") as file:
    file.write(build_svg())

print(f"wrote {OUT} ({os.path.getsize(OUT) // 1024} KB) {W}x{H}")
