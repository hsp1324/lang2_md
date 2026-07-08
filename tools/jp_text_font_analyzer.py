#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


DEFAULT_ROM = Path("Langrisser II (Japan).md")
OUT_DIR = Path("analysis_tiles/jpfont_probe")

JP_FONT_BASE = 0x40000
CONDITION_TABLE = 0x98D7A
CONDITION_COUNT = 32
CONDITION_GLYPH_LIST_TABLE = 0x986C6
SCENARIO_TABLE = 0x9CF7C
SCENARIO_COUNT = 31
SCENARIO_GLYPH_LIST_TABLE = 0x9B2FC

KNOWN_CONTROLS = {
    0xFFFF: "END",
    0xFFFE: "NL",
    0xFFF7: "CTRL_F7",
}


@dataclass(frozen=True)
class TextTable:
    name: str
    offset: int
    count: int


TEXT_TABLES = {
    "conditions": TextTable("conditions", CONDITION_TABLE, CONDITION_COUNT),
    "scenarios": TextTable("scenarios", SCENARIO_TABLE, SCENARIO_COUNT),
}


def be16(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def be32(data: bytes, offset: int) -> int:
    return (
        (data[offset] << 24)
        | (data[offset + 1] << 16)
        | (data[offset + 2] << 8)
        | data[offset + 3]
    )


def load_rom(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) < 0x200:
        raise ValueError(f"{path} is too small to be a Mega Drive ROM")
    return data


def read_pointer_table(data: bytes, table: TextTable) -> list[int]:
    ptrs: list[int] = []
    for i in range(table.count):
        ptr = be32(data, table.offset + i * 4)
        if ptr >= len(data):
            raise ValueError(
                f"{table.name}[{i}] pointer {ptr:06X} is outside ROM size {len(data):06X}"
            )
        ptrs.append(ptr)
    return ptrs


def read_token_stream(data: bytes, offset: int, limit_tokens: int = 4096) -> list[int]:
    tokens: list[int] = []
    pos = offset
    for _ in range(limit_tokens):
        if pos + 1 >= len(data):
            break
        token = be16(data, pos)
        tokens.append(token)
        pos += 2
        if token == 0xFFFF:
            break
    return tokens


def read_word_list(data: bytes, offset: int, limit_words: int = 4096) -> list[int]:
    values: list[int] = []
    pos = offset
    for _ in range(limit_words):
        if pos + 1 >= len(data):
            break
        value = be16(data, pos)
        if value == 0xFFFF:
            break
        values.append(value)
        pos += 2
    return values


def glyph_list_table_for_text_table(table_name: str) -> int:
    if table_name == "conditions":
        return CONDITION_GLYPH_LIST_TABLE
    if table_name == "scenarios":
        return SCENARIO_GLYPH_LIST_TABLE
    raise ValueError(f"unknown text table: {table_name}")


def read_glyph_list_for_record(data: bytes, table_name: str, index: int) -> list[int]:
    table_offset = glyph_list_table_for_text_table(table_name)
    ptr = be32(data, table_offset + index * 4)
    return read_word_list(data, ptr)


def read_all_tokens(data: bytes, table: TextTable) -> list[int]:
    tokens: list[int] = []
    for ptr in read_pointer_table(data, table):
        tokens.extend(read_token_stream(data, ptr))
    return tokens


def render_1bpp16_glyph(
    data: bytes,
    offset: int,
    scale: int,
    invert: bool = False,
    height: int = 16,
) -> Image.Image:
    img = Image.new("RGB", (16 * scale, height * scale), "white")
    for y in range(height):
        row = be16(data, offset + y * 2)
        for x in range(16):
            bit = (row >> (15 - x)) & 1
            if invert:
                bit ^= 1
            color = (0, 0, 0) if bit else (255, 255, 255)
            img.paste(color, (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale))
    return img


def md_4bpp_tile(data: bytes, offset: int) -> list[list[int]]:
    pixels = [[0 for _ in range(8)] for _ in range(8)]
    for y in range(8):
        row = data[offset + y * 4 : offset + y * 4 + 4]
        if len(row) < 4:
            break
        for x in range(8):
            shift = 7 - x
            pixels[y][x] = (
                (((row[0] >> shift) & 1) << 3)
                | (((row[1] >> shift) & 1) << 2)
                | (((row[2] >> shift) & 1) << 1)
                | ((row[3] >> shift) & 1)
            )
    return pixels


def render_md4_8_glyph(data: bytes, offset: int, scale: int) -> Image.Image:
    palette = [
        (255, 255, 255),
        (210, 210, 210),
        (150, 150, 150),
        (90, 90, 90),
        (0, 0, 0),
    ]
    img = Image.new("RGB", (8 * scale, 8 * scale), "white")
    pixels = md_4bpp_tile(data, offset)
    for y in range(8):
        for x in range(8):
            v = pixels[y][x]
            color = palette[min(v, len(palette) - 1)]
            img.paste(color, (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale))
    return img


def render_md4_16_glyph(data: bytes, offset: int, scale: int) -> Image.Image:
    img = Image.new("RGB", (16 * scale, 16 * scale), "white")
    for tile, (tx, ty) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
        glyph = render_md4_8_glyph(data, offset + tile * 32, scale)
        img.paste(glyph, (tx * 8 * scale, ty * 8 * scale))
    return img


def render_jp_2bpp16_glyph(
    data: bytes,
    offset: int,
    scale: int,
    swap_planes: bool = False,
) -> Image.Image:
    # The game routine at 0x2C390 reads 32 source words per glyph. Each word is
    # converted into one 8-pixel Mega Drive 4bpp tile row, where the high and low
    # bytes are two 1bpp planes. Four consecutive 8x8 tiles form one 16x16 glyph.
    palette = [
        (255, 255, 255),
        (170, 170, 170),
        (90, 90, 90),
        (0, 0, 0),
    ]
    img = Image.new("RGB", (16 * scale, 16 * scale), "white")
    for source_row in range(32):
        word = be16(data, offset + source_row * 2)
        tile = source_row // 8
        row = source_row % 8
        tx = tile % 2
        ty = tile // 2
        for x in range(8):
            hi = (word >> (15 - x)) & 1
            lo = (word >> (7 - x)) & 1
            value = (lo << 1) | hi if swap_planes else (hi << 1) | lo
            color = palette[value]
            px = (tx * 8 + x) * scale
            py = (ty * 8 + row) * scale
            img.paste(color, (px, py, px + scale, py + scale))
    return img


def render_glyph(data: bytes, base: int, code: int, fmt: str, scale: int) -> Image.Image:
    if fmt == "1bpp16":
        return render_1bpp16_glyph(data, base + code * 32, scale, invert=False)
    if fmt == "1bpp16-invert":
        return render_1bpp16_glyph(data, base + code * 32, scale, invert=True)
    if fmt == "1bpp16x32":
        return render_1bpp16_glyph(data, base + code * 64, scale, invert=False, height=32)
    if fmt == "1bpp16x32-invert":
        return render_1bpp16_glyph(data, base + code * 64, scale, invert=True, height=32)
    if fmt == "jp2bpp16":
        return render_jp_2bpp16_glyph(data, base + code * 64, scale, swap_planes=False)
    if fmt == "jp2bpp16-swap":
        return render_jp_2bpp16_glyph(data, base + code * 64, scale, swap_planes=True)
    if fmt == "md4-8":
        return render_md4_8_glyph(data, base + code * 32, scale)
    if fmt == "md4-16":
        return render_md4_16_glyph(data, base + code * 128, scale)
    raise ValueError(f"unsupported font format: {fmt}")


def glyph_dimensions(fmt: str) -> tuple[int, int, int]:
    if fmt in {"1bpp16", "1bpp16-invert", "md4-16"}:
        return 16, 16, 32 if fmt.startswith("1bpp") else 128
    if fmt in {"1bpp16x32", "1bpp16x32-invert"}:
        return 16, 32, 64
    if fmt in {"jp2bpp16", "jp2bpp16-swap"}:
        return 16, 16, 64
    if fmt == "md4-8":
        return 8, 8, 32
    raise ValueError(f"unsupported font format: {fmt}")


def render_sheet(
    data: bytes,
    base: int,
    fmt: str,
    count: int,
    cols: int,
    scale: int,
    label: bool,
    out_path: Path,
) -> None:
    gw, gh, _ = glyph_dimensions(fmt)
    rows = (count + cols - 1) // cols
    img = Image.new("RGB", (cols * gw * scale, rows * gh * scale), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    for code in range(count):
        gx = (code % cols) * gw * scale
        gy = (code // cols) * gh * scale
        glyph = render_glyph(data, base, code, fmt, scale)
        img.paste(glyph, (gx, gy))
        if label:
            draw.text((gx + 1, gy + 1), f"{code:02X}", fill=(220, 0, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def render_text_sample(
    data: bytes,
    tokens: list[int],
    base: int,
    fmt: str,
    scale: int,
    cols: int,
    out_path: Path,
    glyph_list: list[int] | None = None,
) -> None:
    gw, gh, _ = glyph_dimensions(fmt)
    cell_w = gw * scale
    cell_h = gh * scale
    lines: list[list[int]] = [[]]
    for token in tokens:
        if token == 0xFFFF:
            break
        if token == 0xFFFE:
            lines.append([])
            continue
        if token >= 0xFF00:
            # Keep controls visible as red cells rather than silently dropping them.
            lines[-1].append(token)
            continue
        lines[-1].append(token)
        if len(lines[-1]) >= cols:
            lines.append([])

    width = max(1, cols) * cell_w
    height = max(1, len(lines)) * cell_h
    img = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    for row_idx, line in enumerate(lines):
        for col_idx, token in enumerate(line[:cols]):
            x = col_idx * cell_w
            y = row_idx * cell_h
            if token >= 0xFF00:
                draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), fill=(80, 0, 0))
                draw.text((x + 1, y + 1), KNOWN_CONTROLS.get(token, f"{token:04X}"), fill=(255, 255, 255))
                continue
            glyph_code = token
            if glyph_list is not None:
                if token >= len(glyph_list):
                    draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), fill=(255, 220, 220))
                    draw.text((x + 1, y + 1), f"{token:04X}?", fill=(255, 0, 0))
                    continue
                glyph_code = glyph_list[token]
            try:
                glyph = render_glyph(data, base, glyph_code, fmt, scale)
                img.paste(glyph, (x, y))
            except Exception:
                draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline=(255, 0, 0))
                draw.text((x + 1, y + 1), f"{token:04X}->{glyph_code:04X}", fill=(255, 0, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def scan_direct_strings(
    data: bytes,
    start: int,
    end: int,
    min_words: int,
    max_words: int,
) -> list[tuple[int, list[int]]]:
    entries: list[tuple[int, list[int]]] = []
    pos = start
    while pos + 1 < end:
        values: list[int] = []
        cursor = pos
        valid = True
        while cursor + 1 < end and len(values) <= max_words:
            value = be16(data, cursor)
            cursor += 2
            if value == 0xFFFF:
                break
            if value >= 0xFF00:
                valid = False
                break
            values.append(value)
        else:
            valid = False
        if valid and min_words <= len(values) <= max_words:
            entries.append((pos, values))
            pos = cursor
        else:
            pos += 2
    return entries


def render_direct_string_sheet(
    data: bytes,
    entries: list[tuple[int, list[int]]],
    base: int,
    fmt: str,
    scale: int,
    out_path: Path,
) -> None:
    gw, gh, _ = glyph_dimensions(fmt)
    label_w = 72
    max_words = max((len(values) for _, values in entries), default=1)
    row_h = gh * scale + 8
    width = label_w + max_words * gw * scale + 8
    height = max(1, len(entries)) * row_h
    img = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    for row_idx, (offset, values) in enumerate(entries):
        y = row_idx * row_h
        draw.text((2, y + 2), f"{offset:06X}", fill=(0, 0, 0))
        for col_idx, glyph_code in enumerate(values):
            x = label_w + col_idx * gw * scale
            try:
                glyph = render_glyph(data, base, glyph_code, fmt, scale)
                img.paste(glyph, (x, y))
            except Exception:
                draw.rectangle((x, y, x + gw * scale - 1, y + gh * scale - 1), outline=(255, 0, 0))
                draw.text((x + 1, y + 1), f"{glyph_code:04X}", fill=(255, 0, 0))
        draw.line((0, y + row_h - 1, width, y + row_h - 1), fill=(220, 220, 220))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def command_report(args: argparse.Namespace) -> None:
    data = load_rom(args.rom)
    for table in TEXT_TABLES.values():
        ptrs = read_pointer_table(data, table)
        tokens = read_all_tokens(data, table)
        ordinary = [t for t in tokens if t < 0xFF00]
        controls = Counter(t for t in tokens if t >= 0xFF00)
        freq = Counter(ordinary)
        print(f"{table.name}: table=0x{table.offset:06X} count={table.count}")
        print(f"  first pointers: {', '.join(f'0x{x:06X}' for x in ptrs[:5])}")
        print(f"  tokens={len(tokens)} ordinary={len(ordinary)} unique_ordinary={len(freq)}")
        if ordinary:
            print(f"  ordinary range=0x{min(ordinary):04X}..0x{max(ordinary):04X}")
        print("  controls:", ", ".join(f"0x{k:04X}={v}" for k, v in sorted(controls.items())) or "none")
        print(
            "  top ordinary:",
            ", ".join(f"0x{k:04X}:{v}" for k, v in freq.most_common(args.top)),
        )
        for i, ptr in enumerate(ptrs[: args.samples]):
            sample = read_token_stream(data, ptr, args.sample_tokens)
            print(f"  sample {i:02d} @0x{ptr:06X}: {' '.join(f'{x:04X}' for x in sample)}")
        glyph_table = glyph_list_table_for_text_table(table.name)
        glyph_ptrs = [be32(data, glyph_table + i * 4) for i in range(min(args.samples, table.count))]
        print(f"  glyph list table=0x{glyph_table:06X}")
        for i, ptr in enumerate(glyph_ptrs):
            values = read_word_list(data, ptr, args.sample_tokens)
            print(f"  glyphs {i:02d} @0x{ptr:06X}: {' '.join(f'{x:04X}' for x in values[:args.sample_tokens])}")


def command_render_fonts(args: argparse.Namespace) -> None:
    data = load_rom(args.rom)
    for base in args.base:
        for fmt in args.format:
            out = OUT_DIR / f"font_{base:06X}_{fmt}_{args.count}.png"
            render_sheet(data, base, fmt, args.count, args.cols, args.scale, args.label, out)
            print(out)


def command_render_text(args: argparse.Namespace) -> None:
    data = load_rom(args.rom)
    table = TEXT_TABLES[args.table]
    ptrs = read_pointer_table(data, table)
    tokens = read_token_stream(data, ptrs[args.index], args.limit)
    glyph_list = None
    mode = "raw"
    if args.mapped:
        glyph_list = read_glyph_list_for_record(data, args.table, args.index)
        mode = "mapped"
    out = OUT_DIR / f"text_{args.table}_{args.index:02d}_{mode}_{args.base:06X}_{args.format}.png"
    render_text_sample(data, tokens, args.base, args.format, args.scale, args.cols, out, glyph_list)
    print(out)
    print("tokens:", " ".join(f"{x:04X}" for x in tokens[: args.print_tokens]))
    if glyph_list is not None:
        print("glyph-list:", " ".join(f"{x:04X}" for x in glyph_list[: args.print_tokens]))


def command_render_direct_strings(args: argparse.Namespace) -> None:
    data = load_rom(args.rom)
    entries = scan_direct_strings(data, args.start, args.end, args.min_words, args.max_words)
    if args.limit:
        entries = entries[: args.limit]
    out = OUT_DIR / f"direct_{args.start:06X}_{args.end:06X}_{args.format}.png"
    render_direct_string_sheet(data, entries, args.base, args.format, args.scale, out)
    print(out)
    for offset, values in entries:
        print(f"0x{offset:06X}: {' '.join(f'{value:04X}' for value in values)}")


def parse_int(value: str) -> int:
    return int(value, 0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Japanese Langrisser II 16-bit text streams and candidate font data."
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser("report")
    report.add_argument("--top", type=int, default=20)
    report.add_argument("--samples", type=int, default=3)
    report.add_argument("--sample-tokens", type=int, default=48)
    report.set_defaults(func=command_report)

    fonts = sub.add_parser("render-fonts")
    fonts.add_argument("--base", type=parse_int, nargs="+", required=True)
    fonts.add_argument(
        "--format",
        choices=(
            "1bpp16",
            "1bpp16-invert",
            "1bpp16x32",
            "1bpp16x32-invert",
            "jp2bpp16",
            "jp2bpp16-swap",
            "md4-8",
            "md4-16",
        ),
        nargs="+",
        default=["jp2bpp16"],
    )
    fonts.add_argument("--count", type=int, default=256)
    fonts.add_argument("--cols", type=int, default=16)
    fonts.add_argument("--scale", type=int, default=3)
    fonts.add_argument("--label", action="store_true")
    fonts.set_defaults(func=command_render_fonts)

    text = sub.add_parser("render-text")
    text.add_argument("--table", choices=tuple(TEXT_TABLES), default="conditions")
    text.add_argument("--index", type=int, default=0)
    text.add_argument("--base", type=parse_int, required=True)
    text.add_argument(
        "--format",
        choices=(
            "1bpp16",
            "1bpp16-invert",
            "1bpp16x32",
            "1bpp16x32-invert",
            "jp2bpp16",
            "jp2bpp16-swap",
            "md4-8",
            "md4-16",
        ),
        default="jp2bpp16",
    )
    text.add_argument("--limit", type=int, default=512)
    text.add_argument("--cols", type=int, default=32)
    text.add_argument("--scale", type=int, default=3)
    text.add_argument("--print-tokens", type=int, default=96)
    text.add_argument("--mapped", action="store_true", help="render through the per-record glyph loading list")
    text.set_defaults(func=command_render_text)

    direct = sub.add_parser("render-direct-strings")
    direct.add_argument("--start", type=parse_int, required=True)
    direct.add_argument("--end", type=parse_int, required=True)
    direct.add_argument("--base", type=parse_int, default=JP_FONT_BASE)
    direct.add_argument(
        "--format",
        choices=(
            "1bpp16",
            "1bpp16-invert",
            "1bpp16x32",
            "1bpp16x32-invert",
            "jp2bpp16",
            "jp2bpp16-swap",
            "md4-8",
            "md4-16",
        ),
        default="jp2bpp16",
    )
    direct.add_argument("--scale", type=int, default=2)
    direct.add_argument("--min-words", type=int, default=2)
    direct.add_argument("--max-words", type=int, default=24)
    direct.add_argument("--limit", type=int, default=0)
    direct.set_defaults(func=command_render_direct_strings)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
