#!/usr/bin/env python3
"""Brighten Liana Sage armor and Sherry Wizard cape without changing shape."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
import time

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "editor/static/ai-class-sprites"
MANIFEST = LIVE / "manifest.json"
OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
MASKS = ROOT / "editor/ai_identity_masks.json"
OUTPUT = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "liana-sage-sherry-wizard-palette-v1"
)
MASTER = OUTPUT / "master"
LOGICAL = OUTPUT / "logical16"
PREVIEWS = OUTPUT / "previews"
ASSET_VERSION = "liana-lana-healer-shared-v106"
DARK = (36, 36, 36, 255)

SAGE_MAIN = (146, 36, 73, 255)
SAGE_LIGHT = (219, 0, 0, 255)
SAGE_ARMOR_POINTS = {
    (6, 11), (7, 11), (8, 11), (9, 11), (10, 11),
    (7, 12), (8, 12), (9, 12), (10, 12),
    (5, 13), (6, 13), (8, 13), (10, 13),
    (5, 14), (7, 14), (8, 14), (9, 14),
    (7, 15), (8, 15), (9, 15), (10, 15),
}
SAGE_HIGHLIGHT_POINTS = {(8, 11), (9, 12), (8, 13), (8, 14), (9, 15)}

WIZARD_OLD_PURPLE = (73, 36, 146, 255)
WIZARD_TEAL_DARK = (0, 73, 109, 255)
WIZARD_TEAL = (0, 109, 146, 255)
WIZARD_SKY = (109, 219, 255, 255)
WIZARD_CAPE_POINTS = {
    (7, 9), (8, 9), (9, 9),
    (3, 10), (4, 10), (5, 10), (6, 10),
    (3, 11), (4, 11), (5, 11),
    (2, 12), (3, 12), (7, 12), (8, 12), (9, 12), (10, 12),
    (1, 13), (2, 13), (4, 13), (10, 13), (11, 13),
    (1, 14), (3, 14), (7, 14), (11, 14),
    (1, 15), (6, 15), (7, 15), (10, 15), (11, 15), (12, 15),
}
WIZARD_HIGHLIGHT_POINTS = {
    (8, 9), (4, 10), (4, 11), (8, 12), (10, 13), (7, 14), (10, 15)
}

CONFIG = {
    (2, 0x18): {
        "master": "02-18-before-bright-armor.png",
        "points": SAGE_ARMOR_POINTS,
        "highlight_points": SAGE_HIGHLIGHT_POINTS,
        "main": SAGE_MAIN,
        "light": SAGE_LIGHT,
        "name": "리아나 세이지 밝은 적색·장미색 몸통 갑옷",
    },
    (4, 0x15): {
        "master": "04-15-user-edited-before-lavender.png",
        "points": WIZARD_CAPE_POINTS,
        "highlight_points": WIZARD_HIGHLIGHT_POINTS,
        "main": WIZARD_TEAL,
        "light": WIZARD_SKY,
        "mapping": {WIZARD_OLD_PURPLE: WIZARD_TEAL_DARK},
        "name": "쉐리 메이지·아크메이지 계열 청록·하늘색 위저드",
    },
}


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def flat_pixels(image: Image.Image) -> list[list[int]]:
    return [list(color) for color in image.get_flattened_data()]


def palette(image: Image.Image, limit: int | None = None) -> list[str]:
    counts = Counter(color for color in image.get_flattened_data() if color[3])
    return [
        "#%02x%02x%02x" % color[:3]
        for color, _ in counts.most_common(limit)
    ]


def ensure_snapshots() -> None:
    for directory in (MASTER, LOGICAL, PREVIEWS):
        directory.mkdir(parents=True, exist_ok=True)
    for (commander_id, class_id), config in CONFIG.items():
        path = MASTER / config["master"]
        if not path.is_file():
            shutil.copy2(
                LIVE / str(commander_id) / f"{class_id:02X}.png",
                path,
            )


def build() -> dict[str, object]:
    ensure_snapshots()
    masks = json.loads(MASKS.read_text(encoding="utf-8"))["masks"]
    reports = []
    for (commander_id, class_id), config in CONFIG.items():
        base = Image.open(MASTER / config["master"]).convert("RGBA")
        result = base.copy()
        identity = {
            tuple(point)
            for point in masks.get(f"{commander_id}:{class_id:02X}", [])
        }
        for y in range(16):
            for x in range(16):
                point = (x, y)
                if point in identity:
                    continue
                mapping = config.get("mapping", {})
                color = result.getpixel(point)
                if color in mapping:
                    result.putpixel(point, mapping[color])
        applied_points = set()
        for point in config["points"] - identity:
            if result.getpixel(point) == DARK:
                result.putpixel(point, config["main"])
                applied_points.add(point)
        for point in config["highlight_points"] - identity:
            if result.getpixel(point) == config["main"]:
                result.putpixel(point, config["light"])

        identity_match = sum(
            result.getpixel(point) == base.getpixel(point)
            for point in identity
        )
        shape_match = sum(
            bool(a[3]) == bool(b[3])
            for a, b in zip(
                result.get_flattened_data(), base.get_flattened_data()
            )
        )
        colors = palette(result)
        dark_before = sum(color == DARK for color in base.get_flattened_data())
        dark_after = sum(color == DARK for color in result.get_flattened_data())
        empty_rows = [
            y for y in range(16)
            if not any(result.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x for x in range(16)
            if not any(result.getpixel((x, y))[3] for y in range(16))
        ]
        accepted = (
            identity_match == len(identity)
            and shape_match == 256
            and len(applied_points) >= 20
            and dark_after < dark_before
            and len(colors) <= 15
            and not empty_rows
            and not empty_columns
            and (0, 0, 0, 255) not in result.get_flattened_data()
        )
        output = LOGICAL / f"{commander_id:02d}-{class_id:02X}.png"
        result.save(output, optimize=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            PREVIEWS / f"{commander_id:02d}-{class_id:02X}.png",
            optimize=True,
        )
        reports.append(
            {
                "commander_id": commander_id,
                "class_id": f"{class_id:02X}",
                "name": config["name"],
                "file": f"logical16/{commander_id:02d}-{class_id:02X}.png",
                "identity_match": identity_match,
                "identity_pixel_count": len(identity),
                "shape_match": shape_match,
                "changed_dark_pixel_count": len(applied_points),
                "dark_pixels_before": dark_before,
                "dark_pixels_after": dark_after,
                "visible_color_count": len(colors),
                "palette": colors,
                "accepted": accepted,
            }
        )

    board = Image.new("RGBA", (1024, 560), (22, 25, 23, 255))
    draw = ImageDraw.Draw(board)
    for index, row in enumerate(reports):
        x = index * 512
        draw.text((x + 10, 12), row["name"], fill=(240, 240, 240, 255))
        image = Image.open(OUTPUT / row["file"]).convert("RGBA").resize(
            (512, 512), Image.Resampling.NEAREST
        )
        board.alpha_composite(image, (x, 48))
    board.convert("RGB").save(OUTPUT / "all-palette-polish.png", optimize=True)
    report = {
        "version": 1,
        "rule": "keep latest geometry and identity; brighten only selected dark interior material cells",
        "all_accepted": all(row["accepted"] for row in reports),
        "classes": reports,
    }
    write_json(OUTPUT / "validation-report.json", report)
    return report


def apply_live(report: dict[str, object]) -> None:
    if not report["all_accepted"]:
        raise ValueError("refusing to apply rejected palette polish")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    for sequence, ((commander_id, class_id), config) in enumerate(CONFIG.items()):
        key = f"{commander_id}:{class_id:02X}"
        source = Image.open(
            LOGICAL / f"{commander_id:02d}-{class_id:02X}.png"
        ).convert("RGBA")
        base = Image.open(MASTER / config["master"]).convert("RGBA")
        source.save(LIVE / str(commander_id) / f"{class_id:02X}.png", optimize=True)
        source.resize((512, 512), Image.Resampling.NEAREST).save(
            LIVE / f"source-cells/{commander_id}-{class_id:02X}.png",
            optimize=True,
        )
        revision = time.time_ns() + sequence
        overrides["designs"][key] = {
            "revision": revision,
            "pixels": flat_pixels(source),
            "base_pixels": flat_pixels(base),
        }
        row = manifest["commanders"][str(commander_id)]["classes"][str(class_id)]
        row["design_override"] = True
        row["design_revision"] = revision
        row["design_override_superseded"] = False
        row["superseded_design_revision"] = 0
        row["ai_source_kind"] = "사용자 최신 편집 형태 기반 수동 16×16 색감 보정"
        row["ai_source_position"] = (
            "latest/liana-sage-sherry-wizard-palette-v1/logical16/"
            f"{commander_id:02d}-{class_id:02X}.png"
        )
        row["source_palette"] = palette(source, 6)
        row["pixel_palette"] = palette(source, 6)
        row["feature"] = (
            config["name"]
            + "·사용자 최신 얼굴·무기·실루엣과 어두운 외곽선 유지·"
            "배경처럼 보이던 내부 순암색 면만 밝은 재료색으로 교체"
        )
    write_json(OVERRIDES, overrides)
    manifest["asset_version"] = ASSET_VERSION
    write_json(MANIFEST, manifest)


def main() -> int:
    report = build()
    apply_live(report)
    print(
        json.dumps(
            {
                "all_accepted": report["all_accepted"],
                "targets": ["2:18", "4:15"],
                "asset_version": ASSET_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
