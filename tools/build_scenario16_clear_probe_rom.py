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
    ROOT / "roms/builds/Langrisser II (Scenario 16 Clear Probe).md"
)

SCENARIO_NUMBER = 16
SCENARIO_HEADER = 0x181CF0
DEPLOYMENT_POINTER_OFFSET = 0x08
PLAYER_NAME_TABLE = SCENARIO_HEADER + 0x10
SOURCE_PLAYER_NAME_IDS = (0x01, 0x05, 0x04, 0x08, 0x07, 0x09, 0x0A, 0x06)
SOURCE_PLAYER_NAME_TABLE = b"\x00\x08" + b"".join(
    name_id.to_bytes(2, "big") for name_id in SOURCE_PLAYER_NAME_IDS
)
DEPLOYMENT_TABLE = 0x181D12
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (5, 32),
    (8, 31),
    (11, 30),
    (15, 30),
    (18, 31),
    (21, 32),
    (10, 34),
    (17, 34),
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 9
LEON_RECORD_INDEX = 0
LAIRD_RECORD_INDEX = 5
HIDDEN_ENEMY_RECORD_INDEXES = (7, 8, 9)
LANA_RECORD_INDEX = 8
CASTLE_GATE_BOUNDS = (12, 1, 14, 5)
COMPLETION_ELWIN_POSITION = (13, 6)
CASTLE_GATE_TARGET = (13, 5)
COMPLETION_TRIGGERS = {
    0x1A0C16: bytes.fromhex("05 01 00 00 0C 01 0E 05 00 1A 0C C2"),
    0x1A0C22: bytes.fromhex("06 F0 00 00 10 03 10 03 00 1A 0C F4"),
    0x1A0C2E: bytes.fromhex("07 01 0C 02 00 00 00 00 00 1A 0D 0A"),
}
PROTAGONIST_DEATH_HANDLER = 0x1A0D0A
PROTAGONIST_DEATH_HANDLER_BYTES = bytes.fromhex("13 FF")
PROBE_AT = 0
PROBE_DF = 0
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_DF_OFFSET = 0x3B
RUNTIME_TURN_COUNTER = 0xFFFFA5F1
TURN_EVENT_PROTECTED_RUNTIME_GROUPS = tuple(range(PLAYER_DEPLOYMENT_COUNT))
TURN_EVENT_PROTECTED_DF = 99
SCENARIO_EVENT_POINTER_TABLE = 0x1A0AA6
SCENARIO_EVENT_POINTER_TABLE_BYTES = bytes.fromhex(
    "00 1A 0A BE "
    "00 1A 0A E0 "
    "00 1A 0B 32 "
    "00 1A 0C 16 "
    "00 1A 0C 3C "
    "00 1A 0C 56"
)
TURN_EVENT_TABLE = 0x1A0C3C
TURN_EVENT_TABLE_BYTES = bytes.fromhex(
    "00 01 00 01 00 1A 0C 5C "
    "03 04 00 03 00 1A 0C 86 "
    "04 04 00 08 00 1A 0C 8C "
    "FF FF"
)
TURN_EVENT_HANDLER_RANGES = {
    "turn-1-entry": (0x1A0C5C, 0x1A0C86),
    "turn-3-end": (0x1A0C86, 0x1A0C8C),
    "turn-8-end": (0x1A0C8C, 0x1A0CC0),
}
TURN_EVENT_HANDLER_SHA256 = {
    "turn-1-entry": (
        "7fed6bbdfbf44456c6f04f41ef66c4db3f69d3b204508a2ecdecf0c317a37963"
    ),
    "turn-3-end": (
        "231a09e50d8f9d2954945f673dad1ded5f76a05d57b33ad094cdf2a4f875ee0c"
    ),
    "turn-8-end": (
        "8b938103a23f0c59833fd54d40c1278a7e2d27e8db8ff28f4d486c5d87219f05"
    ),
}
TURN_EVENT_TEXTS = {
    1: (0x1A1058, 0x1A1072, 0x1A109A, 0x1A1100),
    8: (0x1A114A, 0x1A1166, 0x1A1198, 0x1A11E8, 0x1A120A),
}
# Both remaining records are type 04 and run when their numbered turn ends.
TURN_EVENT_COUNTER_VALUES = {
    3: 3,
    8: 8,
}


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def protagonist_death_wrapper_code() -> bytes:
    record = (
        RUNTIME_GROUP_BASE
        + PROTAGONIST_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    )
    code = bytearray()
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


