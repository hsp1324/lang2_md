#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    commander_sprite_map,
    render_sprite,
)
from tools.build_test_class_sprite_assets import (
    TRANSPARENT,
    class_family,
    class_tiers,
    protected_face_points,
)
from tools.class_change_data import COMMANDER_COUNT
from tools.scenario_data import KOREAN_NAME_BY_ID, class_names


DEFAULT_SHEET = (
    ROOT / "docs/assets/ai-class-source/allied_class_ai_evolution_v2.png"
)
ELWIN_DIRECT_SHEET = (
    ROOT
    / "docs/assets/ai-class-source/commanders/"
    / "01-elwin-logical16-reference.png"
)
DEFAULT_OUTPUT = ROOT / "editor/static/ai-class-sprites"
GRID_COLUMNS = 5
GRID_ROWS = 10


def cell_bounds(
    image: Image.Image,
    row: int,
    column: int,
    *,
    rows: int = GRID_ROWS,
    columns: int = GRID_COLUMNS,
) -> tuple[int, int, int, int]:
    return (
        round(column * image.width / columns),
        round(row * image.height / rows),
        round((column + 1) * image.width / columns),
        round((row + 1) * image.height / rows),
    )


def remove_black_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, _ = rgba.getpixel((x, y))
            if max(red, green, blue) <= 12:
                rgba.putpixel((x, y), TRANSPARENT)
    return rgba


def source_subject(image: Image.Image) -> Image.Image:
    subject = remove_black_background(image)
    bbox = subject.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("AI source cell is empty")
    return subject.crop(bbox)


def pixelize_cell(
    sheet: Image.Image,
    row: int,
    column: int,
    *,
    rows: int = GRID_ROWS,
    columns: int = GRID_COLUMNS,
) -> Image.Image:
    cell = remove_black_background(
        sheet.crop(
            cell_bounds(
                sheet,
                row,
                column,
                rows=rows,
                columns=columns,
            )
        )
    )
    bbox = cell.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"AI sheet cell {row},{column} is empty")
    subject = cell.crop(bbox)
    scale = min(15 / subject.width, 15 / subject.height)
    size = (
        max(1, round(subject.width * scale)),
        max(1, round(subject.height * scale)),
    )
    subject = subject.resize(size, Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (16, 16), TRANSPARENT)
    x = (16 - subject.width) // 2
    y = 16 - subject.height
    canvas.alpha_composite(subject, (x, y))
    alpha = canvas.getchannel("A").point(
        lambda value: 255 if value >= 96 else 0
    )
    rgb = Image.new("RGB", canvas.size, (0, 0, 0))
    rgb.paste(canvas.convert("RGB"), mask=alpha)
    quantized = rgb.quantize(
        colors=16,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    ).convert("RGBA")
    quantized.putalpha(alpha)
    return quantized


def elwin_direct_column(class_id: int, tier: int) -> int:
    family = class_family(class_id)
    if family == "cavalry":
        return (1, 1, 3, 4, 6)[tier - 1]
    if family in {"dragon", "sea"}:
        return 6
    if family == "mage":
        return (2, 2, 2, 3, 5)[tier - 1]
    if family == "cleric":
        return (2, 2, 3, 4, 5)[tier - 1]
    return (0, 1, 3, 5, 6)[tier - 1]


def dominant_colors(
    image: Image.Image,
    count: int = 6,
) -> list[str]:
    rgba = image.convert("RGBA")
    colors = rgba.getcolors(maxcolors=rgba.width * rgba.height) or []
    visible = [
        (frequency, color)
        for frequency, color in colors
        if color[3] >= 96 and max(color[:3]) > 45
    ]
    visible.sort(reverse=True)
    return [
        f"#{red:02x}{green:02x}{blue:02x}"
        for _, (red, green, blue, _) in visible[:count]
    ]


def overlay_rom_head(
    image: Image.Image,
    source: Image.Image,
) -> tuple[Image.Image, int]:
    result = image.copy()
    protected = protected_face_points(source)
    if not protected:
        return result, 0
    left = max(0, min(x for x, _ in protected) - 1)
    right = min(15, max(x for x, _ in protected) + 1)
    top = max(0, min(y for _, y in protected) - 1)
    bottom = min(8, max(y for _, y in protected) + 1)
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            result.putpixel((x, y), source.getpixel((x, y)))
    return result, (right - left + 1) * (bottom - top + 1)


