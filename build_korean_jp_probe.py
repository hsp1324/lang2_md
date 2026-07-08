#!/usr/bin/env python3
from __future__ import annotations

from collections import OrderedDict
import ast
from pathlib import Path
import unicodedata

from PIL import Image, ImageDraw, ImageFont


IN_ROM = Path("Langrisser II (Japan).md")
OUT_ROM = Path("Langrisser II (Korean JP Probe).md")
FONT_PATH = Path("tools/fonts/Galmuri9.ttf")

JP_FONT_BASE = 0x40000
GLYPH_BYTES = 64

CONDITION_POINTER_TABLE = 0x98D7A
CONDITION_GLYPH_LIST_TABLE = 0x986C6
SCENARIO_POINTER_TABLE = 0x9CF7C
SCENARIO_GLYPH_LIST_TABLE = 0x9B2FC

SPACE_GLYPH = 0x0054
CUSTOM_GLYPH_START = 0x0260
CUSTOM_GLYPH_END = 0x03FF
CUSTOM_GLYPH_RESERVED = {0x039C}


def be16(data: bytes | bytearray, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def be32(data: bytes | bytearray, offset: int) -> int:
    return (
        (data[offset] << 24)
        | (data[offset + 1] << 16)
        | (data[offset + 2] << 8)
        | data[offset + 3]
    )


def put16(data: bytearray, offset: int, value: int) -> None:
    data[offset] = (value >> 8) & 0xFF
    data[offset + 1] = value & 0xFF


def read_word_list(data: bytes | bytearray, offset: int) -> list[int]:
    values: list[int] = []
    pos = offset
    while pos + 1 < len(data):
        value = be16(data, pos)
        if value == 0xFFFF:
            break
        values.append(value)
        pos += 2
    return values


def write_word_list(data: bytearray, offset: int, values: list[int], max_words: int) -> None:
    if len(values) + 1 > max_words:
        raise ValueError(f"word list needs {len(values) + 1} words, only {max_words} available")
    for i, value in enumerate(values):
        put16(data, offset + i * 2, value)
    put16(data, offset + len(values) * 2, 0xFFFF)
    for i in range(len(values) + 1, max_words):
        put16(data, offset + i * 2, 0xFFFF)


def write_token_stream(data: bytearray, offset: int, tokens: list[int], max_words: int) -> None:
    if len(tokens) + 1 > max_words:
        raise ValueError(f"token stream needs {len(tokens) + 1} words, only {max_words} available")
    for i, token in enumerate(tokens):
        put16(data, offset + i * 2, token)
    put16(data, offset + len(tokens) * 2, 0xFFFF)
    for i in range(len(tokens) + 1, max_words):
        put16(data, offset + i * 2, 0xFFFF)


def capacity_words(data: bytes | bytearray, table_offset: int, index: int, record_count: int) -> int:
    start = be32(data, table_offset + index * 4)
    if index + 1 < record_count:
        end = be32(data, table_offset + (index + 1) * 4)
    else:
        end = start + 0x400
    return (end - start) // 2


def glyph_list_capacity_words(data: bytes | bytearray, table_offset: int, index: int, record_count: int) -> int:
    start = be32(data, table_offset + index * 4)
    if index + 1 < record_count:
        end = be32(data, table_offset + (index + 1) * 4)
    elif table_offset == SCENARIO_GLYPH_LIST_TABLE:
        end = SCENARIO_POINTER_TABLE
    elif table_offset == CONDITION_GLYPH_LIST_TABLE:
        end = CONDITION_POINTER_TABLE
    else:
        end = start + 0x100
    return (end - start) // 2


def render_hangul_glyph(char: str, font: ImageFont.FreeTypeFont, blank_template: bytes) -> bytes:
    img = Image.new("L", (16, 16), 255)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), char, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (16 - w) // 2 - bbox[0]
    y = (16 - h) // 2 - bbox[1] - 1
    draw.text((x, y), char, font=font, fill=0)

    # Convert one 16x16 bitmap into the Japanese source format consumed by
    # routine 0x2C390: four 8x8 tiles, each row stored as two identical 1bpp
    # planes so the resulting 2bpp pixel is solid dark.
    out = bytearray(blank_template)
    for tile in range(4):
        tx = tile % 2
        ty = tile // 2
        for row in range(8):
            source_row = tile * 8 + row
            high = out[source_row * 2]
            low = out[source_row * 2 + 1]
            for x in range(8):
                px = tx * 8 + x
                py = ty * 8 + row
                dark = img.getpixel((px, py)) < 180
                if dark:
                    high |= 1 << (7 - x)
                    low |= 1 << (7 - x)
            out[source_row * 2] = high
            out[source_row * 2 + 1] = low
    return bytes(out)


def collect_chars(*texts: str) -> list[str]:
    chars: OrderedDict[str, None] = OrderedDict()
    for text in texts:
        for char in text:
            if char in {"\n", " "}:
                continue
            if unicodedata.category(char).startswith("C"):
                continue
            chars[char] = None
    return list(chars)


