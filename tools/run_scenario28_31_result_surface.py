#!/usr/bin/env python3
"""Replay fresh late-scenario completion probes through result and save."""

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
from tools import run_scenario13_result_surface as scenario13_result
from tools import run_scenario21_result_surface as shared
from tools import build_scenario31_clear_probe_rom as scenario31_probe
from tools import run_blastem_sequence as sequence
from tools import verify_hard_mode_first_turn as first_turn
from tools import build_scenario11_clear_probe_rom as scenario11_probe
from tools import build_scenario18_clear_probe_rom as scenario18_probe
from tools import build_scenario20_clear_probe_rom as scenario20_probe


SCENARIOS = (11, 12, 13, 18, 19, 20, 28, 29, 30, 31)
ATTACK_DIRECTIONS = {
    11: "right",
    12: "up",
    13: "up",
    18: "up",
    19: "down",
    20: "down",
    28: "up",
    29: "up",
    30: "up",
}
ATTACK_COMMANDER_CYCLES = {11: 2, 13: 5}
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
    direction: str = "up",
    target_checks: int = 30,
    target_delay: float = 0.15,
    confirm_idle_delay: float = 0.0,
) -> dict[str, object]:
    if direction not in {"up", "down", "left", "right"}:
        raise ValueError(f"unsupported attack direction: {direction}")
    recorder.send(["down"], delay=0.7)
    recorder.send(["c"], delay=0.8)
    recorder.send([direction], delay=0.7)
    target_observations = []
    target = None
    for step in range(target_checks + 1):
        candidate = recorder.capture(
            f"battle/{phase}_target_wait_{step:02d}.png"
        )
        observation = {
            "frame": step,
            "capture": shared.image_report(candidate),
            "battle_map": sequence.battle_map_surface_visible(candidate),
            "command_menu": sequence.battle_command_menu_visible(candidate),
        }
        target_observations.append(observation)
        if observation["battle_map"] and not observation["command_menu"]:
            target = candidate
            break
        if step < target_checks:
            time.sleep(target_delay)
    if target is None:
        raise RuntimeError(
            f"Scenario attack target for {phase} did not settle within "
            f"{target_checks} checks"
        )
    accepted_target = recorder.output / f"battle/{phase}_target.png"
    accepted_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, accepted_target)
    time.sleep(confirm_idle_delay)
    recorder.send(["c"], delay=1.4)
    combat = recorder.capture(f"battle/{phase}_combat.png")
    return {
        "target": shared.image_report(accepted_target),
        "target_frame": target_observations[-1]["frame"],
        "target_observations": target_observations,
        "confirm_idle_delay_seconds": round(confirm_idle_delay, 3),
        "combat": shared.image_report(combat),
    }


