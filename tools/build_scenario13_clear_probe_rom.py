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
    ROOT / "roms/builds/Langrisser II (Scenario 13 Clear Probe).md"
)

SCENARIO_NUMBER = 13
SCENARIO_HEADER = 0x181720
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x181740
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (16, 3),
    (20, 2),
    (24, 2),
    (28, 3),
    (22, 4),
    (20, 6),
    (24, 6),
)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 12
ZORUM_RECORD_INDEX = 8
VARGAS_RECORD_INDEX = 10
COMPLETION_HIDDEN_RECORD_INDICES = (*range(0, 8), 9)
COMPLETION_VARGAS_CLASS = 45  # Enemy-palette Fighter; completion probe only.
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
COMPLETION_HP_WRAPPER = 0x3FEF00
VARGAS_RUNTIME_RECORD = 0xFFFF669C
RUNTIME_NAME_ID_OFFSET = 0x01
RUNTIME_HP_OFFSET = 0x03
SOURCE_ZORUM_POSITION = (19, 27)
PROBE_ZORUM_POSITION = (16, 4)
COMPLETION_PLAYER_POSITIONS = (
    (18, 31),
    (17, 32),
    (19, 32),
    (17, 33),
    (19, 33),
    (17, 34),
    (18, 34),
)
COMPLETION_ZORUM_POSITION = (18, 30)
COMPLETION_ENEMY_POSITIONS = (
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    COMPLETION_ZORUM_POSITION,
    (0xFF, 0xFF),
)
PROBE_AT = 0
PROBE_DF = 0


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def completion_hp_wrapper_code() -> bytes:
    code = bytearray(bytes.fromhex("0C 39 00 0F"))
    code.extend((VARGAS_RUNTIME_RECORD + RUNTIME_NAME_ID_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("66 08"))
    code.extend(bytes.fromhex("13 FC 00 01"))
    code.extend((VARGAS_RUNTIME_RECORD + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 13 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 13 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 13:
        raise ValueError(
            f"unexpected Scenario 13 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 13 deployment table")

    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected_deployments)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end] != expected_deployments:
            raise ValueError(f"{label} Scenario 13 player deployments differ")

    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 13 enemy record {index} differs from Japanese source"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_layout: bool = False,
) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6

    zorum = layout.records_offset + ZORUM_RECORD_INDEX * FIXED_RECORD_SIZE
    zorum_position = (
        COMPLETION_ZORUM_POSITION if completion_layout else PROBE_ZORUM_POSITION
    )
    probe[zorum + FIELD_OFFSETS["x"]] = zorum_position[0]
    probe[zorum + FIELD_OFFSETS["y"]] = zorum_position[1]
    if completion_layout:
        for index, position in enumerate(COMPLETION_ENEMY_POSITIONS):
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[enemy + FIELD_OFFSETS["x"]] = position[0]
            probe[enemy + FIELD_OFFSETS["y"]] = position[1]
        for index in COMPLETION_HIDDEN_RECORD_INDICES:
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[enemy] |= 0x80
        vargas = layout.records_offset + VARGAS_RECORD_INDEX * FIXED_RECORD_SIZE
        probe[vargas + FIELD_OFFSETS["class_id"]] = COMPLETION_VARGAS_CLASS
        completion_deployments = deployment_bytes(COMPLETION_PLAYER_POSITIONS)
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET :
            FIRST_PLAYER_DEPLOYMENT_OFFSET + len(completion_deployments)
        ] = completion_deployments
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
            "Build an ignored Scenario 13 ROM with weakened Imperial groups "
            "and Zorum beside stock Elwin while preserving identities, "
            "classes, levels, hidden reinforcements, and all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "hide the nine generic initial records, place all seven players "
            "around Vargas's arrival lane, and use a Fighter Vargas for "
            "clear-handler verification"
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
        completion_layout=args.completion_layout,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print("Scenario 13 enemy records 0..12: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print(
            "completion layout: generic records hidden, players by Vargas lane, "
            "Vargas changed to Fighter"
        )
        print("Start conditionally lowers live Vargas HP to 1 before stock menu")
        print("identities, levels, reinforcement flags, and events preserved")
    else:
        print("Zorum moved from (19,27) to (16,4), beside stock Elwin at (16,3)")
        print(
            "identities, classes, levels, hidden reinforcements, and events "
            "preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
