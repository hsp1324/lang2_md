#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_scenario1_clear_probe_rom as clear_probe
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


DEFAULT_INPUT_ROM = clear_probe.DEFAULT_OUTPUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 1 Great Slime Status Probe).md"
)

SOURCE_SCENARIO_NUMBER = 10
SOURCE_GREAT_SLIME_RECORD_INDEX = 8
SOURCE_GREAT_SLIME_RECORD_OFFSET = 0x1812DA
SOURCE_GREAT_SLIME_NAME_ID = 58
SOURCE_GREAT_SLIME_CLASS_ID = 81


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, clear_probe.SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, clear_probe.SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 1 layout differs from Japanese source")
    if source_layout.header_offset != clear_probe.SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 1 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 12:
        raise ValueError(
            f"unexpected Scenario 1 fixed record count {source_layout.record_count}"
        )
    if (
        clear_probe.be32(
            source,
            clear_probe.SCENARIO_HEADER + clear_probe.DEPLOYMENT_POINTER_OFFSET,
        )
        != clear_probe.DEPLOYMENT_TABLE
    ):
        raise ValueError("unexpected Japanese Scenario 1 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        start = clear_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET
        if data[start : start + 4] != clear_probe.FIRST_PLAYER_DEPLOYMENT:
            raise ValueError(f"{label} first player deployment is not (11,17)")

    target = clear_probe.BALD_RECORD_OFFSET
    expected_target = bytearray(
        source[target : target + FIXED_RECORD_SIZE]
    )
    expected_target[FIELD_OFFSETS["at"]] = clear_probe.PROBE_BALD_AT
    expected_target[FIELD_OFFSETS["df"]] = clear_probe.PROBE_BALD_DF
    expected_target[FIELD_OFFSETS["x"]] = clear_probe.PROBE_BALD_X
    expected_target[FIELD_OFFSETS["y"]] = clear_probe.PROBE_BALD_Y
    mercenary_offset = FIELD_OFFSETS["mercenaries"]
    expected_target[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    if probe[target : target + FIXED_RECORD_SIZE] != expected_target:
        raise ValueError("input Bald record is not the Scenario 1 clear probe")

    source_layout = scenario_layout(source, SOURCE_SCENARIO_NUMBER)
    source_record = (
        source_layout.records_offset
        + SOURCE_GREAT_SLIME_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if source_record != SOURCE_GREAT_SLIME_RECORD_OFFSET:
        raise ValueError(
            f"unexpected Great Slime record 0x{source_record:06X}"
        )
    if source[source_record + FIELD_OFFSETS["name_id"]] != SOURCE_GREAT_SLIME_NAME_ID:
        raise ValueError("unexpected Japanese Great Slime name ID")
    if source[source_record + FIELD_OFFSETS["class_id"]] != SOURCE_GREAT_SLIME_CLASS_ID:
        raise ValueError("unexpected Japanese Great Slime class ID")


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    target = clear_probe.BALD_RECORD_OFFSET
    source_record = SOURCE_GREAT_SLIME_RECORD_OFFSET
    probe[target + FIELD_OFFSETS["name_id"]] = source[
        source_record + FIELD_OFFSETS["name_id"]
    ]
    probe[target + FIELD_OFFSETS["class_id"]] = source[
        source_record + FIELD_OFFSETS["class_id"]
    ]
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 1 display probe that gives the adjacent "
            "clear-probe target the stock Scenario 10 Great Slime name/class"
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
        "Scenario 1 clear-probe target: stock Scenario 10 Great Slime "
        f"name/class at ({clear_probe.PROBE_BALD_X},{clear_probe.PROBE_BALD_Y})"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
