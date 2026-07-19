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
    outer_width: int,
    outer_height: int,
) -> str:
    escaped_output = output.replace("'", "''")
    return f'''$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
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
$scaleX = ($rect.Right - $rect.Left) / {outer_width}.0
$scaleY = ($rect.Bottom - $rect.Top) / {outer_height}.0
[int]$captureX = [Math]::Round({client_x} * $scaleX)
[int]$captureY = [Math]::Round({client_y} * $scaleY)
[int]$captureWidth = [Math]::Round({width} * $scaleX)
[int]$captureHeight = [Math]::Round({height} * $scaleY)
$bitmap = New-Object System.Drawing.Bitmap $captureWidth,$captureHeight
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen(
 ($rect.Left + $captureX), ($rect.Top + $captureY), 0, 0, $bitmap.Size
)
$bitmap.Save('{escaped_output}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
'''


def windows_print_capture_script(output: str) -> str:
    escaped_output = output.replace("'", "''")
    return f'''$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WindowPrintCapture {{
 [StructLayout(LayoutKind.Sequential)]
 public struct RECT {{ public int Left, Top, Right, Bottom; }}
 [DllImport("dwmapi.dll")]
 public static extern int DwmGetWindowAttribute(
  IntPtr window, int attribute, out RECT rect, int size
 );
 [DllImport("user32.dll")]
 public static extern bool PrintWindow(IntPtr window, IntPtr hdc, uint flags);
}}
"@
$process = Get-Process |
 Where-Object {{ $_.MainWindowTitle -match 'BlastEm' }} |
 Select-Object -First 1
if (-not $process) {{ throw 'BlastEm window not found' }}
$rect = New-Object WindowPrintCapture+RECT
$result = [WindowPrintCapture]::DwmGetWindowAttribute(
 $process.MainWindowHandle, 9, [ref]$rect, 16
)
if ($result -ne 0) {{ throw "DwmGetWindowAttribute failed: $result" }}
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
$bitmap = New-Object System.Drawing.Bitmap $width,$height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
$ok = [WindowPrintCapture]::PrintWindow($process.MainWindowHandle, $hdc, 2)
$graphics.ReleaseHdc($hdc)
if (-not $ok) {{ throw 'PrintWindow failed' }}
$bitmap.Save('{escaped_output}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
'''


def windows_activate_script() -> str:
    return '''$ErrorActionPreference = 'Stop'
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WindowActivation {
 [DllImport("user32.dll")]
 public static extern bool ShowWindow(IntPtr window, int command);
 [DllImport("user32.dll")]
 public static extern bool SetForegroundWindow(IntPtr window);
}
"@
$process = Get-Process |
 Where-Object { $_.MainWindowTitle -match 'BlastEm' } |
 Select-Object -First 1
if (-not $process) { throw 'BlastEm window not found' }
[WindowActivation]::ShowWindow($process.MainWindowHandle, 9) | Out-Null
[WindowActivation]::SetForegroundWindow($process.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 300
'''


def activate_windows_window() -> None:
    if shutil.which("powershell.exe") is None:
        raise RuntimeError("Windows window activation is unavailable")
    subprocess.check_call(
        ["powershell.exe", "-NoProfile", "-Command", windows_activate_script()]
    )


def crop_printed_client(
    image: Image.Image,
    client_x: int,
    client_y: int,
    client_width: int,
    client_height: int,
    outer_width: int,
    outer_height: int,
) -> Image.Image:
    if outer_width <= 0 or outer_height <= 0:
        raise RuntimeError("invalid X11 outer-window geometry")
    scale_x = image.width / outer_width
    scale_y = image.height / outer_height
    if not 0.5 <= scale_x <= 4.0 or not 0.5 <= scale_y <= 4.0:
        raise RuntimeError("Windows/X11 window scale is outside the supported range")
    if abs(scale_x - scale_y) > 0.05:
        raise RuntimeError("Windows/X11 window scale is not uniform")
    left = round(client_x * scale_x)
    top = round(client_y * scale_y)
    right = round((client_x + client_width) * scale_x)
    bottom = round((client_y + client_height) * scale_y)
    if left < 0 or top < 0 or right > image.width or bottom > image.height:
        raise RuntimeError("scaled BlastEm client rectangle exceeds printed window")
    client = image.crop((left, top, right, bottom))
    if client.size != (client_width, client_height):
        client = client.resize(
            (client_width, client_height), Image.Resampling.NEAREST
        )
    return client


def capture_with_windows_print_window(window_id: int, output: Path) -> Image.Image:
    if shutil.which("powershell.exe") is None or shutil.which("wslpath") is None:
        raise RuntimeError("Windows PrintWindow capture is unavailable")
    display = Display()
    window = display.create_resource_object("window", window_id)
    geometry = window.get_geometry()
    parent_geometry = window.query_tree().parent.get_geometry()
    windows_output = subprocess.check_output(
        ["wslpath", "-w", str(output.resolve())], text=True
    ).strip()
    subprocess.check_call(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            windows_print_capture_script(windows_output),
        ]
    )
    with Image.open(output) as printed:
        return crop_printed_client(
            printed.convert("RGB"),
            geometry.x,
            geometry.y,
            geometry.width,
            geometry.height,
            parent_geometry.width,
            parent_geometry.height,
        )


def capture_with_windows_desktop(window_id: int, output: Path) -> Image.Image:
    if shutil.which("powershell.exe") is None or shutil.which("wslpath") is None:
        raise RuntimeError("Windows desktop capture is unavailable")
    display = Display()
    window = display.create_resource_object("window", window_id)
    geometry = window.get_geometry()
    parent_geometry = window.query_tree().parent.get_geometry()
    windows_output = subprocess.check_output(
        ["wslpath", "-w", str(output.resolve())], text=True
    ).strip()
    script = windows_capture_script(
        windows_output,
        geometry.x,
        geometry.y,
        geometry.width,
        geometry.height,
        parent_geometry.width,
        parent_geometry.height,
    )
    subprocess.check_call(
        ["powershell.exe", "-NoProfile", "-Command", script]
    )
    with Image.open(output) as image:
        client = image.convert("RGB")
        if client.size != (geometry.width, geometry.height):
            client = client.resize(
                (geometry.width, geometry.height), Image.Resampling.NEAREST
            )
        return client


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--xlib-only",
        action="store_true",
        help="skip Windows desktop/xwd capture and read the X11 client directly",
    )
    parser.add_argument(
        "--print-window",
        action="store_true",
        help=(
            "capture an occluded Windows window without focus; partial-update "
            "OpenGL frames are diagnostic only"
        ),
    )
    parser.add_argument(
        "--allow-focus-steal",
        action="store_true",
        help=(
            "explicitly restore and foreground BlastEm before one desktop capture; "
            "never use while the user is working in another application"
        ),
    )
    args = parser.parse_args()
    if args.xlib_only and args.print_window:
        raise ValueError("--xlib-only and --print-window are mutually exclusive")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    window = find_blastem_window()
    if args.allow_focus_steal:
        activate_windows_window()
    if args.xlib_only:
        img = capture_with_xlib(window)
    elif args.print_window:
        img = capture_with_windows_print_window(window, args.output)
    else:
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
