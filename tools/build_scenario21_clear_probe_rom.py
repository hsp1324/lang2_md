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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 21 Clear Probe).md"
SCENARIO_NUMBER = 21
SCENARIO_HEADER = 0x18259E
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x1825C0
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_PLAYER_DEPLOYMENTS = (
    (7, 8), (5, 12), (9, 12), (5, 16),
    (9, 16), (5, 19), (9, 19), (7, 22),
)
COMPLETION_PLAYER_DEPLOYMENTS = (
    (37, 10), (35, 13), (2, 4), (2, 16),
    (2, 26), (31, 16), (33, 16), (35, 16),
)
COMPLETION_ENEMY_POSITIONS = {
    0: (31, 15),
    1: (33, 15),
    2: (35, 15),
    4: (31, 17),
    5: (33, 17),
    6: (35, 17),
}
LANA_POSITION = (37, 11)
KRAKEN_REVEAL_POSITIONS = ((2, 5), (1, 16), (2, 27))
ARCHMAGE_REVEAL_POSITION = (35, 14)
PROTAGONIST_DEATH_TRIGGER = 0x1A958C
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "0B 02 01 00 00 1A 97 BE"
)
PROTAGONIST_DEATH_EVENT = 0x1A97BE
PROTAGONIST_DEATH_EVENT_BYTES = bytes.fromhex(
    "02 01 02 01 00 1A 9E D8 13 FF 15 FF FF FF"
)
PROTAGONIST_DEATH_TEXT = 0x1A9ED8
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
COMPLETION_HP_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
FIRST_ENEMY_RUNTIME_GROUP = 8
LAST_ENEMY_RUNTIME_GROUP = 18
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
FIRST_ENEMY_RECORD_INDEX = 0
LAST_ENEMY_RECORD_INDEX = 10
LANA_RECORD_INDEX = 3
HIDDEN_ENEMY_RECORD_INDEXES = (7, 8, 9, 10)
PROBE_AT = 0
PROBE_DF = 0


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def deployment_bytes(positions: tuple[tuple[int, int], ...]) -> bytes:
    return b"".join(
        x.to_bytes(2, "big") + y.to_bytes(2, "big") for x, y in positions
    )


def completion_hp_wrapper_code() -> bytes:
    code = bytearray()
    for group in range(FIRST_ENEMY_RUNTIME_GROUP, LAST_ENEMY_RUNTIME_GROUP + 1):
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        # Hidden records keep X=0xFF; dead records keep HP=0. Only a currently
        # present, living diagnostic target is reduced to one HP.
        code.extend(bytes.fromhex("0C 39 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("67 12"))
        code.extend(bytes.fromhex("0C 39 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
        code.extend(bytes.fromhex("67 08"))
        code.extend(bytes.fromhex("13 FC 00 01"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
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
    if probe[COMPLETION_HP_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input diagnostic wrapper region is not empty")
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = COMPLETION_HP_WRAPPER.to_bytes(4, "big")
    probe[COMPLETION_HP_WRAPPER:wrapper_end] = wrapper


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 21 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 21 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 21 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 21 deployment table")
    expected = deployment_bytes(SOURCE_PLAYER_DEPLOYMENTS)
    end = FIRST_PLAYER_DEPLOYMENT_OFFSET + len(expected)
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if data[FIRST_PLAYER_DEPLOYMENT_OFFSET:end] != expected:
            raise ValueError(f"{label} Scenario 21 player deployments differ")
    for index in range(source_layout.record_count):
        base = source_layout.records_offset + index * FIXED_RECORD_SIZE
        end = base + FIXED_RECORD_SIZE
        if probe[base:end] != source[base:end]:
            raise ValueError(
                f"input Scenario 21 fixed record {index} differs from Japanese source"
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
                f"{label} Scenario 21 protagonist-death trigger changed"
            )
        event_end = PROTAGONIST_DEATH_EVENT + len(PROTAGONIST_DEATH_EVENT_BYTES)
        if (
            data[PROTAGONIST_DEATH_EVENT:event_end]
            != PROTAGONIST_DEATH_EVENT_BYTES
        ):
            raise ValueError(
                f"{label} Scenario 21 protagonist-death event changed"
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
        raise ValueError("Scenario 21 diagnostic modes conflict")
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
        players = deployment_bytes(COMPLETION_PLAYER_DEPLOYMENTS)
        probe[
            FIRST_PLAYER_DEPLOYMENT_OFFSET :
            FIRST_PLAYER_DEPLOYMENT_OFFSET + len(players)
        ] = players
        for index, (x, y) in COMPLETION_ENEMY_POSITIONS.items():
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            probe[enemy + FIELD_OFFSETS["x"]] = x
            probe[enemy + FIELD_OFFSETS["y"]] = y
        wrapper = completion_hp_wrapper_code()
        install_start_wrapper(probe, source, wrapper)
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 21 ROM with weakened monster groups "
            "while preserving Lana, hidden monsters, stock deployments, and "
            "all event handlers"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--completion-layout",
        action="store_true",
        help=(
            "place five players around Lana and the six visible enemies, and "
            "three players beside the stock Kraken reveal coordinates while "
            "preserving all hidden event records for completion-flow verification"
        ),
    )
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 21 deployment and fixed record, then "
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
            "Scenario 21 protagonist-death mode: stock deployments, fixed "
            "records, events, identities, and combat values preserved"
        )
        print("Start marks only runtime player group 0 defeated")
    else:
        print("Scenario 21 enemy records 0..10: AT 0, DF 0, no mercenaries")
    if args.completion_layout:
        print(
            "completion layout: five players and visible generic records "
            "0-2/4-6 compacted around source Lana; three players staged beside "
            "the stock Kraken reveal coordinates"
        )
        print("Start lowers only present, living enemy commanders to one HP")
        print(
            "source record 3 Lana and hidden records 7-10 retain source "
            "coordinates, sides, identities, and event ownership"
        )
    elif not args.protagonist_death:
        print(
            "stock deployments, identities, classes, levels, hidden events, "
            "coordinates, and handlers preserved"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
