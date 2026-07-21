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
    ROOT / "roms/builds/Langrisser II (Scenario 12 Clear Probe).md"
)

SCENARIO_NUMBER = 12
SCENARIO_HEADER = 0x181554
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x181574
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
PLAYER_DEPLOYMENT_COUNT = 7
SOURCE_PLAYER_DEPLOYMENTS = (
    (15, 23),
    (7, 28),
    (10, 27),
    (15, 26),
    (20, 27),
    (23, 28),
    (15, 29),
)
COMPACT_PLAYER_DEPLOYMENTS = (
    (15, 20),
    (14, 20),
    (16, 20),
    (15, 21),
    (14, 21),
    (16, 21),
    (15, 22),
)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 10
LAST_VISIBLE_ENEMY_RECORD_INDEX = 9
COMPACT_VISIBLE_ENEMY_POSITIONS = {
    0: (15, 19),
    1: (14, 19),
    2: (16, 19),
    3: (13, 20),
    4: (17, 20),
    5: (13, 21),
    6: (17, 21),
    7: (13, 22),
    8: (17, 22),
    9: (14, 22),
}
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
        raise ValueError("Scenario 12 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 12 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 12 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 12 deployment table")
    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected_deployments)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected_deployments:
            raise ValueError(f"{label} Scenario 12 player deployments differ")
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 12 enemy record {index} differs from Japanese source"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    compact_layout: bool = False,
) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        start = base + FIELD_OFFSETS["mercenaries"]
        probe[start : start + 6] = b"\xFF" * 6
    if compact_layout:
        positions = deployment_bytes(COMPACT_PLAYER_DEPLOYMENTS)
        end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(positions)
        probe[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] = positions
        for index, (x, y) in COMPACT_VISIBLE_ENEMY_POSITIONS.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[base + FIELD_OFFSETS["x"]] = x
            probe[base + FIELD_OFFSETS["y"]] = y
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 12 ROM with weakened guardians while "
            "preserving identities, classes, levels, and all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--compact-layout",
        action="store_true",
        help=(
            "diagnostic completion route only: place the seven players and "
            "ten initially visible guardians in a compact central layout; "
            "event camera transitions can expose map sprites over the HUD, "
            "so use the default stock-coordinate probe for UI evidence"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(probe, source, compact_layout=args.compact_layout)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print("Scenario 12 enemy records 0..10: AT 0, DF 0, no mercenaries")
    if args.compact_layout:
        print("diagnostic player and visible-guardian layout moved to the center")
    else:
        print("stock player and enemy coordinates preserved")
    print("identities, classes, levels, hidden state, and events preserved")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
