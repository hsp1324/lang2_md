#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_scenario1_clear_probe_rom as clear_probe_builder
from tools.scenario_data import FIELD_OFFSETS


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean All Magic Apply Probe).md"
)

ALL_MAGIC_BRANCH_OFFSET = 0x021228
ALL_MAGIC_BRANCH_SOURCE = bytes.fromhex("67 00 00 08")
ALL_MAGIC_BRANCH_PATCH = bytes.fromhex("4E 71 4E 71")
MAGIC_MP_BRANCH_OFFSET = 0x02141E
MAGIC_MP_BRANCH_SOURCE = bytes.fromhex("66 00 00 D2")
MAGIC_MP_BRANCH_PATCH = bytes.fromhex("60 00 00 D2")
TARGET_BALD_X = 13
TARGET_BALD_Y = 19


def place_bald_by_hein(probe: bytearray, source: bytes) -> None:
    clear_probe_builder.patch_probe(probe, source)
    base = clear_probe_builder.BALD_RECORD_OFFSET
    probe[base + FIELD_OFFSETS["x"]] = TARGET_BALD_X
    probe[base + FIELD_OFFSETS["y"]] = TARGET_BALD_Y


def patch_probe(
    probe: bytearray,
    source: bytes,
    place_target: bool = False,
    enable_all_magic: bool = True,
) -> int:
    if place_target:
        place_bald_by_hein(probe, source)
    patches = (
        (
            "all-magic list branch",
            ALL_MAGIC_BRANCH_OFFSET,
            ALL_MAGIC_BRANCH_SOURCE,
            ALL_MAGIC_BRANCH_PATCH,
        ),
        (
            "magic MP branch",
            MAGIC_MP_BRANCH_OFFSET,
            MAGIC_MP_BRANCH_SOURCE,
            MAGIC_MP_BRANCH_PATCH,
        ),
    )
    for label, offset, expected, replacement in patches:
        if source[offset : offset + len(expected)] != expected:
            raise ValueError(f"Japanese {label} changed")
        if probe[offset : offset + len(expected)] != expected:
            raise ValueError(f"input {label} changed")
        if enable_all_magic:
            probe[offset : offset + len(replacement)] = replacement
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored diagnostic ROM that exposes all 22 stock magic "
            "IDs on a unit with a magic command and bypasses MP rejection so "
            "targeting and result paths can be verified"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--place-bald-by-hein",
        action="store_true",
        help=(
            "diagnostic only: reuse the validated Scenario 1 clear probe and "
            "place unguarded Bald at (13,19), adjacent to Hein"
        ),
    )
    parser.add_argument(
        "--stock-magic",
        action="store_true",
        help="leave both magic branches stock; useful for Hein's natural Magic Arrow",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(
        probe,
        source,
        place_target=args.place_bald_by_hein,
        enable_all_magic=not args.stock_magic,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.stock_magic:
        print("stock magic ownership and MP branches preserved")
    else:
        print("all 22 magic IDs enabled; MP rejection bypassed for diagnostics")
    if args.place_bald_by_hein:
        print(f"unguarded Bald placed at ({TARGET_BALD_X},{TARGET_BALD_Y})")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
