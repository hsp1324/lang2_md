#!/usr/bin/env python3
"""Replay Scenario 13's final Vargas battle and retain result/save surfaces."""

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


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s13_result_revalidation"
DEFAULT_CONTINUATION_GST = (
    ROOT
    / "captures/runtime/s13-completion-0ce6/.local/share/blastem/"
    "Langrisser II (Scenario 13 Completion Probe)/quicksave.gst"
)
EXPECTED_CONTINUATION_SHA256 = (
    "11af030d8cf45a61502a60c1fde7811a3c256e92fcfd751944da739feacad658"
)
SCENARIO_NUMBER = 13
KEITH_RUNTIME_GROUP = 4
VARGAS_RUNTIME_GROUP = 17
EXPECTED_KEITH_POSITION = (19, 33)
EXPECTED_VARGAS_POSITION = (18, 33)
DEFAULT_ATTACK_ATTEMPTS = 8
DEFAULT_RETRY_RNG_DELAY = 0.11


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
    attempt: int,
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
    runtime_quicksave = quicksaves[-1]
    shutil.copy2(continuation_gst, runtime_quicksave)
    recorder.send([f"load:{load_delay}"])
    loaded = recorder.capture(
        f"continuation/attempt_{attempt:02d}_loaded.png"
    )
    retained = recorder.save_gst(
        f"states/attempt_{attempt:02d}_loaded_continuation.gst"
    )
    return loaded, retained


def select_keith_attack(
    recorder: matrix.RuntimeRecorder,
    *,
    attempt: int,
) -> Path:
    """Select Keith from the untouched continuation's command focus."""
    recorder.send(["b:0.6", "a:0.6", "a:0.6", "c:0.7"])
    recorder.send(["down:0.5", "c:0.6", "left:0.5"])
    return recorder.capture(
        f"battle/attempt_{attempt:02d}_target_vargas.png"
    )


def wait_for_result(
    recorder: matrix.RuntimeRecorder,
    *,
    max_frames: int,
    settle_delay: float,
) -> tuple[Path, int, list[dict[str, object]]]:
    """Advance the long stock aftermath until a positive result match."""
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
                "capture": shared.relative(capture),
                "sha256": shared.sha256(capture),
            }
        )
        if surface == "battle_result":
            return capture, frame, observations
        if surface == "save_menu":
            raise RuntimeError("save menu appeared before retaining battle result")
        # Several Scenario 13 dialogue pages satisfy the generic title-screen
        # heuristic. The bounded positive result/save classifiers are the safe
        # endpoint here; do not reject those stock dialogue panels as title.
        recorder.send(["c"], delay=0.45)
    raise RuntimeError("Scenario 13 battle result did not appear")


