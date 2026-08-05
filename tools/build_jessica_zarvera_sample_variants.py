#!/usr/bin/env python3
"""Build five native-16 Jessica Zarvera samples from fresh AI concepts.

The AI images are visual sketches only.  Every logical sprite below is
repixelled with explicit 16x16 coordinates, then Jessica's current 73-pixel
ROM identity is restored at its unshifted source coordinates.  The aggregate
asset builder performs Jessica's final +1 x translation later.
"""

from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    load_identity_mask_overrides,
    protected_eye_points,
)
from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)


OUTPUT = (
    ROOT
    / "docs/assets/ai-class-source/latest/sample-class-variants-v1/"
    "jessica-zarvera"
)
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
WHITE = (255, 255, 255, 255)
SILVER = (146, 146, 146, 255)
GOLD = (255, 182, 0, 255)
WOOD = (109, 73, 36, 255)
PURPLE_DARK = (73, 0, 109, 255)
PURPLE = (146, 36, 182, 255)
LAVENDER = (219, 109, 255, 255)
SKIN = (219, 182, 109, 255)
RESAMPLING = getattr(Image, "Resampling", Image)


def rect(x0: int, y0: int, x1: int, y1: int) -> set[tuple[int, int]]:
    return {
        (x, y)
        for y in range(y0, y1 + 1)
        for x in range(x0, x1 + 1)
    }


def paint(
    image: Image.Image,
    points: set[tuple[int, int]],
    color: tuple[int, int, int, int],
) -> None:
    for point in points:
        image.putpixel(point, color)


def variant_01() -> Image.Image:
    """Long right-side vertical spear and a broad left purple cape."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Complete spear: leaf head, gold collar, shaft, and bottom ferrule.
    paint(image, {(14, 0), (13, 1), (14, 1), (15, 1), (13, 2), (14, 2), (15, 2)}, INK)
    paint(image, {(14, 0), (14, 1), (13, 2)}, WHITE)
    paint(image, {(15, 2), (14, 2)}, SILVER)
    paint(image, {(13, 3), (14, 3), (15, 3)}, GOLD)
    paint(image, {(14, y) for y in range(4, 15)}, WOOD)
    paint(image, {(15, y) for y in range(4, 16)}, INK)
    paint(image, {(13, 15), (14, 15)}, GOLD)

    # Left cape, silver shoulders, arms, and two readable hands.
    paint(image, rect(0, 8, 5, 14), INK)
    paint(image, rect(1, 9, 4, 13), PURPLE_DARK)
    paint(image, {(0, 10), (1, 10), (1, 11), (2, 11), (1, 12), (2, 12), (2, 13)}, PURPLE)
    paint(image, {(0, 13), (1, 13), (1, 14), (2, 14)}, LAVENDER)
    paint(image, rect(3, 7, 6, 9) | rect(9, 7, 13, 9), INK)
    paint(image, {(3, 8), (4, 8), (5, 8), (10, 8), (11, 8), (12, 8)}, SILVER)
    paint(image, {(4, 9), (5, 9), (10, 9), (11, 9), (12, 9)}, WHITE)
    paint(image, {(3, 9), (6, 9), (9, 9), (13, 9)}, GOLD)
    paint(image, rect(3, 10, 5, 12) | rect(11, 9, 13, 11), PURPLE)
    paint(image, {(4, 12), (13, 9)}, SKIN)

    # Closed armor/robe body and separated boots.
    paint(image, rect(5, 9, 11, 14), INK)
    paint(image, rect(6, 10, 10, 14), PURPLE_DARK)
    paint(image, {(6, 10), (10, 10), (6, 11), (10, 11), (6, 13), (10, 13)}, PURPLE)
    paint(image, {(7, 10), (8, 10), (9, 10), (7, 11), (9, 11)}, WHITE)
    paint(image, {(8, 11), (8, 12), (7, 13), (8, 13), (9, 13)}, GOLD)
    paint(image, {(6, 14), (7, 14), (9, 14), (10, 14)}, SILVER)
    paint(image, rect(4, 15, 7, 15) | rect(9, 15, 12, 15), INK)
    paint(image, {(5, 15), (6, 15), (10, 15), (11, 15)}, SILVER)
    return image


def variant_02() -> Image.Image:
    """Diagonal throwing spear with compact light armor."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Stair-stepped lower-left to upper-right javelin, routed below the face.
    shaft = {
        (0, 15), (0, 14), (1, 14), (1, 13), (2, 13), (2, 12),
        (3, 12), (3, 11), (4, 11), (4, 10), (5, 10), (5, 9),
        (6, 9), (7, 9), (8, 9), (9, 8), (10, 8), (10, 7),
        (11, 7), (11, 6), (12, 6), (12, 5), (13, 5), (13, 4),
    }
    paint(image, shaft, WOOD)
    paint(image, {(0, 15), (1, 14), (2, 13), (3, 12), (4, 11), (5, 10), (6, 9),
                  (8, 9), (10, 8), (11, 7), (12, 6), (13, 5)}, INK)
    paint(image, {(14, 2), (15, 2), (13, 3), (14, 3), (15, 3), (13, 4), (14, 4), (15, 4)}, INK)
    paint(image, {(15, 2), (14, 3), (15, 3)}, WHITE)
    paint(image, {(13, 3), (14, 4)}, SILVER)
    paint(image, {(13, 4), (13, 5)}, GOLD)

    # Short coat and lighter silver breastplate.
    paint(image, rect(2, 8, 5, 11) | rect(10, 7, 13, 11), INK)
    paint(image, {(2, 9), (3, 9), (4, 9), (10, 8), (11, 8), (12, 8)}, SILVER)
    paint(image, {(3, 10), (4, 10), (10, 9), (11, 9)}, WHITE)
    paint(image, {(2, 10), (5, 9), (12, 9), (13, 9)}, GOLD)
    paint(image, {(4, 11), (10, 8)}, SKIN)
    paint(image, rect(4, 9, 11, 13), INK)
    paint(image, rect(5, 10, 10, 12), SILVER)
    paint(image, {(5, 10), (10, 10), (5, 12), (10, 12)}, PURPLE)
    paint(image, {(6, 10), (7, 10), (8, 10), (9, 10)}, WHITE)
    paint(image, {(7, 11), (8, 11), (7, 12), (8, 12)}, GOLD)
    paint(image, {(4, 13), (5, 13), (6, 13), (9, 13), (10, 13), (11, 13)}, PURPLE_DARK)
    paint(image, {(3, 13), (4, 14), (5, 14), (10, 14), (11, 14), (12, 13)}, PURPLE)
    paint(image, rect(3, 15, 6, 15) | rect(9, 15, 12, 15), INK)
    paint(image, {(4, 15), (5, 15), (10, 15), (11, 15)}, SILVER)
    return image


