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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 19 Clear Probe).md"
SCENARIO_NUMBER = 19
SCENARIO_HEADER = 0x182242
DEPLOYMENT_POINTER_OFFSET = 0x08
PLAYER_NAME_TABLE = SCENARIO_HEADER + 0x10
SOURCE_PLAYER_NAME_IDS = (0x01, 0x05, 0x04, 0x08, 0x07, 0x09, 0x0A, 0x06)
SOURCE_PLAYER_NAME_TABLE = b"\x00\x08" + b"".join(
    name_id.to_bytes(2, "big") for name_id in SOURCE_PLAYER_NAME_IDS
)
DEPLOYMENT_TABLE = 0x182264
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (2, 9), (3, 12), (3, 15), (6, 15),
    (9, 15), (3, 23), (4, 26), (2, 29),
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
COMPLETION_ELWIN_POSITION = (37, 22)
IMELDA_POSITION = (37, 23)
COMPLETION_HP = 1
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 9
IMELDA_RECORD_INDEX = 2
LAIRD_RECORD_INDEX = 7
HIDDEN_ENEMY_RECORD_INDEXES = (7, 8, 9)
PROTAGONIST_DEATH_TRIGGER = 0x1A5E60
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "0E 02 01 00 00 1A 61 44"
)
PROTAGONIST_DEATH_EVENT = 0x1A6144
PROTAGONIST_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 01 02 01 00 1A 6D 36 13 FF"
)
PROTAGONIST_DEATH_TEXT = 0x1A6D36
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
SCENARIO_EVENT_POINTER_TABLE = 0x1A5DE6
SCENARIO_EVENT_POINTER_TABLE_BYTES = bytes.fromhex(
    "00 1A 5D FE "
    "00 1A 5E 18 "
    "00 1A 5E 60 "
    "00 1A 5E FC "
    "00 1A 5F 3A "
    "00 1A 5F 7C"
)
TURN_EVENT_TABLE = 0x1A5F3A
TURN_EVENT_TABLE_BYTES = bytes.fromhex(
    "00 01 00 01 00 1A 5F A2 "
    "03 01 00 02 00 1A 60 08 "
    "04 04 00 0D 00 1A 60 22 "
    "05 04 00 12 00 1A 60 42 "
    "06 04 00 13 00 1A 60 64 "
    "08 04 00 15 00 1A 60 7A "
    "09 04 00 17 00 1A 60 A0 "
    "02 01 00 00 00 1A 60 B4 "
    "FF FF"
)
TURN_EVENT_HANDLER_RANGES = {
    "turn-1-entry": (0x1A5FA2, 0x1A6008),
    "turn-2-entry": (0x1A6008, 0x1A6022),
    "turn-13-end": (0x1A6022, 0x1A6042),
    "turn-18-end": (0x1A6042, 0x1A6064),
    "turn-19-end": (0x1A6064, 0x1A607A),
    "turn-21-end": (0x1A607A, 0x1A60A0),
    "turn-23-end": (0x1A60A0, 0x1A60B4),
    "turn-0-entry": (0x1A60B4, 0x1A6136),
}
TURN_EVENT_HANDLER_SHA256 = {
    "turn-1-entry": (
        "cd3b055f4c10ff1d188364309f1d4b32294beaf5096235d7bf662a00ad577d79"
    ),
    "turn-2-entry": (
        "b57914bdd53993e2842deebd442d7d20b0f75edf4da8399109bd95de7a182dfe"
    ),
    "turn-13-end": (
        "f15f5df14329fe7c0a573c9449e9a5ed0633dbd4df0e18797fc7dd746e3fb707"
    ),
    "turn-18-end": (
        "edd8b9eb77f0a2cb0e37edd4a2c0e6664741cbbccc3e101fd3872184e534b50a"
    ),
    "turn-19-end": (
        "13674403000867eaf0219c8745c579136c5b35922ec3391f737e1b39f5f08a1a"
    ),
    "turn-21-end": (
        "72b06b339a7a07251a0a35e193117ce047d37080ba630c58374a80b5fffffe9a"
    ),
    "turn-23-end": (
        "53dae5c5e14032067ba9b4cd88c8c9d1f8986660947dfc3310b0d0e0c4ac6ed0"
    ),
    "turn-0-entry": (
        "e61b53173cfd1285191d4dc2f737912bebe700f8aae20321a274b930c56e50f0"
    ),
}
TURN_EVENT_TEXTS = {
    2: (0x1A65EE, 0x1A6648, 0x1A6696),
    13: (0x1A66D8, 0x1A66E8, 0x1A670A),
    18: (0x1A6740, 0x1A674A, 0x1A6772, 0x1A679C),
    19: (0x1A67B8,),
    21: (0x1A67D6, 0x1A67E4, 0x1A67F8),
    23: (0x1A6824, 0x1A686A),
}
# Type 01 runs on entry to its numbered turn. Type 04 runs when that turn
# ends, so only the turn-2 entry diagnostic starts from the prior turn.
TURN_EVENT_COUNTER_VALUES = {
    2: 1,
    13: 13,
    18: 18,
    19: 19,
    21: 21,
    23: 23,
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


def completion_hp_wrapper_code() -> bytes:
    """Set only the adjacent completion Imelda to HP1, then run Start."""
    target_group = PLAYER_DEPLOYMENT_COUNT + IMELDA_RECORD_INDEX
    target_hp = (
        RUNTIME_GROUP_BASE
        + target_group * RUNTIME_GROUP_SIZE
        + RUNTIME_HP_OFFSET
    )
    code = bytearray(bytes.fromhex("13 FC 00"))
    code.extend(COMPLETION_HP.to_bytes(1, "big"))
    code.extend(target_hp.to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def turn_event_wrapper_code(target_turn: int) -> bytes:
    if target_turn not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 19 turn-event target must be one of "
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
        raise ValueError("Scenario 19 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 19 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 19 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 19 deployment table")

    expected = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                PLAYER_NAME_TABLE :
                PLAYER_NAME_TABLE + len(SOURCE_PLAYER_NAME_TABLE)
            ]
            != SOURCE_PLAYER_NAME_TABLE
        ):
            raise ValueError(
                f"{label} Scenario 19 player name table changed"
            )
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 19 player deployments differ")
        pointer_end = (
            SCENARIO_EVENT_POINTER_TABLE
            + len(SCENARIO_EVENT_POINTER_TABLE_BYTES)
        )
        if (
            data[SCENARIO_EVENT_POINTER_TABLE:pointer_end]
            != SCENARIO_EVENT_POINTER_TABLE_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 19 event pointer table changed"
            )
        turn_table_end = TURN_EVENT_TABLE + len(TURN_EVENT_TABLE_BYTES)
        if data[TURN_EVENT_TABLE:turn_table_end] != TURN_EVENT_TABLE_BYTES:
            raise ValueError(
                f"{label} Scenario 19 scheduled turn table changed"
            )
        for handler, (start, handler_end) in (
            TURN_EVENT_HANDLER_RANGES.items()
        ):
            digest = hashlib.sha256(
                bytes(data[start:handler_end])
            ).hexdigest()
            if digest != TURN_EVENT_HANDLER_SHA256[handler]:
                raise ValueError(
                    f"{label} Scenario 19 turn handler {handler} changed"
                )

    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 19 fixed record {index} differs from Japanese source"
            )
    for label, data in (("Japanese", source), ("input", probe)):
        trigger_end = (
            PROTAGONIST_DEATH_TRIGGER
            + len(PROTAGONIST_DEATH_TRIGGER_BYTES)
        )
        if (
            data[PROTAGONIST_DEATH_TRIGGER:trigger_end]
            != PROTAGONIST_DEATH_TRIGGER_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 19 protagonist-death trigger changed"
            )
        event_end = PROTAGONIST_DEATH_EVENT + len(PROTAGONIST_DEATH_EVENT_BYTES)
        if (
            data[PROTAGONIST_DEATH_EVENT:event_end]
            != PROTAGONIST_DEATH_EVENT_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 19 protagonist-death event changed"
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
        raise ValueError("Scenario 19 diagnostic modes conflict")
    if turn_event is not None and turn_event not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 19 turn-event target must be one of "
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
        mercenaries = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
    if completion_layout:
        elwin = deployment_bytes((COMPLETION_ELWIN_POSITION,))
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET :
            FIRST_PLAYER_DEPLOYMENT_OFFSET + len(elwin)
        ] = elwin
        install_start_wrapper(
            probe,
            source,
            completion_hp_wrapper_code(),
        )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 19 ROM with weakened Imperial groups "
            "while preserving Imelda, hidden Laird and reinforcements, stock "
            "deployments, and all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "move only Elwin to (37,22), one tile above the source Imelda "
            "at (37,23)"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 19 deployment and fixed record, then "
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
            "turn event"
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
            "protagonist-death diagnostic: stock deployments and fixed "
            "records preserved; runtime player group 0 marked defeated"
        )
    elif args.turn_event is not None:
        print(
            "turn-event: all Scenario 19 deployments, fixed records, and "
            "source event handlers preserved"
        )
        print(
            "Start protects runtime player groups "
            f"{TURN_EVENT_PROTECTED_RUNTIME_GROUPS[0]}.."
            f"{TURN_EVENT_PROTECTED_RUNTIME_GROUPS[-1]} and raises the "
            f"turn counter only to {TURN_EVENT_COUNTER_VALUES[args.turn_event]}"
        )
    else:
        print("Scenario 19 enemy records 0..9: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print("completion layout: Elwin moved from (2,9) to (37,22)")
        print("Imelda remains at the source position (37,23)")
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
