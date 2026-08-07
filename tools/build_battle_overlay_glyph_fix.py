#!/usr/bin/env python3
"""Relocate battle glyph slots that can still collide with target cursors."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


DEFAULT_INPUT = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
DEFAULT_OUTPUT = ROOT / "tmp/current-battle-overlay-fix-normal.md"
RELOCATIONS = (
    (4, 0x07D0, 0x07EA),
    (6, 0x07D1, 0x07EC),
    (9, 0x07E0, 0x07F2),
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def vdp_write_command(tile: int) -> int:
    address = tile * 32
    return ((0x4000 | (address & 0x3FFF)) << 16) | ((address >> 14) & 3)


def patch(data: bytearray) -> int:
    for slot, old_tile, new_tile in RELOCATIONS:
        command = builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + slot * 4
        tile_id = builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + slot * 2
        current_tile = builder.be16(data, tile_id)
        if current_tile == new_tile:
            continue
        if current_tile != old_tile:
            raise ValueError(f"battle slot {slot} tile ID changed")
        if builder.be32(data, command) != vdp_write_command(old_tile):
            raise ValueError(f"battle slot {slot} VDP command changed")
        builder.put32(data, command, vdp_write_command(new_tile))
        builder.put16(data, tile_id, new_tile)
    return builder.update_md_checksum(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = bytearray(args.input_rom.read_bytes())
    checksum = patch(data)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(data)
    print(args.output_rom)
    print(f"sha256={sha256(data)}")
    print(f"md_checksum={checksum:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
