#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.append(str(Path(__file__).resolve().parents[1]))
from tools.jp_text_font_analyzer import JP_FONT_BASE, render_jp_2bpp16_glyph


JP_ROM = Path("roms/original/Langrisser II (Japan).md")
EN_ROM = Path("roms/original/Langrisser II (English).md")
OUT_DIR = Path("captures/analysis/jp_byte_tables")

CLASS_POINTER_TABLE = 0x05E6D8
CLASS_POINTER_COUNT = 156


KOREAN_CLASS_LABELS = [
    "        ",
    "파이터",
    "클레릭",
    "워록",
    "로드",
    "나이트",
    "호크나이트",
    "크로코나이트",
    "힐러",
    "소서러",
    "샤먼",
    "하이로드",
    "하이랜더",
    "매직나이트",
    "유니콘나이트",
    "드래곤나이트",
    "서펜나이트",
    "프리스트",
    "비숍",
    "메이지",
    "아크메이지",
    "위저드",
    "하이프리스트",
    "세인트",
    "세이지",
    "팔라딘",
    "소드마스터",
    "나이트마스터",
    "그랑나이트",
    "실버나이트",
    "드래곤로드",
    "서펜로드",
    "킹",
    "레인저",
    "히어로",
    "하이마스터",
    "드래곤마스터",
    "에이전트",
    "자베라",
    "프린세스",
    "서머너",
    "로열나이트",
    "서펜마스터",
    "라이더",
    "뱀파이어",
    "파이터",
    "파이터",
    "클레릭",
    "워록",
    "나이트",
    "로드",
    "시프",
    "소서러",
    "호크나이트",
    "샤먼",
    "매직나이트",
    "매직나이트",
    "소드맨",
    "하이로드",
    "어새신",
    "서펜나이트",
    "비숍",
    "드래곤나이트",
    "메이지",
    "네크로맨서",
    "위저드",
    "아크메이지",
    "실버나이트",
    "실버나이트",
    "나이트마스터",
    "나이트마스터",
    "팔라딘",
    "세인트",
    "제너럴",
    "제너럴",
    "드래곤로드",
    "서펜로드",
    "로열가드",
    "엠퍼러",
    "자베라",
    "웨어울프",
    "그레이트슬라임",
    "케르베로스",
    "스큐라",
    "고스트",
    "와이번",
    "마스터디노",
    "아이언골렘",
    "리치",
    "리빙아머",
    "서큐버스",
    "크라켄",
    "미노타우로스",
    "데몬로드",
    "그레이트드래곤",
    "뱀파이어로드",
    "다크프린세스",
    "다크마스터",
    "파이크",
    "팔랑크스",
    "솔저",
    "글래디에이터",
    "아머솔저",
    "호스맨",
    "헤비호스맨",
    "드라군",
    "엘프",
    "발리스타",
    "몽크",
    "가드맨",
    "머맨",
    "그리폰",
    "엔젤",
    "시민",
    "솔저",
    "아머솔저",
    "버서커",
    "바바리안",
    "다크엘프",
    "발리스타",
    "리자드맨",
    "호스맨",
    "헤비호스맨",
    "로열호스",
    "다크가드",
    "그리폰",
    "파이크",
    "팔랑크스",
    "스켈톤",
    "좀비",
    "가고일",
    "울프맨",
    "본디노",
    "리바이어선",
    "골렘",
    "뱀파이어배트",
    "엘리멘탈",
    "아크데몬",
    "레이스",
    "헬하운드",
    "슬라임",
    "엘리멘탈",
    "프레이야",
    "화이트드래곤",
    "발키리",
    "슬레이프니르",
    "펜릴",
    "요르문간드",
    "아니키",
    "빌더",
    "파이터",
    "클레릭",
    "나이트",
    "로드",
    "파이레츠",
    "하이로드",
]


def be16(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def word_swapped_pointer(data: bytes, offset: int) -> int:
    return (be16(data, offset + 2) << 16) | be16(data, offset)


def read_byte_string(data: bytes, offset: int, terminator: int) -> bytes:
    out = bytearray()
    pos = offset
    while pos < len(data):
        value = data[pos]
        pos += 1
        if value == terminator:
            break
        out.append(value)
    return bytes(out)


def read_class_entries(jp_rom: bytes, en_rom: bytes) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(CLASS_POINTER_COUNT):
        ptr = word_swapped_pointer(jp_rom, CLASS_POINTER_TABLE + index * 4)
        jp_raw = read_byte_string(jp_rom, ptr, 0xFF)
        en_ptr = word_swapped_pointer(en_rom, CLASS_POINTER_TABLE + index * 4)
        en_raw = read_byte_string(en_rom, en_ptr, 0xFF)
        english = en_raw.decode("ascii", errors="replace").replace("\x00", "␀")
        rows.append(
            {
                "index": index,
                "pointer": ptr,
                "capacity": len(jp_raw),
                "jp": jp_raw.decode("cp932", errors="replace"),
                "english": english,
                "korean": KOREAN_CLASS_LABELS[index],
            }
        )
    return rows


def command_dump(args: argparse.Namespace) -> None:
    jp_rom = args.jp_rom.read_bytes()
    en_rom = args.en_rom.read_bytes()
    rows = read_class_entries(jp_rom, en_rom)
    for row in rows:
        print(
            f"{row['index']:03d}\t0x{row['pointer']:06X}\t"
            f"cap={row['capacity']:02d}\t{row['jp']}\t{row['english']}\t{row['korean']}"
        )


def command_csv(args: argparse.Namespace) -> None:
    jp_rom = args.jp_rom.read_bytes()
    en_rom = args.en_rom.read_bytes()
    rows = read_class_entries(jp_rom, en_rom)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["index", "pointer", "capacity", "jp", "english", "korean"])
        writer.writeheader()
        writer.writerows(rows)
    print(args.out)