def variant_03() -> Image.Image:
    """Closed robe with a broad spearhead projecting to the right."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Broad cape and ceremonial robe.
    paint(image, rect(0, 8, 5, 14), INK)
    paint(image, rect(1, 9, 4, 13), PURPLE_DARK)
    paint(image, {(0, 10), (1, 10), (1, 11), (2, 11), (1, 12), (2, 12), (2, 13)}, PURPLE)
    paint(image, {(0, 13), (1, 13), (1, 14), (2, 14)}, LAVENDER)
    paint(image, rect(3, 7, 12, 10), INK)
    paint(image, {(3, 8), (4, 8), (5, 8), (10, 8), (11, 8), (12, 8)}, SILVER)
    paint(image, {(4, 9), (5, 9), (10, 9), (11, 9)}, WHITE)
    paint(image, {(3, 9), (6, 9), (9, 9), (12, 9)}, GOLD)
    paint(image, rect(3, 10, 5, 12), PURPLE)
    paint(image, {(4, 11), (10, 9)}, SKIN)

    paint(image, rect(4, 9, 11, 15), INK)
    paint(image, rect(5, 10, 10, 14), PURPLE_DARK)
    paint(image, {(5, 10), (10, 10), (5, 11), (10, 11), (5, 13), (10, 13)}, PURPLE)
    paint(image, {(6, 10), (7, 10), (8, 10), (9, 10), (6, 11), (9, 11)}, WHITE)
    paint(image, {(7, 11), (8, 11), (7, 12), (8, 12), (7, 13), (8, 13)}, GOLD)
    paint(image, {(5, 14), (6, 14), (9, 14), (10, 14)}, LAVENDER)
    paint(image, rect(3, 15, 7, 15) | rect(8, 15, 12, 15), INK)
    paint(image, {(5, 15), (6, 15), (9, 15), (10, 15)}, SILVER)

    # Right-projecting spear: hand/shaft, full leaf point, no clipping.
    paint(image, {(9, 9), (10, 9), (11, 9), (12, 9)}, WOOD)
    paint(image, {(11, 8), (12, 8), (13, 8), (14, 8), (15, 8),
                  (12, 7), (13, 7), (14, 7), (13, 6),
                  (12, 9), (13, 9), (14, 9), (15, 9)}, INK)
    paint(image, {(13, 7), (14, 8), (15, 8), (14, 9), (15, 9)}, WHITE)
    paint(image, {(12, 8), (13, 8), (13, 9)}, SILVER)
    paint(image, {(11, 8), (11, 9), (12, 9)}, GOLD)
    return image


def variant_04() -> Image.Image:
    """Two-handed polearm with oversized symmetrical pauldrons."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Left-of-center polearm remains complete and joins both hands.
    paint(image, {(13, 0), (12, 1), (13, 1), (14, 1), (12, 2), (13, 2), (14, 2)}, INK)
    paint(image, {(13, 0), (13, 1), (12, 2)}, WHITE)
    paint(image, {(14, 2), (13, 2)}, SILVER)
    paint(image, {(12, 3), (13, 3), (14, 3)}, GOLD)
    paint(image, {(13, y) for y in range(4, 16)}, WOOD)
    paint(image, {(14, y) for y in range(4, 16)}, INK)

    # Wide shoulders occupy both sides; hands stack on the same shaft.
    paint(image, rect(0, 7, 5, 10) | rect(9, 7, 15, 10), INK)
    paint(image, {(0, 8), (1, 8), (2, 8), (3, 8), (4, 8),
                  (10, 8), (11, 8), (12, 8), (14, 8), (15, 8)}, SILVER)
    paint(image, {(1, 9), (2, 9), (3, 9), (11, 9), (12, 9), (14, 9)}, WHITE)
    paint(image, {(0, 9), (4, 9), (5, 9), (9, 9), (10, 9), (15, 9)}, GOLD)
    paint(image, rect(1, 10, 4, 13) | rect(10, 10, 15, 13), PURPLE_DARK)
    paint(image, {(1, 10), (2, 10), (3, 10), (11, 10), (12, 10), (15, 10)}, PURPLE)
    paint(image, {(12, 9), (12, 11)}, SKIN)

    paint(image, rect(4, 9, 11, 14), INK)
    paint(image, rect(5, 10, 10, 14), PURPLE_DARK)
    paint(image, {(5, 10), (10, 10), (5, 11), (10, 11), (5, 13), (10, 13)}, PURPLE)
    paint(image, {(6, 10), (7, 10), (8, 10), (9, 10)}, SILVER)
    paint(image, {(7, 11), (8, 11), (7, 12), (8, 12)}, WHITE)
    paint(image, {(6, 11), (9, 11), (7, 13), (8, 13)}, GOLD)
    paint(image, {(5, 14), (6, 14), (9, 14), (10, 14)}, LAVENDER)
    paint(image, rect(3, 15, 7, 15) | rect(8, 15, 12, 15), INK)
    paint(image, {(5, 15), (6, 15), (9, 15), (10, 15)}, SILVER)
    return image


