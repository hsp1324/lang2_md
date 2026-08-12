#!/usr/bin/env python3
"""Build the fresh AI-derived native 16x16 Elwin Hero v4 source."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "assets/class-sprites/source/latest/elwin-hero-ai-v4"
CANDIDATE = OUTPUT / "candidates/variant-02-selected-concept.png"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
ROM_SPRITE = ROOT / "editor/static/class-sprites/commanders/1/22-p1.png"

from tools.build_ai_class_sprite_assets import ROM_INK
from tools.build_liana_lana_native16_assets import (
    limit_visible_palette,
    restore_identity_pixels,
)
from tools.build_liana_lana_strict16_candidates import (
    lock_high_resolution_identity,
    strict_cell_sample,
)


def visible_palette(image: Image.Image) -> list[str]:
    counts = Counter(color for color in image.getdata() if color[3])
    return [
        "#{:02x}{:02x}{:02x}".format(*color[:3])
        for color, _ in counts.most_common()
    ]


def build() -> dict[str, object]:
    candidate = Image.open(CANDIDATE).convert("RGBA")
    original = Image.open(ROM_SPRITE).convert("RGBA")
    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    identity = {tuple(point) for point in masks["1:22"]}

    # Replace the high-resolution logical cells first. This keeps the AI
    # concept as the body/equipment source while preventing its approximate
    # face rendering from leaking into native output.
    selected = lock_high_resolution_identity(
        candidate,
        original,
        identity,
    )
    logical, grid_uniformity = strict_cell_sample(selected)
    image = restore_identity_pixels(logical, original, identity)
    image, palette_remapped = limit_visible_palette(image, identity)

    # The generated sword guard ended at x=1. Extend the same charcoal guard
    # by one native pixel so the weapon deliberately uses the full 16 columns.
    image.putpixel((0, 9), ROM_INK)

    palette = visible_palette(image)
    empty_rows = [
        y
        for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x
        for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    identity_match = sum(
        image.getpixel(point) == original.getpixel(point)
        for point in identity
    )
    if identity_match != len(identity):
        raise ValueError(
            f"Hero identity mismatch: {identity_match}/{len(identity)}"
        )
    if len(palette) > 15 or empty_rows or empty_columns:
        raise ValueError(
            f"invalid Hero v4: colors={len(palette)}, "
            f"rows={empty_rows}, columns={empty_columns}"
        )
    if (0, 0, 0, 255) in image.getdata():
        raise ValueError("Hero v4 must not contain pure black")

    logical_dir = OUTPUT / "logical16"
    preview_dir = OUTPUT / "previews"
    selected_dir = OUTPUT / "selected-sources"
    for directory in (logical_dir, preview_dir, selected_dir):
        directory.mkdir(parents=True, exist_ok=True)
    selected.save(selected_dir / "22-hero-ai.png", optimize=True)
    image.save(OUTPUT / "22-hero.png", optimize=True)
    image.save(logical_dir / "22-hero.png", optimize=True)
    image.resize((512, 512), Image.Resampling.NEAREST).save(
        preview_dir / "22-hero.png", optimize=True
    )

    current = Image.open(
        ROOT / "editor/static/ai-class-sprites/1/22.png"
    ).convert("RGBA")
    comparison = Image.new("RGBA", (768, 288), (210, 210, 210, 255))
    draw = ImageDraw.Draw(comparison)
    for index, (label, sprite) in enumerate(
        (("ROM", original), ("previous", current), ("AI v4 -> 16", image))
    ):
        comparison.alpha_composite(
            sprite.resize((256, 256), Image.Resampling.NEAREST),
            (index * 256, 32),
        )
        draw.text((index * 256 + 8, 8), label, fill=(24, 24, 24, 255))
    comparison.save(OUTPUT / "elwin-hero-v4-comparison.png", optimize=True)

    ai_native = Image.new("RGBA", (1024, 544), (210, 210, 210, 255))
    ai_native.alpha_composite(
        selected.resize((512, 512), Image.Resampling.NEAREST),
        (0, 32),
    )
    ai_native.alpha_composite(
        image.resize((512, 512), Image.Resampling.NEAREST),
        (512, 32),
    )
    draw = ImageDraw.Draw(ai_native)
    draw.text((8, 8), "selected AI concept", fill=(24, 24, 24, 255))
    draw.text((520, 8), "native 16x16", fill=(24, 24, 24, 255))
    ai_native.save(OUTPUT / "elwin-hero-ai-and-native16.png", optimize=True)

    report = {
        "source": str(CANDIDATE.relative_to(ROOT)),
        "source_size": list(candidate.size),
        "native_size": list(image.size),
        "mode": "whole-canvas fixed 16-cell majority sampling",
        "grid_uniformity": round(grid_uniformity, 6),
        "identity_match": identity_match,
        "identity_pixel_count": len(identity),
        "visible_color_count": len(palette),
        "palette": palette,
        "palette_remapped_pixels": palette_remapped,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black": False,
        "accepted": True,
    }
    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
