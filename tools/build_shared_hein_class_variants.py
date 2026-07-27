#!/usr/bin/env python3
"""Share Hein's approved Priest, Mage, and High Priest silhouettes."""

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
    ROOT / "docs/assets/ai-class-source/latest/shared-hein-classes-v1"
)
MANIFEST_PATH = ROOT / "editor/static/ai-class-sprites/manifest.json"
SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders"
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
RESAMPLING = getattr(Image, "Resampling", Image)

CLASS_SPECS = {
    0x11: {
        "name": "PRIEST",
        "master": "master/hein-11-priest-user-approved.png",
        "targets": (2, 3, 5, 7, 10),
        "role_colors": (
            (36, 146, 36, 255),
            (73, 109, 255, 255),
            (109, 219, 146, 255),
        ),
    },
    0x13: {
        "name": "MAGE",
        "master": "master/hein-13-mage-user-approved.png",
        "targets": (1, 2, 3, 4, 5, 8, 9, 10),
        "role_colors": (
            (73, 73, 109, 255),
            (36, 73, 255, 255),
            (73, 109, 255, 255),
            (109, 219, 255, 255),
        ),
    },
    0x16: {
        "name": "HIGH PRIEST",
        "master": "master/hein-16-high-priest-user-approved.png",
        "targets": (2, 3, 5, 7, 10),
        "role_colors": (
            (73, 73, 109, 255),
            (0, 0, 146, 255),
            (73, 73, 219, 255),
        ),
    },
}

# Dark, main, and highlight colors sampled from each target's original class
# sprite. The approved Hein masters remain byte-identical.
CLASS_COMMANDER_SCHEMES = {
    (0x11, 2): ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255)),
    (0x11, 3): ((0, 0, 109, 255), (0, 0, 219, 255), (73, 109, 255, 255)),
    (0x11, 7): None,
    (0x11, 10): ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255)),
    (0x13, 1): ((73, 73, 109, 255), (0, 0, 219, 255), (73, 109, 255, 255)),
    (0x13, 2): ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255)),
    (0x13, 3): ((0, 0, 109, 255), (0, 0, 219, 255), (73, 109, 255, 255)),
    (0x13, 4): ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255)),
    (0x13, 8): ((0, 0, 109, 255), (36, 73, 219, 255), (73, 146, 255, 255)),
    (0x13, 9): ((73, 73, 109, 255), (146, 146, 146, 255), (219, 182, 109, 255)),
    (0x13, 10): ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255)),
    (0x16, 2): ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255)),
    (0x16, 3): ((0, 0, 109, 255), (0, 0, 219, 255), (73, 109, 255, 255)),
    (0x16, 7): ((36, 109, 0, 255), (0, 0, 219, 255), (36, 219, 36, 255)),
    (0x16, 10): ((109, 0, 0, 255), (219, 0, 0, 255), (255, 109, 109, 255)),
}


def points_for(row: dict[str, object]) -> set[tuple[int, int]]:
    return {tuple(point) for point in row["identity_lock_points"]}


def visible_palette(image: Image.Image) -> list[str]:
    colors = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in colors.most_common()
    ]


def role_mapping(
    class_id: int,
    commander_id: int,
) -> dict[tuple[int, int, int, int], tuple[int, int, int, int]]:
    if commander_id == 5:
        return {}
    source_colors = CLASS_SPECS[class_id]["role_colors"]
    scheme = CLASS_COMMANDER_SCHEMES[(class_id, commander_id)]
    if scheme is None:
        return {}
    dark, main, light = scheme
    if len(source_colors) == 3:
        return dict(zip(source_colors, (main, main, light)))
    return dict(zip(source_colors, (dark, main, main, light)))


def build_variants() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    logical_dir = SOURCE_DIR / "logical16"
    logical_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []

    for class_id, spec in CLASS_SPECS.items():
        master = Image.open(SOURCE_DIR / spec["master"]).convert("RGBA")
        master_row = manifest["commanders"]["5"]["classes"][
            str(class_id)
        ]
        master_identity = points_for(master_row)
        for commander_id in spec["targets"]:
            commander = manifest["commanders"][str(commander_id)]
            row = commander["classes"][str(class_id)]
            if not row["redesigned"]:
                raise ValueError(
                    f"{commander_id}:{class_id:02X} is a ROM-base class"
                )
            target_identity = points_for(row)
            original = Image.open(
                SPRITE_DIR
                / str(commander_id)
                / f"{class_id:02X}-p1.png"
            ).convert("RGBA")
            equipment = master.copy()
            for point in master_identity:
                equipment.putpixel(point, TRANSPARENT)
            mapping = role_mapping(class_id, commander_id)
            for y in range(16):
                for x in range(16):
                    point = (x, y)
                    color = equipment.getpixel(point)
                    if color in mapping:
                        equipment.putpixel(point, mapping[color])
            converted, _, _, _ = identity_locked_character_sprite(
                equipment,
                original,
                [INK],
                target_identity,
                preserve_generated_palette=True,
                restore_transparent_locked_points=False,
            )
            output_path = (
                logical_dir / f"{commander_id:02d}-{class_id:02X}.png"
            )
            converted.save(output_path, optimize=True)
            colors = visible_palette(converted)
            empty_rows = [
                y for y in range(16)
                if not any(
                    converted.getpixel((x, y))[3] for x in range(16)
                )
            ]
            empty_columns = [
                x for x in range(16)
                if not any(
                    converted.getpixel((x, y))[3] for y in range(16)
                )
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
                "class_id": f"{class_id:02X}",
                "class_name": spec["name"],
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

    columns = 5
    card_width = 270
    card_height = 305
    rows = (len(reports) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (columns * card_width, rows * card_height),
        (18, 18, 18),
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, report in enumerate(reports):
        x = (index % columns) * card_width
        y = (index // columns) * card_height
        color = (70, 170, 90) if report["accepted"] else (210, 70, 70)
        draw.rectangle(
            (x + 5, y + 5, x + card_width - 6, y + card_height - 6),
            outline=color,
            width=2,
        )
        draw.text(
            (x + 12, y + 12),
            (
                f"{report['commander_id']:02d} "
                f"{report['commander_name']} {report['class_name']}"
            ),
            fill=(245, 245, 245),
            font=font,
        )
        draw.text(
            (x + 12, y + 27),
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
        ).convert("RGB").resize((240, 240), RESAMPLING.NEAREST)
        canvas.paste(preview, (x + 15, y + 50))
    canvas.save(
        SOURCE_DIR / "all-hein-template-variants.png",
        optimize=True,
    )

    result = {
        "version": 1,
        "masters": {
            f"{class_id:02X}": spec["master"]
            for class_id, spec in CLASS_SPECS.items()
        },
        "silhouette_policy": (
            "Hein's user-approved equipment coordinates are shared; "
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