def build_assets(
    rom_path: Path,
    sheet_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    source = rom_path.read_bytes()
    sheet = Image.open(sheet_path).convert("RGB")
    elwin_sheet = Image.open(ELWIN_DIRECT_SHEET).convert("RGB")
    classes = class_names(source)
    commanders: dict[str, object] = {}
    asset_count = 0
    redesigned_count = 0
    source_cell_dir = output_dir / "source-cells"
    source_cell_dir.mkdir(parents=True, exist_ok=True)
    source_cell_files: dict[tuple[int, int], str] = {}
    for commander_id in range(1, COMMANDER_COUNT + 1):
        for stage in range(1, GRID_COLUMNS + 1):
            target = source_cell_dir / f"{commander_id}-{stage}.png"
            source_subject(
                sheet.crop(
                    cell_bounds(sheet, commander_id - 1, stage - 1)
                )
            ).save(target, optimize=True)
            source_cell_files[(commander_id, stage)] = str(
                target.relative_to(output_dir)
            )
    elwin_cell_files: dict[int, str] = {}
    for column in range(7):
        target = source_cell_dir / f"1-direct-{column + 1}.png"
        source_subject(
            elwin_sheet.crop(
                cell_bounds(
                    elwin_sheet,
                    0,
                    column,
                    rows=1,
                    columns=7,
                )
            )
        ).save(target, optimize=True)
        elwin_cell_files[column] = str(target.relative_to(output_dir))

    for commander_id in range(1, COMMANDER_COUNT + 1):
        tiers = class_tiers(source, commander_id)
        sprite_map = commander_sprite_map(source, commander_id)
        by_sprite: dict[int, list[int]] = defaultdict(list)
        for class_id in tiers:
            by_sprite[sprite_map[class_id]].append(class_id)
        for class_ids in by_sprite.values():
            class_ids.sort(key=lambda value: (tiers[value], value))
        commander_dir = output_dir / str(commander_id)
        commander_dir.mkdir(parents=True, exist_ok=True)
        rows: dict[str, object] = {}
        for class_id, tier in sorted(tiers.items()):
            stage = max(1, min(GRID_COLUMNS, tier))
            if commander_id == 1:
                source_column = elwin_direct_column(class_id, tier)
                source_cell = elwin_sheet.crop(
                    cell_bounds(
                        elwin_sheet,
                        0,
                        source_column,
                        rows=1,
                        columns=7,
                    )
                )
                ai_base = pixelize_cell(
                    elwin_sheet,
                    0,
                    source_column,
                    rows=1,
                    columns=7,
                )
                source_cell_file = elwin_cell_files[source_column]
                source_kind = "ROM 원본 직접 참조 AI"
                source_position = f"직접 시안 {source_column + 1}"
            else:
                source_cell = sheet.crop(
                    cell_bounds(sheet, commander_id - 1, stage - 1)
                )
                ai_base = pixelize_cell(
                    sheet,
                    commander_id - 1,
                    stage - 1,
                )
                source_cell_file = source_cell_files[
                    (commander_id, stage)
                ]
                source_kind = "초기 AI 진화 시트"
                source_position = f"{commander_id}행 {stage}단계"
            rom_face = render_sprite(source, sprite_map[class_id], 1)
            group = by_sprite[sprite_map[class_id]]
            group_rank = group.index(class_id)
            redesigned = len(group) > 1 and group_rank > 0
            if redesigned:
                image, face_pixel_count = overlay_rom_head(
                    ai_base,
                    rom_face,
                )
                redesigned_count += 1
            else:
                image = rom_face
                face_pixel_count = 0
            target = commander_dir / f"{class_id:02X}.png"
            image.save(target, optimize=True)
            rows[str(class_id)] = {
                "class_id": class_id,
                "class_name": classes[class_id]["ko"],
                "tier": tier,
                "ai_sheet_row": commander_id,
                "ai_sheet_stage": stage,
                "ai_source_cell_file": source_cell_file,
                "ai_source_kind": source_kind,
                "ai_source_position": source_position,
                "source_palette": dominant_colors(
                    remove_black_background(source_cell)
                ),
                "pixel_palette": dominant_colors(image),
                "face_source_sprite_id": sprite_map[class_id],
                "face_pixel_count": face_pixel_count,
                "duplicate_group": group,
                "group_rank": group_rank,
                "redesigned": redesigned,
                "feature": (
                    "AI 원화 최근접 축소·셀별 적응형 15색·ROM 머리 영역 복원"
                    if redesigned
                    else "중복 그림 묶음의 최저 클래스·ROM 원본 유지"
                ),
                "file": str(target.relative_to(output_dir)),
            }
            asset_count += 1
        commanders[str(commander_id)] = {
            "name": KOREAN_NAME_BY_ID[commander_id],
            "classes": rows,
        }

    manifest = {
        "generated_from": str(rom_path.relative_to(ROOT)),
        "ai_source_sheets": [
            str(sheet_path.relative_to(ROOT)),
            str(ELWIN_DIRECT_SHEET.relative_to(ROOT)),
        ],
        "commander_count": len(commanders),
        "asset_count": asset_count,
        "redesigned_count": redesigned_count,
        "pipeline": (
            "AI concept cell -> background removal -> nearest-neighbor 16x16 "
            "-> per-cell adaptive palette -> original ROM face pixels"
        ),
        "rom_effect": "none; preview PNG assets only",
        "commanders": commanders,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build AI-derived allied class-change sprite previews"
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_assets(args.rom, args.sheet, args.output)
    print(
        f"{args.output}: {manifest['commander_count']} commanders, "
        f"{manifest['asset_count']} AI-derived class sprites"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
