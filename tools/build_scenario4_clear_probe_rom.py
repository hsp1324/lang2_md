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
    ROOT / "roms/builds/Langrisser II (Scenario 4 Clear Probe).md"
)
DEFAULT_PROGRESSION_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 4 Progression Probe).md"
)

SCENARIO_NUMBER = 4
SCENARIO_HEADER = 0x180688
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x1806A0
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0007 0026")
PROBE_FIRST_PLAYER_X = 7
PROBE_FIRST_PLAYER_Y = 22
MORGAN_RECORD_INDEX = 7
MORGAN_RECORD_OFFSET = 0x1807AC
SOURCE_MORGAN_X = 7
SOURCE_MORGAN_Y = 21
PROBE_MORGAN_AT = 0
PROBE_MORGAN_DF = 0
FIRST_ENEMY_RECORD_INDEX = 5
LAST_ENEMY_RECORD_INDEX = 10
PROGRESSION_ENEMY_AT = 0
PROGRESSION_ENEMY_DF = 0


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 4 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 4 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 4 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 4 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
            ]
            != SOURCE_FIRST_PLAYER_DEPLOYMENT
        ):
            raise ValueError(f"{label} first player deployment is not (7,38)")

    record_offset = (
        source_layout.records_offset + MORGAN_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != MORGAN_RECORD_OFFSET:
        raise ValueError(f"unexpected Morgan record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Morgan record differs from Japanese source")
    if (
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_MORGAN_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_MORGAN_Y
    ):
        raise ValueError("unexpected Japanese Scenario 4 Morgan coordinates")


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    probe[
        FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
    ] = bytes.fromhex(
        f"{PROBE_FIRST_PLAYER_X:04X} {PROBE_FIRST_PLAYER_Y:04X}"
    )
    base = MORGAN_RECORD_OFFSET
    probe[base + FIELD_OFFSETS["at"]] = PROBE_MORGAN_AT
    probe[base + FIELD_OFFSETS["df"]] = PROBE_MORGAN_DF
    mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
    probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def patch_progression_probe(probe: bytearray, source: bytes) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 4 enemy record {index} differs from Japanese source"
            )
        probe[base + FIELD_OFFSETS["at"]] = PROGRESSION_ENEMY_AT
        probe[base + FIELD_OFFSETS["df"]] = PROGRESSION_ENEMY_DF
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 4 ROM with Elwin adjacent to an "
            "unguarded Morgan for stock completion-dialogue tests"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument(
        "--mode",
        choices=("clear", "progression"),
        default="clear",
        help="clear moves Elwin next to Morgan; progression preserves all coordinates",
    )
    parser.add_argument("--output-rom", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    if args.mode == "progression":
        checksum = patch_progression_probe(probe, source)
        output_rom = args.output_rom or DEFAULT_PROGRESSION_OUTPUT_ROM
        print(
            "Scenario 4 original coordinates preserved; enemy records "
            f"{FIRST_ENEMY_RECORD_INDEX}..{LAST_ENEMY_RECORD_INDEX}: "
            "AT 0, DF 0, no mercenaries"
        )
    else:
        checksum = patch_probe(probe, source)
        output_rom = args.output_rom or DEFAULT_OUTPUT_ROM
        print(
            f"Scenario 4 Elwin: ({PROBE_FIRST_PLAYER_X},{PROBE_FIRST_PLAYER_Y}); "
            f"Morgan: ({SOURCE_MORGAN_X},{SOURCE_MORGAN_Y}), "
            "AT 0, DF 0, no mercenaries"
        )
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)
    print(f"checksum: {checksum:04X}")
    print(output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
