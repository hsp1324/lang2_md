#!/usr/bin/env python3
"""Recolor Lester's user-edited Archmage for every Archmage commander."""

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
    / "docs/assets/ai-class-source/latest/shared-archmage-lester-v1"
)
MASTER_PATH = SOURCE_DIR / "master/lester-14-user-edited.png"
MANIFEST_PATH = ROOT / "editor/static/ai-class-sprites/manifest.json"
SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders"
ARCHMAGE_CLASS_ID = 0x14
COMMANDER_IDS = (1, 2, 3, 4, 5, 8, 9, 10)
TRANSPARENT = (0, 0, 0, 0)
RESAMPLING = getattr(Image, "Resampling", Image)

INK = (36, 36, 36, 255)
MASTER_BLUE = (36, 73, 219, 255)
MASTER_GOLD = (255, 182, 36, 255)
MASTER_CRIMSON = (146, 0, 36, 255)
MASTER_DARK_RED = (109, 0, 0, 255)
MASTER_BRONZE = (182, 109, 36, 255)
MASTER_GOLD_LIGHT = (255, 219, 146, 255)

# The silhouette stays byte-identical to Lester's edited equipment. Only the
# six role colors change; skin, white/silver, gray, and ink remain shared.
COLOR_SCHEMES = {
    1: {
        MASTER_BLUE: (0, 73, 219, 255),
        MASTER_GOLD: (255, 182, 0, 255),
        MASTER_CRIMSON: (146, 0, 0, 255),
        MASTER_DARK_RED: (109, 0, 0, 255),
        MASTER_BRONZE: (182, 109, 0, 255),
        MASTER_GOLD_LIGHT: (255, 219, 146, 255),
    },
    2: {
        MASTER_BLUE: (219, 0, 0, 255),
        MASTER_GOLD: (255, 182, 0, 255),
        MASTER_CRIMSON: (109, 0, 0, 255),
        MASTER_DARK_RED: (73, 0, 0, 255),
        MASTER_BRONZE: (182, 73, 36, 255),
        MASTER_GOLD_LIGHT: (255, 219, 146, 255),
    },
    3: {
        MASTER_BLUE: (0, 73, 219, 255),
        MASTER_GOLD: (255, 182, 0, 255),
        MASTER_CRIMSON: (36, 73, 146, 255),
        MASTER_DARK_RED: (0, 0, 109, 255),
        MASTER_BRONZE: (146, 109, 36, 255),
        MASTER_GOLD_LIGHT: (255, 219, 146, 255),
    },
    4: {
        MASTER_BLUE: (219, 0, 0, 255),
        MASTER_GOLD: (219, 182, 109, 255),
        MASTER_CRIMSON: (109, 0, 0, 255),
        MASTER_DARK_RED: (73, 73, 109, 255),
        MASTER_BRONZE: (146, 73, 36, 255),
        MASTER_GOLD_LIGHT: (255, 255, 255, 255),
    },
    5: {
        MASTER_BLUE: (36, 219, 36, 255),
        MASTER_GOLD: (255, 255, 255, 255),
        MASTER_CRIMSON: (73, 73, 109, 255),
        MASTER_DARK_RED: (36, 109, 0, 255),
        MASTER_BRONZE: (146, 146, 146, 255),
        MASTER_GOLD_LIGHT: (219, 219, 255, 255),
    },
    8: {
        MASTER_BLUE: (0, 0, 146, 255),
        MASTER_GOLD: (73, 146, 255, 255),
        MASTER_CRIMSON: (36, 73, 219, 255),
        MASTER_DARK_RED: (0, 0, 73, 255),
        MASTER_BRONZE: (73, 109, 255, 255),
        MASTER_GOLD_LIGHT: (146, 182, 255, 255),
    },
    9: {},
    10: {
        MASTER_BLUE: (219, 0, 0, 255),
        MASTER_GOLD: (255, 255, 255, 255),
        MASTER_CRIMSON: (109, 0, 0, 255),
        MASTER_DARK_RED: (36, 36, 36, 255),
        MASTER_BRONZE: (146, 73, 36, 255),
        MASTER_GOLD_LIGHT: (219, 182, 109, 255),
    },
}


