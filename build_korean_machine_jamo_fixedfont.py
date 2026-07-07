#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_korean_machine_jamo as base


OUT = Path("Langrisser II (Korean Machine Jamo FixedFont).md")
FIXED_FONT_BASE = 0x6000
FIXED_TILE_SIZE = 0x20


def map_fixed_tile(code: int) -> int:
    """Match the game's ASCII-to-dialogue-tile mapping at 0x0A874A."""
    code &= 0xFF
    specials = {
        0x0E: 0xCD,
        0x21: 0x2C,
        0x2F: 0x3E,
        0x25: 0x3B,
        0x2C: 0xD0,
        0x3A: 0xD1,
        0x3B: 0xD2,
        0x27: 0xD5,
        0x22: 0xD3,
        0x2E: 0xD6,
        0x23: 0xD7,
        0x2A: 0xD8,
        0x5B: 0xD9,
        0x5D: 0xD4,
    }
    if code in specials:
        return specials[code]
    if 0xA9 <= code <= 0xAF:
        return code
    if code >= 0x60:
        code = (code + 0x50) & 0xFF
    if code < 0x20:
        code = (code + 0x60) & 0xFF
    return code


def encode_fixed_tile(pixels: list[list[int]]) -> bytes:
    out = bytearray()
    for y in range(8):
        row = pixels[y]
        for x in range(0, 8, 2):
            out.append(((row[x] & 0x0F) << 4) | (row[x + 1] & 0x0F))
    return bytes(out)


def render_fixed_glyph(text: str, font: ImageFont.FreeTypeFont) -> bytes:
    scale = 8
    canvas = Image.new("L", (10 * scale, 10 * scale), 0)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (canvas.width - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (canvas.height - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), text, fill=255, font=font)

    bbox = canvas.getbbox()
    if bbox is None:
        return bytes([0x11] * FIXED_TILE_SIZE)
    crop = canvas.crop(bbox)
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
    target_h = 8
    target_w = max(4, min(8, round(crop.width * target_h / crop.height)))
    small = crop.resize((target_w, target_h), resample)

    pixels: list[list[int]] = []
    xoff = (8 - target_w) // 2
    for yy in range(8):
        row = [1] * 8
        for xx in range(target_w):
            v = small.getpixel((xx, yy))
            if v >= 185:
                row[xoff + xx] = 3
            elif v >= 75:
                row[xoff + xx] = 2
            elif v >= 25:
                row[xoff + xx] = 5
        pixels.append(row)
    return encode_fixed_tile(pixels)


def patch_fixed_dialogue_font(
    rom: bytearray, code_map: dict[str, int], font: ImageFont.FreeTypeFont
) -> list[tuple[str, int, int]]:
    mapped: list[tuple[str, int, int]] = []
    used_tiles: dict[int, str] = {}
    for ch, code in code_map.items():
        tile = map_fixed_tile(code)
        if tile in used_tiles:
            raise ValueError(f"fixed tile collision: {ch!r} and {used_tiles[tile]!r} -> 0x{tile:02x}")
        used_tiles[tile] = ch
        glyph = render_fixed_glyph(ch, font)
        off = FIXED_FONT_BASE + tile * FIXED_TILE_SIZE
        rom[off : off + FIXED_TILE_SIZE] = glyph
        mapped.append((ch, code, tile))
    return mapped


def main() -> int:
    if not base.FONT_PATH.exists():
        raise FileNotFoundError(base.FONT_PATH)

    records = json.loads(base.TRANS.read_text(encoding="utf-8"))
    rom = bytearray(base.SRC.read_bytes())

    chars = base.collect_jamo(records)
    code_map = base.assign_codes(chars)
    font_vwf = ImageFont.truetype(str(base.FONT_PATH), 16 * 8)
    font_fixed = ImageFont.truetype(str(base.FONT_PATH), 8 * 8)

    copy_size = base.font_copy_size(rom)
    rom[base.RELOCATED_BITMAP_TABLE : base.RELOCATED_BITMAP_TABLE + copy_size] = rom[
        base.ORIGINAL_BITMAP_TABLE : base.ORIGINAL_BITMAP_TABLE + copy_size
    ]
    rom[base.BITMAP_BASE_PATCH : base.BITMAP_BASE_PATCH + 4] = base.RELOCATED_BITMAP_TABLE.to_bytes(4, "big")
    cursor = base.RELOCATED_BITMAP_TABLE + copy_size
    for ch, code in code_map.items():
        glyph = base.render_glyph(ch, font_vwf)
        entry = base.WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        rom[cursor : cursor + len(glyph)] = glyph
        cursor += len(glyph)
        if cursor & 1:
            cursor += 1

    fixed_mapped = patch_fixed_dialogue_font(rom, code_map, font_fixed)

    old_to_new: dict[int, int] = {}
    script_cursor = base.SCRIPT_BASE
    rom[base.SCRIPT_BASE : base.SCRIPT_LIMIT] = b"\xff" * (base.SCRIPT_LIMIT - base.SCRIPT_BASE)
    for record in records:
        old = int(str(record["address"]), 16)
        prefix = bytes.fromhex(str(record["prefix"]))
        encoded = prefix + base.encode_text(str(record["translation"]), code_map) + b"\xff\xff"
        old_to_new[old] = script_cursor
        rom[script_cursor : script_cursor + len(encoded)] = encoded
        script_cursor += len(encoded)
        if script_cursor & 1:
            script_cursor += 1

    patch_ranges = [(0x88000, 0x96000), (base.SCRIPT_LIMIT, 0x1F0000)]
    for old, new in old_to_new.items():
        old_b = old.to_bytes(4, "big")
        new_b = new.to_bytes(4, "big")
        for range_start, range_end in patch_ranges:
            start = range_start
            while True:
                hit = rom.find(old_b, start, range_end)
                if hit < 0:
                    break
                rom[hit : hit + 4] = new_b
                start = hit + 4

    opening_cursor = script_cursor
    for name, parts in base.OPENING_PARTS.items():
        encoded = base.encode_opening_part(parts, code_map)
        rom[base.OPENING_POINTER_PATCHES[name] : base.OPENING_POINTER_PATCHES[name] + 4] = opening_cursor.to_bytes(
            4, "big"
        )
        rom[opening_cursor : opening_cursor + len(encoded)] = encoded
        opening_cursor += len(encoded)
        if opening_cursor & 1:
            opening_cursor += 1

    if opening_cursor >= base.SCRIPT_LIMIT:
        raise ValueError(f"script overflow: 0x{opening_cursor:x} >= 0x{base.SCRIPT_LIMIT:x}")

    base.update_checksum_and_header(rom)
    OUT.write_bytes(rom)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    print(f"jamo glyphs: {len(chars)}")
    print(f"fixed dialogue tiles patched: {len(fixed_mapped)}")
    print(f"font relocated: 0x{base.RELOCATED_BITMAP_TABLE:x}-0x{cursor:x}")
    print(f"script: 0x{base.SCRIPT_BASE:x}-0x{script_cursor:x}")
    print(f"opening: 0x{script_cursor:x}-0x{opening_cursor:x}")
    print("tile map: " + " ".join(f"{ch}:0x{code:02x}->0x{tile:02x}" for ch, code, tile in fixed_mapped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
