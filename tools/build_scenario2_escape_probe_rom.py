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
    ROOT / "roms/builds/Langrisser II (Scenario 2 Escape Probe).md"
)

SCENARIO_NUMBER = 2
SCENARIO_HEADER = 0x180368
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x180380
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0005 0013")
SOURCE_PLAYER_DEPLOYMENTS = (
    (5, 19),
    (5, 16),
    (19, 16),
)
PLAYER_DEPLOYMENT_COUNT = len(SOURCE_PLAYER_DEPLOYMENTS)
LIANA_RECORD_INDEX = 3
LIANA_RECORD_OFFSET = 0x1803FC
SOURCE_LIANA_X = 8
SOURCE_LIANA_Y = 18
PROBE_LIANA_Y = 1
FIRST_ENEMY_RECORD_INDEX = 4
LAST_ENEMY_RECORD_INDEX = 9

PROTAGONIST_DEATH_TRIGGER = 0x186174
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "09 02 01 00 00 18 65 0E"
)
PROTAGONIST_DEATH_HANDLER = 0x18650E
PROTAGONIST_DEATH_HANDLER_BYTES = bytes.fromhex(
    "02 01 02 01 00 18 76 AE 13 FF 15 FF FF FF"
)
PROTAGONIST_DEATH_TEXT = 0x1876AE
LIANA_DEATH_TRIGGER = 0x18618E
LIANA_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "0E 02 02 00 00 18 65 4C"
)
LIANA_DEATH_HANDLER = 0x18654C
LIANA_DEATH_HANDLER_BYTES = bytes.fromhex(
    "04 13 00 18 65 5A "
    "02 13 60 01 00 18 77 36 "
    "02 02 06 01 00 18 77 62 "
    "04 13 00 18 65 70 "
    "02 13 60 01 00 18 77 74 "
    "02 01 04 01 00 18 77 92 "
    "15 FF FF FF"
)
LIANA_DEATH_TEXTS = (0x187736, 0x187762, 0x187774, 0x187792)
ENEMY_ANNIHILATION_TRIGGER = 0x1861E6
ENEMY_ANNIHILATION_TRIGGER_BYTES = bytes.fromhex(
    "26 06 13 2A 2B 2C 2D 2E 00 18 67 08"
)
ENEMY_ANNIHILATION_HANDLER = 0x186708
ENEMY_ANNIHILATION_HANDLER_BYTES = bytes.fromhex(
    "13 FF "
    "04 05 00 18 67 18 "
    "02 05 11 01 00 18 7B 80 "
    "02 01 01 01 00 18 7B 8C "
    "04 06 00 18 67 34 "
    "02 06 15 01 00 18 7B B6 "
    "16 FF 00 18 67 50 "
    "04 05 00 18 67 48 "
    "02 05 11 01 00 18 7C 20 "
    "16 FF 00 18 67 50 "
    "02 05 12 00 00 18 7C 84 "
    "02 01 01 01 00 18 7D 08 "
    "17 FF 00 18 68 40 "
    "FF FF"
)
ENEMY_ANNIHILATION_TEXTS = (
    0x187B80,
    0x187B8C,
    0x187BB6,
    0x187C20,
    0x187C84,
    0x187D08,
)

