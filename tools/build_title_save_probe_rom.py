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
    ROOT / "roms/builds/Langrisser II (Korean Title Save Probe).md"
)

TITLE_LOAD_ENTRY = 0x029D76
TITLE_SAVE_ENTRY = 0x029B70
# The title main-menu LOAD wrapper contains a MOVE.L immediate and a final
# JMP. Their four-byte operands both point to the stock LOAD renderer.
TITLE_LOAD_ENTRY_OPERANDS = (0x02A40C, 0x02A41C)


def patch_probe(probe: bytearray, source: bytes) -> int:
    expected = TITLE_LOAD_ENTRY.to_bytes(4, "big")
    replacement = TITLE_SAVE_ENTRY.to_bytes(4, "big")
    for offset in TITLE_LOAD_ENTRY_OPERANDS:
        if source[offset : offset + 4] != expected:
            raise ValueError(
                f"Japanese title LOAD operand changed at 0x{offset:06X}"
            )
        if probe[offset : offset + 4] != expected:
            raise ValueError(
                f"input title LOAD operand changed at 0x{offset:06X}"
            )
        probe[offset : offset + 4] = replacement
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored diagnostic ROM that enters the stock title SAVE "
            "renderer from the title LOAD menu. Dynamic save data is not valid "
            "outside the normal scenario-clear path; use this only to verify "
            "fixed text ownership and rendering."
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
        "title LOAD operands redirected to stock SAVE renderer "
        f"0x{TITLE_SAVE_ENTRY:06X}"
    )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
