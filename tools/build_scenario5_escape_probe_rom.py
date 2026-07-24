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
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06


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


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    enemy_annihilation: bool = False,
) -> int:
    validate_layout(probe, source)
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

    expected_start_entry = START_MENU_ENTRY.to_bytes(4, "big")
    for label, data in (("Japanese", source), ("input", probe)):
        if (
            data[START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4]
            != expected_start_entry
        ):
            raise ValueError(f"{label} Start-menu entry operand changed")
    wrapper = annihilation_wrapper_code()
    wrapper_end = ANNIHILATION_WRAPPER + len(wrapper)
    if probe[ANNIHILATION_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input annihilation wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = ANNIHILATION_WRAPPER.to_bytes(4, "big")
    probe[ANNIHILATION_WRAPPER:wrapper_end] = wrapper
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
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--enemy-annihilation",
        action="store_true",
        help=(
            "stage Elwin below source record 0, remove runtime groups 6..13, "
            "and lower group 5 to one HP through Start for the stock "
            "enemy-annihilation victory branch"
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
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.enemy_annihilation:
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
        print(
            "Scenario 5 first Elwin deployment: "
            f"({SOURCE_FIRST_PLAYER_X},{PROBE_FIRST_PLAYER_Y})"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
