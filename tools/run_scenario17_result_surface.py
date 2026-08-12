#!/usr/bin/env python3
"""Capture the current Scenario 17 result path in an isolated probe."""

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

from tools import run_blastem_sequence as sequence
from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario14_15_result_surface as result_surface
from tools import build_scenario17_clear_probe_rom as probe_builder


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s17_result"
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


def work_ram(path: Path) -> bytes:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET:GST_WORK_RAM_OFFSET + WORK_RAM_BYTES]
    if len(ram) != WORK_RAM_BYTES:
        raise ValueError(f"GST is missing work RAM: {path}")
    return ram


def runtime_combat_state(path: Path) -> dict[str, int]:
    ram = work_ram(path)
    elwin = (
        (probe_builder.RUNTIME_GROUP_BASE & 0xFFFF)
        + probe_builder.PROTAGONIST_RUNTIME_GROUP
        * probe_builder.RUNTIME_GROUP_SIZE
    )
    bernhardt = (
        (probe_builder.RUNTIME_GROUP_BASE & 0xFFFF)
        + probe_builder.BERNHARDT_RUNTIME_GROUP
        * probe_builder.RUNTIME_GROUP_SIZE
    )
    return {
        "elwin_acted": ram[elwin + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET],
        "elwin_hp": ram[elwin + probe_builder.RUNTIME_HP_OFFSET],
        "elwin_at": ram[elwin + probe_builder.RUNTIME_AT_OFFSET],
        "bernhardt_hp": ram[bernhardt + probe_builder.RUNTIME_HP_OFFSET],
    }


def attack_bernhardt(recorder: matrix.RuntimeRecorder) -> None:
    # Scenario 17's first row is Move and second is Attack.  Once Attack is
    # selected the cursor starts on Elwin, one tile below Bernhardt.
    recorder.send(["down"], delay=0.7)
    recorder.send(["c"], delay=0.8)
    recorder.send(["up"], delay=0.7)
    recorder.send(["c"], delay=1.2)


def wait_for_first_attack_return(
    recorder: matrix.RuntimeRecorder,
    *,
    max_frames: int,
    settle_delay: float,
) -> tuple[Path, Path, int, list[dict[str, object]], dict[str, int]]:
    observations: list[dict[str, object]] = []
    stable_candidate: tuple[Path, Path, int, dict[str, int]] | None = None
    stable_candidate_frame = 0
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(f"battle/turn1_return_{frame:03d}.png")
        dialogue = sequence.battle_dialogue_visible(capture)
        battle_map = sequence.battle_map_surface_visible(capture)
        observations.append(
            {
                "frame": frame,
                "dialogue": dialogue,
                "battle_map": battle_map,
                "capture": relative(capture),
                "sha256": sha256(capture),
            }
        )
        if sequence.game_over_visible(capture) or sequence.title_screen_visible(capture):
            raise RuntimeError("turn-1 attack entered an ending instead of returning")
        if dialogue:
            stable_candidate = None
            stable_candidate_frame = 0
            recorder.send(["c"], delay=0.45)
            continue
        if battle_map:
            state_path = recorder.save_gst(
                f"states/turn1_return_{frame:03d}.gst"
            )
            state = runtime_combat_state(state_path)
            if (
                state["elwin_acted"] == 1
                and 0 < state["bernhardt_hp"] < 10
            ):
                if stable_candidate is None:
                    stable_candidate = (capture, state_path, frame, state)
                    stable_candidate_frame = frame
                    continue
                # Scenario 17 briefly exposes the map between the battle and
                # Elwin's post-battle dialogue.  Wait for four more stable
                # samples so that transient map cannot be mistaken for the
                # true command-ready return.
                if frame - stable_candidate_frame >= 4:
                    return capture, state_path, frame, observations, state
                continue
        stable_candidate = None
        stable_candidate_frame = 0
    raise RuntimeError("turn-1 stock attack did not return with Bernhardt alive")


