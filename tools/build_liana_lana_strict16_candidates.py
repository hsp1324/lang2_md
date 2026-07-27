#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import colorsys
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    ROM_INK,
    mega_drive_palette_color,
)
from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.build_liana_lana_native16_assets import (
    is_generation_background,
    limit_visible_palette,
    restore_identity_pixels,
    use_outer_canvas,
    visible_palette,
)


OUTPUT_ROOT = (
    ROOT
    / "docs/assets/ai-class-source/latest/liana-lana-strict16-v1"
)
MASK_PATH = ROOT / "editor/ai_identity_masks.json"
TRANSPARENT = (0, 0, 0, 0)
RESAMPLING = getattr(Image, "Resampling", Image)

SELECTED_CANDIDATES = {
    0x08: "08-healer/variant-02.png",
    0x0B: "0B-high-lord/variant-01.png",
    0x11: "11-priest/variant-01.png",
    0x13: "13-mage/variant-01.png",
    0x14: "14-archmage/variant-02.png",
    0x15: "15-wizard/variant-02.png",
    0x16: "16-high-priest/variant-05.png",
    0x18: "18-sage/variant-01.png",
    0x19: "19-paladin/variant-04.png",
    0x1D: "1D-silver-knight/variant-04.png",
    0x28: "28-summoner/variant-01.png",
}


