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
    ROOT / "roms/builds/Langrisser II (Scenario 8 Clear Probe).md"
)

SCENARIO_NUMBER = 8
SCENARIO_HEADER = 0x180DA6
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x180DC6
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0002 0007")
KRAMER_RECORD_INDEX = 5
KRAMER_RECORD_OFFSET = 0x180E9A
SOURCE_KRAMER_X = 38
SOURCE_KRAMER_Y = 8
PROBE_KRAMER_X = 2
PROBE_KRAMER_Y = 6
PROBE_KRAMER_AT = 0
PROBE_KRAMER_DF = 0


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 8 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 8 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 8 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 8 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
            ]
            != SOURCE_FIRST_PLAYER_DEPLOYMENT
        ):
            raise ValueError(f"{label} first player deployment is not (2,7)")

    record_offset = (
        source_layout.records_offset + KRAMER_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != KRAMER_RECORD_OFFSET:
        raise ValueError(f"unexpected Kramer record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Kramer record differs from Japanese source")
    if (
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_KRAMER_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_KRAMER_Y
    ):
        raise ValueError("unexpected Japanese Scenario 8 Kramer coordinates")


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    base = KRAMER_RECORD_OFFSET
    probe[base + FIELD_OFFSETS["at"]] = PROBE_KRAMER_AT
    probe[base + FIELD_OFFSETS["df"]] = PROBE_KRAMER_DF
    probe[base + FIELD_OFFSETS["x"]] = PROBE_KRAMER_X
    probe[base + FIELD_OFFSETS["y"]] = PROBE_KRAMER_Y
    mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
    probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 8 ROM with an unguarded Kramer next to "
            "the stock Elwin deployment for a normal-command completion"
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
        f"Scenario 8 Kramer: ({PROBE_KRAMER_X},{PROBE_KRAMER_Y}), "
        "AT 0, DF 0, no mercenaries"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
