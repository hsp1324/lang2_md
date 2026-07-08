#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SRC = Path("Langrisser II (English).md")
TRANS = Path("script_extract/korean_records_google.json")
OUT = Path("Langrisser II (Korean Machine Jamo).md")
FONT_PATH = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")

ORIGINAL_SIZE = 0x200000
EXPANDED_SIZE = ORIGINAL_SIZE
SCRIPT_BASE = 0x138200
SCRIPT_LIMIT = 0x180000

WIDTH_TABLE = 0xA952C
ORIGINAL_BITMAP_TABLE = 0xA95EC
RELOCATED_BITMAP_TABLE = 0x32000
BITMAP_BASE_PATCH = 0xAD5F8

OPENING_POINTER_PATCHES = {
    "part1": 0xADBAE,
    "part2": 0xADBC6,
    "part3": 0xADBE2,
}

OPENING_PARTS = {
    "part1": [b"\x10\x02", "후후후...", b"\x06\x10\x52", "알하자드...", b"\x04", "전설의 마검...", b"\x0f\xff"],
    "part2": [b"\x10\x02", "이것이 바로", b"\xff", "내가 갈망하던 무한한 힘..."],
    "part3": [
        b"\x08\x11\x15\x12\x10\x02",
        "검이여,",
        b"\x04",
        "내게 힘을 빌려라!",
        b"\x06",
        "대륙을",
        b"\x10\x52",
        "아니 세계를,",
        b"\x04",
        "모두 내 것으로!!",
        b"\x0f\xff",
    ],
}

CHOSUNG = {
    "\u1100": "ㄱ", "\u1101": "ㄲ", "\u1102": "ㄴ", "\u1103": "ㄷ", "\u1104": "ㄸ",
    "\u1105": "ㄹ", "\u1106": "ㅁ", "\u1107": "ㅂ", "\u1108": "ㅃ", "\u1109": "ㅅ",
    "\u110a": "ㅆ", "\u110b": "ㅇ", "\u110c": "ㅈ", "\u110d": "ㅉ", "\u110e": "ㅊ",
    "\u110f": "ㅋ", "\u1110": "ㅌ", "\u1111": "ㅍ", "\u1112": "ㅎ",
}
JUNGSUNG = {
    "\u1161": "ㅏ", "\u1162": "ㅐ", "\u1163": "ㅑ", "\u1164": "ㅒ", "\u1165": "ㅓ",
    "\u1166": "ㅔ", "\u1167": "ㅕ", "\u1168": "ㅖ", "\u1169": "ㅗ", "\u116a": "ㅘ",
    "\u116b": "ㅙ", "\u116c": "ㅚ", "\u116d": "ㅛ", "\u116e": "ㅜ", "\u116f": "ㅝ",
    "\u1170": "ㅞ", "\u1171": "ㅟ", "\u1172": "ㅠ", "\u1173": "ㅡ", "\u1174": "ㅢ",
    "\u1175": "ㅣ",
}
JONGSUNG = {
    "\u11a8": "ㄱ", "\u11a9": "ㄲ", "\u11aa": "ㄳ", "\u11ab": "ㄴ", "\u11ac": "ㄵ",
    "\u11ad": "ㄶ", "\u11ae": "ㄷ", "\u11af": "ㄹ", "\u11b0": "ㄺ", "\u11b1": "ㄻ",
    "\u11b2": "ㄼ", "\u11b3": "ㄽ", "\u11b4": "ㄾ", "\u11b5": "ㄿ", "\u11b6": "ㅀ",
    "\u11b7": "ㅁ", "\u11b8": "ㅂ", "\u11b9": "ㅄ", "\u11ba": "ㅅ", "\u11bb": "ㅆ",
    "\u11bc": "ㅇ", "\u11bd": "ㅈ", "\u11be": "ㅊ", "\u11bf": "ㅋ", "\u11c0": "ㅌ",
    "\u11c1": "ㅍ", "\u11c2": "ㅎ",
}
JAMO_MAP = {**CHOSUNG, **JUNGSUNG, **JONGSUNG}


