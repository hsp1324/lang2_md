#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

import build_korean_machine_jamo as base
import build_korean_machine_jamo_fixedfont as fixedfont
import build_korean_wip as opening_wip


OUT = Path("Langrisser II (Korean Hybrid WIP).md")


def collect_opening_hangul() -> list[str]:
    seen: set[str] = set()
    chars: list[str] = []
    for parts in opening_wip.OPENING_PARTS.values():
        for part in parts:
            if not isinstance(part, str) or part in opening_wip.CONTROL:
                continue
            for ch in part:
                if "가" <= ch <= "힣" and ch not in seen:
                    seen.add(ch)
                    chars.append(ch)
    return chars


def assign_opening_codes(jamo_code_map: dict[str, int], opening_chars: list[str]) -> dict[str, int]:
    # Opening text needs only the punctuation below; other ASCII slots can hold complete Hangul.
    reserved = set(b" .,!?")
    used = set(jamo_code_map.values()) | reserved
    pool = [code for code in range(0x21, 0x7F) if code not in used]
    if len(opening_chars) > len(pool):
        raise ValueError(f"Need {len(opening_chars)} opening slots, only {len(pool)} available")
    return {ch: pool[idx] for idx, ch in enumerate(opening_chars)}


def encode_hybrid_opening(parts: list[str | bytes], opening_code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for part in parts:
        if isinstance(part, bytes):
            out.extend(part)
        elif part in opening_wip.CONTROL:
            out.extend(opening_wip.CONTROL[part])
        else:
            for ch in part:
                if "가" <= ch <= "힣":
                    out.append(opening_code_map[ch])
                else:
                    out.extend(ch.encode("ascii"))
    return bytes(out)


def main() -> int:
    if not base.FONT_PATH.exists():
        raise FileNotFoundError(base.FONT_PATH)

    records = json.loads(base.TRANS.read_text(encoding="utf-8"))
    rom = bytearray(base.SRC.read_bytes())

    jamo_chars = base.collect_jamo(records)
    jamo_code_map = base.assign_codes(jamo_chars)
    opening_chars = collect_opening_hangul()
    opening_code_map = assign_opening_codes(jamo_code_map, opening_chars)

    font_vwf = ImageFont.truetype(str(base.FONT_PATH), 16 * 8)
    font_fixed = ImageFont.truetype(str(base.FONT_PATH), 8 * 8)

    copy_size = base.font_copy_size(rom)
    rom[base.RELOCATED_BITMAP_TABLE : base.RELOCATED_BITMAP_TABLE + copy_size] = rom[
        base.ORIGINAL_BITMAP_TABLE : base.ORIGINAL_BITMAP_TABLE + copy_size
    ]
    rom[base.BITMAP_BASE_PATCH : base.BITMAP_BASE_PATCH + 4] = base.RELOCATED_BITMAP_TABLE.to_bytes(4, "big")
    cursor = base.RELOCATED_BITMAP_TABLE + copy_size

    for ch, code in jamo_code_map.items():
        glyph = base.render_glyph(ch, font_vwf)
        entry = base.WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        rom[cursor : cursor + len(glyph)] = glyph
        cursor += len(glyph)
        if cursor & 1:
            cursor += 1

    for ch, code in opening_code_map.items():
        glyph = opening_wip.render_opening_glyph(ch, font_vwf)
        entry = base.WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (cursor - base.RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        rom[cursor : cursor + len(glyph)] = glyph
        cursor += len(glyph)
        if cursor & 1:
            cursor += 1

    fixed_mapped = fixedfont.patch_fixed_dialogue_font(rom, jamo_code_map, font_fixed)

    old_to_new: dict[int, int] = {}
    script_cursor = base.SCRIPT_BASE
    rom[base.SCRIPT_BASE : base.SCRIPT_LIMIT] = b"\xff" * (base.SCRIPT_LIMIT - base.SCRIPT_BASE)
    for record in records:
        old = int(str(record["address"]), 16)
        prefix = bytes.fromhex(str(record["prefix"]))
        encoded = prefix + base.encode_text(str(record["translation"]), jamo_code_map) + b"\xff\xff"
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
    for name, parts in opening_wip.OPENING_PARTS.items():
        encoded = encode_hybrid_opening(parts, opening_code_map)
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
    print(f"main jamo glyphs: {len(jamo_chars)}")
    print(f"opening complete Hangul glyphs: {len(opening_chars)}")
    print(f"fixed dialogue tiles patched: {len(fixed_mapped)}")
    print(f"font relocated: 0x{base.RELOCATED_BITMAP_TABLE:x}-0x{cursor:x}")
    print(f"script: 0x{base.SCRIPT_BASE:x}-0x{script_cursor:x}")
    print(f"opening: 0x{script_cursor:x}-0x{opening_cursor:x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
