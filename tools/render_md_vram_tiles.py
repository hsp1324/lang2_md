#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def parse_int(text: str) -> int:
    return int(text, 0)


def render_tile(data: bytes, offset: int, scale: int) -> Image.Image:
    palette = [
        (255, 255, 255),
        (210, 210, 210),
        (150, 150, 150),
        (90, 90, 90),
        (0, 0, 0),
        (40, 40, 120),
        (120, 40, 40),
        (40, 120, 40),
    ]
    img = Image.new("RGB", (8 * scale, 8 * scale), palette[0])
    for y in range(8):
        row = data[offset + y * 4 : offset + y * 4 + 4]
        if len(row) < 4:
            break
        for x in range(8):
            shift = 7 - x
            value = (
                (((row[0] >> shift) & 1) << 3)
                | (((row[1] >> shift) & 1) << 2)
                | (((row[2] >> shift) & 1) << 1)
                | ((row[3] >> shift) & 1)
            )
            color = palette[min(value, len(palette) - 1)]
            img.paste(color, (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale))
    return img


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--offset", type=parse_int, default=0)
    parser.add_argument("--count", type=int, default=0x800)
    parser.add_argument("--cols", type=int, default=32)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--label", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    data = args.input.read_bytes()
    rows = (args.count + args.cols - 1) // args.cols
    label_h = 8 if args.label else 0
    tile_w = 8 * args.scale
    tile_h = 8 * args.scale + label_h
    img = Image.new("RGB", (args.cols * tile_w, rows * tile_h), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    for index in range(args.count):
        offset = args.offset + index * 32
        if offset + 32 > len(data):
            break
        x = (index % args.cols) * tile_w
        y = (index // args.cols) * tile_h
        img.paste(render_tile(data, offset, args.scale), (x, y + label_h))
        if args.label:
            draw.text((x, y), f"{index:03X}", fill=(255, 0, 0))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
