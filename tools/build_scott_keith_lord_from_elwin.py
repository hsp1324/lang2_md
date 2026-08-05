#!/usr/bin/env python3
"""Give Sherry, Scott, and Keith Lord the current Elwin Lord design."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
ROM_ROOT = ROOT / "editor/static/class-sprites/commanders"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
MANIFEST_FILE = AI_ROOT / "manifest.json"
SOURCE_ROOT = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "shared-scott-keith-lord-elwin-lord-v1"
)
MASTER_PATH = SOURCE_ROOT / "master/01-04-current-elwin-lord.png"
ARCHIVE_ROOT = SOURCE_ROOT / "archive/before-elwin-lord-shield"
LOGICAL_ROOT = SOURCE_ROOT / "logical16"
PREVIEW_ROOT = SOURCE_ROOT / "previews"
TARGETS = (4, 6, 7)
SHIELD_POINTS = {
    (x, y) for y in range(8, 16) for x in range(11, 16)
}
ASSET_VERSION = "sherry-scott-keith-lord-palettes-v92"

# The two Lords share Elwin's design coordinates but not one palette. Scott
# uses his established green/gold language; Keith uses knightly blue/cyan.
BODY_COLOR_MAPS = {
    4: {
        (73, 73, 109, 255): (0, 36, 73, 255),
        (219, 0, 0, 255): (0, 109, 146, 255),
    },
    6: {
        (73, 73, 109, 255): (36, 73, 36, 255),
        (109, 0, 0, 255): (36, 109, 0, 255),
    },
    7: {
        (73, 73, 109, 255): (36, 36, 109, 255),
        (109, 0, 0, 255): (36, 73, 219, 255),
    },
}
SHIELD_COLOR_MAPS = {
    4: {
        (36, 73, 219, 255): (0, 109, 146, 255),
        (219, 0, 0, 255): (109, 219, 255, 255),
        (109, 0, 0, 255): (0, 36, 73, 255),
    },
    6: {
        (36, 73, 219, 255): (36, 182, 36, 255),
        (219, 0, 0, 255): (36, 219, 36, 255),
        (109, 0, 0, 255): (36, 109, 0, 255),
    },
    7: {
        (36, 73, 219, 255): (36, 73, 219, 255),
        (219, 0, 0, 255): (73, 109, 255, 255),
        (109, 0, 0, 255): (36, 36, 109, 255),
        (255, 182, 0, 255): (109, 219, 255, 255),
        (219, 182, 109, 255): (146, 182, 255, 255),
    },
}


def palette(image: Image.Image, limit: int | None = None) -> list[str]:
    counts = Counter(color for color in image.get_flattened_data() if color[3])
    rows = counts.most_common(limit)
    return ["#{:02x}{:02x}{:02x}".format(*color[:3]) for color, _ in rows]


def ensure_snapshots() -> None:
    MASTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    if not MASTER_PATH.is_file():
        shutil.copy2(AI_ROOT / "1/04.png", MASTER_PATH)
    for commander_id in TARGETS:
        archive = ARCHIVE_ROOT / f"{commander_id:02d}-04.png"
        if not archive.is_file():
            shutil.copy2(AI_ROOT / f"{commander_id}/04.png", archive)


def build() -> dict[str, object]:
    ensure_snapshots()
    LOGICAL_ROOT.mkdir(parents=True, exist_ok=True)
    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    master = Image.open(MASTER_PATH).convert("RGBA")
    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    reports = []
    for commander_id in TARGETS:
        before = Image.open(
            ARCHIVE_ROOT / f"{commander_id:02d}-04.png"
        ).convert("RGBA")
        original = Image.open(
            ROM_ROOT / str(commander_id) / "04-p1.png"
        ).convert("RGBA")
        identity = {tuple(point) for point in masks[f"{commander_id}:04"]}
        result = before.copy()
        body_mapping = BODY_COLOR_MAPS[commander_id]
        for y in range(16):
            for x in range(16):
                point = (x, y)
                if point not in identity and point not in SHIELD_POINTS:
                    color = result.getpixel(point)
                    result.putpixel(point, body_mapping.get(color, color))
        shield_mapping = SHIELD_COLOR_MAPS[commander_id]
        for point in SHIELD_POINTS:
            color = master.getpixel(point)
            result.putpixel(point, shield_mapping.get(color, color))
        # The shield region does not overlap either target mask, but restoring
        # visible identity here makes that invariant explicit and future-safe.
        for point in identity:
            if original.getpixel(point)[3]:
                result.putpixel(point, original.getpixel(point))

        visible_identity = {
            point for point in identity if original.getpixel(point)[3]
        }
        identity_match = sum(
            result.getpixel(point) == original.getpixel(point)
            for point in visible_identity
        )
        shield_role_match = sum(
            result.getpixel(point)
            == shield_mapping.get(master.getpixel(point), master.getpixel(point))
            for point in SHIELD_POINTS
        )
        outside_shape_match = sum(
            bool(result.getpixel((x, y))[3])
            == bool(before.getpixel((x, y))[3])
            for y in range(16)
            for x in range(16)
            if (x, y) not in SHIELD_POINTS and (x, y) not in identity
        )
        outside_total = 256 - len(SHIELD_POINTS | identity)
        body_recolored_pixels = sum(
            result.getpixel((x, y)) != before.getpixel((x, y))
            for y in range(16)
            for x in range(16)
            if (x, y) not in SHIELD_POINTS and (x, y) not in identity
        )
        colors = palette(result)
        empty_rows = [
            y for y in range(16)
            if not any(result.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x for x in range(16)
            if not any(result.getpixel((x, y))[3] for y in range(16))
        ]
        pure_black = sum(
            result.getpixel((x, y)) == (0, 0, 0, 255)
            for y in range(16)
            for x in range(16)
        )
        accepted = (
            identity_match == len(visible_identity)
            and shield_role_match == len(SHIELD_POINTS)
            and outside_shape_match == outside_total
            and body_recolored_pixels >= 10
            and len(colors) <= 15
            and not empty_rows
            and not empty_columns
            and pure_black == 0
        )
        result.save(LOGICAL_ROOT / f"{commander_id:02d}-04.png", optimize=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            PREVIEW_ROOT / f"{commander_id:02d}-04.png", optimize=True
        )
        reports.append(
            {
                "commander_id": commander_id,
                "class_id": "04",
                "identity_match": identity_match,
                "identity_pixel_count": len(visible_identity),
                "shield_role_match": shield_role_match,
                "shield_pixel_count": len(SHIELD_POINTS),
                "outside_shield_shape_match": outside_shape_match,
                "outside_shield_shape_total": outside_total,
                "body_recolored_pixels": body_recolored_pixels,
                "palette_family": (
                    "navy/teal/cyan/gold"
                    if commander_id == 4
                    else "forest-green/lime/gold"
                    if commander_id == 6
                    else "navy/blue/cyan"
                ),
                "visible_color_count": len(colors),
                "palette": colors,
                "empty_rows": empty_rows,
                "empty_columns": empty_columns,
                "pure_black_pixels": pure_black,
                "accepted": accepted,
            }
        )

    board = Image.new("RGBA", (2048, 560), (22, 25, 23, 255))
    draw = ImageDraw.Draw(board)
    entries = [
        ("Elwin Lord shield", MASTER_PATH),
        ("Sherry Lord", LOGICAL_ROOT / "04-04.png"),
        ("Scott Lord", LOGICAL_ROOT / "06-04.png"),
        ("Keith Lord", LOGICAL_ROOT / "07-04.png"),
    ]
    for index, (label, path) in enumerate(entries):
        draw.text((index * 512 + 12, 12), label, fill=(235, 240, 236, 255))
        image = Image.open(path).convert("RGBA").resize(
            (512, 512), Image.Resampling.NEAREST
        )
        board.alpha_composite(image, (index * 512, 48))
    board.convert("RGB").save(SOURCE_ROOT / "all-lord-shields.png", optimize=True)

    report = {
        "version": 1,
        "master": str(MASTER_PATH.relative_to(ROOT)),
        "rule": (
            "copy current Elwin Lord shield roles and body coordinates; "
            "Sherry teal/cyan, Scott green/gold, Keith blue/cyan"
        ),
        "shield_points": [list(point) for point in sorted(SHIELD_POINTS)],
        "all_accepted": all(row["accepted"] for row in reports),
        "classes": reports,
    }
    (SOURCE_ROOT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def apply_live(report: dict[str, object]) -> None:
    if not report["all_accepted"]:
        raise ValueError("refusing to apply rejected Scott/Keith Lord assets")
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    for commander_id in TARGETS:
        source = Image.open(
            LOGICAL_ROOT / f"{commander_id:02d}-04.png"
        ).convert("RGBA")
        source.save(AI_ROOT / f"{commander_id}/04.png", optimize=True)
        source.resize((512, 512), Image.Resampling.NEAREST).save(
            AI_ROOT / f"source-cells/{commander_id}-04.png", optimize=True
        )
        original = Image.open(
            ROM_ROOT / str(commander_id) / "04-p1.png"
        ).convert("RGBA")
        changed = sum(
            source.getpixel((x, y)) != original.getpixel((x, y))
            for y in range(16)
            for x in range(16)
        )
        row = manifest["commanders"][str(commander_id)]["classes"][str(0x04)]
        row["ai_source_kind"] = (
            "현재 엘윈 로드 방패 기반 쉐리·스코트·키스 로드 "
            "공통 16×16 클래스 템플릿"
        )
        row["ai_source_position"] = (
            "latest/shared-scott-keith-lord-elwin-lord-v1/logical16/"
            f"{commander_id:02d}-04.png"
        )
        row["source_palette"] = palette(source, 6)
        row["pixel_palette"] = palette(source, 6)
        row["changed_pixel_count"] = changed
        row["feature"] = (
            "현재 얼굴·몸통·어두운 경계와 엘윈 로드 장비 좌표 유지·"
            + (
                "쉐리 남청·청록·하늘색·금색 장비색 적용·"
                if commander_id == 4
                else "스코트 숲초록·연두·금색 장비색 적용·"
                if commander_id == 6
                else "키스 남청·파랑·하늘색 장비색 적용·"
            )
            + "엘윈 로드 격자 방패 40픽셀 색 역할 적용·"
            f"변경 {changed}픽셀"
        )
        if commander_id == 6:
            previous_revision = int(row.get("design_revision", 0))
            row["design_override"] = False
            row["design_revision"] = 0
            row["design_override_superseded"] = True
            row["superseded_design_revision"] = max(
                previous_revision,
                int(row.get("superseded_design_revision", 0)),
                1785120121020121547,
            )
    manifest["asset_version"] = ASSET_VERSION
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    report = build()
    apply_live(report)
    print(
        json.dumps(
            {
                "all_accepted": report["all_accepted"],
                "targets": ["4:04", "6:04", "7:04"],
                "asset_version": ASSET_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