def command_sheet(args: argparse.Namespace) -> None:
    jp_rom = args.jp_rom.read_bytes()
    en_rom = args.en_rom.read_bytes()
    rows = read_class_entries(jp_rom, en_rom)
    font = ImageFont.truetype(str(args.font), args.font_size)
    row_h = args.font_size + 8
    widths = [52, 84, 52, 210, 180, 240]
    width = sum(widths)
    height = row_h * (len(rows) + 1)
    img = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    headers = ["idx", "ptr", "cap", "jp", "en", "ko"]
    x = 0
    for w, header in zip(widths, headers):
        draw.rectangle((x, 0, x + w - 1, row_h - 1), fill=(220, 220, 220))
        draw.text((x + 4, 4), header, font=font, fill=(0, 0, 0))
        x += w
    for r, row in enumerate(rows, 1):
        values = [
            f"{row['index']:03d}",
            f"{row['pointer']:06X}",
            str(row["capacity"]),
            str(row["jp"]),
            str(row["english"]),
            str(row["korean"]),
        ]
        x = 0
        for w, value in zip(widths, values):
            draw.rectangle((x, r * row_h, x + w - 1, (r + 1) * row_h - 1), outline=(225, 225, 225))
            draw.text((x + 4, r * row_h + 4), value, font=font, fill=(0, 0, 0))
            x += w
    args.out.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(args.out)


def render_byte_string(data: bytes, values: bytes, scale: int) -> Image.Image:
    width = max(1, len(values)) * 16 * scale
    height = 16 * scale
    img = Image.new("RGB", (width, height), "white")
    for i, value in enumerate(values):
        if value == 0x20:
            continue
        glyph = render_jp_2bpp16_glyph(data, JP_FONT_BASE + value * 64, scale)
        img.paste(glyph, (i * 16 * scale, 0))
    return img


def command_render_rom(args: argparse.Namespace) -> None:
    rom = args.rom.read_bytes()
    en_rom = args.en_rom.read_bytes()
    font = ImageFont.truetype(str(args.font), args.font_size)
    row_h = max(args.font_size + 8, 16 * args.scale + 8)
    widths = [52, 80, 150, 180, 16 * args.scale * args.max_chars + 12]
    width = sum(widths)
    height = row_h * (CLASS_POINTER_COUNT + 1)
    img = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    headers = ["idx", "ptr", "en", "ko target", "rom glyphs"]
    x = 0
    for w, header in zip(widths, headers):
        draw.rectangle((x, 0, x + w - 1, row_h - 1), fill=(220, 220, 220))
        draw.text((x + 4, 4), header, font=font, fill=(0, 0, 0))
        x += w

    for index in range(CLASS_POINTER_COUNT):
        ptr = word_swapped_pointer(rom, CLASS_POINTER_TABLE + index * 4)
        raw = read_byte_string(rom, ptr, 0xFF)
        en_ptr = word_swapped_pointer(en_rom, CLASS_POINTER_TABLE + index * 4)
        en_raw = read_byte_string(en_rom, en_ptr, 0xFF)
        values = [
            f"{index:03d}",
            f"{ptr:06X}",
            en_raw.decode("ascii", errors="replace").replace("\x00", " "),
            KOREAN_CLASS_LABELS[index],
        ]
        y = (index + 1) * row_h
        x = 0
        for w, value in zip(widths[:4], values):
            draw.rectangle((x, y, x + w - 1, y + row_h - 1), outline=(225, 225, 225))
            draw.text((x + 4, y + 4), value, font=font, fill=(0, 0, 0))
            x += w
        draw.rectangle((x, y, x + widths[4] - 1, y + row_h - 1), outline=(225, 225, 225))
        glyph_img = render_byte_string(rom, raw[: args.max_chars], args.scale)
        img.paste(glyph_img, (x + 4, y + 4))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(args.out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jp-rom", type=Path, default=JP_ROM)
    parser.add_argument("--en-rom", type=Path, default=EN_ROM)
    sub = parser.add_subparsers(dest="command", required=True)

    dump = sub.add_parser("dump")
    dump.set_defaults(func=command_dump)

    csv_cmd = sub.add_parser("csv")
    csv_cmd.add_argument("--out", type=Path, default=OUT_DIR / "class_table.csv")
    csv_cmd.set_defaults(func=command_csv)

    sheet = sub.add_parser("sheet")
    sheet.add_argument("--out", type=Path, default=OUT_DIR / "class_table.png")
    sheet.add_argument("--font", type=Path, default=Path("tools/fonts/Galmuri9.ttf"))
    sheet.add_argument("--font-size", type=int, default=16)
    sheet.set_defaults(func=command_sheet)

    render = sub.add_parser("render-rom")
    render.add_argument("--rom", type=Path, required=True)
    render.add_argument("--out", type=Path, default=OUT_DIR / "class_table_rendered.png")
    render.add_argument("--font", type=Path, default=Path("tools/fonts/Galmuri9.ttf"))
    render.add_argument("--font-size", type=int, default=16)
    render.add_argument("--scale", type=int, default=2)
    render.add_argument("--max-chars", type=int, default=12)
    render.set_defaults(func=command_render_rom)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