def strict_cell_sample(
    image: Image.Image,
) -> tuple[Image.Image, float]:
    """Read only the fixed 16 equal cells; never crop or resize a subject."""

    source = image.convert("RGBA")
    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    uniformity: list[float] = []
    for logical_y in range(16):
        top = round(logical_y * source.height / 16)
        bottom = round((logical_y + 1) * source.height / 16)
        for logical_x in range(16):
            left = round(logical_x * source.width / 16)
            right = round((logical_x + 1) * source.width / 16)
            region = source.crop((left, top, right, bottom))
            step = max(1, min(region.width, region.height) // 24)
            pixels = [
                region.getpixel((x, y))
                for y in range(0, region.height, step)
                for x in range(0, region.width, step)
            ]
            categorized = Counter()
            foreground = Counter()
            for color in pixels:
                if is_generation_background(color):
                    categorized[TRANSPARENT] += 1
                    continue
                snapped = mega_drive_palette_color(color)
                if snapped[:3] == (0, 0, 0):
                    snapped = ROM_INK
                categorized[snapped] += 1
                foreground[snapped] += 1
            dominant_count = categorized.most_common(1)[0][1]
            uniformity.append(dominant_count / len(pixels))
            foreground_count = sum(foreground.values())
            if foreground_count / len(pixels) < 0.52:
                continue
            result.putpixel(
                (logical_x, logical_y),
                foreground.most_common(1)[0][0],
            )
    return result, sum(uniformity) / len(uniformity)


def lock_high_resolution_identity(
    candidate: Image.Image,
    guide: Image.Image,
    identity_points: set[tuple[int, int]],
) -> Image.Image:
    """Lock the exact saved face cells before native16 conversion."""

    result = candidate.convert("RGBA").copy()
    fixed = guide.convert("RGBA").resize(
        result.size,
        RESAMPLING.NEAREST,
    )
    for logical_x, logical_y in identity_points:
        left = round(logical_x * result.width / 16)
        right = round((logical_x + 1) * result.width / 16)
        top = round(logical_y * result.height / 16)
        bottom = round((logical_y + 1) * result.height / 16)
        result.paste(
            fixed.crop((left, top, right, bottom)),
            (left, top),
        )
    return result


def blue_equipment_pair(
    red: Image.Image,
    identity_points: set[tuple[int, int]],
    blue_original: Image.Image,
) -> Image.Image:
    """Make Lana blue while preserving gold, brown, skin, and identity."""

    result = red.convert("RGBA").copy()
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if point in identity_points:
                result.putpixel(point, blue_original.getpixel(point))
                continue
            red_value, green, blue_value, alpha = result.getpixel(point)
            if (
                not alpha
                or red_value < green + 36
                or red_value < blue_value + 36
                or red_value < 109
            ):
                continue
            _, saturation, value = colorsys.rgb_to_hsv(
                red_value / 255,
                green / 255,
                blue_value / 255,
            )
            converted = colorsys.hsv_to_rgb(
                0.62,
                min(1.0, max(0.55, saturation)),
                value,
            )
            result.putpixel(
                point,
                mega_drive_palette_color(
                    (
                        round(converted[0] * 255),
                        round(converted[1] * 255),
                        round(converted[2] * 255),
                        alpha,
                    )
                ),
            )
    return result


def write_preview(image: Image.Image, path: Path) -> None:
    preview = Image.new("RGBA", (256, 256), (232, 232, 232, 255))
    preview.alpha_composite(
        image.resize((256, 256), RESAMPLING.NEAREST)
    )
    preview.convert("RGB").save(path, optimize=True)


def main() -> None:
    rom = DEFAULT_ROM.read_bytes()
    masks = json.loads(MASK_PATH.read_text(encoding="utf-8"))["masks"]
    identity_points = {
        tuple(point)
        for point in masks["2:18"]
    }
    originals: dict[int, dict[int, Image.Image]] = {}
    for commander_id in (2, 3):
        sprite_map = commander_sprite_map(rom, commander_id)
        originals[commander_id] = {
            class_id: render_sprite(
                rom,
                sprite_map[class_id],
                1,
            )
            for class_id in SELECTED_CANDIDATES
        }
    healer_reference = originals[2][0x08]

    for directory in (
        OUTPUT_ROOT / "native16-red",
        OUTPUT_ROOT / "native16-blue",
        OUTPUT_ROOT / "previews-red",
        OUTPUT_ROOT / "previews-blue",
        OUTPUT_ROOT / "selected-sources",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    report_rows: list[dict[str, object]] = []
    for class_id, relative_candidate in SELECTED_CANDIDATES.items():
        class_text = f"{class_id:02X}"
        candidate_path = OUTPUT_ROOT / "candidates" / relative_candidate
        candidate = Image.open(candidate_path).convert("RGBA")
        raw_sampled, _ = strict_cell_sample(candidate)
        raw_prelock_exact = sum(
            raw_sampled.getpixel(point)
            == healer_reference.getpixel(point)
            for point in identity_points
        )
        raw_prelock_alpha_exact = sum(
            bool(raw_sampled.getpixel(point)[3])
            == bool(healer_reference.getpixel(point)[3])
            for point in identity_points
        )
        # The Sage mask is the user's latest canonical face boundary. Use
        # the clean ROM pixels directly so newly added mask cells can never
        # inherit magenta guide background.
        guide = healer_reference
        selected_source = lock_high_resolution_identity(
            candidate,
            guide,
            identity_points,
        )
        selected_source_path = (
            OUTPUT_ROOT / "selected-sources" / f"{class_text}.png"
        )
        selected_source.save(selected_source_path, optimize=True)
        sampled, grid_uniformity = strict_cell_sample(selected_source)
        selected_prelock_exact = sum(
            sampled.getpixel(point)
            == healer_reference.getpixel(point)
            for point in identity_points
        )
        red = restore_identity_pixels(
            sampled,
            originals[2][class_id],
            identity_points,
        )
        red = use_outer_canvas(red, class_id, identity_points)
        red, red_palette_remapped = limit_visible_palette(
            red,
            identity_points,
        )
        blue = blue_equipment_pair(
            red,
            identity_points,
            originals[3][class_id],
        )
        blue = use_outer_canvas(blue, class_id, identity_points)
        blue, blue_palette_remapped = limit_visible_palette(
            blue,
            identity_points,
        )

        red_path = OUTPUT_ROOT / "native16-red" / f"{class_text}.png"
        blue_path = OUTPUT_ROOT / "native16-blue" / f"{class_text}.png"
        red.save(red_path, optimize=True)
        blue.save(blue_path, optimize=True)
        write_preview(
            red,
            OUTPUT_ROOT / "previews-red" / f"{class_text}.png",
        )
        write_preview(
            blue,
            OUTPUT_ROOT / "previews-blue" / f"{class_text}.png",
        )

        head_exact = all(
            red.getpixel(point)
            == originals[2][class_id].getpixel(point)
            and blue.getpixel(point)
            == originals[3][class_id].getpixel(point)
            for point in identity_points
        )
        report_rows.append(
            {
                "class_id": class_text,
                "selected_candidate": relative_candidate,
                "selected_locked_source": (
                    f"selected-sources/{class_text}.png"
                ),
                "source_size": list(candidate.size),
                "grid_cell_uniformity": round(grid_uniformity, 4),
                "raw_candidate_identity_exact_pixels": (
                    raw_prelock_exact
                ),
                "raw_candidate_identity_alpha_exact_pixels": (
                    raw_prelock_alpha_exact
                ),
                "selected_source_identity_exact_pixels": (
                    selected_prelock_exact
                ),
                "identity_pixel_count": len(identity_points),
                "head_exact_after_lock": head_exact,
                "pair_alpha_equal": (
                    red.getchannel("A").tobytes()
                    == blue.getchannel("A").tobytes()
                ),
                "bbox": list(red.getchannel("A").getbbox() or ()),
                "used_rows": sum(
                    any(red.getpixel((x, y))[3] for x in range(16))
                    for y in range(16)
                ),
                "used_columns": sum(
                    any(red.getpixel((x, y))[3] for y in range(16))
                    for x in range(16)
                ),
                "red_visible_colors": len(visible_palette(red)),
                "blue_visible_colors": len(visible_palette(blue)),
                "red_palette_remapped_pixels": red_palette_remapped,
                "blue_palette_remapped_pixels": blue_palette_remapped,
            }
        )

    comparison = Image.new(
        "RGB",
        (860, 55 + len(SELECTED_CANDIDATES) * 270),
        (238, 238, 238),
    )
    draw = ImageDraw.Draw(comparison)
    draw.text(
        (12, 16),
        "selected strict-grid AI | Liana red native16 | Lana blue native16",
        fill=(24, 24, 24),
    )
    for index, (class_id, relative_candidate) in enumerate(
        SELECTED_CANDIDATES.items()
    ):
        class_text = f"{class_id:02X}"
        y = 55 + index * 270
        draw.text((8, y + 115), class_text, fill=(24, 24, 24))
        candidate = Image.open(
            OUTPUT_ROOT / "selected-sources" / f"{class_text}.png"
        ).convert("RGB")
        candidate.thumbnail((240, 240), RESAMPLING.NEAREST)
        red = Image.open(
            OUTPUT_ROOT / "previews-red" / f"{class_text}.png"
        ).convert("RGB")
        blue = Image.open(
            OUTPUT_ROOT / "previews-blue" / f"{class_text}.png"
        ).convert("RGB")
        comparison.paste(candidate, (55, y + 10))
        comparison.paste(red, (315, y + 10))
        comparison.paste(blue, (585, y + 10))
    comparison.save(
        OUTPUT_ROOT / "strict16-ai-and-native16-comparison.png",
        optimize=True,
    )

    report = {
        "version": 1,
        "mode": (
            "1254px fixed 16-cell guide; whole-canvas 16-cell majority "
            "sampling; exact shared 82-pixel Liana Sage face restoration"
        ),
        "classes": report_rows,
        "all_head_exact": all(
            row["head_exact_after_lock"] for row in report_rows
        ),
        "all_pair_alpha_equal": all(
            row["pair_alpha_equal"] for row in report_rows
        ),
        "all_4bpp": all(
            row["red_visible_colors"] <= 15
            and row["blue_visible_colors"] <= 15
            for row in report_rows
        ),
        "all_full_canvas": all(
            row["bbox"] == [0, 0, 16, 16]
            and row["used_rows"] == 16
            and row["used_columns"] == 16
            for row in report_rows
        ),
    }
    (OUTPUT_ROOT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        OUTPUT_ROOT,
        len(report_rows),
        "strict16 red/blue pairs",
    )


if __name__ == "__main__":
    main()
