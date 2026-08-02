#!/usr/bin/env python3
"""Capture Scenario 14-16 completion and result surfaces without skipping them."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s14_s15_result_retry"
SCENARIO_MOVE_DIRECTIONS = {
    14: "up",
    15: "down",
    16: "up",
}
RESULT_POINTS = {
    (160, 10): (206, 174, 119),
    (160, 30): (0, 0, 119),
    (20, 30): (0, 0, 0),
    (300, 30): (0, 0, 119),
    (160, 200): (0, 0, 119),
    (20, 220): (255, 146, 0),
}
SAVE_POINTS = {
    (160, 10): (206, 174, 119),
    (160, 30): (206, 174, 119),
    (20, 30): (255, 146, 0),
    (300, 30): (255, 146, 0),
    (160, 55): (0, 0, 119),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def classify_surface(path: Path) -> str:
    with Image.open(path) as source:
        image = source.convert("RGB")
        if image.size != (320, 240):
            return "other"
        if all(image.getpixel(point) == color for point, color in RESULT_POINTS.items()):
            return "battle_result"
        if all(image.getpixel(point) == color for point, color in SAVE_POINTS.items()):
            return "save_menu"
    return "other"


def image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as source:
        dimensions = [source.width, source.height]
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "dimensions": dimensions,
        "surface": classify_surface(path),
    }


def perform_completion_move(
    recorder: matrix.RuntimeRecorder,
    direction: str,
) -> None:
    # The probe places Elwin exactly one tile from the stock completion region.
    # C opens Move, direction selects the target, and two C presses commit it.
    recorder.send(["c"], delay=0.8)
    recorder.send([direction], delay=0.7)
    recorder.send(["c"], delay=0.8)
    recorder.send(["c"], delay=1.4)


def wait_for_result(
    recorder: matrix.RuntimeRecorder,
    *,
    max_frames: int,
    settle_delay: float,
    button_delay: float,
) -> tuple[Path, int, list[dict[str, object]]]:
    observations: list[dict[str, object]] = []
    for frame in range(1, max_frames + 1):
        # Inspect the stable surface before sending another button. The former
        # send-then-capture loop could sample a transition and let the next C
        # dismiss the result before it was classified.
        time.sleep(settle_delay)
        capture = recorder.capture(f"battle/clear_path_{frame:03d}.png")
        surface = classify_surface(capture)
        observations.append(
            {
                "frame": frame,
                "surface": surface,
                "capture": relative(capture),
                "sha256": sha256(capture),
            }
        )
        if surface == "battle_result":
            return capture, frame, observations
        if surface == "save_menu":
            raise RuntimeError(
                "save menu reached before a battle-result frame was retained"
            )
        recorder.send(["c"], delay=button_delay)
    raise RuntimeError(
        f"battle result not reached within {max_frames} stable surfaces"
    )


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    direction = SCENARIO_MOVE_DIRECTIONS[args.scenario]
    output = (
        args.output_root
        / args.profile
        / f"s{args.scenario:02d}"
        / args.run_id
    )
    if output.exists():
        raise FileExistsError(f"result output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = (
        f"result-s{args.scenario:02d}-{args.profile}-{args.run_id}"
    )
    if len(runtime_name) > 120 or Path(runtime_name).name != runtime_name:
        raise ValueError("result runtime name is unsafe")
    recorder = matrix.RuntimeRecorder(
        output,
        args.display,
        args.runtime_root / runtime_name,
    )
    started = time.monotonic()
    try:
        scenario_identity = matrix.launch_to_preparation(
            recorder,
            args.rom,
            args.seed_gst,
            args.scenario,
            runtime_name,
            output,
        )
        recorder.capture("preparation.png")
        gray.enter_battle_command(recorder, args.rom, output)
        initial = recorder.capture("battle/initial_command.png")
        perform_completion_move(recorder, direction)
        completion = recorder.capture("battle/completion_event_000.png")
        result_source, result_frame, observations = wait_for_result(
            recorder,
            max_frames=args.max_frames,
            settle_delay=args.settle_delay,
            button_delay=args.button_delay,
        )
        result = output / "battle/battle_result.png"
        shutil.copy2(result_source, result)
        result_gst = recorder.save_gst("states/battle_result.gst")
        report = {
            "schema_version": 1,
            "status": "pass",
            "profile": args.profile,
            "scenario": args.scenario,
            "run_id": args.run_id,
            "rom": {
                "path": relative(args.rom),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "scenario_identity": scenario_identity,
            "completion_move": direction,
            "initial_command": image_report(initial),
            "completion_event": image_report(completion),
            "result_frame": result_frame,
            "battle_result": image_report(result),
            "battle_result_gst": {
                "path": relative(result_gst),
                "sha256": sha256(result_gst),
                "bytes": result_gst.stat().st_size,
            },
            "observations": observations,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
            "acceptance_updated": False,
        }
        (output / "evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    except Exception as exc:
        failure_state = None
        try:
            state = recorder.save_gst("states/failure.gst")
            failure_state = relative(state)
        except Exception:
            pass
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "profile": args.profile,
            "scenario": args.scenario,
            "run_id": args.run_id,
            "rom": {
                "path": relative(args.rom),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failure_gst": failure_state,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
            "acceptance_updated": False,
        }
        (output / "failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        matrix.terminate_blastem_processes(display=args.display)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("normal", "hard"), required=True)
    parser.add_argument(
        "--scenario",
        type=int,
        choices=tuple(SCENARIO_MOVE_DIRECTIONS),
        required=True,
    )
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--max-frames", type=int, default=160)
    parser.add_argument("--settle-delay", type=float, default=0.8)
    parser.add_argument("--button-delay", type=float, default=0.35)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    if args.max_frames < 1:
        parser.error("--max-frames must be positive")
    if args.settle_delay < 0 or args.button_delay < 0:
        parser.error("delays must not be negative")
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    report = run_capture(args)
    print(
        f"{args.profile} Scenario {args.scenario}: "
        f"{report['status']} at frame {report['result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
