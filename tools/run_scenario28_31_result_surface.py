#!/usr/bin/env python3
"""Replay fresh Scenario 28-31 completion probes through result and save."""

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

from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario01_09_result_surface as early
from tools import run_scenario21_result_surface as shared
from tools import build_scenario31_clear_probe_rom as scenario31_probe
from tools import run_blastem_sequence as sequence
from tools import verify_hard_mode_first_turn as first_turn


SCENARIOS = (28, 29, 30, 31)
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s28_31_result"
DETECTOR = ROOT / "tools/run_blastem_sequence.py"
GST_WORK_RAM_OFFSET = 0x2478
WORK_RAM_BYTES = 0x10000
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
SCENARIO31_TARGET_GROUP = (
    scenario31_probe.PLAYER_DEPLOYMENT_COUNT
    + scenario31_probe.COMPLETION_TARGET_RECORD_INDEX
)


def trigger_completion_wrapper(
    recorder: matrix.RuntimeRecorder,
    *,
    scenario: int,
    phase: str,
) -> dict[str, object] | None:
    if scenario == 31:
        return None
    capture = None
    attempts = 0
    for attempts in range(1, 5):
        # Scenario 30 can briefly retain its one-row `명령` panel after the
        # turn detector reports command-ready.  In that transient state the
        # first Start key is ignored.  Prove that the real five-row Start menu
        # opened before relying on the diagnostic wrapper side effect.
        recorder.send(["b"], delay=0.8)
        recorder.send(["start"], delay=1.0)
        capture = recorder.capture(f"battle/{phase}_start_wrapper.png")
        if first_turn.start_menu_cursor_row(capture) is not None:
            break
    else:
        raise RuntimeError(
            f"Scenario {scenario} {phase} completion wrapper did not open "
            "the Start menu"
        )
    assert capture is not None
    gst = recorder.save_gst(f"states/{phase}_start_wrapper.gst")
    recorder.send(["b"], delay=0.8)
    recorder.send(["c"], delay=0.8)
    return {
        "capture": shared.image_report(capture),
        "gst": shared.relative(gst),
        "gst_sha256": shared.sha256(gst),
        "open_attempts": attempts,
    }


def attack_up(
    recorder: matrix.RuntimeRecorder,
    *,
    phase: str,
) -> dict[str, object]:
    recorder.send(["down"], delay=0.7)
    recorder.send(["c"], delay=0.8)
    recorder.send(["up"], delay=0.7)
    target = recorder.capture(f"battle/{phase}_target.png")
    recorder.send(["c"], delay=1.4)
    combat = recorder.capture(f"battle/{phase}_combat.png")
    return {
        "target": shared.image_report(target),
        "combat": shared.image_report(combat),
    }


def scenario31_target_state(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET:GST_WORK_RAM_OFFSET + WORK_RAM_BYTES]
    if len(ram) != WORK_RAM_BYTES:
        raise ValueError(f"GST is missing work RAM: {path}")
    record = RUNTIME_GROUP_BASE + SCENARIO31_TARGET_GROUP * RUNTIME_GROUP_SIZE
    defeated_flag = ram[record + RUNTIME_DEFEATED_FLAG_OFFSET]
    return {
        "class_id": ram[record],
        "name_id": ram[record + 1],
        "defeated_flag": defeated_flag,
        "defeated": bool(defeated_flag & 0x80),
        "hp": ram[record + RUNTIME_HP_OFFSET],
        "x": ram[record + 0x06],
        "y": ram[record + 0x07],
    }


