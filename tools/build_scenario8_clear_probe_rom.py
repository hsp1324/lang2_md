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
    ROOT / "roms/builds/Langrisser II (Scenario 8 Clear Probe).md"
)

SCENARIO_NUMBER = 8
SCENARIO_HEADER = 0x180DA6
DEPLOYMENT_POINTER_OFFSET = 0x08
DEPLOYMENT_TABLE = 0x180DC6
FIRST_PLAYER_DEPLOYMENT_OFFSET = DEPLOYMENT_TABLE + 0x02
SOURCE_FIRST_PLAYER_DEPLOYMENT = bytes.fromhex("0002 0007")
KRAMER_RECORD_INDEX = 5
KRAMER_RECORD_OFFSET = 0x180E9A
SOURCE_KRAMER_X = 38
SOURCE_KRAMER_Y = 8
PROBE_KRAMER_X = 2
PROBE_KRAMER_Y = 6
PROBE_KRAMER_AT = 0
PROBE_KRAMER_DF = 0
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
RUNTIME_WRAPPER = 0x3FEF00
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
PROTAGONIST_RUNTIME_GROUP = 0
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
RUNTIME_TURN_COUNTER = 0xFFFFA5F1
TIMEOUT_LAST_ALLOWED_TURN = 23


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def protagonist_death_wrapper_code() -> bytes:
    protagonist = (
        RUNTIME_GROUP_BASE + PROTAGONIST_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    )
    code = bytearray()
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


def timeout_wrapper_code() -> bytes:
    code = bytearray(bytes.fromhex("13 FC"))
    code.extend(TIMEOUT_LAST_ALLOWED_TURN.to_bytes(2, "big"))
    code.extend(RUNTIME_TURN_COUNTER.to_bytes(4, "big"))
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
        raise ValueError("Scenario 8 layout differs from Japanese source")
    if source_layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 8 header 0x{source_layout.header_offset:06X}"
        )
    if source_layout.record_count != 11:
        raise ValueError(
            f"unexpected Scenario 8 fixed record count {source_layout.record_count}"
        )
    if be32(source, SCENARIO_HEADER + DEPLOYMENT_POINTER_OFFSET) != DEPLOYMENT_TABLE:
        raise ValueError("unexpected Japanese Scenario 8 deployment table")
    for label, data in (("Japanese source", source), ("input ROM", probe)):
        if (
            data[
                FIRST_PLAYER_DEPLOYMENT_OFFSET : FIRST_PLAYER_DEPLOYMENT_OFFSET + 4
            ]
            != SOURCE_FIRST_PLAYER_DEPLOYMENT
        ):
            raise ValueError(f"{label} first player deployment is not (2,7)")

    record_offset = (
        source_layout.records_offset + KRAMER_RECORD_INDEX * FIXED_RECORD_SIZE
    )
    if record_offset != KRAMER_RECORD_OFFSET:
        raise ValueError(f"unexpected Kramer record 0x{record_offset:06X}")
    end = record_offset + FIXED_RECORD_SIZE
    if probe[record_offset:end] != source[record_offset:end]:
        raise ValueError("input Kramer record differs from Japanese source")
    if (
        source[record_offset + FIELD_OFFSETS["x"]] != SOURCE_KRAMER_X
        or source[record_offset + FIELD_OFFSETS["y"]] != SOURCE_KRAMER_Y
    ):
        raise ValueError("unexpected Japanese Scenario 8 Kramer coordinates")


def patch_probe(
    probe: bytearray,
    source: bytes,
    *,
    protagonist_death: bool = False,
    timeout: bool = False,
) -> int:
    validate_layout(probe, source)
    if protagonist_death and timeout:
        raise ValueError("protagonist-death and timeout modes conflict")
    if protagonist_death or timeout:
        layout = scenario_layout(source, SCENARIO_NUMBER)
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            if probe[start:end] != source[start:end]:
                raise ValueError(
                    f"input Scenario 8 fixed record {index} differs from Japanese source"
                )
        wrapper = (
            protagonist_death_wrapper_code()
            if protagonist_death
            else timeout_wrapper_code()
        )
        install_start_wrapper(probe, source, wrapper)
    else:
        base = KRAMER_RECORD_OFFSET
        probe[base + FIELD_OFFSETS["at"]] = PROBE_KRAMER_AT
        probe[base + FIELD_OFFSETS["df"]] = PROBE_KRAMER_DF
        probe[base + FIELD_OFFSETS["x"]] = PROBE_KRAMER_X
        probe[base + FIELD_OFFSETS["y"]] = PROBE_KRAMER_Y
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        probe[mercenary_offset : mercenary_offset + 6] = b"\xFF" * 6
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Scenario 8 ROM with an unguarded Kramer next to "
            "the stock Elwin deployment for a normal-command completion"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--protagonist-death",
        action="store_true",
        help=(
            "preserve every Scenario 8 fixed record and mark only runtime "
            "player group 0 defeated through Start"
        ),
    )
    mode.add_argument(
        "--timeout",
        action="store_true",
        help=(
            "preserve every Scenario 8 fixed record and set the verified "
            "runtime turn counter to the final allowed turn through Start"
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
        timeout=args.timeout,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    if args.protagonist_death:
        print(
            "Scenario 8 protagonist-death mode: all deployments and fixed "
            "records remain source-identical"
        )
        print(
            "Start marks only runtime player group 0 defeated, then returns "
            "to the stock Start handler"
        )
    elif args.timeout:
        print(
            "Scenario 8 timeout mode: all deployments and fixed records "
            "remain source-identical"
        )
        print(
            "Start sets the verified runtime turn counter to 23, then returns "
            "to the stock Start handler"
        )
    else:
        print(
            f"Scenario 8 Kramer: ({PROBE_KRAMER_X},{PROBE_KRAMER_Y}), "
            "AT 0, DF 0, no mercenaries"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