def variant_05() -> Image.Image:
    """Royal spear guard with gold tabard and a short cape."""
    image = Image.new("RGBA", (16, 16), TRANSPARENT)

    # Slender ceremonial spear on the right.
    paint(image, {(14, 0), (13, 1), (14, 1), (15, 1), (13, 2), (14, 2), (15, 2)}, INK)
    paint(image, {(14, 0), (14, 1), (13, 2)}, WHITE)
    paint(image, {(15, 2), (14, 2)}, SILVER)
    paint(image, {(13, 3), (14, 3), (15, 3)}, GOLD)
    paint(image, {(14, y) for y in range(4, 16)}, WOOD)
    paint(image, {(15, y) for y in range(4, 16)}, INK)

    # Compact gold-edged armor and short cape ending above the knee.
    paint(image, rect(2, 7, 6, 10) | rect(9, 7, 13, 10), INK)
    paint(image, {(2, 8), (3, 8), (4, 8), (5, 8), (10, 8), (11, 8), (12, 8)}, SILVER)
    paint(image, {(3, 9), (4, 9), (10, 9), (11, 9)}, WHITE)
    paint(image, {(2, 9), (5, 9), (6, 9), (9, 9), (12, 9), (13, 9)}, GOLD)
    paint(image, rect(1, 9, 4, 12), PURPLE_DARK)
    paint(image, {(0, 10), (1, 10), (1, 11), (2, 11), (2, 12), (3, 12)}, PURPLE)
    paint(image, {(0, 11), (1, 12)}, LAVENDER)
    paint(image, rect(11, 9, 13, 11), PURPLE)
    paint(image, {(12, 10), (13, 9)}, SKIN)

    paint(image, rect(4, 9, 11, 14), INK)
    paint(image, rect(5, 10, 10, 14), PURPLE_DARK)
    paint(image, {(5, 10), (10, 10), (5, 11), (10, 11), (5, 13), (10, 13)}, PURPLE)
    paint(image, {(6, 10), (7, 10), (8, 10), (9, 10)}, SILVER)
    paint(image, {(7, 11), (8, 11), (7, 12), (8, 12)}, WHITE)
    paint(image, {(6, 11), (9, 11), (6, 12), (9, 12), (7, 13), (8, 13)}, GOLD)
    paint(image, {(5, 14), (6, 14), (9, 14), (10, 14)}, PURPLE)
    paint(image, rect(3, 15, 7, 15) | rect(8, 15, 12, 15), INK)
    paint(image, {(5, 15), (6, 15), (9, 15), (10, 15)}, SILVER)
    return image


