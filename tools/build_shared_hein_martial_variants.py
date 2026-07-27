#!/usr/bin/env python3
"""Share Hein's High Lord and Swordmaster designs with selected commanders."""

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


MANIFEST_PATH = ROOT / "editor/static/ai-class-sprites/manifest.json"
SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders"
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
RESAMPLING = getattr(Image, "Resampling", Image)

CLASS_SPECS = {
    0x0B: {
        "name": "HIGH LORD",
        "source_dir": (
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-high-lord-hein-v1"
        ),
        "master": "master/hein-0B-high-lord-user-approved.png",
        "targets": (1, 2, 3, 4, 5, 6, 7, 8, 10),
        "comparison": "all-high-lord-variants.png",
    },
    0x1A: {
        "name": "SWORDMASTER",
        "source_dir": (
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-swordmaster-hein-v1"
        ),
        "master": "master/hein-1A-swordmaster-user-approved.png",
        "targets": (5, 7, 8, 10),
        "comparison": "all-swordmaster-variants.png",
    },
}

# Dark, main, highlight, and secondary accent for each commander. Elwin joins
# the High Lord targets, while his separate Swordmaster design stays untouched.
COMMANDER_SCHEMES = {
    1: {
        "dark": (73, 73, 109, 255),
        "main": (36, 73, 219, 255),
        "light": (109, 219, 255, 255),
        "accent": (219, 0, 0, 255),
    },
    2: {
        "dark": (109, 0, 0, 255),
        "main": (219, 0, 0, 255),
        "light": (255, 109, 109, 255),
        "accent": (146, 73, 36, 255),
    },
    3: {
        "dark": (0, 0, 109, 255),
        "main": (0, 73, 219, 255),
        "light": (73, 146, 255, 255),
        "accent": (109, 36, 36, 255),
    },
    4: {
        "dark": (109, 0, 0, 255),
        "main": (219, 0, 0, 255),
        "light": (255, 109, 109, 255),
        "accent": (146, 73, 36, 255),
    },
    5: {
        "dark": (73, 73, 109, 255),
        "main": (73, 109, 255, 255),
        "light": (109, 219, 255, 255),
        "accent": (146, 36, 0, 255),
    },
    6: {
        "dark": (73, 73, 109, 255),
        "main": (109, 0, 0, 255),
        "light": (219, 0, 0, 255),
        "accent": (146, 73, 36, 255),
    },
    7: {
        "dark": (109, 73, 0, 255),
        "main": (219, 146, 36, 255),
        "light": (255, 219, 109, 255),
        "accent": (146, 36, 0, 255),
    },
    8: {
        "dark": (73, 73, 109, 255),
        "main": (146, 146, 146, 255),
        "light": (255, 255, 255, 255),
        "accent": (146, 73, 36, 255),
    },
    10: {
        "dark": (109, 0, 0, 255),
        "main": (219, 0, 0, 255),
        "light": (255, 109, 109, 255),
        "accent": (146, 73, 36, 255),
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


def role_mapping(
    class_id: int,
    commander_id: int,
) -> dict[tuple[int, int, int, int], tuple[int, int, int, int]]:
    if commander_id == 5:
        if class_id == 0x0B:
            return {
                # Match Hein's bright green Lord/Archmage cloth instead of
                # keeping the red cape from the protected design master.
                (146, 36, 0, 255): (36, 219, 36, 255),
            }
        return {}
    scheme = COMMANDER_SCHEMES[commander_id]
    if class_id == 0x0B:
        return {
            (73, 73, 109, 255): scheme["dark"],
            (73, 109, 255, 255): scheme["main"],
            (146, 36, 0, 255): scheme["accent"],
        }
    return {
        (73, 73, 109, 255): scheme["dark"],
        (73, 36, 36, 255): scheme["dark"],
        (146, 36, 36, 255): scheme["main"],
    }


def validate_variant(
    *,
    converted: Image.Image,
    original: Image.Image,
    identity_points: set[tuple[int, int]],
) -> dict[str, object]:
    visible_identity = {
        point
        for point in identity_points
        if original.getpixel(point)[3]
    }
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
    identity_match = sum(
        converted.getpixel(point) == original.getpixel(point)
        for point in visible_identity
    )
    return {
        "identity_match": identity_match,
        "identity_pixel_count": len(visible_identity),
        "mask_pixel_count": len(identity_points),
        "equipment_priority_transparent_pixels": sum(
            converted.getpixel(point)[3] != 0
            for point in identity_points - visible_identity
        ),
        "visible_color_count": len(colors),
        "palette": colors,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black_pixels": sum(
            converted.getpixel((x, y)) == (0, 0, 0, 255)
            for y in range(16)
            for x in range(16)
        ),
        "accepted": (
            identity_match == len(visible_identity)
            and len(colors) <= 15
            and not empty_rows
            and not empty_columns
            and not any(
                converted.getpixel((x, y)) == (0, 0, 0, 255)
                for y in range(16)
                for x in range(16)
            )
        ),
    }


def write_comparison(
    *,
    source_dir: Path,
    filename: str,
    reports: list[dict[str, object]],
) -> None:
    columns = 4
    card_width = 280
    card_height = 320
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
        color = (
            (70, 170, 90)
            if report["accepted"]
            else (210, 70, 70)
        )
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
            source_dir / report["file"]
        ).convert("RGB").resize((256, 256), RESAMPLING.NEAREST)
        canvas.paste(preview, (x + 12, y + 50))
    canvas.save(source_dir / filename, optimize=True)


