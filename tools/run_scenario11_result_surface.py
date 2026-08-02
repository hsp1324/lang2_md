#!/usr/bin/env python3
"""Replay Scenario 11's retained stock final battle on current probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario11_clear_probe_rom as probe_builder
from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario01_09_result_surface as early
from tools import run_scenario18_20_result_surface as continuation
from tools import run_scenario21_result_surface as shared


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s11_result_revalidation"
DEFAULT_SEED_GST = (
    ROOT
    / "captures/runtime/s11-safe-jessica-d091/.local/share/blastem/"
    "Langrisser II (Scenario 11 Safe Jessica Clear Probe)/quicksave.gst"
)
EXPECTED_SEED_SHA256 = (
    "5a8e1f6e777e7119a3fe22efb37e54cf019d6c0da0456a46ddc65d5ac99c1d13"
)
FINAL_REINFORCEMENT_GROUP = 16
SHERRY_RUNTIME_GROUP = 2
SHERRY_POSITION = (19, 20)
FINAL_REINFORCEMENT_POSITION = (20, 20)


def begin_final_battle(recorder: matrix.RuntimeRecorder) -> Path:
    recorder.send(["c"], delay=0.8)
    recorder.send(["down"], delay=0.55)
    recorder.send(["c"], delay=0.8)
    recorder.send(["right"], delay=0.7)
    target = recorder.capture("battle/final_reinforcement_target.png")
    recorder.send(["c"], delay=1.4)
    return target


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / "s11" / args.run_id
    if output.exists():
        raise FileExistsError(f"result output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s11-result-{args.profile}-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        output,
        args.display,
        args.runtime_root / runtime_name,
    )
    started = time.monotonic()
    try:
        seed_sha256 = shared.sha256(args.seed_gst)
        if seed_sha256 != EXPECTED_SEED_SHA256:
            raise ValueError(f"Scenario 11 continuation GST changed: {seed_sha256}")
        loaded, loaded_gst = continuation.launch_continuation(
            recorder,
            rom=args.rom,
            seed_gst=args.seed_gst,
            runtime_name=runtime_name,
            initial_delay=args.initial_delay,
            load_delay=args.load_delay,
        )
        identity = matrix.verify_runtime_scenario_identity(
            loaded_gst,
            args.rom,
            probe_builder.SCENARIO_NUMBER,
        )
        target_before = early.runtime_group(
            loaded_gst,
            probe_builder,
            FINAL_REINFORCEMENT_GROUP,
        )
        if target_before["hp"] <= 0:
            raise RuntimeError(
                "Scenario 11 final reinforcement is already defeated: "
                f"{target_before}"
            )
        sherry_before = early.runtime_group(
            loaded_gst,
            probe_builder,
            SHERRY_RUNTIME_GROUP,
        )
        if (sherry_before["x"], sherry_before["y"]) != SHERRY_POSITION:
            raise RuntimeError(f"Scenario 11 Sherry position changed: {sherry_before}")
        if (target_before["x"], target_before["y"]) != FINAL_REINFORCEMENT_POSITION:
            raise RuntimeError(
                "Scenario 11 final reinforcement position changed: "
                f"{target_before}"
            )

        # The retained D091 state is stopped on Sherry at (19, 20), with the
        # last reinforcement immediately to her right at (20, 20).  Open her
        # command menu, choose Attack, move the target cursor right, and
        # confirm the unmodified final battle.
        target = begin_final_battle(recorder)
        combat = recorder.capture("battle/final_reinforcement_combat.png")
        result_source, result_frame, result_observations = early.wait_for_surface(
            recorder,
            wanted="battle_result",
            phase="aftermath",
            max_frames=args.max_result_frames,
            settle_delay=args.settle_delay,
        )
        result = output / "aftermath/battle_result.png"
        shutil.copy2(result_source, result)
        result_gst = recorder.save_gst("states/battle_result.gst")
        target_after = early.runtime_group(
            result_gst,
            probe_builder,
            FINAL_REINFORCEMENT_GROUP,
        )
        if target_after["hp"] != 0:
            raise RuntimeError(
                "Scenario 11 result retained the final reinforcement: "
                f"{target_after}"
            )

        recorder.send(["c"], delay=0.8)
        save_source, save_frame, save_observations = early.wait_for_surface(
            recorder,
            wanted="save_menu",
            phase="save",
            max_frames=args.max_save_frames,
            settle_delay=args.settle_delay,
        )
        save_menu = output / "save/save_menu.png"
        shutil.copy2(save_source, save_menu)
        save_gst = recorder.save_gst("states/save_menu.gst")

        report = {
            "schema_version": 1,
            "status": "pass",
            "profile": args.profile,
            "scenario": probe_builder.SCENARIO_NUMBER,
            "run_id": args.run_id,
            "rom": {
                "path": shared.relative(args.rom),
                "sha256": shared.sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "continuation_seed": {
                "path": shared.relative(args.seed_gst),
                "sha256": seed_sha256,
                "modified_before_replay": False,
            },
            "scenario_identity": identity,
            "loaded": shared.image_report(loaded),
            "loaded_gst": shared.relative(loaded_gst),
            "target_before": target_before,
            "sherry_before": sherry_before,
            "target": shared.image_report(target),
            "combat": shared.image_report(combat),
            "target_after": target_after,
            "battle_result": shared.image_report(result),
            "battle_result_frame": result_frame,
            "battle_result_gst": shared.relative(result_gst),
            "battle_result_gst_sha256": shared.sha256(result_gst),
            "result_observations": result_observations,
            "save_menu": shared.image_report(save_menu),
            "save_menu_frame": save_frame,
            "save_menu_gst": shared.relative(save_gst),
            "save_menu_gst_sha256": shared.sha256(save_gst),
            "save_observations": save_observations,
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
        failure_gst = None
        try:
            failure_gst = shared.relative(recorder.save_gst("states/failure.gst"))
        except Exception:
            pass
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "profile": args.profile,
            "scenario": probe_builder.SCENARIO_NUMBER,
            "run_id": args.run_id,
            "rom": shared.relative(args.rom),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failure_gst": failure_gst,
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
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--initial-delay", type=float, default=2.0)
    parser.add_argument("--load-delay", type=float, default=0.8)
    parser.add_argument("--max-result-frames", type=int, default=180)
    parser.add_argument("--max-save-frames", type=int, default=80)
    parser.add_argument("--settle-delay", type=float, default=0.16)
    args = parser.parse_args()
    for name in ("rom", "seed_gst", "output_root", "runtime_root"):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if args.max_result_frames < 1 or args.max_save_frames < 1:
        parser.error("frame limits must be positive")
    if min(args.initial_delay, args.load_delay, args.settle_delay) < 0:
        parser.error("delays must be nonnegative")
    report = run_capture(args)
    print(
        f"{report['status']}: {args.profile} Scenario 11 result at "
        f"frame {report['battle_result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
