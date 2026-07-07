#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SRC = Path("Langrisser II (English).md")
OUT = Path("Langrisser II (Korean WIP).md")
FONT_PATH = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")

OPENING_WIDTH_TABLE = 0xA952C
ORIGINAL_OPENING_BITMAP_TABLE = 0xA95EC
RELOCATED_OPENING_BITMAP_TABLE = 0x173800
OPENING_TEXT_SPACE = 0x177000

# move.l #$000a95ec, $ff0020.l in the opening font setup routine.
OPENING_BITMAP_BASE_PATCH = 0xAD5F8

# Long-immediate addresses in MIJET's opening code.
OPENING_POINTER_PATCHES = {
    "part1": 0xADBAE,
    "part2": 0xADBC6,
    "part3": 0xADBE2,
}

CONTROL = {
    "P": bytes([0x10, 0x02]),
    "R": bytes([0x10, 0x52]),
    "I": bytes([0x04]),
    "W": bytes([0x06]),
    "END": bytes([0x0F, 0xFF]),
    "BREAK": bytes([0xFF]),
}

OPENING_PARTS = {
    "part1": [
        "P",
        "후후후...",
        "W",
        "R",
        "알하자드...",
        "I",
        "전설의 마검...",
        "END",
    ],
    "part2": [
        "P",
        "이것이 바로",
        "BREAK",
        "내가 갈망하던 무한한 힘...",
    ],
    "part3": [
        bytes([0x08, 0x11, 0x15, 0x12]),
        "P",
        "검이여,",
        "I",
        "내게 힘을 빌려라!",
        "W",
        "대륙을",
        "R",
        "아니 세계를,",
        "I",
        "모두 내 것으로!!",
        "END",
    ],
}


def encode_opening_glyph(pixels: list[list[int]], width: int) -> bytes:
    row_bytes = (width + 1) // 2
    out = bytearray([width])
    for y in range(16):
        row = pixels[y]
        for x in range(0, row_bytes * 2, 2):
            left = row[x] if x < width else 1
            right = row[x + 1] if x + 1 < width else 1
            out.append(((left & 0x0F) << 4) | (right & 0x0F))
    return bytes(out)


def render_opening_glyph(text: str, font: ImageFont.FreeTypeFont) -> bytes:
    scale = 8
    canvas = Image.new("L", (18 * scale, 18 * scale), 0)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (canvas.width - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (canvas.height - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), text, fill=255, font=font)

    bbox = canvas.getbbox()
    if bbox is None:
        return bytes([4] + [0x11] * 16 * 2)
    crop = canvas.crop(bbox)
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
    target_h = 16
    target_w = max(8, min(14, round(crop.width * target_h / crop.height)))
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
    return encode_opening_glyph(pixels, target_w)


def collect_hangul() -> list[str]:
    seen: set[str] = set()
    chars: list[str] = []
    for parts in OPENING_PARTS.values():
        for part in parts:
            if not isinstance(part, str) or part in CONTROL:
                continue
            for ch in part:
                if "가" <= ch <= "힣" and ch not in seen:
                    seen.add(ch)
                    chars.append(ch)
    return chars


def assign_codes(chars: list[str]) -> dict[str, int]:
    reserved = set(b" .,!?-'\"/:|")
    pool = [c for c in range(0x21, 0x7F) if c not in reserved]
    if len(chars) > len(pool):
        raise ValueError(f"Need {len(chars)} glyph slots, only {len(pool)} available")
    return {ch: pool[i] for i, ch in enumerate(chars)}


def encode_text(parts: list[str | bytes], code_map: dict[str, int]) -> bytes:
    out = bytearray()
    for part in parts:
        if isinstance(part, bytes):
            out.extend(part)
        elif part in CONTROL:
            out.extend(CONTROL[part])
        else:
            for ch in part:
                if "가" <= ch <= "힣":
                    out.append(code_map[ch])
                else:
                    out.extend(ch.encode("ascii"))
    return bytes(out)


def update_checksum(rom: bytearray) -> None:
    checksum = 0
    for i in range(0x200, len(rom), 2):
        checksum = (checksum + ((rom[i] << 8) | rom[i + 1])) & 0xFFFF
    rom[0x18E:0x190] = checksum.to_bytes(2, "big")


def opening_font_copy_size(rom: bytes) -> int:
    end = 0
    for code in range(0x20, 0x80):
        entry = OPENING_WIDTH_TABLE + (code - 0x20) * 2
        off = int.from_bytes(rom[entry : entry + 2], "big")
        width = rom[ORIGINAL_OPENING_BITMAP_TABLE + off]
        size = 1 + ((width + 1) // 2) * 16
        end = max(end, off + size)
    return (end + 1) & ~1


def main() -> int:
    if not FONT_PATH.exists():
        raise FileNotFoundError(FONT_PATH)

    rom = bytearray(SRC.read_bytes())
    font = ImageFont.truetype(str(FONT_PATH), 16 * 8)
    chars = collect_hangul()
    code_map = assign_codes(chars)

    copy_size = opening_font_copy_size(rom)
    rom[RELOCATED_OPENING_BITMAP_TABLE : RELOCATED_OPENING_BITMAP_TABLE + copy_size] = rom[
        ORIGINAL_OPENING_BITMAP_TABLE : ORIGINAL_OPENING_BITMAP_TABLE + copy_size
    ]
    rom[OPENING_BITMAP_BASE_PATCH : OPENING_BITMAP_BASE_PATCH + 4] = RELOCATED_OPENING_BITMAP_TABLE.to_bytes(4, "big")

    cursor = RELOCATED_OPENING_BITMAP_TABLE + copy_size
    for ch, code in code_map.items():
        glyph = render_opening_glyph(ch, font)
        table_entry = OPENING_WIDTH_TABLE + (code - 0x20) * 2
        rom[table_entry : table_entry + 2] = (cursor - RELOCATED_OPENING_BITMAP_TABLE).to_bytes(2, "big")
        rom[cursor : cursor + len(glyph)] = glyph
        cursor += len(glyph)
        if cursor & 1:
            cursor += 1

    text_cursor = OPENING_TEXT_SPACE
    for name, parts in OPENING_PARTS.items():
        encoded = encode_text(parts, code_map)
        rom[OPENING_POINTER_PATCHES[name] : OPENING_POINTER_PATCHES[name] + 4] = text_cursor.to_bytes(4, "big")
        rom[text_cursor : text_cursor + len(encoded)] = encoded
        text_cursor += len(encoded)
        if text_cursor & 1:
            text_cursor += 1

    if text_cursor >= 0x180000 or cursor >= OPENING_TEXT_SPACE:
        raise ValueError("Opening text/glyph data overflowed free space")

    update_checksum(rom)
    OUT.write_bytes(rom)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    print(f"opening hangul glyphs: {len(chars)}")
    print(f"relocated font: 0x{RELOCATED_OPENING_BITMAP_TABLE:x}-0x{cursor:x}")
    print(f"opening text: 0x{OPENING_TEXT_SPACE:x}-0x{text_cursor:x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
