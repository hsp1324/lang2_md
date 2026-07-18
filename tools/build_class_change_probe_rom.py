#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean Class Change Probe).md"
)

LEVEL_UP_HANDLER = 0x01480C
END_TURN_LEVEL_UP_ENTRY_OPERAND = 0x00D748
PROBE_WRAPPER = 0x3FF000
START_MENU_ENTRY = 0x022C1E
START_MENU_ENTRY_OPERAND = 0x00F2E0
START_MENU_PROBE_WRAPPER = 0x3FF040
ELWIN_RUNTIME_RECORD = 0xFFFF603C
ELWIN_CLASS_OFFSET = 0x00
ELWIN_LEVEL_OFFSET = 0x2E
ELWIN_EXPERIENCE_OFFSET = 0x2F
ELWIN_FIGHTER_CLASS = 0x01
PROBE_LEVEL = 9
PROBE_EXPERIENCE = 16


def wrapper_code() -> bytes:
    # Only the initial Fighter is modified. After the first confirmed class
    # change, later turn endings pass through to the stock handler unchanged.
    return bytes.fromhex(
        "0C 39 00 01 FF FF 60 3C"  # cmpi.b #1,$FFFF603C.l
        "66 00 00 12"              # bne.w stock_handler
        "13 FC 00 09 FF FF 60 6A"  # move.b #9,$FFFF606A.l
        "13 FC 00 10 FF FF 60 6B"  # move.b #16,$FFFF606B.l
        "4E F9 00 01 48 0C"        # jmp $01480C.l
    )


def start_menu_wrapper_code() -> bytes:
    # Reproduce the candidate array built by the stock level-up routine for
    # Fighter Elwin: commander ID 1, then Lord/Knight/Shaman and sentinels.
    return bytes.fromhex(
        "41 F9 FF FF AA 00"  # lea $FFFFAA00.l,a0
        "30 FC 00 01"        # commander ID 1
        "30 FC 00 04"        # Lord
        "30 FC 00 05"        # Knight
        "30 FC 00 0A"        # Shaman
        "30 FC FF FF"
        "30 FC FF FF"
        "30 FC FF FF"
        "30 FC FF FF"
        "43 F9 FF FF 60 3C"  # lea $FFFF603C.l,a1
        "4E F9 00 02 BB 48"  # jmp stock class-change UI
    )


def patch_probe(probe: bytearray, source: bytes) -> int:
    expected = LEVEL_UP_HANDLER.to_bytes(4, "big")
    offset = END_TURN_LEVEL_UP_ENTRY_OPERAND
    if source[offset : offset + 4] != expected:
        raise ValueError("Japanese end-turn level-up operand changed")
    if probe[offset : offset + 4] != expected:
        raise ValueError("input end-turn level-up operand changed")

    code = wrapper_code()
    wrapper_end = PROBE_WRAPPER + len(code)
    if probe[PROBE_WRAPPER:wrapper_end] != b"\xFF" * len(code):
        raise ValueError("input probe wrapper region is not empty")

    probe[offset : offset + 4] = PROBE_WRAPPER.to_bytes(4, "big")
    probe[PROBE_WRAPPER:wrapper_end] = code

    start_expected = START_MENU_ENTRY.to_bytes(4, "big")
    start_offset = START_MENU_ENTRY_OPERAND
    if source[start_offset : start_offset + 4] != start_expected:
        raise ValueError("Japanese Start-menu entry operand changed")
    if probe[start_offset : start_offset + 4] != start_expected:
        raise ValueError("input Start-menu entry operand changed")
    start_code = start_menu_wrapper_code()
    start_wrapper_end = START_MENU_PROBE_WRAPPER + len(start_code)
    if (
        probe[START_MENU_PROBE_WRAPPER:start_wrapper_end]
        != b"\xFF" * len(start_code)
    ):
        raise ValueError("input Start-menu probe wrapper region is not empty")
    probe[start_offset : start_offset + 4] = START_MENU_PROBE_WRAPPER.to_bytes(
        4, "big"
    )
    probe[START_MENU_PROBE_WRAPPER:start_wrapper_end] = start_code
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored diagnostic ROM that gives Fighter Elwin exactly "
            "enough progress to trigger the stock class-change handler at the "
            "next end-turn level-up pass. Pressing Start on a command-ready "
            "map also opens the same UI with Elwin's source-derived candidates."
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(probe, source)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print(
        "end-turn level-up handler redirected through Fighter Elwin "
        f"LV{PROBE_LEVEL}/EXP{PROBE_EXPERIENCE} probe"
    )
    print("Start opens Fighter Elwin's stock Lord/Knight/Shaman selector")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
