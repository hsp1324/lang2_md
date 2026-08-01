#!/usr/bin/env python3
"""Capture current Scenario 21 result and save surfaces from a fresh entry."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario21_clear_probe_rom as probe_builder
from tools import run_blastem_sequence as sequence
from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario14_15_result_surface as result_surface


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s21_result"
GST_WORK_RAM_OFFSET = 0x2478
WORK_RAM_BYTES = 0x10000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def image_report(path: Path) -> dict[str, object]:
    report = result_surface.image_report(path)
    report["surface"] = result_surface.classify_surface(path)
    return report


def runtime_clear_state(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET:GST_WORK_RAM_OFFSET + WORK_RAM_BYTES]
    if len(ram) != WORK_RAM_BYTES:
        raise ValueError(f"GST is missing work RAM: {path}")

    base = probe_builder.RUNTIME_GROUP_BASE & 0xFFFF
    groups = {}
    for group in range(
        probe_builder.FIRST_ENEMY_RUNTIME_GROUP,
        probe_builder.LAST_ENEMY_RUNTIME_GROUP + 1,
    ):
        record = base + group * probe_builder.RUNTIME_GROUP_SIZE
        groups[str(group)] = {
            "class_id": ram[record],
            "name_id": ram[record + 1],
            "defeated_flag": ram[
                record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ],
            "hp": ram[record + probe_builder.RUNTIME_HP_OFFSET],
            "x": ram[record + probe_builder.RUNTIME_X_OFFSET],
            "y": ram[record + probe_builder.RUNTIME_X_OFFSET + 1],
        }
    return {
        "groups": groups,
        "hostiles_defeated": all(
            groups[str(group)]["defeated_flag"] & 0x80
            and groups[str(group)]["hp"] == 0
            and groups[str(group)]["x"] == 0xFF
            for group in probe_builder.RUNTIME_CLEAR_GROUPS
        ),
        "lana_untouched_by_wrapper": (
            groups[str(probe_builder.LANA_RUNTIME_GROUP)]["class_id"] == 0x60
            and groups[str(probe_builder.LANA_RUNTIME_GROUP)]["name_id"] == 0x0C
            and not (
                groups[str(probe_builder.LANA_RUNTIME_GROUP)]["defeated_flag"]
                & 0x80
            )
        ),
    }


def wait_for_result(
    recorder: matrix.RuntimeRecorder,
    *,
    max_frames: int,
    settle_delay: float,
) -> tuple[Path, int, list[dict[str, object]]]:
    observations = []
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(f"aftermath/advance_{frame:03d}.png")
        surface = result_surface.classify_surface(capture)
        dialogue = sequence.battle_dialogue_visible(capture)
        observations.append(
            {
                "frame": frame,
                "surface": surface,
                "dialogue": dialogue,
                "capture": relative(capture),
                "sha256": sha256(capture),
            }
        )
        if surface == "battle_result":
            return capture, frame, observations
        if surface == "save_menu":
            raise RuntimeError("save menu appeared before retaining battle result")
        if sequence.game_over_visible(capture) or sequence.title_screen_visible(capture):
            raise RuntimeError("runtime-clear path entered an ending instead of result")
        recorder.send(["c"], delay=0.45)
    raise RuntimeError("Scenario 21 battle result did not appear")


def wait_for_save_menu(
    recorder: matrix.RuntimeRecorder,
    *,
    max_frames: int,
    settle_delay: float,
) -> tuple[Path, int]:
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(f"save/advance_{frame:03d}.png")
        surface = result_surface.classify_surface(capture)
        if surface == "save_menu":
            return capture, frame
        if sequence.game_over_visible(capture) or sequence.title_screen_visible(capture):
            raise RuntimeError("result path reached an ending before save menu")
        recorder.send(["c"], delay=0.45)
    raise RuntimeError("Scenario 21 save menu did not appear")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / args.run_id
    if output.exists():
        raise FileExistsError(f"result output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s21-result-{args.profile}-{args.run_id}"
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
            probe_builder.SCENARIO_NUMBER,
            runtime_name,
            output,
        )
        preparation = recorder.capture("preparation.png")
        gray.enter_battle_command(recorder, args.rom, output)
        command = recorder.capture("battle/turn1_command.png")

        recorder.send(["b"], delay=0.8)
        recorder.send(["start"], delay=1.0)
        start_menu = recorder.capture("battle/runtime_clear_start_menu.png")
        clear_gst = recorder.save_gst("states/runtime_clear_start_menu.gst")
        clear_state = runtime_clear_state(clear_gst)
        if not clear_state["hostiles_defeated"]:
            raise RuntimeError("Start wrapper did not defeat every hostile group")
        if not clear_state["lana_untouched_by_wrapper"]:
            raise RuntimeError("Start wrapper changed the source Lana group")

        # Close Start, then use the ordinary End Turn command.  Scenario 21's
        # untouched completion handler observes the all-hostile-defeated state
        # and enters its normal aftermath.
        recorder.send(["b"], delay=0.8)
        recorder.send(["start"], delay=1.0)
        recorder.send(["down", "down", "down", "down"], delay=0.55)
        recorder.send(["c"], delay=1.4)

        result_source, result_frame, observations = wait_for_result(
            recorder,
            max_frames=args.max_result_frames,
            settle_delay=args.settle_delay,
        )
        result = output / "aftermath/battle_result.png"
        shutil.copy2(result_source, result)
        result_gst = recorder.save_gst("states/battle_result.gst")

        recorder.send(["c"], delay=0.8)
        save_source, save_frame = wait_for_save_menu(
            recorder,
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
                "path": relative(args.rom),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "scenario_identity": identity,
            "preparation": image_report(preparation),
            "turn1_command": image_report(command),
            "runtime_clear_start_menu": image_report(start_menu),
            "runtime_clear_gst": relative(clear_gst),
            "runtime_clear_state": clear_state,
            "battle_result": image_report(result),
            "battle_result_frame": result_frame,
            "battle_result_gst": relative(result_gst),
            "battle_result_gst_sha256": sha256(result_gst),
            "result_observations": observations,
            "save_menu": image_report(save_menu),
            "save_menu_frame": save_frame,
            "save_menu_gst": relative(save_gst),
            "save_menu_gst_sha256": sha256(save_gst),
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
            failure_gst = relative(recorder.save_gst("states/failure.gst"))
        except Exception:
            pass
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "profile": args.profile,
            "scenario": probe_builder.SCENARIO_NUMBER,
            "run_id": args.run_id,
            "rom": {
                "path": relative(args.rom),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
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
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--max-result-frames", type=int, default=240)
    parser.add_argument("--max-save-frames", type=int, default=100)
    parser.add_argument("--settle-delay", type=float, default=0.8)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    report = run_capture(args)
    print(
        f"{report['status']}: {args.profile} Scenario 21 result at "
        f"frame {report['battle_result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