def open_next_turn_command(
    recorder: matrix.RuntimeRecorder,
    rom: Path,
    output: Path,
    *,
    completed_turn: int,
) -> tuple[Path, dict[str, int]]:
    recorder.send(["start"], delay=1.0)
    start_menu = recorder.capture(
        f"battle/turn{completed_turn}_post_action_start_menu.png"
    )
    restored_gst = recorder.save_gst(
        f"states/turn{completed_turn}_post_action_start_menu.gst"
    )
    restored = runtime_combat_state(restored_gst)
    if restored["elwin_acted"] != 1:
        raise RuntimeError("Elwin was not marked acted before ending turn")
    if restored["elwin_at"] != probe_builder.TWO_HIT_ELWIN_RESTORE_AT:
        raise RuntimeError(
            "diagnostic Start wrapper did not restore Elwin's current AT23"
        )
    recorder.send(["down", "down", "down", "down"], delay=0.55)
    recorder.send(["c"], delay=1.4)
    recorder.run_command(
        [
            sys.executable,
            str(ROOT / "tools/run_blastem_sequence.py"),
            "detect-command",
            "--rom", str(rom),
            "--no-launch",
            "--open-map-command",
            "--confirmation-delay", "0.8",
            "--max-confirmations", "240",
            "--capture-prefix", str(
                output / f"detect/turn{completed_turn + 1}_command.png"
            ),
            "--virtual-display", recorder.display,
            "--send-event",
        ]
    )
    return start_menu, restored


