#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re


DEFAULT_VIRTUAL_DISPLAY = os.environ.get("BLASTEM_VIRTUAL_DISPLAY", ":104")
DISPLAY_PATTERN = re.compile(r"^:\d+(?:\.\d+)?$")


def normalize_display(display: str) -> str:
    value = display.strip()
    if not DISPLAY_PATTERN.fullmatch(value):
        raise ValueError(
            f"invalid X11 display {display!r}; expected a value such as :104"
        )
    server, _, screen = value.partition(".")
    if not screen or screen == "0":
        return server
    return value


def add_display_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--virtual-display",
        default=DEFAULT_VIRTUAL_DISPLAY,
        help=(
            "isolated Xvfb display used by default; override with "
            "BLASTEM_VIRTUAL_DISPLAY or this option"
        ),
    )
    parser.add_argument(
        "--desktop-display",
        action="store_true",
        help=(
            "explicitly use the caller's current desktop display; never use "
            "this option while the user is working"
        ),
    )


def configure_display(args: argparse.Namespace) -> bool:
    if args.desktop_display:
        return False
    display = normalize_display(args.virtual_display)
    if display == ":0":
        raise ValueError(
            "refusing virtual-display :0; pass --desktop-display to opt in "
            "to the physical desktop"
        )
    os.environ["DISPLAY"] = display
    os.environ.pop("WAYLAND_DISPLAY", None)
    os.environ["SDL_VIDEODRIVER"] = "x11"
    return True


def sequence_display_args(desktop_display: bool) -> list[str]:
    if desktop_display:
        return ["--desktop-display"]
    return ["--xlib-capture", "--software-renderer"]
