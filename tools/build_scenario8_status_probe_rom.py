#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_scenario8_clear_probe_rom as clear_probe
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


DEFAULT_INPUT_ROM = clear_probe.DEFAULT_OUTPUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 8 Status Probe).md"
)

SCENARIO_NUMBER = 8
KRAMER_RECORD_INDEX = clear_probe.KRAMER_RECORD_INDEX
KRAMER_RECORD_OFFSET = clear_probe.KRAMER_RECORD_OFFSET
VARGAS_RECORD_INDEX = 9
VARGAS_RECORD_OFFSET = 0x180F2A


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 8 layout differs from Japanese source")
    kramer_offset = (
        source_layout.records_offset + KRAMER_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if kramer_offset != KRAMER_RECORD_OFFSET:
        raise ValueError(f"unexpected Kramer record 0x{kramer_offset:06X}")
    expected_kramer = bytearray(
        source[kramer_offset : kramer_offset + FIXED_RECORD_SIZE]
    )
    expected_kramer[FIELD_OFFSETS["at"]] = clear_probe.PROBE_KRAMER_AT
    expected_kramer[FIELD_OFFSETS["df"]] = clear_probe.PROBE_KRAMER_DF
    expected_kramer[FIELD_OFFSETS["x"]] = clear_probe.PROBE_KRAMER_X
    expected_kramer[FIELD_OFFSETS["y"]] = clear_probe.PROBE_KRAMER_Y
    mercenary_offset = FIELD_OFFSETS["mercenaries"]
    expected_kramer[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    if probe[kramer_offset : kramer_offset + FIXED_RECORD_SIZE] != expected_kramer:
        raise ValueError("input Kramer record is not the Scenario 8 clear probe")
    record_offset = (
        source_layout.records_offset + VARGAS_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != VARGAS_RECORD_OFFSET:
        raise ValueError(f"unexpected Vargas record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Vargas record differs from Japanese source")


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    probe[KRAMER_RECORD_OFFSET + FIELD_OFFSETS["name_id"]] = source[
        VARGAS_RECORD_OFFSET + FIELD_OFFSETS["name_id"]
    ]
    probe[KRAMER_RECORD_OFFSET + FIELD_OFFSETS["class_id"]] = source[
        VARGAS_RECORD_OFFSET + FIELD_OFFSETS["class_id"]
    ]
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 8 ROM that gives the relocated clear-"
            "probe Kramer the stock Vargas name/class for status validation"
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
        "Scenario 8 clear-probe target: stock Vargas name/class at "
        f"({clear_probe.PROBE_KRAMER_X},{clear_probe.PROBE_KRAMER_Y})"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
