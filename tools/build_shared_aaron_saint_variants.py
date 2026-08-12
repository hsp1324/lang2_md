#!/usr/bin/env python3
"""Share Aaron's user-edited Saint equipment with every Saint commander."""

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
    load_ai_design_overrides,
    load_identity_mask_overrides,
    protected_eye_points,
)
from tools.scenario_data import KOREAN_NAME_BY_ID


CLASS_ID = 0x17
SOURCE_COMMANDER = 8
TARGETS = (1, 2, 3, 4, 5, 6, 7, 8, 10)
SOURCE_DIR = (
    ROOT / "assets/class-sprites/source/latest/shared-saint-aaron-v1"
)
ROM_SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders"
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
RESAMPLING = getattr(Image, "Resampling", Image)

AARON_CLOTH_DARK = (109, 36, 0, 255)
AARON_CLOTH_MAIN = (219, 146, 0, 255)
AARON_MAGIC_LIGHT = (109, 182, 255, 255)

# Dark cloth, main cloth, and the small magical highlight. Metal, skin, white
# vestments, and gold trim remain shared so the class still reads as Saint.
COLOR_SCHEMES = {
    1: {
        AARON_CLOTH_DARK: (109, 0, 0, 255),
        AARON_CLOTH_MAIN: (219, 0, 0, 255),
        AARON_MAGIC_LIGHT: (255, 109, 109, 255),
    },
    2: {
        AARON_CLOTH_DARK: (109, 0, 0, 255),
        AARON_CLOTH_MAIN: (219, 0, 0, 255),
        AARON_MAGIC_LIGHT: (255, 109, 109, 255),
    },
    3: {
        AARON_CLOTH_DARK: (0, 0, 219, 255),
        AARON_CLOTH_MAIN: (73, 109, 255, 255),
        AARON_MAGIC_LIGHT: (109, 219, 255, 255),
    },
    4: {
        AARON_CLOTH_DARK: (36, 36, 109, 255),
        AARON_CLOTH_MAIN: (0, 109, 146, 255),
        AARON_MAGIC_LIGHT: (109, 219, 255, 255),
    },
    5: {
        AARON_CLOTH_DARK: (36, 109, 0, 255),
        AARON_CLOTH_MAIN: (36, 182, 36, 255),
        AARON_MAGIC_LIGHT: (109, 219, 146, 255),
    },
    6: {
        AARON_CLOTH_DARK: (36, 109, 0, 255),
        AARON_CLOTH_MAIN: (36, 182, 36, 255),
        AARON_MAGIC_LIGHT: (109, 219, 146, 255),
    },
    7: {
        AARON_CLOTH_DARK: (0, 36, 182, 255),
        AARON_CLOTH_MAIN: (73, 109, 255, 255),
        AARON_MAGIC_LIGHT: (109, 219, 255, 255),
    },
    8: {},
    10: {
        AARON_CLOTH_DARK: (73, 36, 109, 255),
        AARON_CLOTH_MAIN: (146, 73, 182, 255),
        AARON_MAGIC_LIGHT: (219, 146, 255, 255),
    },
}


def visible_palette(image: Image.Image) -> list[str]:
    colors = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in colors.most_common()
    ]


def editor_master() -> Image.Image:
    designs = load_ai_design_overrides()
    entry = designs.get((SOURCE_COMMANDER, CLASS_ID))
    if entry is None:
        raise ValueError("Aaron Saint editor design 8:17 is missing")
    master = Image.new("RGBA", (16, 16), TRANSPARENT)
    master.putdata(entry["pixels"])
    return master


def validate(
    image: Image.Image,
    original: Image.Image,
    identity_points: set[tuple[int, int]],
) -> dict[str, object]:
    visible_identity = {
        point for point in identity_points if original.getpixel(point)[3]
    }
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
        for point in visible_identity
    )
    pure_black = sum(
        image.getpixel((x, y)) == (0, 0, 0, 255)
        for y in range(16)
        for x in range(16)
    )
    return {
        "identity_match": identity_match,
        "identity_pixel_count": len(visible_identity),
        "visible_color_count": len(palette),
        "palette": palette,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black_pixels": pure_black,
        "accepted": (
            identity_match == len(visible_identity)
            and len(palette) <= 15
            and not empty_rows
            and not empty_columns
            and pure_black == 0
        ),
    }


