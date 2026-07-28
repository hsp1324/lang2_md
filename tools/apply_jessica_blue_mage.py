#!/usr/bin/env python3
"""Apply Jessica's blue/cyan Mage palette with original red shoulders.

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
from tools.build_shared_hein_class_variants import (  # noqa: E402
    JESSICA_MAGE_RED_SHOULDER_DARK_POINTS,
    JESSICA_MAGE_RED_SHOULDER_MAIN_POINTS,
    apply_variant_details,
    refresh_variant_report,
    role_mapping,
    visible_palette,
)


COMMANDER_ID = 10
CLASS_ID = 0x13
MASK_KEY = "10:13"
ASSET_DIR = ROOT / "editor/static/ai-class-sprites"
MANIFEST_PATH = ASSET_DIR / "manifest.json"
MASK_PATH = ROOT / "editor/ai_identity_masks.json"
DESIGN_PATH = ROOT / "editor/ai_class_design_overrides.json"
MASTER_PATH = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "shared-hein-classes-v1/master/"
    "hein-13-mage-user-approved.png"
)
LOGICAL_PATH = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "shared-hein-classes-v1/logical16/10-13.png"
)
ORIGINAL_SPRITE_PATH = (
    ROOT / "editor/static/class-sprites/commanders/10/13-p1.png"
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
        raise ValueError("Jessica Mage identity mask is empty")

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

    mapping = role_mapping(CLASS_ID, COMMANDER_ID)
    for y in range(16):
        for x in range(16):
            point = (x, y)
            color = equipment.getpixel(point)
            if color in mapping:
                equipment.putpixel(point, mapping[color])

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

    visible_colors = {
        color for color in converted.getdata() if color[3]
    }
    if len(visible_colors) > 15:
        raise ValueError(
            f"Jessica Mage exceeds 15 colors: {len(visible_colors)}"
        )
    if converted.getchannel("A").getbbox() != (0, 0, 16, 16):
        raise ValueError("Jessica Mage must occupy the full canvas")
    if any(
        converted.getpixel(point) != (219, 0, 0, 255)
        for point in JESSICA_MAGE_RED_SHOULDER_MAIN_POINTS
    ):
        raise ValueError("Jessica Mage red shoulder highlights were lost")
    if any(
        converted.getpixel(point) != (109, 0, 0, 255)
        for point in JESSICA_MAGE_RED_SHOULDER_DARK_POINTS
    ):
        raise ValueError("Jessica Mage red shoulder shadows were lost")

    LOGICAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    converted.save(LOGICAL_PATH, optimize=True)
    converted.resize((512, 512), Image.NEAREST).save(
        ASSET_DIR / "source-cells/10-13.png",
        optimize=True,
    )
    converted.save(ASSET_DIR / "10/13.png", optimize=True)

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
        converted.getpixel((x, y)) != rom_face.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )
    eye_points = protected_eye_points(original)
    jessica_row.update({
        "ai_source_kind": (
            "헤인 사용자 편집 메이지 공통 16×16 클래스 템플릿"
        ),
        "ai_source_position": (
            "latest/shared-hein-classes-v1/logical16/10-13.png"
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
            "헤인의 사용자 승인 메이지 로브·망토·지팡이 실루엣을 "
            "제시카에게 다시 적용·로브와 망토는 진한 파랑·중간 "
            "파랑·밝은 하늘색 3단 명암·양쪽 어깨 장식 11픽셀은 "
            "제시카 원본의 빨강·진홍 유지·청색 머리·얼굴·눈 "
            "73픽셀과 목제 지팡이·녹색 보석 유지·메가드라이브 "
            "4bpp·기존 사용자 편집 이력 보존·실제 ROM 미적용"
        ),
    })
    manifest["asset_version"] = ASSET_VERSION
    write_json(MANIFEST_PATH, manifest)
    refresh_variant_report(CLASS_ID, {COMMANDER_ID})

    print(json.dumps({
        "asset_version": ASSET_VERSION,
        "visible_colors": len(visible_colors),
        "robe_colors": ["#2449db", "#4992ff", "#6ddbff"],
        "red_shoulder_pixel_count": (
            len(JESSICA_MAGE_RED_SHOULDER_MAIN_POINTS)
            + len(JESSICA_MAGE_RED_SHOULDER_DARK_POINTS)
        ),
        "identity_pixel_count": len(identity_points),
        "palette": visible_palette(converted),
    }, ensure_ascii=False))


if __name__ == "__main__":
    apply()
