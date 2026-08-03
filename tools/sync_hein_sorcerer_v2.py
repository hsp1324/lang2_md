#!/usr/bin/env python3
"""Install Hein's AI Sorcerer and explicit editor source originals.

This is intentionally an editor-preview-only sync. It never writes a ROM.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (  # noqa: E402
    ASSET_VERSION,
    HEIN_SORCERER_V2_CLEAN_SOURCE,
    HEIN_SORCERER_V2_LOGICAL_SOURCE,
    IDENTITY_MASK_OVERRIDES,
    RESAMPLING,
    SHARED_HEIN_CLASS_SOURCE_DIR,
    dominant_colors,
    identity_locked_character_sprite,
    load_pixel_mask_overrides,
    protected_eye_points,
)
from tools.build_class_sprite_assets import render_sprite  # noqa: E402


ASSET_DIR = ROOT / "editor/static/ai-class-sprites"
MANIFEST_PATH = ASSET_DIR / "manifest.json"
PRIEST_MASTER = (
    SHARED_HEIN_CLASS_SOURCE_DIR.parent
    / "master/hein-11-priest-user-approved.png"
)
HIGH_PRIEST_MASTER = (
    SHARED_HEIN_CLASS_SOURCE_DIR.parent
    / "master/hein-16-high-priest-user-approved.png"
)


def save_source_cell(source: Image.Image, target: Path) -> None:
    isolated = source.convert("RGBA")
    bbox = isolated.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("Hein Sorcerer AI source is empty")
    preview = isolated.crop(bbox)
    preview.thumbnail((512, 512), RESAMPLING.NEAREST)
    preview.save(target, optimize=True)


def source_paths() -> dict[int, Path]:
    return {
        0x09: HEIN_SORCERER_V2_CLEAN_SOURCE,
        0x11: PRIEST_MASTER,
        0x16: HIGH_PRIEST_MASTER,
    }


def sync() -> None:
    for source in (
        HEIN_SORCERER_V2_CLEAN_SOURCE,
        HEIN_SORCERER_V2_LOGICAL_SOURCE,
        PRIEST_MASTER,
        HIGH_PRIEST_MASTER,
        MANIFEST_PATH,
    ):
        if not source.is_file():
            raise FileNotFoundError(source)

    generated = Image.open(
        HEIN_SORCERER_V2_LOGICAL_SOURCE
    ).convert("RGBA")
    if generated.size != (16, 16):
        raise ValueError("Hein Sorcerer logical source must be 16x16")
    bbox = generated.getchannel("A").getbbox()
    if bbox is None or bbox[1] != 0 or bbox[3] != 16:
        raise ValueError("Hein Sorcerer must occupy all 16 logical rows")
    visible_colors = {
        color for color in generated.getdata() if color[3]
    }
    if len(visible_colors) > 15:
        raise ValueError("Hein Sorcerer exceeds 15 visible colors")

    source_original_dir = ASSET_DIR / "source-originals"
    source_original_dir.mkdir(parents=True, exist_ok=True)
    for class_id, source in source_paths().items():
        shutil.copyfile(
            source,
            source_original_dir / f"5-{class_id:02X}.png",
        )

    sorcerer_source = Image.open(
        HEIN_SORCERER_V2_CLEAN_SOURCE
    ).convert("RGBA")
    save_source_cell(
        sorcerer_source,
        ASSET_DIR / "source-cells/5-09.png",
    )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["asset_version"] = ASSET_VERSION
    rows = manifest["commanders"]["5"]["classes"]
    row = rows[str(0x09)]
    rom_path = ROOT / manifest["generated_from"]
    rom_source = rom_path.read_bytes()
    rom_face = render_sprite(
        rom_source,
        int(row["face_source_sprite_id"]),
        1,
    )
    identity_masks = load_pixel_mask_overrides(
        IDENTITY_MASK_OVERRIDES,
        label="identity",
    )
    identity_points = (
        set(identity_masks[(5, 0x09)])
        | protected_eye_points(rom_face)
    )
    logical, _, _, _ = identity_locked_character_sprite(
        generated,
        rom_face,
        [],
        identity_masks[(5, 0x09)],
        preserve_generated_palette=True,
    )
    logical.save(ASSET_DIR / "5/09.png", optimize=True)
    changed_pixel_count = sum(
        logical.getpixel((x, y)) != rom_face.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )
    row.update({
        "ai_source_cell_file": "source-cells/5-09.png",
        "ai_source_original_file": "source-originals/5-09.png",
        "ai_source_kind": (
            "OpenAI 신규 헤인 소서러 전용 네이티브 논리16 원화"
        ),
        "ai_source_position": (
            "latest/hein-sorcerer-v2/clean/"
            "hein-09-sorcerer-ai.png + logical16/"
            "hein-09-sorcerer-ai.png"
        ),
        "source_palette": dominant_colors(sorcerer_source),
        "pixel_palette": dominant_colors(logical),
        "eye_lock_points": [
            list(point)
            for point in sorted(protected_eye_points(rom_face))
        ],
        "eye_lock_pixel_count": len(protected_eye_points(rom_face)),
        "identity_lock_default_points": [],
        "identity_lock_points": [
            list(point) for point in sorted(identity_points)
        ],
        "identity_lock_pixel_count": len(identity_points),
        "identity_lock_mode": "custom",
        "identity_lock_transparency_mode": "exact",
        "identity_mask_pending_rebuild": False,
        "identity_mask_superseded": False,
        "identity_lock_box": None,
        "changed_pixel_count": changed_pixel_count,
        "feature": (
            "현재 헤인의 얼굴·눈·청색 머리 확대 원본과 승인된 "
            "헤인 메이지 장비 문법을 레퍼런스로 신규 AI 생성·"
            "생성 단계에서 헤인 얼굴·머리 형태 유지·남청색 "
            "소서러 로브·목제 지팡이·정확한 16×16 논리 격자·"
            f"메가드라이브 15색·사용자 얼굴 마스크 "
            f"{len(identity_points)}픽셀과 원본 눈 완전 복원·"
            "실제 ROM 미적용"
        ),
        "design_override": False,
        "design_revision": 0,
    })
    rows[str(0x11)]["ai_source_original_file"] = (
        "source-originals/5-11.png"
    )
    rows[str(0x16)]["ai_source_original_file"] = (
        "source-originals/5-16.png"
    )

    extra_sources = [
        str(HEIN_SORCERER_V2_CLEAN_SOURCE.relative_to(ROOT)),
        str(HEIN_SORCERER_V2_LOGICAL_SOURCE.relative_to(ROOT)),
        str(PRIEST_MASTER.relative_to(ROOT)),
        str(HIGH_PRIEST_MASTER.relative_to(ROOT)),
    ]
    source_images = manifest.setdefault("ai_source_images", [])
    source_images[:] = [
        source
        for source in source_images
        if source
        != (
            "docs/assets/ai-class-source/latest/hein/raw/"
            "09-sorcerer.png"
        )
    ]
    for source in extra_sources:
        if source not in source_images:
            source_images.append(source)

    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(MANIFEST_PATH)


if __name__ == "__main__":
    sync()
