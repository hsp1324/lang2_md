#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw


GST_VRAM_OFFSET = 0x12478
VRAM_SIZE = 0x10000
NEAREST = getattr(getattr(Image, "Resampling", Image), "NEAREST")


def parse_int(text: str) -> int:
    return int(text, 0)


def load_vram(path: Path, offset: int) -> bytes:
    data = path.read_bytes()
    vram = data[offset : offset + VRAM_SIZE]
    if len(vram) != VRAM_SIZE:
        raise ValueError(f"{path} does not contain a full VRAM dump at 0x{offset:X}")
    return vram


def tile_pixels(vram: bytes, tile_id: int) -> list[list[int]]:
    base = tile_id * 32
    pixels = [[0 for _ in range(8)] for _ in range(8)]
    if base + 32 > len(vram):
        return pixels
    for y in range(8):
        row = vram[base + y * 4 : base + y * 4 + 4]
        for x in range(8):
            value = row[x // 2]
            pixels[y][x] = (value >> 4) & 0x0F if x % 2 == 0 else value & 0x0F
    return pixels


def render_block(vram: bytes, tile_id: int, block_w: int, block_h: int) -> Image.Image:
    img = Image.new("L", (block_w * 8, block_h * 8), 0)
    for ty in range(block_h):
        for tx in range(block_w):
            sub = ty * block_w + tx
            ox = tx * 8
            oy = ty * 8
            pixels = tile_pixels(vram, tile_id + sub)
            for y in range(8):
                for x in range(8):
                    value = pixels[y][x]
                    img.putpixel((ox + x, oy + y), 255 if value else 0)
    return img


def render_block_old_order(vram: bytes, tile_id: int, block_w: int, block_h: int) -> Image.Image:
    img = Image.new("L", (block_w * 8, block_h * 8), 0)
    for tx in range(block_w):
        for ty in range(block_h):
            sub = tx * block_h + ty
            ox = tx * 8
            oy = ty * 8
            pixels = tile_pixels(vram, tile_id + sub)
            for y in range(8):
                for x in range(8):
                    value = pixels[y][x]
                    img.putpixel((ox + x, oy + y), 255 if value else 0)
    return img


def crop_mask(image: Image.Image, x: int, y: int, width: int, height: int) -> Image.Image:
    crop = image.crop((x, y, x + width, y + height)).convert("RGB")
    mask = Image.new("L", (width, height), 0)
    for yy in range(height):
        for xx in range(width):
            r, g, b = crop.getpixel((xx, yy))
            # White/gray text on dark blue; ignore yellow frame and blue background.
            if r > 135 and g > 135 and b > 135 and max(r, g, b) - min(r, g, b) < 90:
                mask.putpixel((xx, yy), 255)
    return mask


def score_masks(a: Image.Image, b: Image.Image) -> tuple[float, int, int, int]:
    intersection = 0
    union = 0
    a_count = 0
    b_count = 0
    width, height = a.size
    if b.size != a.size:
        b = b.resize(a.size, NEAREST)
    for y in range(height):
        for x in range(width):
            av = a.getpixel((x, y)) > 0
            bv = b.getpixel((x, y)) > 0
            if av:
                a_count += 1
            if bv:
                b_count += 1
            if av and bv:
                intersection += 1
            if av or bv:
                union += 1
    return ((intersection / union) if union else 0.0, intersection, a_count, b_count)


def parse_crop(text: str) -> tuple[str, int, int]:
    # label:x:y
    label, x_text, y_text = text.split(":", 2)
    return label, int(x_text), int(y_text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gst", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--crop", action="append", required=True, help="label:x:y crop anchor")
    parser.add_argument("--vram-offset", type=parse_int, default=GST_VRAM_OFFSET)
    parser.add_argument("--tile-start", type=parse_int, default=0x000)
    parser.add_argument("--tile-end", type=parse_int, default=0x7FC)
    parser.add_argument("--block-w", type=int, default=2)
    parser.add_argument("--block-h", type=int, default=2)
    parser.add_argument("--crop-w", type=int, default=16)
    parser.add_argument("--crop-h", type=int, default=16)
    parser.add_argument("--column-major", action="store_true", help="render consecutive tiles down first, useful for 8x16 glyphs")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-sheet", type=Path, required=True)
    args = parser.parse_args()

    vram = load_vram(args.gst, args.vram_offset)
    image = Image.open(args.image)
    rows: list[dict[str, str]] = []
    sheet_rows: list[tuple[str, Image.Image, list[tuple[int, float, Image.Image]]]] = []
    for label, x, y in [parse_crop(crop) for crop in args.crop]:
        target = crop_mask(image, x, y, args.crop_w, args.crop_h)
        matches: list[tuple[int, float, Image.Image]] = []
        for tile_id in range(args.tile_start, args.tile_end + 1):
            if args.column_major:
                block = render_block_old_order(vram, tile_id, args.block_w, args.block_h)
            else:
                block = render_block(vram, tile_id, args.block_w, args.block_h)
            score, intersection, a_count, b_count = score_masks(target, block)
            matches.append((tile_id, score, block))
            rows.append(
                {
                    "label": label,
                    "x": str(x),
                    "y": str(y),
                    "tile": f"{tile_id:03X}",
                    "score": f"{score:.4f}",
                    "intersection": str(intersection),
                    "target_pixels": str(a_count),
                    "candidate_pixels": str(b_count),
                }
            )
        matches.sort(key=lambda row: row[1], reverse=True)
        sheet_rows.append((label, target, matches[: args.top]))

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["label", "x", "y", "tile", "score", "intersection", "target_pixels", "candidate_pixels"],
        )
        writer.writeheader()
        writer.writerows(rows)

    scale = 4
    label_w = 80
    cell_w = args.crop_w * scale
    cell_h = args.crop_h * scale
    gap = 8
    width = label_w + (1 + args.top) * (cell_w + gap)
    height = len(sheet_rows) * (cell_h + 16 + gap)
    sheet = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for label, target, matches in sheet_rows:
        draw.text((4, y + 20), label, fill=(0, 0, 0))
        sheet.paste(target.resize((cell_w, cell_h), NEAREST).convert("RGB"), (label_w, y + 16))
        x = label_w + cell_w + gap
        for tile_id, score, block in matches:
            draw.text((x, y), f"{tile_id:03X} {score:.2f}", fill=(0, 0, 0))
            sheet.paste(block.resize((cell_w, cell_h), NEAREST).convert("RGB"), (x, y + 16))
            x += cell_w + gap
        y += cell_h + 16 + gap
    args.out_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out_sheet)
    print(args.out_sheet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
