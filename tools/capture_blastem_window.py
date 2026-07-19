#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
from pathlib import Path

from PIL import Image
from Xlib import X
from Xlib.display import Display


def find_blastem_window_xlib() -> int:
    display = Display()
    stack = [display.screen().root]
    while stack:
        window = stack.pop()
        try:
            name = window.get_wm_name() or ""
            cls = window.get_wm_class() or ()
            if "BlastEm" in name or "Langrisser" in name or any(
                part.lower() == "blastem" for part in cls
            ):
                return window.id
            stack.extend(window.query_tree().children)
        except Exception:
            continue
    raise RuntimeError("could not find BlastEm window via Xlib")


def find_blastem_window() -> int:
    try:
        tree = subprocess.check_output(
            ["xwininfo", "-root", "-tree"], text=True, errors="ignore"
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return find_blastem_window_xlib()
    for line in tree.splitlines():
        if "BlastEm" in line or "Langrisser" in line:
            return int(line.strip().split()[0], 16)
    return find_blastem_window_xlib()


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


def capture_with_xlib(window_id: int) -> Image.Image:
    display = Display()
    window = display.create_resource_object("window", window_id)
    geom = window.get_geometry()
    image = window.get_image(0, 0, geom.width, geom.height, X.ZPixmap, 0xFFFFFFFF)
    return Image.frombytes("RGB", (geom.width, geom.height), image.data, "raw", "BGRX")


def windows_capture_script(
    output: str,
    client_x: int,
    client_y: int,
    width: int,
    height: int,
) -> str:
    escaped_output = output.replace("'", "''")
    return f'''Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class DwmCapture {{
 [StructLayout(LayoutKind.Sequential)]
 public struct RECT {{ public int Left, Top, Right, Bottom; }}
 [DllImport("dwmapi.dll")]
 public static extern int DwmGetWindowAttribute(
  IntPtr window, int attribute, out RECT rect, int size
 );
}}
"@
$process = Get-Process |
 Where-Object {{ $_.MainWindowTitle -match 'BlastEm' }} |
 Select-Object -First 1
if (-not $process) {{ throw 'BlastEm window not found' }}
$rect = New-Object DwmCapture+RECT
$result = [DwmCapture]::DwmGetWindowAttribute(
 $process.MainWindowHandle, 9, [ref]$rect, 16
)
if ($result -ne 0) {{ throw "DwmGetWindowAttribute failed: $result" }}
$bitmap = New-Object System.Drawing.Bitmap {width},{height}
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen(
 ($rect.Left + {client_x}), ($rect.Top + {client_y}), 0, 0, $bitmap.Size
)
$bitmap.Save('{escaped_output}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
'''


def capture_with_windows_desktop(window_id: int, output: Path) -> Image.Image:
    if shutil.which("powershell.exe") is None or shutil.which("wslpath") is None:
        raise RuntimeError("Windows desktop capture is unavailable")
    display = Display()
    window = display.create_resource_object("window", window_id)
    geometry = window.get_geometry()
    windows_output = subprocess.check_output(
        ["wslpath", "-w", str(output.resolve())], text=True
    ).strip()
    script = windows_capture_script(
        windows_output,
        geometry.x,
        geometry.y,
        geometry.width,
        geometry.height,
    )
    subprocess.check_call(
        ["powershell.exe", "-NoProfile", "-Command", script]
    )
    with Image.open(output) as image:
        return image.convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    window = find_blastem_window()
    try:
        img = capture_with_windows_desktop(window, args.output)
    except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError):
        try:
            xwd = subprocess.check_output(
                ["xwd", "-silent", "-id", f"{window:#x}"]
            )
            img = read_xwd(xwd)
        except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError):
            img = capture_with_xlib(window)
    img.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
