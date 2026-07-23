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
    ROOT / "roms/builds/Langrisser II (Scenario 11 Clear Probe).md"
)

SCENARIO_NUMBER = 11
SCENARIO_HEADER = 0x18138E
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x1813AC
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
PLAYER_DEPLOYMENT_COUNT = 6
SOURCE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("000E 000A")
SAFE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0012 0014")
SAFE_PLAYER_DEPLOYMENTS = (
    (18, 20),
    (17, 20),
    (19, 20),
    (18, 19),
    (17, 19),
    (19, 19),
)
JESSICA_RECORD_INDEX = 0
SAFE_JESSICA_POSITION = (18, 18)
LIVE_VERIFIED_SAFE_JESSICA_CHECKSUM = 0xD091
EXPECTED_SAFE_JESSICA_CHECKSUM = 0x3A72
FIRST_ENEMY_RECORD_INDEX = 1
LAST_ENEMY_RECORD_INDEX = 10
PROBE_AT = 0
PROBE_DF = 0
SAFE_CLEAR_ENEMY_LEVEL = 0
SAFE_CLEAR_ENEMY_CLASS = 0x01
SAFE_CLEAR_VISIBLE_POSITIONS = {
    # Egbert must be immediately attackable before his scripted retreat.
    # Keeping him two cells away requires moving Elwin into the fire-event
    # area and makes the completion probe unnecessarily timing-sensitive.
    1: (18, 21),
    2: (17, 21),
    3: (19, 21),
    4: (16, 20),
    5: (20, 20),
    6: (16, 19),
    7: (20, 19),
    8: (17, 18),
    9: (19, 18),
}


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 11 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 11 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 11 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 11 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
            ]
            != SOURCE_FIRST_PLAYER_DEPLOYMENT
        ):
            raise ValueError(f"{label} first player deployment is not (14,10)")

    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 11 enemy record {index} differs from Japanese source"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    safe_elwin: bool = False,
    safe_clear_layout: bool = False,
    safe_jessica: bool = False,
) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    if safe_elwin:
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
        ] = SAFE_FIRST_PLAYER_DEPLOYMENT
    if safe_clear_layout:
        for index, (x, y) in enumerate(SAFE_PLAYER_DEPLOYMENTS):
            offset = FIRST_PLAYER_DEPLOYMENT_OFFSET + index * 4
            probe[offset : offset + 2] = x.to_bytes(2, "big")
            probe[offset + 2 : offset + 4] = y.to_bytes(2, "big")
        for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[base + FIELD_OFFSETS["level"]] = SAFE_CLEAR_ENEMY_LEVEL
            probe[base + FIELD_OFFSETS["class_id"]] = SAFE_CLEAR_ENEMY_CLASS
        for index, (x, y) in SAFE_CLEAR_VISIBLE_POSITIONS.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[base + FIELD_OFFSETS["x"]] = x
            probe[base + FIELD_OFFSETS["y"]] = y
    if safe_jessica:
        base = layout.records_offset + JESSICA_RECORD_INDEX * FIXED_RECORD_SIZE
        x, y = SAFE_JESSICA_POSITION
        probe[base + FIELD_OFFSETS["x"]] = x
        probe[base + FIELD_OFFSETS["y"]] = y
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 11 ROM with weakened Imperial groups "
            "while preserving Jessica and all scenario events"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--safe-elwin",
        action="store_true",
        help=(
            "diagnostic completion route only: move Elwin from (14,10) to "
            "(18,20), beyond the turn-5 fire spread"
        ),
    )
    parser.add_argument(
        "--safe-clear-layout",
        action="store_true",
        help=(
            "diagnostic completion route only: set enemy levels to zero and "
            "classes to Fighter, then place all selectable commanders and "
            "visible enemies in a compact southern assault layout"
        ),
    )
    parser.add_argument(
        "--safe-jessica",
        action="store_true",
        help=(
            "diagnostic completion route only: move Jessica from the "
            "turn-eight fire area to the compact southern battle area"
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
        safe_elwin=args.safe_elwin,
        safe_clear_layout=args.safe_clear_layout,
        safe_jessica=args.safe_jessica,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print(
        "Scenario 11 Jessica and events preserved; enemy records 1..10: "
        "AT 0, DF 0, no mercenaries"
    )
    if args.safe_clear_layout:
        print("diagnostic player assault deployment moved south")
        print(
            "diagnostic enemy levels: 0; classes: Fighter; "
            "player and visible-enemy assault layout moved south"
        )
    else:
        if args.safe_elwin:
            print("diagnostic Elwin deployment: (14,10) -> (18,20)")
        else:
            print("stock Elwin deployment preserved: (14,10)")
        print("stock enemy levels and coordinates preserved")
    if args.safe_jessica:
        print("diagnostic Jessica deployment moved to (18,18)")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
