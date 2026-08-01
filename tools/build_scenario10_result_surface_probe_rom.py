#!/usr/bin/env python3
"""Build a Scenario 10 result-surface-only diagnostic ROM.

The probe preserves every byte from the input candidate apart from the ROM
checksum, one Start-menu target operand, and an unused tail wrapper.  Pressing
Start marks only Scenario 10's ten monster runtime groups defeated, allowing
the stock completion/reward/result path to run without modifying scenario
records or event data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.scenario_data import scenario_layout


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_OUTPUT_ROM = ROOT / "tmp/scenario10-result-surface-probe.md"

SCENARIO_NUMBER = 10
SCENARIO_HEADER = 0x181186
SCENARIO_RECORD_COUNT = 13

START_MENU_ENTRY_OPERAND = 0x00F2E0
START_MENU_ENTRY = 0x022C1E
RUNTIME_WRAPPER = 0x3FEF00

FIRST_MONSTER_RUNTIME_GROUP = 8
LAST_MONSTER_RUNTIME_GROUP = 17
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06


def result_surface_wrapper_code() -> bytes:
    """Return the unconditional runtime-only Scenario 10 finish wrapper."""
    code = bytearray()
    for group in range(
        FIRST_MONSTER_RUNTIME_GROUP,
        LAST_MONSTER_RUNTIME_GROUP + 1,
    ):
        record = RUNTIME_GROUP_BASE + group * RUNTIME_GROUP_SIZE
        # ORI.B #$80,(abs.l): mark the runtime commander record defeated.
        code.extend(bytes.fromhex("00 39 00 80"))
        code.extend(
            (record + RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big")
        )
        # MOVE.B #$00,(abs.l): clear commander HP.
        code.extend(bytes.fromhex("13 FC 00 00"))
        code.extend((record + RUNTIME_HP_OFFSET).to_bytes(4, "big"))
        # MOVE.B #$FF,(abs.l): hide the defeated runtime commander.
        code.extend(bytes.fromhex("13 FC 00 FF"))
        code.extend((record + RUNTIME_X_OFFSET).to_bytes(4, "big"))

    # Reproduce the displaced stock instruction and continue at its entry.
    code.extend(bytes.fromhex("41 F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9"))
    code.extend(START_MENU_ENTRY.to_bytes(4, "big"))
    return bytes(code)


def validate_input(data: bytes | bytearray) -> None:
    layout = scenario_layout(data, SCENARIO_NUMBER)
    if layout.header_offset != SCENARIO_HEADER:
        raise ValueError(
            f"unexpected Scenario 10 header 0x{layout.header_offset:06X}"
        )
    if layout.record_count != SCENARIO_RECORD_COUNT:
        raise ValueError(
            f"unexpected Scenario 10 fixed record count {layout.record_count}"
        )
    expected_entry = START_MENU_ENTRY.to_bytes(4, "big")
    actual_entry = data[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ]
    if actual_entry != expected_entry:
        raise ValueError("input Start-menu entry operand changed")

    wrapper = result_surface_wrapper_code()
    wrapper_end = RUNTIME_WRAPPER + len(wrapper)
    if wrapper_end > len(data):
        raise ValueError("input ROM is too short for the diagnostic wrapper")
    if data[RUNTIME_WRAPPER:wrapper_end] != b"\xFF" * len(wrapper):
        raise ValueError("input diagnostic wrapper region is not empty")


def patch_probe(probe: bytearray) -> int:
    validate_input(probe)
    wrapper = result_surface_wrapper_code()
    probe[
        START_MENU_ENTRY_OPERAND : START_MENU_ENTRY_OPERAND + 4
    ] = RUNTIME_WRAPPER.to_bytes(4, "big")
    probe[RUNTIME_WRAPPER : RUNTIME_WRAPPER + len(wrapper)] = wrapper
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a runtime-only Scenario 10 result-surface diagnostic ROM "
            "without changing any candidate scenario record or event data"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.input_rom.read_bytes()
    probe = bytearray(source)
    checksum = patch_probe(probe)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print(
        "Scenario 10 result-surface probe preserves all input scenario and "
        "event bytes"
    )
    print(
        "Start defeats only runtime monster groups 8..17; "
        f"checksum 0x{checksum:04X}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
