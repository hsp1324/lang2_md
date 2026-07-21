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
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
COMPACT_PLAYER_DEPLOYMENTS = (
    (14, 56),
    (16, 56),
    (12, 56),
    (18, 56),
    (15, 58),
    *SOURCE_PLAYER_DEPLOYMENTS[5:],
)
FIRST_COMBAT_RECORD_INDEX = 0
LAST_COMBAT_RECORD_INDEX = 9
COMPACT_COMBAT_POSITIONS = {
    0: (13, 55),
    1: (14, 55),
    2: (15, 55),
    3: (16, 55),
    4: (17, 55),
    5: (13, 56),
    6: (15, 56),
    7: (17, 56),
    8: (14, 57),
    9: (16, 57),
}
COMPLETION_SOURCE_RECORD_INDEX = 9
COMPLETION_TARGET_RECORD_INDEX = 0
COMPLETION_RECORD_COUNT = 1
COMPLETION_ACTIVE_POSITION = (14, 60)
COMPLETION_AT = 0xF4
COMPLETION_DF = 0xFC
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


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    compact_layout: bool = False,
    completion_layout: bool = False,
) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_COMBAT_RECORD_INDEX, LAST_COMBAT_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenaries = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
    if compact_layout:
        positions = deployment_bytes(COMPACT_PLAYER_DEPLOYMENTS)
        end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(positions)
        probe[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] = positions
        for index, (x, y) in COMPACT_COMBAT_POSITIONS.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[base + FIELD_OFFSETS["x"]] = x
            probe[base + FIELD_OFFSETS["y"]] = y
    elif completion_layout:
        source_record = (
            layout.records_offset
            + COMPLETION_SOURCE_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        active = (
            layout.records_offset
            + COMPLETION_TARGET_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        probe[active : active + FIXED_RECORD_SIZE] = source[
            source_record : source_record + FIXED_RECORD_SIZE
        ]
        probe[active + FIELD_OFFSETS["at"]] = COMPLETION_AT
        probe[active + FIELD_OFFSETS["df"]] = COMPLETION_DF
        mercenaries = active + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
        probe[active + FIELD_OFFSETS["x"]] = COMPLETION_ACTIVE_POSITION[0]
        probe[active + FIELD_OFFSETS["y"]] = COMPLETION_ACTIVE_POSITION[1]
        probe[layout.record_list_offset : layout.record_list_offset + 2] = (
            COMPLETION_RECORD_COUNT.to_bytes(2, "big")
        )
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
    layout_group = parser.add_mutually_exclusive_group()
    layout_group.add_argument(
        "--compact-layout",
        action="store_true",
        help=(
            "diagnostic completion route only: move the first five player "
            "deployments and all ten combat records into the source-verified "
            "lower hall; use the default probe for stock-coordinate evidence"
        ),
    )
    layout_group.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "diagnostic completion route only: move Bernhardt directly above "
            "stock Elwin and temporarily reduce the fixed combat list to "
            "that single source-copied record; "
            "use this derivative only to test the stock victory handler"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(
        probe,
        source,
        compact_layout=args.compact_layout,
        completion_layout=args.completion_layout,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.completion_layout:
        print("Scenario 31 Bernhardt: AT -12, DF -4, no mercenaries")
        print("diagnostic single-record adjacent Bernhardt layout applied")
        print("Bernhardt's source record and all scenario handlers preserved")
    elif args.compact_layout:
        print("Scenario 31 combat records 0..9: AT 0, DF 0, no mercenaries")
        print("diagnostic five-player and combat layout moved to the lower hall")
        print("side IDs, commander identities, classes, and all handlers preserved")
    else:
        print("Scenario 31 combat records 0..9: AT 0, DF 0, no mercenaries")
        print("stock player and combat coordinates preserved")
        print("side IDs, commander identities, classes, and all handlers preserved")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
