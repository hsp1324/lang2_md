#!/usr/bin/env python3
"""Apply Elwin's High Lord equipment to eligible Lord classes."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    identity_locked_character_sprite,
)


SOURCE_DIR = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "shared-lord-elwin-high-lord-v1"
)
MASTER_PATH = (
    SOURCE_DIR / "master/elwin-0B-high-lord-user-approved.png"
)
MANIFEST_PATH = ROOT / "editor/static/ai-class-sprites/manifest.json"
SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders"
LORD_CLASS_ID = 0x04
MASTER_CLASS_ID = 0x0B
TARGETS = (1, 4, 6, 7, 8)
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
RESAMPLING = getattr(Image, "Resampling", Image)

MASTER_DARK_BLUE = (73, 73, 109, 255)
MASTER_RED = (109, 0, 0, 255)
MASTER_GOLD = (255, 182, 0, 255)

# Colors are sampled from each target's original Lord equipment palette.
COLOR_SCHEMES = {
    1: {
        MASTER_DARK_BLUE: MASTER_DARK_BLUE,
        MASTER_RED: (219, 0, 0, 255),
        MASTER_GOLD: MASTER_GOLD,
    },
    4: {
        MASTER_DARK_BLUE: (73, 73, 109, 255),
        MASTER_RED: (219, 0, 0, 255),
        MASTER_GOLD: (255, 182, 0, 255),
    },
    6: {
        MASTER_DARK_BLUE: (73, 73, 109, 255),
        MASTER_RED: (109, 0, 0, 255),
        MASTER_GOLD: (255, 182, 0, 255),
    },
    7: {
        MASTER_DARK_BLUE: (73, 73, 109, 255),
        MASTER_RED: (109, 0, 0, 255),
        MASTER_GOLD: (255, 182, 0, 255),
    },
    8: {
        MASTER_DARK_BLUE: (146, 146, 146, 255),
        MASTER_RED: (109, 109, 109, 255),
        MASTER_GOLD: (255, 255, 255, 255),
    },
}


def points_for(row: dict[str, object]) -> set[tuple[int, int]]:
    return {tuple(point) for point in row["identity_lock_points"]}


def visible_palette(image: Image.Image) -> list[str]:
    colors = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in colors.most_common()
    ]


def build_variants() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    master = Image.open(MASTER_PATH).convert("RGBA")
    master_row = manifest["commanders"]["1"]["classes"][
        str(MASTER_CLASS_ID)
    ]
    master_identity = points_for(master_row)
    logical_dir = SOURCE_DIR / "logical16"
    logical_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []

    for commander_id in TARGETS:
        commander = manifest["commanders"][str(commander_id)]
        row = commander["classes"][str(LORD_CLASS_ID)]
        if row["group_rank"] == 0:
            raise ValueError(
                f"{commander_id}:04 is a ROM-base Lord and cannot change"
            )
        target_identity = points_for(row)
        original = Image.open(
            SPRITE_DIR / str(commander_id) / "04-p1.png"
        ).convert("RGBA")
        equipment = master.copy()
        for point in master_identity:
            equipment.putpixel(point, TRANSPARENT)
        mapping = COLOR_SCHEMES[commander_id]
        for y in range(16):
            for x in range(16):
                color = equipment.getpixel((x, y))
                if color in mapping:
                    equipment.putpixel((x, y), mapping[color])
        converted, _, _, _ = identity_locked_character_sprite(
            equipment,
            original,
            [INK],
            target_identity,
            preserve_generated_palette=True,
            restore_transparent_locked_points=False,
        )
        # The accepted Elwin High Lord shield ends at column 14. Extend its
        # rounded outer edge by one logical pixel so the Lord variants use
        # the full 16-column canvas without stretching the whole sprite.
        for y in (10, 11, 12):
            converted.putpixel((15, y), converted.getpixel((14, y)))
        output_path = logical_dir / f"{commander_id:02d}-04.png"
        converted.save(output_path, optimize=True)

        visible_identity = {
            point
            for point in target_identity
            if original.getpixel(point)[3]
        }
        identity_match = sum(
            converted.getpixel(point) == original.getpixel(point)
            for point in visible_identity
        )
        colors = visible_palette(converted)
        empty_rows = [
            y
            for y in range(16)
            if not any(converted.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x
            for x in range(16)
            if not any(converted.getpixel((x, y))[3] for y in range(16))
        ]
        pure_black_pixels = sum(
            converted.getpixel((x, y)) == (0, 0, 0, 255)
            for y in range(16)
            for x in range(16)
        )
        reports.append({
            "commander_id": commander_id,
            "commander_name": commander["name"],
            "class_id": "04",
            "class_name": "LORD",
            "group_rank": row["group_rank"],
            "initial_class": {
                1: "파이터",
                4: "파이터",
                6: "파이터",
                7: "파이터",
                8: "파이터",
            }[commander_id],
            "identity_match": identity_match,
            "identity_pixel_count": len(visible_identity),
            "mask_pixel_count": len(target_identity),
            "equipment_priority_transparent_pixels": sum(
                converted.getpixel(point)[3] != 0
                for point in target_identity - visible_identity
            ),
            "visible_color_count": len(colors),
            "palette": colors,
            "empty_rows": empty_rows,
            "empty_columns": empty_columns,
            "pure_black_pixels": pure_black_pixels,
            "file": str(output_path.relative_to(SOURCE_DIR)),
            "accepted": (
                identity_match == len(visible_identity)
                and len(colors) <= 15
                and not empty_rows
                and not empty_columns
                and pure_black_pixels == 0
            ),
        })

    card_width = 300
    card_height = 340
    canvas = Image.new(
        "RGB",
        (card_width * len(reports), card_height),
        (18, 18, 18),
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, report in enumerate(reports):
        x = index * card_width
        color = (
            (70, 170, 90)
            if report["accepted"]
            else (210, 70, 70)
        )
        draw.rectangle(
            (x + 6, 6, x + card_width - 7, card_height - 7),
            outline=color,
            width=2,
        )
        draw.text(
            (x + 12, 12),
            (
                f"{report['commander_id']:02d} "
                f"{report['commander_name']} LORD"
            ),
            fill=(245, 245, 245),
            font=font,
        )
        draw.text(
            (x + 12, 27),
            (
                f"identity {report['identity_match']}/"
                f"{report['identity_pixel_count']} "
                f"colors {report['visible_color_count']}"
            ),
            fill=(180, 190, 180),
            font=font,
        )
        preview = Image.open(
            SOURCE_DIR / report["file"]
        ).convert("RGB").resize((270, 270), RESAMPLING.NEAREST)
        canvas.paste(preview, (x + 15, 50))
    comparison_path = SOURCE_DIR / "all-lord-variants.png"
    canvas.save(comparison_path, optimize=True)

    result = {
        "version": 1,
        "master": "master/elwin-0B-high-lord-user-approved.png",
        "master_class_id": "0B",
        "target_class_id": "04",
        "eligible_rule": (
            "Lord is redesigned only when it follows Fighter in the same "
            "shared sprite group"
        ),
        "excluded_rom_base_lords": [
            {"commander_id": 2, "name": "리아나", "initial": "클레릭"},
            {"commander_id": 3, "name": "라나", "initial": "클레릭"},
            {"commander_id": 5, "name": "헤인", "initial": "워록"},
            {"commander_id": 10, "name": "제시카", "initial": "워록"},
        ],
        "missing_lord_class": [
            {"commander_id": 9, "name": "레스터"},
        ],
        "all_accepted": all(row["accepted"] for row in reports),
        "classes": reports,
    }
    (SOURCE_DIR / "validation-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> int:
    report = build_variants()
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