def build_variants() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    all_reports: list[dict[str, object]] = []
    class_results: dict[str, object] = {}
    master_row = manifest["commanders"]["5"]["classes"]

    for class_id, spec in CLASS_SPECS.items():
        source_dir = spec["source_dir"]
        logical_dir = source_dir / "logical16"
        logical_dir.mkdir(parents=True, exist_ok=True)
        master = Image.open(source_dir / spec["master"]).convert("RGBA")
        master_identity = points_for(master_row[str(class_id)])
        reports: list[dict[str, object]] = []

        for commander_id in spec["targets"]:
            commander = manifest["commanders"][str(commander_id)]
            row = commander["classes"][str(class_id)]
            target_identity = points_for(row)
            original = Image.open(
                SPRITE_DIR
                / str(commander_id)
                / f"{class_id:02X}-p1.png"
            ).convert("RGBA")
            if commander_id == 5:
                converted = master.copy()
                mapping = role_mapping(class_id, commander_id)
                for y in range(16):
                    for x in range(16):
                        point = (x, y)
                        color = converted.getpixel(point)
                        if color in mapping:
                            converted.putpixel(point, mapping[color])
            else:
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
            validation = validate_variant(
                converted=converted,
                original=original,
                identity_points=target_identity,
            )
            report = {
                "commander_id": commander_id,
                "commander_name": commander["name"],
                "class_id": f"{class_id:02X}",
                "class_name": spec["name"],
                "file": str(output_path.relative_to(source_dir)),
                **validation,
            }
            reports.append(report)
            all_reports.append(report)

        write_comparison(
            source_dir=source_dir,
            filename=spec["comparison"],
            reports=reports,
        )
        result = {
            "version": 1,
            "master": spec["master"],
            "silhouette_policy": (
                "Hein's user-approved equipment coordinates are shared; "
                "Elwin joins High Lord but remains excluded from Swordmaster; "
                "each target keeps visible identity pixels and "
                "commander-specific colors"
            ),
            "all_accepted": all(row["accepted"] for row in reports),
            "classes": reports,
        }
        (source_dir / "validation-report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        class_results[f"{class_id:02X}"] = result

    return {
        "all_accepted": all(row["accepted"] for row in all_reports),
        "classes": class_results,
    }


def main() -> int:
    report = build_variants()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
