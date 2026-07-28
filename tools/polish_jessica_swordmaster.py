#!/usr/bin/env python3
"""Polish small gaps in Jessica's saved Swordmaster editor design.

The current user-edited head position, sword, palette, and silhouette remain
the baseline. This updates preview assets only and never writes a ROM.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from editor.server import design_palette  # noqa: E402
from tools.build_ai_class_sprite_assets import ASSET_VERSION  # noqa: E402
from tools.build_class_sprite_assets import render_sprite  # noqa: E402


COMMANDER_ID = 10
CLASS_ID = 0x1A
DESIGN_KEY = "10:1A"
ASSET_DIR = ROOT / "editor/static/ai-class-sprites"
TARGET_PATH = ASSET_DIR / "10/1A.png"
MANIFEST_PATH = ASSET_DIR / "manifest.json"
DESIGN_PATH = ROOT / "editor/ai_class_design_overrides.json"
ARCHIVE_PATH = (
    ROOT
    / "docs/assets/ai-class-source/archive/"
    "jessica-swordmaster-before-polish-v1/"
    "10-1A-editor-v62.png"
)

INK = (36, 36, 36, 255)
DARK_RED = (109, 0, 0, 255)
RED = (219, 0, 0, 255)
SKIN = (219, 182, 109, 255)
STEEL = (146, 146, 182, 255)

# Only bridge obvious one-pixel holes between the existing shoulder, torso,
# waist armor, and cape. Head, sword, boots, and outer silhouette are untouched.
POLISH_PIXELS = {
    (7, 6): INK,
    (5, 7): SKIN,
    (11, 7): STEEL,
    (6, 8): SKIN,
    (4, 9): DARK_RED,
    (5, 9): DARK_RED,
    (6, 9): DARK_RED,
    (7, 9): INK,
    (8, 9): INK,
    (9, 9): INK,
    (10, 9): INK,
    (11, 9): DARK_RED,
    (12, 9): INK,
    (4, 10): DARK_RED,
    (4, 13): DARK_RED,
    (5, 13): DARK_RED,
    (8, 13): DARK_RED,
    (9, 13): DARK_RED,
    (10, 13): DARK_RED,
    (11, 13): RED,
    (12, 13): DARK_RED,
}


def write_json(path: Path, document: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def polish() -> None:
    if not TARGET_PATH.is_file():
        raise FileNotFoundError(TARGET_PATH)
    if not ARCHIVE_PATH.exists():
        ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TARGET_PATH, ARCHIVE_PATH)

    image = Image.open(TARGET_PATH).convert("RGBA")
    before = image.copy()
    for point, color in POLISH_PIXELS.items():
        image.putpixel(point, color)
    changed_points = {
        point
        for point in POLISH_PIXELS
        if before.getpixel(point) != image.getpixel(point)
    }
    if len(changed_points) < 16:
        raise ValueError(
            "Jessica Swordmaster polish changed too few pixels: "
            f"{len(changed_points)}"
        )
    visible_colors = {
        color for color in image.getdata() if color[3]
    }
    if len(visible_colors) > 15:
        raise ValueError(
            f"Jessica Swordmaster exceeds 15 colors: {len(visible_colors)}"
        )
    if image.getchannel("A").getbbox() != (0, 0, 16, 16):
        raise ValueError("Jessica Swordmaster must occupy the full canvas")

    temporary_image = TARGET_PATH.with_suffix(".png.tmp")
    image.save(temporary_image, format="PNG", optimize=True)
    temporary_image.replace(TARGET_PATH)

    design_document = json.loads(
        DESIGN_PATH.read_text(encoding="utf-8")
    )
    existing = design_document["designs"].get(DESIGN_KEY, {})
    revision = time.time_ns()
    pixels = [list(pixel) for pixel in image.getdata()]
    design_document["designs"][DESIGN_KEY] = {
        "revision": revision,
        "pixels": pixels,
        "base_pixels": existing.get("base_pixels", pixels),
    }
    write_json(DESIGN_PATH, design_document)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    row = manifest["commanders"][str(COMMANDER_ID)]["classes"][
        str(CLASS_ID)
    ]
    rom_path = ROOT / manifest["generated_from"]
    rom_source = rom_path.read_bytes()
    original = render_sprite(
        rom_source,
        int(row["face_source_sprite_id"]),
        1,
    )
    row["changed_pixel_count"] = sum(
        image.getpixel((x, y)) != original.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )
    row["pixel_palette"] = design_palette(pixels)
    row["design_override"] = True
    row["design_revision"] = revision
    row["design_override_superseded"] = False
    row["superseded_design_revision"] = 0
    row["identity_translation_applied_in_override"] = True
    marker = (
        "·사용자 저장본의 끊긴 몸통·오른쪽 소매·하단 망토 "
        f"연결 {len(changed_points)}픽셀 소폭 보정"
    )
    feature = str(row.get("feature", ""))
    if marker not in feature:
        row["feature"] = feature + marker
    manifest["asset_version"] = ASSET_VERSION
    write_json(MANIFEST_PATH, manifest)

    print(json.dumps({
        "asset_version": ASSET_VERSION,
        "changed_pixel_count": len(changed_points),
        "visible_color_count": len(visible_colors),
        "identity_translation_applied_in_override": True,
        "archive": str(ARCHIVE_PATH.relative_to(ROOT)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    polish()
