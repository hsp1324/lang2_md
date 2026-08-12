#!/usr/bin/env python3
"""Merge Jessica Wizard's one-pixel near-duplicate purple palette entry."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_refined_recent_class_variants import (  # noqa: E402
    OUTPUT,
    merge_jessica_wizard_near_duplicate,
    merge_jessica_wizard_rare_equipment_blue,
    write_contact,
)
from tools.build_ai_class_sprite_assets import (  # noqa: E402
    load_identity_mask_overrides,
    protected_eye_points,
)
from tools.build_shared_new_class_variants import validate  # noqa: E402
from tools.pillow_compat import flattened_image_data  # noqa: E402


SOURCE = OUTPUT / "logical16/10-15.png"
PREVIEW = OUTPUT / "previews/10-15.png"
REPORT = OUTPUT / "validation-report.json"
MASKS = OUTPUT / "identity-masks.json"
ORIGINAL = ROOT / "editor/static/class-sprites/commanders/10/15-p1.png"
LIVE = ROOT / "editor/static/ai-class-sprites/10/15.png"
SOURCE_CELL = ROOT / "editor/static/ai-class-sprites/source-cells/10-15.png"
MANIFEST = ROOT / "editor/static/ai-class-sprites/manifest.json"
ASSET_VERSION = "liana-lana-healer-shared-v106"


def dominant_colors(image: Image.Image, limit: int = 6) -> list[str]:
    counts: dict[tuple[int, int, int, int], int] = {}
    for color in flattened_image_data(image):
        if color[3]:
            counts[color] = counts.get(color, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: -item[1])[:limit]
    return ["#{:02x}{:02x}{:02x}".format(*color[:3]) for color, _ in ranked]


def main() -> int:
    image = Image.open(SOURCE).convert("RGBA")
    original = Image.open(ORIGINAL).convert("RGBA")
    identity = {
        tuple(point)
        for point in json.loads(MASKS.read_text(encoding="utf-8"))["masks"][
            "10:15"
        ]
    }
    result, changed = merge_jessica_wizard_near_duplicate(image, identity)
    if changed not in {0, 1}:
        raise ValueError(f"expected at most one near-purple pixel, got {changed}")
    result, changed_blue = merge_jessica_wizard_rare_equipment_blue(
        result, identity
    )
    if changed_blue not in {0, 1}:
        raise ValueError(
            f"expected at most one rare-blue pixel, got {changed_blue}"
        )
    result.save(SOURCE, optimize=True)
    result.resize((512, 512), Image.Resampling.NEAREST).save(
        PREVIEW, optimize=True
    )

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    row = next(
        item
        for item in report["classes"]
        if item["commander_id"] == 10 and item["class_id"] == "15"
    )
    row.update(validate(result, original, identity))
    row["palette_remapped_pixels"] = int(
        row.get("palette_remapped_pixels", 0)
    ) + changed + changed_blue
    row["near_duplicate_palette_merge"] = (
        "#9224B6 -> #9249B6; #2449FF -> #496DFF"
    )
    report["all_accepted"] = all(
        bool(item["accepted"]) for item in report["classes"]
    )
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_contact(report["classes"])

    # Apply the exact aggregate-build composition only to Jessica Wizard.  A
    # complete rebuild is verified separately, but copying all 180 sprites
    # here would overwrite unrelated live editor work.
    global_identity = load_identity_mask_overrides()[(10, 0x15)]
    global_identity |= protected_eye_points(original)
    composed = result.copy()
    for point in global_identity:
        if original.getpixel(point)[3]:
            composed.putpixel(point, original.getpixel(point))
    final_colors = {
        color for color in flattened_image_data(composed) if color[3]
    }
    if len(final_colors) > 15:
        raise ValueError(
            f"Jessica Wizard final composition still has {len(final_colors)} colors"
        )
    composed.save(LIVE, optimize=True)
    result.resize((512, 512), Image.Resampling.NEAREST).save(
        SOURCE_CELL, optimize=True
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["asset_version"] = ASSET_VERSION
    live_row = manifest["commanders"]["10"]["classes"][str(0x15)]
    live_row["source_palette"] = dominant_colors(result)
    live_row["pixel_palette"] = dominant_colors(composed)
    live_row["changed_pixel_count"] = sum(
        composed.getpixel((x, y)) != original.getpixel((x, y))
        for y in range(16)
        for x in range(16)
    )
    live_row["feature"] = (
        "캐릭터별 승인 기준형 위저드의 장비·무기·실루엣 유지·"
        "제시카 얼굴·눈·머리 마스크 복원·장비의 1픽셀 근접 자주색 "
        "#9224B6을 #9249B6으로 병합·최신 회색 얼굴 경계 슬롯을 위해 "
        "장비 1픽셀 #2449FF를 #496DFF로 병합·메가드라이브 최종 15색 유지"
    )
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "target": "10:15",
                "merged_pixels": changed + changed_blue,
                "source_visible_colors": row["visible_color_count"],
                "final_visible_colors": len(final_colors),
                "accepted": row["accepted"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if row["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
