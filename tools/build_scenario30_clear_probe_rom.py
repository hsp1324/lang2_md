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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 30 Clear Probe).md"
SCENARIO_NUMBER = 30
SCENARIO_HEADER = 0x183594
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x1835B8
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (15, 18),
    (17, 20),
    (15, 22),
    (18, 23),
    (14, 25),
    (18, 26),
    (13, 28),
    (15, 29),
    (19, 29),
)
COMPLETION_PLAYER_DEPLOYMENTS = (
    (15, 7),
    *SOURCE_PLAYER_DEPLOYMENTS[1:],
)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 10
GREAT_DRAGON_RECORD_INDEX = 0
VISIBLE_WITCH_RECORD_INDEX = 9
HIDDEN_WITCH_RECORD_INDEX = 10
COMPLETION_TARGET_RECORD_INDEX = VISIBLE_WITCH_RECORD_INDEX
PROBE_AT = 0
PROBE_DF = 0
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
COMPLETION_HP_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
FIRST_FIXED_RUNTIME_GROUP = len(SOURCE_PLAYER_DEPLOYMENTS)
COMPLETION_TARGET_RUNTIME_GROUP = (
    FIRST_FIXED_RUNTIME_GROUP + COMPLETION_TARGET_RECORD_INDEX
)
COMPLETION_HIDDEN_RUNTIME_GROUPS = tuple(
    range(FIRST_FIXED_RUNTIME_GROUP, COMPLETION_TARGET_RUNTIME_GROUP)
)
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
ACCEPTED_COMPLETION_CHECKSUM = 0x8386


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def completion_hp_wrapper_code() -> bytes:
    code = bytearray()
    for group in COMPLETION_HIDDEN_RUNTIME_GROUPS:
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    target = (
        RUNTIME_GROUP_BASE
        + COMPLETION_TARGET_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
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
        raise ValueError("Scenario 30 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 30 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 30 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 30 deployment table")
    expected = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 30 player deployments differ")
    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 30 fixed record {index} differs from Japanese source"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_target_only: bool = False,
) -> int:
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        probe[base + FIELD_OFFSETS["at"]] = PROBE_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_DF
        mercenaries = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenaries : mercenaries + 6] = b"\xFF" * 6
    if completion_target_only:
        completion_deployments = deployment_bytes(
            COMPLETION_PLAYER_DEPLOYMENTS
        )
        completion_end = (
            FIRST_PLAYER_DEPLOYMENT_OFFSET + len(completion_deployments)
        )
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET:completion_end
        ] = completion_deployments
        expected_start_entry = START_MENU_ENTRY.to_bytes(4, "big")
        if source[
            START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
        ] != expected_start_entry:
            raise ValueError("Japanese Start-menu entry operand changed")
        if probe[
            START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
        ] != expected_start_entry:
            raise ValueError("input Start-menu entry operand changed")
        wrapper = completion_hp_wrapper_code()
        wrapper_end = COMPLETION_HP_WRAPPER + len(wrapper)
        if probe[COMPLETION_HP_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
            raise ValueError("input completion wrapper region is not empty")
        probe[
            START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
        ] = COMPLETION_HP_WRAPPER.to_bytes(4, "big")
        probe[COMPLETION_HP_WRAPPER:wrapper_end] = wrapper
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 30 ROM with weakened Great Dragon and "
            "witch groups while preserving stock deployments, hidden state, "
            "identities, classes, and event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-target-only",
        action="store_true",
        help=(
            "stage only the first Elwin deployment below source-position Mina, "
            "remove runtime groups 9..17, and lower group 18 Mina to one HP "
            "when Start is opened"
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
        completion_target_only=args.completion_target_only,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print("Scenario 30 enemy records 0..10: AT 0, DF 0, no mercenaries")
    print(
        "stock deployments, visible/hidden witch distinction, identities, "
        "classes, and all handlers preserved"
    )
    if args.completion_target_only:
        print(
            "only the first Elwin deployment is staged at "
            f"{COMPLETION_PLAYER_DEPLOYMENTS[0]}; visible Mina stays at the "
            "Japanese-source position"
        )
        print(
            "Start hides and defeats runtime groups 9..17, then lowers only "
            "present, living group 18 Mina to one HP; hidden record 10 stays "
            "source-identical"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
