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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 22 Clear Probe).md"
SCENARIO_NUMBER = 22
SCENARIO_HEADER = 0x182770
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x182792
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (5, 39), (16, 40), (24, 39), (5, 42),
    (16, 44), (25, 42), (5, 45), (26, 45),
)
COMPLETION_PLAYER_DEPLOYMENTS = (
    (16, 4), (14, 5), (16, 6), (15, 9),
    (15, 13), (3, 14), (10, 21), (19, 20),
)
LIANA_RECORD_INDEX = 0
FIRST_COMBAT_RECORD_INDEX = 1
LAST_COMBAT_RECORD_INDEX = 11
LANA_RECORD_INDEX = 1
BOZEL_RECORD_INDEX = 2
BERNHARDT_RECORD_INDEX = 3
EGBERT_RECORD_INDEX = 7
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
COMPLETION_HP_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
FIRST_ENEMY_RUNTIME_GROUP = 9
LAST_ENEMY_RUNTIME_GROUP = 19
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
PROBE_AT = 0
PROBE_DF = 0


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def completion_hp_wrapper_code() -> bytes:
    code = bytearray()
    for group in range(FIRST_ENEMY_RUNTIME_GROUP, LAST_ENEMY_RUNTIME_GROUP + 1):
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        # Preserve hidden and defeated records. Only a currently present,
        # living diagnostic target is reduced to one HP.
        code.extend(bytes.fromhex("0C 39 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("67 12"))
        code.extend(bytes.fromhex("0C 39 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("67 08"))
        code.extend(bytes.fromhex("13 FC 00 01"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 22 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 22 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 12:
        raise ValueError(
            f"unexpected Scenario 22 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 22 deployment table")
    expected = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 22 player deployments differ")
    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 22 fixed record {index} differs from Japanese source"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_hp: bool = False,
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
    if completion_layout:
        players = deployment_bytes(COMPLETION_PLAYER_DEPLOYMENTS)
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET :
            FIRST_PLAYER_DEPLOYMENT_OFFSET + len(players)
        ] = players
    if completion_hp or completion_layout:
        expected_start_entry = START_MENU_ENTRY.to_bytes(4, "big")
        if source[
            START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
        ] != expected_start_entry:
            raise ValueError("Japanese Start-menu entry operand changed")
        if probe[
            START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
        ] != expected_start_entry:
            raise ValueError("input Start-menu entry operand changed")
        wrapper = completion_hp_wrapper_code()
        wrapper_end = COMPLETION_HP_WRAPPER + len(wrapper)
        if probe[COMPLETION_HP_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
            raise ValueError("input completion wrapper region is not empty")
        probe[
            START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
        ] = COMPLETION_HP_WRAPPER.to_bytes(4, "big")
        probe[COMPLETION_HP_WRAPPER:wrapper_end] = wrapper
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 22 ROM with weakened special/enemy "
            "combat groups while preserving allied Liana, stock deployments, "
            "side transitions, and all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-hp",
        action="store_true",
        help=(
            "route the Start menu through a diagnostic wrapper that lowers "
            "only present, living enemy commanders to one HP"
        ),
    )
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "stage the eight players beside source enemy positions and enable "
            "the completion HP wrapper without moving any enemy record"
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
        completion_hp=args.completion_hp,
        completion_layout=args.completion_layout,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print("Scenario 22 combat records 1..11: AT 0, DF 0, no mercenaries")
    print(
        "allied Liana, stock deployments, side IDs, identities, classes, "
        "levels, hidden events, coordinates, and handlers preserved"
    )
    if args.completion_layout:
        print(
            "completion layout: eight players staged beside source enemies; "
            "all enemy coordinates remain source-identical"
        )
    if args.completion_hp or args.completion_layout:
        print("Start lowers only present, living enemy commanders to one HP")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
