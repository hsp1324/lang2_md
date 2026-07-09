#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


JP_FONT_BASE = 0x40000
GLYPH_BYTES = 64


def parse_int(text: str) -> int:
    return int(text, 0)


def be16(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def render_glyph_left_half(data: bytes, code: int, scale: int) -> Image.Image:
    offset = JP_FONT_BASE + code * GLYPH_BYTES
    img = Image.new("RGB", (8 * scale, 16 * scale), "white")
    palette = [
        (255, 255, 255),
        (170, 170, 170),
        (90, 90, 90),
        (0, 0, 0),
    ]
    for source_row in range(32):
        if source_row // 8 not in (0, 2):
            continue
        word = be16(data, offset + source_row * 2)
        row = source_row % 8
        y = row if source_row < 8 else row + 8
        for x in range(8):
            hi = (word >> (15 - x)) & 1
            lo = (word >> (7 - x)) & 1
            color = palette[(hi << 1) | lo]
            img.paste(color, (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale))
    return img


def read_byte_string(data: bytes, offset: int, max_len: int) -> list[int]:
    values: list[int] = []
    for pos in range(offset, min(offset + max_len, len(data))):
        value = data[pos]
        if value == 0xFF:
            break
        values.append(value)
    return values


def render_string(data: bytes, values: list[int], scale: int) -> Image.Image:
    width = max(1, len(values)) * 8 * scale
    img = Image.new("RGB", (width, 16 * scale), "white")
    for index, value in enumerate(values):
        glyph = render_glyph_left_half(data, value, scale)
        img.paste(glyph, (index * 8 * scale, 0))
    return img


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--offset", type=parse_int, action="append", required=True)
    parser.add_argument("--max-len", type=int, default=16)
    parser.add_argument("--scale", type=int, default=4)
    args = parser.parse_args()

    data = args.rom.read_bytes()
    rows: list[tuple[int, list[int], Image.Image]] = []
    for offset in args.offset:
        values = read_byte_string(data, offset, args.max_len)
        rows.append((offset, values, render_string(data, values, args.scale)))

    label_width = 120
    gap = 8
    width = max(label_width + row[2].width for row in rows)
    height = max(1, len(rows)) * (16 * args.scale + gap) - gap
    sheet = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for offset, values, image in rows:
        draw.text((4, y + 4), f"0x{offset:06X} " + " ".join(f"{v:02X}" for v in values), fill=(0, 0, 0))
        sheet.paste(image, (label_width, y))
        y += 16 * args.scale + gap

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
