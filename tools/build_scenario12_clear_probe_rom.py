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
    ROOT / "roms/builds/Langrisser II (Scenario 12 Clear Probe).md"
)

SCENARIO_NUMBER = 12
SCENARIO_HEADER = 0x181554
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x181574
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
PLAYER_DEPLOYMENT_COUNT = 7
SOURCE_PLAYER_DEPLOYMENTS = (
    (15, 23),
    (7, 28),
    (10, 27),
    (15, 26),
    (20, 27),
    (23, 28),
    (15, 29),
)
COMPACT_PLAYER_DEPLOYMENTS = (
    (15, 20),
    (14, 20),
    (16, 20),
    (15, 21),
    (14, 21),
    (16, 21),
    (15, 22),
)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 10
LAST_VISIBLE_ENEMY_RECORD_INDEX = 9
COMPACT_VISIBLE_ENEMY_POSITIONS = {
    0: (15, 19),
    1: (14, 19),
    2: (16, 19),
    3: (13, 20),
    4: (17, 20),
    5: (13, 21),
    6: (17, 21),
    7: (13, 22),
    8: (17, 22),
    9: (14, 22),
}
SCENARIO_TRIGGERS = {
    0x198F06: bytes.fromhex("06 F1 00 00 05 04 19 0D 00 19 8F F6"),
    0x198F12: bytes.fromhex("07 01 00 00 04 06 04 06 00 19 90 74"),
    0x198F1E: bytes.fromhex("08 F0 00 00 0F 06 0F 06 00 19 90 82"),
}
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


def mark_runtime_group_defeated_code(group: int) -> bytes:
    record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
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
        raise ValueError("Scenario 12 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 12 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 12 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 12 deployment table")
    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected_deployments)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected_deployments:
            raise ValueError(f"{label} Scenario 12 player deployments differ")
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 12 enemy record {index} differs from Japanese source"
            )
    for offset, expected in SCENARIO_TRIGGERS.items():
        end = offset + len(expected)
        if source[offset:end] != expected:
            raise ValueError(
                f"Japanese Scenario 12 trigger at 0x{offset:06X} changed"
            )
        if probe[offset:end] != expected:
            raise ValueError(
                f"input Scenario 12 trigger at 0x{offset:06X} changed"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    compact_layout: bool = False,
    protagonist_death: bool = False,
) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    if protagonist_death and compact_layout:
        raise ValueError("protagonist-death conflicts with layout options")
    if protagonist_death:
        install_start_wrapper(
            probe,
            source,
            mark_runtime_group_defeated_code(PROTAGONIST_RUNTIME_GROUP),
        )
        return builder.update_md_checksum(probe)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        start = base + FIELD_OFFSETS["mercenaries"]
        probe[start : start + 6] = b"\xFF" * 6
    if compact_layout:
        positions = deployment_bytes(COMPACT_PLAYER_DEPLOYMENTS)
        end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(positions)
        probe[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] = positions
        for index, (x, y) in COMPACT_VISIBLE_ENEMY_POSITIONS.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[base + FIELD_OFFSETS["x"]] = x
            probe[base + FIELD_OFFSETS["y"]] = y
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 12 ROM with weakened guardians while "
            "preserving identities, classes, levels, and all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--compact-layout",
        action="store_true",
        help=(
            "diagnostic completion route only: place the seven players and "
            "ten initially visible guardians in a compact central layout; "
            "event camera transitions can expose map sprites over the HUD, "
            "so use the default stock-coordinate probe for UI evidence"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 12 deployment and fixed record, then "
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
        compact_layout=args.compact_layout,
        protagonist_death=args.protagonist_death,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "Scenario 12 defeat mode: all deployments and fixed records "
            "remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    else:
        print("Scenario 12 enemy records 0..10: AT 0, DF 0, no mercenaries")
    if args.compact_layout:
        print("diagnostic player and visible-guardian layout moved to the center")
    elif not args.protagonist_death:
        print("stock player and enemy coordinates preserved")
    if not args.protagonist_death:
        print("identities, classes, levels, hidden state, and events preserved")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
