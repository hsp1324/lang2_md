#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageFilter

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
    class_tiers,
)
from tools.class_change_data import COMMANDER_COUNT
from tools.scenario_data import KOREAN_NAME_BY_ID, class_names


DEFAULT_SHEET = ROOT / "docs/assets/allied_class_redesign_concept.png"
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


def source_foreground(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    seed = Image.new("L", rgb.size, 0)
    for y in range(rgb.height):
        for x in range(rgb.width):
            red, green, blue = rgb.getpixel((x, y))
            brightest = max(red, green, blue)
            chroma = brightest - min(red, green, blue)
            if brightest >= 55 or chroma >= 18:
                seed.putpixel((x, y), 255)

    # The concept sheet is already pixel art, but its black outlines sit on a
    # dark gray background. Grow from visible color instead of treating every
    # dark pixel as background so the outlines survive without the broad glow.
    mask = central_component(seed.filter(ImageFilter.MaxFilter(13)))
    rgba = rgb.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def central_component(mask: Image.Image) -> Image.Image:
    width, height = mask.size
    active = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if mask.getpixel((x, y)) >= 128
    }
    components: list[set[tuple[int, int]]] = []
    while active:
        start = active.pop()
        component = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for ny in range(max(0, y - 1), min(height, y + 2)):
                for nx in range(max(0, x - 1), min(width, x + 2)):
                    point = (nx, ny)
                    if point in active:
                        active.remove(point)
                        component.add(point)
                        pending.append(point)
        components.append(component)
    if not components:
        return mask

    center_x = (width - 1) / 2
    center_y = (height - 1) / 2
    largest = max(len(component) for component in components)
    candidates = [
        component
        for component in components
        if len(component) >= largest * 0.2
    ]
    selected = min(
        candidates,
        key=lambda component: (
            (
                sum(x for x, _ in component) / len(component) - center_x
            )
            ** 2
            + (
                sum(y for _, y in component) / len(component) - center_y
            )
            ** 2,
            -len(component),
        ),
    )
    result = Image.new("L", mask.size, 0)
    for point in selected:
        result.putpixel(point, 255)
    return result


def source_subject(image: Image.Image) -> Image.Image:
    subject = source_foreground(image)
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
    cell = source_subject(
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
    alpha = cell.getchannel("A")
    rgb = Image.new("RGB", cell.size, (0, 0, 0))
    rgb.paste(cell.convert("RGB"), mask=alpha)
    palette_source = rgb.quantize(
        colors=15,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    ).convert("RGB")

    # The AI sheet is high-resolution pseudo-pixel art. A single NEAREST
    # sample per destination pixel can land between its macro pixels and erase
    # small features such as eyes. Collapse every source block by its dominant
    # pre-quantized color instead, using the complete 16x16 destination extent.
    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    for target_y in range(16):
        source_y0 = target_y * cell.height // 16
        source_y1 = max(
            source_y0 + 1,
            (target_y + 1) * cell.height // 16,
        )
        for target_x in range(16):
            source_x0 = target_x * cell.width // 16
            source_x1 = max(
                source_x0 + 1,
                (target_x + 1) * cell.width // 16,
            )
            colors: Counter[tuple[int, int, int]] = Counter()
            visible = 0
            sample_count = (
                (source_x1 - source_x0) * (source_y1 - source_y0)
            )
            for source_y in range(source_y0, source_y1):
                for source_x in range(source_x0, source_x1):
                    if alpha.getpixel((source_x, source_y)) < 64:
                        continue
                    visible += 1
                    colors[palette_source.getpixel((source_x, source_y))] += 1
            if visible < max(1, sample_count // 10):
                continue
            color = colors.most_common(1)[0][0]
            result.putpixel((target_x, target_y), (*color, 255))

    return result


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


def build_assets(
    rom_path: Path,
    sheet_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    source = rom_path.read_bytes()
    sheet = Image.open(sheet_path).convert("RGB")
    classes = class_names(source)
    commanders: dict[str, object] = {}
    asset_count = 0
    redesigned_count = 0
    if output_dir.exists():
        shutil.rmtree(output_dir)
    source_cell_dir = output_dir / "source-cells"
    source_cell_dir.mkdir(parents=True, exist_ok=True)
    source_cell_files: dict[tuple[int, int], str] = {}
    pixelized_cells: dict[tuple[int, int], Image.Image] = {}
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
            pixelized_cells[(commander_id, stage)] = pixelize_cell(
                sheet,
                commander_id - 1,
                stage - 1,
            )

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
            source_cell = sheet.crop(
                cell_bounds(sheet, commander_id - 1, stage - 1)
            )
            ai_base = pixelized_cells[(commander_id, stage)]
            source_cell_file = source_cell_files[
                (commander_id, stage)
            ]
            source_kind = "선호 AI 도트 진화 시트"
            source_position = f"{commander_id}행 {stage}단계"
            rom_face = render_sprite(source, sprite_map[class_id], 1)
            group = by_sprite[sprite_map[class_id]]
            group_rank = group.index(class_id)
            redesigned = len(group) > 1 and group_rank > 0
            if redesigned:
                image = ai_base
                redesigned_count += 1
            else:
                image = rom_face
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
                    source_foreground(source_cell)
                ),
                "pixel_palette": dominant_colors(image),
                "face_source_sprite_id": sprite_map[class_id],
                "face_pixel_count": 0,
                "duplicate_group": group,
                "group_rank": group_rank,
                "redesigned": redesigned,
                "feature": (
                    "AI 원화 중앙 전경·16×16 블록 집계·셀별 적응형 15색·고정 영역 없음"
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
        ],
        "commander_count": len(commanders),
        "asset_count": asset_count,
        "redesigned_count": redesigned_count,
        "pipeline": (
            "AI concept cell -> central foreground isolation -> adaptive "
            "palette -> dominant-block 16x16"
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
