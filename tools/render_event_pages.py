#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.jp_text_font_analyzer import JP_FONT_BASE, render_text_sample
except ModuleNotFoundError:  # Support `python3 tools/render_event_pages.py`.
    from jp_text_font_analyzer import JP_FONT_BASE, render_text_sample


def parse_int(text: str) -> int:
    return int(text, 0)


def parse_tokens(text: str) -> list[int]:
    return [int(value, 16) for value in text.split()]


def render_scenario_pages(
    rom: bytes,
    scenario: dict[str, object],
    out_dir: Path,
    *,
    scale: int,
    cols: int,
    pages_per_sheet: int,
) -> list[Path]:
    number = int(scenario["scenario"])
    page_dir = out_dir / f"scenario_{number:02d}"
    page_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[tuple[str, Image.Image]] = []
    physical_pages = [
        physical
        for page in scenario["pages"]
        for physical in page.get("physical_pages", [page])
    ]
    for page_index, page in enumerate(physical_pages):
        address = str(page["address"])
        tokens = parse_tokens(str(page["tokens"]))
        page_path = page_dir / f"{page_index:03d}_{address[2:]}.png"
        render_text_sample(
            rom,
            tokens,
            JP_FONT_BASE,
            "jp2bpp16",
            scale,
            cols,
            page_path,
        )
        rendered.append((f"{page_index:03d} {address}", Image.open(page_path).convert("RGB")))

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
        sheet_path = out_dir / f"scenario_{number:02d}_pages_{sheet_index:02d}.png"
        sheet.save(sheet_path)
        sheets.append(sheet_path)
    return sheets


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Japanese event-page candidates with addresses")
    parser.add_argument("--rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument("--inventory", type=Path, default=Path("localization/event_pages.json"))
    parser.add_argument("--scenario", type=int, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("captures/analysis/event_pages"))
    parser.add_argument("--scale", type=parse_int, default=2)
    parser.add_argument("--cols", type=parse_int, default=32)
    parser.add_argument("--pages-per-sheet", type=parse_int, default=12)
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    if not 1 <= args.scenario <= int(inventory["scenario_count"]):
        raise ValueError(f"scenario must be 1..{inventory['scenario_count']}")
    scenario = inventory["scenarios"][args.scenario - 1]
    sheets = render_scenario_pages(
        args.rom.read_bytes(),
        scenario,
        args.out_dir,
        scale=args.scale,
        cols=args.cols,
        pages_per_sheet=args.pages_per_sheet,
    )
    print(f"rendered {scenario['physical_page_count']} physical pages to {args.out_dir}")
    for path in sheets:
        print(path)


if __name__ == "__main__":
    main()
