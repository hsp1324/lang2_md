#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 7 Clear Probe).md"
)

SCENARIO_NUMBER = 7
SCENARIO_HEADER = 0x180BBC
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x180BDA
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0007 0014")
GINAM_RECORD_INDEX = 4
GINAM_RECORD_OFFSET = 0x180C86
SOURCE_GINAM_X = 6
SOURCE_GINAM_Y = 6
PROBE_GINAM_X = 7
PROBE_GINAM_Y = 19
PROBE_GINAM_AT = 0
PROBE_GINAM_DF = 0


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 7 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 7 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 12:
        raise ValueError(
            f"unexpected Scenario 7 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 7 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
            ]
            != SOURCE_FIRST_PLAYER_DEPLOYMENT
        ):
            raise ValueError(f"{label} first player deployment is not (7,20)")

    record_offset = (
        source_layout.records_offset + GINAM_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != GINAM_RECORD_OFFSET:
        raise ValueError(f"unexpected Ginam record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Ginam record differs from Japanese source")
    if (
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_GINAM_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_GINAM_Y
    ):
        raise ValueError("unexpected Japanese Scenario 7 Ginam coordinates")


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    base = GINAM_RECORD_OFFSET
    probe[base + FIELD_OFFSETS["at"]] = PROBE_GINAM_AT
    probe[base + FIELD_OFFSETS["df"]] = PROBE_GINAM_DF
    probe[base + FIELD_OFFSETS["x"]] = PROBE_GINAM_X
    probe[base + FIELD_OFFSETS["y"]] = PROBE_GINAM_Y
    mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
    probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 7 ROM with an unguarded Ginam next to "
            "the stock Elwin deployment for civilian-safe completion"
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
    print(
        f"Scenario 7 Ginam: ({PROBE_GINAM_X},{PROBE_GINAM_Y}), "
        "AT 0, DF 0, no mercenaries"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
