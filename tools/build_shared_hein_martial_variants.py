#!/usr/bin/env python3
# ruff: noqa: E402
"""Share Hein's High Lord and Swordmaster designs with selected commanders."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_DARK_BOUNDARY_REFERENCE_POINTS,
    identity_locked_character_sprite,
)
from tools.pillow_compat import flattened_image_data


MANIFEST_PATH = ROOT / "editor/static/ai-class-sprites/manifest.json"
LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"
OVERRIDES_PATH = ROOT / "editor/ai_class_design_overrides.json"
SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders"
TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
RESAMPLING = getattr(Image, "Resampling", Image)

CLASS_SPECS = {
    0x0B: {
        "name": "HIGH LORD",
        "source_dir": (
            ROOT
            / "assets/class-sprites/source/latest/"
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
            / "assets/class-sprites/source/latest/"
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
        "dark": (0, 36, 182, 255),
        "main": (73, 109, 255, 255),
        "light": (109, 219, 255, 255),
        "accent": (109, 219, 255, 255),
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

JESSICA_HIGH_LORD_CAPE_POINTS = {
    (5, 10),
    (11, 10),
    (5, 11),
    (11, 11),
    (11, 12),
    (12, 12),
    (4, 13),
    (12, 13),
    (13, 13),
    (3, 14),
    (4, 14),
    (12, 14),
    (13, 14),
    (2, 15),
    (3, 15),
    (6, 15),
    (7, 15),
    (8, 15),
    (9, 15),
    (13, 15),
}
JESSICA_HIGH_LORD_CAPE_LIGHT_POINTS = {
    (5, 10),
    (11, 10),
    (12, 12),
    (13, 13),
    (3, 14),
    (13, 14),
    (2, 15),
    (6, 15),
    (13, 15),
}
JESSICA_HIGH_LORD_CAPE_DARK_POINTS = {
    (5, 11),
    (11, 12),
    (4, 13),
    (12, 14),
    (3, 15),
    (8, 15),
    (9, 15),
}
LANA_HIGH_LORD_GRAY_FOOT_POINTS = {
    (5, 14),
    (6, 14),
    (4, 15),
    (5, 15),
    (10, 15),
    (11, 15),
    (12, 15),
}


def points_for(row: dict[str, object]) -> set[tuple[int, int]]:
    return {tuple(point) for point in row["identity_lock_points"]}


def source_points_for(row: dict[str, object]) -> set[tuple[int, int]]:
    """Return identity points before the editor-only final translation."""
    points = points_for(row)
    translation = row.get("identity_translation")
    if (
        translation is None
        or row.get("identity_translation_applied_in_override", False)
    ):
        return points
    dx, dy = translation
    return {(x - int(dx), y - int(dy)) for x, y in points}


def visible_palette(image: Image.Image) -> list[str]:
    colors = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in colors.most_common()
    ]


def flat_pixels(image: Image.Image) -> list[list[int]]:
    return [list(color) for color in flattened_image_data(image)]


def role_mapping(
    class_id: int,
    commander_id: int,
) -> dict[tuple[int, int, int, int], tuple[int, int, int, int]]:
    if commander_id == 5:
        if class_id == 0x0B:
            return {
                # Use the same restrained green as Hein Mage/Archmage rather
                # than the former near-neon lime cape.
                (146, 36, 0, 255): (36, 182, 36, 255),
            }
        if class_id == 0x1A:
            return {
                # Tie Hein's Swordmaster cape and cloth to the restrained
                # green progression already used by his Lord/High Lord.
                (73, 36, 36, 255): (36, 109, 0, 255),
                (146, 36, 36, 255): (36, 182, 36, 255),
            }
        return {}
    scheme = COMMANDER_SCHEMES[commander_id]
    if class_id == 0x0B:
        if commander_id == 3:
            # Match Lana's original High Lord ramp: cyan armor, blue cape.
            return {
                (73, 73, 109, 255): (73, 109, 255, 255),
                (73, 109, 255, 255): (109, 219, 255, 255),
                (146, 36, 0, 255): (0, 73, 219, 255),
            }
        if commander_id == 10:
            # Keep Hein's blue-and-gold armor language. Only replace the
            # master's red cape with Jessica's blue/cyan cloth ramp.
            return {
                (146, 36, 0, 255): (73, 146, 255, 255),
            }
        if commander_id == 8:
            # Reuse Aaron Knight's blue shield ramp only on High Lord.
            # Swordmaster has its own blue progression mapping below.
            scheme = {
                **scheme,
                "dark": (73, 109, 255, 255),
                "main": (109, 219, 255, 255),
                "light": (109, 219, 255, 255),
            }
        return {
            (73, 73, 109, 255): scheme["dark"],
            (73, 109, 255, 255): scheme["main"],
            (146, 36, 0, 255): scheme["accent"],
        }
    if commander_id == 8:
        # Aaron Swordmaster sits visually between his blue High Lord and
        # High Master. Keep the silver blades, but give the cloth and light
        # armor three separated blue roles instead of the former flat gray.
        return {
            (73, 73, 109, 255): (36, 73, 219, 255),
            (73, 36, 36, 255): (73, 109, 255, 255),
            (146, 36, 36, 255): (109, 219, 255, 255),
        }
    if commander_id == 7:
        # Keith's Lord and Saint already use a dark-blue -> sky-blue ramp.
        # Carry that same family into Swordmaster while retaining white blades.
        return {
            (73, 73, 109, 255): scheme["dark"],
            (73, 36, 36, 255): scheme["dark"],
            (146, 36, 36, 255): scheme["main"],
            (146, 146, 182, 255): scheme["light"],
        }
    return {
        (73, 73, 109, 255): scheme["dark"],
        (73, 36, 36, 255): scheme["dark"],
        (146, 36, 36, 255): scheme["main"],
    }


def apply_variant_details(
    class_id: int,
    commander_id: int,
    converted: Image.Image,
) -> None:
    if (commander_id, class_id) != (10, 0x0B):
        if (commander_id, class_id) != (3, 0x0B):
            return
        for point in JESSICA_HIGH_LORD_CAPE_POINTS:
            converted.putpixel(point, (0, 73, 219, 255))
        for point in JESSICA_HIGH_LORD_CAPE_DARK_POINTS:
            converted.putpixel(point, (0, 0, 219, 255))
        for point in JESSICA_HIGH_LORD_CAPE_LIGHT_POINTS:
            converted.putpixel(point, (73, 109, 255, 255))
        for point in LANA_HIGH_LORD_GRAY_FOOT_POINTS:
            converted.putpixel(point, (146, 146, 146, 255))
        return
    for point in JESSICA_HIGH_LORD_CAPE_POINTS:
        converted.putpixel(point, (73, 146, 255, 255))
    for point in JESSICA_HIGH_LORD_CAPE_DARK_POINTS:
        converted.putpixel(point, (36, 73, 219, 255))
    for point in JESSICA_HIGH_LORD_CAPE_LIGHT_POINTS:
        converted.putpixel(point, (109, 219, 255, 255))


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
                f"{report['class_name']}"
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


def refresh_variant_report(
    class_id: int,
    commander_ids: set[int],
) -> None:
    """Refresh selected rows without rebuilding other commanders."""
    spec = CLASS_SPECS[class_id]
    source_dir = spec["source_dir"]
    report_path = source_dir / "validation-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for row in report["classes"]:
        commander_id = int(row["commander_id"])
        if commander_id not in commander_ids:
            continue
        manifest_row = manifest["commanders"][str(commander_id)][
            "classes"
        ][str(class_id)]
        identity_points = source_points_for(manifest_row)
        original = Image.open(
            SPRITE_DIR
            / str(commander_id)
            / f"{class_id:02X}-p1.png"
        ).convert("RGBA")
        converted = Image.open(
            source_dir / row["file"]
        ).convert("RGBA")
        row.update(validate_variant(
            converted=converted,
            original=original,
            identity_points=identity_points,
        ))
    report["all_accepted"] = all(
        row["accepted"] for row in report["classes"]
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_comparison(
        source_dir=source_dir,
        filename=spec["comparison"],
        reports=report["classes"],
    )


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
            target_identity = source_points_for(row)
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
            apply_variant_details(class_id, commander_id, converted)

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


def apply_live_variant(
    commander_id: int,
    class_id: int,
    feature: str,
) -> None:
    """Publish one generated shared-class result without touching peers."""
    source = (
        CLASS_SPECS[class_id]["source_dir"]
        / f"logical16/{commander_id:02d}-{class_id:02X}.png"
    )
    result = Image.open(source).convert("RGBA")
    live_path = LIVE_ROOT / str(commander_id) / f"{class_id:02X}.png"
    before = Image.open(live_path).convert("RGBA")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    row = manifest["commanders"][str(commander_id)]["classes"][str(class_id)]
    protected = {
        tuple(point)
        for point in row.get("identity_lock_points", [])
        + row.get("mount_lock_points", [])
    }
    for point in SHARED_DARK_BOUNDARY_REFERENCE_POINTS.get(class_id, set()):
        if point not in protected and not result.getpixel(point)[3]:
            result.putpixel(point, INK)

    revision = time.time_ns()
    result.save(live_path, optimize=True)
    result.resize((512, 512), Image.Resampling.NEAREST).save(
        LIVE_ROOT / f"source-cells/{commander_id}-{class_id:02X}.png",
        optimize=True,
    )
    key = f"{commander_id}:{class_id:02X}"
    overrides["designs"][key] = {
        "revision": revision,
        "pixels": flat_pixels(result),
        "base_pixels": flat_pixels(before),
    }
    row["design_override"] = True
    row["design_revision"] = revision
    row["design_override_superseded"] = False
    row["superseded_design_revision"] = 0
    row["ai_source_kind"] = (
        f"헤인 사용자 편집 {CLASS_SPECS[class_id]['name']} "
        "공통 16×16 클래스 템플릿"
    )
    row["ai_source_position"] = (
        "latest/"
        + (
            "shared-high-lord-hein-v1"
            if class_id == 0x0B
            else "shared-swordmaster-hein-v1"
        )
        + f"/logical16/{commander_id:02d}-{class_id:02X}.png"
    )
    row["source_palette"] = visible_palette(result)[:6]
    row["pixel_palette"] = visible_palette(result)[:6]
    row["feature"] = feature
    manifest["asset_version"] = ASSET_VERSION
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OVERRIDES_PATH.write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def apply_hein_swordmaster_live() -> None:
    apply_live_variant(
        5,
        0x1A,
        "헤인 사용자 편집 소드마스터의 쌍검·갑옷·실루엣 유지·"
        "로드·하이로드와 같은 짙은 초록·연두 망토 명암 적용·"
        "청색 머리·얼굴·흰 검날 유지·메가드라이브 15색 이하",
    )


def apply_keith_blue_live() -> None:
    apply_live_variant(
        7,
        0x0B,
        "헤인 하이로드 장비·방패·검 실루엣 유지·키스 로드·세인트와 "
        "같은 진청·파랑·하늘색 단계색 적용·얼굴·머리·흰 검날 유지",
    )
    apply_live_variant(
        7,
        0x1A,
        "헤인 소드마스터 쌍검·견갑 실루엣 유지·키스 로드·세인트와 "
        "같은 진청·파랑·하늘색 단계색 적용·얼굴·머리·흰 쌍검 유지",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-hein-swordmaster", action="store_true")
    parser.add_argument("--apply-keith-blue", action="store_true")
    args = parser.parse_args()
    report = build_variants()
    if report["all_accepted"] and args.apply_hein_swordmaster:
        apply_hein_swordmaster_live()
    if report["all_accepted"] and args.apply_keith_blue:
        apply_keith_blue_live()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
