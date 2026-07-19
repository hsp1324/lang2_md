#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as production_builder
from tools import build_magic_application_probe_rom as probe_builder
from tools.run_blastem_sequence import (
    GST_WORK_RAM_FILE_OFFSET,
    RUNTIME_ROOT,
    battle_command_menu_visible,
    terminate_blastem_processes,
)


RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"
CAPTURE_WINDOW = ROOT / "tools/capture_blastem_window.py"
MAGIC_COUNT = 22
MAGIC_ROWS_PER_PAGE = 6
HEIN_RUNTIME_RECORD = 1
RUNTIME_RECORD_BASE = 0x603C
RUNTIME_RECORD_SIZE = 0x60
CURRENT_MP_OFFSET = 0x38
MAX_MP_OFFSET = 0x39
DEFAULT_EFFECT_DELAY = 8.0
DEFAULT_FINAL_CONFIRMATIONS = 2


def magic_position(magic_id: int) -> tuple[int, int]:
    if not 0 <= magic_id < MAGIC_COUNT:
        raise ValueError(f"magic ID must be 0..{MAGIC_COUNT - 1}")
    return divmod(magic_id, MAGIC_ROWS_PER_PAGE)


def movement_specs(dx: int, dy: int, wait: float = 0.35) -> list[str]:
    horizontal = "right" if dx > 0 else "left"
    vertical = "down" if dy > 0 else "up"
    return [f"{horizontal}@0.02:{wait}"] * abs(dx) + [
        f"{vertical}@0.02:{wait}"
    ] * abs(dy)


def runtime_mp(gst: bytes, runtime_record_index: int = HEIN_RUNTIME_RECORD) -> tuple[int, int]:
    record = RUNTIME_RECORD_BASE + runtime_record_index * RUNTIME_RECORD_SIZE
    offset = GST_WORK_RAM_FILE_OFFSET + record
    end = offset + RUNTIME_RECORD_SIZE
    if len(gst) < end:
        raise ValueError("GST is too short to contain the runtime record")
    return gst[offset + CURRENT_MP_OFFSET], gst[offset + MAX_MP_OFFSET]


def quicksave_path(runtime_name: str) -> Path:
    states = list((RUNTIME_ROOT / runtime_name).rglob("quicksave.gst"))
    if len(states) != 1:
        raise RuntimeError(
            f"expected one quicksave.gst for {runtime_name}, found {len(states)}"
        )
    return states[0]


def save_and_read_mp(runtime_name: str) -> tuple[Path, int, int]:
    send_keys("save:0.6")
    state = quicksave_path(runtime_name)
    current_mp, max_mp = runtime_mp(state.read_bytes())
    return state, current_mp, max_mp


def portrait_dialogue_visible(path: Path) -> bool:
    image = Image.open(path).convert("RGB")
    if image.size != (320, 240):
        return False
    crop = image.crop((30, 110, 295, 185))
    pixels = list(crop.get_flattened_data())
    blue_pixels = sum(
        1
        for red, green, blue in pixels
        if blue > 60 and blue > red * 1.2 and blue > green * 1.2
    )
    return blue_pixels / len(pixels) > 0.6


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def send_keys(*keys: str) -> None:
    run([sys.executable, str(SEND_KEYS), "--send-event", *keys])


def send_steps(keys: list[str] | tuple[str, ...]) -> None:
    for key in keys:
        send_keys(key)