def turn_event_wrapper_code(target_turn: int) -> bytes:
    if target_turn not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 16 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_COUNTER_VALUES)
        )
    counter_value = TURN_EVENT_COUNTER_VALUES[target_turn]
    code = bytearray()
    for runtime_group in TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + runtime_group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC"))
        code.extend(TURN_EVENT_PROTECTED_DF.to_bytes(2, "big"))
        code.extend((record + RUNTIME_DF_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("0C 39"))
    code.extend(counter_value.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
    code.extend(bytes.fromhex("64 08"))
    code.extend(bytes.fromhex("13 FC"))
    code.extend(counter_value.to_bytes(2, "big"))
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
        raise ValueError("Scenario 16 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 16 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 16 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 16 deployment table")

    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected_deployments)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                PLAYER_NAME_TABLE :
                PLAYER_NAME_TABLE + len(SOURCE_PLAYER_NAME_TABLE)
            ]
            != SOURCE_PLAYER_NAME_TABLE
        ):
            raise ValueError(
                f"{label} Scenario 16 player name table changed"
            )
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end] != expected_deployments:
            raise ValueError(f"{label} Scenario 16 player deployments differ")
        pointer_end = (
            SCENARIO_EVENT_POINTER_TABLE
            + len(SCENARIO_EVENT_POINTER_TABLE_BYTES)
        )
        if (
            data[SCENARIO_EVENT_POINTER_TABLE:pointer_end]
            != SCENARIO_EVENT_POINTER_TABLE_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 16 event pointer table changed"
            )
        turn_table_end = TURN_EVENT_TABLE + len(TURN_EVENT_TABLE_BYTES)
        if data[TURN_EVENT_TABLE:turn_table_end] != TURN_EVENT_TABLE_BYTES:
            raise ValueError(
                f"{label} Scenario 16 scheduled turn table changed"
            )
        for handler, (start, end) in TURN_EVENT_HANDLER_RANGES.items():
            digest = hashlib.sha256(bytes(data[start:end])).hexdigest()
            if digest != TURN_EVENT_HANDLER_SHA256[handler]:
                raise ValueError(
                    f"{label} Scenario 16 turn handler {handler} changed"
                )

    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 16 fixed record {index} differs from Japanese source"
            )

    for offset, expected in COMPLETION_TRIGGERS.items():
        end = offset + len(expected)
        if source[offset:end] != expected:
            raise ValueError(
                f"Japanese Scenario 16 completion trigger at 0x{offset:06X} changed"
            )
        if probe[offset:end] != expected:
            raise ValueError(
                f"input Scenario 16 completion trigger at 0x{offset:06X} changed"
            )
    handler_end = (
        PROTAGONIST_DEATH_HANDLER + len(PROTAGONIST_DEATH_HANDLER_BYTES)
    )
    for label, data in (("Japanese", source), ("input", probe)):
        if (
            data[PROTAGONIST_DEATH_HANDLER:handler_end]
            != PROTAGONIST_DEATH_HANDLER_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 16 protagonist-death handler changed"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_layout: bool = False,
    protagonist_death: bool = False,
    turn_event: int | None = None,
) -> int:
    validate_layout(probe, source)
    if sum((completion_layout, protagonist_death, turn_event is not None)) > 1:
        raise ValueError("Scenario 16 diagnostic modes conflict")
    if turn_event is not None and turn_event not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 16 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_COUNTER_VALUES)
        )
    if protagonist_death:
        install_start_wrapper(
            probe,
            source,
            protagonist_death_wrapper_code(),
        )
        return builder.update_md_checksum(probe)
    if turn_event is not None:
        install_start_wrapper(
            probe,
            source,
            turn_event_wrapper_code(turn_event),
        )
        return builder.update_md_checksum(probe)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    if completion_layout:
        elwin = deployment_bytes((COMPLETION_ELWIN_POSITION,))
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET :
            FIRST_PLAYER_DEPLOYMENT_OFFSET + len(elwin)
        ] = elwin
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 16 ROM with weakened Imperial groups "
            "while preserving stock deployments, hidden Lana and ghosts, and "
            "all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "move only Elwin to (13,6), one tile below the source-verified "
            "castle-gate region X 12..14 / Y 1..5"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 16 deployment and fixed record, then "
            "mark only runtime player group 0 defeated through Start"
        ),
    )
    parser.add_argument(
        "--turn-event",
        type=int,
        choices=tuple(TURN_EVENT_COUNTER_VALUES),
        help=(
            "preserve all deployments/fixed records/events, protect only "
            "the eight player runtime groups, and advance to a scheduled "
            "turn-end event"
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
        protagonist_death=args.protagonist_death,
        turn_event=args.turn_event,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "protagonist-death: all Scenario 16 deployments and fixed "
            "records preserved"
        )
        print("Start marks only runtime player group 0 defeated")
    elif args.turn_event is not None:
        print(
            "turn-event: all Scenario 16 deployments, fixed records, and "
            "source event handlers preserved"
        )
        print(
            "Start protects runtime player groups "
            f"{TURN_EVENT_PROTECTED_RUNTIME_GROUPS[0]}.."
            f"{TURN_EVENT_PROTECTED_RUNTIME_GROUPS[-1]} and raises the "
            f"turn counter only to {TURN_EVENT_COUNTER_VALUES[args.turn_event]}"
        )
    else:
        print("Scenario 16 enemy records 0..9: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print("completion layout: Elwin moved from (5,32) to (13,6)")
        print("castle-gate region X 12..14 / Y 1..5 and handlers preserved")
    elif not args.protagonist_death and args.turn_event is None:
        print(
            "stock deployments, identities, classes, levels, hidden events, "
            "coordinates, and handlers preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
