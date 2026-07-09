#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


BYTE_UI_FONT_RESOURCE_TABLE = 0x0B0000
BYTE_UI_FONT_RESOURCE_INDEX = 1


def parse_int(text: str) -> int:
    return int(text, 0)


def be16(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def be32(data: bytes, offset: int) -> int:
    return (
        (data[offset] << 24)
        | (data[offset + 1] << 16)
        | (data[offset + 2] << 8)
        | data[offset + 3]
    )


def decompress_9dfe(data: bytes, offset: int) -> bytes:
    remaining = be16(data, offset)
    pos = offset + 2
    ring = bytearray([0x20] * 0x1000)
    ring_pos = 0x0FEE
    out = bytearray()
    while remaining > 0:
        flags = data[pos]
        pos += 1
        for _ in range(8):
            if flags & 1:
                value = data[pos]
                pos += 1
                ring[ring_pos] = value
                ring_pos = (ring_pos + 1) & 0x0FFF
                out.append(value)
                remaining -= 1
            else:
                lo = data[pos]
                hi = data[pos + 1]
                pos += 2
                source = lo | ((hi << 4) & 0x0F00)
                count = (hi & 0x0F) + 3
                for _ in range(count):
                    value = ring[source]
                    source = (source + 1) & 0x0FFF
                    ring[ring_pos] = value
                    ring_pos = (ring_pos + 1) & 0x0FFF
                    out.append(value)
                    remaining -= 1
                    if remaining <= 0:
                        break
            flags >>= 1
            if remaining <= 0:
                break
    return bytes(out)


def load_byte_ui_tiles(data: bytes) -> bytes:
    entry = BYTE_UI_FONT_RESOURCE_TABLE + BYTE_UI_FONT_RESOURCE_INDEX * 4
    resource_offset = be32(data, entry) & 0x00FFFFFF
    if data[resource_offset] != 0x03:
        raise ValueError(f"unsupported byte UI font resource type at 0x{resource_offset:06X}")
    return decompress_9dfe(data, resource_offset + 1)


def render_glyph_tile(font_tiles: bytes, code: int, scale: int) -> Image.Image:
    offset = code * 32
    img = Image.new("RGB", (8 * scale, 8 * scale), "white")
    palette = {
        0x0: (0, 0, 0),
        0x1: (0, 0, 88),
        0x2: (160, 160, 160),
        0x3: (255, 255, 255),
        0x4: (255, 96, 96),
        0x5: (255, 255, 96),
        0x9: (96, 96, 96),
        0xB: (120, 120, 255),
        0xC: (255, 120, 120),
        0xD: (120, 255, 120),
        0xF: (255, 255, 255),
    }
    for y in range(8):
        for byte_x in range(4):
            value = font_tiles[offset + y * 4 + byte_x]
            for nibble_x, color_index in enumerate(((value >> 4) & 0x0F, value & 0x0F)):
                x = byte_x * 2 + nibble_x
                color = palette.get(color_index, (255, 0, 255))
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


def render_string(font_tiles: bytes, values: list[int], scale: int) -> Image.Image:
    width = max(1, len(values)) * 8 * scale
    img = Image.new("RGB", (width, 8 * scale), (0, 0, 88))
    for index, value in enumerate(values):
        glyph = render_glyph_tile(font_tiles, value, scale)
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
    font_tiles = load_byte_ui_tiles(data)
    rows: list[tuple[int, list[int], Image.Image]] = []
    for offset in args.offset:
        values = read_byte_string(data, offset, args.max_len)
        rows.append((offset, values, render_string(font_tiles, values, args.scale)))

    label_width = 120
    gap = 8
    width = max(label_width + row[2].width for row in rows)
    height = max(1, len(rows)) * (8 * args.scale + gap) - gap
    sheet = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for offset, values, image in rows:
        draw.text((4, y + 4), f"0x{offset:06X} " + " ".join(f"{v:02X}" for v in values), fill=(0, 0, 0))
        sheet.paste(image, (label_width, y))
        y += 8 * args.scale + gap

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
