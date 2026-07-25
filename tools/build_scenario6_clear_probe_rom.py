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
    ROOT / "roms/builds/Langrisser II (Scenario 6 Clear Probe).md"
)
DEFAULT_TURN_EVENT_OUTPUT_PATTERN = (
    "Langrisser II (Scenario 6 turn {turn} Probe).md"
)
DEFAULT_TURN_EVENT_BRANCH_OUTPUT_PATTERN = (
    "Langrisser II (Scenario 6 turn {turn} {branch} Probe).md"
)

SCENARIO_NUMBER = 6
SCENARIO_HEADER = 0x1809B4
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x1809D0
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0004 001A")
PLAYER_DEPLOYMENT_COUNT = 5
FIRST_ENEMY_RECORD_INDEX = 4
LAST_VISIBLE_ENEMY_RECORD_INDEX = 11
LAST_ENEMY_RECORD_INDEX = 12
PROBE_AT = 0
PROBE_DF = 0
PROBE_VISIBLE_COORDINATES = (
    (4, 25),
    (7, 26),
    (9, 28),
    (11, 26),
    (15, 26),
    (4, 27),
    (7, 28),
    (9, 30),
)
PARTIAL_LOSS_TARGET_COORDINATE = PROBE_VISIBLE_COORDINATES[0]
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
PARTIAL_LOSS_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
FIRST_FIXED_RUNTIME_GROUP = PLAYER_DEPLOYMENT_COUNT
DEFAULT_LOST_CIVILIAN_RECORDS = (1,)
VALID_CIVILIAN_RECORDS = (1, 2, 3)
PARTIAL_LOSS_TARGET_RUNTIME_GROUP = (
    FIRST_FIXED_RUNTIME_GROUP + FIRST_ENEMY_RECORD_INDEX
)
PARTIAL_LOSS_HIDDEN_ENEMY_GROUPS = tuple(
    range(PARTIAL_LOSS_TARGET_RUNTIME_GROUP + 1, FIRST_FIXED_RUNTIME_GROUP + 13)
)
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_DF_OFFSET = 0x3B
RUNTIME_TURN_COUNTER = 0xFFFFA5F1
TURN_EVENT_PROTECTED_RUNTIME_GROUPS = tuple(
    range(FIRST_FIXED_RUNTIME_GROUP + FIRST_ENEMY_RECORD_INDEX)
)
TURN_EVENT_PROTECTED_DF = 99
TURN_EVENT_TABLE = 0x18D778
TURN_EVENT_TABLE_BYTES = bytes.fromhex(
    "00 01 00 01 00 18 D7 BC "
    "01 01 00 03 00 18 D8 16 "
    "02 04 00 07 00 18 D8 24 "
    "05 04 00 04 00 18 D8 88 "
    "06 04 00 05 00 18 D8 A2 "
    "FF FF"
)
TURN_EVENT_HANDLERS = {
    3: 0x18D816,
    4: 0x18D888,
    5: 0x18D8A2,
    7: 0x18D824,
}
TURN_EVENT_TABLE_TURN7_TARGET = TURN_EVENT_TABLE + 2 * 8 + 4
TURN7_BRANCH_HANDLERS = {
    "stock": TURN_EVENT_HANDLERS[7],
    "support-arrival": 0x18D836,
    "morgan-alternate": 0x18D844,
    "late-arrival": 0x18D87E,
}
TURN7_BRANCH_PREFIX_BYTES = {
    "support-arrival": bytes.fromhex("02 31 9F 01 00 18 DF 2C"),
    "morgan-alternate": bytes.fromhex("02 16 62 01 00 18 DF 4C"),
    "late-arrival": bytes.fromhex("02 31 9F 01 00 18 E0 CA"),
}
TURN_EVENT_HANDLER_BYTES = {
    3: bytes.fromhex(
        "12 08 17 00 "
        "12 2C 17 00 "
        "12 30 17 00 "
        "FF FF"
    ),
    4: bytes.fromhex(
        "11 2C 17 00 "
        "10 2C 22 09 "
        "10 2C 23 19 "
        "11 30 17 00 "
        "10 30 22 0F "
        "10 30 23 1B "
        "FF FF"
    ),
    5: bytes.fromhex(
        "12 2C 17 00 "
        "12 30 17 00 "
        "FF FF"
    ),
    7: bytes.fromhex(
        "0C 04 10 FF "
        "0D 31 1D "
        "13 "
        "08 00 03 FF "
        "04 16 00 18 D8 7E "
        "02 31 9F 01 00 18 DF 2C "
        "06 04 00 18 D8 52 "
        "02 16 62 01 00 18 DF 4C "
        "16 FF 00 18 D8 5A "
        "02 16 62 01 00 18 DF B0 "
        "04 05 00 18 D8 78 "
        "02 05 11 01 00 18 E0 0E "
        "02 16 62 01 00 18 E0 44 "
        "02 05 11 01 00 18 E0 BA "
        "16 FF 00 18 D8 86 "
        "02 31 9F 01 00 18 E0 CA "
        "FF FF"
    ),
}
# Type 01 runs when entering its numbered turn. Type 04 is evaluated when
# ending that numbered turn, as independently established by Scenario 5.
TURN_EVENT_COUNTER_VALUES = {
    3: 2,
    4: 4,
    5: 5,
    7: 7,
}
TURN_EVENT_TEXTS = {
    7: (
        0x18DF2C,
        0x18DF4C,
        0x18DFB0,
        0x18E00E,
        0x18E044,
        0x18E088,
        0x18E0BA,
        0x18E0CA,
        0x18E0F4,
    ),
}


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_lost_civilian_records(records: tuple[int, ...]) -> None:
    if not records:
        raise ValueError("partial-loss mode requires at least one resident")
    if len(records) >= len(VALID_CIVILIAN_RECORDS):
        raise ValueError("partial-loss mode must leave at least one resident")
    if len(set(records)) != len(records):
        raise ValueError("partial-loss resident records must be unique")
    invalid = sorted(set(records) - set(VALID_CIVILIAN_RECORDS))
    if invalid:
        raise ValueError(f"invalid Scenario 6 resident records: {invalid}")


