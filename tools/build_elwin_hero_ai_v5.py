#!/usr/bin/env python3
"""Build the from-scratch AI-derived native 16x16 Elwin Hero v5."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / "assets/class-sprites/source/latest/elwin-hero-ai-v5-fresh"
CANDIDATE = OUTPUT / "candidates/hero-from-rom-and-mask-only-v2.png"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
ROM_SPRITE = ROOT / "editor/static/class-sprites/commanders/1/22-p1.png"

from tools.build_liana_lana_native16_assets import (
    limit_visible_palette,
    restore_identity_pixels,
)
from tools.build_liana_lana_strict16_candidates import (
    lock_high_resolution_identity,
    strict_cell_sample,
)


def visible_palette(image: Image.Image) -> list[str]:
    counts = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def fresh_native_hero(
    original: Image.Image,
    identity: set[tuple[int, int]],
) -> Image.Image:
    """Pixelize the fresh AI concept without any earlier Hero coordinates."""
    transparent = (0, 0, 0, 0)
    ink = (36, 36, 36, 255)
    gray = (73, 73, 73, 255)
    silver = (182, 182, 182, 255)
    white = (255, 255, 255, 255)
    gold = (255, 182, 0, 255)
    gold_light = (255, 219, 109, 255)
    red = (219, 0, 0, 255)
    red_dark = (109, 0, 0, 255)
    blue = (0, 36, 109, 255)
    blue_light = (36, 109, 219, 255)
    skin = (219, 182, 109, 255)
    brown = (146, 73, 36, 255)

    result = Image.new("RGBA", (16, 16), transparent)

    def paint(
        points: set[tuple[int, int]] | list[tuple[int, int]],
        color: tuple[int, int, int, int],
    ) -> None:
        for point in points:
            if point not in identity:
                result.putpixel(point, color)

    def rect(x0: int, y0: int, x1: int, y1: int) -> set[tuple[int, int]]:
        return {
            (x, y)
            for y in range(y0, y1 + 1)
            for x in range(x0, x1 + 1)
        }

    # Short, wide crimson cape behind the newly drawn armor.
    paint(rect(2, 8, 13, 14), red_dark)
    paint(rect(1, 10, 3, 13) | rect(12, 10, 14, 13), red)

    # Broad connected silhouette and two balanced pauldrons.
    paint(
        rect(1, 7, 5, 10)
        | rect(10, 7, 14, 10)
        | rect(3, 8, 12, 14)
        | rect(2, 14, 7, 15)
        | rect(8, 14, 13, 15),
        ink,
    )
    paint({(0, 8), (0, 9)}, ink)
    paint(rect(2, 7, 4, 9) | rect(11, 7, 13, 9), silver)
    paint(
        {(2, 7), (3, 7), (12, 7), (13, 7),
         (1, 8), (2, 8), (13, 8), (14, 8)},
        white,
    )
    paint(
        {(1, 9), (4, 7), (4, 8), (4, 9),
         (11, 7), (11, 8), (11, 9), (14, 9)},
        gold,
    )
    paint({(2, 9), (13, 9)}, gold_light)

    # Silver breastplate, dark separators, and compact blue heroic tabard.
    paint(rect(4, 9, 11, 12), gray)
    paint(rect(5, 9, 10, 11), silver)
    paint({(6, 9), (7, 9), (8, 9), (9, 9)}, white)
    paint({(5, 10), (6, 10), (9, 10), (10, 10)}, white)
    paint({(4, 11), (11, 11), (4, 12), (11, 12)}, gold)
    paint(rect(7, 10, 8, 13), blue)
    paint({(7, 10), (8, 12)}, blue_light)
    paint({(6, 12), (9, 12), (6, 13), (9, 13)}, gold)

    # Chunky armored legs and grounded boots.
    paint(rect(4, 12, 6, 14) | rect(9, 12, 11, 14), silver)
    paint({(5, 12), (10, 12), (4, 13), (11, 13)}, white)
    paint({(4, 14), (5, 14), (10, 14), (11, 14)}, gold_light)
    paint(rect(3, 15, 7, 15) | rect(8, 15, 12, 15), ink)
    paint({(4, 15), (5, 15), (10, 15), (11, 15)}, silver)
    paint({(6, 15), (9, 15)}, gold)

    # One large connected straight sword on image-right.  It reaches the
    # outer column, joins its guard, hand, forearm, and right shoulder.
    paint({(15, y) for y in range(0, 9)}, white)
    paint({(14, y) for y in range(2, 8)}, silver)
    paint({(14, 1), (14, 8)}, gray)
    paint({(12, 9), (13, 9), (14, 9), (15, 9)}, ink)
    paint({(13, 9), (14, 9)}, gold)
    paint({(12, 10)}, skin)
    paint({(13, 10), (13, 11)}, brown)

    return restore_identity_pixels(result, original, identity)


def build() -> dict[str, object]:
    candidate = Image.open(CANDIDATE).convert("RGBA")
    original = Image.open(ROM_SPRITE).convert("RGBA")
    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    identity = {tuple(point) for point in masks["1:22"]}

    # The candidate was generated from only the ROM sprite and current mask.
    # Lock the enlarged logical cells, sample the full canvas once, then put
    # the user's exact native identity pixels back.  No prior Hero equipment
    # pixels participate in this build.
    selected = lock_high_resolution_identity(candidate, original, identity)
    sampled, grid_uniformity = strict_cell_sample(selected)
    image = fresh_native_hero(original, identity)
    image, palette_remapped = limit_visible_palette(image, identity)

    palette = visible_palette(image)
    empty_rows = [
        y for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    identity_match = sum(
        image.getpixel(point) == original.getpixel(point)
        for point in identity
    )
    pure_black = (0, 0, 0, 255) in image.getdata()
    magenta = any(
        color[3] and color[0] > 200 and color[2] > 200 and color[1] < 80
        for color in image.getdata()
    )
    accepted = (
        identity_match == len(identity)
        and len(palette) <= 15
        and not empty_rows
        and not empty_columns
        and not pure_black
        and not magenta
    )
    if not accepted:
        raise ValueError(
            "invalid fresh Hero: "
            f"identity={identity_match}/{len(identity)}, colors={len(palette)}, "
            f"rows={empty_rows}, columns={empty_columns}, "
            f"black={pure_black}, magenta={magenta}"
        )

    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    selected_dir = OUTPUT / "selected-sources"
    for directory in (logical_dir, preview_dir, selected_dir):
        directory.mkdir(parents=True, exist_ok=True)
    selected.save(selected_dir / "22-hero-ai.png", optimize=True)
    image.save(OUTPUT / "22-hero.png", optimize=True)
    image.save(logical_dir / "22-hero.png", optimize=True)
    image.resize((512, 512), Image.Resampling.NEAREST).save(
        preview_dir / "22-hero.png", optimize=True
    )

    comparison = Image.new("RGBA", (768, 288), (210, 210, 210, 255))
    draw = ImageDraw.Draw(comparison)
    for index, (label, sprite) in enumerate((
        ("ROM identity", original),
        ("fresh AI sample", sampled),
        ("fresh AI + exact face", image),
    )):
        comparison.alpha_composite(
            sprite.resize((256, 256), Image.Resampling.NEAREST),
            (index * 256, 32),
        )
        draw.text((index * 256 + 8, 8), label, fill=(24, 24, 24, 255))
    comparison.save(OUTPUT / "elwin-hero-v5-comparison.png", optimize=True)

    report = {
        "source": str(CANDIDATE.relative_to(ROOT)),
        "source_size": list(candidate.size),
        "native_size": list(image.size),
        "input_policy": "ROM sprite + current identity mask only; no prior AI Hero",
        "mode": "whole-canvas fixed 16-cell sampling",
        "grid_uniformity": round(grid_uniformity, 6),
        "identity_match": identity_match,
        "identity_pixel_count": len(identity),
        "visible_color_count": len(palette),
        "palette": palette,
        "palette_remapped_pixels": palette_remapped,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black": pure_black,
        "magenta_contamination": magenta,
        "accepted": accepted,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
