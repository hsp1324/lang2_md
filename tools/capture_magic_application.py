#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
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
DEFAULT_DIALOGUE_DELAY = 0.9
DEFAULT_FINAL_CONFIRMATIONS = 2
POST_EFFECT_SETTLE_DELAY = 1.2
POST_EFFECT_CLEAR_CHECKS = 2
DIALOGUE_SCAN_X_RANGE = range(15, 305)
DIALOGUE_SCAN_Y_RANGE = range(45, 195)
DIALOGUE_MIN_WIDE_BLUE_PIXELS = 200
DIALOGUE_MIN_WIDE_BLUE_ROWS = 20
MAGIC_CURSOR_X_RANGE = range(34, 53)
MAGIC_CURSOR_Y_STARTS = (25, 43, 61, 79, 97, 115)
MAGIC_CURSOR_ROW_HEIGHT = 16
MAGIC_CURSOR_MIN_SCORE = 8
MAGIC_CURSOR_MAX_RUNNER_UP_RATIO = 0.7
DIRECTION_HOLD = 0.08
UNACCEPTED_TARGET_MAX_CHANGE_RATIO = 0.15
DEFAULT_VIRTUAL_DISPLAY = os.environ.get("BLASTEM_VIRTUAL_DISPLAY", ":104")
XLIB_ONLY_CAPTURE = False


def magic_position(magic_id: int) -> tuple[int, int]:
    if not 0 <= magic_id < MAGIC_COUNT:
        raise ValueError(f"magic ID must be 0..{MAGIC_COUNT - 1}")
    return divmod(magic_id, MAGIC_ROWS_PER_PAGE)


def movement_specs(dx: int, dy: int, wait: float = 0.35) -> list[str]:
    horizontal = "right" if dx > 0 else "left"
    vertical = "down" if dy > 0 else "up"
    return [f"{horizontal}@{DIRECTION_HOLD}:{wait}"] * abs(dx) + [
        f"{vertical}@{DIRECTION_HOLD}:{wait}"
    ] * abs(dy)


def runtime_mp(gst: bytes, runtime_record_index: int = HEIN_RUNTIME_RECORD) -> tuple[int, int]:
    record = RUNTIME_RECORD_BASE + runtime_record_index * RUNTIME_RECORD_SIZE
    offset = GST_WORK_RAM_FILE_OFFSET + record
    end = offset + RUNTIME_RECORD_SIZE
    if len(gst) < end:
        raise ValueError("GST is too short to contain the runtime record")
    return gst[offset + CURRENT_MP_OFFSET], gst[offset + MAX_MP_OFFSET]


def list_cursor_scores(path: Path) -> list[int]:
    image = Image.open(path).convert("RGB")
    scores = []
    for start_y in MAGIC_CURSOR_Y_STARTS:
        score = 0
        for y in range(start_y, start_y + MAGIC_CURSOR_ROW_HEIGHT):
            for x in MAGIC_CURSOR_X_RANGE:
                red, green, blue = image.getpixel((x, y))
                if max(red, green, blue) - min(red, green, blue) < 40:
                    if red + green + blue > 300:
                        score += 1
        scores.append(score)
    return scores


def selected_list_row(path: Path) -> int:
    scores = list_cursor_scores(path)
    selected = max(range(len(scores)), key=scores.__getitem__)
    if scores[selected] < MAGIC_CURSOR_MIN_SCORE:
        raise RuntimeError(f"magic list cursor not detected: scores={scores}")
    runner_up = sorted(scores)[-2]
    if runner_up >= scores[selected] * MAGIC_CURSOR_MAX_RUNNER_UP_RATIO:
        raise RuntimeError(f"magic list cursor is ambiguous: scores={scores}")
    return selected


def image_change_ratio(before_path: Path, after_path: Path) -> float:
    before = Image.open(before_path).convert("RGB")
    after = Image.open(after_path).convert("RGB")
    if before.size != after.size:
        return 1.0
    before_bytes = before.tobytes()
    after_bytes = after.tobytes()
    changed = sum(
        before_bytes[index : index + 3] != after_bytes[index : index + 3]
        for index in range(0, len(before_bytes), 3)
    )
    return changed / (before.width * before.height)


def require_target_confirmation_accepted(
    target_path: Path,
    after_path: Path,
    current_mp: int,
    max_mp: int,
) -> None:
    if current_mp < max_mp:
        return
    change_ratio = image_change_ratio(target_path, after_path)
    if change_ratio <= UNACCEPTED_TARGET_MAX_CHANGE_RATIO:
        raise RuntimeError(
            "target confirmation was not accepted: "
            f"MP {current_mp}/{max_mp}, frame change {change_ratio:.1%}"
        )


