#!/usr/bin/env python3
"""Replay Scenario 12's final stock battle and retain result/save surfaces."""

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

from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario21_result_surface as shared


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s12_result_revalidation"
DEFAULT_CONTINUATION_GST = (
    ROOT
    / "captures/runtime/s12-load-old-40bc/.local/share/blastem/"
    "Langrisser II (Scenario 12 Compact Clear Probe)/quicksave.gst"
)
EXPECTED_CONTINUATION_SHA256 = (
    "ac2958e056561b4c8345805b351f5b45ac55453c8e89db94ba787317d7588878"
)
SCENARIO_NUMBER = 12
SHERRY_RUNTIME_GROUP = 2
FINAL_LIVING_ARMOR_RUNTIME_GROUP = 9
EXPECTED_SHERRY_POSITION = (22, 8)
EXPECTED_TARGET_POSITION = (23, 8)


def runtime_group(path: Path, group: int) -> dict[str, int]:
    payload = path.read_bytes()
    start = matrix.GST_WORK_RAM_FILE_OFFSET
    ram = payload[start : start + 0x10000]
    if len(ram) != 0x10000:
        raise ValueError(f"GST is missing work RAM: {path}")
    record = matrix.RUNTIME_GROUP_BASE + group * matrix.RUNTIME_GROUP_SIZE
    return {
        "group": group,
        "class_id": ram[record],
        "name_id": ram[record + 1],
        "defeated_flag": ram[record + 2],
        "hp": ram[record + 3],
        "x": ram[record + 6],
        "y": ram[record + 7],
    }


