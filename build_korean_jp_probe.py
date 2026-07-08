#!/usr/bin/env python3
from __future__ import annotations

from collections import OrderedDict
import ast
import argparse
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
CONDITION_GLYPH_LIST_RELOC_BASE = 0x1E7000
SCENARIO_POINTER_TABLE = 0x9CF7C
SCENARIO_GLYPH_LIST_TABLE = 0x9B2FC

SPACE_GLYPH = 0x0054
CUSTOM_GLYPH_START = 0x0260
CUSTOM_GLYPH_END = 0x07FF
CUSTOM_GLYPH_RESERVED = {0x039C}

DIRECT_STRING_PATCHES = {
    0x82BFE: "마법화살",
    0x82C0E: "블래스트",
    0x82C18: "썬더",
    0x82C22: "파이어볼",
    0x82C34: "메테오",
    0x82C3C: "블리자드",
    0x82C48: "토네이도",
    0x82C54: "턴언데드",
    0x82C66: "어스퀘이크",
    0x82C76: "힐1",
    0x82C80: "힐2",
    0x82C8A: "포스힐1",
    0x82C9C: "포스힐2",
    0x82CAE: "수면",
    0x82CB8: "침묵",
    0x82CC2: "보호",
    0x82CD2: "공격",
    0x82CDC: "존",
    0x82CE4: "순간이동",
    0x82CF0: "환영",
    0x82D00: "저항",
    0x82D0A: "매혹",
    0x82D14: "소환마법",
    0x82D5A: "파이크",
    0x82D62: "팔랑크스",
    0x82D70: "솔저",
    0x82D7C: "검투사",
    0x82D8E: "장갑병",
    0x82DA0: "기병",
    0x82DAC: "중기병",
    0x82DBE: "드라군",
    0x82DCA: "엘프",
    0x82DD2: "발리스타",
    0x82DDC: "몽크",
    0x82DE4: "가드맨",
    0x82DF0: "머맨",
    0x82DFA: "그리폰",
    0x82E06: "엔젤",
    0x97404: "엘윈",
    0x97410: "리아나",
    0x97418: "라나",
    0x97420: "쉐리",
    0x9742A: "헤인",
    0x97432: "스코트",
    0x9743C: "키스",
    0x97444: "아론",
    0x9744E: "레스터",
    0x97458: "제시카",
    0x97462: "가면기사",
    0x9746C: "레온",
    0x97474: "베른하르트",
    0x97482: "발가스",
    0x9748C: "보젤",
    0x97496: "레아드",
    0x974A0: "볼도",
    0x974AA: "졸름",
    0x974B2: "에그베르트",
    0x974BE: "이멜다",
    0x974C8: "모건",
    0x974D2: "기잠",
    0x974DA: "클레이머",
    0x974E6: "세이갈",
    0x974F0: "폴거",
    0x974FC: "일반병",
    0x97504: "지휘관",
    0x9750C: "사제",
    0x97512: "주민",
    0x97518: "해적",
    0x9751E: "자경단",
    0x97526: "로렌",
    0x97530: "아돈",
    0x97538: "삼손",
    0x97542: "바란",
    0x9754A: "제국군지휘관",
    0x97558: "웨어울프",
    0x97566: "그레이트슬라임",
    0x97578: "스큐라",
    0x97582: "아이언골렘",
    0x97594: "리치",
    0x9759C: "리빙아머",
    0x975AE: "뱀파이어로드",
    0x975C0: "고스트",
    0x975CA: "케르베로스",
    0x975D6: "마스터디노",
    0x975E8: "와이번",
    0x975F4: "대드래곤",
    0x97606: "미노타우로스",
    0x97614: "크라켄",
    0x97620: "서큐버스",
    0x9762C: "데몬로드",
    0x9763C: "형님",
    0x97642: "마녀",
    0x97648: "신관",
    0x9764E: "제국병",
    0x97656: "파이어스",
}

DIRECT_FIXED_STRING_PATCHES = {
    0x9702C: (4, "출격준비"),
    0x97034: (4, "용병고용"),
    0x9703C: (6, "장비착용"),
    0x97048: (4, "상점"),
    0x97050: (5, "지휘관배치"),
    0x9705A: (2, "구입"),
    0x9705E: (2, "판매"),
    0x97062: (3, "취소"),
    0x9706C: (2, "이동"),
    0x97070: (2, "공격"),
    0x97074: (2, "마법"),
    0x97078: (2, "소환"),
    0x9707C: (2, "치료"),
    0x97080: (2, "명령"),
}

