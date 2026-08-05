#!/usr/bin/env python3
"""Apply the approved purple Elwin Hero sample to the live editor asset."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import ASSET_VERSION
from tools.rework_king_hero_and_archmage_magic_samples import (
    HERO_HEAD_ORNAMENT_POINTS,
)


SAMPLE_ROOT = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "sample-class-variants-v4-free-five/01-elwin-22-hero"
)
SOURCE = SAMPLE_ROOT / "logical16/04.png"
AI_SOURCE = SAMPLE_ROOT / "ai/04.png"
LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"
LIVE = LIVE_ROOT / "1/22.png"
MANIFEST = LIVE_ROOT / "manifest.json"
OVERRIDES = ROOT / "editor/ai_class_design_overrides.json"
MASKS = ROOT / "editor/ai_identity_masks.json"
ARCHIVE = SAMPLE_ROOT / "archive/01-22-before-purple-sample-04.png"


def flat_pixels(image: Image.Image) -> list[list[int]]:
    return [list(color) for color in image.get_flattened_data()]


def palette(image: Image.Image, limit: int | None = None) -> list[str]:
    counts = Counter(color for color in image.get_flattened_data() if color[3])
    return [
        "#%02x%02x%02x" % color[:3]
        for color, _ in counts.most_common(limit)
    ]


def main() -> int:
    source = Image.open(SOURCE).convert("RGBA")
    before = Image.open(LIVE).convert("RGBA")
    if source.size != (16, 16):
        raise ValueError("Elwin Hero sample must be native 16x16")
    colors = {color for color in source.get_flattened_data() if color[3]}
    if len(colors) > 15:
        raise ValueError("Elwin Hero sample exceeds the 15-color limit")
    if (0, 0, 0, 255) in colors or (255, 0, 255, 255) in colors:
        raise ValueError("Elwin Hero sample contains a forbidden background color")

    mask_document = json.loads(MASKS.read_text(encoding="utf-8"))
    identity_points = {
        tuple(point) for point in mask_document["masks"]["1:22"]
    }
    locked_points = identity_points - HERO_HEAD_ORNAMENT_POINTS
    mismatches = {
        point
        for point in locked_points
        if source.getpixel(point) != before.getpixel(point)
    }
    if mismatches:
        raise ValueError(
            f"purple Hero sample changes {len(mismatches)} locked face/hair pixels"
        )

    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE.is_file():
        shutil.copy2(LIVE, ARCHIVE)

    source.save(LIVE, optimize=True)
    source.resize((512, 512), Image.Resampling.NEAREST).save(
        LIVE_ROOT / "source-cells/1-22.png",
        optimize=True,
    )
    Image.open(AI_SOURCE).convert("RGBA").save(
        LIVE_ROOT / "source-originals/1-22.png",
        optimize=True,
    )

    revision = time.time_ns()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    overrides["designs"]["1:22"] = {
        "revision": revision,
        "pixels": flat_pixels(source),
        "base_pixels": flat_pixels(before),
    }
    row = manifest["commanders"]["1"]["classes"][str(0x22)]
    row["design_override"] = True
    row["design_revision"] = revision
    row["design_override_superseded"] = False
    row["superseded_design_revision"] = 0
    row["ai_source_kind"] = (
        "샘플 클래스 선정 엘윈 킹 기반 보라색 히어로"
    )
    row["ai_source_position"] = (
        "latest/sample-class-variants-v4-free-five/"
        "01-elwin-22-hero/logical16/04.png"
    )
    row["source_palette"] = palette(source, 6)
    row["pixel_palette"] = palette(source, 6)
    row["feature"] = (
        "샘플 클래스 4번 전체 적용·킹 기반 히어로 형태·보라·연보라 "
        "장비색·붉은 머리와 얼굴 유지·흰·회색 머리 장식 6픽셀만 "
        "보라 명암 적용·16×16·15색 이하"
    )
    manifest["asset_version"] = ASSET_VERSION
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OVERRIDES.write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "applied": "1:22",
                "sample": "01-elwin-22-hero/04",
                "visible_color_count": len(colors),
                "identity_pixels_preserved": len(locked_points),
                "ornament_pixels_recolored": len(HERO_HEAD_ORNAMENT_POINTS),
                "asset_version": ASSET_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
