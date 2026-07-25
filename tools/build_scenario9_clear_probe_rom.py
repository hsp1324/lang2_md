#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
    ROOT / "roms/builds/Langrisser II (Scenario 9 Clear Probe).md"
)
DEFAULT_TURN_EVENT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 9 turn 2 Probe).md"
)

SCENARIO_NUMBER = 9
SCENARIO_HEADER = 0x180F72
DEPLOYMENT_POINTER_OFFSET = 0x08
PLAYER_NAME_TABLE = SCENARIO_HEADER + 0x10
SOURCE_PLAYER_NAME_IDS = (0x01, 0x05, 0x06, 0x02, 0x04, 0x08, 0x07)
SOURCE_PLAYER_NAME_TABLE = b"\x00\x07" + b"".join(
    name_id.to_bytes(2, "big") for name_id in SOURCE_PLAYER_NAME_IDS
)
DEPLOYMENT_TABLE = 0x180F92
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = bytes.fromhex(
    "0008 001C"
    "000A 001A"
    "000D 001B"
    "0010 001D"
    "0013 001B"
    "0016 001A"
    "0019 001C"
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS) // 4
NPC_RECORD_INDICES = (0, 1, 2)
NPC_SIDE_ID = 0x03
LAIRD_RECORD_INDEX = 3
LAIRD_RECORD_OFFSET = 0x18101E
SOURCE_LAIRD_X = 14
SOURCE_LAIRD_Y = 15
SOURCE_LAIRD_NAME_ID = 0x11
SOURCE_LAIRD_CLASS_ID = 0x43
PROBE_LAIRD_X = 8
PROBE_LAIRD_Y = 27
PROBE_LAIRD_AT = 0
PROBE_LAIRD_DF = 0
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
FIRST_FIXED_RUNTIME_GROUP = PLAYER_DEPLOYMENT_COUNT
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_DF_OFFSET = 0x3B
RUNTIME_TURN_COUNTER = 0xFFFFA5F1
TURN_EVENT_TARGET = 2
TURN_EVENT_COUNTER_VALUE = 1
TURN_EVENT_PROTECTED_RUNTIME_GROUPS = tuple(
    range(PLAYER_DEPLOYMENT_COUNT + len(NPC_RECORD_INDICES))
)
TURN_EVENT_PROTECTED_DF = 99
SCENARIO_EVENT_POINTER_TABLE = 0x192B72
SCENARIO_EVENT_POINTER_TABLE_BYTES = bytes.fromhex(
    "00 19 2B 8A "
    "00 19 2B CC "
    "00 19 2C 6E "
    "00 19 2D 3A "
    "00 19 2D 48 "
    "00 19 2D 62"
)
TURN_EVENT_TABLE = 0x192D48
TURN_EVENT_TABLE_BYTES = bytes.fromhex(
    "00 01 00 01 00 19 2D 88 "
    "08 04 00 01 00 19 2E 4C "
    "09 01 00 02 00 19 2E 56 "
    "FF FF"
)
TURN_EVENT_HANDLER_RANGES = {
    "turn-1-entry": (0x192D88, 0x192E4C),
    "turn-1-end": (0x192E4C, 0x192E56),
    "turn-2-entry": (0x192E56, 0x192E78),
}
TURN_EVENT_HANDLER_SHA256 = {
    "turn-1-entry": (
        "4d5886b0a993df5934cea8fbd9fb1c8a66c02ed85d0aa4c442b5c2660973563b"
    ),
    "turn-1-end": (
        "398a6b105ad4e814269c9a1396a81f1140665a3e83721efa9c884751ef130f0c"
    ),
    "turn-2-entry": (
        "9e41758445a9b9e5d9b7e8d051482846920c854979f866b15a44ed9e4323db9b"
    ),
}
TURN_EVENT_TEXTS = (
    0x19389A,
    0x193A02,
    0x193A80,
    0x193B42,
    0x193B84,
)


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def mark_runtime_groups_defeated_code(groups: tuple[int, ...]) -> bytes:
    code = bytearray()
    for group in groups:
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("00 39 00 80"))
        code.extend(
            (record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
        )
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def npc_annihilation_wrapper_code() -> bytes:
    groups = tuple(
        FIRST_FIXED_RUNTIME_GROUP + index for index in NPC_RECORD_INDICES
    )
    return mark_runtime_groups_defeated_code(groups)


def protagonist_death_wrapper_code() -> bytes:
    return mark_runtime_groups_defeated_code((PROTAGONIST_RUNTIME_GROUP,))


def turn_event_wrapper_code() -> bytes:
    code = bytearray()
    for runtime_group in TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + runtime_group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC"))
        code.extend(TURN_EVENT_PROTECTED_DF.to_bytes(2, "big"))
        code.extend((record + RUNTIME_DF_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("0C 39"))
    code.extend(TURN_EVENT_COUNTER_VALUE.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
    code.extend(bytes.fromhex("64 08"))
    code.extend(bytes.fromhex("13 FC"))
    code.extend(TURN_EVENT_COUNTER_VALUE.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
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
    wrapper_end = RUNTIME_WRAPPER + len(wrapper)
    if probe[RUNTIME_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input diagnostic wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = RUNTIME_WRAPPER.to_bytes(4, "big")
    probe[RUNTIME_WRAPPER:wrapper_end] = wrapper


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 9 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 9 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 13:
        raise ValueError(
            f"unexpected Scenario 9 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 9 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                PLAYER_NAME_TABLE : PLAYER_NAME_TABLE
                + len(SOURCE_PLAYER_NAME_TABLE)
            ]
            != SOURCE_PLAYER_NAME_TABLE
        ):
            raise ValueError(f"{label} Scenario 9 player name table changed")
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET :
                FIRST_PLAYER_DEPLOYMENT_OFFSET + len(SOURCE_PLAYER_DEPLOYMENTS)
            ]
            != SOURCE_PLAYER_DEPLOYMENTS
        ):
            raise ValueError(f"{label} Scenario 9 player deployments changed")
        pointer_end = (
            SCENARIO_EVENT_POINTER_TABLE
            + len(SCENARIO_EVENT_POINTER_TABLE_BYTES)
        )
        if (
            data[SCENARIO_EVENT_POINTER_TABLE:pointer_end]
            != SCENARIO_EVENT_POINTER_TABLE_BYTES
        ):
            raise ValueError(f"{label} Scenario 9 event pointer table changed")
        turn_table_end = TURN_EVENT_TABLE + len(TURN_EVENT_TABLE_BYTES)
        if data[TURN_EVENT_TABLE:turn_table_end] != TURN_EVENT_TABLE_BYTES:
            raise ValueError(f"{label} Scenario 9 scheduled turn table changed")
        for handler, (start, end) in TURN_EVENT_HANDLER_RANGES.items():
            payload = bytes(data[start:end])
            if (
                hashlib.sha256(payload).hexdigest()
                != TURN_EVENT_HANDLER_SHA256[handler]
            ):
                raise ValueError(
                    f"{label} Scenario 9 turn handler {handler} changed"
                )

    for index in NPC_RECORD_INDICES:
        record_offset = source_layout.records_offset + index * FIXED_RECORD_SIZE
        if source[record_offset + 0x08] != NPC_SIDE_ID:
            raise ValueError(f"unexpected Japanese Scenario 9 NPC record {index}")

    record_offset = (
        source_layout.records_offset + LAIRD_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != LAIRD_RECORD_OFFSET:
        raise ValueError(f"unexpected Laird record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Laird record differs from Japanese source")
    if (
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_LAIRD_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_LAIRD_Y
        or source[record_offset + FIELD_OFFSETS["name_id"]] != SOURCE_LAIRD_NAME_ID
        or source[record_offset + FIELD_OFFSETS["class_id"]]
        != SOURCE_LAIRD_CLASS_ID
    ):
        raise ValueError("unexpected Japanese Scenario 9 Laird identity or position")


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    npc_annihilation: bool = False,
    protagonist_death: bool = False,
    turn_event: bool = False,
) -> int:
    validate_layout(probe, source)
    if sum((npc_annihilation, protagonist_death, turn_event)) > 1:
        raise ValueError("Scenario 9 diagnostic modes conflict")
    if npc_annihilation or protagonist_death or turn_event:
        layout = scenario_layout(source, SCENARIO_NUMBER)
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            if probe[start:end] != source[start:end]:
                raise ValueError(
                    f"input Scenario 9 fixed record {index} differs from Japanese source"
                )
        wrapper = (
            npc_annihilation_wrapper_code()
            if npc_annihilation
            else (
                protagonist_death_wrapper_code()
                if protagonist_death
                else turn_event_wrapper_code()
            )
        )
        install_start_wrapper(probe, source, wrapper)
    else:
        base = LAIRD_RECORD_OFFSET
        probe[base + FIELD_OFFSETS["at"]] = PROBE_LAIRD_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_LAIRD_DF
        probe[base + FIELD_OFFSETS["x"]] = PROBE_LAIRD_X
        probe[base + FIELD_OFFSETS["y"]] = PROBE_LAIRD_Y
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 9 ROM with an unguarded Laird next to "
            "the stock Elwin deployment for normal-command completion"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--npc-annihilation",
        action="store_true",
        help=(
            "preserve every Scenario 9 fixed record and mark only the three "
            "runtime NPC groups defeated through Start"
        ),
    )
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 9 fixed record and mark only runtime "
            "player group 0 defeated through Start"
        ),
    )
    mode.add_argument(
        "--turn-event",
        action="store_true",
        help=(
            "preserve every Scenario 9 deployment/fixed record and scheduled "
            "event, protect player/NPC runtime groups, and advance from turn 1 "
            "through the turn-1 end and turn-2 entry dialogue"
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
        npc_annihilation=args.npc_annihilation,
        protagonist_death=args.protagonist_death,
        turn_event=args.turn_event,
    )
    output_rom = args.output_rom or (
        DEFAULT_TURN_EVENT_OUTPUT_ROM
        if args.turn_event
        else DEFAULT_OUTPUT_ROM
    )
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)
    if args.npc_annihilation:
        print(
            "Scenario 9 NPC-annihilation mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime NPC groups 7..9 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.protagonist_death:
        print(
            "Scenario 9 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.turn_event:
        print(
            "Scenario 9 turn-event mode: all deployments, fixed records, "
            "scheduled records, and handlers remain source-identical"
        )
        print(
            "Start protects runtime player/NPC groups 0..9 and raises the "
            "turn counter only to 1"
        )
    else:
        print(
            f"Scenario 9 Laird: ({PROBE_LAIRD_X},{PROBE_LAIRD_Y}), "
            "AT 0, DF 0, no mercenaries"
        )
    print(f"checksum: {checksum:04X}")
    print(output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
