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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 31 Clear Probe).md"
SCENARIO_NUMBER = 31
SCENARIO_HEADER = 0x18376C
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x183792
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (14, 61),
    (16, 61),
    (5, 56),
    (5, 46),
    (25, 46),
    (25, 36),
    (25, 26),
    (5, 26),
    (5, 16),
    (25, 16),
)
FIRST_COMBAT_RECORD_INDEX = 0
LAST_COMBAT_RECORD_INDEX = 9
VARGAS_RECORD_INDEX = 0
LEON_RECORD_INDEX = 3
LAIRD_RECORD_INDEX = 4
EGBERT_RECORD_INDEX = 5
BOZEL_RECORD_INDEX = 7
BERNHARDT_RECORD_INDEX = 9
PROBE_AT = 0
PROBE_DF = 0


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 31 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 31 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 31 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 31 deployment table")
    expected = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 31 player deployments differ")
    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 31 fixed record {index} differs from Japanese source"
            )


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_COMBAT_RECORD_INDEX, LAST_COMBAT_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenaries = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 31 ROM with weakened enemy/special "
            "combat groups while preserving stock deployments, commander "
            "identities, classes, and event handlers"
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
    print("Scenario 31 combat records 0..9: AT 0, DF 0, no mercenaries")
    print(
        "stock deployments, side IDs, commander identities, classes, "
        "coordinates, and all handlers preserved"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
