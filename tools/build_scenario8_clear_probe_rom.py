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
    ROOT / "roms/builds/Langrisser II (Scenario 8 Clear Probe).md"
)
DEFAULT_TURN_EVENT_OUTPUT_PATTERN = (
    "Langrisser II (Scenario 8 turn {turn} Probe).md"
)
DEFAULT_TURN_EVENT_SEQUENCE_OUTPUT = (
    "Langrisser II (Scenario 8 turn event sequence Probe).md"
)
DEFAULT_TURN_23_NO_SCOTT_OUTPUT = (
    "Langrisser II (Scenario 8 turn 23 no Scott Probe).md"
)

SCENARIO_NUMBER = 8
SCENARIO_HEADER = 0x180DA6
DEPLOYMENT_POINTER_OFFSET = 0x08
PLAYER_NAME_TABLE = SCENARIO_HEADER + 0x10
SOURCE_PLAYER_NAME_IDS = (0x01, 0x05, 0x06, 0x02, 0x04, 0x08, 0x07)
SOURCE_PLAYER_NAME_TABLE = b"\x00\x07" + b"".join(
    name_id.to_bytes(2, "big") for name_id in SOURCE_PLAYER_NAME_IDS
)
DEPLOYMENT_TABLE = 0x180DC6
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = bytes.fromhex(
    "0002 0007"
    "0006 0008"
    "0009 0008"
    "0002 000A"
    "0003 000F"
    "0006 000D"
    "0006 0012"
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS) // 4
KRAMER_RECORD_INDEX = 5
KRAMER_RECORD_OFFSET = 0x180E9A
SOURCE_KRAMER_X = 38
SOURCE_KRAMER_Y = 8
PROBE_KRAMER_X = 2
PROBE_KRAMER_Y = 6
PROBE_KRAMER_AT = 0
PROBE_KRAMER_DF = 0
PROBE_KRAMER_SURVIVAL_DF = 14
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
TIMEOUT_LAST_ALLOWED_TURN = 23
TURN_EVENT_PROTECTED_RUNTIME_GROUPS = tuple(range(PLAYER_DEPLOYMENT_COUNT))
TURN_EVENT_PROTECTED_DF = 99
SCOTT_NAME_ID = 0x06
SCOTT_RUNTIME_GROUP = SOURCE_PLAYER_NAME_IDS.index(SCOTT_NAME_ID)
TURN_EVENT_TABLE = 0x190E96
TURN_EVENT_TABLE_BYTES = bytes.fromhex(
    "00 01 00 01 00 19 0F 0A "
    "04 04 00 01 00 19 0F 64 "
    "05 04 00 02 00 19 0F 76 "
    "06 04 00 0C 00 19 0F 90 "
    "07 01 00 12 00 19 0F AA "
    "08 04 00 15 00 19 0F C2 "
    "09 01 00 17 00 19 0F D4 "
    "0A 04 00 17 00 19 10 08 "
    "0B 01 00 02 00 19 10 30 "
    "03 04 00 00 00 19 10 62 "
    "FF FF"
)
TURN_EVENT_HANDLERS = {
    "turn-1-end": 0x190F64,
    "turn-2-end": 0x190F76,
    "turn-12-end": 0x190F90,
    "turn-18-entry": 0x190FAA,
    "turn-21-end": 0x190FC2,
    "turn-23-entry": 0x190FD4,
    "turn-23-end": 0x191008,
    "turn-2-entry": 0x191030,
}
TURN_EVENT_HANDLER_BYTES = {
    "turn-1-end": bytes.fromhex(
        "02 18 93 01 00 19 16 34 "
        "02 2A 9F 01 00 19 16 DA "
        "FF FF"
    ),
    "turn-2-end": bytes.fromhex(
        "02 18 93 01 00 19 16 E2 "
        "02 72 AA 00 00 19 17 06 "
        "02 18 93 01 00 19 17 1E "
        "FF FF"
    ),
    "turn-12-end": bytes.fromhex(
        "02 18 93 01 00 19 17 7E "
        "02 72 AA 00 00 19 17 A2 "
        "02 18 93 01 00 19 17 CA "
        "FF FF"
    ),
    "turn-18-entry": bytes.fromhex(
        "02 01 01 01 00 19 18 38 "
        "04 07 00 19 0F C0 "
        "02 07 21 01 00 19 18 62 "
        "FF FF"
    ),
    "turn-21-end": bytes.fromhex(
        "02 72 AA 00 00 19 18 AE "
        "02 18 93 01 00 19 18 DA "
        "FF FF"
    ),
    "turn-23-entry": bytes.fromhex(
        "04 06 00 19 0F E8 "
        "02 06 15 01 00 19 18 EC "
        "16 FF 00 19 0F F0 "
        "02 1B 29 00 00 19 19 1A "
        "04 04 00 19 0F FE "
        "02 04 0D 01 00 19 19 3A "
        "02 01 01 01 00 19 19 70 "
        "FF FF"
    ),
    "turn-23-end": bytes.fromhex(
        "02 72 AA 00 00 19 19 A2 "
        "02 18 93 01 00 19 19 B4 "
        "2F FF "
        "02 1B 29 00 00 19 19 C2 "
        "13 FF "
        "02 18 93 01 00 19 19 CC "
        "15 FF "
        "FF FF"
    ),
    "turn-2-entry": bytes.fromhex(
        "02 04 0D 01 00 19 1A 24 "
        "02 06 15 01 00 19 1A 8E "
        "02 04 0D 01 00 19 1A F8 "
        "02 07 21 01 00 19 1B 3A "
        "02 04 0D 01 00 19 1B CC "
        "02 08 25 01 00 19 1C 1E "
        "FF FF"
    ),
}
# Type 01 runs on entry to its numbered turn. Type 04 runs when that turn
# ends. Target 2 starts from turn 1 so two normal end-turn transitions cover
# turn-1 end, turn-2 entry, and turn-2 end. Target 23 similarly starts from
# turn 22 so two transitions cover both turn-23 handlers.
TURN_EVENT_COUNTER_VALUES = {
    2: 1,
    12: 12,
    18: 17,
    21: 21,
    23: 22,
}
TURN_EVENT_SEQUENCE_COUNTER_VALUES = (12, 17, 21, 22)
TURN_EVENT_TEXTS = {
    2: (
        0x191634,
        0x19168E,
        0x1916DA,
        0x1916E2,
        0x191706,
        0x19171E,
        0x19174C,
        0x191A24,
        0x191A8E,
        0x191ACA,
        0x191AF8,
        0x191B3A,
        0x191B84,
        0x191BCC,
        0x191C1E,
    ),
    12: (0x19177E, 0x1917A2, 0x1917CA, 0x191800),
    18: (0x191838, 0x191862),
    21: (0x1918AE, 0x1918DA),
    23: (
        0x1918EC,
        0x19191A,
        0x19193A,
        0x191970,
        0x1919A2,
        0x1919B4,
        0x1919C2,
        0x1919CC,
        0x191A14,
    ),
}


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def protagonist_death_wrapper_code() -> bytes:
    protagonist = (
        RUNTIME_GROUP_BASE + PROTAGONIST_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    )
    code = bytearray()
    code.extend(bytes.fromhex("00 39 00 80"))
    code.extend(
        (protagonist + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
    )
    code.extend(bytes.fromhex("13 FC 00 00"))
    code.extend((protagonist + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("13 FC 00 FF"))
    code.extend((protagonist + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def timeout_wrapper_code() -> bytes:
    code = bytearray(bytes.fromhex("13 FC"))
    code.extend(TIMEOUT_LAST_ALLOWED_TURN.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def turn_event_wrapper_code(
    target_turn: int,
    *,
    unavailable_runtime_group: int | None = None,
) -> bytes:
    if target_turn not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 8 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_COUNTER_VALUES)
        )
    if unavailable_runtime_group is not None and (
        target_turn != 23 or unavailable_runtime_group != SCOTT_RUNTIME_GROUP
    ):
        raise ValueError(
            "Scenario 8 alternate turn-event path supports only "
            "turn 23 without Scott"
        )
    counter_value = TURN_EVENT_COUNTER_VALUES[target_turn]
    code = bytearray()
    for runtime_group in TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + runtime_group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC"))
        code.extend(TURN_EVENT_PROTECTED_DF.to_bytes(2, "big"))
        code.extend((record + RUNTIME_DF_OFFSET).to_bytes(4, "big"))
    if unavailable_runtime_group is not None:
        record = (
            RUNTIME_GROUP_BASE
            + unavailable_runtime_group * RUNTIME_GROUP_SIZE
        )
        code.extend(bytes.fromhex("00 39 00 80"))
        code.extend(
            (record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
        )
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
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


def turn_event_sequence_wrapper_code() -> bytes:
    code = bytearray()
    for runtime_group in TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + runtime_group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC"))
        code.extend(TURN_EVENT_PROTECTED_DF.to_bytes(2, "big"))
        code.extend((record + RUNTIME_DF_OFFSET).to_bytes(4, "big"))

    tail_branches: list[int] = []
    for counter_value in TURN_EVENT_SEQUENCE_COUNTER_VALUES:
        code.extend(bytes.fromhex("0C 39"))
        code.extend(counter_value.to_bytes(2, "big"))
        code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
        next_branch = len(code)
        code.extend(bytes.fromhex("64 00"))
        code.extend(bytes.fromhex("13 FC"))
        code.extend(counter_value.to_bytes(2, "big"))
        code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
        tail_branch = len(code)
        code.extend(bytes.fromhex("60 00"))
        next_offset = len(code) - (next_branch + 2)
        if not 0 <= next_offset <= 0x7F:
            raise ValueError("Scenario 8 sequence comparison branch is too long")
        code[next_branch + 1] = next_offset
        tail_branches.append(tail_branch)

    tail = len(code)
    for branch in tail_branches:
        displacement = tail - (branch + 2)
        if not 0 <= displacement <= 0x7F:
            raise ValueError("Scenario 8 sequence tail branch is too long")
        code[branch + 1] = displacement
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
        raise ValueError("Scenario 8 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 8 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 8 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 8 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                PLAYER_NAME_TABLE :
                PLAYER_NAME_TABLE + len(SOURCE_PLAYER_NAME_TABLE)
            ]
            != SOURCE_PLAYER_NAME_TABLE
        ):
            raise ValueError(f"{label} Scenario 8 player order changed")
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET :
                FIRST_PLAYER_DEPLOYMENT_OFFSET + len(SOURCE_PLAYER_DEPLOYMENTS)
            ]
            != SOURCE_PLAYER_DEPLOYMENTS
        ):
            raise ValueError(f"{label} Scenario 8 player deployments changed")

    record_offset = (
        source_layout.records_offset + KRAMER_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != KRAMER_RECORD_OFFSET:
        raise ValueError(f"unexpected Kramer record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Kramer record differs from Japanese source")
    if (
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_KRAMER_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_KRAMER_Y
    ):
        raise ValueError("unexpected Japanese Scenario 8 Kramer coordinates")
    table_end = TURN_EVENT_TABLE + len(TURN_EVENT_TABLE_BYTES)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[TURN_EVENT_TABLE:table_end] != TURN_EVENT_TABLE_BYTES:
            raise ValueError(f"{label} Scenario 8 scheduled turn table changed")
        for handler, offset in TURN_EVENT_HANDLERS.items():
            expected = TURN_EVENT_HANDLER_BYTES[handler]
            if data[offset : offset + len(expected)] != expected:
                raise ValueError(
                    f"{label} Scenario 8 turn handler {handler} changed"
                )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    boss_survival: bool = False,
    protagonist_death: bool = False,
    timeout: bool = False,
    turn_event: int | None = None,
    turn_event_sequence: bool = False,
    turn_23_no_scott: bool = False,
) -> int:
    validate_layout(probe, source)
    if sum(
        (
            boss_survival,
            protagonist_death,
            timeout,
            turn_event is not None,
            turn_event_sequence,
            turn_23_no_scott,
        )
    ) > 1:
        raise ValueError("Scenario 8 diagnostic modes conflict")
    if turn_event is not None and turn_event not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 8 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_COUNTER_VALUES)
        )
    if (
        protagonist_death
        or timeout
        or turn_event is not None
        or turn_event_sequence
        or turn_23_no_scott
    ):
        layout = scenario_layout(source, SCENARIO_NUMBER)
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            if probe[start:end] != source[start:end]:
                raise ValueError(
                    f"input Scenario 8 fixed record {index} differs from Japanese source"
                )
        wrapper = (
            protagonist_death_wrapper_code()
            if protagonist_death
            else (
                timeout_wrapper_code()
                if timeout
                else (
                    turn_event_wrapper_code(turn_event)
                    if turn_event is not None
                    else (
                        turn_event_sequence_wrapper_code()
                        if turn_event_sequence
                        else turn_event_wrapper_code(
                            23,
                            unavailable_runtime_group=SCOTT_RUNTIME_GROUP,
                        )
                    )
                )
            )
        )
        install_start_wrapper(probe, source, wrapper)
    else:
        base = KRAMER_RECORD_OFFSET
        probe[base + FIELD_OFFSETS["at"]] = PROBE_KRAMER_AT
        probe[base + FIELD_OFFSETS["df"]] = (
            PROBE_KRAMER_SURVIVAL_DF
            if boss_survival
            else PROBE_KRAMER_DF
        )
        probe[base + FIELD_OFFSETS["x"]] = PROBE_KRAMER_X
        probe[base + FIELD_OFFSETS["y"]] = PROBE_KRAMER_Y
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 8 ROM with an unguarded Kramer next to "
            "the stock Elwin deployment for a normal-command completion"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--boss-survival",
        action="store_true",
        help=(
            "keep the relocated unguarded Kramer at DF 14 so the current "
            "canonical Elwin deals nine damage and exercises the stock "
            "HP-1 reinforcement branch"
        ),
    )
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 8 fixed record and mark only runtime "
            "player group 0 defeated through Start"
        ),
    )
    mode.add_argument(
        "--timeout",
        action="store_true",
        help=(
            "preserve every Scenario 8 fixed record and set the verified "
            "runtime turn counter to the final allowed turn through Start"
        ),
    )
    mode.add_argument(
        "--turn-event",
        type=int,
        choices=tuple(TURN_EVENT_COUNTER_VALUES),
        help=(
            "preserve every Scenario 8 deployment/fixed record, protect the "
            "seven player runtime groups, and advance to a scheduled turn"
        ),
    )
    mode.add_argument(
        "--turn-event-sequence",
        action="store_true",
        help=(
            "preserve source scenario data and advance successive Start uses "
            "through turns 12, 18, 21, and 23 in one isolated run"
        ),
    )
    mode.add_argument(
        "--turn-23-no-scott",
        action="store_true",
        help=(
            f"preserve source scenario data, mark only runtime player group "
            f"{SCOTT_RUNTIME_GROUP} "
            "unavailable, and exercise the stock turn-23 generic-soldier "
            "alternate line"
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
        boss_survival=args.boss_survival,
        protagonist_death=args.protagonist_death,
        timeout=args.timeout,
        turn_event=args.turn_event,
        turn_event_sequence=args.turn_event_sequence,
        turn_23_no_scott=args.turn_23_no_scott,
    )
    if args.output_rom is not None:
        output_rom = args.output_rom
    elif args.turn_event is not None:
        output_rom = (
            ROOT
            / "roms/builds"
            / DEFAULT_TURN_EVENT_OUTPUT_PATTERN.format(turn=args.turn_event)
        )
    elif args.turn_event_sequence:
        output_rom = (
            ROOT / "roms/builds" / DEFAULT_TURN_EVENT_SEQUENCE_OUTPUT
        )
    elif args.turn_23_no_scott:
        output_rom = ROOT / "roms/builds" / DEFAULT_TURN_23_NO_SCOTT_OUTPUT
    else:
        output_rom = DEFAULT_OUTPUT_ROM
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)
    if args.boss_survival:
        print(
            f"Scenario 8 Kramer survival branch: "
            f"({PROBE_KRAMER_X},{PROBE_KRAMER_Y}), AT 0, "
            f"DF {PROBE_KRAMER_SURVIVAL_DF}, no mercenaries"
        )
    elif args.protagonist_death:
        print(
            "Scenario 8 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.timeout:
        print(
            "Scenario 8 timeout mode: all deployments and fixed records "
            "remain source-identical"
        )
        print(
            "Start sets the verified runtime turn counter to 23, then returns "
            "to the stock Start handler"
        )
    elif args.turn_event is not None:
        print(
            f"Scenario 8 turn-{args.turn_event} mode: all deployments and "
            "fixed records remain source-identical"
        )
        print(
            "Start protects runtime player groups 0..6, raises the verified "
            f"turn counter to {TURN_EVENT_COUNTER_VALUES[args.turn_event]}, "
            "then returns to the stock Start handler"
        )
    elif args.turn_event_sequence:
        print(
            "Scenario 8 turn-event sequence mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Successive Start uses protect runtime player groups 0..6 and "
            "raise the counter only to 12, 17, 21, and 22"
        )
    elif args.turn_23_no_scott:
        print(
            "Scenario 8 turn-23 no-Scott mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            f"Start marks only runtime player group {SCOTT_RUNTIME_GROUP} "
            "unavailable, protects "
            "the other player groups, and raises the turn counter to 22"
        )
    else:
        print(
            f"Scenario 8 Kramer: ({PROBE_KRAMER_X},{PROBE_KRAMER_Y}), "
            "AT 0, DF 0, no mercenaries"
        )
    print(f"checksum: {checksum:04X}")
    print(output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
