#!/usr/bin/env python3
"""Reach Scenario 10's stock TURN 3 event and capture changed conditions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix


DEFAULT_ROM = Path(
    "/tmp/Langrisser II (v132 Scenario 10 TURN3 Condition Probe).md"
)
DEFAULT_OUTPUT = ROOT / "captures/run/v132_s10_turn3_condition"
DEFAULT_RUNTIME_ROOT = ROOT / "captures/runtime"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Enter Scenario 10 through the stock selector, trigger the "
            "source TURN 3 end reveal, and capture the changed victory condition"
        )
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=":109")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", default="current")
    parser.add_argument("--max-confirmations", type=int, default=240)
    parser.add_argument(
        "--emulator-speed",
        type=int,
        choices=range(8),
        default=4,
        metavar="0..7",
        help=(
            "BlastEm host speed slot used while the long TURN 3 enemy phase "
            "runs; slot 4 is 400%% and slot 0 restores normal speed"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    runtime_name = f"v132-s10-turn3-condition-{args.run_id}"
    runtime_home = args.runtime_root / runtime_name
    recorder = matrix.RuntimeRecorder(args.output, args.display, runtime_home)
    started = time.monotonic()
    try:
        identity = matrix.launch_to_preparation(
            recorder,
            args.rom,
            args.seed_gst,
            10,
            runtime_name,
            args.output,
        )
        recorder.capture("preparation.png")
        gray.enter_battle_command(recorder, args.rom, args.output)
        recorder.capture("battle/turn1_command.png")

        # Close the command panel. The first Start invocation runs the
        # diagnostic wrapper, which only protects groups 0..7 and raises the
        # live turn counter to the stock TURN 3 end prerequisite.
        recorder.send(["b"], delay=0.7)
        recorder.send(["start"], delay=1.0)
        recorder.capture("battle/turn1_start_after_wrapper.png")

        # Choose the stock final row (턴 종료). Ending the raised TURN 3
        # causes the unchanged Scenario 10 TURN 3 end event to reveal the
        # monsters and switch its alternate condition record.
        recorder.send(["down", "down", "down", "down"], delay=0.45)
        recorder.send(["c"], delay=1.5)
        if args.emulator_speed:
            recorder.send([str(args.emulator_speed)], delay=0.5)
        recorder.run_command(
            [
                sys.executable,
                str(ROOT / "tools/run_blastem_sequence.py"),
                "detect-command",
                "--rom",
                str(args.rom),
                "--no-launch",
                "--open-map-command",
                "--confirmation-delay",
                "0.8",
                "--max-confirmations",
                str(args.max_confirmations),
                "--capture-prefix",
                str(args.output / "detect/turn3.png"),
                "--virtual-display",
                recorder.display,
                "--send-event",
            ]
        )
        if args.emulator_speed:
            recorder.send(["0"], delay=0.5)
        recorder.capture("battle/turn3_command.png")

        # Close the commander panel, open Start, and choose 승리조건 (row 3).
        recorder.send(["b"], delay=0.7)
        recorder.send(["start"], delay=1.0)
        recorder.capture("battle/turn3_start_menu.png")
        recorder.send(["down", "down"], delay=0.55)
        recorder.send(["c"], delay=1.2)
        condition = recorder.capture("battle/turn3_conditions.png")
        state = recorder.save_gst("states/turn3_conditions.gst")

        report = {
            "schema_version": 1,
            "status": "captured_unreviewed",
            "scenario": 10,
            "rom": {
                "path": str(args.rom),
                "sha256": sha256(args.rom),
                "md_checksum": args.rom.read_bytes()[0x18E:0x190].hex().upper(),
            },
            "scenario_identity": identity,
            "condition_capture": str(condition.resolve().relative_to(ROOT)),
            "condition_sha256": sha256(condition),
            "condition_gst": str(state.resolve().relative_to(ROOT)),
            "condition_gst_sha256": sha256(state),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "emulator_speed_slot": args.emulator_speed,
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (args.output / "evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        matrix.terminate_blastem_processes(display=args.display)


if __name__ == "__main__":
    raise SystemExit(main())
