#!/usr/bin/env python3
"""Add every stock fifth-tier class to the current editor AI asset set.

The complete AI builder needs its archived large source boards. This focused
sync keeps an already-built editor asset set usable when only the read-only
supplemental hidden-class metadata changed. It never writes a ROM.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    DEFAULT_OUTPUT,
    RESAMPLING,
    box_points,
    dominant_colors,
    head_lock_box,
    load_ai_design_overrides,
    load_identity_mask_overrides,
    protected_eye_points,
)
from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.build_test_class_sprite_assets import class_tiers
from tools.class_change_data import COMMANDER_COUNT, hidden_class_routes
from tools.scenario_data import class_names


def sync_hidden_assets(
    rom_path: Path = DEFAULT_ROM,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, object]:
    source = rom_path.read_bytes()
    classes = class_names(source)
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    identity_masks = load_identity_mask_overrides()
    design_overrides = load_ai_design_overrides()
    added_count = 0

    for commander_id in range(1, COMMANDER_COUNT + 1):
        sprite_map = commander_sprite_map(source, commander_id)
        tiers = class_tiers(source, commander_id)
        by_sprite: dict[int, list[int]] = defaultdict(list)
        for class_id in tiers:
            by_sprite[sprite_map[class_id]].append(class_id)
        for group in by_sprite.values():
            group.sort(key=lambda value: (tiers[value], value))

        rows = manifest["commanders"][str(commander_id)]["classes"]
        for route in hidden_class_routes(commander_id):
            class_id = route.candidates[0]
            key = (commander_id, class_id)
            existing = rows.get(str(class_id))
            if existing is not None:
                existing["hidden_class"] = True
                existing["hidden_source_class"] = route.current_class
                existing.setdefault("supplemental_hidden_baseline", False)
                continue

            original = render_sprite(source, sprite_map[class_id], 1)
            eye_points = protected_eye_points(original)
            detected_box = head_lock_box(original)
            lock_box = (
                detected_box[0],
                detected_box[1],
                detected_box[2],
                max(9, detected_box[3]),
            )
            automatic_points = box_points(lock_box) | eye_points
            identity_points = (
                set(identity_masks[key]) | eye_points
                if key in identity_masks
                else automatic_points
            )
            image = original.copy()
            design = design_overrides.get(key)
            if design is not None:
                image.putdata(
                    [tuple(pixel) for pixel in design["pixels"]]
                )
                for point in identity_points:
                    image.putpixel(point, original.getpixel(point))

            commander_dir = output_dir / str(commander_id)
            commander_dir.mkdir(parents=True, exist_ok=True)
            target = commander_dir / f"{class_id:02X}.png"
            image.save(target, optimize=True)

            source_cell_dir = output_dir / "source-cells"
            source_cell_dir.mkdir(parents=True, exist_ok=True)
            source_cell = source_cell_dir / (
                f"{commander_id}-{class_id:02X}.png"
            )
            original.resize(
                (512, 512),
                RESAMPLING.NEAREST,
            ).save(source_cell, optimize=True)

            group = by_sprite[sprite_map[class_id]]
            rows[str(class_id)] = {
                "class_id": class_id,
                "class_name": classes[class_id]["ko"],
                "tier": 5,
                "ai_sheet_row": commander_id,
                "ai_sheet_stage": 5,
                "ai_source_cell_file": str(
                    source_cell.relative_to(output_dir)
                ),
                "ai_source_kind": (
                    "원작 캐릭터 전용 히든 클래스 네이티브 "
                    "16×16 편집 기준"
                ),
                "ai_source_position": (
                    f"{commander_id}번 지휘관 "
                    f"{classes[class_id]['ko']} 원작 전용 스프라이트"
                ),
                "source_palette": dominant_colors(original),
                "pixel_palette": dominant_colors(image),
                "face_source_sprite_id": sprite_map[class_id],
                "face_pixel_count": 0,
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
                "identity_lock_mode": (
                    "custom" if key in identity_masks else "automatic"
                ),
                "identity_lock_transparency_mode": "exact",
                "identity_mask_pending_rebuild": False,
                "identity_translation": None,
                "mount_lock_points": [],
                "mount_lock_pixel_count": 0,
                "mount_lock_mode": "none",
                "mount_mask_pending_rebuild": False,
                "design_override": design is not None,
                "design_revision": (
                    int(design["revision"]) if design is not None else 0
                ),
                "design_override_superseded": False,
                "superseded_design_revision": 0,
                "duplicate_group": group,
                "group_rank": group.index(class_id),
                "redesigned": True,
                "pending_redesign": False,
                "hidden_class": True,
                "hidden_source_class": route.current_class,
                "supplemental_hidden_baseline": True,
                "identity_lock_box": list(lock_box),
                "changed_pixel_count": sum(
                    image.getpixel((x, y))
                    != original.getpixel((x, y))
                    for y in range(16)
                    for x in range(16)
                ),
                "feature": (
                    "ROM 전직 레코드의 대표 히든 경로 밖에 있던 원작 "
                    "복수 히든 클래스를 에디터에 복원·캐릭터 전용 "
                    "원작 16×16 스프라이트를 초기 디자인으로 사용·"
                    "원본 머리·얼굴·눈 잠금·사용자 디자인 편집 가능·"
                    "실제 ROM 미적용"
                ),
                "file": str(target.relative_to(output_dir)),
            }
            added_count += 1

    manifest["asset_version"] = ASSET_VERSION
    manifest["asset_count"] = sum(
        len(commander["classes"])
        for commander in manifest["commanders"].values()
    )
    manifest["redesigned_count"] = sum(
        bool(row["redesigned"])
        for commander in manifest["commanders"].values()
        for row in commander["classes"].values()
    )
    manifest["pending_redesign_count"] = sum(
        bool(row["pending_redesign"])
        for commander in manifest["commanders"].values()
        for row in commander["classes"].values()
    )
    hidden_note = (
        " Every stock fifth-tier route is present, including supplemental "
        "multi-hidden routes stored outside the ten writable chain records; "
        "supplemental entries start from editable character-specific native "
        "16x16 ROM art."
    )
    pipeline = str(manifest.get("pipeline", ""))
    if hidden_note.strip() not in pipeline:
        manifest["pipeline"] = pipeline + hidden_note

    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest_path)
    manifest["supplemental_hidden_added_count"] = added_count
    return manifest


def main() -> None:
    manifest = sync_hidden_assets()
    print(
        "synced "
        f"{manifest['supplemental_hidden_added_count']} supplemental hidden "
        f"classes; {manifest['asset_count']} editor AI assets total"
    )


if __name__ == "__main__":
    main()
