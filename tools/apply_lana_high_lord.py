#!/usr/bin/env python3
"""Apply Lana's original cyan/blue palette to the Hein High Lord design.

This updates editor preview assets only and never writes or patches a ROM.
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
)
from tools.build_class_sprite_assets import render_sprite  # noqa: E402
from tools.build_shared_hein_martial_variants import (  # noqa: E402
    JESSICA_HIGH_LORD_CAPE_POINTS,
    LANA_HIGH_LORD_GRAY_FOOT_POINTS,
    apply_variant_details,
    refresh_variant_report,
    visible_palette,
)


COMMANDER_ID = 3
CLASS_ID = 0x0B
MASK_KEY = "3:0B"
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
    "shared-high-lord-hein-v1/logical16/03-0B.png"
)
ORIGINAL_SPRITE_PATH = (
    ROOT / "editor/static/class-sprites/commanders/3/0B-p1.png"
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
    identity_points = {
        tuple(point)
        for point in mask_document["masks"][MASK_KEY]
    }
    if not identity_points:
        raise ValueError("Lana High Lord identity mask is empty")

    rows = manifest["commanders"]
    hein_row = rows["5"]["classes"][str(CLASS_ID)]
    lana_row = rows[str(COMMANDER_ID)]["classes"][str(CLASS_ID)]
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

    # Apply the same mappings as the reproducible shared-template builder.
    for y in range(16):
        for x in range(16):
            point = (x, y)
            color = converted.getpixel(point)
            if point in identity_points:
                continue
            mapping = {
                (73, 73, 109, 255): (73, 109, 255, 255),
                (73, 109, 255, 255): (109, 219, 255, 255),
                (146, 36, 0, 255): (0, 73, 219, 255),
            }
            if color in mapping:
                converted.putpixel(point, mapping[color])
    apply_variant_details(CLASS_ID, COMMANDER_ID, converted)

    visible_colors = {
        color for color in converted.getdata() if color[3]
    }
    if len(visible_colors) > 15:
        raise ValueError(
            f"Lana High Lord exceeds 15 colors: {len(visible_colors)}"
        )
    if converted.getchannel("A").getbbox() != (0, 0, 16, 16):
        raise ValueError("Lana High Lord must occupy the full canvas")
    expected_foot = (146, 146, 146, 255)
    if any(
        converted.getpixel(point) != expected_foot
        for point in LANA_HIGH_LORD_GRAY_FOOT_POINTS
    ):
        raise ValueError("Lana High Lord gray feet were not preserved")

    LOGICAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    converted.save(LOGICAL_PATH, optimize=True)
    converted.resize((512, 512), Image.NEAREST).save(
        ASSET_DIR / "source-cells/3-0B.png",
        optimize=True,
    )
    converted.save(ASSET_DIR / "3/0B.png", optimize=True)

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
        int(lana_row["face_source_sprite_id"]),
        1,
    )
    changed_pixel_count = sum(
        converted.getpixel((x, y)) != rom_face.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )
    eye_points = protected_eye_points(original)
    lana_row.update({
        "ai_source_kind": (
            "헤인 사용자 편집 하이로드 공통 16×16 클래스 템플릿"
        ),
        "ai_source_position": (
            "latest/shared-high-lord-hein-v1/logical16/03-0B.png"
        ),
        "source_palette": dominant_colors(converted),
        "pixel_palette": dominant_colors(converted),
        "eye_lock_points": [
            list(point) for point in sorted(eye_points)
        ],
        "eye_lock_pixel_count": len(eye_points),
        "identity_lock_default_points": [
            list(point) for point in sorted(automatic_points)
        ],
        "identity_lock_points": [
            list(point) for point in sorted(identity_points)
        ],
        "identity_lock_pixel_count": len(identity_points),
        "identity_lock_mode": "custom",
        "identity_lock_transparency_mode": "equipment_priority",
        "identity_mask_pending_rebuild": False,
        "identity_translation": None,
        "identity_translation_applied_in_override": False,
        "identity_lock_box": list(lock_box),
        "design_override": False,
        "design_revision": 0,
        "design_override_superseded": stored_design is not None,
        "superseded_design_revision": stored_revision,
        "changed_pixel_count": changed_pixel_count,
        "feature": (
            "헤인의 사용자 승인 하이로드 장비·방패·검 실루엣을 "
            "라나에게 적용·라나 원본 하이로드 팔레트 기준·갑옷 "
            "넓은 면은 하늘색, 갑옷 음영은 중간 파랑·망토는 "
            "중간 파랑·진한 파랑 명암·양쪽 발·부츠 회색 7픽셀 "
            "유지·원본 얼굴·머리·눈 75픽셀 유지·메가드라이브 "
            "4bpp·기존 사용자 편집 이력 보존·실제 ROM 미적용"
        ),
    })
    manifest["asset_version"] = ASSET_VERSION
    write_json(MANIFEST_PATH, manifest)
    refresh_variant_report(CLASS_ID, {COMMANDER_ID})

    print(json.dumps({
        "asset_version": ASSET_VERSION,
        "visible_colors": len(visible_colors),
        "armor_colors": ["#6ddbff", "#496dff"],
        "cape_colors": ["#496dff", "#0049db", "#0000db"],
        "cape_pixel_count": len(JESSICA_HIGH_LORD_CAPE_POINTS),
        "gray_foot_pixel_count": len(
            LANA_HIGH_LORD_GRAY_FOOT_POINTS
        ),
        "identity_pixel_count": len(identity_points),
        "palette": visible_palette(converted),
    }, ensure_ascii=False))


if __name__ == "__main__":
    apply()
