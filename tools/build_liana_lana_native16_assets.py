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
    identity_locked_character_sprite,
    mega_drive_palette_color,
    remove_ai_border_colors,
)
from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.build_test_class_sprite_assets import class_tiers


OUTPUT_ROOT = (
    ROOT
    / "assets/class-sprites/source/latest/liana-lana-paired"
)
MASK_PATH = ROOT / "editor/ai_identity_masks.json"
TRANSPARENT = (0, 0, 0, 0)
RESAMPLING = getattr(Image, "Resampling", Image)

SOURCE_FILES = {
    0x08: "08-healer-ai.png",
    0x0B: "0B-high-lord-ai.png",
    0x11: "11-priest-ai.png",
    0x13: "13-mage-ai.png",
    0x14: "14-archmage-ai.png",
    0x15: "15-wizard-ai.png",
    0x16: "16-high-priest-ai.png",
    0x18: "18-sage-ai.png",
    0x19: "19-paladin-ai.png",
    0x1D: "1D-silver-knight-ai.png",
    0x28: "28-summoner-ai.png",
}


def sage_face_reference_points(
    masks: dict[str, list[list[int]]],
) -> set[tuple[int, int]]:
    """Use the user's latest Liana Sage face mask without pruning it.

    Sage is the canonical coordinate mask for every Liana/Lana redesign.
    Each class still restores its own ROM pixels at these coordinates, so
    mounted and standing poses keep their class-specific original drawing.
    """

    return {
        tuple(point)
        for point in masks["2:18"]
    }


def is_generation_background(
    color: tuple[int, int, int, int],
) -> bool:
    red, green, blue, alpha = color
    if not alpha:
        return True
    bright_key = (
        red >= 145
        and blue >= 145
        and green <= 115
        and red + blue >= 330
    )
    dark_fringe = (
        red >= 36
        and blue >= 36
        and green * 2 < min(red, blue)
    )
    return bright_key or dark_fringe