START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
FIRST_FIXED_RUNTIME_GROUP = PLAYER_DEPLOYMENT_COUNT
PROTAGONIST_RUNTIME_GROUP = 0
LIANA_RUNTIME_GROUP = FIRST_FIXED_RUNTIME_GROUP + LIANA_RECORD_INDEX
ANNIHILATION_RUNTIME_GROUPS = tuple(
    range(
        FIRST_FIXED_RUNTIME_GROUP + FIRST_ENEMY_RECORD_INDEX,
        FIRST_FIXED_RUNTIME_GROUP + LAST_ENEMY_RECORD_INDEX + 1,
    )
)
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def runtime_death_wrapper_code(target_group: int) -> bytes:
    if target_group not in (PROTAGONIST_RUNTIME_GROUP, LIANA_RUNTIME_GROUP):
        raise ValueError("unsupported Scenario 2 death target")
    target = RUNTIME_GROUP_BASE + target_group * RUNTIME_GROUP_SIZE
    code = bytearray()
    code.extend(bytes.fromhex("00 39 00 80"))
    code.extend(
        (target + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
    )
    code.extend(bytes.fromhex("13 FC 00 00"))
    code.extend((target + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("13 FC 00 FF"))
    code.extend((target + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def enemy_annihilation_wrapper_code() -> bytes:
    code = bytearray()
    for group in ANNIHILATION_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("00 39 00 80"))
        code.extend(
            (record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
        )
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
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


def validate_events(probe: bytes, source: bytes) -> None:
    for event_label, offset, expected in (
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
            "Liana-death trigger",
            LIANA_DEATH_TRIGGER,
            LIANA_DEATH_TRIGGER_BYTES,
        ),
        (
            "Liana-death handler",
            LIANA_DEATH_HANDLER,
            LIANA_DEATH_HANDLER_BYTES,
        ),
        (
            "enemy-annihilation trigger",
            ENEMY_ANNIHILATION_TRIGGER,
            ENEMY_ANNIHILATION_TRIGGER_BYTES,
        ),
        (
            "enemy-annihilation handler",
            ENEMY_ANNIHILATION_HANDLER,
            ENEMY_ANNIHILATION_HANDLER_BYTES,
        ),
    ):
        end = offset + len(expected)
        for source_label, data in (("Japanese", source), ("input", probe)):
            if data[offset:end] != expected:
                raise ValueError(
                    f"{source_label} Scenario 2 {event_label} changed"
                )


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 2 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 2 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 10:
        raise ValueError(
            f"unexpected Scenario 2 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 2 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
        deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(
            expected_deployments
        )
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end] != expected_deployments:
            raise ValueError(f"{label} first player deployment is not (5,19)")

    record_offset = (
        source_layout.records_offset + LIANA_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != LIANA_RECORD_OFFSET:
        raise ValueError(f"unexpected Liana record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Liana record differs from Japanese source")
    if (
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_LIANA_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_LIANA_Y
    ):
        raise ValueError("unexpected Japanese Scenario 2 Liana coordinates")
    for index in range(source_layout.record_count):
        if index == LIANA_RECORD_INDEX:
            continue
        start = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = start + FIXED_RECORD_SIZE
        if probe[start:end] != source[start:end]:
            raise ValueError(
                f"input Scenario 2 fixed record {index} differs from Japanese source"
            )
    validate_events(probe, source)


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    enemy_annihilation: bool = False,
    liana_death: bool = False,
    protagonist_death: bool = False,
) -> int:
    if sum((enemy_annihilation, liana_death, protagonist_death)) > 1:
        raise ValueError("Scenario 2 diagnostic modes are mutually exclusive")
    validate_layout(probe, source)
    if enemy_annihilation:
        install_start_wrapper(
            probe,
            source,
            enemy_annihilation_wrapper_code(),
            label="enemy-annihilation",
        )
    elif liana_death:
        install_start_wrapper(
            probe,
            source,
            runtime_death_wrapper_code(LIANA_RUNTIME_GROUP),
            label="Liana-death",
        )
    elif protagonist_death:
        install_start_wrapper(
            probe,
            source,
            runtime_death_wrapper_code(PROTAGONIST_RUNTIME_GROUP),
            label="protagonist-death",
        )
    else:
        probe[LIANA_RECORD_OFFSET + FIELD_OFFSETS["y"]] = PROBE_LIANA_Y
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 2 ROM with Liana one row from the "
            "north edge for stock escape-completion playback"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--enemy-annihilation",
        action="store_true",
        help=(
            "preserve all Scenario 2 records and mark only the six source "
            "enemy runtime groups defeated through Start"
        ),
    )
    mode.add_argument(
        "--liana-death",
        action="store_true",
        help=(
            "preserve all Scenario 2 records and mark only Liana's source-"
            "owned runtime group defeated through Start"
        ),
    )
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve all Scenario 2 records and mark only runtime player "
            "group 0 defeated through Start"
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
        liana_death=args.liana_death,
        protagonist_death=args.protagonist_death,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.enemy_annihilation:
        print(
            "Scenario 2 enemy-annihilation mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only enemy runtime groups 7..12 defeated, then "
            "returns to the stock Start handler"
        )
    elif args.liana_death:
        print(
            "Scenario 2 Liana-death mode: all deployments and fixed records "
            "remain source-identical"
        )
        print(
            f"Start marks only runtime group {LIANA_RUNTIME_GROUP} defeated, "
            "then returns to the stock Start handler"
        )
    elif args.protagonist_death:
        print(
            "Scenario 2 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    else:
        print(f"Scenario 2 Liana: ({SOURCE_LIANA_X},{PROBE_LIANA_Y})")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