def wait_for_attack_outcome(
    recorder: matrix.RuntimeRecorder,
    *,
    turn: int,
    max_frames: int,
    settle_delay: float,
) -> dict[str, object]:
    observations: list[dict[str, object]] = []
    stable_candidate_frame = 0
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(
            f"battle/turn{turn}_outcome_{frame:03d}.png"
        )
        surface = result_surface.classify_surface(capture)
        dialogue = sequence.battle_dialogue_visible(capture)
        battle_map = sequence.battle_map_surface_visible(capture)
        observations.append(
            {
                "frame": frame,
                "surface": surface,
                "dialogue": dialogue,
                "battle_map": battle_map,
                "capture": relative(capture),
                "sha256": sha256(capture),
            }
        )
        if surface == "battle_result":
            return {
                "kind": "result",
                "capture": capture,
                "frame": frame,
                "observations": observations,
            }
        if surface == "save_menu":
            raise RuntimeError("save menu appeared before retaining battle result")
        if sequence.game_over_visible(capture) or sequence.title_screen_visible(capture):
            raise RuntimeError(f"turn-{turn} attack entered a non-result ending")
        if dialogue:
            stable_candidate_frame = 0
            recorder.send(["c"], delay=0.45)
            continue
        if battle_map:
            state_path = recorder.save_gst(
                f"states/turn{turn}_outcome_{frame:03d}.gst"
            )
            state = runtime_combat_state(state_path)
            if state["elwin_acted"] == 1 and state["bernhardt_hp"] > 0:
                if stable_candidate_frame == 0:
                    stable_candidate_frame = frame
                    continue
                if frame - stable_candidate_frame >= 4:
                    return {
                        "kind": "survived",
                        "capture": capture,
                        "gst": state_path,
                        "frame": frame,
                        "state": state,
                        "observations": observations,
                    }
                continue
        stable_candidate_frame = 0
        # Battle animations advance automatically; C is harmless there and is
        # required for the ordinary dialogue, level-up, and class pages that
        # can follow a killing attack.
        recorder.send(["c"], delay=0.45)
    raise RuntimeError(f"turn-{turn} attack outcome was not resolved")


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
            raise RuntimeError("result path reached an ending before the save menu")
        recorder.send(["c"], delay=0.45)
    raise RuntimeError("save menu did not appear after the battle result")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / args.run_id
    if output.exists():
        raise FileExistsError(f"result output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"s17-result-{args.profile}-{args.run_id}"
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
        initial_command = recorder.capture("battle/turn1_command.png")

        # Close the command panel before invoking the diagnostic Start wrapper.
        recorder.send(["b"], delay=0.8)
        recorder.send(["start"], delay=1.0)
        first_start = recorder.capture("battle/first_start_menu.png")
        first_start_gst = recorder.save_gst("states/first_start_menu.gst")
        first_state = runtime_combat_state(first_start_gst)
        if first_state["elwin_acted"] != 0:
            raise RuntimeError("Elwin was already acted before the first attack")
        if first_state["elwin_at"] != probe_builder.TWO_HIT_ELWIN_AT:
            raise RuntimeError("diagnostic Start wrapper did not lower Elwin AT to 5")
        if first_state["bernhardt_hp"] != 10:
            raise RuntimeError("diagnostic wrapper changed Bernhardt's stock HP10")

        recorder.send(["b"], delay=0.7)
        recorder.send(["c"], delay=0.8)
        attack_bernhardt(recorder)
        (
            turn1_return,
            turn1_gst,
            turn1_frame,
            turn1_observations,
            turn1_state,
        ) = wait_for_first_attack_return(
            recorder,
            max_frames=args.max_first_attack_frames,
            settle_delay=args.settle_delay,
        )

        start_menu, restored_state = open_next_turn_command(
            recorder,
            args.rom,
            output,
            completed_turn=1,
        )
        turn2_command = recorder.capture("battle/turn2_command.png")
        turn2_gst = recorder.save_gst("states/turn2_command.gst")
        turn2_state = runtime_combat_state(turn2_gst)
        if turn2_state["elwin_acted"] != 0:
            raise RuntimeError("turn 2 command did not reset Elwin's acted flag")
        if turn2_state["elwin_at"] != probe_builder.TWO_HIT_ELWIN_RESTORE_AT:
            raise RuntimeError("turn 2 did not retain restored Elwin AT23")
        if not 0 < turn2_state["bernhardt_hp"] <= 10:
            raise RuntimeError("Bernhardt was not alive in the stock HP range on turn 2")

        attack_turns: list[dict[str, object]] = []
        current_turn = 2
        while True:
            attack_bernhardt(recorder)
            outcome = wait_for_attack_outcome(
                recorder,
                turn=current_turn,
                max_frames=args.max_result_frames,
                settle_delay=args.settle_delay,
            )
            attack_turns.append(
                {
                    **outcome,
                    "capture": image_report(outcome["capture"]),
                    **(
                        {"gst": relative(outcome["gst"])}
                        if "gst" in outcome
                        else {}
                    ),
                }
            )
            if outcome["kind"] == "result":
                result_source = outcome["capture"]
                result_frame = outcome["frame"]
                result_observations = outcome["observations"]
                break
            if current_turn >= args.max_attack_turn:
                raise RuntimeError(
                    "Bernhardt survived the configured stock-attack turns"
                )
            open_next_turn_command(
                recorder,
                args.rom,
                output,
                completed_turn=current_turn,
            )
            current_turn += 1
            command = recorder.capture(
                f"battle/turn{current_turn}_command.png"
            )
            command_gst = recorder.save_gst(
                f"states/turn{current_turn}_command.gst"
            )
            command_state = runtime_combat_state(command_gst)
            if command_state["elwin_acted"] != 0:
                raise RuntimeError(
                    f"turn {current_turn} did not reset Elwin's acted flag"
                )
            attack_turns.append(
                {
                    "kind": "next_turn_command",
                    "turn": current_turn,
                    "capture": image_report(command),
                    "gst": relative(command_gst),
                    "state": command_state,
                }
            )
        result = output / "battle/battle_result.png"
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
            "turn1_command": image_report(initial_command),
            "first_start_menu": image_report(first_start),
            "first_start_gst": relative(first_start_gst),
            "first_start_state": first_state,
            "turn1_return": image_report(turn1_return),
            "turn1_return_gst": relative(turn1_gst),
            "turn1_return_frame": turn1_frame,
            "turn1_state": turn1_state,
            "turn1_observations": turn1_observations,
            "post_action_start_menu": image_report(start_menu),
            "post_action_restored_state": restored_state,
            "turn2_command": image_report(turn2_command),
            "turn2_command_gst": relative(turn2_gst),
            "turn2_state": turn2_state,
            "attack_turns": attack_turns,
            "battle_result": image_report(result),
            "battle_result_frame": result_frame,
            "battle_result_gst": relative(result_gst),
            "battle_result_gst_sha256": sha256(result_gst),
            "result_observations": result_observations,
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
    parser.add_argument(
        "--profile", choices=("pure", "normal", "hard"), required=True
    )
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--max-first-attack-frames", type=int, default=80)
    parser.add_argument("--max-result-frames", type=int, default=240)
    parser.add_argument("--max-attack-turn", type=int, default=4)
    parser.add_argument("--max-save-frames", type=int, default=80)
    parser.add_argument("--settle-delay", type=float, default=0.8)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    report = run_capture(args)
    print(
        f"{report['status']}: {args.profile} Scenario 17 result at "
        f"frame {report['battle_result_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
