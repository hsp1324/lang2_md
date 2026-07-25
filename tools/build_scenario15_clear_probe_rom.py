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
    ROOT / "roms/builds/Langrisser II (Scenario 15 Clear Probe).md"
)

SCENARIO_NUMBER = 15
SCENARIO_HEADER = 0x181B00
DEPLOYMENT_POINTER_OFFSET = 0x08
PLAYER_NAME_TABLE = SCENARIO_HEADER + 0x10
SOURCE_PLAYER_NAME_IDS = (0x01, 0x05, 0x04, 0x08, 0x07, 0x09, 0x0A)
SOURCE_PLAYER_NAME_TABLE = b"\x00\x07" + b"".join(
    name_id.to_bytes(2, "big") for name_id in SOURCE_PLAYER_NAME_IDS
)
DEPLOYMENT_TABLE = 0x181B20
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (3, 2),
    (6, 3),
    (10, 3),
    (22, 3),
    (27, 4),
    (33, 3),
    (38, 3),
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
SCOTT_RECORD_INDEX = 0
FIRST_ENEMY_RECORD_INDEX = 1
LAST_ENEMY_RECORD_INDEX = 11
IMELDA_RECORD_INDEX = 3
HIDDEN_ENEMY_RECORD_INDEXES = (8, 9, 10, 11)
ESCAPE_BOUNDS = (1, 21, 46, 22)
COMPLETION_ELWIN_POSITION = (3, 20)
ESCAPE_TARGET = (3, 21)
COMPLETION_TRIGGERS = {
    0x19F13C: bytes.fromhex("0C F0 00 00 01 0E 2E 16 00 19 F2 FE"),
    0x19F148: bytes.fromhex("0D 01 00 00 01 15 2E 16 00 19 F3 0A"),
    0x19F154: bytes.fromhex("0E 01 0C 02 00 00 00 00 00 19 F3 1A"),
}
PROTAGONIST_DEATH_HANDLER = 0x19F31A
PROTAGONIST_DEATH_HANDLER_BYTES = bytes.fromhex("13 FF")
PROBE_AT = 0
PROBE_DF = 0
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
TURN_EVENT_PROTECTED_RUNTIME_GROUPS = tuple(
    range(FIRST_FIXED_RUNTIME_GROUP + SCOTT_RECORD_INDEX + 1)
)
TURN_EVENT_PROTECTED_DF = 99
SCENARIO_EVENT_POINTER_TABLE = 0x19EFA2
SCENARIO_EVENT_POINTER_TABLE_BYTES = bytes.fromhex(
    "00 19 EF BA "
    "00 19 EF EC "
    "00 19 F0 8E "
    "00 19 F1 3C "
    "00 19 F1 62 "
    "00 19 F1 A4"
)
TURN_EVENT_TABLE = 0x19F162
TURN_EVENT_TABLE_BYTES = bytes.fromhex(
    "00 01 00 01 00 19 F1 C6 "
    "05 01 00 06 00 19 F2 34 "
    "06 04 00 06 00 19 F2 3A "
    "07 01 00 07 00 19 F2 42 "
    "08 01 00 08 00 19 F2 70 "
    "09 01 00 02 00 19 F2 92 "
    "0A 04 00 01 00 19 F2 A2 "
    "0B 04 00 03 00 19 F2 BC "
    "FF FF"
)
TURN_EVENT_HANDLER_RANGES = {
    "turn-1-entry": (0x19F1C6, 0x19F234),
    "turn-6-entry": (0x19F234, 0x19F23A),
    "turn-6-end": (0x19F23A, 0x19F242),
    "turn-7-entry": (0x19F242, 0x19F270),
    "turn-8-entry": (0x19F270, 0x19F292),
    "turn-2-entry": (0x19F292, 0x19F2A2),
    "turn-1-end": (0x19F2A2, 0x19F2BC),
    "turn-3-end": (0x19F2BC, 0x19F2FE),
    "turn-6-end-body": (0x19F670, 0x19F782),
}
TURN_EVENT_HANDLER_SHA256 = {
    "turn-1-entry": (
        "869b00d242c0a90f99fd05fb90153b1179812cc7036df3cc7a0f55cabf4ba18f"
    ),
    "turn-6-entry": (
        "25c65e1966770b054f8ef6351226febae543a6339542a3cb4632fd892ddc3464"
    ),
    "turn-6-end": (
        "1a46e0bcb59c05f8d5b2ad83333041e8e3e9ddc7e728bde2ee5c377db7cbedf0"
    ),
    "turn-7-entry": (
        "68c733f07f3ded4c3b8827bd9beb1c71475c5911afbb6b4cd55442175929abf5"
    ),
    "turn-8-entry": (
        "595dfa7241bcee9a6ef336321e8e5296006237b1943f198b370d73c1ad306f96"
    ),
    "turn-2-entry": (
        "bd700b5b6a5d6b17489b1a8458c6c7fe011272ede921ce497406785d43eddcca"
    ),
    "turn-1-end": (
        "dd86ea3ba17753b71d67c4e578710635e65a89f008ca86b42c558bcf1731e86a"
    ),
    "turn-3-end": (
        "b475db036515bd140c7bc479aea15fe3bad2f9fec20d96380e97173bead38406"
    ),
    "turn-6-end-body": (
        "8fb7abcfedeb2f6521986af8f5aea8a35697993cb3e7ade5661b36be23627dcd"
    ),
}
TURN_EVENT_TEXTS = (
    0x19F782,
    0x19F7A6,
    0x19F7CE,
    0x19F7F4,
    0x19F80E,
    0x19F872,
    0x19F894,
    0x19F8D8,
    0x19F90A,
    0x19F938,
    0x19F968,
    0x19F992,
    0x19F9B2,
    0x19F9BA,
    0x19F9DE,
    0x19FA42,
    0x19FA88,
    0x19FAC0,
    0x19FAE2,
    0x19FB30,
    0x19FB7E,
    0x19FB9C,
    0x19FBEA,
)
TURN6_FIRST_CALL_TEXTS = (
    0x1A05E2,
    0x1A05F0,
    0x1A05FA,
    0x1A061E,
    0x1A068C,
    0x1A0720,
    0x1A0762,
    0x1A07A6,
)
# Type 01 runs on entry to its numbered turn. Type 04 runs when that turn
# ends. A target value of 6 starts from turn 5 so two normal transitions cover
# both turn-6 handlers.
TURN_EVENT_COUNTER_VALUES = {
    2: 1,
    3: 3,
    6: 5,
    7: 6,
    8: 7,
}
TURN_EVENT_TABLE_TURN3_TARGET = TURN_EVENT_TABLE + 7 * 8 + 4
TURN3_BRANCH_HANDLERS = {
    "stock": TURN_EVENT_HANDLER_RANGES["turn-3-end"][0],
    "imperial-soldier": 0x19F2E6,
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
            "Scenario 15 turn-event target must be one of "
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
        raise ValueError("Scenario 15 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 15 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 12:
        raise ValueError(
            f"unexpected Scenario 15 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 15 deployment table")

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
                f"{label} Scenario 15 player name table changed"
            )
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end] != expected_deployments:
            raise ValueError(f"{label} Scenario 15 player deployments differ")
        pointer_end = (
            SCENARIO_EVENT_POINTER_TABLE
            + len(SCENARIO_EVENT_POINTER_TABLE_BYTES)
        )
        if (
            data[SCENARIO_EVENT_POINTER_TABLE:pointer_end]
            != SCENARIO_EVENT_POINTER_TABLE_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 15 event pointer table changed"
            )
        turn_table_end = TURN_EVENT_TABLE + len(TURN_EVENT_TABLE_BYTES)
        if data[TURN_EVENT_TABLE:turn_table_end] != TURN_EVENT_TABLE_BYTES:
            raise ValueError(
                f"{label} Scenario 15 scheduled turn table changed"
            )
        for handler, (start, end) in TURN_EVENT_HANDLER_RANGES.items():
            digest = hashlib.sha256(bytes(data[start:end])).hexdigest()
            if digest != TURN_EVENT_HANDLER_SHA256[handler]:
                raise ValueError(
                    f"{label} Scenario 15 turn handler {handler} changed"
                )

    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 15 fixed record {index} differs from Japanese source"
            )

    for offset, expected in COMPLETION_TRIGGERS.items():
        end = offset + len(expected)
        if source[offset:end] != expected:
            raise ValueError(
                f"Japanese Scenario 15 completion trigger at 0x{offset:06X} changed"
            )
        if probe[offset:end] != expected:
            raise ValueError(
                f"input Scenario 15 completion trigger at 0x{offset:06X} changed"
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
                f"{label} Scenario 15 protagonist-death handler changed"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_layout: bool = False,
    protagonist_death: bool = False,
    turn_event: int | None = None,
    turn_event_branch: str = "stock",
) -> int:
    validate_layout(probe, source)
    if sum((completion_layout, protagonist_death, turn_event is not None)) > 1:
        raise ValueError("Scenario 15 diagnostic modes conflict")
    if turn_event is not None and turn_event not in TURN_EVENT_COUNTER_VALUES:
        raise ValueError(
            "Scenario 15 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_COUNTER_VALUES)
        )
    if turn_event_branch not in TURN3_BRANCH_HANDLERS:
        raise ValueError(
            "Scenario 15 turn-3 branch must be one of "
            + ", ".join(TURN3_BRANCH_HANDLERS)
        )
    if turn_event_branch != "stock" and turn_event != 3:
        raise ValueError(
            "Scenario 15 non-stock turn-event branch requires --turn-event 3"
        )
    if protagonist_death:
        install_start_wrapper(
            probe,
            source,
            protagonist_death_wrapper_code(),
        )
        return builder.update_md_checksum(probe)
    if turn_event is not None:
        if turn_event_branch != "stock":
            probe[
                TURN_EVENT_TABLE_TURN3_TARGET :
                TURN_EVENT_TABLE_TURN3_TARGET + 4
            ] = TURN3_BRANCH_HANDLERS[turn_event_branch].to_bytes(4, "big")
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
            "Build an ignored Scenario 15 ROM with weakened Imperial and "
            "monster groups while preserving allied Scott, stock deployments, "
            "hidden Lana and monsters, and all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "move only Elwin to (3,20), one tile above the source-verified "
            "escape region X 1..46 / Y 21..22"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 15 deployment and fixed record, then "
            "mark only runtime player group 0 defeated through Start"
        ),
    )
    parser.add_argument(
        "--turn-event",
        type=int,
        choices=tuple(TURN_EVENT_COUNTER_VALUES),
        help=(
            "preserve all deployments/fixed records/events, protect only "
            "player and Scott runtime groups, and advance to a scheduled "
            "turn event"
        ),
    )
    parser.add_argument(
        "--turn-event-branch",
        choices=tuple(TURN3_BRANCH_HANDLERS),
        default="stock",
        help=(
            "select the stock turn-3 handler or its source-owned imperial-"
            "soldier fallback dialogue body"
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
        turn_event_branch=args.turn_event_branch,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "protagonist-death: all Scenario 15 deployments and fixed "
            "records preserved"
        )
        print("Start marks only runtime player group 0 defeated")
    elif args.turn_event is not None:
        print(
            "turn-event: all Scenario 15 deployments, fixed records, and "
            "source event handlers preserved"
        )
        if args.turn_event_branch != "stock":
            print(
                "turn-3 scheduled target redirected only to the source-owned "
                "imperial-soldier fallback dialogue body"
            )
        print(
            "Start protects runtime player/Scott groups "
            f"{TURN_EVENT_PROTECTED_RUNTIME_GROUPS[0]}.."
            f"{TURN_EVENT_PROTECTED_RUNTIME_GROUPS[-1]} and raises the "
            f"turn counter only to {TURN_EVENT_COUNTER_VALUES[args.turn_event]}"
        )
    else:
        print("Scenario 15 enemy records 1..11: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print("completion layout: Elwin moved from (3,2) to (3,20)")
        print("escape region X 1..46 / Y 21..22 and handlers preserved")
    elif not args.protagonist_death and args.turn_event is None:
        print(
            "allied Scott, stock deployments, identities, classes, levels, "
            "hidden events, and handlers preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
