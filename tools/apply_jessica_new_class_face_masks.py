#!/usr/bin/env python3
"""Apply Jessica's latest hand-painted face masks to selected classes."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pillow_compat import flattened_image_data  # noqa: E402


LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"
MANIFEST = LIVE_ROOT / "manifest.json"
MASKS = ROOT / "editor/ai_identity_masks.json"
OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
OUTPUT = (
    ROOT
    / "assets/class-sprites/source/latest/jessica-face-mask-refresh-v1"
)
ASSET_VERSION = "liana-lana-healer-shared-v106"

TARGETS = (0x08, 0x11, 0x15, 0x18, 0x1A, 0x26)
SOURCE_PATHS = {
    0x08: ROOT
    / "assets/class-sprites/source/latest/shared-new-classes-v2-refined/logical16/10-08.png",
    0x11: ROOT
    / "assets/class-sprites/source/latest/shared-hein-classes-v1/logical16/10-11.png",
    0x15: ROOT
    / "assets/class-sprites/source/latest/shared-new-classes-v2-refined/logical16/10-15.png",
    0x18: ROOT
    / "assets/class-sprites/source/latest/shared-new-classes-v2-refined/logical16/10-18.png",
    0x1A: ROOT
    / "assets/class-sprites/source/latest/shared-swordmaster-hein-v1/logical16/10-1A.png",
    0x26: ROOT
    / "assets/class-sprites/source/latest/shared-keith-wizard-new-classes-v1/logical16/10-26.png",
}
PREVIEW_PATHS = {
    0x08: SOURCE_PATHS[0x08].parents[1] / "previews/10-08.png",
    0x11: None,
    0x15: SOURCE_PATHS[0x15].parents[1] / "previews/10-15.png",
    0x18: SOURCE_PATHS[0x18].parents[1] / "previews/10-18.png",
    0x1A: None,
    0x26: SOURCE_PATHS[0x26].parents[1] / "previews/10-26.png",
}
CLASS_NAMES = {
    0x08: "힐러",
    0x11: "프리스트",
    0x15: "위저드",
    0x18: "세이지",
    0x1A: "소드마스터",
    0x26: "자베라",
}

RARE_WIZARD_BLUE = (36, 73, 255, 255)
MAIN_WIZARD_BLUE = (73, 109, 255, 255)


def flat_pixels(image: Image.Image) -> list[list[int]]:
    return [list(color) for color in flattened_image_data(image)]


def palette(image: Image.Image) -> list[str]:
    counts = Counter(
        color for color in flattened_image_data(image) if color[3]
    )
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def restore_mask(
    image: Image.Image,
    original: Image.Image,
    points: set[tuple[int, int]],
) -> tuple[Image.Image, int]:
    result = image.copy().convert("RGBA")
    changed = 0
    for point in points:
        color = original.getpixel(point)
        if color[3] and result.getpixel(point) != color:
            result.putpixel(point, color)
            changed += 1
    return result, changed


def merge_wizard_equipment_blue(
    image: Image.Image,
    points: set[tuple[int, int]],
) -> tuple[Image.Image, int]:
    result = image.copy().convert("RGBA")
    changed = 0
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if (
                point not in points
                and result.getpixel(point) == RARE_WIZARD_BLUE
            ):
                result.putpixel(point, MAIN_WIZARD_BLUE)
                changed += 1
    return result, changed


def update_source_report(
    source_path: Path,
    class_id: int,
    image: Image.Image,
    original: Image.Image,
    points: set[tuple[int, int]],
) -> None:
    report_path = source_path.parents[1] / "validation-report.json"
    if not report_path.is_file():
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = [
        row
        for row in report.get("classes", [])
        if int(row["commander_id"]) == 10
        and int(row["class_id"], 16) == class_id
    ]
    if not rows:
        return
    row = rows[0]
    visible_points = {
        point for point in points if original.getpixel(point)[3]
    }
    colors = palette(image)
    row["identity_match"] = sum(
        image.getpixel(point) == original.getpixel(point)
        for point in visible_points
    )
    row["identity_matches"] = row["identity_match"]
    row["identity_pixel_count"] = len(visible_points)
    row["identity_visible"] = len(visible_points)
    row["mask_pixel_count"] = len(points)
    row["visible_color_count"] = len(colors)
    row["palette"] = colors
    if class_id == 0x15:
        row["near_duplicate_palette_merge"] = (
            "#9224B6 -> #9249B6; #2449FF -> #496DFF"
        )
        row["accepted"] = (
        row["identity_match"] == len(visible_points)
        and len(colors) <= 15
    )
    report["all_accepted"] = all(
        bool(item["accepted"]) for item in report.get("classes", [])
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_contact(rows: list[dict[str, object]]) -> None:
    scale = 16
    cell = 256
    header = 34
    canvas = Image.new(
        "RGB", (len(rows) * cell, cell + header), (24, 24, 24)
    )
    draw = ImageDraw.Draw(canvas)
    for index, row in enumerate(rows):
        x = index * cell
        draw.text(
            (x + 6, 8),
            f"Jessica {row['class_name']} {row['class_id']}",
            fill="white",
        )
        sprite = Image.open(OUTPUT / row["file"]).convert("RGBA")
        background = Image.new("RGBA", (16, 16), (35, 35, 35, 255))
        background.alpha_composite(sprite)
        canvas.paste(
            background.convert("RGB").resize(
                (16 * scale, 16 * scale), Image.Resampling.NEAREST
            ),
            (x, header),
        )
    canvas.save(OUTPUT / "all-jessica-face-mask-refresh.png", optimize=True)


def main() -> int:
    masks = json.loads(MASKS.read_text(encoding="utf-8"))["masks"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    for child in ("previous", "logical16", "previews"):
        (OUTPUT / child).mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, object]] = []
    for sequence, class_id in enumerate(TARGETS):
        key = f"10:{class_id:02X}"
        points = {tuple(point) for point in masks[key]}
        live_path = LIVE_ROOT / f"10/{class_id:02X}.png"
        original_path = (
            ROOT
            / f"editor/static/class-sprites/commanders/10/{class_id:02X}-p1.png"
        )
        previous_path = OUTPUT / f"previous/10-{class_id:02X}.png"
        if not previous_path.is_file():
            shutil.copy2(live_path, previous_path)

        original = Image.open(original_path).convert("RGBA")
        result, restored = restore_mask(
            Image.open(live_path).convert("RGBA"), original, points
        )
        merged = 0
        if class_id == 0x15:
            result, merged = merge_wizard_equipment_blue(result, points)
        colors = palette(result)
        visible_points = {
            point for point in points if original.getpixel(point)[3]
        }
        matches = sum(
            result.getpixel(point) == original.getpixel(point)
            for point in visible_points
        )
        if matches != len(visible_points):
            raise ValueError(f"{key}: face mask restoration failed")
        if len(colors) > 15:
            raise ValueError(f"{key}: {len(colors)} visible colors")

        result.save(live_path, optimize=True)
        result.save(SOURCE_PATHS[class_id], optimize=True)
        result.save(OUTPUT / f"logical16/10-{class_id:02X}.png", optimize=True)
        preview = result.resize((512, 512), Image.Resampling.NEAREST)
        preview.save(OUTPUT / f"previews/10-{class_id:02X}.png", optimize=True)
        preview.save(
            LIVE_ROOT / f"source-cells/10-{class_id:02X}.png",
            optimize=True,
        )
        if PREVIEW_PATHS[class_id] is not None:
            PREVIEW_PATHS[class_id].parent.mkdir(parents=True, exist_ok=True)
            preview.save(PREVIEW_PATHS[class_id], optimize=True)
        update_source_report(
            SOURCE_PATHS[class_id], class_id, result, original, points
        )

        revision = time.time_ns() + sequence
        if key in overrides.get("designs", {}):
            overrides["designs"][key]["revision"] = revision
            overrides["designs"][key]["pixels"] = flat_pixels(result)
        row = manifest["commanders"]["10"]["classes"][str(class_id)]
        row["identity_lock_points"] = [
            list(point) for point in sorted(points)
        ]
        row["identity_lock_pixel_count"] = len(points)
        row["identity_mask_pending_rebuild"] = False
        row["identity_translation"] = None
        row["identity_translation_applied_in_override"] = False
        row["design_revision"] = (
            revision if key in overrides.get("designs", {}) else 0
        )
        row["pixel_palette"] = colors[:15]
        row["changed_pixel_count"] = sum(
            result.getpixel((x, y)) != original.getpixel((x, y))
            for y in range(16)
            for x in range(16)
        )
        marker = "·최신 제시카 눈·얼굴 사용자 마스크 원본 픽셀 재적용"
        if marker not in row.get("feature", ""):
            row["feature"] = row.get("feature", "") + marker
        if class_id == 0x15:
            row["feature"] += (
                "·얼굴 회색 슬롯 확보를 위해 장비 1픽셀 "
                "#2449FF를 #496DFF로 병합"
            )

        reports.append(
            {
                "class_id": f"{class_id:02X}",
                "class_name": CLASS_NAMES[class_id],
                "file": f"logical16/10-{class_id:02X}.png",
                "mask_points": len(points),
                "visible_identity_points": len(visible_points),
                "identity_matches": matches,
                "restored_pixels": restored,
                "merged_equipment_pixels": merged,
                "visible_color_count": len(colors),
                "accepted": True,
            }
        )

    manifest["asset_version"] = ASSET_VERSION
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OVERRIDES.write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "version": 1,
        "asset_version": ASSET_VERSION,
        "all_accepted": True,
        "classes": reports,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_contact(reports)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
