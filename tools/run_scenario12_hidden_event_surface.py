#!/usr/bin/env python3
"""Capture one stock Scenario 12 hidden-tile dialogue from a fresh entry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario12_hidden_event_probe_rom as probe_builder
from tools import run_gray_acted_surface_matrix as gray
from tools import run_blastem_sequence as sequence
from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario21_result_surface as shared


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s12_hidden_events"
TARGETS = {
    "muscle": {"start": [4, 6], "target": [4, 6], "leave_return": True},
    "carbunkle": {
        "start": [14, 6],
        "target": [15, 6],
        "leave_return": False,
        # Scenario 12 still has scheduled opening work on turn 1. Let that
        # queue finish before testing the distinct one-time item trigger.
        "defer_turn": True,
    },
}


def wait_for_battle_command(
    recorder: matrix.RuntimeRecorder,
    rom: Path,
    output: Path,
) -> None:
    recorder.run_command(
        [
            sys.executable,
            str(ROOT / "tools/run_blastem_sequence.py"),
            "detect-command",
            "--rom", str(rom),
            "--no-launch",
            "--open-map-command",
            "--confirmation-delay", "0.8",
            "--max-confirmations", "200",
            "--capture-prefix", str(output / "detect/command.png"),
            "--virtual-display", recorder.display,
            "--send-event",
        ]
    )


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.event / args.run_id
    if output.exists():
        raise FileExistsError(f"hidden-event output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s12-hidden-{args.event}-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        output,
        args.display,
        args.runtime_root / runtime_name,
    )
    started = time.monotonic()
    try:
        identity = matrix.launch_to_preparation(
            recorder,
            args.rom,
            args.seed_gst,
            12,
            runtime_name,
            output,
        )
        preparation = recorder.capture("preparation.png")
        gray.enter_battle_command(recorder, args.rom, output)
        command = recorder.capture("battle/command.png")
        before_gst = recorder.save_gst("states/before_move.gst")
        before = gray.runtime_group_zero(before_gst)

        definition = TARGETS[args.event]
        start = definition["start"]
        target = definition["target"]
        if [before["x"], before["y"]] != start:
            raise RuntimeError(
                f"probe did not place Elwin on the target: {before}; "
                f"expected {start}"
            )

        away = None
        away_state = None
        return_command = None
        if definition["leave_return"]:
            # A deployment that begins on the trigger does not activate it.
            # Leave the tile, complete the turn, and re-enter it normally.
            recorder.send(["c"], delay=0.8)
            recorder.send(["down"], delay=0.6)
            recorder.send(["c"], delay=0.8)
            recorder.send(["c"], delay=1.4)
            away = recorder.capture("battle/away.png")
            away_gst = recorder.save_gst("states/away.gst")
            away_state = gray.runtime_group_zero(away_gst)
            if [away_state["x"], away_state["y"]] != [target[0], target[1] + 1]:
                raise RuntimeError(f"Elwin did not leave the target: {away_state}")

            recorder.send(["start"], delay=1.0)
            recorder.send(["down", "down", "down", "down"], delay=0.55)
            recorder.send(["c"], delay=1.4)
            wait_for_battle_command(recorder, args.rom, output)
            return_command = recorder.capture("battle/return_command.png")
            direction = "up"
            destination_name = "battle/return_destination.png"
        else:
            if definition.get("defer_turn"):
                recorder.send(["b"], delay=0.8)
                recorder.send(["start"], delay=1.0)
                recorder.send(["down", "down", "down", "down"], delay=0.55)
                recorder.send(["c"], delay=1.4)
                wait_for_battle_command(recorder, args.rom, output)
                return_command = recorder.capture(
                    "battle/deferred_turn_command.png"
                )
            direction = "right"
            destination_name = "battle/destination.png"

        recorder.send(["c"], delay=0.8)
        recorder.send([direction], delay=0.6)
        recorder.send(["c"], delay=0.8)
        destination = recorder.capture(destination_name)
        recorder.send(["c"], delay=1.4)
        event = recorder.capture("battle/event_attempt_1.png")
        event_attempt = 1
        while not sequence.battle_dialogue_visible(event) and event_attempt < 3:
            event_attempt += 1
            recorder.send(["c"], delay=1.4)
            event = recorder.capture(
                f"battle/event_attempt_{event_attempt}.png"
            )
        dialogue_visible = sequence.battle_dialogue_visible(event)
        if not dialogue_visible:
            raise RuntimeError("hidden-tile dialogue did not become visible")
        event_gst = recorder.save_gst("states/event.gst")
        after = gray.runtime_group_zero(event_gst)

        coordinates_valid = (
            [before["x"], before["y"]] == start
            and (
                not definition["leave_return"]
                or [away_state["x"], away_state["y"]]
                == [target[0], target[1] + 1]
            )
            and [after["x"], after["y"]] == target
        )
        if not coordinates_valid:
            raise RuntimeError(
                f"unexpected hidden-event path: {before} -> {away_state} -> "
                f"{after}; expected start {start}, target {target}"
            )

        report = {
            "schema_version": 1,
            "status": "pass",
            "scenario": 12,
            "event": args.event,
            "run_id": args.run_id,
            "rom": {
                "path": shared.relative(args.rom),
                "sha256": shared.sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "scenario_identity": identity,
            "preparation": shared.image_report(preparation),
            "command": shared.image_report(command),
            "away": shared.image_report(away) if away else None,
            "return_command": (
                shared.image_report(return_command) if return_command else None
            ),
            "return_destination": shared.image_report(destination),
            "event_surface": shared.image_report(event),
            "event_confirmation_attempt": event_attempt,
            "dialogue_visible": dialogue_visible,
            "before_move": before,
            "away_state": away_state,
            "after_move": after,
            "coordinates_valid": coordinates_valid,
            "event_gst": shared.relative(event_gst),
            "event_gst_sha256": shared.sha256(event_gst),
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
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "scenario": 12,
            "event": args.event,
            "run_id": args.run_id,
            "error_type": type(exc).__name__,
            "error": str(exc),
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
    parser.add_argument("--event", choices=tuple(TARGETS), required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    report = run_capture(args)
    print(
        f"{report['status']}: Scenario 12 {args.event} at "
        f"{report['after_move']['x']},{report['after_move']['y']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
