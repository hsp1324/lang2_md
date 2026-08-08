#!/usr/bin/env python3
"""Build a minimal Scenario 6 Rune Stone live-play probe.

The production v1.3.2 ROM expands the hidden-item trigger from the occupied
well cell (5,4) through the reachable right approach at (7,4). This diagnostic
changes only Elwin's Scenario 6 deployment to (6,4), allowing one ordinary
rightward move to prove the production trigger in BlastEm without altering any
event or NPC record.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.scenario_data import scenario_layout


DEFAULT_INPUT = ROOT / "roms/builds/Langrisser II (Korean).md"
DEFAULT_SOURCE = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_OUTPUT = ROOT / "roms/builds/Langrisser II (Scenario 6 Rune Stone Probe).md"
SCENARIO_NUMBER = 6
DEPLOYMENT_POINTER_OFFSET = 0x08
FIRST_PLAYER_DEPLOYMENT = 0x1809D2
SOURCE_FIRST_PLAYER_COORDINATE = bytes.fromhex("00 04 00 1A")
PROBE_FIRST_PLAYER_COORDINATE = bytes.fromhex("00 06 00 04")


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def build_probe(input_rom: bytes, source_rom: bytes) -> bytearray:
    source_layout = scenario_layout(source_rom, SCENARIO_NUMBER)
    input_layout = scenario_layout(input_rom, SCENARIO_NUMBER)
    if source_layout != input_layout:
        raise ValueError("Scenario 6 layout differs from Japanese source")
    deployment_table = be32(
        source_rom,
        source_layout.header_offset + DEPLOYMENT_POINTER_OFFSET,
    )
    if deployment_table + 2 != FIRST_PLAYER_DEPLOYMENT:
        raise ValueError(
            "unexpected Scenario 6 deployment table "
            f"0x{deployment_table:06X}"
        )
    end = FIRST_PLAYER_DEPLOYMENT + len(SOURCE_FIRST_PLAYER_COORDINATE)
    for label, data in (
        ("Japanese source", source_rom),
        ("production input", input_rom),
    ):
        if data[FIRST_PLAYER_DEPLOYMENT:end] != SOURCE_FIRST_PLAYER_COORDINATE:
            raise ValueError(f"{label} Scenario 6 Elwin deployment changed")
    trigger = builder.SCENARIO6_RUNESTONE_TRIGGER
    trigger_end = trigger + len(
        builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE
    )
    if (
        input_rom[trigger:trigger_end]
        != builder.SCENARIO6_RUNESTONE_TRIGGER_ACCESSIBLE
    ):
        raise ValueError("input ROM does not contain the v1.3.2 Rune Stone trigger")

    probe = bytearray(input_rom)
    probe[FIRST_PLAYER_DEPLOYMENT:end] = PROBE_FIRST_PLAYER_COORDINATE
    builder.update_md_checksum(probe)
    return probe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    probe = build_probe(args.input.read_bytes(), args.source.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(probe)
    print(f"wrote {args.out}")
    print("only Scenario 6 Elwin deployment changed: (4,26) -> (6,4)")
    print(f"checksum: {int.from_bytes(probe[0x18E:0x190], 'big'):04X}")


if __name__ == "__main__":
    main()
