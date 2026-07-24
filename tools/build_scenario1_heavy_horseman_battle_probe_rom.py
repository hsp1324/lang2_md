#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_scenario1_clear_probe_rom as scenario1
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT
    / "roms/builds/Langrisser II (Scenario 1 Heavy Horseman Battle Probe).md"
)

LAIRD_RECORD_INDEX = 10
LAIRD_RECORD_OFFSET = 0x180320
LAIRD_NAME_ID = 0x11
LAIRD_CLASS_ID = 0x37
HEAVY_HORSEMAN_ID = 0x7A
PROBE_LAIRD_X = 11
PROBE_LAIRD_Y = 15
HIDDEN_UNRELATED_ENEMY_RECORD_INDEXES = (8, 9, 11)


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, scenario1.SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, scenario1.SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 1 layout differs from Japanese source")
    if source_layout.header_offset != scenario1.SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 1 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 12:
        raise ValueError(
            f"unexpected Scenario 1 fixed record count {source_layout.record_count}"
        )
    laird = source_layout.records_offset + LAIRD_RECORD_INDEX * FIXED_RECORD_SIZE
    if laird != LAIRD_RECORD_OFFSET:
        raise ValueError(f"unexpected Laird record 0x{laird:06X}")

    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[laird + FIELD_OFFSETS["name_id"]] != LAIRD_NAME_ID:
            raise ValueError(f"{label} Laird name ID differs")
        if data[laird + FIELD_OFFSETS["class_id"]] != LAIRD_CLASS_ID:
            raise ValueError(f"{label} Laird class ID differs")
        mercenary_offset = laird + FIELD_OFFSETS["mercenaries"]
        if data[mercenary_offset : mercenary_offset + 6] != bytes(
            [HEAVY_HORSEMAN_ID, HEAVY_HORSEMAN_ID, 0xFF, 0xFF, 0xFF, 0xFF]
        ):
            raise ValueError(f"{label} Laird mercenaries differ")

    records_start = source_layout.records_offset
    records_end = records_start + source_layout.record_count * FIXED_RECORD_SIZE
    if probe[records_start:records_end] != source[records_start:records_end]:
        raise ValueError("input Scenario 1 fixed records differ from Japanese source")


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, scenario1.SCENARIO_NUMBER)
    for record_index in HIDDEN_UNRELATED_ENEMY_RECORD_INDEXES:
        base = layout.records_offset + record_index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["x"]] = 0xFF
        probe[base + FIELD_OFFSETS["y"]] = 0xFF

    probe[LAIRD_RECORD_OFFSET + FIELD_OFFSETS["x"]] = PROBE_LAIRD_X
    probe[LAIRD_RECORD_OFFSET + FIELD_OFFSETS["y"]] = PROBE_LAIRD_Y
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 1 probe that keeps the Japanese Laird "
            "record and both Heavy Horseman mercenaries, stages that group near "
            "Elwin, and hides unrelated fixed records"
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
        "Scenario 1 source Laird group: "
        f"({PROBE_LAIRD_X},{PROBE_LAIRD_Y}), "
        "two source 0x7A Heavy Horseman mercenaries"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