def restore_quicksave(
    recorder: matrix.RuntimeRecorder,
    checkpoint: Path,
    *,
    load_delay: float,
) -> None:
    candidates = sorted(
        recorder.runtime_home.rglob("quicksave.gst"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    if not candidates:
        raise RuntimeError("BlastEm runtime has no quicksave.gst to restore")
    shutil.copy2(checkpoint, candidates[-1])
    recorder.send(["load"], delay=load_delay)


def attack_scenario31_until_defeated(
    recorder: matrix.RuntimeRecorder,
    *,
    attack_attempts: int,
    retry_rng_delay: float,
    battle_frames: int,
    battle_delay: float,
) -> list[dict[str, object]]:
    """Retry the ordinary adjacent battle until stock variance reaches HP0."""
    pre_attack = recorder.save_gst("states/pre_scenario31_attack.gst")
    attempts = []
    target_state = None
    for attempt in range(1, attack_attempts + 1):
        if attempt > 1:
            restore_quicksave(recorder, pre_attack, load_delay=1.2)
        recorder.send(["down"], delay=0.45)
        recorder.send(["c"], delay=0.65)
        recorder.send(["up"], delay=0.45)
        target = recorder.capture(
            f"battle/attempt_{attempt:02d}_bernhardt_target.png"
        )
        rng_delay = retry_rng_delay * (attempt - 1)
        time.sleep(rng_delay)
        recorder.send(["c"], delay=0.25)
        frames = []
        checkpoint = None
        for frame in range(1, battle_frames + 1):
            capture = recorder.capture(
                f"battle/attempt_{attempt:02d}_advance_{frame:03d}.png"
            )
            frames.append(shared.image_report(capture))
            recorder.send(["c"], delay=battle_delay)
            checkpoint = recorder.save_gst(
                f"states/attempt_{attempt:02d}_frame_{frame:03d}.gst"
            )
            target_state = scenario31_target_state(checkpoint)
            if target_state["hp"] == 0:
                break
        assert checkpoint is not None
        assert target_state is not None
        attempts.append({
            "attempt": attempt,
            "rng_idle_delay_seconds": round(rng_delay, 3),
            "target": shared.image_report(target),
            "battle_frames": frames,
            "post_battle_gst": shared.relative(checkpoint),
            "post_battle_gst_sha256": shared.sha256(checkpoint),
            "target_runtime_state": target_state,
        })
        if target_state["hp"] == 0:
            return attempts
    raise RuntimeError(
        "Scenario 31 adjacent Bernhardt survived ordinary attack retries: "
        f"{target_state}"
    )


def wait_for_second_mina(
    recorder: matrix.RuntimeRecorder,
    *,
    output: Path,
    max_confirmations: int,
) -> Path:
    # The stock transformation does not restore Elwin's action flag.  The
    # accepted completion route therefore attacks the transformed Mina on the
    # next player turn, not by trying to reopen the acted Elwin immediately.
    # Wait until the first side-view battle and transformation dialogue have
    # fully returned to the map. Inputs sent while the combat animation is
    # still active are ignored, which previously made the apparent Start-menu
    # navigation race the fight.
    stable_map_checks = 0
    for step in range(max_confirmations + 1):
        frame = recorder.capture(f"battle/mina_transform_wait_{step:03d}.png")
        if sequence.battle_dialogue_visible(frame):
            time.sleep(0.3)
            recorder.send(["c"], delay=0.3)
            stable_map_checks = 0
        elif sequence.battle_map_surface_visible(frame):
            # The stock event briefly returns to the map before item awards
            # and transformation dialogue. Confirm that transition once. A
            # A sustained map observation means the queued event pages and
            # Mina's delayed transformation animation are exhausted and the
            # residual status panel can be closed.
            stable_map_checks += 1
            if stable_map_checks >= 8:
                break
            if stable_map_checks == 1:
                recorder.send(["c"], delay=0.3)
            else:
                time.sleep(0.18)
        else:
            # A newly opened dialogue panel has one or more blank draw frames
            # before its white glyphs appear. Do not count the map preceding
            # that transient blank panel as the final command-ready map.
            stable_map_checks = 0
            time.sleep(0.18)
    else:
        raise RuntimeError(
            "Scenario 30 first Mina battle did not return to the map within "
            f"{max_confirmations} screen checks"
        )

    # B safely closes the one-row `명령` status panel when it is present.
    recorder.send(["b"], delay=0.6)
    recorder.send(["start"], delay=1.0)
    start_menu = recorder.capture("battle/mina_transform_start_menu.png")
    initial_row = first_turn.start_menu_cursor_row(start_menu)
    if initial_row is None:
        raise RuntimeError(
            "Scenario 30 did not reach the Start menu after Mina transformed"
        )
    navigation_count = (4 - initial_row) % 5
    recorder.send(["down"] * navigation_count, delay=0.55)
    recorder.send(["c"], delay=0.6)
    recorder.run_command([
        sys.executable,
        str(DETECTOR),
        "detect-command",
        "--no-launch",
        "--open-map-command",
        "--send-event",
        "--virtual-display",
        recorder.display,
        "--max-confirmations",
        str(max_confirmations),
        "--confirmation-delay",
        "0.18",
        "--capture-prefix",
        str(output / "battle/mina_transform.png"),
    ])
    return recorder.capture("battle/mina_second_command.png")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = (
        args.output_root / args.profile / f"s{args.scenario:02d}" / args.run_id
    )
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

        first_wrapper = trigger_completion_wrapper(
            recorder,
            scenario=args.scenario,
            phase="first",
        )
        if args.scenario == 31:
            attacks = attack_scenario31_until_defeated(
                recorder,
                attack_attempts=args.attack_attempts,
                retry_rng_delay=args.retry_rng_delay,
                battle_frames=args.battle_frames,
                battle_delay=args.battle_delay,
            )
        else:
            attacks = [attack_up(recorder, phase="first")]
        second_command = None
        second_wrapper = None
        if args.scenario == 30:
            second_command = wait_for_second_mina(
                recorder,
                output=output,
                max_confirmations=args.max_transform_confirmations,
            )
            second_wrapper = trigger_completion_wrapper(
                recorder,
                scenario=args.scenario,
                phase="second",
            )
            attacks.append(attack_up(recorder, phase="second"))

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
            "first_wrapper": first_wrapper,
            "attacks": attacks,
            "second_mina_command": (
                shared.image_report(second_command)
                if second_command is not None
                else None
            ),
            "second_wrapper": second_wrapper,
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
            failure_gst = shared.relative(
                recorder.save_gst("states/failure.gst")
            )
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
    parser.add_argument("--scenario", type=int, choices=SCENARIOS, required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--max-transform-confirmations", type=int, default=500)
    parser.add_argument("--max-result-frames", type=int, default=500)
    parser.add_argument("--max-save-frames", type=int, default=160)
    parser.add_argument("--settle-delay", type=float, default=0.16)
    parser.add_argument("--attack-attempts", type=int, default=8)
    parser.add_argument("--retry-rng-delay", type=float, default=0.11)
    parser.add_argument("--battle-frames", type=int, default=36)
    parser.add_argument("--battle-delay", type=float, default=0.2)
    args = parser.parse_args()
    for name in ("rom", "seed_gst", "output_root", "runtime_root"):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if args.attack_attempts < 1 or args.battle_frames < 1:
        parser.error("attack attempts and battle frames must be positive")
    if args.retry_rng_delay < 0 or args.battle_delay < 0:
        parser.error("battle delays must not be negative")
    report = run_capture(args)
    print(
        f"{report['status']}: {args.profile} Scenario {args.scenario} "
        f"result at frame {report['battle_result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
