#!/usr/bin/env python3
"""Build the cleaned native 16x16 Elwin Hero v3 source."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "docs/assets/ai-class-source/latest/elwin-hero-v2/logical16/22-hero.png"
)
OUTPUT = ROOT / "docs/assets/ai-class-source/latest/elwin-hero-v3"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
ROM_SPRITE = ROOT / "editor/static/class-sprites/commanders/1/22-p1.png"

TRANSPARENT = (0, 0, 0, 0)
COLORS = {
    ".": TRANSPARENT,
    "K": (36, 36, 36, 255),
    "D": (109, 0, 0, 255),
    "R": (146, 0, 0, 255),
    "S": (146, 146, 146, 255),
    "W": (255, 255, 255, 255),
    "B": (0, 73, 182, 255),
    "L": (182, 219, 219, 255),
    "G": (219, 146, 0, 255),
    "T": (146, 73, 36, 255),
}

# The accepted v2 head, face, large sword, and upper silhouette stay intact.
# Only the seven lower rows are redrawn with larger coherent material blocks.
LOWER_ROWS = (
    ".GGRKSWGBWSKRR..",
    "..GSKSBBBGRRRK..",
    "...K.KSBWBGDRRK.",
    "...TKSBGBBKDRRRK",
    "...DRTLBGBLTRDRK",
    "...TWWT..TWWDRG.",
    ".....WT..TW.....",
)


def visible_palette(image: Image.Image) -> list[str]:
    counts = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def build() -> dict[str, object]:
    previous = Image.open(SOURCE).convert("RGBA")
    if previous.size != (16, 16):
        raise ValueError(f"Elwin Hero v2 must be 16x16, got {previous.size}")
    image = previous.copy()
    for y, row in enumerate(LOWER_ROWS, start=9):
        if len(row) != 16:
            raise ValueError(f"invalid Hero row {y}: {row!r}")
        for x, symbol in enumerate(row):
            image.putpixel((x, y), COLORS[symbol])

    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    identity = {tuple(point) for point in masks["1:22"]}
    rom = Image.open(ROM_SPRITE).convert("RGBA")
    for point in identity:
        if image.getpixel(point) != rom.getpixel(point):
            raise ValueError(f"Hero identity pixel changed at {point}")

    palette = visible_palette(image)
    empty_rows = [
        y
        for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x
        for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    if len(palette) > 15 or empty_rows or empty_columns:
        raise ValueError(
            f"invalid Hero v3: colors={len(palette)}, "
            f"rows={empty_rows}, columns={empty_columns}"
        )
    if (0, 0, 0, 255) in image.getdata():
        raise ValueError("Hero v3 must not contain pure black")

    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT / "22-hero.png", optimize=True)
    image.save(logical_dir / "22-hero.png", optimize=True)
    image.resize((512, 512), Image.Resampling.NEAREST).save(
        preview_dir / "22-hero.png", optimize=True
    )

    comparison = Image.new("RGBA", (512, 256), (36, 36, 42, 255))
    comparison.alpha_composite(
        previous.resize((256, 256), Image.Resampling.NEAREST), (0, 0)
    )
    comparison.alpha_composite(
        image.resize((256, 256), Image.Resampling.NEAREST), (256, 0)
    )
    draw = ImageDraw.Draw(comparison)
    draw.text((8, 8), "v2", fill=(255, 255, 255, 255))
    draw.text((264, 8), "v3 cleaned", fill=(255, 255, 255, 255))
    comparison.save(OUTPUT / "elwin-hero-v2-v3-comparison.png", optimize=True)

    report = {
        "size": list(image.size),
        "identity_match": len(identity),
        "identity_pixel_count": len(identity),
        "visible_color_count": len(palette),
        "palette": palette,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black": False,
        "accepted": True,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
