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
    ROOT / "roms/builds/Langrisser II (Scenario 7 Clear Probe).md"
)

SCENARIO_NUMBER = 7
SCENARIO_HEADER = 0x180BBC
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x180BDA
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = bytes.fromhex(
    "0007 0014"
    "000C 0014"
    "000F 0014"
    "0008 0018"
    "000E 001B"
    "0012 0017"
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS) // 4
RESIDENT_RECORD_INDICES = (0, 1, 2)
SOURCE_RESIDENT_NAME_IDS = (0x22, 0x20, 0x21)
RESIDENT_SIDE_ID = 0x03
RESIDENT_DEATH_EVENT_TABLE = 0x18F374
SOURCE_RESIDENT_DEATH_EVENTS = bytes.fromhex(
    "17 02 20 00 00 18 F6 7C"
    "19 02 21 00 00 18 F6 9C"
    "1C 02 22 00 00 18 F6 D6"
    "1D 04 20 21 22 00 00 18 F6 E0"
)
HIDDEN_KEITH_RECORD_INDEX = 3
GINAM_RECORD_INDEX = 4
GINAM_RECORD_OFFSET = 0x180C86
SOURCE_GINAM_X = 6
SOURCE_GINAM_Y = 6
PROBE_GINAM_X = 7
PROBE_GINAM_Y = 19
PROBE_GINAM_AT = 0
PROBE_GINAM_DF = 0
LAST_ENEMY_RECORD_INDEX = 11
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
FIRST_FIXED_RUNTIME_GROUP = PLAYER_DEPLOYMENT_COUNT
DEFAULT_LOST_CIVILIAN_RECORDS = (0,)
VALID_CIVILIAN_RECORDS = RESIDENT_RECORD_INDICES
GINAM_RUNTIME_GROUP = FIRST_FIXED_RUNTIME_GROUP + GINAM_RECORD_INDEX
HIDDEN_ENEMY_RUNTIME_GROUPS = tuple(
    range(GINAM_RUNTIME_GROUP + 1, FIRST_FIXED_RUNTIME_GROUP + 12)
)
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_lost_civilian_records(records: tuple[int, ...]) -> None:
    if not records:
        raise ValueError("civilian-loss mode requires at least one resident")
    if len(set(records)) != len(records):
        raise ValueError("civilian-loss resident records must be unique")
    invalid = sorted(set(records) - set(VALID_CIVILIAN_RECORDS))
    if invalid:
        raise ValueError(f"invalid Scenario 7 resident records: {invalid}")


