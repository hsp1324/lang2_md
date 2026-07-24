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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 19 Clear Probe).md"
SCENARIO_NUMBER = 19
SCENARIO_HEADER = 0x182242
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x182264
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (2, 9), (3, 12), (3, 15), (6, 15),
    (9, 15), (3, 23), (4, 26), (2, 29),
)
COMPLETION_ELWIN_POSITION = (37, 22)
IMELDA_POSITION = (37, 23)
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
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 19 player deployments differ")

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
) -> int:
    validate_layout(probe, source)
    if completion_layout and protagonist_death:
        raise ValueError("Scenario 19 diagnostic modes conflict")
    if protagonist_death:
        install_start_wrapper(
            probe,
            source,
            protagonist_death_wrapper_code(),
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
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "protagonist-death diagnostic: stock deployments and fixed "
            "records preserved; runtime player group 0 marked defeated"
        )
    else:
        print("Scenario 19 enemy records 0..9: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print("completion layout: Elwin moved from (2,9) to (37,22)")
        print("Imelda remains at the source position (37,23)")
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
