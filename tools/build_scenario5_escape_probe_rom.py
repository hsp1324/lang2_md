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
    ROOT / "roms/builds/Langrisser II (Scenario 5 Escape Probe).md"
)
DEFAULT_PROTAGONIST_DEATH_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 5 protagonist Probe).md"
)
DEFAULT_TIMEOUT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Scenario 5 timeout Probe).md"
)
DEFAULT_TIMEOUT_ALTERNATE_OUTPUT_ROM = (
    ROOT
    / "roms/builds/Langrisser II (Scenario 5 timeout alternate Probe).md"
)
DEFAULT_TURN_EVENT_OUTPUT_PATTERN = (
    "Langrisser II (Scenario 5 turn {turn} Probe).md"
)
DEFAULT_TURN_EVENT_ALTERNATE_OUTPUT_ROM = (
    ROOT
    / "roms/builds/Langrisser II (Scenario 5 turn 20 alternate Probe).md"
)

SCENARIO_NUMBER = 5
SCENARIO_HEADER = 0x18083C
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x180858
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (13, 50),
    (16, 50),
    (9, 53),
    (12, 53),
    (15, 53),
)
SOURCE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("000D 0032")
SOURCE_FIRST_PLAYER_X = 13
SOURCE_FIRST_PLAYER_Y = 50
PROBE_FIRST_PLAYER_Y = 1
ANNIHILATION_PLAYER_DEPLOYMENTS = (
    (12, 43),
    *SOURCE_PLAYER_DEPLOYMENTS[1:],
)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 8
ANNIHILATION_TARGET_RECORD_INDEX = 0
PROBE_AT = 0
PROBE_DF = 0
EVENT_BLOCK_START = 0x18C056
EVENT_BLOCK_END = 0x18D5F2
PROTAGONIST_DEATH_TRIGGER = 0x18C0C6
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "0F 02 01 00 00 18 C3 D6"
)
PROTAGONIST_DEATH_HANDLER = 0x18C3D6
PROTAGONIST_DEATH_HANDLER_BYTES = bytes.fromhex(
    "02 01 02 01 00 18 CB D0 "
    "13 FF "
    "04 16 00 18 C3 EE "
    "02 16 62 01 00 18 CB EA "
    "15 FF FF FF"
)
PROTAGONIST_DEATH_TEXTS = (0x18CBD0, 0x18CBEA)
PROTAGONIST_DEATH_PHYSICAL_TEXTS = (0x18CBD0, 0x18CBEA, 0x18CC2C)
PROTAGONIST_DEATH_CONTINUATIONS = {0x18CBEA: 0x18CC2C}
TIMEOUT_TRIGGER = 0x18C1CA
TIMEOUT_TRIGGER_BYTES = bytes.fromhex(
    "04 04 00 16 00 18 C2 AE"
)
TIMEOUT_HANDLER = 0x18C2AE
TIMEOUT_HANDLER_BYTES = bytes.fromhex(
    "04 06 00 18 C2 C2 "
    "02 06 18 01 00 18 C8 E4 "
    "16 FF 00 18 C2 CA "
    "02 1B 2A 00 00 18 C9 08 "
    "02 01 04 01 00 18 C9 2A "
    "15 FF FF FF"
)
TIMEOUT_TEXTS = (0x18C8E4, 0x18C908, 0x18C92A)
TIMEOUT_TRIGGER_TARGET_OFFSET = TIMEOUT_TRIGGER + 5
TIMEOUT_ALTERNATE_HANDLER = 0x18C2C2
TURN_EVENT_TABLE = 0x18C1AA
TURN_EVENT_TABLE_BYTES = bytes.fromhex(
    "00 01 00 01 00 18 C2 06 "
    "01 01 00 10 00 18 C2 66 "
    "02 01 00 14 00 18 C2 7E "
    "03 01 00 16 00 18 C2 A4 "
    "04 04 00 16 00 18 C2 AE "
    "FF FF"
)
TURN_EVENT_HANDLERS = {
    16: 0x18C266,
    20: 0x18C27E,
    22: 0x18C2A4,
}
TURN_EVENT_HANDLER_BYTES = {
    16: bytes.fromhex(
        "04 02 00 18 C2 74 "
        "02 02 05 01 00 18 C8 00 "
        "02 01 01 01 00 18 C8 24 "
        "FF FF"
    ),
    20: bytes.fromhex(
        "04 06 00 18 C2 92 "
        "02 06 15 01 00 18 C8 4C "
        "16 FF 00 18 C2 9A "
        "02 1B 29 00 00 18 C8 7C "
        "02 01 01 01 00 18 C8 AC "
        "FF FF"
    ),
    22: bytes.fromhex(
        "02 01 01 01 00 18 C8 BC "
        "FF FF"
    ),
}
TURN_EVENT_TEXTS = {
    16: (0x18C800, 0x18C824),
    20: (0x18C84C, 0x18C87C, 0x18C8AC),
    22: (0x18C8BC,),
}
TURN_EVENT_ALTERNATE_TARGET = 20
TURN_EVENT_ALTERNATE_TRIGGER_TARGET_OFFSET = 0x18C1BF
TURN_EVENT_ALTERNATE_HANDLER = 0x18C292
TURN_EVENT_ALTERNATE_TEXT = 0x18C87C
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
ANNIHILATION_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
FIRST_FIXED_RUNTIME_GROUP = len(SOURCE_PLAYER_DEPLOYMENTS)
ANNIHILATION_TARGET_RUNTIME_GROUP = (
    FIRST_FIXED_RUNTIME_GROUP + ANNIHILATION_TARGET_RECORD_INDEX
)
ANNIHILATION_HIDDEN_RUNTIME_GROUPS = tuple(
    range(ANNIHILATION_TARGET_RUNTIME_GROUP + 1, FIRST_FIXED_RUNTIME_GROUP + 9)
)
PROTAGONIST_RUNTIME_GROUP = 0
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_TURN_COUNTER = 0xFFFFA5F1
TIMEOUT_LAST_ALLOWED_TURN = 22


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def annihilation_wrapper_code() -> bytes:
    code = bytearray()
    for group in ANNIHILATION_HIDDEN_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    target = (
        RUNTIME_GROUP_BASE
        + ANNIHILATION_TARGET_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
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
    code = bytearray(bytes.fromhex("0C 39"))
    code.extend(TIMEOUT_LAST_ALLOWED_TURN.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
    # Preserve turn 20 and every later turn when Start is opened again.
    code.extend(bytes.fromhex("64 08"))
    code.extend(bytes.fromhex("13 FC"))
    code.extend(TIMEOUT_LAST_ALLOWED_TURN.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def turn_event_wrapper_code(target_turn: int) -> bytes:
    if target_turn not in TURN_EVENT_HANDLERS:
        raise ValueError(
            "Scenario 5 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_HANDLERS)
        )
    preceding_turn = target_turn - 1
    code = bytearray(bytes.fromhex("0C 39"))
    code.extend(preceding_turn.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
    # Raise an earlier save to the preceding turn once, without rewinding it
    # if Start is reopened after the scheduled event has fired.
    code.extend(bytes.fromhex("64 08"))
    code.extend(bytes.fromhex("13 FC"))
    code.extend(preceding_turn.to_bytes(2, "big"))
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
    for rom_label, data in (("Japanese", source), ("input", probe)):
        if (
            data[START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4]
            != expected_start_entry
        ):
            raise ValueError(f"{rom_label} Start-menu entry operand changed")
    wrapper_end = ANNIHILATION_WRAPPER + len(wrapper)
    if probe[ANNIHILATION_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError(f"input {label} wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = ANNIHILATION_WRAPPER.to_bytes(4, "big")
    probe[ANNIHILATION_WRAPPER:wrapper_end] = wrapper


def validate_result_events(probe: bytes, source: bytes) -> None:
    for label, offset, expected in (
        (
            "protagonist-death trigger",
            PROTAGONIST_DEATH_TRIGGER,
            PROTAGONIST_DEATH_TRIGGER_BYTES,
        ),
        (
            "protagonist-death handler",
            PROTAGONIST_DEATH_HANDLER,
            PROTAGONIST_DEATH_HANDLER_BYTES,
        ),
        (
            "timeout trigger",
            TIMEOUT_TRIGGER,
            TIMEOUT_TRIGGER_BYTES,
        ),
        (
            "timeout handler",
            TIMEOUT_HANDLER,
            TIMEOUT_HANDLER_BYTES,
        ),
    ):
        end = offset + len(expected)
        for rom_label, data in (("Japanese", source), ("input", probe)):
            if data[offset:end] != expected:
                raise ValueError(
                    f"{rom_label} Scenario 5 {label} changed"
                )
    table_end = TURN_EVENT_TABLE + len(TURN_EVENT_TABLE_BYTES)
    for rom_label, data in (("Japanese", source), ("input", probe)):
        if data[TURN_EVENT_TABLE:table_end] != TURN_EVENT_TABLE_BYTES:
            raise ValueError(
                f"{rom_label} Scenario 5 scheduled turn-event table changed"
            )
        for turn, offset in TURN_EVENT_HANDLERS.items():
            expected = TURN_EVENT_HANDLER_BYTES[turn]
            if data[offset : offset + len(expected)] != expected:
                raise ValueError(
                    f"{rom_label} Scenario 5 turn {turn} handler changed"
                )


def install_timeout_alternate_bridge(probe: bytearray) -> None:
    current = int.from_bytes(
        probe[
            TIMEOUT_TRIGGER_TARGET_OFFSET :
            TIMEOUT_TRIGGER_TARGET_OFFSET + 3
        ],
        "big",
    )
    if current != TIMEOUT_HANDLER:
        raise ValueError(
            "input Scenario 5 timeout trigger target changed: "
            f"0x{current:06X} != 0x{TIMEOUT_HANDLER:06X}"
        )
    probe[
        TIMEOUT_TRIGGER_TARGET_OFFSET :
        TIMEOUT_TRIGGER_TARGET_OFFSET + 3
    ] = TIMEOUT_ALTERNATE_HANDLER.to_bytes(3, "big")


def install_turn_event_alternate_bridge(probe: bytearray) -> None:
    offset = TURN_EVENT_ALTERNATE_TRIGGER_TARGET_OFFSET
    current = int.from_bytes(probe[offset : offset + 3], "big")
    expected = TURN_EVENT_HANDLERS[TURN_EVENT_ALTERNATE_TARGET]
    if current != expected:
        raise ValueError(
            "input Scenario 5 turn-20 trigger target changed: "
            f"0x{current:06X} != 0x{expected:06X}"
        )
    probe[offset : offset + 3] = TURN_EVENT_ALTERNATE_HANDLER.to_bytes(
        3,
        "big",
    )


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 5 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 5 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 9:
        raise ValueError(
            f"unexpected Scenario 5 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 5 deployment table")
    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected_deployments)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end]
            != expected_deployments
        ):
            raise ValueError(f"{label} Scenario 5 player deployments differ")
    start = source_layout.records_offset
    end = start + source_layout.record_count * FIXED_RECORD_SIZE
    if probe[start:end] != source[start:end]:
        raise ValueError("input Scenario 5 fixed records differ from Japanese source")
    validate_result_events(probe, source)


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    enemy_annihilation: bool = False,
    protagonist_death: bool = False,
    timeout: bool = False,
    timeout_alternate: bool = False,
    turn_event: int | None = None,
    turn_event_alternate: bool = False,
) -> int:
    validate_layout(probe, source)
    if sum(
        (
            enemy_annihilation,
            protagonist_death,
            timeout,
            timeout_alternate,
            turn_event is not None,
            turn_event_alternate,
        )
    ) > 1:
        raise ValueError("Scenario 5 diagnostic modes are mutually exclusive")
    if turn_event is not None and turn_event not in TURN_EVENT_HANDLERS:
        raise ValueError(
            "Scenario 5 turn-event target must be one of "
            + ", ".join(str(turn) for turn in TURN_EVENT_HANDLERS)
        )
    if (
        protagonist_death
        or timeout
        or timeout_alternate
        or turn_event is not None
        or turn_event_alternate
    ):
        wrapper = (
            protagonist_death_wrapper_code()
            if protagonist_death
            else (
                turn_event_wrapper_code(TURN_EVENT_ALTERNATE_TARGET)
                if turn_event_alternate
                else (
                    turn_event_wrapper_code(turn_event)
                    if turn_event is not None
                    else timeout_wrapper_code()
                )
            )
        )
        install_start_wrapper(
            probe,
            source,
            wrapper,
            label=(
                "protagonist-death"
                if protagonist_death
                else (
                    "timeout-alternate"
                    if timeout_alternate
                    else (
                        f"turn-{turn_event}"
                        if turn_event is not None
                        else (
                            "turn-20-alternate"
                            if turn_event_alternate
                            else "timeout"
                        )
                    )
                )
            ),
        )
        if timeout_alternate:
            install_timeout_alternate_bridge(probe)
        if turn_event_alternate:
            install_turn_event_alternate_bridge(probe)
        return builder.update_md_checksum(probe)
    if not enemy_annihilation:
        y_offset = FIRST_PLAYER_DEPLOYMENT_OFFSET + 2
        probe[y_offset : y_offset + 2] = PROBE_FIRST_PLAYER_Y.to_bytes(2, "big")
        return builder.update_md_checksum(probe)

    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenaries = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6

    deployments = deployment_bytes(ANNIHILATION_PLAYER_DEPLOYMENTS)
    deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(deployments)
    probe[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end] = deployments

    wrapper = annihilation_wrapper_code()
    install_start_wrapper(
        probe,
        source,
        wrapper,
        label="annihilation",
    )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 5 ROM with Elwin one row from the "
            "north edge for stock escape-completion playback"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--enemy-annihilation",
        action="store_true",
        help=(
            "stage Elwin below source record 0, remove runtime groups 6..13, "
            "and lower group 5 to one HP through Start for the stock "
            "enemy-annihilation victory branch"
        ),
    )
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every deployment and fixed record, then mark only "
            "runtime player group 0 defeated through Start"
        ),
    )
    mode.add_argument(
        "--timeout",
        action="store_true",
        help=(
            "preserve every deployment and fixed record, then set the "
            "verified runtime turn counter to the final allowed turn"
        ),
    )
    mode.add_argument(
        "--timeout-alternate",
        action="store_true",
        help=(
            "set the verified final allowed turn and bridge the stock timeout "
            "trigger directly to its source-owned alternate dialogue body"
        ),
    )
    mode.add_argument(
        "--turn-event",
        type=int,
        choices=tuple(TURN_EVENT_HANDLERS),
        metavar="{16,20,22}",
        help=(
            "preserve the source scenario and raise the runtime counter only "
            "to the turn immediately before the selected scheduled event"
        ),
    )
    mode.add_argument(
        "--turn-event-alternate",
        action="store_true",
        help=(
            "enter stock turn 20 while bridging its dispatch pointer directly "
            "to the source-owned general-soldier fallback body"
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
        enemy_annihilation=args.enemy_annihilation,
        protagonist_death=args.protagonist_death,
        timeout=args.timeout,
        timeout_alternate=args.timeout_alternate,
        turn_event=args.turn_event,
        turn_event_alternate=args.turn_event_alternate,
    )
    if args.protagonist_death:
        output_rom = args.output_rom or DEFAULT_PROTAGONIST_DEATH_OUTPUT_ROM
        print(
            "Scenario 5 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.timeout_alternate:
        output_rom = args.output_rom or DEFAULT_TIMEOUT_ALTERNATE_OUTPUT_ROM
        print(
            "Scenario 5 timeout-alternate mode: all deployments, fixed "
            "records, and the source alternate body remain unchanged"
        )
        print(
            "The timeout trigger is bridged directly to source body "
            f"0x{TIMEOUT_ALTERNATE_HANDLER:06X}; Start sets turn 22 once"
        )
    elif args.timeout:
        output_rom = args.output_rom or DEFAULT_TIMEOUT_OUTPUT_ROM
        print(
            "Scenario 5 timeout mode: all deployments and fixed records "
            "remain source-identical"
        )
        print(
            "Start sets the verified runtime turn counter to 22, then returns "
            "to the stock Start handler"
        )
    elif args.turn_event is not None:
        output_rom = args.output_rom or (
            ROOT
            / "roms/builds"
            / DEFAULT_TURN_EVENT_OUTPUT_PATTERN.format(turn=args.turn_event)
        )
        print(
            f"Scenario 5 turn-{args.turn_event} mode: all deployments, fixed "
            "records, and event bytes remain source-identical"
        )
        print(
            "Start raises the verified runtime turn counter only to "
            f"{args.turn_event - 1}; stock turn end enters turn "
            f"{args.turn_event}"
        )
    elif args.turn_event_alternate:
        output_rom = args.output_rom or DEFAULT_TURN_EVENT_ALTERNATE_OUTPUT_ROM
        print(
            "Scenario 5 turn-20 alternate mode: all deployments, fixed "
            "records, and the source fallback body remain unchanged"
        )
        print(
            "The turn-20 trigger is bridged directly to source body "
            f"0x{TURN_EVENT_ALTERNATE_HANDLER:06X}; Start raises the counter "
            "only to turn 19"
        )
    elif args.enemy_annihilation:
        output_rom = args.output_rom or DEFAULT_OUTPUT_ROM
        print(
            "Scenario 5 enemy-annihilation target: source record 0 at "
            "(12,42), Elwin staged at (12,43)"
        )
        print(
            "enemy records 0..8 retain identity/class/level/coordinates and "
            "handlers; only AT/DF and mercenaries are limited"
        )
        print(
            "Start hides and defeats runtime groups 6..13, then lowers only "
            "present, living group 5 to one HP"
        )
    else:
        output_rom = args.output_rom or DEFAULT_OUTPUT_ROM
        print(
            "Scenario 5 first Elwin deployment: "
            f"({SOURCE_FIRST_PLAYER_X},{PROBE_FIRST_PLAYER_Y})"
        )
    print(f"checksum: {checksum:04X}")
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)
    print(output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