def install_custom_glyphs(data: bytearray, chars: list[str]) -> dict[str, int]:
    glyph_ids = [
        glyph_id
        for glyph_id in range(CUSTOM_GLYPH_START, CUSTOM_GLYPH_END + 1)
        if glyph_id not in CUSTOM_GLYPH_RESERVED
    ]
    if len(chars) > len(glyph_ids):
        raise ValueError(f"need {len(chars)} custom glyphs, only {len(glyph_ids)} reserved slots")
    font = ImageFont.truetype(str(FONT_PATH), 16)
    blank_offset = JP_FONT_BASE + SPACE_GLYPH * GLYPH_BYTES
    blank_template = bytes(data[blank_offset : blank_offset + GLYPH_BYTES])
    mapping: dict[str, int] = {}
    for i, char in enumerate(chars):
        glyph_id = glyph_ids[i]
        mapping[char] = glyph_id
        offset = JP_FONT_BASE + glyph_id * GLYPH_BYTES
        data[offset : offset + GLYPH_BYTES] = render_hangul_glyph(char, font, blank_template)
    return mapping


def make_record_encoding(text: str, glyph_by_char: dict[str, int]) -> tuple[list[int], list[int]]:
    glyphs: list[int] = [SPACE_GLYPH]
    local_by_glyph = {SPACE_GLYPH: 0}
    tokens: list[int] = []
    for char in text:
        if char == "\n":
            tokens.append(0xFFFE)
            continue
        glyph = SPACE_GLYPH if char == " " else glyph_by_char[char]
        if glyph not in local_by_glyph:
            local_by_glyph[glyph] = len(glyphs)
            glyphs.append(glyph)
        tokens.append(local_by_glyph[glyph])
    return glyphs, tokens


def make_condition_screen(glyph_by_char: dict[str, int]) -> tuple[list[int], list[int]]:
    rows = [[" "] * 18 for _ in range(6)]

    def put(row: int, col: int, text: str) -> None:
        for i, char in enumerate(text):
            rows[row][col + i] = char

    put(0, 0, "승리조건")
    put(1, 1, "-볼도 처치")
    put(3, 0, "패배조건")
    put(4, 1, "-볼도 도주")
    put(5, 1, "-주인공 사망")

    glyphs: list[int] = [SPACE_GLYPH]
    local_by_glyph = {SPACE_GLYPH: 0}
    tokens: list[int] = []
    for row in rows:
        for char in row:
            glyph = SPACE_GLYPH if char == " " else glyph_by_char[char]
            if glyph not in local_by_glyph:
                local_by_glyph[glyph] = len(glyphs)
                glyphs.append(glyph)
            tokens.append(local_by_glyph[glyph])
    return glyphs, tokens


def wrap_korean(text: str, width: int = 18) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def load_scenario_descriptions() -> list[str]:
    src = Path("build_korean_complete_wip.py").read_text()
    module = ast.parse(src)
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "SCENARIO_DESCRIPTIONS":
                descriptions = ast.literal_eval(node.value)
                if len(descriptions) != 31:
                    raise ValueError(f"expected 31 scenario descriptions, got {len(descriptions)}")
                return descriptions
    raise ValueError("SCENARIO_DESCRIPTIONS not found")


def patch_condition_1(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    glyphs, tokens = make_condition_screen(glyph_by_char)
    glyph_ptr = be32(data, CONDITION_GLYPH_LIST_TABLE)
    token_ptr = be32(data, CONDITION_POINTER_TABLE)
    write_word_list(
        data,
        glyph_ptr,
        glyphs,
        glyph_list_capacity_words(data, CONDITION_GLYPH_LIST_TABLE, 0, 32),
    )
    write_token_stream(
        data,
        token_ptr,
        tokens,
        capacity_words(data, CONDITION_POINTER_TABLE, 0, 32),
    )


def normalize_scenario_text(text: str) -> str:
    normalized_lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            normalized_lines.append("")
            continue
        normalized_lines.extend(wrap_korean(line, 18))
    return "\n".join(normalized_lines)


def patch_scenario(data: bytearray, index: int, text: str, glyph_by_char: dict[str, int]) -> None:
    scenario_text = normalize_scenario_text(text)
    glyphs, tokens = make_record_encoding(scenario_text, glyph_by_char)
    glyph_ptr = be32(data, SCENARIO_GLYPH_LIST_TABLE + index * 4)
    token_ptr = be32(data, SCENARIO_POINTER_TABLE + index * 4)
    write_word_list(
        data,
        glyph_ptr,
        glyphs,
        glyph_list_capacity_words(data, SCENARIO_GLYPH_LIST_TABLE, index, 31),
    )
    write_token_stream(
        data,
        token_ptr,
        tokens,
        capacity_words(data, SCENARIO_POINTER_TABLE, index, 31),
    )


def patch_scenarios(data: bytearray, descriptions: list[str], glyph_by_char: dict[str, int]) -> None:
    for index, text in enumerate(descriptions):
        patch_scenario(data, index, text, glyph_by_char)


def main() -> None:
    data = bytearray(IN_ROM.read_bytes())
    descriptions = load_scenario_descriptions()
    condition_chars = "승리조건-볼도 처치패배주인공 사망도주"
    chars = collect_chars(condition_chars, *descriptions)
    glyph_by_char = install_custom_glyphs(data, chars)
    patch_condition_1(data, glyph_by_char)
    patch_scenarios(data, descriptions, glyph_by_char)
    OUT_ROM.write_bytes(data)
    print(f"wrote {OUT_ROM}")
    used = sorted(glyph_by_char.values())
    print(f"custom glyphs: {len(glyph_by_char)} ({used[0]:04X}-{used[-1]:04X})")


if __name__ == "__main__":
    main()
