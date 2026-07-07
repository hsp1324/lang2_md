#!/usr/bin/env python3
import ctypes
import os
import re
import subprocess
import sys
import time


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: romhack_capture.py KEY[:WAIT] ...", file=sys.stderr)
        return 2

    x11 = ctypes.CDLL("libX11.so.6")
    xtst = ctypes.CDLL("libXtst.so.6")
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
    x11.XStringToKeysym.restype = ctypes.c_ulong
    x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XKeysymToKeycode.restype = ctypes.c_uint
    x11.XFlush.argtypes = [ctypes.c_void_p]
    x11.XFlush.restype = ctypes.c_int
    x11.XSetInputFocus.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    x11.XSetInputFocus.restype = ctypes.c_int
    x11.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XRaiseWindow.restype = ctypes.c_int
    xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeMotionEvent.restype = ctypes.c_int
    xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeButtonEvent.restype = ctypes.c_int
    xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeKeyEvent.restype = ctypes.c_int

    display = x11.XOpenDisplay(None)
    if not display:
        print("could not open X display", file=sys.stderr)
        return 1

    tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True, errors="ignore")
    window = None
    for line in tree.splitlines():
        if "BlastEm" in line or "Langrisser" in line:
            window = int(line.split()[0], 16)
            print(f"using window {window:#x}: {line.strip()}")
            break
    if window is None:
        print("could not find BlastEm window", file=sys.stderr)
        return 1

    x11.XRaiseWindow(display, window)
    x11.XSetInputFocus(display, window, 1, 0)
    x11.XFlush(display)
    time.sleep(0.3)
    try:
        info = subprocess.check_output(["xwininfo", "-id", f"{window:#x}"], text=True, errors="ignore")
        def field(name: str) -> int:
            match = re.search(rf"{re.escape(name)}:\s+(-?\d+)", info)
            if not match:
                raise ValueError(name)
            return int(match.group(1))

        cx = field("Absolute upper-left X") + field("Width") // 2
        cy = field("Absolute upper-left Y") + field("Height") // 2
        xtst.XTestFakeMotionEvent(display, -1, cx, cy, 0)
        x11.XFlush(display)
        time.sleep(0.05)
        xtst.XTestFakeButtonEvent(display, 1, 1, 0)
        x11.XFlush(display)
        time.sleep(0.03)
        xtst.XTestFakeButtonEvent(display, 1, 0, 0)
        x11.XFlush(display)
        time.sleep(0.2)
    except Exception as exc:
        print(f"focus click skipped: {exc}", file=sys.stderr)

    for spec in sys.argv[1:]:
        if ":" in spec:
            key, wait_text = spec.split(":", 1)
            wait = float(wait_text)
        else:
            key, wait = spec, 0.2
        keysym = x11.XStringToKeysym(key.encode("ascii"))
        keycode = x11.XKeysymToKeycode(display, keysym)
        if keycode == 0:
            print(f"unknown key: {key}", file=sys.stderr)
            return 1
        print(f"press {key} wait {wait}")
        xtst.XTestFakeKeyEvent(display, keycode, 1, 0)
        x11.XFlush(display)
        time.sleep(0.08)
        xtst.XTestFakeKeyEvent(display, keycode, 0, 0)
        x11.XFlush(display)
        time.sleep(wait)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
