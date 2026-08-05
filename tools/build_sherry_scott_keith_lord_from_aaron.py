#!/usr/bin/env python3
"""Share the latest user-edited Aaron Lord design with three Lords."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
ROM_ROOT = ROOT / "editor/static/class-sprites/commanders"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"
MANIFEST_FILE = AI_ROOT / "manifest.json"
SOURCE_ROOT = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "shared-sherry-scott-keith-lord-aaron-lord-v1"
)
MASTER_PATH = SOURCE_ROOT / "master/08-04-current-user-edited.png"
MASTER_ROM_PATH = SOURCE_ROOT / "references/08-04-rom.png"
ARCHIVE_ROOT = SOURCE_ROOT / "archive/before-aaron-lord"
LOGICAL_ROOT = SOURCE_ROOT / "logical16"
PREVIEW_ROOT = SOURCE_ROOT / "previews"
TARGETS = (4, 6, 7)
TRANSPARENT = (0, 0, 0, 0)
ASSET_VERSION = "liana-lana-healer-shared-v106"

# Aaron's blue/cyan/gold equipment roles become a distinct Lord palette for
# each commander. Neutral outline, skin, white blade and silver armor remain
# unchanged so the equipment materials read consistently at native 16x16.
SCHEMES = {
    4: {
        (73, 109, 255, 255): (0, 109, 146, 255),
        (109, 219, 255, 255): (109, 219, 255, 255),
        (219, 146, 36, 255): (255, 182, 0, 255),
        (109, 109, 109, 255): (36, 109, 146, 255),
    },
    6: {
        (73, 109, 255, 255): (36, 182, 36, 255),
        (109, 219, 255, 255): (36, 219, 36, 255),
        (219, 146, 36, 255): (255, 182, 0, 255),
        (109, 109, 109, 255): (36, 109, 0, 255),
    },
    7: {
        (73, 109, 255, 255): (36, 73, 219, 255),
        (109, 219, 255, 255): (109, 219, 255, 255),
        (219, 146, 36, 255): (146, 182, 255, 255),
        (109, 109, 109, 255): (73, 109, 255, 255),
    },
}
PALETTE_NAMES = {
    4: "navy/teal/cyan/gold",
    6: "forest-green/lime/gold",
    7: "navy/blue/cyan",
}


def palette(image: Image.Image, limit: int | None = None) -> list[str]:
    counts = Counter(color for color in image.get_flattened_data() if color[3])
    rows = counts.most_common(limit)
    return ["#{:02x}{:02x}{:02x}".format(*color[:3]) for color, _ in rows]


def ensure_snapshots() -> None:
    for directory in (
        MASTER_PATH.parent,
        MASTER_ROM_PATH.parent,
        ARCHIVE_ROOT,
        LOGICAL_ROOT,
        PREVIEW_ROOT,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    # Capture only once. A future aggregate rebuild must not silently replace
    # the user-approved Aaron master with a derived output.
    if not MASTER_PATH.is_file():
        shutil.copy2(AI_ROOT / "8/04.png", MASTER_PATH)
    if not MASTER_ROM_PATH.is_file():
        shutil.copy2(ROM_ROOT / "8/04-p1.png", MASTER_ROM_PATH)
    for commander_id in TARGETS:
        archive = ARCHIVE_ROOT / f"{commander_id:02d}-04.png"
        if not archive.is_file():
            shutil.copy2(AI_ROOT / f"{commander_id}/04.png", archive)


def build_variant(
    master: Image.Image,
    master_rom: Image.Image,
    master_identity: set[tuple[int, int]],
    before: Image.Image,
    target_original: Image.Image,
    target_identity: set[tuple[int, int]],
    commander_id: int,
) -> tuple[Image.Image, set[tuple[int, int]]]:
    result = master.copy()
    # A changed pixel inside Aaron's mask is deliberate equipment drawn over
    # the old head boundary (the two white sword pixels at x=2). Keep it when
    # the target's own identity mask does not claim that coordinate.
    master_equipment_overrides = {
        point
        for point in master_identity
        if master.getpixel(point) != master_rom.getpixel(point)
    }
    replaceable_master_identity = master_identity - master_equipment_overrides

    mapping = SCHEMES[commander_id]
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if point not in target_identity:
                color = result.getpixel(point)
                result.putpixel(point, mapping.get(color, color))

    # Replace Aaron-only head/hair coordinates with the target's current local
    # pixels, preventing either Aaron hair remnants or transparent neck holes.
    for point in replaceable_master_identity:
        result.putpixel(point, before.getpixel(point))

    # The target's saved identity is authoritative wherever masks overlap the
    # donor sword, shield, armor, or hair.
    for point in target_identity:
        result.putpixel(point, target_original.getpixel(point))
    return result, master_equipment_overrides


def build() -> dict[str, object]:
    ensure_snapshots()
    masks = json.loads(MASK_FILE.read_text(encoding="utf-8"))["masks"]
    master = Image.open(MASTER_PATH).convert("RGBA")
    master_rom = Image.open(MASTER_ROM_PATH).convert("RGBA")
    master_identity = {tuple(point) for point in masks["8:04"]}
    reports = []

    for commander_id in TARGETS:
        before = Image.open(
            ARCHIVE_ROOT / f"{commander_id:02d}-04.png"
        ).convert("RGBA")
        original = Image.open(
            ROM_ROOT / str(commander_id) / "04-p1.png"
        ).convert("RGBA")
        identity = {tuple(point) for point in masks[f"{commander_id}:04"]}
        result, master_overrides = build_variant(
            master,
            master_rom,
            master_identity,
            before,
            original,
            identity,
            commander_id,
        )

        visible_identity = {
            point for point in identity if original.getpixel(point)[3]
        }
        identity_match = sum(
            result.getpixel(point) == original.getpixel(point)
            for point in visible_identity
        )
        equipment_points = {
            (x, y)
            for y in range(16)
            for x in range(16)
            if (x, y) not in identity
            and (x, y) not in (master_identity - master_overrides)
        }
        mapping = SCHEMES[commander_id]
        equipment_role_match = sum(
            result.getpixel(point)
            == mapping.get(master.getpixel(point), master.getpixel(point))
            for point in equipment_points
        )
        colors = palette(result)
        empty_rows = [
            y for y in range(16)
            if not any(result.getpixel((x, y))[3] for x in range(16))
        ]
        empty_columns = [
            x for x in range(16)
            if not any(result.getpixel((x, y))[3] for y in range(16))
        ]
        pure_black = sum(
            result.getpixel((x, y)) == (0, 0, 0, 255)
            for y in range(16)
            for x in range(16)
        )
        accepted = (
            identity_match == len(visible_identity)
            and equipment_role_match == len(equipment_points)
            and len(colors) <= 15
            and not empty_rows
            and not empty_columns
            and pure_black == 0
        )
        result.save(LOGICAL_ROOT / f"{commander_id:02d}-04.png", optimize=True)
        result.resize((512, 512), Image.Resampling.NEAREST).save(
            PREVIEW_ROOT / f"{commander_id:02d}-04.png", optimize=True
        )
        reports.append(
            {
                "commander_id": commander_id,
                "class_id": "04",
                "identity_match": identity_match,
                "identity_pixel_count": len(visible_identity),
                "equipment_role_match": equipment_role_match,
                "equipment_pixel_count": len(equipment_points),
                "master_equipment_override_points": [
                    list(point) for point in sorted(master_overrides)
                ],
                "palette_family": PALETTE_NAMES[commander_id],
                "visible_color_count": len(colors),
                "palette": colors,
                "empty_rows": empty_rows,
                "empty_columns": empty_columns,
                "pure_black_pixels": pure_black,
                "accepted": accepted,
            }
        )

    board = Image.new("RGBA", (2048, 560), (22, 25, 23, 255))
    draw = ImageDraw.Draw(board)
    entries = [
        ("Aaron Lord master", MASTER_PATH),
        ("Sherry Lord", LOGICAL_ROOT / "04-04.png"),
        ("Scott Lord", LOGICAL_ROOT / "06-04.png"),
        ("Keith Lord", LOGICAL_ROOT / "07-04.png"),
    ]
    for index, (label, path) in enumerate(entries):
        draw.text((index * 512 + 12, 12), label, fill=(235, 240, 236, 255))
        image = Image.open(path).convert("RGBA").resize(
            (512, 512), Image.Resampling.NEAREST
        )
        board.alpha_composite(image, (index * 512, 48))
    board.convert("RGB").save(SOURCE_ROOT / "all-lord-variants.png", optimize=True)

    report = {
        "version": 1,
        "master": str(MASTER_PATH.relative_to(ROOT)),
        "rule": (
            "copy the latest user-edited Aaron Lord equipment coordinates; "
            "restore each target identity; recolor only equipment roles"
        ),
        "all_accepted": all(row["accepted"] for row in reports),
        "classes": reports,
    }
    (SOURCE_ROOT / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def apply_live(report: dict[str, object]) -> None:
    if not report["all_accepted"]:
        raise ValueError("refusing to apply rejected Aaron Lord variants")
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    for commander_id in TARGETS:
        source = Image.open(
            LOGICAL_ROOT / f"{commander_id:02d}-04.png"
        ).convert("RGBA")
        source.save(AI_ROOT / f"{commander_id}/04.png", optimize=True)
        source.resize((512, 512), Image.Resampling.NEAREST).save(
            AI_ROOT / f"source-cells/{commander_id}-04.png", optimize=True
        )
        original = Image.open(
            ROM_ROOT / str(commander_id) / "04-p1.png"
        ).convert("RGBA")
        changed = sum(
            source.getpixel((x, y)) != original.getpixel((x, y))
            for y in range(16)
            for x in range(16)
        )
        row = manifest["commanders"][str(commander_id)]["classes"][str(0x04)]
        row["ai_source_kind"] = (
            "최신 아론 사용자 편집 로드 기반 쉐리·스코트·키스 로드 "
            "공통 16×16 클래스 템플릿"
        )
        row["ai_source_position"] = (
            "latest/shared-sherry-scott-keith-lord-aaron-lord-v1/logical16/"
            f"{commander_id:02d}-04.png"
        )
        row["source_palette"] = palette(source, 6)
        row["pixel_palette"] = palette(source, 6)
        row["changed_pixel_count"] = changed
        row["feature"] = (
            "방금 저장된 아론 로드의 방패·갑옷·검·외곽선 좌표 적용·"
            "각 캐릭터 원작 얼굴·머리·눈 마스크 복원·"
            + (
                "쉐리 남청·청록·하늘색·금색 장비색·"
                if commander_id == 4
                else "스코트 숲초록·연두·금색 장비색·"
                if commander_id == 6
                else "키스 남청·파랑·하늘색 장비색·"
            )
            + "아론 머리 앞 흰 검날과 오른쪽 방패 형태 유지·"
            f"변경 {changed}픽셀"
        )
        if commander_id == 6:
            previous_revision = int(row.get("design_revision", 0))
            row["design_override"] = False
            row["design_revision"] = 0
            row["design_override_superseded"] = True
            row["superseded_design_revision"] = max(
                previous_revision,
                int(row.get("superseded_design_revision", 0)),
                1785120121020121547,
            )
    manifest["asset_version"] = ASSET_VERSION
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    report = build()
    apply_live(report)
    print(
        json.dumps(
            {
                "all_accepted": report["all_accepted"],
                "targets": ["4:04", "6:04", "7:04"],
                "asset_version": ASSET_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