def points_for(row: dict[str, object]) -> set[tuple[int, int]]:
    return {
        tuple(point)
        for point in row["identity_lock_points"]
    }


def visible_palette(image: Image.Image) -> list[str]:
    colors = Counter(
        color
        for color in image.getdata()
        if color[3]
    )
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in colors.most_common()
    ]


def build_variants() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    master = Image.open(MASTER_PATH).convert("RGBA")
    if master.size != (16, 16):
        raise ValueError("Lester Archmage master must be 16x16")
    master_row = manifest["commanders"]["9"]["classes"][
        str(ARCHMAGE_CLASS_ID)
    ]
    master_identity = points_for(master_row)

    logical_dir = SOURCE_DIR / "logical16"
    preview_dir = SOURCE_DIR / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []

    for commander_id in COMMANDER_IDS:
        commander = manifest["commanders"][str(commander_id)]
        row = commander["classes"][str(ARCHMAGE_CLASS_ID)]
        target_identity = points_for(row)
        original = Image.open(
            SPRITE_DIR
            / str(commander_id)
            / f"{ARCHMAGE_CLASS_ID:02X}-p1.png"
        ).convert("RGBA")
        scheme = COLOR_SCHEMES[commander_id]

        equipment = master.copy()
        for point in master_identity:
            equipment.putpixel(point, TRANSPARENT)
        for y in range(16):
            for x in range(16):
                point = (x, y)
                color = equipment.getpixel(point)
                if color in scheme:
                    equipment.putpixel(point, scheme[color])

        converted, _, _, _ = identity_locked_character_sprite(
            equipment,
            original,
            [INK],
            target_identity,
            preserve_generated_palette=True,
            restore_transparent_locked_points=False,
        )
        output_path = (
            logical_dir
            / f"{commander_id:02d}-{ARCHMAGE_CLASS_ID:02X}.png"
        )
        converted.save(output_path, optimize=True)
        converted.resize((512, 512), RESAMPLING.NEAREST).save(
            preview_dir
            / f"{commander_id:02d}-{ARCHMAGE_CLASS_ID:02X}.png",
            optimize=True,
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
        visible_identity = {
            point
            for point in target_identity
            if original.getpixel(point)[3]
        }
        identity_match = sum(
            converted.getpixel(point) == original.getpixel(point)
            for point in visible_identity
        )
        reports.append({
            "commander_id": commander_id,
            "commander_name": commander["name"],
            "class_id": f"{ARCHMAGE_CLASS_ID:02X}",
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
            "file": str(output_path.relative_to(SOURCE_DIR)),
            "accepted": (
                identity_match == len(visible_identity)
                and len(colors) <= 15
                and not empty_rows
                and not empty_columns
            ),
        })

    card_width = 300
    card_height = 340
    canvas = Image.new(
        "RGB",
        (card_width * 4, card_height * 2),
        (18, 18, 18),
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, report in enumerate(reports):
        x = (index % 4) * card_width
        y = (index // 4) * card_height
        color = (70, 170, 90) if report["accepted"] else (210, 70, 70)
        draw.rectangle(
            (x + 6, y + 6, x + card_width - 7, y + card_height - 7),
            outline=color,
            width=2,
        )
        draw.text(
            (x + 14, y + 14),
            f"{report['commander_id']:02d} {report['commander_name']} ARCHMAGE",
            fill=(245, 245, 245),
            font=font,
        )
        draw.text(
            (x + 14, y + 29),
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
        ).convert("RGB").resize((256, 256), RESAMPLING.NEAREST)
        canvas.paste(preview, (x + 22, y + 55))
    canvas.save(
        SOURCE_DIR / "all-archmage-variants.png",
        optimize=True,
    )

    result = {
        "version": 1,
        "source": str(MASTER_PATH.relative_to(SOURCE_DIR)),
        "silhouette_policy": (
            "Lester user-edited 16x16 equipment coordinates are shared; "
            "only role colors and each commander's identity mask differ"
        ),
        "all_accepted": all(row["accepted"] for row in reports),
        "classes": reports,
    }
    (SOURCE_DIR / "validation-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    report = build_variants()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