def launch_continuation(
    recorder: matrix.RuntimeRecorder,
    *,
    rom: Path,
    continuation_gst: Path,
    runtime_name: str,
    initial_delay: float,
    load_delay: float,
) -> tuple[Path, Path]:
    """Launch an isolated emulator, then load the untouched continuation GST."""
    recorder.run_command(
        [
            sys.executable,
            str(ROOT / "tools/run_blastem_sequence.py"),
            "launch-only",
            "--rom",
            str(rom),
            "--runtime-name",
            runtime_name,
            "--initial-delay",
            str(initial_delay),
            "--virtual-display",
            recorder.display,
            "--replace-existing",
            "--send-event",
        ]
    )
    # Create the ROM-specific quicksave directory without deriving or editing
    # any game state. Replace that disposable state with the historical GST,
    # then ask BlastEm to load it normally.
    recorder.send(["save:0.8"])
    quicksaves = sorted(
        recorder.runtime_home.rglob("quicksave.gst"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    if not quicksaves:
        raise RuntimeError("BlastEm did not create a continuation quicksave")
    runtime_quicksave = quicksaves[-1]
    shutil.copy2(continuation_gst, runtime_quicksave)
    recorder.send([f"load:{load_delay}"])
    loaded = recorder.capture("continuation/loaded.png")
    retained = recorder.save_gst("states/loaded_continuation.gst")
    return loaded, retained


def select_sherry_attack(
    recorder: matrix.RuntimeRecorder,
    *,
    round_number: int,
) -> Path:
    """Close the current menu, cycle Elwin -> Hein -> Sherry, and target right."""
    recorder.send(["b:0.5", "a:0.5", "a:0.8", "c:0.5"])
    recorder.send(["down:0.5", "c:0.6", "right:0.5"])
    return recorder.capture(
        f"battle/round_{round_number:02d}_target_living_armor.png"
    )


def resolve_attack(
    recorder: matrix.RuntimeRecorder,
    *,
    round_number: int,
) -> tuple[dict[str, int], dict[str, object]]:
    target = select_sherry_attack(recorder, round_number=round_number)
    recorder.send(["c:0.35"])
    combat = recorder.capture(
        f"battle/round_{round_number:02d}_ordinary_combat.png"
    )
    recorder.send(["c:0.5"])
    checkpoint = recorder.save_gst(
        f"states/round_{round_number:02d}_post_combat.gst"
    )
    state = runtime_group(checkpoint, FINAL_LIVING_ARMOR_RUNTIME_GROUP)
    return state, {
        "round": round_number,
        "target": shared.image_report(target),
        "combat": shared.image_report(combat),
        "checkpoint": shared.relative(checkpoint),
        "checkpoint_sha256": shared.sha256(checkpoint),
        "target_runtime_state": state,
    }


def advance_to_second_round(
    recorder: matrix.RuntimeRecorder,
    *,
    rom: Path,
    output: Path,
) -> Path:
    # Dismiss the surviving Living Armor line, cancel the lingering target
    # cursor, and choose the untouched Start > End Turn entry.
    recorder.send(["c:0.7"])
    recorder.capture("battle/round_01_returned_map.png")
    recorder.send(["b:0.6", "start:0.8"])
    recorder.capture("battle/round_01_end_turn_menu.png")
    recorder.send(["down:0.4", "down:0.4", "down:0.4", "down:0.4", "c:1.4"])
    recorder.run_command(
        [
            sys.executable,
            str(ROOT / "tools/run_blastem_sequence.py"),
            "detect-command",
            "--rom",
            str(rom),
            "--no-launch",
            "--open-map-command",
            "--confirmation-delay",
            "0.8",
            "--max-confirmations",
            "200",
            "--capture-prefix",
            str(output / "battle/turn_02_detect.png"),
            "--virtual-display",
            recorder.display,
            "--send-event",
        ]
    )
    return recorder.capture("battle/turn_02_elwin_command.png")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / args.run_id
    if output.exists():
        raise FileExistsError(f"result output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s12-result-{args.profile}-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        output,
        args.display,
        args.runtime_root / runtime_name,
    )
    started = time.monotonic()
    try:
        continuation_sha256 = shared.sha256(args.seed_gst)
        if continuation_sha256 != EXPECTED_CONTINUATION_SHA256:
            raise ValueError(
                "Scenario 12 continuation GST changed: "
                f"{continuation_sha256}"
            )
        loaded, loaded_gst = launch_continuation(
            recorder,
            rom=args.rom,
            continuation_gst=args.seed_gst,
            runtime_name=runtime_name,
            initial_delay=args.initial_delay,
            load_delay=args.load_delay,
        )
        identity = matrix.verify_runtime_scenario_identity(
            loaded_gst,
            args.rom,
            SCENARIO_NUMBER,
        )
        sherry = runtime_group(loaded_gst, SHERRY_RUNTIME_GROUP)
        target_before = runtime_group(
            loaded_gst,
            FINAL_LIVING_ARMOR_RUNTIME_GROUP,
        )
        if (sherry["x"], sherry["y"]) != EXPECTED_SHERRY_POSITION:
            raise RuntimeError(f"continuation Sherry position changed: {sherry}")
        if (
            target_before["class_id"] != 0x59
            or target_before["name_id"] != 0x49
            or target_before["hp"] != 10
            or (target_before["x"], target_before["y"])
            != EXPECTED_TARGET_POSITION
        ):
            raise RuntimeError(
                f"continuation final Living Armor changed: {target_before}"
            )

        attacks = []
        state, attack = resolve_attack(recorder, round_number=1)
        attacks.append(attack)
        turn_two_command = None
        if state["hp"]:
            if not 1 <= state["hp"] < target_before["hp"]:
                raise RuntimeError(
                    "first ordinary attack did not reduce target HP: "
                    f"{state['hp']}"
                )
            turn_two_command = advance_to_second_round(
                recorder,
                rom=args.rom,
                output=output,
            )
            state, attack = resolve_attack(recorder, round_number=2)
            attacks.append(attack)
        if state["hp"] != 0:
            raise RuntimeError(
                f"final Living Armor survived two ordinary attacks: {state}"
            )

        result_source, result_frame, observations = shared.wait_for_result(
            recorder,
            max_frames=args.max_result_frames,
            settle_delay=args.settle_delay,
        )
        result = output / "aftermath/battle_result.png"
        shutil.copy2(result_source, result)
        result_gst = recorder.save_gst("states/battle_result.gst")
        recorder.send(["c:0.8"])
        save_source, save_frame = shared.wait_for_save_menu(
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
            "scenario": SCENARIO_NUMBER,
            "run_id": args.run_id,
            "rom": {
                "path": shared.relative(args.rom),
                "sha256": shared.sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "continuation_gst": {
                "path": shared.relative(args.seed_gst),
                "sha256": continuation_sha256,
                "untouched": True,
                "scope": (
                    "resume the final ordinary battle only; not fresh "
                    "deployment or hard-mode balance evidence"
                ),
            },
            "loaded": shared.image_report(loaded),
            "loaded_gst": shared.relative(loaded_gst),
            "scenario_identity": identity,
            "sherry_runtime_state": sherry,
            "target_before": target_before,
            "attack_rounds": attacks,
            "turn_two_command": (
                shared.image_report(turn_two_command)
                if turn_two_command is not None
                else None
            ),
            "battle_result": shared.image_report(result),
            "battle_result_frame": result_frame,
            "battle_result_gst": shared.relative(result_gst),
            "battle_result_gst_sha256": shared.sha256(result_gst),
            "result_observations": observations,
            "save_menu": shared.image_report(save_menu),
            "save_menu_frame": save_frame,
            "save_menu_gst": shared.relative(save_gst),
            "save_menu_gst_sha256": shared.sha256(save_gst),
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
            failure_gst = shared.relative(
                recorder.save_gst("states/failure.gst")
            )
        except Exception:
            pass
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "profile": args.profile,
            "scenario": SCENARIO_NUMBER,
            "run_id": args.run_id,
            "rom": {
                "path": shared.relative(args.rom),
                "sha256": shared.sha256(args.rom),
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
    parser.add_argument(
        "--seed-gst",
        type=Path,
        default=DEFAULT_CONTINUATION_GST,
        help="untouched historical final-battle continuation GST",
    )
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--initial-delay", type=float, default=3.0)
    parser.add_argument("--load-delay", type=float, default=0.8)
    parser.add_argument("--max-result-frames", type=int, default=120)
    parser.add_argument("--max-save-frames", type=int, default=80)
    parser.add_argument("--settle-delay", type=float, default=0.8)
    args = parser.parse_args()
    for name in ("rom", "seed_gst", "output_root", "runtime_root"):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (("ROM", args.rom), ("continuation GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if args.initial_delay < 0 or args.load_delay < 0 or args.settle_delay < 0:
        parser.error("delays must not be negative")
    if args.max_result_frames < 1 or args.max_save_frames < 1:
        parser.error("frame limits must be positive")
    report = run_capture(args)
    print(
        f"{report['status']}: {args.profile} Scenario 12 result at "
        f"frame {report['battle_result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
