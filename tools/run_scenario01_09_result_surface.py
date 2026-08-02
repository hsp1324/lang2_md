#!/usr/bin/env python3
"""Capture current Scenario 1-9 result/save surfaces from fresh entries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import time
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario1_clear_probe_rom as scenario1
from tools import build_scenario2_escape_probe_rom as scenario2
from tools import build_scenario3_clear_probe_rom as scenario3
from tools import build_scenario4_clear_probe_rom as scenario4
from tools import build_scenario5_escape_probe_rom as scenario5
from tools import build_scenario6_clear_probe_rom as scenario6
from tools import build_scenario7_clear_probe_rom as scenario7
from tools import build_scenario8_clear_probe_rom as scenario8
from tools import build_scenario9_clear_probe_rom as scenario9
from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario21_result_surface as shared


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s01_09_result_revalidation"
GST_WORK_RAM_OFFSET = 0x2478
WORK_RAM_BYTES = 0x10000

SCENARIOS: dict[int, dict[str, object]] = {
    1: {
        "module": scenario1,
        "completion": "runtime_end_turn",
        "clear_groups": (scenario1.RUNTIME_BALD_GROUP_INDEX,),
    },
    2: {
        "module": scenario2,
        "completion": "runtime_end_turn",
        "clear_groups": scenario2.ANNIHILATION_RUNTIME_GROUPS,
    },
    3: {
        "module": scenario3,
        "completion": "runtime_end_turn",
        "clear_groups": scenario3.ANNIHILATION_RUNTIME_GROUPS,
    },
    4: {
        "module": scenario4,
        "completion": "runtime_end_turn",
        "clear_groups": (scenario4.MORGAN_RUNTIME_GROUP,),
    },
    5: {"module": scenario5, "completion": "move_up"},
    6: {
        "module": scenario6,
        "completion": "runtime_end_turn",
        "clear_groups": scenario6.ENEMY_ANNIHILATION_RUNTIME_GROUPS,
    },
    7: {
        "module": scenario7,
        "completion": "runtime_end_turn",
        "clear_groups": (scenario7.GINAM_RUNTIME_GROUP,),
    },
    8: {
        "module": scenario8,
        "completion": "runtime_end_turn",
        "clear_groups": (scenario8.BOSS_RUNTIME_GROUP,),
    },
    9: {
        "module": scenario9,
        "completion": "runtime_end_turn",
        "clear_groups": (scenario9.LAIRD_RUNTIME_GROUP,),
    },
}


def runtime_group(path: Path, module: ModuleType, group: int) -> dict[str, int]:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET : GST_WORK_RAM_OFFSET + WORK_RAM_BYTES]
    if len(ram) != WORK_RAM_BYTES:
        raise ValueError(f"GST is missing work RAM: {path}")
    record = (int(module.RUNTIME_GROUP_BASE) & 0xFFFF) + (
        group * int(module.RUNTIME_GROUP_SIZE)
    )
    return {
        "group": group,
        "class_id": ram[record],
        "name_id": ram[record + 1],
        "defeated_flag": ram[record + 2],
        "hp": ram[record + 3],
        "x": ram[record + 6],
        "y": ram[record + 7],
    }


def runtime_clear_state(
    path: Path,
    module: ModuleType,
    clear_groups: tuple[int, ...],
) -> dict[str, object]:
    groups = {
        str(group): runtime_group(path, module, group)
        for group in clear_groups
    }
    return {
        "groups": groups,
        "clear_groups_defeated": all(
            row["defeated_flag"] & 0x80
            and row["hp"] == 0
            and row["x"] == 0xFF
            for row in groups.values()
        ),
    }


def wait_for_surface(
    recorder: matrix.RuntimeRecorder,
    *,
    wanted: str,
    phase: str,
    max_frames: int,
    settle_delay: float,
) -> tuple[Path, int, list[dict[str, object]]]:
    observations = []
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(f"{phase}/advance_{frame:03d}.png")
        surface = shared.result_surface.classify_surface(capture)
        observations.append(
            {
                "frame": frame,
                "surface": surface,
                "capture": shared.relative(capture),
                "sha256": shared.sha256(capture),
            }
        )
        if surface == wanted:
            return capture, frame, observations
        if wanted == "battle_result" and surface == "save_menu":
            raise RuntimeError("save menu appeared before retaining battle result")
        recorder.send(["c"], delay=0.45)
    raise RuntimeError(f"{wanted} did not appear within {max_frames} frames")


def trigger_completion(
    recorder: matrix.RuntimeRecorder,
    definition: dict[str, object],
) -> dict[str, object]:
    mode = str(definition["completion"])
    if mode == "runtime_end_turn":
        module = definition["module"]
        if not isinstance(module, ModuleType):
            raise TypeError("scenario probe module is invalid")
        clear_groups = tuple(int(group) for group in definition["clear_groups"])
        recorder.send(["b"], delay=0.8)
        recorder.send(["start"], delay=1.0)
        start_menu = recorder.capture("battle/runtime_clear_start_menu.png")
        clear_gst = recorder.save_gst("states/runtime_clear_start_menu.gst")
        state = runtime_clear_state(clear_gst, module, clear_groups)
        if not state["clear_groups_defeated"]:
            raise RuntimeError("Start wrapper did not defeat every target group")
        recorder.send(["b"], delay=0.8)
        recorder.send(["start"], delay=1.0)
        recorder.send(["down", "down", "down", "down"], delay=0.55)
        recorder.send(["c"], delay=1.4)
        return {
            "mode": mode,
            "start_menu": shared.image_report(start_menu),
            "clear_gst": shared.relative(clear_gst),
            "clear_state": state,
        }
    if mode == "attack_up":
        recorder.send(["down"], delay=0.55)
        recorder.send(["c"], delay=0.8)
        recorder.send(["up"], delay=0.7)
        target = recorder.capture("battle/attack_target.png")
        recorder.send(["c"], delay=1.4)
        return {"mode": mode, "target": shared.image_report(target)}
    if mode == "move_up":
        recorder.send(["c"], delay=0.8)
        recorder.send(["up"], delay=0.7)
        destination = recorder.capture("battle/escape_destination.png")
        recorder.send(["c"], delay=0.8)
        recorder.send(["c"], delay=1.4)
        return {
            "mode": mode,
            "destination": shared.image_report(destination),
        }
    raise ValueError(f"unsupported completion mode: {mode}")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = (
        args.output_root / args.profile / f"s{args.scenario:02d}" / args.run_id
    )
    if output.exists():
        raise FileExistsError(f"result output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s{args.scenario:02d}-result-{args.profile}-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        output,
        args.display,
        args.runtime_root / runtime_name,
    )
    started = time.monotonic()
    definition = SCENARIOS[args.scenario]
    try:
        identity = matrix.launch_to_preparation(
            recorder,
            args.rom,
            args.seed_gst,
            args.scenario,
            runtime_name,
            output,
        )
        preparation = recorder.capture("preparation.png")
        gray.enter_battle_command(recorder, args.rom, output)
        command = recorder.capture("battle/turn1_command.png")
        completion = trigger_completion(recorder, definition)

        result_source, result_frame, result_observations = wait_for_surface(
            recorder,
            wanted="battle_result",
            phase="aftermath",
            max_frames=args.max_result_frames,
            settle_delay=args.settle_delay,
        )
        result = output / "aftermath/battle_result.png"
        shutil.copy2(result_source, result)
        result_gst = recorder.save_gst("states/battle_result.gst")

        recorder.send(["c"], delay=0.8)
        save_source, save_frame, save_observations = wait_for_surface(
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
            "scenario": args.scenario,
            "run_id": args.run_id,
            "rom": {
                "path": shared.relative(args.rom),
                "sha256": shared.sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "scenario_identity": identity,
            "preparation": shared.image_report(preparation),
            "turn1_command": shared.image_report(command),
            "completion": completion,
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
            "scenario": args.scenario,
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
    parser.add_argument("--scenario", type=int, choices=tuple(SCENARIOS), required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--max-result-frames", type=int, default=260)
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
    if args.settle_delay < 0:
        parser.error("--settle-delay must be nonnegative")
    report = run_capture(args)
    print(
        f"{report['status']}: {args.profile} Scenario {args.scenario} "
        f"result at frame {report['battle_result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