def wait_for_post_attack_dialogue(
    recorder: matrix.RuntimeRecorder,
    *,
    max_frames: int,
    settle_delay: float,
) -> tuple[Path, int]:
    """Let the ordinary battle animation finish without injecting input."""
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(
            f"battle/post_attack_wait_{frame:03d}.png"
        )
        if shared.sequence.battle_dialogue_visible(capture):
            return capture, frame
    raise RuntimeError("Scenario 13 post-attack dialogue did not appear")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / args.run_id
    if output.exists():
        raise FileExistsError(f"result output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s13-result-{args.profile}-{args.run_id}"
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
                "Scenario 13 continuation GST changed: "
                f"{continuation_sha256}"
            )
        attack_attempts = []
        loaded = None
        loaded_gst = None
        identity = None
        keith = None
        vargas_before = None
        start_menu = None
        wrapper_gst = None
        vargas_hp_one = None
        target = None
        combat = None
        post_attack_gst = None
        vargas_after = None
        for attempt in range(1, args.attack_attempts + 1):
            # A miss cannot safely be retried from a restored mid-turn GST:
            # Scenario 13's event flow can reinsert Vargas and invalidate the
            # diagnostic HP wrapper. Relaunch the untouched continuation for
            # every RNG attempt instead.
            loaded, loaded_gst = launch_continuation(
                recorder,
                rom=args.rom,
                continuation_gst=args.seed_gst,
                runtime_name=runtime_name,
                attempt=attempt,
                initial_delay=args.initial_delay,
                load_delay=args.load_delay,
            )
            identity = matrix.verify_runtime_scenario_identity(
                loaded_gst,
                args.rom,
                SCENARIO_NUMBER,
            )
            keith = runtime_group(loaded_gst, KEITH_RUNTIME_GROUP)
            vargas_before = runtime_group(
                loaded_gst,
                VARGAS_RUNTIME_GROUP,
            )
            if (keith["x"], keith["y"]) != EXPECTED_KEITH_POSITION:
                raise RuntimeError(
                    f"continuation Keith position changed: {keith}"
                )
            if (
                vargas_before["name_id"] != 0x0F
                or vargas_before["hp"] != 8
                or (vargas_before["x"], vargas_before["y"])
                != EXPECTED_VARGAS_POSITION
            ):
                raise RuntimeError(
                    f"continuation Vargas changed: {vargas_before}"
                )

            # The diagnostic continuation probe hooks the stock Start entry.
            recorder.send(["b:0.6", "start:0.8"])
            start_menu = recorder.capture(
                f"battle/attempt_{attempt:02d}_vargas_hp_wrapper_start_menu.png"
            )
            wrapper_gst = recorder.save_gst(
                f"states/attempt_{attempt:02d}_vargas_hp_wrapper.gst"
            )
            vargas_hp_one = runtime_group(
                wrapper_gst,
                VARGAS_RUNTIME_GROUP,
            )
            if vargas_hp_one["name_id"] != 0x0F or vargas_hp_one["hp"] != 1:
                raise RuntimeError(
                    "identity-guarded Vargas HP wrapper did not run: "
                    f"{vargas_hp_one}"
                )

            target = select_keith_attack(
                recorder,
                attempt=attempt,
            )
            rng_delay = args.retry_rng_delay * (attempt - 1)
            time.sleep(rng_delay)
            recorder.send(["c:0.35"])
            combat = recorder.capture(
                f"battle/attempt_{attempt:02d}_ordinary_combat.png"
            )
            recorder.send(["c:0.5"])
            post_attack_gst = recorder.save_gst(
                f"states/attempt_{attempt:02d}_post_vargas_attack.gst"
            )
            vargas_after = runtime_group(
                post_attack_gst,
                VARGAS_RUNTIME_GROUP,
            )
            attack_attempts.append(
                {
                    "attempt": attempt,
                    "fresh_process_launch": True,
                    "rng_idle_delay_seconds": round(rng_delay, 3),
                    "loaded": shared.image_report(loaded),
                    "loaded_gst": shared.relative(loaded_gst),
                    "start_menu": shared.image_report(start_menu),
                    "wrapper_gst": shared.relative(wrapper_gst),
                    "target": shared.image_report(target),
                    "combat": shared.image_report(combat),
                    "checkpoint": shared.relative(post_attack_gst),
                    "checkpoint_sha256": shared.sha256(post_attack_gst),
                    "vargas_runtime_state": vargas_after,
                }
            )
            if vargas_after["hp"] == 0:
                break
            if vargas_after["hp"] != 1:
                raise RuntimeError(
                    "ordinary attack changed Vargas to unexpected HP: "
                    f"{vargas_after}"
                )
        assert target is not None
        assert combat is not None
        assert post_attack_gst is not None
        assert vargas_after is not None
        assert loaded is not None
        assert loaded_gst is not None
        assert identity is not None
        assert keith is not None
        assert vargas_before is not None
        assert start_menu is not None
        assert wrapper_gst is not None
        assert vargas_hp_one is not None
        if vargas_after["hp"] != 0:
            raise RuntimeError(
                "Vargas survived every stock-turn ordinary attack: "
                f"{vargas_after}"
            )

        post_attack_dialogue, post_attack_dialogue_frame = (
            wait_for_post_attack_dialogue(
                recorder,
                max_frames=args.max_post_attack_frames,
                settle_delay=args.post_attack_settle_delay,
            )
        )

        result_source, result_frame, observations = wait_for_result(
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
                    "resume the final Vargas battle and stock aftermath only; "
                    "pre-result map sprites are covered independently"
                ),
            },
            "loaded": shared.image_report(loaded),
            "loaded_gst": shared.relative(loaded_gst),
            "scenario_identity": identity,
            "keith_runtime_state": keith,
            "vargas_before": vargas_before,
            "start_menu": shared.image_report(start_menu),
            "wrapper_gst": shared.relative(wrapper_gst),
            "vargas_hp_one": vargas_hp_one,
            "attack_attempts": attack_attempts,
            "retry_method": (
                "fresh emulator process and untouched continuation GST for "
                "every miss; no mid-turn GST restore or later-turn retry"
            ),
            "target": shared.image_report(target),
            "combat": shared.image_report(combat),
            "post_attack_gst": shared.relative(post_attack_gst),
            "post_attack_gst_sha256": shared.sha256(post_attack_gst),
            "vargas_after": vargas_after,
            "post_attack_dialogue": shared.image_report(post_attack_dialogue),
            "post_attack_dialogue_frame": post_attack_dialogue_frame,
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
        help="untouched historical final-Vargas continuation GST",
    )
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--initial-delay", type=float, default=3.0)
    parser.add_argument("--load-delay", type=float, default=0.8)
    parser.add_argument(
        "--attack-attempts",
        type=int,
        default=DEFAULT_ATTACK_ATTEMPTS,
    )
    parser.add_argument(
        "--retry-rng-delay",
        type=float,
        default=DEFAULT_RETRY_RNG_DELAY,
    )
    parser.add_argument("--max-result-frames", type=int, default=140)
    parser.add_argument("--max-save-frames", type=int, default=80)
    parser.add_argument("--max-post-attack-frames", type=int, default=80)
    parser.add_argument("--post-attack-settle-delay", type=float, default=0.35)
    parser.add_argument("--settle-delay", type=float, default=0.8)
    args = parser.parse_args()
    for name in ("rom", "seed_gst", "output_root", "runtime_root"):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (("ROM", args.rom), ("continuation GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if (
        args.initial_delay < 0
        or args.load_delay < 0
        or args.settle_delay < 0
        or args.retry_rng_delay < 0
        or args.post_attack_settle_delay < 0
    ):
        parser.error("delays must not be negative")
    if args.attack_attempts < 1:
        parser.error("--attack-attempts must be positive")
    if (
        args.max_result_frames < 1
        or args.max_save_frames < 1
        or args.max_post_attack_frames < 1
    ):
        parser.error("frame limits must be positive")
    report = run_capture(args)
    print(
        f"{report['status']}: {args.profile} Scenario 13 result at "
        f"frame {report['battle_result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
