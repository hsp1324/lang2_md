#!/usr/bin/env python3
"""Normalize Elwin mounted imagegen drafts with exact face and mount locks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    ROM_INK,
    identity_locked_character_sprite,
    load_identity_mask_overrides,
    load_mount_mask_overrides,
    quantize_16_color_rgba,
    remove_magenta_background,
)


RESAMPLING = getattr(Image, "Resampling", Image)
MAGENTA = (255, 0, 255, 255)
GUIDE_DIR = (
    ROOT / "docs/assets/ai-class-source/latest/elwin-mounted-v2/guides"
)
CLASS_FILES = {
    0x0C: "0C-highlander.png",
    0x1D: "1D-silver-knight.png",
}
LEFT_EDGE_WEAPON_EXTENSIONS = {
    0x0C: ((0, 2), (1, 2)),
    0x1D: ((0, 11), (1, 11)),
}


def logical_original(class_id: int) -> Image.Image:
    path = GUIDE_DIR / f"{class_id:02X}-original-full-ratio.png"
    return remove_magenta_background(
        Image.open(path).convert("RGBA").resize(
            (16, 16),
            RESAMPLING.NEAREST,
        )
    )


def magenta_canvas(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", image.size, MAGENTA)
    canvas.alpha_composite(image)
    return canvas


def occupied_axes(
    image: Image.Image,
) -> tuple[list[int], list[int]]:
    columns = [
        x
        for x in range(16)
        if any(image.getpixel((x, y))[3] for y in range(16))
    ]
    rows = [
        y
        for y in range(16)
        if any(image.getpixel((x, y))[3] for x in range(16))
    ]
    return columns, rows


def normalize_one(
    *,
    class_id: int,
    raw_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    key = (1, class_id)
    identity_points = load_identity_mask_overrides()[key]
    mount_points = load_mount_mask_overrides()[key]
    original = logical_original(class_id)
    raw = remove_magenta_background(
        Image.open(raw_path).convert("RGBA")
    )
    generated_16 = quantize_16_color_rgba(
        raw.resize((16, 16), RESAMPLING.NEAREST)
    )
    converted, changed, _, _ = (
        identity_locked_character_sprite(
            generated_16,
            original,
            [ROM_INK],
            identity_points,
            additional_locked_points=mount_points,
            preserve_generated_palette=True,
        )
    )
    destination, source = LEFT_EDGE_WEAPON_EXTENSIONS[class_id]
    locked_union = identity_points | mount_points
    if destination not in locked_union:
        converted.putpixel(destination, converted.getpixel(source))
    changed = sum(
        converted.getpixel((x, y)) != original.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )

    logical_dir = output_dir / "logical16"
    logical_dir.mkdir(parents=True, exist_ok=True)
    filename = CLASS_FILES[class_id]
    logical_path = logical_dir / filename
    source_path = output_dir / filename
    magenta_canvas(converted).save(logical_path, optimize=True)
    magenta_canvas(
        converted.resize((1024, 1024), RESAMPLING.NEAREST)
    ).save(source_path, optimize=True)

    identity_matches = sum(
        converted.getpixel(point) == original.getpixel(point)
        for point in identity_points
    )
    mount_matches = sum(
        converted.getpixel(point) == original.getpixel(point)
        for point in mount_points
    )
    visible_colors = {
        color
        for _, color in converted.getcolors(maxcolors=256) or []
        if color[3]
    }
    columns, rows = occupied_axes(converted)
    pure_black_pixels = sum(
        converted.getpixel((x, y)) == (0, 0, 0, 255)
        for y in range(16)
        for x in range(16)
    )
    accepted = (
        identity_matches == len(identity_points)
        and mount_matches == len(mount_points)
        and len(visible_colors) <= 15
        and columns == list(range(16))
        and rows == list(range(16))
        and pure_black_pixels == 0
    )
    return {
        "class_id": f"{class_id:02X}",
        "raw": str(raw_path.relative_to(ROOT)),
        "logical16": str(logical_path.relative_to(ROOT)),
        "source": str(source_path.relative_to(ROOT)),
        "identity_matches": identity_matches,
        "identity_points": len(identity_points),
        "mount_matches": mount_matches,
        "mount_points": len(mount_points),
        "locked_union_points": len(locked_union),
        "changed_pixels_from_original": changed,
        "visible_colors": len(visible_colors),
        "occupied_columns": columns,
        "occupied_rows": rows,
        "pure_black_pixels": pure_black_pixels,
        "accepted": accepted,
    }


def write_comparison(
    output_dir: Path,
    reports: list[dict[str, object]],
) -> Path:
    card_width = 360
    card_height = 350
    canvas = Image.new(
        "RGB",
        (card_width * len(reports), card_height),
        (24, 24, 24),
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, report in enumerate(reports):
        left = index * card_width
        class_id = int(report["class_id"], 16)
        sprite = Image.open(ROOT / report["logical16"]).convert("RGB")
        sprite = sprite.resize((320, 320), RESAMPLING.NEAREST)
        canvas.paste(sprite, (left + 20, 20))
        draw.text(
            (left + 20, 4),
            (
                f"{report['class_id']} "
                f"{'HIGHLANDER' if class_id == 0x0C else 'SILVER KNIGHT'}"
            ),
            fill=(245, 245, 245),
            font=font,
        )
        draw.text(
            (left + 20, 335),
            (
                f"face {report['identity_matches']}/"
                f"{report['identity_points']}  mount "
                f"{report['mount_matches']}/{report['mount_points']}  "
                f"colors {report['visible_colors']}"
            ),
            fill=(150, 220, 160),
            font=font,
        )
    path = output_dir / "all-elwin-mounted-v2.png"
    canvas.save(path, optimize=True)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT
            / "docs/assets/ai-class-source/latest/elwin-mounted-v2"
        ),
    )
    parser.add_argument(
        "--highlander-raw",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--silver-knight-raw",
        type=Path,
        required=True,
    )
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = [
        normalize_one(
            class_id=0x0C,
            raw_path=args.highlander_raw.resolve(),
            output_dir=output_dir,
        ),
        normalize_one(
            class_id=0x1D,
            raw_path=args.silver_knight_raw.resolve(),
            output_dir=output_dir,
        ),
    ]
    comparison_path = write_comparison(output_dir, reports)
    document = {
        "all_accepted": all(report["accepted"] for report in reports),
        "comparison": str(comparison_path.relative_to(ROOT)),
        "classes": reports,
    }
    (output_dir / "validation-report.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return 0 if document["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
