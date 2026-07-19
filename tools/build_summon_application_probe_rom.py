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
    ROOT / "roms/builds/Langrisser II (Korean Summon Apply Probe).md"
)

SUMMON_COMMAND_BRANCH_OFFSET = 0x020DFA
SUMMON_COMMAND_BRANCH_SOURCE = bytes.fromhex("67 1C")
SUMMON_COMMAND_BRANCH_PATCH = bytes.fromhex("4E 71")
ALL_SUMMON_BRANCH_OFFSET = 0x021724
ALL_SUMMON_BRANCH_SOURCE = bytes.fromhex("67 00 00 1A")
ALL_SUMMON_BRANCH_PATCH = bytes.fromhex("4E 71 4E 71")
SUMMON_MP_BRANCH_OFFSET = 0x021938
SUMMON_MP_BRANCH_SOURCE = bytes.fromhex("66 00 00 CE")
SUMMON_MP_BRANCH_PATCH = bytes.fromhex("60 00 00 CE")


def patch_probe(probe: bytearray, source: bytes) -> int:
    patches = (
        (
            "summon command branch",
            SUMMON_COMMAND_BRANCH_OFFSET,
            SUMMON_COMMAND_BRANCH_SOURCE,
            SUMMON_COMMAND_BRANCH_PATCH,
        ),
        (
            "all-summon list branch",
            ALL_SUMMON_BRANCH_OFFSET,
            ALL_SUMMON_BRANCH_SOURCE,
            ALL_SUMMON_BRANCH_PATCH,
        ),
        (
            "summon MP branch",
            SUMMON_MP_BRANCH_OFFSET,
            SUMMON_MP_BRANCH_SOURCE,
            SUMMON_MP_BRANCH_PATCH,
        ),
    )
    for label, offset, expected, replacement in patches:
        if source[offset : offset + len(expected)] != expected:
            raise ValueError(f"Japanese {label} changed")
        if probe[offset : offset + len(expected)] != expected:
            raise ValueError(f"input {label} changed")
        probe[offset : offset + len(replacement)] = replacement
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored diagnostic ROM that offers Summon on Hein, "
            "exposes all eight summon IDs, and accepts a selected summon"
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
    print("summon command and all eight summon IDs enabled for diagnostics")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
