#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import struct
import sys
import time


EV_SYN = 0x00
EV_KEY = 0x01
EV_ABS = 0x03
SYN_REPORT = 0

ABS_X = 0x00
ABS_Y = 0x01
ABS_HAT0X = 0x10
ABS_HAT0Y = 0x11
ABS_CNT = 0x40

BTN_SOUTH = 0x130
BTN_EAST = 0x131
BTN_NORTH = 0x133
BTN_WEST = 0x134
BTN_TL = 0x136
BTN_TR = 0x137
BTN_SELECT = 0x13A
BTN_START = 0x13B

BUS_USB = 0x03

UINPUT_IOCTL_BASE = ord("U")


def _ioc(direction: int, type_: int, nr: int, size: int) -> int:
    return (direction << 30) | (size << 16) | (type_ << 8) | nr


def _io(type_: int, nr: int) -> int:
    return _ioc(0, type_, nr, 0)


def _iow(type_: int, nr: int, size: int) -> int:
    return _ioc(1, type_, nr, size)


UI_DEV_CREATE = _io(UINPUT_IOCTL_BASE, 1)
UI_DEV_DESTROY = _io(UINPUT_IOCTL_BASE, 2)
UI_SET_EVBIT = _iow(UINPUT_IOCTL_BASE, 100, 4)
UI_SET_KEYBIT = _iow(UINPUT_IOCTL_BASE, 101, 4)
UI_SET_ABSBIT = _iow(UINPUT_IOCTL_BASE, 103, 4)

KEYS = {
    "a": BTN_SOUTH,
    "b": BTN_EAST,
    "c": BTN_TR,
    "x": BTN_NORTH,
    "y": BTN_WEST,
    "z": BTN_TL,
    "start": BTN_START,
    "select": BTN_SELECT,
}

DIRECTIONS = {
    "left": (ABS_HAT0X, -1),
    "right": (ABS_HAT0X, 1),
    "up": (ABS_HAT0Y, -1),
    "down": (ABS_HAT0Y, 1),
}


def emit(fd: int, event_type: int, code: int, value: int) -> None:
    fd.write(struct.pack("llHHI", 0, 0, event_type, code, value & 0xFFFFFFFF))


def sync(fd: int) -> None:
    emit(fd, EV_SYN, SYN_REPORT, 0)
    fd.flush()


def ioctl_int(fd: int, request: int, value: int) -> None:
    fcntl.ioctl(fd, request, value)


def create_device() -> object:
    fd = open("/dev/uinput", "wb", buffering=0)
    ioctl_int(fd, UI_SET_EVBIT, EV_KEY)
    ioctl_int(fd, UI_SET_EVBIT, EV_ABS)

    for code in KEYS.values():
        ioctl_int(fd, UI_SET_KEYBIT, code)
    for code in (ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y):
        ioctl_int(fd, UI_SET_ABSBIT, code)

    name = b"Xbox 360 Controller"
    user_dev = bytearray()
    user_dev.extend(struct.pack("80sHHHHI", name, BUS_USB, 0x045E, 0x028E, 0x0110, 0))
    absmax = [0] * ABS_CNT
    absmin = [0] * ABS_CNT
    absfuzz = [0] * ABS_CNT
    absflat = [0] * ABS_CNT
    absmin[ABS_X] = absmin[ABS_Y] = -32768
    absmax[ABS_X] = absmax[ABS_Y] = 32767
    absmin[ABS_HAT0X] = absmin[ABS_HAT0Y] = -1
    absmax[ABS_HAT0X] = absmax[ABS_HAT0Y] = 1
    for arr in (absmax, absmin, absfuzz, absflat):
        user_dev.extend(struct.pack(f"{ABS_CNT}i", *arr))

    fd.write(user_dev)
    fcntl.ioctl(fd, UI_DEV_CREATE)
    time.sleep(0.5)
    for code in (ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y):
        emit(fd, EV_ABS, code, 0)
    sync(fd)
    return fd


def press(fd: object, name: str, hold: float) -> None:
    if name in DIRECTIONS:
        axis, value = DIRECTIONS[name]
        emit(fd, EV_ABS, axis, value)
        sync(fd)
        time.sleep(hold)
        emit(fd, EV_ABS, axis, 0)
        sync(fd)
        return
    if name not in KEYS:
        raise ValueError(f"unknown input: {name}")
    code = KEYS[name]
    emit(fd, EV_KEY, code, 1)
    sync(fd)
    time.sleep(hold)
    emit(fd, EV_KEY, code, 0)
    sync(fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="*", help="input[:wait], e.g. start:1 c left up")
    parser.add_argument("--hold", type=float, default=0.08)
    parser.add_argument("--ready-delay", type=float, default=0.5)
    args = parser.parse_args()

    fd = create_device()
    try:
        print("virtual gamepad ready", flush=True)
        time.sleep(args.ready_delay)
        for spec in args.inputs:
            if ":" in spec:
                name, wait_text = spec.split(":", 1)
                wait = float(wait_text)
            else:
                name, wait = spec, 0.2
            press(fd, name, args.hold)
            time.sleep(wait)
        if not args.inputs:
            while True:
                time.sleep(1)
    finally:
        fcntl.ioctl(fd, UI_DEV_DESTROY)
        fd.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
