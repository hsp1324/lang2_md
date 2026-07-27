#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

from PIL import Image, ImageDraw

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.jp_compressed_resource_inventory import (
    decoded_payload,
    direct_load_calls,
    resource_pointers,
)


DEFAULT_PALETTE = tuple(
    (value * 17, value * 17, value * 17, 255)
    for value in range(16)
)


def decode_4bpp_tiles(payload: bytes) -> list[list[int]]:
    if len(payload) % 32:
        raise ValueError(f"tile payload size {len(payload)} is not divisible by 32")
    tiles: list[list[int]] = []
    for tile_offset in range(0, len(payload), 32):
        pixels: list[int] = []
        tile = payload[tile_offset : tile_offset + 32]
        for row_offset in range(0, 32, 4):
            for value in tile[row_offset : row_offset + 4]:
                pixels.extend((value >> 4, value & 0x0F))
        if len(pixels) != 64:
            raise AssertionError("decoded tile is not 8x8")
        tiles.append(pixels)
    return tiles


def render_tiles(
    payload: bytes,
    tiles_per_row: int = 16,
    palette: tuple[tuple[int, int, int, int], ...] = DEFAULT_PALETTE,
) -> Image.Image:
    if tiles_per_row <= 0:
        raise ValueError("tiles_per_row must be positive")
    if len(palette) != 16:
        raise ValueError("palette must contain 16 colors")
    tiles = decode_4bpp_tiles(payload)
    columns = min(tiles_per_row, max(1, len(tiles)))
    rows = max(1, math.ceil(len(tiles) / columns))
    image = Image.new("RGBA", (columns * 8, rows * 8), palette[0])
    pixels = image.load()
    for tile_index, tile in enumerate(tiles):
        tile_x = (tile_index % columns) * 8
        tile_y = (tile_index // columns) * 8
        for pixel_index, color_index in enumerate(tile):
            pixels[tile_x + pixel_index % 8, tile_y + pixel_index // 8] = palette[
                color_index
            ]
    return image


def immediate_resource_indices(rom: bytes) -> list[int]:
    return sorted(
        {
            int(call["resource_index"])
            for call in direct_load_calls(rom)
            if call["immediate_resource"]
        }
    )


def parse_indices(value: str) -> list[int]:
    indices: set[int] = set()
    for part in value.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = int(start_text, 0)
            end = int(end_text, 0)
            if end < start:
                raise ValueError(f"descending resource range: {token}")
            indices.update(range(start, end + 1))
        else:
            indices.add(int(token, 0))
    return sorted(indices)


def render_atlas(
    rom: bytes,
    indices: list[int],
    tiles_per_row: int = 16,
    panel_columns: int = 4,
    scale: int = 2,
) -> Image.Image:
    if panel_columns <= 0:
        raise ValueError("panel_columns must be positive")
    if scale <= 0:
        raise ValueError("scale must be positive")
    pointers = resource_pointers(rom)
    panels: list[tuple[int, int, str, Image.Image]] = []
    for index in indices:
        if not 0 <= index < len(pointers):
            raise ValueError(f"resource index {index} is outside 0..{len(pointers) - 1}")
        pointer = pointers[index]
        payload = decoded_payload(rom, pointer)
        if payload is None:
            raise ValueError(f"resource {index} uses an unsupported decoder")
        panel = render_tiles(payload, tiles_per_row=tiles_per_row)
        label = (
            f"{index:03d}  type {rom[pointer]}  "
            f"{panel.width // 8 * panel.height // 8} tiles"
        )
        panels.append((index, rom[pointer], label, panel))

    label_height = 14
    padding = 6
    measuring_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    label_widths = [
        measuring_draw.textbbox((0, 0), label)[2]
        for _, _, label, _ in panels
    ]
    cell_width = max(
        [
            8,
            *(panel.width for _, _, _, panel in panels),
            *label_widths,
        ]
    ) + padding * 2
    cell_height = (
        max((panel.height for _, _, _, panel in panels), default=8)
        + label_height
        + padding * 2
    )
    panel_rows = max(1, math.ceil(len(panels) / panel_columns))
    atlas = Image.new(
        "RGBA",
        (cell_width * panel_columns, cell_height * panel_rows),
        (24, 24, 24, 255),
    )
    draw = ImageDraw.Draw(atlas)
    for position, (index, resource_type, label, panel) in enumerate(panels):
        column = position % panel_columns
        row = position // panel_columns
        x = column * cell_width + padding
        y = row * cell_height + padding
        draw.text(
            (x, y),
            label,
            fill=(240, 240, 240, 255),
        )
        atlas.alpha_composite(panel, (x, y + label_height))
    if scale != 1:
        atlas = atlas.resize(
            (atlas.width * scale, atlas.height * scale),
            Image.Resampling.NEAREST,
        )
    return atlas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render decoded Mega Drive compressed resources as 4bpp tile atlases"
    )
    parser.add_argument(
        "--rom",
        type=Path,
        default=Path("roms/original/Langrisser II (Japan).md"),
    )
    parser.add_argument(
        "--indices",
        help="comma-separated resource IDs or inclusive ranges; defaults to immediate-ID calls",
    )
    parser.add_argument("--tiles-per-row", type=int, default=16)
    parser.add_argument("--panel-columns", type=int, default=4)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/lang2_compressed_resource_atlas.png"),
    )
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    indices = (
        parse_indices(args.indices)
        if args.indices is not None
        else immediate_resource_indices(rom)
    )
    atlas = render_atlas(
        rom,
        indices,
        tiles_per_row=args.tiles_per_row,
        panel_columns=args.panel_columns,
        scale=args.scale,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(args.out)
    print(f"rendered {len(indices)} resources to {args.out}")


if __name__ == "__main__":
    main()
