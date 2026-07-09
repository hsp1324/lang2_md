#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_int(value: str) -> int:
    return int(value, 0)


def decompress_9dfe(data: bytes, offset: int, max_output: int = 0x8000) -> bytes | None:
    if offset + 2 > len(data):
        return None
    remaining = int.from_bytes(data[offset : offset + 2], "big")
    pos = offset + 2
    if remaining <= 0 or remaining > max_output:
        return None

    ring = bytearray([0x20] * 0x1000)
    ring_pos = 0x0FEE
    out = bytearray()
    try:
        while remaining > 0:
            flags = data[pos]
            pos += 1
            for _ in range(8):
                if flags & 1:
                    value = data[pos]
                    pos += 1
                    ring[ring_pos] = value
                    ring_pos = (ring_pos + 1) & 0x0FFF
                    out.append(value)
                    remaining -= 1
                else:
                    lo = data[pos]
                    hi = data[pos + 1]
                    pos += 2
                    src = lo | ((hi << 4) & 0x0F00)
                    count = (hi & 0x0F) + 2
                    for _ in range(count + 1):
                        value = ring[src]
                        src = (src + 1) & 0x0FFF
                        ring[ring_pos] = value
                        ring_pos = (ring_pos + 1) & 0x0FFF
                        out.append(value)
                        remaining -= 1
                        if remaining <= 0:
                            break
                flags >>= 1
                if remaining <= 0:
                    break
                if pos >= len(data):
                    return None
        return bytes(out)
    except IndexError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--start", type=parse_int, default=0)
    parser.add_argument("--end", type=parse_int, default=0x200000)
    parser.add_argument("--step", type=parse_int, default=1)
    parser.add_argument("--max-output", type=parse_int, default=0x8000)
    parser.add_argument(
        "--pointer-candidates",
        action="store_true",
        help="scan only unique 24-bit/32-bit ROM pointer values found in the ROM",
    )
    args = parser.parse_args()

    rom = args.rom.read_bytes()
    target = args.target.read_bytes()
    hits = []
    end = min(args.end, len(rom))
    if args.pointer_candidates:
        offsets: list[int] = []
        seen = set()
        for pos in range(0, len(rom) - 3, 2):
            value = int.from_bytes(rom[pos : pos + 4], "big") & 0x00FFFFFF
            if args.start <= value < end and value not in seen:
                seen.add(value)
                offsets.append(value)
        offsets.sort()
    else:
        offsets = list(range(args.start, end, args.step))

    for offset in offsets:
        out = decompress_9dfe(rom, offset, args.max_output)
        if out is None:
            continue
        pos = out.find(target)
        if pos >= 0:
            hits.append((offset, pos, len(out)))
            print(f"hit source=0x{offset:06X} output_offset=0x{pos:X} output_len=0x{len(out):X}")
    if not hits:
        print("no hits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
