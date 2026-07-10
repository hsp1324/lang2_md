#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"
BLASTEM = ROOT / "tools/blastem/blastem"
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"


SEQUENCES = {
    # Opening/title into the name entry screen. Useful as a glyph/code probe.
    "name-entry": ["start:2.0", "start:1.0", "c:0.8"],
    # Opening/title/name/route into the scenario description screen.
    "scenario": ["start:2.0", "start:1.0", "c:0.8", "c:0.8", "c:0.8"],
    # Scenario screen into the commander preparation screen.
    "prep": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:0.8",
    ],
    # Scenario 1 shop, first item selected/purchased-confirm screen.
    "shop": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "c:0.8",
        "c:0.8",
    ],
    # Scenario 1 shop, purchase the first item after selecting it.
    "shop-buy": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "c:0.8",
        "c:0.8",
        "c:0.8",
    ],
    # Scenario 1 commander arrangement screen.
    "arrange": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "down:0.8",
        "c:0.8",
    ],
    # Scenario 1 deploy from commander arrangement, then advance dialogue a few pages.
    "deploy-dialogue": [
        "start:2.0",
        "start:1.0",
        "c:0.8",
        "c:0.8",
        "c:1.4",
        "s@3.0:0.8",
        "c:1.2",
        "down:0.8",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "down:0.8",
        "down:0.8",
        "down:0.8",
        "down:0.8",
        "c:1.2",
        "c:1.2",
        "c:1.2",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sequence", choices=sorted(SEQUENCES))
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--hold", type=float, default=0.08)
    parser.add_argument("--window-width", type=int, default=320)
    parser.add_argument("--window-height", type=int, default=240)
    parser.add_argument("--click-window", action="store_true")
    parser.add_argument("--send-event", action="store_true", help="send direct window events instead of global XTest input")
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.no_launch:
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = str(ROOT / "tools/blastem/lib")
        command = [str(BLASTEM), str(args.rom), str(args.window_width), str(args.window_height)]
        if args.dry_run:
            print("launch:", " ".join(command))
        else:
            subprocess.Popen(
                command,
                cwd=ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            time.sleep(args.initial_delay)

    key_command = [
        sys.executable,
        str(SEND_KEYS),
        "--hold",
        str(args.hold),
        *SEQUENCES[args.sequence],
    ]
    if args.send_event:
        key_command.insert(2, "--send-event")
    if args.click_window:
        key_command.insert(2, "--click-window")
    if args.dry_run:
        print("keys:", " ".join(key_command))
        return 0
    return subprocess.call(key_command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