def cast_magic_arrow_up(
    recorder: matrix.RuntimeRecorder,
    *,
    phase: str,
    confirm_idle_delay: float = 0.0,
) -> dict[str, object]:
    """Choose the first spell (Magic Arrow) and target one cell upward."""
    command = recorder.capture(f"battle/{phase}_command.png")
    if not sequence.battle_command_menu_visible(command):
        raise RuntimeError(f"{phase} allied command menu is not visible")
    recorder.send(["down", "down"], delay=0.35)
    recorder.send(["c"], delay=0.7)
    magic_menu = recorder.capture(f"battle/{phase}_magic_menu.png")
    recorder.send(["c"], delay=1.0)
    target_origin = recorder.capture(
        f"battle/{phase}_magic_target_origin.png"
    )
    recorder.send(["up"], delay=0.7)
    target = recorder.capture(f"battle/{phase}_magic_target.png")
    if not sequence.battle_map_surface_visible(target):
        raise RuntimeError(f"{phase} Magic Arrow target overlay is not visible")
    time.sleep(confirm_idle_delay)
    recorder.send(["c"], delay=1.4)
    effect = recorder.capture(f"battle/{phase}_magic_effect.png")
    return {
        "mode": "magic_arrow",
        "command": shared.image_report(command),
        "magic_menu": shared.image_report(magic_menu),
        "target_origin": shared.image_report(target_origin),
        "target": shared.image_report(target),
        "confirm_idle_delay_seconds": round(confirm_idle_delay, 3),
        "effect": shared.image_report(effect),
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


def scenario11_completion_states(path: Path) -> dict[str, object]:
    """Read the retired stock groups and untouched final reinforcement."""
    prior = [
        early.runtime_group(path, scenario11_probe, group)
        for group in scenario11_probe.COMPLETION_DEFEATED_RUNTIME_GROUPS
    ]
    target_group = (
        scenario11_probe.PLAYER_DEPLOYMENT_COUNT
        + scenario11_probe.COMPLETION_TARGET_RECORD_INDEX
    )
    return {
        "prior_groups": prior,
        "target": early.runtime_group(path, scenario11_probe, target_group),
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


def attack_scenario13_vargas_until_defeated(
    recorder: matrix.RuntimeRecorder,
    *,
    pre_attack: Path,
    commander_cycles: int,
    attack_attempts: int,
    retry_rng_delay: float,
    battle_frames: int,
    battle_delay: float,
) -> list[dict[str, object]]:
    """Retry the identity-guarded HP1 Vargas Magic Arrow on a miss."""
    attempts = []
    vargas_state = None
    for attempt in range(1, attack_attempts + 1):
        if attempt > 1:
            restore_quicksave(recorder, pre_attack, load_delay=1.2)
        rng_delay = retry_rng_delay * (attempt - 1)
        recorder.send(["b"], delay=0.7)
        recorder.send(["a"] * commander_cycles, delay=0.6)
        recorder.send(["c"], delay=0.8)
        attack = cast_magic_arrow_up(
            recorder,
            phase=f"vargas_attempt_{attempt:02d}",
            confirm_idle_delay=rng_delay,
        )
        frames = []
        checkpoint = None
        for frame in range(1, battle_frames + 1):
            capture = recorder.capture(
                f"battle/vargas_attempt_{attempt:02d}_advance_{frame:03d}.png"
            )
            frames.append(shared.image_report(capture))
            recorder.send(["c"], delay=battle_delay)
            checkpoint = recorder.save_gst(
                f"states/vargas_attempt_{attempt:02d}_frame_{frame:03d}.gst"
            )
            vargas_state = scenario13_result.runtime_group(
                checkpoint,
                scenario13_result.VARGAS_RUNTIME_GROUP,
            )
            if vargas_state["hp"] == 0:
                break
        assert checkpoint is not None
        assert vargas_state is not None
        attempts.append({
            "attempt": attempt,
            "rng_idle_delay_seconds": round(rng_delay, 3),
            **attack,
            "battle_frames": frames,
            "post_battle_gst": shared.relative(checkpoint),
            "post_battle_gst_sha256": shared.sha256(checkpoint),
            "vargas_runtime_state": vargas_state,
        })
        if vargas_state["hp"] == 0:
            return attempts
        if vargas_state["name_id"] != 0x0F or vargas_state["hp"] != 1:
            raise RuntimeError(
                "Scenario 13 Vargas changed unexpectedly after Magic Arrow: "
                f"{vargas_state}"
            )
    raise RuntimeError(
        "Scenario 13 Vargas survived Magic Arrow retries: "
        f"{vargas_state}"
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


def wait_for_post_battle_command(
    recorder: matrix.RuntimeRecorder,
    *,
    output: Path,
    phase: str,
    max_confirmations: int,
) -> tuple[Path, Path]:
    stable_map_checks = 0
    for step in range(max_confirmations + 1):
        frame = recorder.capture(
            f"battle/{phase}_transition_{step:03d}.png"
        )
        if sequence.battle_dialogue_visible(frame):
            recorder.send(["c"], delay=0.3)
            stable_map_checks = 0
        elif sequence.battle_map_surface_visible(frame):
            stable_map_checks += 1
            if stable_map_checks >= 8:
                break
            time.sleep(0.18)
        else:
            # Dialogue panels have blank draw frames before their glyphs
            # appear. Do not accept the map immediately preceding one as the
            # settled post-Zorum map.
            stable_map_checks = 0
            time.sleep(0.18)
    else:
        raise RuntimeError(
            f"{phase} did not settle on the battle map within "
            f"{max_confirmations} checks"
        )

    # Scenario 13 returns with the cursor on newly spawned Vargas. C would
    # repeatedly open his enemy status panel, so explicitly cancel it, cycle
    # to an allied commander, and prove that the allied command menu opened.
    for attempt in range(1, 9):
        recorder.send(["b"], delay=0.5)
        recorder.send(["a"], delay=0.5)
        recorder.send(["c"], delay=0.8)
        command = recorder.capture(
            f"battle/{phase}_command_attempt_{attempt:02d}.png"
        )
        if sequence.battle_command_menu_visible(command):
            accepted = output / f"battle/{phase}_command.png"
            shutil.copy2(command, accepted)
            checkpoint = recorder.save_gst(f"states/{phase}_command.gst")
            return accepted, checkpoint
    raise RuntimeError(
        f"{phase} could not open an allied command menu after Vargas spawned"
    )


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

        first_wrapper = None
        second_command = None
        second_wrapper = None
        scenario13_transition = None
        scenario11_runtime = None
        completion_runtime = None
        if args.scenario == 13:
            attacks = [
                attack_up(
                    recorder,
                    phase="zorum",
                    direction="up",
                )
            ]
            second_command, transition_gst = wait_for_post_battle_command(
                recorder,
                output=output,
                phase="post_zorum",
                max_confirmations=args.max_transform_confirmations,
            )
            zorum_after = scenario13_result.runtime_group(
                transition_gst,
                15,
            )
            vargas_before = scenario13_result.runtime_group(
                transition_gst,
                scenario13_result.VARGAS_RUNTIME_GROUP,
            )
            if zorum_after["hp"] != 0 or vargas_before["name_id"] != 0x0F:
                raise RuntimeError(
                    "Scenario 13 Zorum/Vargas transition changed: "
                    f"Zorum={zorum_after}, Vargas={vargas_before}"
                )
            first_wrapper = trigger_completion_wrapper(
                recorder,
                scenario=args.scenario,
                phase="vargas",
            )
            wrapper_gst = ROOT / str(first_wrapper["gst"])
            vargas_hp_one = scenario13_result.runtime_group(
                wrapper_gst,
                scenario13_result.VARGAS_RUNTIME_GROUP,
            )
            if (
                vargas_hp_one["name_id"] != 0x0F
                or vargas_hp_one["hp"] != 1
            ):
                raise RuntimeError(
                    "Scenario 13 identity-guarded Vargas HP wrapper failed: "
                    f"{vargas_hp_one}"
                )
            pre_vargas_attack = recorder.save_gst(
                "states/pre_vargas_attack.gst"
            )
            attacks.extend(
                attack_scenario13_vargas_until_defeated(
                    recorder,
                    pre_attack=pre_vargas_attack,
                    commander_cycles=ATTACK_COMMANDER_CYCLES[args.scenario],
                    attack_attempts=args.attack_attempts,
                    retry_rng_delay=args.retry_rng_delay,
                    battle_frames=args.battle_frames,
                    battle_delay=args.battle_delay,
                )
            )
            scenario13_transition = {
                "command": shared.image_report(second_command),
                "gst": shared.relative(transition_gst),
                "gst_sha256": shared.sha256(transition_gst),
                "zorum_after": zorum_after,
                "vargas_before_wrapper": vargas_before,
                "vargas_after_wrapper": vargas_hp_one,
                "pre_vargas_attack_gst": shared.relative(pre_vargas_attack),
                "pre_vargas_attack_gst_sha256": shared.sha256(
                    pre_vargas_attack
                ),
            }
        else:
            first_wrapper = trigger_completion_wrapper(
                recorder,
                scenario=args.scenario,
                phase="first",
            )
            if args.scenario == 11:
                wrapper_gst = ROOT / str(first_wrapper["gst"])
                before = scenario11_completion_states(wrapper_gst)
                if any(
                    group["hp"] != 0
                    or not group["defeated_flag"] & 0x80
                    or group["x"] != 0xFF
                    for group in before["prior_groups"]
                ):
                    raise RuntimeError(
                        "Scenario 11 prior imperial groups were not retired: "
                        f"{before['prior_groups']}"
                    )
                target = before["target"]
                if (
                    target["name_id"]
                    != scenario11_probe.COMPLETION_TARGET_NAME_ID
                    or target["class_id"]
                    != scenario11_probe.COMPLETION_TARGET_CLASS_ID
                    or target["hp"] != scenario11_probe.COMPLETION_HP
                    or (target["x"], target["y"])
                    != scenario11_probe.COMPLETION_TARGET_POSITION
                ):
                    raise RuntimeError(
                        "Scenario 11 final reinforcement identity changed: "
                        f"{target}"
                    )
                scenario11_runtime = {"before_attack": before}
            elif args.scenario in (18, 20):
                module = (
                    scenario18_probe
                    if args.scenario == 18
                    else scenario20_probe
                )
                target_group = (
                    module.GREAT_DRAGON_RUNTIME_GROUP
                    if args.scenario == 18
                    else module.FIAS_RUNTIME_GROUP
                )
                expected_name = (
                    module.GREAT_DRAGON_NAME_ID
                    if args.scenario == 18
                    else module.FIAS_NAME_ID
                )
                expected_class = (
                    module.GREAT_DRAGON_CLASS_ID
                    if args.scenario == 18
                    else module.FIAS_CLASS_ID
                )
                wrapper_gst = ROOT / str(first_wrapper["gst"])
                before = early.runtime_group(
                    wrapper_gst,
                    module,
                    target_group,
                )
                if (
                    before["name_id"] != expected_name
                    or before["class_id"] != expected_class
                    or before["hp"] != module.COMPLETION_HP
                ):
                    raise RuntimeError(
                        f"Scenario {args.scenario} identity-guarded completion "
                        f"wrapper failed: {before}"
                    )
                completion_runtime = {"before_attack": before}
        if args.scenario == 31:
            attacks = attack_scenario31_until_defeated(
                recorder,
                attack_attempts=args.attack_attempts,
                retry_rng_delay=args.retry_rng_delay,
                battle_frames=args.battle_frames,
                battle_delay=args.battle_delay,
            )
        elif args.scenario != 13:
            commander_cycles = ATTACK_COMMANDER_CYCLES.get(args.scenario, 0)
            if commander_cycles:
                recorder.send(["b"], delay=0.7)
                recorder.send(["a"] * commander_cycles, delay=0.6)
                recorder.send(["c"], delay=0.8)
            attacks = [
                attack_up(
                    recorder,
                    phase="first",
                    direction=ATTACK_DIRECTIONS[args.scenario],
                )
            ]
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
            attacks.append(
                attack_up(
                    recorder,
                    phase="second",
                    direction=ATTACK_DIRECTIONS[args.scenario],
                )
            )

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
        if args.scenario == 11:
            after = scenario11_completion_states(result_gst)
            target = after["target"]
            if target["hp"] != 0 or not target["defeated_flag"] & 0x80:
                raise RuntimeError(
                    "Scenario 11 final reinforcement survived completion: "
                    f"{target}"
                )
            assert scenario11_runtime is not None
            scenario11_runtime["after_attack"] = after
        elif args.scenario in (18, 20):
            module = (
                scenario18_probe if args.scenario == 18 else scenario20_probe
            )
            target_group = (
                module.GREAT_DRAGON_RUNTIME_GROUP
                if args.scenario == 18
                else module.FIAS_RUNTIME_GROUP
            )
            after = early.runtime_group(result_gst, module, target_group)
            if after["hp"] != 0 or not after["defeated_flag"] & 0x80:
                raise RuntimeError(
                    f"Scenario {args.scenario} completion target survived: "
                    f"{after}"
                )
            assert completion_runtime is not None
            completion_runtime["after_attack"] = after

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
            "scenario13_transition": scenario13_transition,
            "scenario11_runtime": scenario11_runtime,
            "completion_runtime": completion_runtime,
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
