#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import colorsys
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
DEFAULT_BOARD_DIR = (
    ROOT
    / "docs/assets/ai-class-source/identity-locked-class-boards"
)
DEFAULT_OUTPUT = ROOT / "editor/static/ai-class-sprites"
GRID_COLUMNS = 5
GRID_ROWS = 10

RESAMPLING = getattr(Image, "Resampling", Image)
QUANTIZE = getattr(Image, "Quantize", Image)
DITHER = getattr(Image, "Dither", Image)

# Each generated board contains only the classes whose ROM map image is shared
# with a lower class for that commander.  Keeping the cell order explicit
# avoids guessing from the art and makes an incorrectly positioned crop
# impossible.
BOARD_SPECS: dict[int, dict[str, object]] = {
    1: {
        "file": "01-elwin.png",
        "columns": 4,
        "rows": 3,
        "class_ids": [0x04, 0x0B, 0x0C, 0x12, 0x13, 0x14, 0x1A, 0x1B, 0x1D, 0x22],
    },
    2: {
        "file": "02-liana.png",
        "columns": 4,
        "rows": 3,
        "class_ids": [0x08, 0x0B, 0x11, 0x13, 0x14, 0x15, 0x16, 0x18, 0x19, 0x1D, 0x28],
    },
    3: {
        "file": "03-lana.png",
        "columns": 4,
        "rows": 3,
        "class_ids": [0x08, 0x0B, 0x11, 0x13, 0x14, 0x15, 0x16, 0x18, 0x19, 0x1D, 0x28],
    },
    4: {
        "file": "04-sherry.png",
        "columns": 4,
        "rows": 3,
        "class_ids": [0x04, 0x0B, 0x13, 0x14, 0x15, 0x17, 0x19, 0x1D, 0x1E, 0x21, 0x23],
    },
    5: {
        "file": "05-hein.png",
        "columns": 4,
        "rows": 3,
        "class_ids": [0x09, 0x0A, 0x0B, 0x13, 0x14, 0x15, 0x16, 0x18, 0x19, 0x1A, 0x28],
    },
    6: {
        "file": "06-scott.png",
        "columns": 4,
        "rows": 2,
        "class_ids": [0x04, 0x0B, 0x0C, 0x19, 0x1B, 0x1D, 0x1E, 0x29],
    },
    7: {
        "file": "07-keith.png",
        "columns": 5,
        "rows": 3,
        "class_ids": [0x04, 0x0B, 0x11, 0x15, 0x16, 0x19, 0x1A, 0x1D, 0x1E, 0x24],
    },
    8: {
        "file": "08-aaron.png",
        "columns": 5,
        "rows": 3,
        "class_ids": [0x04, 0x0B, 0x0C, 0x13, 0x14, 0x17, 0x19, 0x1A, 0x1B, 0x23],
    },
    9: {
        "file": "09-lester.png",
        "columns": 3,
        "rows": 3,
        "class_ids": [0x0C, 0x13, 0x14, 0x15, 0x19, 0x1B, 0x1D, 0x1F, 0x2A],
    },
    10: {
        "file": "10-jessica.png",
        "columns": 4,
        "rows": 3,
        "class_ids": [0x09, 0x0B, 0x11, 0x13, 0x14, 0x15, 0x16, 0x18, 0x19, 0x1A, 0x26],
    },
}


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
            if brightest >= 60 or chroma >= 20:
                seed.putpixel((x, y), 255)

    # The concept sheet is already pixel art, but its black outlines sit on a
    # dark gray background. Grow from visible color instead of treating every
    # dark pixel as background. Three source pixels are enough to retain the
    # outline while excluding the broad dark glow around each sprite.
    mask = central_component(seed.filter(ImageFilter.MaxFilter(7)))
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


def accent_hue_bucket(color: tuple[int, int, int]) -> int | None:
    red, green, blue = (channel / 255 for channel in color)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    if saturation < 0.45 or value < 0.4:
        return None
    return int(hue * 12) % 12


def accent_hues(
    image: Image.Image,
    *,
    minimum: int | None = None,
) -> set[int]:
    counts: Counter[int] = Counter()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = image.getpixel((x, y))
            if alpha < 64:
                continue
            bucket = accent_hue_bucket((red, green, blue))
            if bucket is not None:
                counts[bucket] += 1
    if minimum is None:
        minimum = max(
            8,
            round(image.width * image.height * 0.0015),
        )
    return {
        bucket
        for bucket, frequency in counts.items()
        if frequency >= minimum
    }


