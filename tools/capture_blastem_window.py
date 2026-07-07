#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import struct
import subprocess
from pathlib import Path

from PIL import Image


def find_blastem_window() -> int:
    tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True, errors="ignore")
    for line in tree.splitlines():
        if "BlastEm" in line or "Langrisser" in line:
            return int(line.strip().split()[0], 16)
    raise RuntimeError("could not find BlastEm window")


def read_xwd(data: bytes) -> Image.Image:
    for endian in (">", "<"):
        vals = struct.unpack(endian + "25I", data[:100])
        header_size, version, _, depth, width, height = vals[:6]
        if version == 7 and 100 <= header_size < len(data) and 0 < width < 10000 and 0 < height < 10000:
            break
    else:
        raise RuntimeError("could not parse XWD header")

    (
        _header_size,
        _version,
        _pixmap_format,
        _depth,
        width,
        height,
        _xoffset,
        byte_order,
        _bitmap_unit,
        _bitmap_bit_order,
        _bitmap_pad,
        bits_per_pixel,
        bytes_per_line,
        _visual_class,
        red_mask,
        green_mask,
        blue_mask,
        _bits_per_rgb,
        _colormap_entries,
        ncolors,
        *_rest,
    ) = vals

    pos = header_size + ncolors * 12
    raw = data[pos : pos + bytes_per_line * height]
    if bits_per_pixel not in (16, 24, 32):
        raise RuntimeError(f"unsupported XWD bits-per-pixel: {bits_per_pixel}")

    def mask_shift(mask: int) -> tuple[int, int]:
        if mask == 0:
            return 0, 0
        shift = 0
        while ((mask >> shift) & 1) == 0:
            shift += 1
        bits = 0
        while ((mask >> (shift + bits)) & 1) == 1:
            bits += 1
        return shift, bits

    def scale(value: int, bits: int) -> int:
        if bits <= 0:
            return 0
        return (value * 255) // ((1 << bits) - 1)

    rs, rb = mask_shift(red_mask)
    gs, gb = mask_shift(green_mask)
    bs, bb = mask_shift(blue_mask)
    order = "little" if byte_order == 0 else "big"
    bytes_per_pixel = bits_per_pixel // 8

    img = Image.new("RGB", (width, height))
    pix = img.load()
    for y in range(height):
        row = raw[y * bytes_per_line : (y + 1) * bytes_per_line]
        for x in range(width):
            off = x * bytes_per_pixel
            px = int.from_bytes(row[off : off + bytes_per_pixel], order)
            pix[x, y] = (
                scale((px & red_mask) >> rs, rb),
                scale((px & green_mask) >> gs, gb),
                scale((px & blue_mask) >> bs, bb),
            )
    return img


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    window = find_blastem_window()
    xwd = subprocess.check_output(["xwd", "-silent", "-id", f"{window:#x}"])
    img = read_xwd(xwd)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
