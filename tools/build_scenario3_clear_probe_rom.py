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
    ROOT / "roms/builds/Langrisser II (Scenario 3 Clear Probe).md"
)

SCENARIO_NUMBER = 3
SCENARIO_HEADER = 0x1804F8
DEPLOYMENT_TABLE = 0x180510
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0010 0010")
FIRST_ENEMY_RECORD_INDEX = 2
LAST_ENEMY_RECORD_INDEX = 9
PROBE_AT = 90
PROBE_DF = 0
PROBE_COORDINATES = (
    (16, 15),
    (15, 15),
    (17, 15),
    (14, 15),
    (18, 15),
    (14, 16),
    (18, 16),
    (16, 14),
)


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 3 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 3 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 3 fixed record count {source_layout.record_count}"
        )
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
            ]
            != FIRST_PLAYER_DEPLOYMENT
        ):
            raise ValueError(f"{label} first player deployment is not (16,16)")
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 3 enemy record {index} differs from Japanese source"
            )


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index, (x, y) in enumerate(
        PROBE_COORDINATES, start=FIRST_ENEMY_RECORD_INDEX
    ):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        probe[base + FIELD_OFFSETS["x"]] = x
        probe[base + FIELD_OFFSETS["y"]] = y
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 3 ROM with weakened enemies placed "
            "around Elwin for stock completion-dialogue tests"
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
        f"Scenario 3 enemies: AT {PROBE_AT}, DF {PROBE_DF}, no mercenaries, "
        "placed around first Elwin deployment"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