def nearest_detail_sample(image: Image.Image) -> Image.Image:
    wanted_hues = accent_hues(image)
    best: tuple[tuple[int, int, int, int], Image.Image] | None = None
    for offset_y in range(-1, 2):
        for offset_x in range(-1, 2):
            shifted = Image.new("RGBA", image.size, TRANSPARENT)
            shifted.alpha_composite(image, (-offset_x, -offset_y))
            candidate = shifted.resize((16, 16), RESAMPLING.NEAREST)
            score = (
                len(wanted_hues & accent_hues(candidate, minimum=1)),
                -abs(offset_x) - abs(offset_y),
                -abs(offset_y),
                -abs(offset_x),
            )
            if best is None or score > best[0]:
                best = (score, candidate)
    if best is None:
        raise ValueError("AI source cell produced no sampling candidate")
    return best[1]


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
    # The concept sheet uses enlarged pseudo-pixels. Sample those blocks
    # directly into the complete 16x16 destination instead of averaging them;
    # averaging destroys one-pixel eyes and thin weapon edges. MAXCOVERAGE
    # retains small, high-contrast accent colors that MEDIANCUT discards.
    sampled = nearest_detail_sample(cell)
    alpha = sampled.getchannel("A").point(
        lambda value: 255 if value >= 64 else 0
    )
    rgb = Image.new("RGB", sampled.size, (0, 0, 0))
    rgb.paste(sampled.convert("RGB"), mask=alpha)
    palette = rgb.quantize(
        colors=15,
        method=QUANTIZE.MAXCOVERAGE,
        dither=DITHER.NONE,
    ).convert("RGB")
    result = palette.convert("RGBA")
    result.putalpha(alpha)
    return result


def board_cell(
    board: Image.Image,
    index: int,
    *,
    rows: int,
    columns: int,
) -> Image.Image:
    row, column = divmod(index, columns)
    if row >= rows:
        raise ValueError(
            f"board cell {index} exceeds {columns}x{rows} layout"
        )
    return board.crop(
        cell_bounds(
            board,
            row,
            column,
            rows=rows,
            columns=columns,
        )
    )


def quantize_16_color_rgba(
    image: Image.Image,
    *,
    visible_colors: int = 15,
) -> Image.Image:
    alpha = image.getchannel("A").point(
        lambda value: 255 if value >= 64 else 0
    )
    rgb = Image.new("RGB", image.size, (0, 0, 0))
    rgb.paste(image.convert("RGB"), mask=alpha)
    palette = rgb.quantize(
        colors=visible_colors,
        method=QUANTIZE.MAXCOVERAGE,
        dither=DITHER.NONE,
    ).convert("RGB")
    result = palette.convert("RGBA")
    result.putalpha(alpha)
    return result