def civilian_loss_wrapper_code(
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

    for group in HIDDEN_ENEMY_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))

    target = RUNTIME_GROUP_BASE + GINAM_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
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
    wrapper_end = RUNTIME_WRAPPER + len(wrapper)
    if probe[RUNTIME_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError(f"input {label} wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = RUNTIME_WRAPPER.to_bytes(4, "big")
    probe[RUNTIME_WRAPPER:wrapper_end] = wrapper


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 7 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 7 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 12:
        raise ValueError(
            f"unexpected Scenario 7 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 7 deployment table")
    event_end = RESIDENT_DEATH_EVENT_TABLE + len(SOURCE_RESIDENT_DEATH_EVENTS)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[RESIDENT_DEATH_EVENT_TABLE:event_end]
            != SOURCE_RESIDENT_DEATH_EVENTS
        ):
            raise ValueError(f"{label} Scenario 7 resident death events changed")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET :
                FIRST_PLAYER_DEPLOYMENT_OFFSET + len(SOURCE_PLAYER_DEPLOYMENTS)
            ]
            != SOURCE_PLAYER_DEPLOYMENTS
        ):
            raise ValueError(f"{label} Scenario 7 player deployments changed")

    for index in range(source_layout.record_count):
        record_offset = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = record_offset + FIXED_RECORD_SIZE
        if probe[record_offset:end] != source[record_offset:end]:
            raise ValueError(
                f"input Scenario 7 fixed record {index} differs from Japanese source"
            )

    for index, expected_name_id in zip(
        RESIDENT_RECORD_INDICES, SOURCE_RESIDENT_NAME_IDS
    ):
        record_offset = source_layout.records_offset + index * FIXED_RECORD_SIZE
        if (
            source[record_offset + 0x08] != RESIDENT_SIDE_ID
            or source[record_offset + FIELD_OFFSETS["name_id"]]
            != expected_name_id
        ):
            raise ValueError(f"unexpected Japanese Scenario 7 resident {index}")

    keith_offset = (
        source_layout.records_offset
        + HIDDEN_KEITH_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if (
        source[keith_offset + FIELD_OFFSETS["name_id"]] != 0x07
        or source[
            keith_offset + FIELD_OFFSETS["x"] :
            keith_offset + FIELD_OFFSETS["y"] + 1
        ]
        != b"\xFF\xFF"
    ):
        raise ValueError("unexpected Japanese Scenario 7 hidden Keith record")

    record_offset = source_layout.records_offset + GINAM_RECORD_INDEX * FIXED_RECORD_SIZE
    if record_offset != GINAM_RECORD_OFFSET:
        raise ValueError(f"unexpected Ginam record 0x{record_offset:06X}")
    if (
        source[record_offset + FIELD_OFFSETS["name_id"]] != 0x17
        or
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_GINAM_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_GINAM_Y
    ):
        raise ValueError("unexpected Japanese Scenario 7 Ginam coordinates")


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    civilian_loss: bool = False,
    lost_civilian_records: tuple[int, ...] = DEFAULT_LOST_CIVILIAN_RECORDS,
    protagonist_death: bool = False,
) -> int:
    validate_layout(probe, source)
    if civilian_loss and protagonist_death:
        raise ValueError("civilian-loss and protagonist-death modes conflict")
    if civilian_loss:
        validate_lost_civilian_records(lost_civilian_records)
    if not protagonist_death:
        base = GINAM_RECORD_OFFSET
        probe[base + FIELD_OFFSETS["at"]] = PROBE_GINAM_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_GINAM_DF
        probe[base + FIELD_OFFSETS["x"]] = PROBE_GINAM_X
        probe[base + FIELD_OFFSETS["y"]] = PROBE_GINAM_Y
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    if civilian_loss:
        install_start_wrapper(
            probe,
            source,
            civilian_loss_wrapper_code(lost_civilian_records),
            label="civilian-loss",
        )
    elif protagonist_death:
        install_start_wrapper(
            probe,
            source,
            protagonist_death_wrapper_code(),
            label="protagonist-death",
        )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 7 ROM with an unguarded Ginam next to "
            "the stock Elwin deployment for civilian-safe completion"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--civilian-loss",
        action="store_true",
        help=(
            "mark one or more runtime residents defeated through Start, hide "
            "the non-Ginam enemies, and leave source Ginam at one HP"
        ),
    )
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 7 fixed record and mark only runtime "
            "player group 0 defeated through Start"
        ),
    )
    parser.add_argument(
        "--lost-civilian-record",
        action="append",
        type=int,
        choices=VALID_CIVILIAN_RECORDS,
        help=(
            "fixed resident record to mark defeated; repeat for multiple "
            "losses (default: 0)"
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
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.civilian_loss:
        print(
            "Scenario 7 civilian-loss mode: all resident/Keith fixed records "
            "remain source-identical"
        )
        print(
            "Start marks fixed resident record(s) "
            f"{','.join(map(str, lost_civilian_records))} defeated, removes "
            "enemy groups 11..17, and lowers Ginam group 10 to one HP"
        )
    elif args.protagonist_death:
        print(
            "Scenario 7 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    else:
        print(
            f"Scenario 7 Ginam: ({PROBE_GINAM_X},{PROBE_GINAM_Y}), "
            "AT 0, DF 0, no mercenaries"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
