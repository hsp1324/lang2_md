#!/usr/bin/env python3
"""Build the narrow B1.0.3 playtest update from the B1.0.2 release ROM.

The update relocates dynamic glyph slot 5 away from the Ballista hiring icon
and fixes the independently stored hard-build version shown on the title
screen. It intentionally preserves all translation, design, balance, and save
format bytes inherited from B1.0.2.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


SOURCE_ROM = ROOT / "roms/releases/Langrisser II (Korean Hard T1.0.1 B1.0.2).md"
OUTPUT_ROM = ROOT / "roms/releases/Langrisser II (Korean Hard T1.0.1 B1.0.3).md"
SOURCE_SHA256 = "b160e2e703a78b43b7f1e3a39d51225c7bd9e3bf8dff92ecdd17e1e07efaa132"
SOURCE_BUILD = "1.0.2"
TARGET_BUILD = "1.0.3"
SOURCE_VISIBLE_BUILD = "1.0.1"
SLOT = 5
OLD_TILE = 0x036D
NEW_TILE = 0x07F0
SOURCE_HEADER = "LANGRISSER II KOREAN T1.0.1 B1.0.2 BY HSP1324"
TARGET_HEADER = "LANGRISSER II KOREAN T1.0.1 B1.0.3 BY HSP1324"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def vdp_write_command(tile: int) -> int:
    address = tile * 32
    return ((0x4000 | (address & 0x3FFF)) << 16) | ((address >> 14) & 3)


def build(source: bytes) -> bytes:
    if sha256(source) != SOURCE_SHA256:
        raise ValueError("B1.0.3 must be based on the exact B1.0.2 release ROM")

    data = bytearray(source)
    header_slice = slice(
        builder.MD_HEADER_INTERNATIONAL_TITLE,
        builder.MD_HEADER_INTERNATIONAL_TITLE + builder.MD_HEADER_TITLE_SIZE,
    )
    if data[header_slice].decode("ascii").rstrip() != SOURCE_HEADER:
        raise ValueError("B1.0.2 ROM header title changed")

    command_offset = builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + SLOT * 4
    tile_offset = builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + SLOT * 2
    if builder.be32(data, command_offset) != vdp_write_command(OLD_TILE):
        raise ValueError("B1.0.2 dynamic slot 5 VDP command changed")
    if builder.be16(data, tile_offset) != OLD_TILE:
        raise ValueError("B1.0.2 dynamic slot 5 tile ID changed")

    source_title_record = builder.build_title_version_record(
        f"하드:{SOURCE_VISIBLE_BUILD}"
    )
    target_title_record = builder.build_title_version_record(
        f"하드:{TARGET_BUILD}"
    )
    title_offset = builder.TITLE_HARD_BALANCE_TEXT_RECORD
    title_end = title_offset + len(source_title_record)
    if bytes(data[title_offset:title_end]) != source_title_record:
        raise ValueError("B1.0.2 visible hard-build title record changed")
    if len(target_title_record) != len(source_title_record):
        raise ValueError("B1.0.3 title record unexpectedly changed size")

    header = TARGET_HEADER.encode("ascii")
    data[header_slice] = header.ljust(builder.MD_HEADER_TITLE_SIZE, b" ")
    builder.put32(data, command_offset, vdp_write_command(NEW_TILE))
    builder.put16(data, tile_offset, NEW_TILE)
    data[title_offset:title_end] = target_title_record
    builder.update_md_checksum(data)
    return bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROM)
    args = parser.parse_args()

    output = build(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    checksum = int.from_bytes(output[0x18E:0x190], "big")
    print(args.output)
    print(f"sha256={sha256(output)}")
    print(f"md_checksum={checksum:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
