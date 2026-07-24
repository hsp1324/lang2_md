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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 20 Clear Probe).md"
SCENARIO_NUMBER = 20
SCENARIO_HEADER = 0x1823F0
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x182412
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (9, 7), (6, 11), (12, 11), (7, 14),
    (11, 14), (7, 18), (11, 18), (9, 21),
)
COMPLETION_ELWIN_POSITION = (22, 22)
FIAS_POSITION = (22, 23)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 9
FIAS_RECORD_INDEX = 5
HIDDEN_ENEMY_RECORD_INDEXES = (7, 8, 9)
COMPLETION_HIDDEN_RECORD_INDEXES = (0, 1, 2, 3, 4, 6, 7, 8, 9)
PROTAGONIST_DEATH_TRIGGER = 0x1A78D4
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "0A 02 01 00 00 1A 7B C4"
)
PROTAGONIST_DEATH_EVENT = 0x1A7BC4
PROTAGONIST_DEATH_EVENT_BYTES = bytes.fromhex(
    "04 73 00 1A 7B D8 "
    "02 01 02 01 00 1A 89 66 "
    "16 FF 00 1A 7B E0 "
    "02 01 02 01 00 1A 89 74 "
    "13 FF 15 FF FF FF"
)
PROTAGONIST_DEATH_FIAS_TEXT = 0x1A8966
PROTAGONIST_DEATH_ALTERNATE_TEXT = 0x1A8974
KRAKEN_EVENT_TRIGGER = 0x1A79CA
KRAKEN_EVENT_TRIGGER_BYTES = bytes.fromhex(
    "03 04 00 09 00 1A 7A 90"
)
KRAKEN_EVENT_TURN_THREE_TRIGGER_BYTES = bytes.fromhex(
    "03 01 00 03 00 1A 7A 90"
)
KRAKEN_EVENT = 0x1A7A90
KRAKEN_EVENT_BYTES = bytes.fromhex(
    "0D 52 02 06 0D 60 02 0E 0D 53 02 "
    "16 12 45 17 00 12 46 17 00 12 73 17 00 "
    "02 60 D0 01 00 1A 82 16 "
    "02 52 B6 01 00 1A 82 2C "
    "04 73 00 1A 7A C6 "
    "02 73 C3 01 00 1A 82 3E "
    "04 05 00 1A 7A D4 "
    "02 05 11 01 00 1A 82 A6 "
    "04 06 00 1A 7A E2 "
    "02 06 15 01 00 1A 82 CA "
    "02 01 01 01 00 1A 82 F6 FF FF"
)
KRAKEN_EVENT_TEXTS = (
    0x1A8216,
    0x1A822C,
    0x1A823E,
    0x1A82A6,
    0x1A82CA,
    0x1A82F6,
)
DOREN_EVENT_TRIGGER = 0x1A79D2
DOREN_EVENT_TRIGGER_BYTES = bytes.fromhex(
    "04 04 00 02 00 1A 7A EC"
)
DOREN_EVENT_TURN_FOUR_TRIGGER_BYTES = bytes.fromhex(
    "04 01 00 04 00 1A 7A EC"
)
DOREN_EVENT = 0x1A7AEC
DOREN_EVENT_BYTES = bytes.fromhex(
    "02 73 C3 01 00 1A 83 40 "
    "02 01 01 01 00 1A 83 94 "
    "02 73 C3 01 00 1A 83 A0 "
    "02 01 03 01 00 1A 84 52 "
    "02 73 C3 01 00 1A 84 84 "
    "02 01 03 01 00 1A 85 06 FF FF"
)
DOREN_EVENT_TEXTS = (
    0x1A8340,
    0x1A8394,
    0x1A83A0,
    0x1A8452,
    0x1A8484,
    0x1A8506,
)
LIANA_THREAT_EVENT_TRIGGER = 0x1A79EA
LIANA_THREAT_EVENT_TRIGGER_BYTES = bytes.fromhex(
    "06 04 00 04 00 1A 7B 56"
)
LIANA_THREAT_EVENT_TURN_FIVE_TRIGGER_BYTES = bytes.fromhex(
    "06 01 00 05 00 1A 7B 56"
)
LIANA_THREAT_EVENT = 0x1A7B56
LIANA_THREAT_EVENT_BYTES = bytes.fromhex(
    "04 73 00 1A 7B 74 "
    "02 73 C3 01 00 1A 86 C0 "
    "02 01 03 01 00 1A 87 6E "
    "02 73 C3 01 00 1A 87 AA FF FF"
)
LIANA_THREAT_EVENT_TEXTS = (
    0x1A86C0,
    0x1A876E,
    0x1A87AA,
)
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
        raise ValueError("Scenario 20 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 20 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 20 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 20 deployment table")
    expected = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 20 player deployments differ")
    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 20 fixed record {index} differs from Japanese source"
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
                f"{label} Scenario 20 protagonist-death trigger changed"
            )
        event_end = PROTAGONIST_DEATH_EVENT + len(PROTAGONIST_DEATH_EVENT_BYTES)
        if (
            data[PROTAGONIST_DEATH_EVENT:event_end]
            != PROTAGONIST_DEATH_EVENT_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 20 protagonist-death event changed"
            )
        kraken_trigger_end = (
            KRAKEN_EVENT_TRIGGER + len(KRAKEN_EVENT_TRIGGER_BYTES)
        )
        if (
            data[KRAKEN_EVENT_TRIGGER:kraken_trigger_end]
            != KRAKEN_EVENT_TRIGGER_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 20 Kraken trigger changed"
            )
        kraken_event_end = KRAKEN_EVENT + len(KRAKEN_EVENT_BYTES)
        if data[KRAKEN_EVENT:kraken_event_end] != KRAKEN_EVENT_BYTES:
            raise ValueError(
                f"{label} Scenario 20 Kraken event changed"
            )
        for name, trigger, trigger_bytes, event, event_bytes in (
            (
                "Doren",
                DOREN_EVENT_TRIGGER,
                DOREN_EVENT_TRIGGER_BYTES,
                DOREN_EVENT,
                DOREN_EVENT_BYTES,
            ),
            (
                "Liana-threat",
                LIANA_THREAT_EVENT_TRIGGER,
                LIANA_THREAT_EVENT_TRIGGER_BYTES,
                LIANA_THREAT_EVENT,
                LIANA_THREAT_EVENT_BYTES,
            ),
        ):
            trigger_end = trigger + len(trigger_bytes)
            if data[trigger:trigger_end] != trigger_bytes:
                raise ValueError(
                    f"{label} Scenario 20 {name} trigger changed"
                )
            event_end = event + len(event_bytes)
            if data[event:event_end] != event_bytes:
                raise ValueError(
                    f"{label} Scenario 20 {name} event changed"
                )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_layout: bool = False,
    protagonist_death: bool = False,
    kraken_event: bool = False,
    conditional_dialogues: bool = False,
) -> int:
    validate_layout(probe, source)
    if sum(
        (
            completion_layout,
            protagonist_death,
            kraken_event,
            conditional_dialogues,
        )
    ) > 1:
        raise ValueError("Scenario 20 diagnostic modes conflict")
    if protagonist_death:
        install_start_wrapper(
            probe,
            source,
            protagonist_death_wrapper_code(),
        )
        return builder.update_md_checksum(probe)
    if kraken_event:
        end = KRAKEN_EVENT_TRIGGER + len(KRAKEN_EVENT_TRIGGER_BYTES)
        probe[KRAKEN_EVENT_TRIGGER:end] = KRAKEN_EVENT_TURN_THREE_TRIGGER_BYTES
    if conditional_dialogues:
        end = DOREN_EVENT_TRIGGER + len(DOREN_EVENT_TRIGGER_BYTES)
        probe[DOREN_EVENT_TRIGGER:end] = DOREN_EVENT_TURN_FOUR_TRIGGER_BYTES
        end = LIANA_THREAT_EVENT_TRIGGER + len(
            LIANA_THREAT_EVENT_TRIGGER_BYTES
        )
        probe[
            LIANA_THREAT_EVENT_TRIGGER:end
        ] = LIANA_THREAT_EVENT_TURN_FIVE_TRIGGER_BYTES
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
        for index in COMPLETION_HIDDEN_RECORD_INDEXES:
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[enemy] |= 0x80
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 20 ROM with weakened monster groups "
            "while preserving source identities, record indexes, and all "
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
            "move only Elwin to (22,22), preserve Fias at source record 5, "
            "and hide the nine other records for completion-flow verification"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 20 deployment and fixed record, then "
            "mark only runtime player group 0 defeated through Start"
        ),
    )
    parser.add_argument(
        "--kraken-event",
        action="store_true",
        help=(
            "preserve the stock Kraken reveal event and hidden records, but "
            "change only event ID 3 from the fixed-record-range condition "
            "to a turn-3 diagnostic trigger"
        ),
    )
    parser.add_argument(
        "--conditional-dialogues",
        action="store_true",
        help=(
            "preserve the stock Doren and Liana-threat handlers, but change "
            "only event IDs 4 and 6 to turn-4 and turn-5 diagnostic triggers"
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
        kraken_event=args.kraken_event,
        conditional_dialogues=args.conditional_dialogues,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "protagonist-death diagnostic: stock deployments and fixed "
            "records preserved; runtime player group 0 marked defeated"
        )
    elif args.kraken_event:
        print(
            "Kraken-event diagnostic: event ID 3 uses a turn-3 trigger; "
            "the stock reveal handler and hidden records are preserved"
        )
        print("Scenario 20 enemy records 0..9: AT 0, DF 0, no mercenaries")
    elif args.conditional_dialogues:
        print(
            "conditional-dialogue diagnostic: event IDs 4 and 6 use "
            "turn-4 and turn-5 triggers; stock handlers are preserved"
        )
        print("Scenario 20 enemy records 0..9: AT 0, DF 0, no mercenaries")
    else:
        print("Scenario 20 enemy records 0..9: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print("completion layout: Elwin moved from (9,7) to (22,22)")
        print(
            "completion list: source record 5 Fias visible; "
            "records 0-4/6-9 hidden"
        )
    else:
        print(
            "stock deployments, identities, classes, levels, hidden events, "
            "coordinates, and handlers preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
