#!/usr/bin/env python3
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SRC = Path("Langrisser II (English).md")
OUT = Path("Langrisser II (Korean Probe).md")
FONT_PATHS = [
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]

# Opening text font tables used by MIJET's added intro/ending text renderer.
OPENING_WIDTH_TABLE = 0xA952C
OPENING_BITMAP_TABLE = 0xA95EC
OPENING_FREE_SPACE = 0xAF800

PROBE_GLYPHS = {
    "H": "한",
    "e": "글",
    "h": "테",
    "r": "스",
    "s": "트",
}


def find_font() -> Path:
    for path in FONT_PATHS:
        if path.exists():
            return path
    raise FileNotFoundError("No usable font found")


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


def render_opening_glyph(text: str, font_path: Path) -> bytes:
    # MIJET's opening renderer uses 16-pixel-high, variable-width 4bpp glyphs.
    scale = 8
    canvas = Image.new("L", (18 * scale, 18 * scale), 0)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(font_path), 16 * scale)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (canvas.width - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (canvas.height - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), text, fill=255, font=font)

    bbox = canvas.getbbox()
    if bbox is None:
        return bytes([4] + [0x11] * 16 * 2)
    crop = canvas.crop(bbox)
    target_h = 16
    target_w = max(8, min(14, round(crop.width * target_h / crop.height)))
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
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


def update_checksum(rom: bytearray) -> None:
    checksum = 0
    for i in range(0x200, len(rom), 2):
        word = (rom[i] << 8) | rom[i + 1]
        checksum = (checksum + word) & 0xFFFF
    rom[0x18E:0x190] = checksum.to_bytes(2, "big")


def main() -> int:
    rom = bytearray(SRC.read_bytes())
    font_path = find_font()

    cursor = OPENING_FREE_SPACE
    for code, glyph in PROBE_GLYPHS.items():
        glyph_data = render_opening_glyph(glyph, font_path)
        table_entry = OPENING_WIDTH_TABLE + (ord(code) - 0x20) * 2
        rom[table_entry : table_entry + 2] = (cursor - OPENING_BITMAP_TABLE).to_bytes(2, "big")
        rom[cursor : cursor + len(glyph_data)] = glyph_data
        cursor += len(glyph_data)
        if cursor & 1:
            cursor += 1

    # Original bytes at 0xADC98 start after control bytes: "Heh heh heh..."
    # Keep the timing/control byte before it and replace the visible text.
    phrase = b"He hrs..."  # H/e/h/r/s are patched to 한/글/테/스/트.
    rom[0xADC98 : 0xADC98 + len(phrase)] = phrase

    update_checksum(rom)
    OUT.write_bytes(rom)
    print(f"wrote {OUT} ({len(rom)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
