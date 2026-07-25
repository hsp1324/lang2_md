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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 23 Clear Probe).md"
SCENARIO_NUMBER = 23
SCENARIO_HEADER = 0x182966
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x18298A
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (3, 23),
    (23, 24),
    (44, 23),
    (3, 26),
    (24, 26),
    (44, 26),
    (3, 29),
    (23, 29),
    (44, 29),
)
COMPLETION_PLAYER_DEPLOYMENTS = (
    (23, 14),
    (21, 16),
    (26, 16),
    (24, 11),
    (23, 8),
    (22, 5),
    (19, 4),
    (16, 4),
    (25, 5),
)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 10
DRAGON_LORD_RECORD_INDEX = 0
LAIRD_RECORD_INDEX = 4
WIZARD_RECORD_INDEX = 10
COMPLETION_TARGET_RECORD_INDEX = DRAGON_LORD_RECORD_INDEX
COMPLETION_HIDDEN_RECORD_INDEXES = tuple(range(1, 11))
COMPLETION_ELWIN_POSITION = (23, 14)
PROTAGONIST_DEATH_TRIGGER = 0x1AD3D6
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "06 02 01 00 00 1A D7 AC"
)
PROTAGONIST_DEATH_EVENT = 0x1AD7AC
PROTAGONIST_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 01 02 01 00 1A EB 14 13 FF 15 FF FF FF"
)
PROTAGONIST_DEATH_TEXT = 0x1AEB14
HOLY_ROD_ESCAPE_TRIGGER = 0x1AD6C8
HOLY_ROD_ESCAPE_TRIGGER_BYTES = bytes.fromhex(
    "42 F2 00 00 15 01 1A 03 00 1A E5 DA"
)
HOLY_ROD_ESCAPE_EVENT = 0x1AE5DA
HOLY_ROD_ESCAPE_EVENT_BYTES = bytes.fromhex(
    "08 FF 43 FF 2A 26 04 15 01 1A 03 FF 00 1A E6 02 "
    "04 11 00 1A E5 F8 02 11 C6 01 00 1A F0 8C "
    "02 01 01 01 00 1A F0 E0 15 FF FF FF"
)
HOLY_ROD_ESCAPE_ENDING = 0x1AE5F0
HOLY_ROD_ESCAPE_ENDING_BYTES = bytes.fromhex(
    "02 11 C6 01 00 1A F0 8C "
    "02 01 01 01 00 1A F0 E0 15 FF FF FF"
)
HOLY_ROD_ESCAPE_LAIRD_TEXT = 0x1AF08C
HOLY_ROD_ESCAPE_ELWIN_TEXT = 0x1AF0E0
PROBE_AT = 0
PROBE_DF = 0
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
COMPLETION_HP_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
FIRST_ENEMY_RUNTIME_GROUP = 9
LAST_ENEMY_RUNTIME_GROUP = 19
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06


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


