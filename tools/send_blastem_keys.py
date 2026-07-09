#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import time

from Xlib import XK, X
from Xlib.display import Display
from Xlib.ext import xtest
from Xlib.protocol import event


KEYSYMS = {
    "enter": XK.XK_Return,
    "start": XK.XK_Return,
    "a": XK.XK_a,
    "b": XK.XK_s,
    "s": XK.XK_s,
    "c": XK.XK_d,
    "d": XK.XK_d,
    "up": XK.XK_Up,
    "down": XK.XK_Down,
    "left": XK.XK_Left,
    "right": XK.XK_Right,
    "save": XK.XK_grave,
}


def find_blastem_window(display: Display):
    root = display.screen().root
    stack = [root]
    while stack:
        window = stack.pop()
        try:
            name = window.get_wm_name() or ""
            cls = window.get_wm_class() or ()
            if "BlastEm" in name or any(part == "blastem" for part in cls):
                return window
            stack.extend(window.query_tree().children)
        except Exception:
            continue
    raise RuntimeError("could not find BlastEm window")


def find_blastem_window_xwininfo(display: Display):
    tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True, errors="ignore")
    for line in tree.splitlines():
        if '("blastem" "blastem")' not in line:
            continue
        window_id = int(line.split()[0], 16)
        return display.create_resource_object("window", window_id)
    raise RuntimeError("could not find BlastEm window via xwininfo")


def wait_for_blastem_window(display: Display, timeout: float):
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() <= deadline:
        try:
            return find_blastem_window(display)
        except Exception as exc:
            last_error = exc
        try:
            return find_blastem_window_xwininfo(display)
        except Exception as exc:
            last_error = exc
        time.sleep(0.1)
    if last_error is not None:
        raise last_error
    raise RuntimeError("could not find BlastEm window")


def activate_window(display: Display, window) -> None:
    root = display.screen().root
    net_active_window = display.intern_atom("_NET_ACTIVE_WINDOW")
    message = event.ClientMessage(
        window=window,
        client_type=net_active_window,
        data=(32, [2, X.CurrentTime, 0, 0, 0]),
    )
    root.send_event(
        message,
        event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask,
    )
    window.configure(stack_mode=X.Above)
    display.sync()


def click_window_center(display: Display, window) -> None:
    root = display.screen().root
    geom = window.get_geometry()
    coords = window.translate_coords(root, geom.width // 2, geom.height // 2)
    xtest.fake_input(display, X.MotionNotify, x=coords.x, y=coords.y)
    display.sync()
    time.sleep(0.05)
    xtest.fake_input(display, X.ButtonPress, 1)
    display.sync()
    time.sleep(0.05)
    xtest.fake_input(display, X.ButtonRelease, 1)
    display.sync()


def press(display: Display, window, key: str, hold: float, send_event: bool) -> None:
    if key not in KEYSYMS:
        raise ValueError(f"unknown key: {key}")
    keycode = display.keysym_to_keycode(KEYSYMS[key])

    if send_event:
        root = display.screen().root
        for event_type in (X.KeyPress, X.KeyRelease):
            key_event = event.KeyPress(
                time=X.CurrentTime,
                root=root,
                window=window,
                same_screen=1,
                child=X.NONE,
                root_x=0,
                root_y=0,
                event_x=10,
                event_y=10,
                state=0,
                detail=keycode,
            )
            key_event.type = event_type
            window.send_event(key_event, propagate=True)
            display.sync()
            if event_type == X.KeyPress:
                time.sleep(hold)
        return

    xtest.fake_input(display, X.KeyPress, keycode)
    display.sync()
    time.sleep(hold)
    xtest.fake_input(display, X.KeyRelease, keycode)
    display.sync()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "keys",
        nargs="+",
        help="key[@hold][:wait], e.g. start:0.35 c b@5:0.1 down",
    )
    parser.add_argument("--hold", type=float, default=0.08)
    parser.add_argument("--ready-delay", type=float, default=0.0)
    parser.add_argument("--wait-window", type=float, default=5.0)
    parser.add_argument(
        "--click-window",
        action="store_true",
        help="click the BlastEm window center before sending keys to force SDL focus",
    )
    parser.add_argument(
        "--send-event",
        action="store_true",
        help="send KeyPress/KeyRelease events directly to the BlastEm window instead of global XTest input",
    )
    args = parser.parse_args()

    display = Display()
    window = wait_for_blastem_window(display, args.wait_window)
    activate_window(display, window)
    if args.click_window:
        click_window_center(display, window)
    time.sleep(args.ready_delay)

    for spec in args.keys:
        hold = args.hold
        if ":" in spec:
            key_hold, wait_text = spec.split(":", 1)
            wait = float(wait_text)
        else:
            key_hold, wait = spec, 0.2
        if "@" in key_hold:
            key, hold_text = key_hold.split("@", 1)
            hold = float(hold_text)
        else:
            key = key_hold
        press(display, window, key, hold, args.send_event)
        time.sleep(wait)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
