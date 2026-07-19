#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.class_change_data import (
    ClassTransition,
    read_class_change_chain,
    transition_for_class,
)


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
RUNTIME_RECORD_BASE = 0xFFFF603C
RUNTIME_RECORD_SIZE = 0x60
PLAYER_RUNTIME_RECORD_COUNT = 10
ELWIN_CLASS_OFFSET = 0x00
ELWIN_LEVEL_OFFSET = 0x2E
ELWIN_EXPERIENCE_OFFSET = 0x2F
ELWIN_FIGHTER_CLASS = 0x01
PROBE_LEVEL = 9
PROBE_EXPERIENCE = 16


def runtime_record_address(runtime_record_index: int) -> int:
    if not 0 <= runtime_record_index < PLAYER_RUNTIME_RECORD_COUNT:
        raise ValueError("runtime record index must be 0..9")
    return RUNTIME_RECORD_BASE + runtime_record_index * RUNTIME_RECORD_SIZE


def wrapper_code(
    runtime_record_index: int = 0,
    expected_class: int = ELWIN_FIGHTER_CLASS,
) -> bytes:
    if not 0 <= expected_class <= 0xFF:
        raise ValueError("expected class ID must fit one byte")
    record = runtime_record_address(runtime_record_index)
    code = bytearray(bytes.fromhex("0C 39"))
    code.extend(expected_class.to_bytes(2, "big"))
    code.extend(record.to_bytes(4, "big"))
    code.extend(bytes.fromhex("66 00 00 12"))
    for value, field_offset in (
        (PROBE_LEVEL, ELWIN_LEVEL_OFFSET),
        (PROBE_EXPERIENCE, ELWIN_EXPERIENCE_OFFSET),
    ):
        code.extend(bytes.fromhex("13 FC"))
        code.extend(value.to_bytes(2, "big"))
        code.extend((record + field_offset).to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9 00 01 48 0C"))
    return bytes(code)


def start_menu_wrapper_code(
    commander_id: int = 1,
    candidates: tuple[int, ...] = (4, 5, 10),
    runtime_record_index: int = 0,
) -> bytes:
    if not 1 <= commander_id <= 10:
        raise ValueError("commander ID must be 1..10")
    if not 1 <= len(candidates) <= 3:
        raise ValueError("class-change probe needs 1..3 candidates")
    if any(not 0 <= candidate <= 0xFFFF for candidate in candidates):
        raise ValueError("candidate class ID must fit one word")

    # Reproduce the eight-word candidate array built by the stock level-up
    # routine: commander ID, up to three classes, then FFFF sentinels.
    values = [commander_id, *candidates]
    values.extend([0xFFFF] * (8 - len(values)))
    code = bytearray(bytes.fromhex("41 F9 FF FF AA 00"))
    for value in values:
        code.extend(bytes.fromhex("30 FC"))
        code.extend(value.to_bytes(2, "big"))
    runtime_record = runtime_record_address(runtime_record_index)
    code.extend(bytes.fromhex("43 F9"))
    code.extend(runtime_record.to_bytes(4, "big"))
    code.extend(bytes.fromhex("4E F9 00 02 BB 48"))
    return bytes(code)


def selected_transition(
    source: bytes, commander_id: int, current_class: int | None
) -> ClassTransition:
    if current_class is None:
        return read_class_change_chain(source, commander_id)[0]
    return transition_for_class(source, commander_id, current_class)


def patch_probe(
    probe: bytearray,
    source: bytes,
    commander_id: int = 1,
    current_class: int | None = None,
    runtime_record_index: int = 0,
    enable_start_menu_probe: bool = True,
) -> int:
    transition = selected_transition(source, commander_id, current_class)
    expected = LEVEL_UP_HANDLER.to_bytes(4, "big")
    offset = END_TURN_LEVEL_UP_ENTRY_OPERAND
    if source[offset : offset + 4] != expected:
        raise ValueError("Japanese end-turn level-up operand changed")
    if probe[offset : offset + 4] != expected:
        raise ValueError("input end-turn level-up operand changed")

    code = wrapper_code(
        runtime_record_index=runtime_record_index,
        expected_class=transition.current_class,
    )
    wrapper_end = PROBE_WRAPPER + len(code)
    if probe[PROBE_WRAPPER:wrapper_end] != b"\xFF" * len(code):
        raise ValueError("input probe wrapper region is not empty")

    probe[offset : offset + 4] = PROBE_WRAPPER.to_bytes(4, "big")
    probe[PROBE_WRAPPER:wrapper_end] = code

    if enable_start_menu_probe:
        start_expected = START_MENU_ENTRY.to_bytes(4, "big")
        start_offset = START_MENU_ENTRY_OPERAND
        if source[start_offset : start_offset + 4] != start_expected:
            raise ValueError("Japanese Start-menu entry operand changed")
        if probe[start_offset : start_offset + 4] != start_expected:
            raise ValueError("input Start-menu entry operand changed")
        start_code = start_menu_wrapper_code(
            commander_id,
            transition.candidates,
            runtime_record_index=runtime_record_index,
        )
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
            "Build an ignored diagnostic ROM that gives one selected active "
            "commander exactly enough progress to trigger the stock class-change "
            "handler at the next end-turn level-up pass. Pressing Start on a "
            "command-ready map also opens the same UI with that commander's "
            "source-derived candidates."
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument("--commander-id", type=int, default=1)
    parser.add_argument(
        "--runtime-record-index",
        type=int,
        default=0,
        help=(
            "active player runtime record index (0..9); independent of the "
            "source class-chain commander ID"
        ),
    )
    parser.add_argument(
        "--end-turn-only",
        action="store_true",
        help="preserve the normal Start menu and install only the end-turn trigger",
    )
    parser.add_argument(
        "--current-class",
        type=lambda value: int(value, 0),
        help="source class ID; defaults to the commander's initial class",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    transition = selected_transition(source, args.commander_id, args.current_class)
    checksum = patch_probe(
        probe,
        source,
        commander_id=args.commander_id,
        current_class=transition.current_class,
        runtime_record_index=args.runtime_record_index,
        enable_start_menu_probe=not args.end_turn_only,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print(
        "end-turn level-up handler redirected through runtime record "
        f"{args.runtime_record_index} class 0x{transition.current_class:02X} "
        f"LV{PROBE_LEVEL}/EXP{PROBE_EXPERIENCE} probe"
    )
    candidates = "/".join(f"0x{value:02X}" for value in transition.candidates)
    if args.end_turn_only:
        print("normal Start menu preserved for end-turn application verification")
    else:
        print(
            f"Start opens commander {args.commander_id} class "
            f"0x{transition.current_class:02X} candidates {candidates} using "
            f"runtime record {args.runtime_record_index}"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