def capture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(CAPTURE_WINDOW), str(path)])
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture one all-magic diagnostic path through Hein's stock magic "
            "menu, optional target selection, and post-effect GST"
        )
    )
    parser.add_argument("--magic-id", type=int, required=True)
    parser.add_argument(
        "--stock-magic",
        action="store_true",
        help="use Hein's natural one-row magic list; currently valid for magic ID 0",
    )
    parser.add_argument("--target-dx", type=int, default=0)
    parser.add_argument("--target-dy", type=int, default=0)
    parser.add_argument(
        "--target-key",
        action="append",
        choices=("up", "down", "left", "right"),
        default=[],
        help="append an exact target-cursor step after target-dx/target-dy",
    )
    parser.add_argument(
        "--immediate",
        action="store_true",
        help="the selected spell resolves without a separate target confirmation",
    )
    parser.add_argument(
        "--input-rom", type=Path, default=probe_builder.DEFAULT_INPUT_ROM
    )
    parser.add_argument(
        "--source-rom", type=Path, default=probe_builder.DEFAULT_SOURCE_ROM
    )
    parser.add_argument("--output-rom", type=Path)
    parser.add_argument("--runtime-name")
    parser.add_argument("--capture-prefix", type=Path)
    parser.add_argument("--gst-output", type=Path)
    parser.add_argument("--initial-delay", type=float, default=12.0)
    parser.add_argument("--confirmation-delay", type=float, default=0.9)
    parser.add_argument(
        "--effect-delay",
        type=float,
        default=DEFAULT_EFFECT_DELAY,
        help="seconds to keep BlastEm focused after the final confirmation",
    )
    parser.add_argument(
        "--final-confirmations",
        type=int,
        default=DEFAULT_FINAL_CONFIRMATIONS,
        help="diagnostic count of confirmations sent after positioning the target",
    )
    parser.add_argument(
        "--max-event-confirmations",
        type=int,
        default=12,
        help="maximum inserted event-dialogue pages to advance before MP changes",
    )
    parser.add_argument("--max-confirmations", type=int, default=40)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.stock_magic and args.magic_id != 0:
        raise ValueError("stock Hein magic verification supports only magic ID 0")
    page, row = magic_position(args.magic_id)
    output_rom = args.output_rom or (
        ROOT
        / "roms/builds"
        / f"Langrisser II (Korean Magic Apply M{args.magic_id:02d}).md"
    )
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = probe_builder.patch_probe(
        probe,
        source,
        place_target=True,
        enable_all_magic=not args.stock_magic,
    )
    output_rom.parent.mkdir(parents=True, exist_ok=True)
    output_rom.write_bytes(probe)

    magic_name = production_builder.MAGIC_LIST_NAMES[args.magic_id]
    stem = f"{checksum:04x}_magic_{args.magic_id:02d}"
    prefix = args.capture_prefix or ROOT / "captures/run" / stem
    runtime_name = args.runtime_name or f"magic-apply-{stem}"
    gst_output = args.gst_output or ROOT / "captures/analysis" / f"{stem}.gst"

    print(
        f"probe {checksum:04X}: magic {args.magic_id} {magic_name}, "
        f"page {page + 1}, row {row + 1}",
        flush=True,
    )
    try:
        run(
            [
                sys.executable,
                str(RUN_SEQUENCE),
                "battle-command",
                "--rom",
                str(output_rom),
                "--runtime-name",
                runtime_name,
                "--replace-existing",
                "--send-event",
                "--initial-delay",
                str(args.initial_delay),
                "--max-confirmations",
                str(args.max_confirmations),
                "--confirmation-delay",
                str(args.confirmation_delay),
            ]
        )
        # Elwin (11,17) is selected. Hein is at (13,20).
        send_keys("b:0.5")
        # Reach Hein without crossing diagnostic Bald at (13,19). A missed
        # vertical event must land on an empty cell rather than open Bald's menu.
        send_steps(movement_specs(0, 3, wait=0.45))
        send_steps(movement_specs(2, 0, wait=0.45))
        send_keys("c:0.7")
        hein_command = capture(Path(f"{prefix}_hein_command.png"))
        if not battle_command_menu_visible(hein_command):
            raise RuntimeError("Hein command menu was not detected")
        send_steps(["down@0.02:0.35", "down@0.02:0.35"])
        send_keys("c:0.7")
        send_steps(["right@0.02:0.4"] * page)
        send_steps(["down@0.02:0.35"] * row)
        capture(Path(f"{prefix}_selected.png"))
        send_keys("c:1.0")
        capture(Path(f"{prefix}_target_or_result.png"))

        if not args.immediate:
            target_movement = movement_specs(args.target_dx, args.target_dy)
            target_movement.extend(
                f"{key}@0.02:0.35" for key in args.target_key
            )
            if target_movement:
                send_steps(target_movement)
            capture(Path(f"{prefix}_target.png"))
            if args.final_confirmations < 1:
                raise ValueError("final confirmations must be at least one")
            for index in range(args.final_confirmations):
                delay = (
                    args.effect_delay
                    if index + 1 == args.final_confirmations
                    else 0.8
                )
                send_keys(f"c@0.12:{delay}")
                if index + 1 < args.final_confirmations:
                    capture(Path(f"{prefix}_target_confirmed_{index + 1:02d}.png"))

        state, current_mp, max_mp = save_and_read_mp(runtime_name)
        for event_index in range(args.max_event_confirmations):
            if current_mp < max_mp:
                break
            capture(Path(f"{prefix}_event_{event_index + 1:02d}.png"))
            send_keys(f"c@0.12:{args.effect_delay}")
            state, current_mp, max_mp = save_and_read_mp(runtime_name)

        result = capture(Path(f"{prefix}_result.png"))
        for event_index in range(args.max_event_confirmations):
            if not portrait_dialogue_visible(result):
                break
            send_keys(f"c@0.12:{args.effect_delay}")
            result = capture(
                Path(f"{prefix}_post_event_{event_index + 1:02d}.png")
            )
        time.sleep(1.2)
        capture(Path(f"{prefix}_result_stable.png"))
        state, final_current_mp, final_max_mp = save_and_read_mp(runtime_name)
        if (final_current_mp, final_max_mp) != (current_mp, max_mp):
            raise RuntimeError(
                "post-event MP changed unexpectedly: "
                f"{current_mp}/{max_mp} -> {final_current_mp}/{final_max_mp}"
            )
        if current_mp >= max_mp:
            raise RuntimeError(
                f"magic did not consume MP: current {current_mp}, max {max_mp}"
            )
        gst_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(state, gst_output)
        print(f"verified post-effect MP {current_mp}/{max_mp}", flush=True)
        print(gst_output, flush=True)
    finally:
        terminate_blastem_processes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