CONDITION_SCREENS = [
    ["승리조건", "-볼도 격파", "", "패배조건", "-주인공 사망", "-볼도 우하단 도주"],
    ["승리조건", "-리아나 북쪽 도착", "-적 전멸", "패배조건", "-리아나 사망", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-리아나 사망", "-주인공 사망"],
    ["승리조건", "-모건 격파", "", "패배조건", "-신관 전멸", "-리아나/주인공 사망"],
    ["승리조건", "-2턴 안에 적 전멸", "-주인공 목표 이동", "패배조건", "-턴 오버", "-주인공 사망"],
    ["승리조건", "-목표 적 격파", "-맵 위쪽 도착", "패배조건", "-시민 전멸", "-주인공 사망"],
    ["승리조건", "-기잠 격파", "", "패배조건", "-조비리안 전멸", "-주인공 사망"],
    ["승리조건", "-3턴 안에 클레이머 격파", "", "패배조건", "-턴 오버", "-주인공 사망"],
    ["승리조건", "-레아드 격파", "", "패배조건", "-NPC 전멸", "-주인공 사망"],
    ["승리조건", "-레스터 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망", "-제시카 사망"],
    ["승리조건", "-적 전멸", "-다크로드 획득", "패배조건", "-주인공 사망"],
    ["승리조건", "-발가스 장군 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-랑그릿사 도달", "-레온 격파", "패배조건", "-레온 도달", "-주인공 사망"],
    ["승리조건", "-이멜다 장군 격파", "-주인공 아래 이동", "패배조건", "-주인공 사망"],
    ["승리조건", "-레온 격파", "-성문으로 이동", "패배조건", "-주인공 사망"],
    ["승리조건", "-베른하르트 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-레드드래곤 격파", "-프린세스 격파", "패배조건", "-주인공 사망", "-주민 전멸"],
    ["승리조건", "-3턴 안에 이멜다 격파", "", "패배조건", "-턴 오버", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망", "-제시카 사망"],
    ["승리조건", "-소드마스터 도달", "-적 전멸", "패배조건", "-롯시 납치", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-에그베르트 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-베른하르트 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-마녀 격파", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
    ["승리조건", "-적 전멸", "", "패배조건", "-주인공 사망"],
]


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


def put32(data: bytearray, offset: int, value: int) -> None:
    data[offset] = (value >> 24) & 0xFF
    data[offset + 1] = (value >> 16) & 0xFF
    data[offset + 2] = (value >> 8) & 0xFF
    data[offset + 3] = value & 0xFF


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


def write_word_list_exact(data: bytearray, offset: int, values: list[int]) -> int:
    for i, value in enumerate(values):
        put16(data, offset + i * 2, value)
    put16(data, offset + len(values) * 2, 0xFFFF)
    return offset + (len(values) + 1) * 2


def write_token_stream(data: bytearray, offset: int, tokens: list[int], max_words: int) -> None:
    if len(tokens) + 1 > max_words:
        raise ValueError(f"token stream needs {len(tokens) + 1} words, only {max_words} available")
    for i, token in enumerate(tokens):
        put16(data, offset + i * 2, token)
    put16(data, offset + len(tokens) * 2, 0xFFFF)
    for i in range(len(tokens) + 1, max_words):
        put16(data, offset + i * 2, 0xFFFF)


def direct_string_capacity_words(data: bytes | bytearray, offset: int) -> int:
    pos = offset
    while pos + 1 < len(data):
        value = be16(data, pos)
        pos += 2
        if value == 0xFFFF:
            return (pos - offset) // 2
    raise ValueError(f"unterminated direct string at 0x{offset:06X}")


def write_direct_string(data: bytearray, offset: int, text: str, glyph_by_char: dict[str, int]) -> None:
    values = [glyph_by_char[char] for char in text if char != " "]
    capacity = direct_string_capacity_words(data, offset)
    if len(values) + 1 > capacity:
        raise ValueError(
            f"direct string at 0x{offset:06X} needs {len(values) + 1} words, only {capacity}"
        )
    write_word_list(data, offset, values, capacity)


def write_fixed_direct_string(
    data: bytearray,
    offset: int,
    max_words: int,
    text: str,
    glyph_by_char: dict[str, int],
) -> None:
    values = [SPACE_GLYPH if char == " " else glyph_by_char[char] for char in text]
    if len(values) > max_words:
        raise ValueError(
            f"fixed direct string at 0x{offset:06X} needs {len(values)} words, only {max_words}"
        )
    values.extend([SPACE_GLYPH] * (max_words - len(values)))
    for i, value in enumerate(values):
        put16(data, offset + i * 2, value)


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


def make_condition_screen(lines: list[str], glyph_by_char: dict[str, int]) -> tuple[list[int], list[int]]:
    if len(lines) > 6:
        raise ValueError("condition screen supports at most 6 rows")
    rows = [[" "] * 18 for _ in range(6)]

    def put(row: int, col: int, text: str) -> None:
        if len(text) > 18:
            raise ValueError(f"condition row too long ({len(text)} > 18): {text!r}")
        for i, char in enumerate(text):
            rows[row][col + i] = char

    for row, line in enumerate(lines):
        put(row, 0, line)

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


def patch_condition(
    data: bytearray,
    index: int,
    lines: list[str],
    glyph_by_char: dict[str, int],
    glyph_cursor: int,
) -> int:
    glyphs, tokens = make_condition_screen(lines, glyph_by_char)
    token_ptr = be32(data, CONDITION_POINTER_TABLE + index * 4)
    put32(data, CONDITION_GLYPH_LIST_TABLE + index * 4, glyph_cursor)
    glyph_cursor = write_word_list_exact(data, glyph_cursor, glyphs)
    if glyph_cursor & 1:
        glyph_cursor += 1
    write_token_stream(
        data,
        token_ptr,
        tokens,
        capacity_words(data, CONDITION_POINTER_TABLE, index, 32),
    )
    return glyph_cursor


def patch_conditions(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    if len(CONDITION_SCREENS) != 32:
        raise ValueError(f"expected 32 condition screens, got {len(CONDITION_SCREENS)}")
    glyph_cursor = CONDITION_GLYPH_LIST_RELOC_BASE
    for index, lines in enumerate(CONDITION_SCREENS):
        glyph_cursor = patch_condition(data, index, lines, glyph_by_char, glyph_cursor)
    if glyph_cursor >= 0x1E8000:
        raise ValueError(f"relocated condition glyph lists overflow: 0x{glyph_cursor:06X}")


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


def patch_direct_strings(data: bytearray, glyph_by_char: dict[str, int]) -> None:
    for offset, text in DIRECT_STRING_PATCHES.items():
        write_direct_string(data, offset, text, glyph_by_char)
    for offset, (max_words, text) in DIRECT_FIXED_STRING_PATCHES.items():
        write_fixed_direct_string(data, offset, max_words, text, glyph_by_char)


def update_md_checksum(data: bytearray) -> int:
    checksum = 0
    for offset in range(0x200, len(data), 2):
        checksum = (checksum + be16(data, offset)) & 0xFFFF
    put16(data, 0x18E, checksum)
    return checksum


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_ROM)
    parser.add_argument(
        "--scenario-count",
        type=int,
        default=31,
        help="number of scenario description records to patch from the start",
    )
    parser.add_argument("--skip-condition", action="store_true")
    args = parser.parse_args()

    data = bytearray(IN_ROM.read_bytes())
    descriptions = load_scenario_descriptions()
    if not 0 <= args.scenario_count <= len(descriptions):
        raise ValueError(f"--scenario-count must be 0..{len(descriptions)}")
    active_condition_chars = "" if args.skip_condition else "\n".join(
        line for screen in CONDITION_SCREENS for line in screen
    )
    chars = collect_chars(
        active_condition_chars,
        *descriptions[: args.scenario_count],
        *DIRECT_STRING_PATCHES.values(),
        *(text for _, text in DIRECT_FIXED_STRING_PATCHES.values()),
    )
    glyph_by_char = install_custom_glyphs(data, chars)
    if not args.skip_condition:
        patch_conditions(data, glyph_by_char)
    patch_scenarios(data, descriptions[: args.scenario_count], glyph_by_char)
    patch_direct_strings(data, glyph_by_char)
    checksum = update_md_checksum(data)
    args.out.write_bytes(data)
    print(f"wrote {args.out}")
    used = sorted(glyph_by_char.values())
    if used:
        print(f"custom glyphs: {len(glyph_by_char)} ({used[0]:04X}-{used[-1]:04X})")
    else:
        print("custom glyphs: 0")
    print(f"checksum: {checksum:04X}")


if __name__ == "__main__":
    main()