def fixed_canvas_native16(image: Image.Image) -> Image.Image:
    """Read the AI's unchanged canvas as 16 logical cells.

    This deliberately does not crop a subject bounding box and does not
    resize that box to a square. Each destination pixel comes from the same
    fixed 1/16 canvas region, so a wide horse or narrow robe keeps its
    original proportions.
    """

    source = image.convert("RGBA")
    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    for logical_y in range(16):
        top = round(logical_y * source.height / 16)
        bottom = round((logical_y + 1) * source.height / 16)
        for logical_x in range(16):
            left = round(logical_x * source.width / 16)
            right = round((logical_x + 1) * source.width / 16)
            region = source.crop((left, top, right, bottom))
            step = max(1, min(region.width, region.height) // 24)
            sampled = [
                region.getpixel((x, y))
                for y in range(0, region.height, step)
                for x in range(0, region.width, step)
            ]
            foreground = [
                color
                for color in sampled
                if not is_generation_background(color)
            ]
            if not foreground:
                continue
            coverage = len(foreground) / len(sampled)
            if coverage < 0.06:
                continue
            snapped = Counter()
            for color in foreground:
                palette_color = mega_drive_palette_color(color)
                if palette_color[:3] == (0, 0, 0):
                    palette_color = ROM_INK
                snapped[palette_color] += 1
            result.putpixel(
                (logical_x, logical_y),
                snapped.most_common(1)[0][0],
            )
    return result


def red_equipment_pair(
    blue: Image.Image,
    identity_points: set[tuple[int, int]],
    red_original: Image.Image,
) -> Image.Image:
    """Create Liana by recoloring only Lana's blue equipment pixels."""

    result = blue.copy().convert("RGBA")
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if point in identity_points:
                result.putpixel(point, red_original.getpixel(point))
                continue
            red, green, blue_value, alpha = result.getpixel(point)
            if not alpha:
                continue
            hue, saturation, value = colorsys.rgb_to_hsv(
                red / 255,
                green / 255,
                blue_value / 255,
            )
            if (
                saturation >= 0.16
                and 0.48 <= hue <= 0.74
                and blue_value >= red
            ):
                target_hue = 0.985 if hue >= 0.62 else 0.01
                converted = colorsys.hsv_to_rgb(
                    target_hue,
                    min(1.0, saturation * 1.08),
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
    return remove_ai_border_colors(result, identity_points)


def use_outer_canvas(
    image: Image.Image,
    class_id: int,
    identity_points: set[tuple[int, int]],
) -> Image.Image:
    """Finish edge pixels without cropping or scaling the fixed canvas."""

    result = image.copy().convert("RGBA")
    if class_id == 0x1D:
        # The model placed the Silver Knight's lance beside the fixed head.
        # Clear that upper fragment and express the same weapon as a readable
        # one-pixel shaft at the far-right edge, joined at the rider's hand.
        for y in range(7):
            for x in range(12, 16):
                if (x, y) not in identity_points:
                    result.putpixel((x, y), TRANSPARENT)
        for y in range(7):
            result.putpixel(
                (15, y),
                (
                    (255, 255, 255, 255)
                    if y in {0, 2, 4}
                    else (146, 146, 146, 255)
                ),
            )
        result.putpixel((13, 7), (36, 36, 36, 255))
        result.putpixel((14, 7), (182, 109, 0, 255))
        result.putpixel((15, 7), (146, 146, 146, 255))

    alpha = result.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("native16 source is empty")
    left, _, right, bottom = bbox
    if bottom < 16:
        source_y = bottom - 1
        for x in range(16):
            color = result.getpixel((x, source_y))
            if color[3] and (x, 15) not in identity_points:
                result.putpixel((x, 15), color)
    if left > 0:
        candidates = [
            y
            for y in range(15, 6, -1)
            if result.getpixel((left, y))[3]
        ]
        if not candidates:
            candidates = [
                y
                for y in range(15, -1, -1)
                if result.getpixel((left, y))[3]
            ]
        if candidates:
            y = candidates[0]
            color = result.getpixel((left, y))
            for x in range(left):
                if (x, y) not in identity_points:
                    result.putpixel((x, y), color)
    bbox = result.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("native16 source vanished")
    right = bbox[2]
    if right < 16:
        edge_x = right - 1
        for y in range(16):
            color = result.getpixel((edge_x, y))
            if color[3] and (15, y) not in identity_points:
                result.putpixel((15, y), color)
    return result


def visible_palette(image: Image.Image) -> set[tuple[int, int, int, int]]:
    return {
        color
        for _, color in image.getcolors(maxcolors=256) or []
        if color[3]
    }


def write_preview(image: Image.Image, path: Path) -> None:
    preview = Image.new("RGBA", (512, 512), (232, 232, 232, 255))
    enlarged = image.resize((512, 512), RESAMPLING.NEAREST)
    preview.alpha_composite(enlarged)
    preview.convert("RGB").save(path, optimize=True)


def write_head_guide(
    original: Image.Image,
    points: set[tuple[int, int]],
    path: Path,
) -> None:
    guide = Image.new("RGBA", (16, 16), (207, 65, 225, 255))
    for point in points:
        guide.putpixel(point, original.getpixel(point))
    guide.resize((1024, 1024), RESAMPLING.NEAREST).save(
        path,
        optimize=True,
    )


def restore_identity_pixels(
    accepted_native16: Image.Image,
    original: Image.Image,
    points: set[tuple[int, int]],
) -> Image.Image:
    """Change only the shared mask; keep accepted AI equipment byte-exact."""

    result = accepted_native16.convert("RGBA").copy()
    if result.size != (16, 16):
        raise ValueError(
            f"accepted native source must be 16x16, got {result.size}"
        )
    for point in points:
        result.putpixel(point, original.getpixel(point))
    return result


def limit_visible_palette(
    image: Image.Image,
    protected_points: set[tuple[int, int]],
) -> tuple[Image.Image, int]:
    """Fit 4bpp by merging only the rarest unprotected equipment shade."""

    result = image.convert("RGBA").copy()
    remapped_pixels = 0
    while len(visible_palette(result)) > 15:
        protected_colors = {
            result.getpixel(point)
            for point in protected_points
            if result.getpixel(point)[3]
        }
        outside_counts = Counter(
            result.getpixel((x, y))
            for y in range(16)
            for x in range(16)
            if (
                (x, y) not in protected_points
                and result.getpixel((x, y))[3]
            )
        )
        candidates = [
            (count, color)
            for color, count in outside_counts.items()
            if color not in protected_colors
        ]
        if not candidates:
            raise ValueError(
                "cannot reduce visible palette without changing identity"
            )
        _, source_color = min(candidates)
        target_color = min(
            visible_palette(result) - {source_color},
            key=lambda color: (
                sum(
                    (source_color[index] - color[index]) ** 2
                    for index in range(3)
                ),
                color,
            ),
        )
        for y in range(16):
            for x in range(16):
                if (
                    (x, y) not in protected_points
                    and result.getpixel((x, y)) == source_color
                ):
                    result.putpixel((x, y), target_color)
                    remapped_pixels += 1
    return result, remapped_pixels


def main() -> None:
    rom = DEFAULT_ROM.read_bytes()
    masks = json.loads(MASK_PATH.read_text(encoding="utf-8"))["masks"]
    originals: dict[int, dict[int, Image.Image]] = {}
    points = sage_face_reference_points(masks)
    for commander_id in (2, 3):
        sprite_map = commander_sprite_map(rom, commander_id)
        tiers = class_tiers(rom, commander_id)
        originals[commander_id] = {
            class_id: render_sprite(rom, sprite_map[class_id], 1)
            for class_id in tiers
        }
    for directory in (
        OUTPUT_ROOT / "native16-blue",
        OUTPUT_ROOT / "native16-red",
        OUTPUT_ROOT / "preview-blue",
        OUTPUT_ROOT / "preview-red",
        OUTPUT_ROOT / "head-guides",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    report_rows: list[dict[str, object]] = []
    for class_id, source_filename in SOURCE_FILES.items():
        class_text = f"{class_id:02X}"
        source_path = OUTPUT_ROOT / "generation-evidence" / source_filename
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        blue_path = (
            OUTPUT_ROOT / "native16-blue" / f"{class_text}.png"
        )
        red_path = OUTPUT_ROOT / "native16-red" / f"{class_text}.png"
        blue = restore_identity_pixels(
            Image.open(blue_path),
            originals[3][class_id],
            points,
        )
        red = restore_identity_pixels(
            Image.open(red_path),
            originals[2][class_id],
            points,
        )
        blue, blue_palette_remapped = limit_visible_palette(
            blue,
            points,
        )
        red, red_palette_remapped = limit_visible_palette(
            red,
            points,
        )

        blue.save(blue_path, optimize=True)
        red.save(red_path, optimize=True)
        write_preview(
            blue,
            OUTPUT_ROOT / "preview-blue" / f"{class_text}.png",
        )
        write_preview(
            red,
            OUTPUT_ROOT / "preview-red" / f"{class_text}.png",
        )
        write_head_guide(
            originals[2][class_id],
            points,
            OUTPUT_ROOT
            / "head-guides"
            / f"{class_text}-head-only.png",
        )

        blue_alpha = blue.getchannel("A")
        red_alpha = red.getchannel("A")
        head_exact = all(
            blue.getpixel(point)
            == originals[3][class_id].getpixel(point)
            and red.getpixel(point)
            == originals[2][class_id].getpixel(point)
            for point in points
        )
        black_outside = any(
            blue.getpixel((x, y)) == (0, 0, 0, 255)
            or red.getpixel((x, y)) == (0, 0, 0, 255)
            for y in range(16)
            for x in range(16)
            if (x, y) not in points
        )
        report_rows.append(
            {
                "class_id": class_text,
                "source": source_filename,
                "head_lock_pixel_count": len(points),
                "head_exact": head_exact,
                "blue_red_alpha_equal": (
                    blue_alpha.tobytes() == red_alpha.tobytes()
                ),
                "bbox": list(blue_alpha.getbbox() or ()),
                "used_rows": sum(
                    any(blue.getpixel((x, y))[3] for x in range(16))
                    for y in range(16)
                ),
                "used_columns": sum(
                    any(blue.getpixel((x, y))[3] for y in range(16))
                    for x in range(16)
                ),
                "right_band_pixels": sum(
                    bool(blue.getpixel((x, y))[3])
                    for y in range(16)
                    for x in range(13, 16)
                ),
                "blue_visible_colors": len(visible_palette(blue)),
                "red_visible_colors": len(visible_palette(red)),
                "blue_palette_remapped_pixels": (
                    blue_palette_remapped
                ),
                "red_palette_remapped_pixels": red_palette_remapped,
                "black_outside_head": black_outside,
            }
        )

    comparison = Image.new(
        "RGB",
        (1180, 70 + len(SOURCE_FILES) * 270),
        (238, 238, 238),
    )
    draw = ImageDraw.Draw(comparison)
    draw.text(
        (12, 16),
        "fixed head guide | Lana native16 blue | Liana native16 red",
        fill=(24, 24, 24),
    )
    for index, class_id in enumerate(SOURCE_FILES):
        class_text = f"{class_id:02X}"
        y = 70 + index * 270
        draw.text((12, y + 110), class_text, fill=(24, 24, 24))
        guide = Image.open(
            OUTPUT_ROOT / "head-guides" / f"{class_text}-head-only.png"
        ).convert("RGBA")
        guide.thumbnail((240, 240), RESAMPLING.NEAREST)
        blue_preview = Image.open(
            OUTPUT_ROOT / "preview-blue" / f"{class_text}.png"
        ).convert("RGBA")
        red_preview = Image.open(
            OUTPUT_ROOT / "preview-red" / f"{class_text}.png"
        ).convert("RGBA")
        blue_preview = blue_preview.resize(
            (240, 240),
            RESAMPLING.NEAREST,
        )
        red_preview = red_preview.resize(
            (240, 240),
            RESAMPLING.NEAREST,
        )
        comparison.paste(guide.convert("RGB"), (120, y + 10))
        comparison.paste(blue_preview.convert("RGB"), (390, y + 10))
        comparison.paste(red_preview.convert("RGB"), (660, y + 10))
    comparison.save(
        OUTPUT_ROOT / "liana-lana-native16-comparison.png",
        optimize=True,
    )

    report = {
        "version": 1,
        "mode": (
            "accepted AI native16 body/equipment reused with the exact "
            "shared 82-pixel Liana Sage face mask; only a rare "
            "unprotected equipment shade may merge to satisfy 4bpp"
        ),
        "sage_face_reference_mask_pixel_count": len(points),
        "classes": report_rows,
        "all_head_exact": all(row["head_exact"] for row in report_rows),
        "all_pair_alpha_equal": all(
            row["blue_red_alpha_equal"] for row in report_rows
        ),
        "all_4bpp": all(
            row["blue_visible_colors"] <= 15
            and row["red_visible_colors"] <= 15
            for row in report_rows
        ),
        "all_no_generated_black": not any(
            row["black_outside_head"] for row in report_rows
        ),
    }
    (OUTPUT_ROOT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        OUTPUT_ROOT,
        len(report_rows),
        "native16 blue/red class pairs",
    )


if __name__ == "__main__":
    main()