BUILDERS = {
    "01": variant_01,
    "02": variant_02,
    "03": variant_03,
    "04": variant_04,
    "05": variant_05,
}


def component_sizes(image: Image.Image) -> list[int]:
    active = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3]
    }
    sizes: list[int] = []
    while active:
        queue = deque([active.pop()])
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in active:
                    active.remove(neighbor)
                    queue.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def validate(
    image: Image.Image,
    original: Image.Image,
    identity: set[tuple[int, int]],
) -> dict[str, object]:
    identity_match = sum(
        image.getpixel(point) == original.getpixel(point)
        for point in identity
    )
    palette = Counter(color for color in image.getdata() if color[3])
    empty_rows = [
        y for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    center_holes = [
        [x, y]
        for y in range(10, 14)
        for x in range(6, 10)
        if not image.getpixel((x, y))[3]
    ]
    pure_black = (0, 0, 0, 255) in palette
    magenta = any(
        color[0] > 200 and color[2] > 200 and color[1] < 80
        for color in palette
    )
    components = component_sizes(image)
    return {
        "identity_match": identity_match,
        "identity_pixel_count": len(identity),
        "visible_color_count": len(palette),
        "palette": [
            "#{:02x}{:02x}{:02x}".format(*color[:3])
            for color, _ in palette.most_common()
        ],
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "center_holes": center_holes,
        "pure_black": pure_black,
        "magenta_contamination": magenta,
        "connected_components": components,
        "accepted": (
            identity_match == len(identity)
            and len(palette) <= 15
            and not empty_rows
            and not empty_columns
            and not center_holes
            and not pure_black
            and not magenta
            and len(components) == 1
        ),
    }


def write_contact() -> None:
    canvas = Image.new("RGBA", (5 * 256, 290), (210, 210, 210, 255))
    draw = ImageDraw.Draw(canvas)
    for index, key in enumerate(BUILDERS):
        image = Image.open(OUTPUT / "logical16" / f"{key}.png").convert("RGBA")
        canvas.alpha_composite(
            image.resize((256, 256), RESAMPLING.NEAREST),
            (index * 256, 34),
        )
        draw.text((index * 256 + 8, 8), f"Jessica Zarvera {key}", fill=INK)
    canvas.save(OUTPUT / "all-logical16-variants.png", optimize=True)


def write_ai_contact() -> None:
    """Place the five independent AI concepts on one neutral comparison board."""
    canvas = Image.new("RGBA", (5 * 256, 290), (210, 210, 210, 255))
    draw = ImageDraw.Draw(canvas)
    for index, key in enumerate(BUILDERS):
        image = Image.open(OUTPUT / "ai" / f"{key}.png").convert("RGBA")
        alpha = image.getchannel("A")
        bbox = alpha.getbbox()
        if bbox:
            image = image.crop(bbox)
        fitted = ImageOps.contain(image, (240, 240), method=RESAMPLING.LANCZOS)
        x = index * 256 + (256 - fitted.width) // 2
        y = 42 + (240 - fitted.height) // 2
        canvas.alpha_composite(fitted, (x, y))
        draw.text((index * 256 + 8, 8), f"Jessica Zarvera AI {key}", fill=INK)
    canvas.save(OUTPUT / "all-ai-variants.png", optimize=True)


def write_combined_contact() -> None:
    """Show each accepted AI concept directly above its native 16x16 redraw."""
    canvas = Image.new("RGBA", (5 * 256, 570), (210, 210, 210, 255))
    draw = ImageDraw.Draw(canvas)
    for index, key in enumerate(BUILDERS):
        ai_image = Image.open(OUTPUT / "ai" / f"{key}.png").convert("RGBA")
        bbox = ai_image.getchannel("A").getbbox()
        if bbox:
            ai_image = ai_image.crop(bbox)
        fitted = ImageOps.contain(ai_image, (232, 232), method=RESAMPLING.LANCZOS)
        ai_x = index * 256 + (256 - fitted.width) // 2
        ai_y = 34 + (232 - fitted.height) // 2
        canvas.alpha_composite(fitted, (ai_x, ai_y))

        logical = Image.open(OUTPUT / "logical16" / f"{key}.png").convert("RGBA")
        logical = logical.resize((256, 256), RESAMPLING.NEAREST)
        canvas.alpha_composite(logical, (index * 256, 304))
        draw.text((index * 256 + 8, 8), f"Variant {key}: AI concept", fill=INK)
        draw.text((index * 256 + 8, 280), "Native logical 16x16", fill=INK)
    canvas.save(OUTPUT / "all-ai-and-logical16-variants.png", optimize=True)


def build() -> dict[str, object]:
    rom = DEFAULT_ROM.read_bytes()
    sprite_id = commander_sprite_map(rom, 10)[0x26]
    original = render_sprite(rom, sprite_id, 1)
    identity = (
        set(load_identity_mask_overrides()[(10, 0x26)])
        | protected_eye_points(original)
    )
    if len(identity) != 73:
        raise ValueError(f"expected Jessica Zarvera 73-pixel identity, got {len(identity)}")

    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, object]] = []
    for key, builder in BUILDERS.items():
        image = builder()
        for point in identity:
            image.putpixel(point, original.getpixel(point))
        logical_path = logical_dir / f"{key}.png"
        preview_path = preview_dir / f"{key}.png"
        image.save(logical_path, optimize=True)
        image.resize((256, 256), RESAMPLING.NEAREST).save(
            preview_path,
            optimize=True,
        )
        reports.append({
            "variant": key,
            "ai_source": f"ai/{key}.png",
            "logical16": f"logical16/{key}.png",
            "preview_16x": f"previews/{key}.png",
            "identity_coordinates": "unshifted; aggregate applies +1 x later",
            **validate(image, original, identity),
        })

    write_contact()
    write_ai_contact()
    write_combined_contact()
    report = {
        "version": 1,
        "mode": "fresh built-in imagegen concepts; hand-repixelled native logical16",
        "inputs": [
            "jessica-zarvera-summoner-ai-v1-fresh/references/10-26-zarvera-rom-original-32x.png",
            "jessica-zarvera-summoner-ai-v1-fresh/references/10-26-jessica-identity-only-32x.png",
        ],
        "previous_ai_inputs": [],
        "identity_pixel_count": len(identity),
        "aggregate_identity_translation": [1, 0],
        "all_accepted": all(bool(row["accepted"]) for row in reports),
        "variants": reports,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    result = build()
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["all_accepted"] else 1)