def partial_loss_wrapper_code(
    lost_civilian_records: tuple[int, ...] = DEFAULT_LOST_CIVILIAN_RECORDS,
) -> bytes:
    validate_lost_civilian_records(lost_civilian_records)
    code = bytearray()
    for fixed_record in lost_civilian_records:
        runtime_group = FIRST_FIXED_RUNTIME_GROUP + fixed_record
        civilian = RUNTIME_GROUP_BASE + runtime_group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("00 39 00 80"))
        code.extend(
            (civilian + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
        )
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((civilian + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((civilian + RUNTIME_X_OFFSET).to_bytes(4, "big"))

    for group in PARTIAL_LOSS_HIDDEN_ENEMY_GROUPS:
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))

    target = (
        RUNTIME_GROUP_BASE
        + PARTIAL_LOSS_TARGET_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    )
    code.extend(bytes.fromhex("0C 39 00 FF"))
    code.extend((target + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("67 12"))
    code.extend(bytes.fromhex("0C 39 00 00"))
    code.extend((target + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("67 08"))
    code.extend(bytes.fromhex("13 FC 00 01"))
    code.extend((target + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def protagonist_death_wrapper_code() -> bytes:
    code = bytearray()
    protagonist = (
        RUNTIME_GROUP_BASE + PROTAGONIST_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    )
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


def turn_event_wrapper_code(target_turn: int) -> bytes:
    if target_turn not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 6 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_COUNTER_VALUES)
    )
    counter_value = TURN_EVENT_COUNTER_VALUES[target_turn]
    code = bytearray()
    # A no-action stock phase can kill residents or Elwin before a later
    # scheduled event. Protect only the five player groups, Aaron, and the
    # three resident groups; fixed records and event bytes stay source-identical.
    for runtime_group in TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + runtime_group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC"))
        code.extend(TURN_EVENT_PROTECTED_DF.to_bytes(2, "big"))
        code.extend((record + RUNTIME_DF_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("0C 39"))
    code.extend(counter_value.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
    # Raise an earlier save to the required event state once, but never
    # rewind a later turn when Start is reopened.
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
    *,
    label: str,
) -> None:
    expected_start_entry = START_MENU_ENTRY.to_bytes(4, "big")
    for source_label, data in (("Japanese", source), ("input", probe)):
        if (
            data[START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4]
            != expected_start_entry
        ):
            raise ValueError(f"{source_label} Start-menu entry operand changed")
    wrapper_end = PARTIAL_LOSS_WRAPPER + len(wrapper)
    if probe[PARTIAL_LOSS_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError(f"input {label} wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = PARTIAL_LOSS_WRAPPER.to_bytes(4, "big")
    probe[PARTIAL_LOSS_WRAPPER:wrapper_end] = wrapper


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 6 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 6 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 13:
        raise ValueError(
            f"unexpected Scenario 6 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 6 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
            ]
            != SOURCE_FIRST_PLAYER_DEPLOYMENT
        ):
            raise ValueError(f"{label} first player deployment is not (4,26)")
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 6 enemy record {index} differs from Japanese source"
            )
    table_end = TURN_EVENT_TABLE + len(TURN_EVENT_TABLE_BYTES)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[TURN_EVENT_TABLE:table_end] != TURN_EVENT_TABLE_BYTES:
            raise ValueError(f"{label} Scenario 6 scheduled turn table changed")
        for turn, offset in TURN_EVENT_HANDLERS.items():
            expected = TURN_EVENT_HANDLER_BYTES[turn]
            if data[offset : offset + len(expected)] != expected:
                raise ValueError(
                    f"{label} Scenario 6 turn {turn} handler changed"
                )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    civilian_loss: bool = False,
    lost_civilian_records: tuple[int, ...] = DEFAULT_LOST_CIVILIAN_RECORDS,
    protagonist_death: bool = False,
    turn_event: int | None = None,
    turn_event_branch: str = "stock",
) -> int:
    validate_layout(probe, source)
    if sum((civilian_loss, protagonist_death, turn_event is not None)) > 1:
        raise ValueError("Scenario 6 diagnostic modes conflict")
    if turn_event is not None and turn_event not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 6 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_COUNTER_VALUES)
        )
    if turn_event_branch not in TURN7_BRANCH_HANDLERS:
        raise ValueError(
            "Scenario 6 turn-7 branch must be one of "
            + ", ".join(TURN7_BRANCH_HANDLERS)
        )
    if turn_event_branch != "stock" and turn_event != 7:
        raise ValueError(
            "Scenario 6 alternate turn-event branches require --turn-event 7"
        )
    if civilian_loss:
        validate_lost_civilian_records(lost_civilian_records)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    if not protagonist_death and turn_event is None:
        for index in range(
            FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
            probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
            mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
            probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
            if civilian_loss and index == FIRST_ENEMY_RECORD_INDEX:
                x, y = PARTIAL_LOSS_TARGET_COORDINATE
                probe[base + FIELD_OFFSETS["x"]] = x
                probe[base + FIELD_OFFSETS["y"]] = y
            elif (
                not civilian_loss
                and index <= LAST_VISIBLE_ENEMY_RECORD_INDEX
            ):
                x, y = PROBE_VISIBLE_COORDINATES[
                    index - FIRST_ENEMY_RECORD_INDEX
                ]
                probe[base + FIELD_OFFSETS["x"]] = x
                probe[base + FIELD_OFFSETS["y"]] = y

    if civilian_loss:
        wrapper = partial_loss_wrapper_code(lost_civilian_records)
        install_start_wrapper(
            probe,
            source,
            wrapper,
            label="partial-loss",
        )
    elif protagonist_death:
        install_start_wrapper(
            probe,
            source,
            protagonist_death_wrapper_code(),
            label="protagonist-death",
        )
    elif turn_event is not None:
        if turn_event_branch != "stock":
            probe[
                TURN_EVENT_TABLE_TURN7_TARGET
                : TURN_EVENT_TABLE_TURN7_TARGET + 4
            ] = TURN7_BRANCH_HANDLERS[turn_event_branch].to_bytes(4, "big")
        install_start_wrapper(
            probe,
            source,
            turn_event_wrapper_code(turn_event),
            label=f"turn-{turn_event}",
        )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 6 ROM with weakened visible enemies "
            "near the stock player deployment for civilian-safe completion"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--civilian-loss",
        action="store_true",
        help=(
            "retain two residents, mark one runtime resident defeated through "
            "Start, and leave one source enemy at one HP for the damaged-"
            "village/no-Amulet completion branch"
        ),
    )
    parser.add_argument(
        "--turn-event-branch",
        choices=tuple(TURN7_BRANCH_HANDLERS),
        default="stock",
        help=(
            "for --turn-event 7 only, redirect the scheduled-event table to "
            "one of the stock handler's internal dialogue branches"
        ),
    )
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 6 fixed record and mark only runtime "
            "player group 0 defeated through Start"
        ),
    )
    mode.add_argument(
        "--turn-event",
        type=int,
        choices=tuple(TURN_EVENT_HANDLERS),
        metavar="{3,4,5,7}",
        help=(
            "preserve all Scenario 6 fixed/event data and raise the runtime "
            "turn counter only to the stock state required by the selected "
            "scheduled event"
        ),
    )
    parser.add_argument(
        "--lost-civilian-record",
        action="append",
        type=int,
        choices=VALID_CIVILIAN_RECORDS,
        help=(
            "fixed resident record to mark defeated; repeat for two losses "
            "(default: 1)"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    lost_civilian_records = tuple(
        args.lost_civilian_record or DEFAULT_LOST_CIVILIAN_RECORDS
    )
    checksum = patch_probe(
        probe,
        source,
        civilian_loss=args.civilian_loss,
        lost_civilian_records=lost_civilian_records,
        protagonist_death=args.protagonist_death,
        turn_event=args.turn_event,
        turn_event_branch=args.turn_event_branch,
    )
    if args.output_rom is not None:
        output_rom = args.output_rom
    elif args.turn_event is not None and args.turn_event_branch != "stock":
        output_rom = (
            ROOT
            / "roms/builds"
            / DEFAULT_TURN_EVENT_BRANCH_OUTPUT_PATTERN.format(
                turn=args.turn_event,
                branch=args.turn_event_branch,
            )
        )
    elif args.turn_event is not None:
        output_rom = (
            ROOT
            / "roms/builds"
            / DEFAULT_TURN_EVENT_OUTPUT_PATTERN.format(turn=args.turn_event)
        )
    else:
        output_rom = DEFAULT_OUTPUT_ROM
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)
    if args.civilian_loss:
        print(
            "Scenario 6 partial-loss mode: fixed allied/NPC records remain "
            "source-identical; only enemy record 4 moves to (4,25)"
        )
        print(
            "Start marks fixed resident record(s) "
            f"{','.join(map(str, lost_civilian_records))} defeated, removes "
            "enemy groups 10..17, and lowers living enemy group 9 to one HP"
        )
    elif args.protagonist_death:
        print(
            "Scenario 6 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.turn_event is not None:
        if args.turn_event_branch != "stock":
            print(
                f"Scenario 6 turn-{args.turn_event} mode: all deployments and "
                "fixed records remain source-identical"
            )
            print(
                "scheduled turn-7 table target redirected to stock internal "
                f"branch {args.turn_event_branch} at "
                f"0x{TURN7_BRANCH_HANDLERS[args.turn_event_branch]:06X}"
            )
        else:
            print(
                f"Scenario 6 turn-{args.turn_event} mode: all deployments, "
                "fixed records, and event bytes remain source-identical"
            )
        print(
            "Start raises the verified runtime turn counter only to "
            f"{TURN_EVENT_COUNTER_VALUES[args.turn_event]}, then returns to "
            "the stock Start handler"
        )
    else:
        print(
            "Scenario 6 enemy records 4..12: AT 0, DF 0, no mercenaries; "
            "visible records 4..11 moved near the stock player deployment"
        )
    print(f"checksum: {checksum:04X}")
    print(output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
