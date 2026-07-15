#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.game_genie import GameGeniePatch, decode_genesis_game_genie


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = ROOT / "roms/builds/Langrisser II (Game Genie Probe).md"
REV00_SHA1 = "4bbc2502784a61eedf45eca5303dc68062964ff4"


def apply_patches(
    probe: bytearray,
    source: bytes,
    patches: list[GameGeniePatch],
) -> int:
    seen_addresses: set[int] = set()
    for patch in patches:
        if patch.address & 1:
            raise ValueError(
                f"{patch.code} targets odd 68000 address 0x{patch.address:06X}"
            )
        if patch.address + 2 > len(source) or patch.address + 2 > len(probe):
            raise ValueError(
                f"{patch.code} target 0x{patch.address:06X} is outside the ROM"
            )
        if patch.address in seen_addresses:
            raise ValueError(f"duplicate Game Genie target 0x{patch.address:06X}")
        seen_addresses.add(patch.address)

        end = patch.address + 2
        source_word = source[patch.address:end]
        input_word = probe[patch.address:end]
        if input_word != source_word:
            raise ValueError(
                f"{patch.code} input word at 0x{patch.address:06X} differs from "
                f"Japanese source: {input_word.hex().upper()} != "
                f"{source_word.hex().upper()}"
            )
        probe[patch.address:end] = patch.value.to_bytes(2, "big")
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored Korean UI probe ROM from decoded Genesis Game "
            "Genie patches; never use this output as a distributable build. "
            "Codes are revision-specific and this tool does not infer their "
            "compatibility."
        ),
        epilog=(
            "The project source ROM is Japanese REV00. Published REV01 codes "
            "can decode to valid addresses and still crash REV00."
        ),
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument("--code", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    codes = args.code
    if not codes:
        raise ValueError("at least one explicit --code is required")

    patches = [decode_genesis_game_genie(code) for code in codes]
    source = args.source_rom.read_bytes()
    source_sha1 = hashlib.sha1(source).hexdigest()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = apply_patches(probe, source, patches)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    for patch in patches:
        print(f"{patch.code}: 0x{patch.address:06X} -> {patch.value:04X}")
    revision = "Japanese REV00" if source_sha1 == REV00_SHA1 else "unknown revision"
    print(f"source: {revision} ({source_sha1})")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
