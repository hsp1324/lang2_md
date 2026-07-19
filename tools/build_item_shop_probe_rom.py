#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean All Item Shop Probe).md"
)

SHOP_LIST_SELECTOR_OFFSET = 0x027B32
SHOP_LIST_SELECTOR_SOURCE = bytes.fromhex("30 38 A4 9C")
SHOP_LIST_SELECTOR_PATCH = bytes.fromhex("30 3C 00 21")
SHOP_LIST_POINTER_TABLE = 0x0A1BB8
SHOP_LIST_COUNT = 33
ALL_ITEM_LIST_INDEX = 32
ALL_ITEM_COUNT = 37


def read_shop_list(data: bytes | bytearray, index: int) -> list[int]:
    if not 0 <= index < SHOP_LIST_COUNT:
        raise ValueError(f"shop list index must be 0..{SHOP_LIST_COUNT - 1}")
    pointer = builder.be32(data, SHOP_LIST_POINTER_TABLE + index * 4)
    items: list[int] = []
    cursor = pointer
    while cursor < len(data):
        item_id = data[cursor]
        cursor += 1
        if item_id == 0xFF:
            return items
        items.append(item_id)
    raise ValueError(f"unterminated shop list {index + 1} at 0x{pointer:06X}")


def validate_all_item_list(data: bytes | bytearray) -> list[int]:
    items = read_shop_list(data, ALL_ITEM_LIST_INDEX)
    expected = list(range(1, ALL_ITEM_COUNT + 1))
    if items != expected:
        raise ValueError(
            f"all-item shop list changed: expected {expected!r}, got {items!r}"
        )
    return items


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_all_item_list(source)
    validate_all_item_list(probe)
    offset = SHOP_LIST_SELECTOR_OFFSET
    size = len(SHOP_LIST_SELECTOR_SOURCE)
    if source[offset : offset + size] != SHOP_LIST_SELECTOR_SOURCE:
        raise ValueError("Japanese shop-list selector changed")
    if probe[offset : offset + size] != SHOP_LIST_SELECTOR_SOURCE:
        raise ValueError("input shop-list selector changed")
    probe[offset : offset + size] = SHOP_LIST_SELECTOR_PATCH
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored diagnostic ROM that displays original shop list "
            "33, containing item IDs 1..37, through the stock purchase renderer"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(probe, source)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print("stock shop list 33 enabled: item IDs 1..37")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