def correct_selected_row(prefix: Path, expected_row: int) -> Path:
    selected_path = Path(f"{prefix}_selected.png")
    for attempt in range(8):
        attempt_path = Path(f"{prefix}_selected_attempt_{attempt + 1:02d}.png")
        capture(attempt_path)
        actual_row = selected_list_row(attempt_path)
        if actual_row == expected_row:
            shutil.copy2(attempt_path, selected_path)
            return selected_path
        direction = "down" if actual_row < expected_row else "up"
        send_keys(f"{direction}@{DIRECTION_HOLD}:0.55")
        print(
            f"correcting magic cursor row {actual_row + 1} "
            f"to {expected_row + 1} (attempt {attempt + 1})",
            flush=True,
        )
    raise RuntimeError(
        f"magic cursor row mismatch after 8 attempts: "
        f"expected {expected_row + 1}"
    )


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
    wide_blue_rows = 0
    for y in DIALOGUE_SCAN_Y_RANGE:
        blue_pixels = 0
        for x in DIALOGUE_SCAN_X_RANGE:
            red, green, blue = image.getpixel((x, y))
            if blue > 60 and blue > red * 1.2 and blue > green * 1.2:
                blue_pixels += 1
        if blue_pixels > DIALOGUE_MIN_WIDE_BLUE_PIXELS:
            wide_blue_rows += 1
    return wide_blue_rows >= DIALOGUE_MIN_WIDE_BLUE_ROWS


def require_effect_settled(path: Path, confirmation_limit: int) -> None:
    if portrait_dialogue_visible(path):
        raise RuntimeError(
            "post-effect dialogue remained after "
            f"{confirmation_limit} confirmations"
        )


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def send_keys(*keys: str) -> None:
    run([sys.executable, str(SEND_KEYS), "--send-event", *keys])


def send_steps(keys: list[str] | tuple[str, ...]) -> None:
    for key in keys:
        send_keys(key)


def capture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(CAPTURE_WINDOW), str(path)]
    if XLIB_ONLY_CAPTURE:
        command.append("--xlib-only")
    run(command)
    return path


def sequence_display_args(desktop_display: bool) -> list[str]:
    if desktop_display:
        return []
    return ["--xlib-capture", "--software-renderer"]


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
        "--dialogue-delay",
        type=float,
        default=DEFAULT_DIALOGUE_DELAY,
        help="seconds between post-effect portrait-dialogue confirmations",
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
            "explicit opt-in to the caller's current desktop display; never "
            "use while the user is working"
        ),
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help=(
            "resume an existing isolated BlastEm instance already stopped at "
            "Elwin's battle command menu"
        ),
    )
    return parser.parse_args()


def main() -> int:
    global XLIB_ONLY_CAPTURE
    args = parse_args()
    if not args.desktop_display:
        os.environ["DISPLAY"] = args.virtual_display
        XLIB_ONLY_CAPTURE = True
        print(
            f"isolated virtual display {args.virtual_display}; "
            "software renderer and Xlib capture enabled",
            flush=True,
        )
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
        if not args.no_launch:
            sequence_command = [
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
            sequence_command.extend(sequence_display_args(args.desktop_display))
            run(sequence_command)
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
        send_steps([f"down@{DIRECTION_HOLD}:0.35"] * 2)
        send_keys("c:0.7")
        send_steps([f"right@{DIRECTION_HOLD}:0.4"] * page)
        send_steps([f"down@{DIRECTION_HOLD}:0.35"] * row)
        correct_selected_row(prefix, row)
        send_keys("c:1.0")
        target_path = capture(Path(f"{prefix}_target_or_result.png"))

        if not args.immediate:
            target_movement = movement_specs(args.target_dx, args.target_dy)
            target_movement.extend(
                f"{key}@{DIRECTION_HOLD}:0.35" for key in args.target_key
            )
            if target_movement:
                send_steps(target_movement)
            target_path = capture(Path(f"{prefix}_target.png"))
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
        if current_mp >= max_mp:
            pending_path = capture(Path(f"{prefix}_pending.png"))
            require_target_confirmation_accepted(
                target_path,
                pending_path,
                current_mp,
                max_mp,
            )
        for event_index in range(args.max_event_confirmations):
            if current_mp < max_mp:
                break
            capture(Path(f"{prefix}_event_{event_index + 1:02d}.png"))
            send_keys(f"c@0.12:{args.effect_delay}")
            state, current_mp, max_mp = save_and_read_mp(runtime_name)

        result = capture(Path(f"{prefix}_result.png"))
        dialogue_confirmations = 0
        clear_checks = 0
        max_observations = args.max_event_confirmations * 4 + 4
        for event_index in range(max_observations):
            if portrait_dialogue_visible(result):
                if dialogue_confirmations >= args.max_event_confirmations:
                    break
                send_keys(f"c@0.12:{args.dialogue_delay}")
                dialogue_confirmations += 1
                clear_checks = 0
            else:
                clear_checks += 1
                if clear_checks >= POST_EFFECT_CLEAR_CHECKS:
                    break
                time.sleep(POST_EFFECT_SETTLE_DELAY)
            result = capture(
                Path(f"{prefix}_post_event_{event_index + 1:02d}.png")
            )
        require_effect_settled(result, args.max_event_confirmations)
        stable = capture(Path(f"{prefix}_result_stable.png"))
        require_effect_settled(stable, args.max_event_confirmations)
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