def mark_runtime_group_defeated_code(group: int) -> bytes:
    record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
    code = bytearray()
    code.extend(bytes.fromhex("00 39 00 80"))
    code.extend((record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("13 FC 00 00"))
    code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("13 FC 00 FF"))
    code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def install_start_wrapper(
    probe: bytearray,
    source: bytes,
    wrapper: bytes,
) -> None:
    expected_start_entry = START_MENU_ENTRY.to_bytes(4, "big")
    for label, data in (("Japanese", source), ("input", probe)):
        if (
            data[START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4]
            != expected_start_entry
        ):
            raise ValueError(f"{label} Start-menu entry operand changed")
    wrapper_end = COMPLETION_HP_WRAPPER + len(wrapper)
    if probe[COMPLETION_HP_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input diagnostic wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = COMPLETION_HP_WRAPPER.to_bytes(4, "big")
    probe[COMPLETION_HP_WRAPPER:wrapper_end] = wrapper


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 23 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 23 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 23 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 23 deployment table")
    expected = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 23 player deployments differ")
    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 23 fixed record {index} differs from Japanese source"
            )
    event_spans = (
        (
            "protagonist-death trigger",
            PROTAGONIST_DEATH_TRIGGER,
            PROTAGONIST_DEATH_TRIGGER_BYTES,
        ),
        (
            "protagonist-death event",
            PROTAGONIST_DEATH_EVENT,
            PROTAGONIST_DEATH_EVENT_BYTES,
        ),
        (
            "Holy Rod escape trigger",
            HOLY_ROD_ESCAPE_TRIGGER,
            HOLY_ROD_ESCAPE_TRIGGER_BYTES,
        ),
        (
            "Holy Rod escape event",
            HOLY_ROD_ESCAPE_EVENT,
            HOLY_ROD_ESCAPE_EVENT_BYTES,
        ),
    )
    for label, offset, expected_bytes in event_spans:
        end = offset + len(expected_bytes)
        for rom_label, data in (("Japanese", source), ("input", probe)):
            if data[offset:end] != expected_bytes:
                raise ValueError(f"{rom_label} Scenario 23 {label} changed")


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_layout: bool = False,
    completion_target_only: bool = False,
    protagonist_death: bool = False,
    holy_rod_escape: bool = False,
) -> int:
    validate_layout(probe, source)
    enabled_modes = (
        int(completion_layout)
        + int(completion_target_only)
        + int(protagonist_death)
        + int(holy_rod_escape)
    )
    if enabled_modes > 1:
        raise ValueError(
            "Scenario 23 diagnostic modes are mutually exclusive"
        )
    if protagonist_death or holy_rod_escape:
        if holy_rod_escape:
            pointer = PROTAGONIST_DEATH_TRIGGER + 4
            probe[pointer : pointer + 4] = HOLY_ROD_ESCAPE_ENDING.to_bytes(
                4, "big"
            )
        install_start_wrapper(
            probe,
            source,
            mark_runtime_group_defeated_code(PROTAGONIST_RUNTIME_GROUP),
        )
        return builder.update_md_checksum(probe)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenaries = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
    if completion_layout:
        positions = deployment_bytes(COMPLETION_PLAYER_DEPLOYMENTS)
        end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(positions)
        probe[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] = positions
    if completion_target_only:
        elwin = deployment_bytes((COMPLETION_ELWIN_POSITION,))
        end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(elwin)
        probe[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] = elwin
        for index in COMPLETION_HIDDEN_RECORD_INDEXES:
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[base] |= 0x80
    if completion_layout or completion_target_only:
        wrapper = completion_hp_wrapper_code()
        install_start_wrapper(probe, source, wrapper)
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 23 ROM with weakened enemy groups "
            "while preserving the Holy Rod map, stock deployments, and all "
            "event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "stage only the nine player deployments beside the stock enemy "
            "groups; enemy coordinates and all event data remain unchanged"
        ),
    )
    parser.add_argument(
        "--completion-target-only",
        action="store_true",
        help=(
            "move only Elwin below source record 0 Dragon Lord, hide records "
            "1..10, and enable the completion HP wrapper"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every deployment, fixed record, and source event while "
            "marking only runtime player group 0 defeated through Start"
        ),
    )
    parser.add_argument(
        "--holy-rod-escape",
        action="store_true",
        help=(
            "bridge the deterministic protagonist-death condition to the "
            "stock Holy Rod enemy-escape ending body, then mark only runtime "
            "player group 0 defeated through Start"
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
        completion_target_only=args.completion_target_only,
        protagonist_death=args.protagonist_death,
        holy_rod_escape=args.holy_rod_escape,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death or args.holy_rod_escape:
        print("Scenario 23 source deployments and all fixed records preserved")
        print("Start marks only runtime player group 0 defeated")
        if args.holy_rod_escape:
            print(
                "diagnostic bridge: protagonist-death condition dispatches "
                "the stock Holy Rod enemy-escape ending body"
            )
            print(
                "stock spatial trigger, Laird/Elwin dialogue pointers, and "
                "GAME OVER bytes preserved"
            )
        else:
            print("stock protagonist-death trigger and event preserved")
    else:
        print("Scenario 23 enemy records 0..10: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print(
            "completion layout: only the nine player deployment coordinates "
            "are staged beside stock enemy groups"
        )
        print(
            "enemy coordinates, sides, identities, classes, levels, Holy Rod "
            "events, and handlers preserved"
        )
        print("Start lowers only present, living enemy commanders to one HP")
    elif args.completion_target_only:
        print(
            "completion target: only source record 0 Dragon Lord remains "
            "visible; records 1..10 hidden"
        )
        print("Elwin staged at (23,14); all enemy coordinates remain unchanged")
        print("Start lowers only the visible, living Dragon Lord to one HP")
    elif not args.protagonist_death and not args.holy_rod_escape:
        print(
            "stock deployments, sides, identities, classes, levels, "
            "coordinates, Holy Rod events, and handlers preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