def to_compat_jamo(text: str) -> str:
    out: list[str] = []
    for ch in unicodedata.normalize("NFKD", text):
        out.append(JAMO_MAP.get(ch, ch))
    return "".join(out)


def collect_jamo(records: list[dict[str, object]]) -> list[str]:
    seen: set[str] = set()
    chars: list[str] = []
    sources = [str(r["translation"]) for r in records]
    for parts in OPENING_PARTS.values():
        for part in parts:
            if isinstance(part, str):
                sources.append(part)
    for text in sources:
        for ch in to_compat_jamo(text):
            if "\u3130" <= ch <= "\u318f" and ch not in seen:
                seen.add(ch)
                chars.append(ch)
    return chars


def assign_codes(chars: list[str]) -> dict[str, int]:
    reserved = set(b" .,!?-'\"/:|0123456789")
    pool = [c for c in range(0x21, 0x7F) if c not in reserved]
    if len(chars) > len(pool):
        raise ValueError(f"Need {len(chars)} jamo slots, only {len(pool)} available")
    return {ch: pool[i] for i, ch in enumerate(chars)}


def encode_glyph(pixels: list[list[int]], width: int) -> bytes:
    row_bytes = (width + 1) // 2
    out = bytearray([width])
    for y in range(16):
        row = pixels[y]
        for x in range(0, row_bytes * 2, 2):
            left = row[x] if x < width else 1
            right = row[x + 1] if x + 1 < width else 1
            out.append(((left & 0x0F) << 4) | (right & 0x0F))
    return bytes(out)


def render_glyph(text: str, font: ImageFont.FreeTypeFont) -> bytes:
    scale = 8
    canvas = Image.new("L", (16 * scale, 18 * scale), 0)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (canvas.width - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (canvas.height - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), text, fill=255, font=font)
    bbox = canvas.getbbox()
    if bbox is None:
        return bytes([4] + [0x11] * 32)
    crop = canvas.crop(bbox)
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
    target_h = 16
    target_w = max(5, min(10, round(crop.width * target_h / crop.height)))
    small = crop.resize((target_w, target_h), resample)
    pixels: list[list[int]] = []
    for yy in range(16):
        row: list[int] = []
        for xx in range(target_w):
            v = small.getpixel((xx, yy))
            if v >= 190:
                row.append(0xE)
            elif v >= 100:
                row.append(0xD)
            elif v >= 35:
                row.append(0xA)
            else:
                row.append(1)
        pixels.append(row)
    return encode_glyph(pixels, target_w)


