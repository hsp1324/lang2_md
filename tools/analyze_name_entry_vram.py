#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw


GST_VRAM_OFFSET = 0x12478
VRAM_SIZE = 0x10000
PLANE_WIDTH_TILES = 64
PLANE_HEIGHT_TILES = 32


def parse_int(text: str) -> int:
    return int(text, 0)


def load_vram(path: Path, offset: int) -> bytes:
    data = path.read_bytes()
    vram = data[offset : offset + VRAM_SIZE]
    if len(vram) != VRAM_SIZE:
        raise ValueError(f"{path} does not contain {VRAM_SIZE} VRAM bytes at 0x{offset:X}")
    return vram


def md_4bpp_tile(vram: bytes, tile_id: int) -> list[list[int]]:
    offset = tile_id * 32
    pixels = [[0 for _ in range(8)] for _ in range(8)]
    if offset + 32 > len(vram):
        return pixels
    for y in range(8):
        row = vram[offset + y * 4 : offset + y * 4 + 4]
        for x in range(8):
            shift = 7 - x
            pixels[y][x] = (
                (((row[0] >> shift) & 1) << 3)
                | (((row[1] >> shift) & 1) << 2)
                | (((row[2] >> shift) & 1) << 1)
                | ((row[3] >> shift) & 1)
            )
    return pixels


def render_tile(vram: bytes, tile_id: int, palette_index: int, hflip: bool, vflip: bool, scale: int) -> Image.Image:
    palettes = [
        [(0, 0, 80), (80, 80, 120), (150, 150, 180), (255, 255, 255)] * 4,
        [(0, 0, 0), (70, 70, 70), (160, 160, 160), (255, 255, 255)] * 4,
        [(0, 30, 0), (50, 120, 50), (160, 220, 160), (255, 255, 255)] * 4,
        [(40, 0, 0), (130, 50, 50), (220, 160, 160), (255, 255, 255)] * 4,
    ]
    palette = palettes[palette_index & 3]
    pixels = md_4bpp_tile(vram, tile_id)
    img = Image.new("RGB", (8 * scale, 8 * scale), palette[0])
    for y in range(8):
        for x in range(8):
            sx = 7 - x if hflip else x
            sy = 7 - y if vflip else y
            color = palette[pixels[sy][sx] & 0x0F]
            img.paste(color, (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale))
    return img


def plane_entry(vram: bytes, plane_base: int, x: int, y: int) -> int:
    offset = plane_base + ((y * PLANE_WIDTH_TILES + x) * 2)
    return int.from_bytes(vram[offset : offset + 2], "big")


def render_plane(vram: bytes, plane_base: int, scale: int, label: bool) -> Image.Image:
    img = Image.new("RGB", (PLANE_WIDTH_TILES * 8 * scale, PLANE_HEIGHT_TILES * 8 * scale), (0, 0, 40))
    draw = ImageDraw.Draw(img)
    for y in range(PLANE_HEIGHT_TILES):
        for x in range(PLANE_WIDTH_TILES):
            entry = plane_entry(vram, plane_base, x, y)
            tile_id = entry & 0x07FF
            hflip = bool(entry & 0x0800)
            vflip = bool(entry & 0x1000)
            palette = (entry >> 13) & 3
            tile = render_tile(vram, tile_id, palette, hflip, vflip, scale)
            px = x * 8 * scale
            py = y * 8 * scale
            img.paste(tile, (px, py))
            if label and tile_id:
                draw.text((px, py), f"{tile_id:03X}", fill=(255, 60, 60))
    return img


def dump_plane_csv(vram: bytes, plane_base: int, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["x", "y", "entry", "tile", "palette", "hflip", "vflip", "priority"])
        for y in range(PLANE_HEIGHT_TILES):
            for x in range(PLANE_WIDTH_TILES):
                entry = plane_entry(vram, plane_base, x, y)
                tile_id = entry & 0x07FF
                if not tile_id:
                    continue
                writer.writerow(
                    [
                        x,
                        y,
                        f"{entry:04X}",
                        f"{tile_id:03X}",
                        (entry >> 13) & 3,
                        int(bool(entry & 0x0800)),
                        int(bool(entry & 0x1000)),
                        int(bool(entry & 0x8000)),
                    ]
                )


def dump_grid_csv(
    vram: bytes,
    plane_base: int,
    x0: int,
    y0: int,
    cols: int,
    rows: int,
    cell_w: int,
    cell_h: int,
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["col", "row", "x", "y", "tiles"])
        for row in range(rows):
            for col in range(cols):
                x = x0 + col * cell_w
                y = y0 + row * cell_h
                tiles: list[str] = []
                for dy in range(cell_h):
                    for dx in range(cell_w):
                        entry = plane_entry(vram, plane_base, x + dx, y + dy)
                        tiles.append(f"{entry & 0x07FF:03X}")
                writer.writerow([col, row, x, y, " ".join(tiles)])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gst", type=Path)
    parser.add_argument("--vram-offset", type=parse_int, default=GST_VRAM_OFFSET)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--label", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("captures/analysis/name_entry_probe"))
    parser.add_argument("--grid-plane", type=parse_int, default=0xE000)
    parser.add_argument("--grid-x", type=int, default=0)
    parser.add_argument("--grid-y", type=int, default=0)
    parser.add_argument("--grid-cols", type=int, default=0)
    parser.add_argument("--grid-rows", type=int, default=0)
    parser.add_argument("--grid-cell-w", type=int, default=2)
    parser.add_argument("--grid-cell-h", type=int, default=2)
    args = parser.parse_args()

    vram = load_vram(args.gst, args.vram_offset)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for plane_base in (0xC000, 0xE000, 0xF000):
        suffix = f"{plane_base:04x}"
        render_plane(vram, plane_base, args.scale, args.label).save(args.out_dir / f"plane_{suffix}.png")
        dump_plane_csv(vram, plane_base, args.out_dir / f"plane_{suffix}.csv")
    if args.grid_cols and args.grid_rows:
        dump_grid_csv(
            vram,
            args.grid_plane,
            args.grid_x,
            args.grid_y,
            args.grid_cols,
            args.grid_rows,
            args.grid_cell_w,
            args.grid_cell_h,
            args.out_dir / "grid_cells.csv",
        )
    print(args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
