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
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Scenario 1 Clear Probe).md"

SCENARIO_NUMBER = 1
SCENARIO_HEADER = 0x180196
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x1801AC
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("000B 0011")
BALD_RECORD_INDEX = 8
BALD_RECORD_OFFSET = 0x1802D8
PROBE_BALD_X = 11
PROBE_BALD_Y = 16
PROBE_BALD_AT = 0
PROBE_BALD_DF = 0
PLAYER_DEPLOYMENT_COUNT = 2
PROTAGONIST_DEATH_TRIGGER = 0x184244
PROTAGONIST_DEATH_TRIGGER_BYTES = bytes.fromhex(
    "07 02 01 00 00 18 43 9E"
)
PROTAGONIST_DEATH_HANDLER = 0x18439E
PROTAGONIST_DEATH_HANDLER_BYTES = bytes.fromhex(
    "02 01 02 01 00 18 4B 0A 13 FF 15 FF FF FF"
)
PROTAGONIST_DEATH_TEXT = 0x184B0A
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_BALD_GROUP_INDEX = PLAYER_DEPLOYMENT_COUNT + BALD_RECORD_INDEX


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def validate_layout(probe: bytes, source: bytes) -> None:
    source_layout = scenario_layout(source, SCENARIO_NUMBER)
    probe_layout = scenario_layout(probe, SCENARIO_NUMBER)
    if source_layout != probe_layout:
        raise ValueError("Scenario 1 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 1 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 12:
        raise ValueError(
            f"unexpected Scenario 1 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 1 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
            ]
            != FIRST_PLAYER_DEPLOYMENT
        ):
            raise ValueError(f"{label} first player deployment is not (11,17)")

    record_offset = source_layout.records_offset + BALD_RECORD_INDEX * FIXED_RECORD_SIZE
    if record_offset != BALD_RECORD_OFFSET:
        raise ValueError(f"unexpected Bald record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Bald record differs from Japanese source")


def protagonist_death_wrapper_code() -> bytes:
    code = bytearray()
    code.extend(bytes.fromhex("00 39 00 80"))
    code.extend(
        (RUNTIME_GROUP_BASE + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
    )
    code.extend(bytes.fromhex("13 FC 00 00"))
    code.extend((RUNTIME_GROUP_BASE + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("13 FC 00 FF"))
    code.extend((RUNTIME_GROUP_BASE + RUNTIME_X_OFFSET).to_bytes(4, "big"))
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def bald_defeat_wrapper_code() -> bytes:
    record = RUNTIME_GROUP_BASE + RUNTIME_BALD_GROUP_INDEX * RUNTIME_GROUP_SIZE
    code = bytearray()
    code.extend(bytes.fromhex("00 39 00 80"))
    code.extend((record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big"))
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


def validate_protagonist_death_event(probe: bytes, source: bytes) -> None:
    for label, data in (("Japanese", source), ("input", probe)):
        if (
            data[
                PROTAGONIST_DEATH_TRIGGER : PROTAGONIST_DEATH_TRIGGER
                + len(PROTAGONIST_DEATH_TRIGGER_BYTES)
            ]
            != PROTAGONIST_DEATH_TRIGGER_BYTES
        ):
            raise ValueError(f"{label} Scenario 1 protagonist-death trigger changed")
        if (
            data[
                PROTAGONIST_DEATH_HANDLER : PROTAGONIST_DEATH_HANDLER
                + len(PROTAGONIST_DEATH_HANDLER_BYTES)
            ]
            != PROTAGONIST_DEATH_HANDLER_BYTES
        ):
            raise ValueError(f"{label} Scenario 1 protagonist-death handler changed")


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    protagonist_death: bool = False,
    runtime_defeat_bald: bool = False,
) -> int:
    if protagonist_death and runtime_defeat_bald:
        raise ValueError("probe modes are mutually exclusive")
    validate_layout(probe, source)
    layout = scenario_layout(source, SCENARIO_NUMBER)
    if protagonist_death:
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            if probe[start:end] != source[start:end]:
                raise ValueError(
                    f"input Scenario 1 fixed record {index} differs from Japanese source"
                )
        validate_protagonist_death_event(probe, source)
        install_start_wrapper(probe, source, protagonist_death_wrapper_code())
    else:
        base = BALD_RECORD_OFFSET
        probe[base + FIELD_OFFSETS["at"]] = PROBE_BALD_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_BALD_DF
        probe[base + FIELD_OFFSETS["x"]] = PROBE_BALD_X
        probe[base + FIELD_OFFSETS["y"]] = PROBE_BALD_Y
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
        if runtime_defeat_bald:
            install_start_wrapper(
                probe,
                source,
                bald_defeat_wrapper_code(),
            )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 1 ROM with an adjacent, unguarded Bald "
            "for stock clear-dialogue and next-scenario SAVE tests"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 1 deployment and fixed record, then mark "
            "only runtime player group 0 defeated through Start"
        ),
    )
    parser.add_argument(
        "--runtime-defeat-bald",
        action="store_true",
        help=(
            "mark only the live Bald group defeated through Start so a "
            "later-turn persistence probe can enter the stock clear path"
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
        protagonist_death=args.protagonist_death,
        runtime_defeat_bald=args.runtime_defeat_bald,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "Scenario 1 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    else:
        print(
            f"Scenario 1 Bald: ({PROBE_BALD_X},{PROBE_BALD_Y}), "
            "AT 0, DF 0, no mercenaries"
        )
        if args.runtime_defeat_bald:
            print(
                "Start marks only the live Bald group defeated before opening "
                "the stock Start menu"
            )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