def fit_subject_to_16(
    image: Image.Image,
    *,
    maximum_extent: int = 16,
    foreground_isolated: bool = False,
) -> Image.Image:
    """Fit a generated sprite without stretching, clipping, or averaging it.

    Preserve the generated board's hard source pixels with nearest-neighbour
    sampling, use the complete 16-pixel extent on the limiting axis, center
    horizontally, and align feet or a mount to the bottom row. Reserving even
    one blank border pixel here discards too much class equipment.
    """

    subject = (
        image.convert("RGBA")
        if foreground_isolated
        else source_subject(image)
    )
    width, height = subject.size
    scale = min(maximum_extent / width, maximum_extent / height)
    target_width = max(1, min(maximum_extent, round(width * scale)))
    target_height = max(1, min(maximum_extent, round(height * scale)))
    sampled = subject.resize(
        (target_width, target_height),
        RESAMPLING.NEAREST,
    )
    sampled = quantize_16_color_rgba(sampled)
    sampled_bbox = sampled.getchannel("A").getbbox()
    if sampled_bbox is None:
        raise ValueError("generated class cell vanished during 16x16 fit")
    sampled = sampled.crop(sampled_bbox)
    target_width, target_height = sampled.size
    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    x = (16 - target_width) // 2
    y = 16 - target_height
    result.alpha_composite(sampled, (x, y))
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
    board_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    source = rom_path.read_bytes()
    classes = class_names(source)
    commanders: dict[str, object] = {}
    asset_count = 0
    redesigned_count = 0
    if output_dir.exists():
        shutil.rmtree(output_dir)
    source_cell_dir = output_dir / "source-cells"
    source_cell_dir.mkdir(parents=True, exist_ok=True)

    board_subjects: dict[tuple[int, int], Image.Image] = {}
    converted_subjects: dict[tuple[int, int], Image.Image] = {}
    source_cell_files: dict[tuple[int, int], str] = {}
    board_paths: list[Path] = []
    for commander_id, spec in BOARD_SPECS.items():
        board_path = board_dir / str(spec["file"])
        board_paths.append(board_path)
        board = Image.open(board_path).convert("RGB")
        rows = int(spec["rows"])
        columns = int(spec["columns"])
        class_ids = list(spec["class_ids"])
        for index, class_id in enumerate(class_ids):
            cell = board_cell(
                board,
                index,
                rows=rows,
                columns=columns,
            )
            subject = source_subject(cell)
            target = (
                source_cell_dir
                / f"{commander_id}-{class_id:02X}.png"
            )
            subject.save(target, optimize=True)
            key = (commander_id, class_id)
            board_subjects[key] = subject
            converted_subjects[key] = fit_subject_to_16(
                subject,
                foreground_isolated=True,
            )
            source_cell_files[key] = str(
                target.relative_to(output_dir)
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
            rom_face = render_sprite(source, sprite_map[class_id], 1)
            group = by_sprite[sprite_map[class_id]]
            group_rank = group.index(class_id)
            redesigned = len(group) > 1 and group_rank > 0
            if redesigned:
                key = (commander_id, class_id)
                if key not in converted_subjects:
                    raise ValueError(
                        "generated board is missing redesigned class "
                        f"{commander_id}:{class_id:02X}"
                    )
                # The source board was generated from the ROM character
                # reference. Keep its head/neck/body drawing coherent.
                # Pasting a rectangular ROM head over it erased shoulders,
                # weapon edges, wings, and mounts at this tiny resolution.
                image = converted_subjects[key]
                face_pixel_count = 0
                source_image = board_subjects[key]
                source_cell_file = source_cell_files[key]
                spec = BOARD_SPECS[commander_id]
                cell_index = list(spec["class_ids"]).index(class_id)
                source_kind = "원작 정체성 기반 AI 클래스별 보드"
                source_position = (
                    f"{commander_id}번 지휘관 · "
                    f"{cell_index + 1}번 클래스 셀"
                )
                redesigned_count += 1
            else:
                image = rom_face
                face_pixel_count = 0
                source_image = rom_face
                source_cell_file = None
                source_kind = "중복 묶음 기준 ROM 원본"
                source_position = (
                    f"{commander_id}번 지휘관 · AI 미적용"
                )
            target = commander_dir / f"{class_id:02X}.png"
            image.save(target, optimize=True)
            rows[str(class_id)] = {
                "class_id": class_id,
                "class_name": classes[class_id]["ko"],
                "tier": tier,
                "ai_sheet_row": commander_id,
                "ai_sheet_stage": tier,
                "ai_source_cell_file": source_cell_file,
                "ai_source_kind": source_kind,
                "ai_source_position": source_position,
                "source_palette": dominant_colors(
                    source_image
                ),
                "pixel_palette": dominant_colors(image),
                "face_source_sprite_id": sprite_map[class_id],
                "face_pixel_count": face_pixel_count,
                "duplicate_group": group,
                "group_rank": group_rank,
                "redesigned": redesigned,
                "feature": (
                    "원작 정체성 레퍼런스 AI 원화·얼굴/머리와 몸 연결 유지·16픽셀 전체 사용·종횡비 보존·바닥선 정렬·15색"
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
        "asset_version": "coherent-full-16-fit-2",
        "generated_from": str(rom_path.relative_to(ROOT)),
        "ai_source_sheets": [
            str(path.relative_to(ROOT))
            for path in board_paths
        ],
        "commander_count": len(commanders),
        "asset_count": asset_count,
        "redesigned_count": redesigned_count,
        "pipeline": (
            "original-identity-referenced class board -> fixed grid cell -> "
            "central foreground -> full-extent aspect-preserving nearest "
            "fit -> horizontal center + bottom alignment -> coherent AI "
            "head/body retained -> 15-color palette"
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
    parser.add_argument(
        "--boards",
        type=Path,
        default=DEFAULT_BOARD_DIR,
        help="directory containing the per-commander generated class boards",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_assets(args.rom, args.boards, args.output)
    print(
        f"{args.output}: {manifest['commander_count']} commanders, "
        f"{manifest['asset_count']} AI-derived class sprites"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