def write_comparison(reports: list[dict[str, object]]) -> None:
    columns = 3
    card_width = 280
    card_height = 310
    rows = (len(reports) + columns - 1) // columns
    canvas = Image.new(
        "RGB", (columns * card_width, rows * card_height), (18, 18, 18)
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, report in enumerate(reports):
        x = (index % columns) * card_width
        y = (index // columns) * card_height
        border = (70, 170, 90) if report["accepted"] else (210, 70, 70)
        draw.rectangle(
            (x + 5, y + 5, x + card_width - 6, y + card_height - 6),
            outline=border,
            width=2,
        )
        draw.text(
            (x + 12, y + 12),
            f"{report['commander_id']:02d} {report['commander_name']} SAINT",
            fill=(245, 245, 245),
            font=font,
        )
        draw.text(
            (x + 12, y + 28),
            (
                f"identity {report['identity_match']}/"
                f"{report['identity_pixel_count']} "
                f"colors {report['visible_color_count']}"
            ),
            fill=(180, 190, 180),
            font=font,
        )
        preview = Image.open(SOURCE_DIR / report["file"]).convert("RGBA")
        backdrop = Image.new("RGBA", (16, 16), (48, 48, 48, 255))
        backdrop.alpha_composite(preview)
        preview = backdrop.convert("RGB").resize(
            (240, 240), RESAMPLING.NEAREST
        )
        canvas.paste(preview, (x + 20, y + 52))
    canvas.save(SOURCE_DIR / "all-saint-variants.png", optimize=True)


def build_variants() -> dict[str, object]:
    logical_dir = SOURCE_DIR / "logical16"
    preview_dir = SOURCE_DIR / "previews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    masks = load_identity_mask_overrides()
    master = editor_master()
    source_original = Image.open(
        ROM_SPRITE_DIR / str(SOURCE_COMMANDER) / f"{CLASS_ID:02X}-p1.png"
    ).convert("RGBA")
    source_identity = (
        set(masks[(SOURCE_COMMANDER, CLASS_ID)])
        | protected_eye_points(source_original)
    )
    equipment = master.copy()
    for point in source_identity:
        if source_original.getpixel(point)[3]:
            equipment.putpixel(point, TRANSPARENT)

    reports: list[dict[str, object]] = []
    for commander_id in TARGETS:
        original = Image.open(
            ROM_SPRITE_DIR / str(commander_id) / f"{CLASS_ID:02X}-p1.png"
        ).convert("RGBA")
        if commander_id == SOURCE_COMMANDER:
            converted = master.copy()
            identity_points = source_identity
        else:
            prepared = equipment.copy()
            scheme = COLOR_SCHEMES[commander_id]
            for y in range(16):
                for x in range(16):
                    point = (x, y)
                    color = prepared.getpixel(point)
                    if color in scheme:
                        prepared.putpixel(point, scheme[color])
            manual_identity = masks.get((commander_id, CLASS_ID))
            restore_full_mask = manual_identity is not None
            converted, _, _, automatic_identity = (
                identity_locked_character_sprite(
                    prepared,
                    original,
                    [INK],
                    manual_identity,
                    preserve_generated_palette=True,
                    restore_transparent_locked_points=restore_full_mask,
                )
            )
            identity_points = (
                set(manual_identity)
                if manual_identity is not None
                else set(automatic_identity)
            ) | protected_eye_points(original)

            # Keep the three character-specific cloth roles distinct after
            # 4bpp fitting. Visible head pixels always win over equipment.
            requested_colors = set(scheme.values())
            visible_identity = {
                point
                for point in identity_points
                if original.getpixel(point)[3]
            }
            protected_identity = (
                set(identity_points)
                if restore_full_mask
                else visible_identity
            )
            for y in range(16):
                for x in range(16):
                    point = (x, y)
                    color = prepared.getpixel(point)
                    if point not in protected_identity and color in requested_colors:
                        converted.putpixel(point, color)

        output = logical_dir / f"{commander_id:02d}-{CLASS_ID:02X}.png"
        converted.save(output, optimize=True)
        converted.resize((512, 512), RESAMPLING.NEAREST).save(
            preview_dir / output.name,
            optimize=True,
        )
        report = {
            "commander_id": commander_id,
            "commander_name": KOREAN_NAME_BY_ID[commander_id],
            "class_id": f"{CLASS_ID:02X}",
            "class_name": "SAINT",
            "file": str(output.relative_to(SOURCE_DIR)),
            **validate(converted, original, identity_points),
        }
        reports.append(report)

    write_comparison(reports)
    result = {
        "version": 2,
        "source": "editor/ai_class_design_overrides.json 8:17",
        "silhouette_policy": (
            "Aaron's user-edited Saint vestment, staff, and equipment "
            "coordinates are shared; each target restores its own visible "
            "head, face, eyes, and character-specific cloth colors"
        ),
        "all_accepted": all(report["accepted"] for report in reports),
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
