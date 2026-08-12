#!/usr/bin/env python3
"""Build Sherry Ranger as a lighter predecessor to her High Master."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    load_identity_mask_overrides,
    protected_eye_points,
)


SOURCE = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "shared-high-master-elwin-swordmaster-v1/logical16/04-23.png"
)
SOURCE_DIR = ROOT / "assets/class-sprites/source/latest/sherry-ranger-v3"
ORIGINAL = ROOT / "editor/static/class-sprites/commanders/4/21-p1.png"
CLASS_ID = 0x21
COMMANDER_ID = 4
INK = (36, 36, 36, 255)
WHITE = (255, 255, 255, 255)
GOLD = (255, 182, 0, 255)
CYAN = (109, 219, 255, 255)
TEAL = (0, 109, 146, 255)
MID_TEAL = (36, 109, 146, 255)
RESAMPLING = getattr(Image, "Resampling", Image)

# The High Master carries ornate equipment on both sides. Ranger keeps the
# same body scale and palette, but the former left blade becomes a layered
# cyan cloak and only one clean white blade remains on the right.
RIGHT_BLADE_WHITE_POINTS = {
    (15, 8), (15, 9), (14, 10), (15, 10), (15, 11),
    (14, 12), (15, 12), (14, 13), (15, 13),
    (14, 14), (15, 14), (15, 15),
}
RIGHT_BLADE_OUTLINE_POINTS = {
    (14, 8), (14, 9), (13, 10), (14, 11),
    (13, 12), (13, 13), (13, 14), (14, 15),
}
RIGHT_BLADE_HILT_POINTS = {(12, 10), (13, 9), (13, 11)}


def build() -> dict[str, object]:
    image = Image.open(SOURCE).convert("RGBA")
    original = Image.open(ORIGINAL).convert("RGBA")

    # Convert the elaborate left weapon into a readable two-tone short cloak.
    for y in range(8, 16):
        for x in range(0, 6):
            color = image.getpixel((x, y))
            if color == WHITE:
                image.putpixel((x, y), CYAN)
            elif color == GOLD:
                image.putpixel((x, y), TEAL)

    # Reduce gold density through the torso so Ranger reads one tier below
    # High Master even though both retain Sherry's blue/cyan color language.
    for y in range(8, 14):
        for x in range(4, 12):
            if image.getpixel((x, y)) == GOLD:
                image.putpixel((x, y), MID_TEAL)

    for point in RIGHT_BLADE_WHITE_POINTS:
        image.putpixel(point, WHITE)
    for point in RIGHT_BLADE_OUTLINE_POINTS:
        image.putpixel(point, INK)
    for point in RIGHT_BLADE_HILT_POINTS:
        image.putpixel(point, GOLD)

    masks = load_identity_mask_overrides()
    identity = set(masks[(COMMANDER_ID, CLASS_ID)]) | protected_eye_points(
        original
    )
    visible_identity = {
        point for point in identity if original.getpixel(point)[3]
    }
    for point in visible_identity:
        image.putpixel(point, original.getpixel(point))

    colors = Counter(color for color in image.getdata() if color[3])
    empty_rows = [
        y for y in range(16)
        if not any(image.getpixel((x, y))[3] for x in range(16))
    ]
    empty_columns = [
        x for x in range(16)
        if not any(image.getpixel((x, y))[3] for y in range(16))
    ]
    identity_match = sum(
        image.getpixel(point) == original.getpixel(point)
        for point in visible_identity
    )
    pure_black = sum(
        image.getpixel((x, y)) == (0, 0, 0, 255)
        for y in range(16)
        for x in range(16)
    )
    report = {
        "version": 3,
        "source": str(SOURCE.relative_to(ROOT)),
        "target": "04-21",
        "identity_match": identity_match,
        "identity_pixel_count": len(visible_identity),
        "visible_color_count": len(colors),
        "palette": [
            "#{:02x}{:02x}{:02x}".format(*color[:3])
            for color, _ in colors.most_common()
        ],
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "pure_black_pixels": pure_black,
        "accepted": (
            identity_match == len(visible_identity)
            and len(colors) <= 15
            and not empty_rows
            and not empty_columns
            and pure_black == 0
        ),
    }

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    image.save(SOURCE_DIR / "04-21.png", optimize=True)
    image.resize((512, 512), RESAMPLING.NEAREST).save(
        SOURCE_DIR / "04-21-preview.png",
        optimize=True,
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
