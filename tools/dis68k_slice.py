#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000


def parse_int(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Disassemble a 68K slice from a flat ROM.")
    parser.add_argument("rom", type=Path)
    parser.add_argument("start", type=parse_int)
    parser.add_argument("length", type=parse_int, nargs="?", default=0x200)
    args = parser.parse_args()

    data = args.rom.read_bytes()
    code = data[args.start : args.start + args.length]
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    for insn in md.disasm(code, args.start):
        print(f"{insn.address:06X}: {insn.bytes.hex(' '):<18} {insn.mnemonic:<10} {insn.op_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