def font_copy_size(rom: bytes) -> int:
    end = 0
    for code in range(0x20, 0x80):
        entry = WIDTH_TABLE + (code - 0x20) * 2
        off = int.from_bytes(rom[entry : entry + 2], "big")
        width = rom[ORIGINAL_BITMAP_TABLE + off]
        size = 1 + ((width + 1) // 2) * 16
        end = max(end, off + size)
    return (end + 1) & ~1


def wrap_units(units: list[int], max_units: int = 32) -> list[int]:
    lines: list[list[int]] = [[]]
    last_space = -1
    for unit in units:
        if unit == 0xFE:
            lines.append([])
            last_space = -1
            continue
        lines[-1].append(unit)
        if unit == 0x20:
            last_space = len(lines[-1]) - 1
        if len(lines[-1]) > max_units:
            if last_space > 0:
                overflow = lines[-1][last_space + 1 :]
                lines[-1] = lines[-1][:last_space]
                lines.append(overflow)
            else:
                overflow = lines[-1][max_units:]
                lines[-1] = lines[-1][:max_units]
                lines.append(overflow)
            last_space = -1
    out: list[int] = []
    for idx, line in enumerate(lines):
        if idx:
            out.append(0xFE)
        out.extend(line)
    return out


def encode_text(text: str, code_map: dict[str, int]) -> bytes:
    text = text.replace(" / ", "\n").replace("/", "\n")
    units: list[int] = []
    for ch in to_compat_jamo(text):
        if ch == "\n":
            units.append(0xFE)
        elif "\u3130" <= ch <= "\u318f":
            units.append(code_map[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            units.append(ord(ch))
        else:
            units.append(ord("?"))
    return bytes(wrap_units(units))


def encode_opening_part(parts: list[str | bytes], code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for part in parts:
        if isinstance(part, bytes):
            out.extend(part)
        else:
            out.extend(encode_text(part, code_map))
    return bytes(out)


def update_checksum_and_header(rom: bytearray) -> None:
    rom[0x1A0:0x1A4] = (0).to_bytes(4, "big")
    rom[0x1A4:0x1A8] = (len(rom) - 1).to_bytes(4, "big")
    checksum = 0
    for i in range(0x200, len(rom), 2):
        checksum = (checksum + ((rom[i] << 8) | rom[i + 1])) & 0xFFFF
    rom[0x18E:0x190] = checksum.to_bytes(2, "big")


def main() -> int:
    records = json.loads(TRANS.read_text(encoding="utf-8"))
    rom = bytearray(SRC.read_bytes())

    chars = collect_jamo(records)
    code_map = assign_codes(chars)
    font = ImageFont.truetype(str(FONT_PATH), 16 * 8)

    copy_size = font_copy_size(rom)
    rom[RELOCATED_BITMAP_TABLE : RELOCATED_BITMAP_TABLE + copy_size] = rom[
        ORIGINAL_BITMAP_TABLE : ORIGINAL_BITMAP_TABLE + copy_size
    ]
    rom[BITMAP_BASE_PATCH : BITMAP_BASE_PATCH + 4] = RELOCATED_BITMAP_TABLE.to_bytes(4, "big")
    cursor = RELOCATED_BITMAP_TABLE + copy_size
    for ch, code in code_map.items():
        glyph = render_glyph(ch, font)
        entry = WIDTH_TABLE + (code - 0x20) * 2
        rom[entry : entry + 2] = (cursor - RELOCATED_BITMAP_TABLE).to_bytes(2, "big")
        rom[cursor : cursor + len(glyph)] = glyph
        cursor += len(glyph)
        if cursor & 1:
            cursor += 1

    old_to_new: dict[int, int] = {}
    script_cursor = SCRIPT_BASE
    rom[SCRIPT_BASE:SCRIPT_LIMIT] = b"\xff" * (SCRIPT_LIMIT - SCRIPT_BASE)
    for record in records:
        old = int(str(record["address"]), 16)
        prefix = bytes.fromhex(str(record["prefix"]))
        encoded = prefix + encode_text(str(record["translation"]), code_map) + b"\xff\xff"
        old_to_new[old] = script_cursor
        rom[script_cursor : script_cursor + len(encoded)] = encoded
        script_cursor += len(encoded)
        if script_cursor & 1:
            script_cursor += 1

    patch_ranges = [(0x88000, 0x96000), (SCRIPT_LIMIT, 0x1F0000)]
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
    for name, parts in OPENING_PARTS.items():
        encoded = encode_opening_part(parts, code_map)
        rom[OPENING_POINTER_PATCHES[name] : OPENING_POINTER_PATCHES[name] + 4] = opening_cursor.to_bytes(4, "big")
        rom[opening_cursor : opening_cursor + len(encoded)] = encoded
        opening_cursor += len(encoded)
        if opening_cursor & 1:
            opening_cursor += 1

    if opening_cursor >= SCRIPT_LIMIT:
        raise ValueError(f"script overflow: 0x{opening_cursor:x} >= 0x{SCRIPT_LIMIT:x}")

    update_checksum_and_header(rom)
    OUT.write_bytes(rom)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    print(f"jamo glyphs: {len(chars)}")
    print(f"font relocated: 0x{RELOCATED_BITMAP_TABLE:x}-0x{cursor:x}")
    print(f"script: 0x{SCRIPT_BASE:x}-0x{script_cursor:x}")
    print(f"opening: 0x{script_cursor:x}-0x{opening_cursor:x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
