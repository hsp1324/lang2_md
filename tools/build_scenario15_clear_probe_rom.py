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
    ROOT / "roms/builds/Langrisser II (Scenario 15 Clear Probe).md"
)

SCENARIO_NUMBER = 15
SCENARIO_HEADER = 0x181B00
DEPLOYMENT_POINTER_OFFSET = 0x08
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
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end] != expected_deployments:
            raise ValueError(f"{label} Scenario 15 player deployments differ")

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
) -> int:
    validate_layout(probe, source)
    if completion_layout and protagonist_death:
        raise ValueError("Scenario 15 diagnostic modes conflict")
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
            "protagonist-death: all Scenario 15 deployments and fixed "
            "records preserved"
        )
        print("Start marks only runtime player group 0 defeated")
    else:
        print("Scenario 15 enemy records 1..11: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print("completion layout: Elwin moved from (3,2) to (3,20)")
        print("escape region X 1..46 / Y 21..22 and handlers preserved")
    elif not args.protagonist_death:
        print(
            "allied Scott, stock deployments, identities, classes, levels, "
            "hidden events, and handlers preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
