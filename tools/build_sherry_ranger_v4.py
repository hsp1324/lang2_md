#!/usr/bin/env python3
"""Build Sherry Ranger from the exact approved High Master design."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (  # noqa: E402
    load_identity_mask_overrides,
    protected_eye_points,
)


SOURCE = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "shared-high-master-elwin-swordmaster-v1/logical16/04-23.png"
)
SOURCE_DIR = ROOT / "docs/assets/ai-class-source/latest/sherry-ranger-v4"
LOGICAL_DIR = SOURCE_DIR / "logical16"
PREVIEW_DIR = SOURCE_DIR / "previews"
ORIGINAL = ROOT / "editor/static/class-sprites/commanders/4/21-p1.png"
CLASS_ID = 0x21
COMMANDER_ID = 4
TRANSPARENT = (0, 0, 0, 0)
RESAMPLING = getattr(Image, "Resampling", Image)

# Keep the approved High Master pixel layout exactly.  Ranger receives a
# quieter blue-steel ramp and pale gold trim so the two tiers remain readable
# without weakening either shoulder, blade, or cape silhouette.
RANGER_RECOLOR = {
    (0, 36, 73, 255): (36, 36, 109, 255),
    (0, 109, 146, 255): (36, 73, 219, 255),
    (36, 109, 146, 255): (73, 109, 219, 255),
    (109, 219, 255, 255): (146, 182, 255, 255),
    (255, 182, 0, 255): (219, 182, 109, 255),
}


def visible_palette(image: Image.Image) -> Counter[tuple[int, int, int, int]]:
    return Counter(color for color in image.get_flattened_data() if color[3])


def build() -> dict[str, object]:
    high_master = Image.open(SOURCE).convert("RGBA")
    original = Image.open(ORIGINAL).convert("RGBA")
    masks = load_identity_mask_overrides()
    identity = set(masks[(COMMANDER_ID, CLASS_ID)]) | protected_eye_points(
        original
    )
    visible_identity = {
        point for point in identity if original.getpixel(point)[3]
    }

    ranger = high_master.copy()
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if point not in visible_identity:
                color = high_master.getpixel(point)
                ranger.putpixel(point, RANGER_RECOLOR.get(color, color))
    for point in visible_identity:
        ranger.putpixel(point, original.getpixel(point))

    colors = visible_palette(ranger)
    identity_match = sum(
        ranger.getpixel(point) == original.getpixel(point)
        for point in visible_identity
    )
    shape_match = sum(
        bool(ranger.getpixel((x, y))[3])
        == bool(high_master.getpixel((x, y))[3])
        for y in range(16)
        for x in range(16)
        if (x, y) not in identity
    )
    shape_total = 256 - len(identity)
    equipment_color_differences = sum(
        ranger.getpixel((x, y)) != high_master.getpixel((x, y))
        for y in range(16)
        for x in range(16)
        if (x, y) not in identity
        and high_master.getpixel((x, y))[3]
    )
    empty_rows = [
        y
        for y in range(16)
        if not any(ranger.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x
        for x in range(16)
        if not any(ranger.getpixel((x, y))[3] for y in range(16))
    ]
    pure_black = sum(
        ranger.getpixel((x, y)) == (0, 0, 0, 255)
        for y in range(16)
        for x in range(16)
    )
    report = {
        "version": 4,
        "source": str(SOURCE.relative_to(ROOT)),
        "target": "04-21",
        "design_rule": "exact High Master shape; Ranger palette only",
        "identity_match": identity_match,
        "identity_pixel_count": len(visible_identity),
        "template_shape_match": shape_match,
        "template_shape_total": shape_total,
        "equipment_color_differences": equipment_color_differences,
        "visible_color_count": len(colors),
        "palette": [
            "#{:02x}{:02x}{:02x}".format(*color[:3])
            for color, _ in colors.most_common()
        ],
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black_pixels": pure_black,
    }
    report["accepted"] = (
        identity_match == len(visible_identity)
        and shape_match == shape_total
        and equipment_color_differences >= 24
        and len(colors) <= 15
        and not empty_rows
        and not empty_columns
        and pure_black == 0
    )

    LOGICAL_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    ranger.save(LOGICAL_DIR / "04-21.png", optimize=True)
    ranger.resize((512, 512), RESAMPLING.NEAREST).save(
        PREVIEW_DIR / "04-21.png", optimize=True
    )
    comparison = Image.new("RGBA", (1040, 560), (22, 25, 23, 255))
    draw = ImageDraw.Draw(comparison)
    draw.text((20, 16), "High Master template", fill=(235, 240, 236, 255))
    draw.text((540, 16), "Ranger palette", fill=(235, 240, 236, 255))
    comparison.alpha_composite(
        high_master.resize((512, 512), RESAMPLING.NEAREST), (0, 48)
    )
    comparison.alpha_composite(
        ranger.resize((512, 512), RESAMPLING.NEAREST), (528, 48)
    )
    comparison.convert("RGB").save(
        SOURCE_DIR / "high-master-ranger-comparison.png", optimize=True
    )
    (SOURCE_DIR / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    report = build()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
