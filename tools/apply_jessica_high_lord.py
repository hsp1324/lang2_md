#!/usr/bin/env python3
"""Apply Hein's High Lord design to Jessica with a blue cape.

This updates editor preview assets and source metadata only. It never writes
or patches a ROM.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (  # noqa: E402
    ASSET_VERSION,
    ROM_INK,
    dominant_colors,
    identity_locked_character_sprite,
    protected_eye_points,
    translate_points,
    translate_selected_pixels,
)
from tools.build_class_sprite_assets import render_sprite  # noqa: E402
from tools.build_shared_hein_martial_variants import (  # noqa: E402
    JESSICA_HIGH_LORD_CAPE_DARK_POINTS,
    JESSICA_HIGH_LORD_CAPE_LIGHT_POINTS,
    JESSICA_HIGH_LORD_CAPE_POINTS,
    apply_variant_details,
    refresh_variant_report,
    visible_palette,
)


COMMANDER_ID = 10
CLASS_ID = 0x0B
MASK_KEY = "10:0B"
MASK_DONOR_KEY = "10:1A"
ASSET_DIR = ROOT / "editor/static/ai-class-sprites"
MANIFEST_PATH = ASSET_DIR / "manifest.json"
MASK_PATH = ROOT / "editor/ai_identity_masks.json"
DESIGN_PATH = ROOT / "editor/ai_class_design_overrides.json"
MASTER_PATH = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "shared-high-lord-hein-v1/master/"
    "hein-0B-high-lord-user-approved.png"
)
LOGICAL_PATH = (
    ROOT
    / "assets/class-sprites/source/latest/"
    "shared-high-lord-hein-v1/logical16/10-0B.png"
)
ORIGINAL_SPRITE_PATH = (
    ROOT / "editor/static/class-sprites/commanders/10/0B-p1.png"
)


def write_json(path: Path, document: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def apply() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mask_document = json.loads(MASK_PATH.read_text(encoding="utf-8"))
    masks = mask_document["masks"]
    identity_points = {
        tuple(point) for point in masks[MASK_DONOR_KEY]
    }
    if not identity_points:
        raise ValueError("Jessica identity mask donor is empty")
    masks[MASK_KEY] = [
        list(point) for point in sorted(identity_points)
    ]
    write_json(MASK_PATH, mask_document)

    rows = manifest["commanders"]
    hein_row = rows["5"]["classes"][str(CLASS_ID)]
    jessica_row = rows[str(COMMANDER_ID)]["classes"][str(CLASS_ID)]
    master_identity = {
        tuple(point) for point in hein_row["identity_lock_points"]
    }
    master = Image.open(MASTER_PATH).convert("RGBA")
    equipment = master.copy()
    for point in master_identity:
        equipment.putpixel(point, (0, 0, 0, 0))

    original = Image.open(ORIGINAL_SPRITE_PATH).convert("RGBA")
    converted, _, lock_box, automatic_points = (
        identity_locked_character_sprite(
            equipment,
            original,
            [ROM_INK],
            identity_points,
            preserve_generated_palette=True,
            restore_transparent_locked_points=False,
        )
    )
    apply_variant_details(CLASS_ID, COMMANDER_ID, converted)
    LOGICAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    converted.save(LOGICAL_PATH, optimize=True)
    converted.resize((512, 512), Image.NEAREST).save(
        ASSET_DIR / "source-cells/10-0B.png",
        optimize=True,
    )

    visible_identity = {
        point for point in identity_points
        if original.getpixel(point)[3]
    }
    final = translate_selected_pixels(
        converted,
        visible_identity,
        1,
        0,
    )
    visible_colors = {
        color for color in final.getdata() if color[3]
    }
    if len(visible_colors) > 15:
        raise ValueError(
            f"Jessica High Lord exceeds 15 colors: {len(visible_colors)}"
        )
    if final.getchannel("A").getbbox() != (0, 0, 16, 16):
        raise ValueError("Jessica High Lord must occupy the full canvas")
    final.save(ASSET_DIR / "10/0B.png", optimize=True)

    translated_identity = translate_points(identity_points, 1, 0)
    translated_eye = translate_points(
        protected_eye_points(original),
        1,
        0,
    )
    design_document = json.loads(
        DESIGN_PATH.read_text(encoding="utf-8")
    )
    stored_design = design_document.get("designs", {}).get(MASK_KEY)
    stored_revision = (
        int(stored_design.get("revision", 0))
        if stored_design is not None
        else 0
    )
    rom_path = ROOT / manifest["generated_from"]
    rom_source = rom_path.read_bytes()
    rom_face = render_sprite(
        rom_source,
        int(jessica_row["face_source_sprite_id"]),
        1,
    )
    changed_pixel_count = sum(
        final.getpixel((x, y)) != rom_face.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )
    jessica_row.update({
        "ai_source_kind": (
            "헤인 사용자 편집 하이로드 공통 16×16 클래스 템플릿"
        ),
        "ai_source_position": (
            "latest/shared-high-lord-hein-v1/logical16/10-0B.png"
        ),
        "source_palette": dominant_colors(converted),
        "pixel_palette": dominant_colors(final),
        "eye_lock_points": [
            list(point) for point in sorted(translated_eye)
        ],
        "eye_lock_pixel_count": len(translated_eye),
        "identity_lock_default_points": [
            list(point) for point in sorted(automatic_points)
        ],
        "identity_lock_points": [
            list(point) for point in sorted(translated_identity)
        ],
        "identity_lock_pixel_count": len(translated_identity),
        "identity_lock_mode": "custom",
        "identity_lock_transparency_mode": "equipment_priority",
        "identity_mask_pending_rebuild": False,
        "identity_translation": [1, 0],
        "identity_translation_applied_in_override": False,
        "identity_lock_box": list(lock_box),
        "design_override": False,
        "design_revision": 0,
        "design_override_superseded": stored_design is not None,
        "superseded_design_revision": stored_revision,
        "changed_pixel_count": changed_pixel_count,
        "feature": (
            "헤인의 사용자 승인 하이로드 장비·방패·검 실루엣을 "
            "제시카에게 다시 적용·파랑·금색 갑옷 유지·망토만 "
            "밝은 하늘색·파랑·진한 파랑 3단 명암으로 변경·"
            "제시카 원본 얼굴·머리·눈 73픽셀 유지·최종 합성에서 "
            "머리·얼굴 오른쪽 1칸 이동·메가드라이브 4bpp·"
            "기존 사용자 편집 이력 보존·실제 ROM 미적용"
        ),
    })
    manifest["asset_version"] = ASSET_VERSION
    write_json(MANIFEST_PATH, manifest)
    refresh_variant_report(CLASS_ID, {COMMANDER_ID})

    print(json.dumps({
        "asset_version": ASSET_VERSION,
        "visible_colors": len(visible_colors),
        "cape_colors": [
            "#6ddbff",
            "#4992ff",
            "#2449db",
        ],
        "cape_pixel_count": len(JESSICA_HIGH_LORD_CAPE_POINTS),
        "cape_light_pixel_count": len(
            JESSICA_HIGH_LORD_CAPE_LIGHT_POINTS
        ),
        "cape_dark_pixel_count": len(
            JESSICA_HIGH_LORD_CAPE_DARK_POINTS
        ),
        "identity_pixel_count": len(translated_identity),
        "head_translation": [1, 0],
        "palette": visible_palette(final),
    }, ensure_ascii=False))


if __name__ == "__main__":
    apply()
