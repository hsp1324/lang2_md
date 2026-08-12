#!/usr/bin/env python3
"""Publish AI class samples to the editor and build visual review sheets."""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    ROOT / "assets/class-sprites/source/latest/sample-class-variants-v1"
)
STATIC_ROOT = ROOT / "editor/static/sample-class-sprites"
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
MANIFEST_PATH = STATIC_ROOT / "manifest.json"
AI_MANIFEST_PATH = AI_ROOT / "manifest.json"
FORBIDDEN_COLORS = {(0, 0, 0, 255), (255, 0, 255, 255)}


def visible_colors(image: Image.Image) -> set[tuple[int, int, int, int]]:
    return {
        color
        for _, color in image.convert("RGBA").getcolors(maxcolors=256) or []
        if color[3]
    }


def connected_components(image: Image.Image) -> list[int]:
    remaining = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if image.getpixel((x, y))[3]
    }
    sizes: list[int] = []
    while remaining:
        queue = deque([remaining.pop()])
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            for point in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if point in remaining:
                    remaining.remove(point)
                    queue.append(point)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def center_holes(image: Image.Image) -> list[tuple[int, int]]:
    transparent = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if not image.getpixel((x, y))[3]
    }
    outside = {
        point
        for point in transparent
        if point[0] in (0, 15) or point[1] in (0, 15)
    }
    queue = deque(outside)
    while queue:
        x, y = queue.popleft()
        for point in (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ):
            if point in transparent and point not in outside:
                outside.add(point)
                queue.append(point)
    return sorted(
        (
            point
            for point in transparent - outside
            if 4 <= point[0] <= 11 and 8 <= point[1] <= 14
        ),
        key=lambda point: (point[1], point[0]),
    )


def publish_ai_thumbnail(source: Path, target: Path) -> Image.Image:
    with Image.open(source) as opened:
        image = opened.convert("RGBA")
    image.thumbnail((384, 384), Image.Resampling.NEAREST)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)
    return image


