#!/usr/bin/env python3
"""Replay current Scenario 18-20 final battles and retain result surfaces."""

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

from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario21_result_surface as shared


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s18_20_result_revalidation"
GST_WORK_RAM_OFFSET = 0x2478
WORK_RAM_BYTES = 0x10000

SCENARIOS: dict[int, dict[str, object]] = {
    18: {
        "seed": (
            ROOT
            / "captures/runtime/s18_completion_17f2/.local/share/blastem/"
            "Langrisser II (Scenario 18 Completion Probe)/quicksave.gst"
        ),
        "seed_sha256": (
            "7705afdf02ad178b589c74dbd59998279759f8eb68014b0fe74271a8741d01d3"
        ),
        "boss_group": 13,
        "boss_class": 0x5E,
        "boss_name": 0x54,
        "boss_position": (35, 4),
        "initial_hp": {"normal": 9, "hard": 9},
    },
    19: {
        "seed": (
            ROOT
            / "captures/runtime/s19_completion_2829_strong/.local/share/blastem/"
            "Langrisser II (Scenario 19 Completion Probe)/quicksave.gst"
        ),
        "seed_sha256": (
            "b7ea024e1332febd6dd00cd79224d99abc1543b830d9f2957189fd446956597d"
        ),
        "hard_seed": (
            ROOT
            / "captures/runtime/current-s19-hard-result06/.local/share/blastem/"
            "s19/quicksave.gst"
        ),
        "hard_seed_sha256": (
            "da46cf9718c0c93d9d643eb41fb385e394847beaa287c72c994a3700813ba54b"
        ),
        "boss_group": 10,
        "boss_class": 0x4A,
        "boss_name": 0x15,
        "boss_position": (37, 23),
        "initial_hp": {"normal": 10, "hard": 1},
    },
    20: {
        "seed": (
            ROOT
            / "captures/runtime/s20_completion_d2f9_hidden/.local/share/blastem/"
            "Langrisser II (Scenario 20 Completion Probe)/quicksave.gst"
        ),
        "seed_sha256": (
            "595c32d434bb3d79d0dd8513256c77a38c2191bedea95730c3eca1e23d3b3bc2"
        ),
        "boss_group": 13,
        "boss_class": 0x5D,
        "boss_name": 0x73,
        "boss_position": (22, 23),
        "initial_hp": {"normal": 10, "hard": 10},
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def runtime_group(path: Path, group: int) -> dict[str, int]:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET:GST_WORK_RAM_OFFSET + WORK_RAM_BYTES]
    if len(ram) != WORK_RAM_BYTES:
        raise ValueError(f"GST is missing work RAM: {path}")
    record = (matrix.RUNTIME_GROUP_BASE & 0xFFFF) + group * matrix.RUNTIME_GROUP_SIZE
    return {
        "group": group,
        "class_id": ram[record],
        "name_id": ram[record + 1],
        "defeated_flag": ram[record + 2],
        "hp": ram[record + 3],
        "x": ram[record + 6],
        "y": ram[record + 7],
    }


def default_seed(scenario: int, profile: str) -> Path:
    definition = SCENARIOS[scenario]
    if scenario == 19 and profile == "hard":
        return Path(definition["hard_seed"])
    return Path(definition["seed"])


def expected_seed_sha256(scenario: int, profile: str) -> str:
    definition = SCENARIOS[scenario]
    if scenario == 19 and profile == "hard":
        return str(definition["hard_seed_sha256"])
    return str(definition["seed_sha256"])


def launch_continuation(
    recorder: matrix.RuntimeRecorder,
    *,
    rom: Path,
    seed_gst: Path,
    runtime_name: str,
    initial_delay: float,
    load_delay: float,
) -> tuple[Path, Path]:
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
    recorder.send(["save:0.8"])
    quicksaves = sorted(
        recorder.runtime_home.rglob("quicksave.gst"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    if not quicksaves:
        raise RuntimeError("BlastEm did not create a continuation quicksave")
    shutil.copy2(seed_gst, quicksaves[-1])
    recorder.send([f"load:{load_delay}"])
    loaded = recorder.capture("continuation/loaded_target.png")
    loaded_gst = recorder.save_gst("states/loaded_continuation.gst")
    return loaded, loaded_gst


def begin_final_battle(
    recorder: matrix.RuntimeRecorder,
    *,
    scenario: int,
    loaded: Path,
) -> Path:
    if scenario == 20:
        recorder.send(["b:0.6", "c:0.7", "down:0.6", "c:0.7", "down:0.6"])
        attack_target = recorder.capture("battle/fias_attack_target.png")
    else:
        attack_target = loaded
    recorder.send(["c"], delay=0.45)
    return attack_target


def wait_for_result(
    recorder: matrix.RuntimeRecorder,
    *,
    scenario: int,
    max_frames: int,
    settle_delay: float,
) -> tuple[Path, int, list[dict[str, object]]]:
    observations = []
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(f"aftermath/advance_{frame:03d}.png")
        surface = shared.result_surface.classify_surface(capture)
        observations.append(
            {
                "frame": frame,
                "surface": surface,
                "dialogue": shared.sequence.battle_dialogue_visible(capture),
                "capture": relative(capture),
                "sha256": sha256(capture),
            }
        )
        if surface == "battle_result":
            return capture, frame, observations
        if surface == "save_menu":
            raise RuntimeError("save menu appeared before retaining battle result")
        # Several aftermath and class-change panels satisfy broad title-screen
        # heuristics. Only the bounded positive result/save classifiers are
        # safe for these historical stock continuations.
        recorder.send(["c"], delay=0.45)
    raise RuntimeError(f"Scenario {scenario} battle result did not appear")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / f"s{args.scenario:02d}" / args.run_id
    if output.exists():
        raise FileExistsError(f"result output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s{args.scenario}-result-{args.profile}-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        output,
        args.display,
        args.runtime_root / runtime_name,
    )
    started = time.monotonic()
    definition = SCENARIOS[args.scenario]
    try:
        seed_sha256 = sha256(args.seed_gst)
        expected_sha256 = expected_seed_sha256(args.scenario, args.profile)
        if seed_sha256 != expected_sha256:
            raise ValueError(
                f"Scenario {args.scenario} continuation GST changed: "
                f"{seed_sha256}"
            )

        loaded, loaded_gst = launch_continuation(
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
            args.scenario,
        )
        boss_group = int(definition["boss_group"])
        boss_before = runtime_group(loaded_gst, boss_group)
        expected_hp = int(definition["initial_hp"][args.profile])
        if (
            boss_before["class_id"] != int(definition["boss_class"])
            or boss_before["name_id"] != int(definition["boss_name"])
            or boss_before["hp"] != expected_hp
            or (boss_before["x"], boss_before["y"])
            != tuple(definition["boss_position"])
        ):
            raise RuntimeError(
                f"Scenario {args.scenario} boss continuation changed: "
                f"{boss_before}"
            )

        # Scenarios 18 and 19 retain an Attack target cursor. Scenario 20's
        # historical continuation instead retains the adjacent enemy-inspect
        # cursor: B returns to Elwin, C opens his command, then Attack + Down
        # selects Fias. Keep that distinction explicit so a status panel can
        # never be mistaken for a stalled result path.
        attack_target = begin_final_battle(
            recorder,
            scenario=args.scenario,
            loaded=loaded,
        )
        result_source, result_frame, observations = wait_for_result(
            recorder,
            scenario=args.scenario,
            max_frames=args.max_result_frames,
            settle_delay=args.settle_delay,
        )
        result = output / "aftermath/battle_result.png"
        shutil.copy2(result_source, result)
        result_gst = recorder.save_gst("states/battle_result.gst")
        boss_after = runtime_group(result_gst, boss_group)
        if boss_after["hp"] != 0:
            raise RuntimeError(
                f"Scenario {args.scenario} result retained boss HP: "
                f"{boss_after}"
            )

        recorder.send(["c"], delay=0.8)
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
            "scenario": args.scenario,
            "run_id": args.run_id,
            "rom": {
                "path": relative(args.rom),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "continuation_gst": {
                "path": relative(args.seed_gst),
                "sha256": seed_sha256,
                "untouched": True,
                "scope": "final adjacent boss target and stock aftermath only",
            },
            "scenario_identity": identity,
            "loaded": shared.image_report(loaded),
            "loaded_gst": relative(loaded_gst),
            "boss_before": boss_before,
            "attack_target": shared.image_report(attack_target),
            "battle_result": shared.image_report(result),
            "battle_result_frame": result_frame,
            "battle_result_gst": relative(result_gst),
            "battle_result_gst_sha256": sha256(result_gst),
            "boss_after": boss_after,
            "result_observations": observations,
            "save_menu": shared.image_report(save_menu),
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
            "scenario": args.scenario,
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
    parser.add_argument("--scenario", type=int, choices=tuple(SCENARIOS), required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--initial-delay", type=float, default=3.0)
    parser.add_argument("--load-delay", type=float, default=0.8)
    parser.add_argument("--max-result-frames", type=int, default=180)
    parser.add_argument("--max-save-frames", type=int, default=80)
    parser.add_argument("--settle-delay", type=float, default=0.7)
    args = parser.parse_args()
    if args.seed_gst is None:
        args.seed_gst = default_seed(args.scenario, args.profile)
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
        f"{report['status']}: {args.profile} Scenario {args.scenario} "
        f"result at frame {report['battle_result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
