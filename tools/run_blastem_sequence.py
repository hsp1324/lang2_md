#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"
BLASTEM = ROOT / "tools/blastem/blastem"
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"
CAPTURE_WINDOW = ROOT / "tools/capture_blastem_window.py"
RUNTIME_ROOT = ROOT / "captures/runtime"
LOG_ROOT = ROOT / "captures/run"


SEQUENCES = {
    # Opening/title into the game's load-slot screen. Copy or retain a runtime
    # SRAM with at least one valid scenario save before using scenario select.
    "load-screen": ["start:2.0", "start:1.0", "down:0.8", "c:1.5"],
    # Opening/title into the name entry screen. Useful as a glyph/code probe.
    "name-entry": ["start:2.0", "start:1.0", "c:0.8"],
    # Opening/title/name/route into the scenario description screen.
    "scenario": ["start:2.0", "start:1.0", "c:0.8", "c:0.8", "c:0.8"],
    # Filled from --scenario-number after argument parsing. This uses a valid
    # manual save in the load-screen runtime SRAM to enter the built-in
    # Left, Right, Start, C scenario selector.
    "scenario-select": [],
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
    "shop-buy-list": [
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
    ],
    # Scenario 1 shop, one step past the buy list. This enters the follow-up
    # item/possession path and is not the first shop title check.
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
    # Scenario 1 full shop regression path:
    # Buy the first dagger, confirm the completion popup with C, leave the item
    # list with B, re-enter the shop, enter sell, and select the bought dagger.
    "shop-buy-sell": [
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
        "c:3.0",
        "c:0.8",
        "c:0.8",
        "b:3.0",
        "down:0.8",
        "down:0.8",
        "c:0.8",
        "down:0.8",
        "c:3.0",
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

# Same regression path, stopped on the sell list before confirming the dagger.
SEQUENCES["shop-sell-list"] = list(SEQUENCES["shop-buy-sell"][:-1])

# This sequence uses the deploy/dialogue inputs, then advances one confirmation
# at a time until the full command menu is detected. Fixed confirmation counts
# are timing-sensitive and can accidentally choose Move on faster hosts.
SEQUENCES["battle-command"] = list(SEQUENCES["deploy-dialogue"])
SEQUENCES["first-turn-dialogue"] = list(SEQUENCES["deploy-dialogue"])


def make_key_command(args: argparse.Namespace, keys: list[str]) -> list[str]:
    command = [
        sys.executable,
        str(SEND_KEYS),
        "--hold",
        str(args.hold),
        *keys,
    ]
    if args.send_event:
        command.insert(2, "--send-event")
    if args.click_window:
        command.insert(2, "--click-window")
    return command


def battle_command_menu_visible(path: Path) -> bool:
    frame = Image.open(path).convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    image = frame.crop(
        (
            round(15 * scale_x),
            round(25 * scale_y),
            round(95 * scale_x),
            round(110 * scale_y),
        )
    )
    pixels = image.load()
    blue_pixels = 0
    dark_panel_pixels = 0
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            if blue > 70 and blue > red * 1.3 and blue > green * 1.2:
                blue_pixels += 1
            if 50 <= blue <= 180 and red < 45 and green < 65 and blue > red * 2 and blue > green * 1.8:
                dark_panel_pixels += 1
    # Portrait cut-ins also have a broad blue background and used to trigger
    # this detector early. A real command menu is only available with the blue
    # battle status bar visible across the bottom of the frame.
    status = frame.crop((0, round(195 * scale_y), frame.width, round(235 * scale_y)))
    status_blue_pixels = sum(
        1
        for red, green, blue in status.get_flattened_data()
        if blue > 70 and blue > red * 1.3 and blue > green * 1.2
    )
    return (
        blue_pixels > 3200 * scale_x * scale_y
        # Water-heavy maps can fill this entire crop with blue pixels. A real
        # command panel also contains its gold frame, labels, and portrait/map
        # content, so reject nearly solid-blue backgrounds.
        and blue_pixels < image.width * image.height * 0.85
        and dark_panel_pixels > 1000 * scale_x * scale_y
        # The ornate status-bar frame occupies a little over half of this
        # crop on some maps; 45% still distinguishes it from dialogue views.
        and status_blue_pixels > status.width * status.height * 0.45
    )


def advance_to_battle_command(args: argparse.Namespace) -> int:
    probe = LOG_ROOT / "battle_command_probe.png"
    for step in range(1, 16):
        status = subprocess.call(make_key_command(args, ["c:0.9"]), cwd=ROOT)
        if status:
            return status
        subprocess.check_call(
            [sys.executable, str(CAPTURE_WINDOW), str(probe)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
        )
        if battle_command_menu_visible(probe):
            time.sleep(2.0)
            subprocess.check_call(
                [sys.executable, str(CAPTURE_WINDOW), str(probe)],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
            )
            if battle_command_menu_visible(probe):
                print(f"battle command menu detected after {step} confirmations")
                return 0
    raise RuntimeError("battle command menu was not detected after 15 confirmations")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sequence", choices=sorted(SEQUENCES))
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--hold", type=float, default=0.08)
    parser.add_argument("--window-width", type=int, default=320)
    parser.add_argument("--window-height", type=int, default=240)
    parser.add_argument("--scenario-number", type=int, default=14)
    parser.add_argument("--click-window", action="store_true")
    parser.add_argument("--send-event", action="store_true", help="send direct window events instead of global XTest input")
    parser.add_argument(
        "--reuse-runtime-state",
        action="store_true",
        help="reuse the isolated test SRAM/save-state directory for this sequence",
    )
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.scenario_number <= 31:
        raise ValueError("--scenario-number must be 1..31")
    if args.sequence == "scenario-select":
        SEQUENCES[args.sequence] = [
            *SEQUENCES["load-screen"],
            "down:0.8",
            "left:0.8",
            "right:0.8",
            "start:0.8",
            "c:1.2",
            *(["down:0.35"] * (args.scenario_number - 1)),
            "c:4.0",
        ]

    if not args.no_launch:
        runtime_name = "load-screen" if args.sequence == "scenario-select" else args.sequence
        runtime_home = RUNTIME_ROOT / runtime_name
        if not args.reuse_runtime_state:
            shutil.rmtree(runtime_home, ignore_errors=True)
        runtime_home.mkdir(parents=True, exist_ok=True)
        config_dir = runtime_home / ".config/blastem"
        config_dir.mkdir(parents=True, exist_ok=True)
        default_config = (BLASTEM.parent / "default.cfg").read_text(encoding="utf-8")
        test_config = default_config.replace("state_format native", "state_format gst")
        (config_dir / "blastem.cfg").write_text(test_config, encoding="utf-8")
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        log_path = LOG_ROOT / f"blastem_{args.sequence}.log"

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = str(ROOT / "tools/blastem/lib")
        env["HOME"] = str(runtime_home)
        if "microsoft" in platform.release().lower():
            env.setdefault("SDL_AUDIODRIVER", "dummy")
        command = [
            str(BLASTEM),
            str(args.rom.resolve()),
            str(args.window_width),
            str(args.window_height),
        ]
        if args.dry_run:
            print("launch:", " ".join(command))
            print("runtime home:", runtime_home)
            print("log:", log_path)
        else:
            with log_path.open("w", encoding="utf-8") as log_file:
                process = subprocess.Popen(
                    command,
                    cwd=BLASTEM.parent,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            time.sleep(args.initial_delay)
            if process.poll() is not None:
                log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                raise RuntimeError(
                    f"BlastEm exited with status {process.returncode} before input; "
                    f"log: {log_path}\n{log_tail}"
                )

    key_command = make_key_command(args, SEQUENCES[args.sequence])
    if args.dry_run:
        print("keys:", " ".join(key_command))
        if args.sequence in {"battle-command", "first-turn-dialogue"}:
            print("then: confirm and capture until the full command menu is detected")
        if args.sequence == "first-turn-dialogue":
            print("then: close the unit menu and choose Start > 턴 종료")
        return 0
    status = subprocess.call(key_command, cwd=ROOT)
    if status or args.sequence not in {"battle-command", "first-turn-dialogue"}:
        return status
    status = advance_to_battle_command(args)
    if status or args.sequence == "battle-command":
        return status
    return subprocess.call(
        make_key_command(
            args,
            [
                "b:0.8",
                "start:1.0",
                "down:0.8",
                "down:0.8",
                "down:0.8",
                "down:1.0",
                "c:4.0",
            ],
        ),
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