def publish_logical16(image: Image.Image, target: Path) -> Image.Image:
    if image.size != (16, 16):
        raise ValueError(f"logical sprite must be 16x16: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)
    return image


def editor_space_identity(
    image: Image.Image,
    group: dict,
    ai_manifest: dict,
) -> Image.Image:
    """Match the editor's final identity coordinates without moving gear."""
    commander_id = int(group["commander_id"])
    class_id = int(group["class_id"])
    row = ai_manifest["commanders"][str(commander_id)]["classes"][
        str(class_id)
    ]
    target_points = {
        tuple(point) for point in row.get("identity_lock_points", [])
    }
    dx, dy = group.get("identity_translation", [0, 0])
    source_points = {
        (x - dx, y - dy)
        for x, y in target_points
        if 0 <= x - dx < 16 and 0 <= y - dy < 16
    }
    result = image.copy()
    for point in source_points - target_points:
        result.putpixel(point, (0, 0, 0, 0))
    identity_path = AI_ROOT / str(commander_id) / f"{class_id:02X}.png"
    with Image.open(identity_path) as opened:
        current = opened.convert("RGBA")
    for point in target_points:
        result.putpixel(point, current.getpixel(point))
    for point in group.get("identity_seam_points", []):
        seam_point = tuple(point)
        if not result.getpixel(seam_point)[3]:
            result.putpixel(seam_point, (36, 36, 36, 255))
    return result


def publish_preview(image: Image.Image, target: Path) -> Image.Image:
    preview = image.resize((256, 256), Image.Resampling.NEAREST)
    target.parent.mkdir(parents=True, exist_ok=True)
    preview.save(target, optimize=True)
    return preview


def fit_on_canvas(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", size, (20, 23, 21, 255))
    fitted = image.copy()
    fitted.thumbnail((size[0] - 12, size[1] - 12), Image.Resampling.NEAREST)
    canvas.alpha_composite(
        fitted,
        ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2),
    )
    return canvas


def sample_review_panel(
    sample_id: str,
    ai_image: Image.Image,
    preview: Image.Image,
) -> Image.Image:
    panel = Image.new("RGBA", (248, 442), (35, 40, 36, 255))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle(
        (1, 1, 246, 440),
        radius=8,
        outline=(83, 112, 91, 255),
        width=2,
    )
    draw.text((12, 10), sample_id, fill=(235, 242, 236, 255))
    panel.alpha_composite(fit_on_canvas(ai_image, (224, 224)), (12, 34))
    panel.alpha_composite(fit_on_canvas(preview, (224, 160)), (12, 270))
    return panel


def validate_identity(
    image: Image.Image,
    commander_id: int,
    class_id: int,
    ai_manifest: dict,
) -> tuple[int, int]:
    row = ai_manifest["commanders"][str(commander_id)]["classes"][
        str(class_id)
    ]
    points = [tuple(point) for point in row.get("identity_lock_points", [])]
    original_path = AI_ROOT / str(commander_id) / f"{class_id:02X}.png"
    with Image.open(original_path) as opened:
        original = opened.convert("RGBA")
    matches = sum(
        image.getpixel(point) == original.getpixel(point)
        for point in points
    )
    return matches, len(points)


def build() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ai_manifest = json.loads(AI_MANIFEST_PATH.read_text(encoding="utf-8"))
    reports: list[dict] = []
    group_sheets: list[Image.Image] = []
    contact_dir = SOURCE_ROOT / "contact-sheets"
    contact_dir.mkdir(parents=True, exist_ok=True)

    for group in manifest["groups"]:
        group_id = group["id"]
        panels: list[Image.Image] = []
        for sample in group["samples"]:
            sample_id = sample["id"]
            source_ai = SOURCE_ROOT / group_id / "ai" / f"{sample_id}.png"
            source_logical = (
                SOURCE_ROOT / group_id / "logical16" / f"{sample_id}.png"
            )
            if not source_ai.is_file() or not source_logical.is_file():
                missing = source_ai if not source_ai.is_file() else source_logical
                raise FileNotFoundError(missing)

            static_ai = ROOT / "editor/static" / sample["ai_source"]
            static_logical = ROOT / "editor/static" / sample["logical16"]
            static_preview = ROOT / "editor/static" / sample["preview"]
            ai_image = publish_ai_thumbnail(source_ai, static_ai)
            with Image.open(source_logical) as opened:
                source_sprite = opened.convert("RGBA")
            editor_sprite = editor_space_identity(
                source_sprite,
                group,
                ai_manifest,
            )
            logical = publish_logical16(editor_sprite, static_logical)
            preview = publish_preview(logical, static_preview)

            colors = visible_colors(logical)
            empty_rows = [
                y
                for y in range(16)
                if not any(logical.getpixel((x, y))[3] for x in range(16))
            ]
            empty_columns = [
                x
                for x in range(16)
                if not any(logical.getpixel((x, y))[3] for y in range(16))
            ]
            identity_matches, identity_total = validate_identity(
                logical,
                int(group["commander_id"]),
                int(group["class_id"]),
                ai_manifest,
            )
            components = connected_components(logical)
            holes = center_holes(logical)
            report = {
                "group": group_id,
                "sample": sample_id,
                "visible_colors": len(colors),
                "forbidden_colors": [
                    list(color) for color in sorted(colors & FORBIDDEN_COLORS)
                ],
                "empty_rows": empty_rows,
                "empty_columns": empty_columns,
                "connected_components": components,
                "center_holes": [list(point) for point in holes],
                "identity_matches": identity_matches,
                "identity_total": identity_total,
            }
            report["accepted"] = all(
                (
                    len(colors) <= 15,
                    not report["forbidden_colors"],
                    not empty_rows,
                    not empty_columns,
                    len(components) == 1,
                    not holes,
                    identity_matches == identity_total,
                )
            )
            reports.append(report)
            panels.append(sample_review_panel(sample_id, ai_image, preview))

        sheet = Image.new(
            "RGBA",
            (len(panels) * 248, 442),
            (15, 18, 16, 255),
        )
        for index, panel in enumerate(panels):
            sheet.alpha_composite(panel, (index * 248, 0))
        sheet.save(contact_dir / f"{group_id}.png", optimize=True)
        group_sheets.append(sheet)

    all_sheet = Image.new(
        "RGBA",
        (
            max(sheet.width for sheet in group_sheets),
            sum(sheet.height for sheet in group_sheets),
        ),
        (15, 18, 16, 255),
    )
    offset_y = 0
    for sheet in group_sheets:
        all_sheet.alpha_composite(sheet, (0, offset_y))
        offset_y += sheet.height
    all_sheet.save(SOURCE_ROOT / "all-samples.png", optimize=True)

    validation = {
        "asset_version": manifest["asset_version"],
        "sample_count": len(reports),
        "all_accepted": all(report["accepted"] for report in reports),
        "samples": reports,
    }
    validation_path = SOURCE_ROOT / "validation-report.json"
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(validation_path, STATIC_ROOT / "validation-report.json")
    if not validation["all_accepted"]:
        rejected = [
            f"{row['group']}:{row['sample']}" for row in reports
            if not row["accepted"]
        ]
        raise ValueError(f"sample validation failed: {', '.join(rejected)}")
    print(f"published {len(reports)} samples to {STATIC_ROOT}")


if __name__ == "__main__":
    build()
