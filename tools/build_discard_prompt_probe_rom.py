#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_item_shop_probe_rom as shop_probe


DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Korean Discard Prompt Probe).md"
SHOP_FULL_HOOK = 0x0276AC
SHOP_FULL_HOOK_SOURCE = bytes.fromhex("41 F9 00 0A 17 7E")
NOTICE_DISMISS_CALLBACK_POINTER = 0x0261F2
NOTICE_DISMISS_CALLBACK_SOURCE = 0x00026212
PROBE_ROUTINE = 0x3F0000
PROBE_INIT_CALLBACK = 0x3F0020
PROBE_ARM_CALLBACK = 0x3F0060
PROBE_CLEAR_CALLBACK = 0x3F0080
PROBE_PLANE_CLEAR_ROUTINE = 0x3F00A0
PROBE_INPUT_CALLBACK = 0x3F00D0
SHOP_IDLE_CALLBACK = 0x0249F8
PROBE_ROUTINE_BYTES = bytes.fromhex(
    "33 FC 11 11 FF FF AE F0"  # diagnostic stage marker: shop hook entered
    "33 FC 00 01 FF FF AE 42"  # selected award item = dagger (ID 1)
    "20 3C 00 01 7C E8"        # run the complete stock award/full-item path
    "4E F9 00 00 85 EE"
)
PROBE_INIT_CALLBACK_BYTES = bytes.fromhex(
    "33 FC 22 22 FF FF AE F2"  # diagnostic stage marker: notice returned
    "4A 38 81 79"              # wait until the confirmation input is released
    "66 00 00 22"
    "4E B9 00 02 C2 A6"        # clear transient window/sprite state
    "4E B9 00 02 40 EC"
    "4E B9 00 2B 84 40"        # reload current production item-name glyphs
    "4E B9 00 01 7D 5E"        # initialize stock discard selection
    "21 FC 00 3F 00 60 80 04"  # render one input-free frame before arming it
    "4E 75"
)
PROBE_ARM_CALLBACK_BYTES = bytes.fromhex(
    "33 FC 33 33 FF FF AE F4"  # diagnostic stage marker: selection armed
    "42 38 81 79"              # consume any transition input still latched
    "21 FC 00 3F 00 D0 80 04"  # arm the instrumented stock callback
    "4E F9 00 01 7F 08"        # render the selection without reading input
)
PROBE_CLEAR_CALLBACK_BYTES = bytes.fromhex(
    "4E B9 00 3F 00 A0"        # clear Plane A behind the dormant sprite UI
    "21 FC 00 3F 00 20 80 04"  # enter discard initialization after clearing
    "20 3C 00 00 DA 7A"        # stock window-clear transition
    "4E F9 00 00 85 EE"
)
PROBE_PLANE_CLEAR_ROUTINE_BYTES = bytes.fromhex(
    "33 FC 8F 02 00 C0 00 04"  # VDP auto-increment = one word
    "23 FC 40 00 00 03 00 C0 00 04"  # VRAM write at Plane A 0xC000
    "30 3C 80 00"              # blank tile with UI priority/palette
    "32 3C 07 FF"              # 64 x 32 name-table words
    "33 C0 00 C0 00 00"
    "51 C9 FF F8"
    "4E 75"
)
PROBE_INPUT_CALLBACK_BYTES = bytes.fromhex(
    "10 38 81 79"              # remember the last nonzero input edge
    "67 00 00 06"
    "11 C0 AE F6"
    "08 00 00 05"              # do not lose C at the next VBlank boundary
    "66 00 00 08"
    "4E F9 00 01 7E 04"        # preserve stock movement behavior
    "33 FC 44 44 FF FF AE F8"  # confirm branch entered
    "4E B9 00 01 7E C4"        # run the stock confirmation branch
    "23 F8 80 04 FF FF AE E0"  # callback immediately after stock pop
    "23 F8 80 00 FF FF AE E4"  # callback-stack pointer after stock pop
    "42 38 81 79"              # prevent the same C edge buying again
    "21 FC 00 02 49 F8 80 04"  # diagnostic returns to the idle shop
    "33 FC 55 55 FF FF AE FA"  # stock confirmation returned
    "4E 75"
)


def patch_probe(probe: bytearray, source: bytes) -> int:
    # Reuse the original complete secret list and zero-price diagnostic so 40
    # owned slots can be reached without editing a save by hand.
    shop_probe.patch_probe(probe, source, free_prices=True)
    if source[SHOP_FULL_HOOK : SHOP_FULL_HOOK + len(SHOP_FULL_HOOK_SOURCE)] != SHOP_FULL_HOOK_SOURCE:
        raise ValueError("Japanese full-inventory shop branch changed")
    if probe[SHOP_FULL_HOOK : SHOP_FULL_HOOK + len(SHOP_FULL_HOOK_SOURCE)] != SHOP_FULL_HOOK_SOURCE:
        raise ValueError("input full-inventory shop branch changed")
    if builder.be32(source, NOTICE_DISMISS_CALLBACK_POINTER) != NOTICE_DISMISS_CALLBACK_SOURCE:
        raise ValueError("Japanese full-inventory notice dismiss callback changed")
    if builder.be32(probe, NOTICE_DISMISS_CALLBACK_POINTER) != NOTICE_DISMISS_CALLBACK_SOURCE:
        raise ValueError("input full-inventory notice dismiss callback changed")
    init_end = PROBE_INIT_CALLBACK + len(PROBE_INIT_CALLBACK_BYTES)
    arm_end = PROBE_ARM_CALLBACK + len(PROBE_ARM_CALLBACK_BYTES)
    clear_end = PROBE_CLEAR_CALLBACK + len(PROBE_CLEAR_CALLBACK_BYTES)
    plane_end = PROBE_PLANE_CLEAR_ROUTINE + len(PROBE_PLANE_CLEAR_ROUTINE_BYTES)
    input_end = PROBE_INPUT_CALLBACK + len(PROBE_INPUT_CALLBACK_BYTES)
    if any(value != 0xFF for value in probe[PROBE_ROUTINE:input_end]):
        raise ValueError("discard prompt probe routine area is not blank")
    probe[PROBE_ROUTINE : PROBE_ROUTINE + len(PROBE_ROUTINE_BYTES)] = (
        PROBE_ROUTINE_BYTES
    )
    probe[PROBE_INIT_CALLBACK:init_end] = PROBE_INIT_CALLBACK_BYTES
    probe[PROBE_ARM_CALLBACK:arm_end] = PROBE_ARM_CALLBACK_BYTES
    probe[PROBE_CLEAR_CALLBACK:clear_end] = PROBE_CLEAR_CALLBACK_BYTES
    probe[PROBE_PLANE_CLEAR_ROUTINE:plane_end] = PROBE_PLANE_CLEAR_ROUTINE_BYTES
    probe[PROBE_INPUT_CALLBACK:input_end] = PROBE_INPUT_CALLBACK_BYTES
    probe[SHOP_FULL_HOOK : SHOP_FULL_HOOK + len(SHOP_FULL_HOOK_SOURCE)] = (
        bytes.fromhex("4E F9") + PROBE_ROUTINE.to_bytes(4, "big")
    )
    builder.put32(
        probe, NOTICE_DISMISS_CALLBACK_POINTER, PROBE_CLEAR_CALLBACK
    )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored 0P all-item shop probe whose full-inventory "
            "branch enters the stock discard-selection renderer"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=ROOT / builder.OUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=ROOT / builder.IN_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(probe, source)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print("full inventory runs stock award transition and discard selection; award item ID: 1")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
