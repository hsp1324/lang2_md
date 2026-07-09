#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    "c": XK.XK_d,
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


def wait_for_blastem_window(display: Display, timeout: float):
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() <= deadline:
        try:
            return find_blastem_window(display)
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
    window.set_input_focus(X.RevertToParent, X.CurrentTime)
    display.sync()


def press(display: Display, key: str, hold: float) -> None:
    if key not in KEYSYMS:
        raise ValueError(f"unknown key: {key}")
    keycode = display.keysym_to_keycode(KEYSYMS[key])
    xtest.fake_input(display, X.KeyPress, keycode)
    display.sync()
    time.sleep(hold)
    xtest.fake_input(display, X.KeyRelease, keycode)
    display.sync()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("keys", nargs="+", help="key[:wait], e.g. start:1 c left up")
    parser.add_argument("--hold", type=float, default=0.08)
    parser.add_argument("--ready-delay", type=float, default=0.0)
    parser.add_argument("--wait-window", type=float, default=5.0)
    args = parser.parse_args()

    display = Display()
    window = wait_for_blastem_window(display, args.wait_window)
    activate_window(display, window)
    time.sleep(args.ready_delay)

    for spec in args.keys:
        if ":" in spec:
            key, wait_text = spec.split(":", 1)
            wait = float(wait_text)
        else:
            key, wait = spec, 0.2
        press(display, key, args.hold)
        time.sleep(wait)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
