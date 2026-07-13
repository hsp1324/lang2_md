#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.jp_text_font_analyzer import JP_FONT_BASE, render_text_sample
except ModuleNotFoundError:  # Support direct execution from the tools directory.
    from jp_text_font_analyzer import JP_FONT_BASE, render_text_sample


def parse_int(text: str) -> int:
    return int(text, 0)


def parse_tokens(text: str) -> list[int]:
    return [int(word, 16) for word in text.split()]


def read_direct_tokens(rom: bytes, address: int, limit: int = 1024) -> list[int]:
    tokens: list[int] = []
    for index in range(limit):
        offset = address + index * 2
        if offset + 1 >= len(rom):
            raise ValueError(f"direct record at 0x{address:06X} runs past the ROM")
        token = int.from_bytes(rom[offset : offset + 2], "big")
        tokens.append(token)
        if token == 0xFFFF:
            return tokens
    raise ValueError(f"unterminated direct record at 0x{address:06X}")


def render_inventory_pages(
    rom: bytes,
    inventory: dict[str, object],
    ownership: str,
    out_dir: Path,
    *,
    scale: int,
    cols: int,
    pages_per_sheet: int,
) -> list[Path]:
    rows = [
        row
        for row in inventory["candidates"]
        if row["ownership"] == ownership
    ]
    if not rows:
        raise ValueError(f"no direct-string rows have ownership {ownership!r}")

    page_dir = out_dir / ownership
    page_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[tuple[str, Image.Image]] = []
    for index, row in enumerate(rows):
        address = str(row["address"])
        tokens = parse_tokens(str(row["original_tokens"]))
        page_path = page_dir / f"{index:03d}_{address[2:]}.png"
        render_text_sample(
            rom,
            tokens,
            JP_FONT_BASE,
            "jp2bpp16",
            scale,
            cols,
            page_path,
        )
        rendered.append((f"{index:03d} {address}", Image.open(page_path).convert("RGB")))

    sheets: list[Path] = []
    for sheet_index, start in enumerate(range(0, len(rendered), pages_per_sheet)):
        chunk = rendered[start : start + pages_per_sheet]
        label_height = 22
        gap = 8
        width = max(image.width for _, image in chunk)
        height = sum(label_height + image.height + gap for _, image in chunk) - gap
        sheet = Image.new("RGB", (width, height), (235, 235, 235))
        draw = ImageDraw.Draw(sheet)
        y = 0
        for label, image in chunk:
            draw.text((4, y + 3), label, fill=(0, 0, 0))
            y += label_height
            sheet.paste(image, (0, y))
            y += image.height + gap
        sheet_path = out_dir / f"{ownership}_{sheet_index:02d}.png"
        sheet.save(sheet_path)
        sheets.append(sheet_path)
    return sheets


def render_address_pages(
    rom: bytes,
    addresses: list[int],
    out_dir: Path,
    *,
    scale: int,
    cols: int,
    pages_per_sheet: int,
) -> list[Path]:
    ownership = "direct_record"
    page_dir = out_dir / ownership
    page_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[tuple[str, Image.Image]] = []
    for index, address in enumerate(addresses):
        page_path = page_dir / f"{index:03d}_{address:06X}.png"
        render_text_sample(
            rom,
            read_direct_tokens(rom, address),
            JP_FONT_BASE,
            "jp2bpp16",
            scale,
            cols,
            page_path,
        )
        rendered.append((f"{index:03d} 0x{address:06X}", Image.open(page_path).convert("RGB")))

    sheets: list[Path] = []
    for sheet_index, start in enumerate(range(0, len(rendered), pages_per_sheet)):
        chunk = rendered[start : start + pages_per_sheet]
        label_height = 22
        gap = 8
        width = max(image.width for _, image in chunk)
        height = sum(label_height + image.height + gap for _, image in chunk) - gap
        sheet = Image.new("RGB", (width, height), (235, 235, 235))
        draw = ImageDraw.Draw(sheet)
        y = 0
        for label, image in chunk:
            draw.text((4, y + 3), label, fill=(0, 0, 0))
            y += label_height
            sheet.paste(image, (0, y))
            y += image.height + gap
        sheet_path = out_dir / f"direct_record_{sheet_index:02d}.png"
        sheet.save(sheet_path)
        sheets.append(sheet_path)
    return sheets


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render classified direct-string inventory pages with addresses"
    )
    parser.add_argument(
        "--rom",
        type=Path,
        default=Path("roms/original/Langrisser II (Japan).md"),
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("localization/direct_word_candidates.json"),
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--ownership")
    source.add_argument("--address", action="append", type=parse_int)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("captures/analysis/direct_inventory_pages"),
    )
    parser.add_argument("--scale", type=parse_int, default=2)
    parser.add_argument("--cols", type=parse_int, default=32)
    parser.add_argument("--pages-per-sheet", type=parse_int, default=12)
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    rom = args.rom.read_bytes()
    if args.address:
        sheets = render_address_pages(
            rom,
            args.address,
            args.out_dir,
            scale=args.scale,
            cols=args.cols,
            pages_per_sheet=args.pages_per_sheet,
        )
        source_label = f"{len(args.address)} direct records"
    else:
        sheets = render_inventory_pages(
            rom,
            inventory,
            args.ownership,
            args.out_dir,
            scale=args.scale,
            cols=args.cols,
            pages_per_sheet=args.pages_per_sheet,
        )
        source_label = str(args.ownership)
    print(f"rendered {source_label} to {args.out_dir}")
    for path in sheets:
        print(path)


if __name__ == "__main__":
    main()
