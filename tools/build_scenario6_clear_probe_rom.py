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
    layout = scenario_layout(source, SCENARIO_NUMBER)
    if not protagonist_death:
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
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
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
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 6 fixed record and mark only runtime "
            "player group 0 defeated through Start"
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
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
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
    else:
        print(
            "Scenario 6 enemy records 4..12: AT 0, DF 0, no mercenaries; "
            "visible records 4..11 moved near the stock player deployment"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
