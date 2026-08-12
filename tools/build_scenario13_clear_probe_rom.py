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
    ROOT / "roms/builds/Langrisser II (Scenario 13 Clear Probe).md"
)

SCENARIO_NUMBER = 13
SCENARIO_HEADER = 0x181720
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x181740
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (16, 3),
    (20, 2),
    (24, 2),
    (28, 3),
    (22, 4),
    (20, 6),
    (24, 6),
)
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 12
ZORUM_RECORD_INDEX = 8
VARGAS_RECORD_INDEX = 10
COMPLETION_HIDDEN_RECORD_INDICES = (*range(0, 8), 9)
COMPLETION_VARGAS_CLASS = 45  # Enemy-palette Fighter; completion probe only.
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
START_MENU_ENTRY_PATCH_SIZE = 6
COMPLETION_HP_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
ZORUM_RUNTIME_GROUP = 15
ZORUM_RUNTIME_RECORD = (
    RUNTIME_GROUP_BASE + ZORUM_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
)
VARGAS_RUNTIME_RECORD = 0xFFFF669C
RUNTIME_NAME_ID_OFFSET = 0x01
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
ZORUM_NAME_ID = 0x13
VARGAS_NAME_ID = 0x0F
SOURCE_ZORUM_POSITION = (19, 27)
PROBE_ZORUM_POSITION = (16, 4)
COMPLETION_PLAYER_POSITIONS = (
    (18, 31),
    (17, 32),
    (19, 32),
    (17, 33),
    (19, 33),
    (17, 34),
    (18, 34),
)
COMPLETION_ZORUM_POSITION = (18, 30)
COMPLETION_ENEMY_POSITIONS = (
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    (0xFF, 0xFF),
    COMPLETION_ZORUM_POSITION,
    (0xFF, 0xFF),
)
PROBE_AT = 0
PROBE_DF = 0


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def identity_guarded_hp_one_code(runtime_record: int, name_id: int) -> bytes:
    """Lower one exact live, visible actor without touching another group."""
    code = bytearray(bytes.fromhex("0C 39"))
    code.extend(name_id.to_bytes(2, "big"))
    code.extend((runtime_record + RUNTIME_NAME_ID_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("66 24"))
    code.extend(bytes.fromhex("08 39 00 07"))
    code.extend(
        (runtime_record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
    )
    code.extend(bytes.fromhex("66 1A"))
    code.extend(bytes.fromhex("4A 39"))
    code.extend((runtime_record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("67 12"))
    code.extend(bytes.fromhex("0C 39 00 FF"))
    code.extend((runtime_record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("67 08"))
    code.extend(bytes.fromhex("13 FC 00 01"))
    code.extend((runtime_record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    return bytes(code)


def completion_hp_wrapper_code() -> bytes:
    code = bytearray(
        identity_guarded_hp_one_code(ZORUM_RUNTIME_RECORD, ZORUM_NAME_ID)
    )
    code.extend(
        identity_guarded_hp_one_code(VARGAS_RUNTIME_RECORD, VARGAS_NAME_ID)
    )
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def completion_continuation_wrapper_code(source: bytes) -> bytes:
    """Return an inline trampoline for already-running battle continuations.

    A battle savestate can retain the stock Start-menu callback address in
    work RAM.  Redirecting only the callback initializer therefore does not
    affect that continuation.  This diagnostic trampoline hooks the retained
    stock entry itself, conditionally lowers only the exact live Zorum and
    Vargas records, replays the displaced stock instruction, and resumes at
    the next stock instruction.
    """
    displaced = source[
        START_MENU_ENTRY : START_MENU_ENTRY + START_MENU_ENTRY_PATCH_SIZE
    ]
    expected = bytes.fromhex("31 FC 00 00 BE AC")
    if displaced != expected:
        raise ValueError("Japanese Start-menu entry prologue changed")
    code = bytearray(
        identity_guarded_hp_one_code(ZORUM_RUNTIME_RECORD, ZORUM_NAME_ID)
    )
    code.extend(
        identity_guarded_hp_one_code(VARGAS_RUNTIME_RECORD, VARGAS_NAME_ID)
    )
    code.extend(displaced)
    code.extend(bytes.fromhex("4E F9"))
    code.extend((START_MENU_ENTRY + START_MENU_ENTRY_PATCH_SIZE).to_bytes(4, "big"))
    return bytes(code)


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
    wrapper_end = COMPLETION_HP_WRAPPER + len(wrapper)
    if (
        probe[COMPLETION_HP_WRAPPER:wrapper_end]
        != b"\xFF" * len(wrapper)
    ):
        raise ValueError("input diagnostic wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = COMPLETION_HP_WRAPPER.to_bytes(4, "big")
    probe[COMPLETION_HP_WRAPPER:wrapper_end] = wrapper


def install_continuation_start_wrapper(
    probe: bytearray,
    source: bytes,
) -> None:
    wrapper = completion_continuation_wrapper_code(source)
    entry_end = START_MENU_ENTRY + START_MENU_ENTRY_PATCH_SIZE
    expected_entry = source[START_MENU_ENTRY:entry_end]
    if probe[START_MENU_ENTRY:entry_end] != expected_entry:
        raise ValueError("input Start-menu entry prologue changed")
    wrapper_end = COMPLETION_HP_WRAPPER + len(wrapper)
    if probe[COMPLETION_HP_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input diagnostic wrapper region is not empty")
    probe[START_MENU_ENTRY:entry_end] = (
        bytes.fromhex("4E F9") + COMPLETION_HP_WRAPPER.to_bytes(4, "big")
    )
    probe[COMPLETION_HP_WRAPPER:wrapper_end] = wrapper


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 13 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 13 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 13:
        raise ValueError(
            f"unexpected Scenario 13 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 13 deployment table")

    expected_deployments = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    deployment_end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected_deployments)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end] != expected_deployments:
            raise ValueError(f"{label} Scenario 13 player deployments differ")

    for index in range(FIRST_ENEMY_RECORD_INDEX, LAST_ENEMY_RECORD_INDEX + 1):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 13 enemy record {index} differs from Japanese source"
            )


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    completion_layout: bool = False,
    completion_continuation: bool = False,
    protagonist_death: bool = False,
) -> int:
    validate_layout(probe, source)
    if completion_continuation and not completion_layout:
        raise ValueError(
            "completion-continuation requires completion-layout"
        )
    if completion_layout and protagonist_death:
        raise ValueError(
            "protagonist-death conflicts with completion-layout"
        )
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

    zorum = layout.records_offset + ZORUM_RECORD_INDEX * FIXED_RECORD_SIZE
    zorum_position = (
        COMPLETION_ZORUM_POSITION if completion_layout else PROBE_ZORUM_POSITION
    )
    probe[zorum + FIELD_OFFSETS["x"]] = zorum_position[0]
    probe[zorum + FIELD_OFFSETS["y"]] = zorum_position[1]
    if completion_layout:
        for index, position in enumerate(COMPLETION_ENEMY_POSITIONS):
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[enemy + FIELD_OFFSETS["x"]] = position[0]
            probe[enemy + FIELD_OFFSETS["y"]] = position[1]
        for index in COMPLETION_HIDDEN_RECORD_INDICES:
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[enemy] |= 0x80
        vargas = layout.records_offset + VARGAS_RECORD_INDEX * FIXED_RECORD_SIZE
        probe[vargas + FIELD_OFFSETS["class_id"]] = COMPLETION_VARGAS_CLASS
        completion_deployments = deployment_bytes(COMPLETION_PLAYER_POSITIONS)
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET :
            FIRST_PLAYER_DEPLOYMENT_OFFSET + len(completion_deployments)
        ] = completion_deployments
        if completion_continuation:
            install_continuation_start_wrapper(probe, source)
        else:
            wrapper = completion_hp_wrapper_code()
            install_start_wrapper(probe, source, wrapper)
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 13 ROM with weakened Imperial groups "
            "and Zorum beside stock Elwin while preserving identities, "
            "classes, levels, hidden reinforcements, and all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "hide the nine generic initial records, place all seven players "
            "around Vargas's arrival lane, and use a Fighter Vargas for "
            "clear-handler verification"
        ),
    )
    parser.add_argument(
        "--completion-continuation",
        action="store_true",
        help=(
            "with --completion-layout, hook the stock Start-menu entry so "
            "an already-running battle continuation that cached the stock "
            "callback still reaches the Zorum/Vargas HP diagnostic"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 13 deployment and fixed record, then "
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
        completion_continuation=args.completion_continuation,
        protagonist_death=args.protagonist_death,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "protagonist-death: all Scenario 13 deployments and fixed "
            "records preserved"
        )
        print("Start marks only runtime player group 0 defeated")
        print(f"checksum: {checksum:04X}")
        print(args.output_rom)
        return 0
    print("Scenario 13 enemy records 0..12: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print(
            "completion layout: generic records hidden, players by Vargas lane, "
            "Vargas changed to Fighter"
        )
        if args.completion_continuation:
            print(
                "continuation Start trampoline conditionally lowers live "
                "Zorum/Vargas HP to 1 before resuming the stock menu"
            )
        else:
            print(
                "Start conditionally lowers exact live Zorum/Vargas HP to 1 "
                "before stock menu"
            )
        print("identities, levels, reinforcement flags, and events preserved")
    else:
        print("Zorum moved from (19,27) to (16,4), beside stock Elwin at (16,3)")
        print(
            "identities, classes, levels, hidden reinforcements, and events "
            "preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
