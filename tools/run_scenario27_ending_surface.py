#!/usr/bin/env python3
"""Capture current Scenario 27 preparation, Bernhardt battle, and ending."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario27_ending_probe_rom as probe_builder  # noqa: E402
from tools.capture_magic_application import portrait_dialogue_visible  # noqa: E402
from tools import run_blastem_sequence as sequence  # noqa: E402
from tools import run_gray_acted_surface_matrix as gray  # noqa: E402
from tools import run_preparation_surface_matrix as matrix  # noqa: E402
from tools import run_scenario21_result_surface as shared  # noqa: E402
from tools import verify_hard_mode_first_turn as first_turn  # noqa: E402


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s27_ending"
DEFAULT_ATTACK_ATTEMPTS = 8
DEFAULT_RETRY_RNG_DELAY = 0.11
DEFAULT_MAX_ENDING_FRAMES = 5200
STATIC_CAPTION_CONFIRM_FRAMES = 3
FIN_SHA256 = (
    "4cb7db62c30ace38e0d8b2fa1a34fc7b"
    "a31586104f5b59c9663b6ad9564a46b0"
)
GST_WORK_RAM_OFFSET = 0x2478
WORK_RAM_BYTES = 0x10000
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
BERNHARDT_RUNTIME_GROUP = 18
BERNHARDT_INITIAL_HP = 10


def fin_visible(path: Path) -> bool:
    """Recognize the reviewed terminal Fin frame without an ignored fixture."""
    return path.is_file() and shared.sha256(path) == FIN_SHA256


def ending_caption_visible(path: Path) -> bool:
    """Detect white closing captions drawn directly over a black field."""
    with Image.open(path).convert("RGB") as source:
        if source.size != (320, 240):
            return False
        band = source.crop((0, 175, 320, 235))
        pixels = list(band.get_flattened_data())
    white = sum(
        red > 160 and green > 160 and blue > 160
        for red, green, blue in pixels
    ) / len(pixels)
    black = sum(
        red < 25 and green < 25 and blue < 25
        for red, green, blue in pixels
    ) / len(pixels)
    return white > 0.01 and black > 0.85


def should_confirm_ending_surface(
    *,
    dialogue: bool,
    caption: bool,
    stable_caption_frames: int,
) -> bool:
    return dialogue or (
        caption and stable_caption_frames >= STATIC_CAPTION_CONFIRM_FRAMES
    )


def bernhardt_runtime_record(path: Path) -> bytes:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET:GST_WORK_RAM_OFFSET + WORK_RAM_BYTES]
    if len(ram) != WORK_RAM_BYTES:
        raise ValueError(f"GST is missing work RAM: {path}")
    record = (
        (RUNTIME_GROUP_BASE & 0xFFFF)
        + BERNHARDT_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    )
    return ram[record:record + RUNTIME_GROUP_SIZE]


def bernhardt_runtime_state(path: Path) -> dict[str, int | bool]:
    record = bernhardt_runtime_record(path)
    flag = record[RUNTIME_DEFEATED_FLAG_OFFSET]
    return {
        "class_id": record[0],
        "name_id": record[1],
        "defeated_flag": flag,
        "defeated": bool(flag & 0x80),
        "hp": record[RUNTIME_HP_OFFSET],
        "x": record[RUNTIME_X_OFFSET],
        "y": record[RUNTIME_X_OFFSET + 1],
    }


def require_staged_bernhardt(path: Path) -> dict[str, int | bool]:
    """Require the diagnostic Start wrapper's exact one-HP battle state."""
    state = bernhardt_runtime_state(path)
    expected = {
        "class_id": 0x4E,
        "name_id": 0x0E,
        "defeated": False,
        "hp": probe_builder.PROBE_BERNHARDT_HP,
        "x": probe_builder.PROBE_BERNHARDT_X,
        "y": probe_builder.PROBE_BERNHARDT_Y,
    }
    mismatches = {
        key: {"expected": value, "actual": state.get(key)}
        for key, value in expected.items()
        if state.get(key) != value
    }
    if mismatches:
        raise RuntimeError(
            "Scenario 27 diagnostic Start wrapper did not stage the exact "
            f"Bernhardt root: {mismatches}"
        )
    return state


def trigger_and_verify_start_wrapper(
    recorder: matrix.RuntimeRecorder,
) -> dict[str, object]:
    """Open the real Start menu and prove its diagnostic HP-only effect.

    ``gray.enter_battle_command`` stops in Elwin's unit command panel.  The
    wrapper operand at ROM ``0x00F2E0`` is only consumed when the global Start
    menu is opened, so merely reaching the unit panel cannot stage Bernhardt.
    Keep the exact close/open/close/reopen input round trip explicit here.
    """
    before_gst = recorder.save_gst("states/before_start_wrapper.gst")
    before_state = bernhardt_runtime_state(before_gst)
    expected_before = {
        "class_id": 0x4E,
        "name_id": 0x0E,
        "defeated": False,
        "hp": BERNHARDT_INITIAL_HP,
        "x": probe_builder.PROBE_BERNHARDT_X,
        "y": probe_builder.PROBE_BERNHARDT_Y,
    }
    before_mismatches = {
        key: {"expected": value, "actual": before_state.get(key)}
        for key, value in expected_before.items()
        if before_state.get(key) != value
    }
    if before_mismatches:
        raise RuntimeError(
            "Scenario 27 pre-wrapper Bernhardt root is unexpected: "
            f"{before_mismatches}"
        )

    recorder.send(["b"], delay=0.8)
    recorder.send(["start"], delay=1.0)
    start_menu = recorder.capture("battle/start_wrapper_menu.png")
    if first_turn.start_menu_cursor_row(start_menu) is None:
        raise RuntimeError("Scenario 27 diagnostic did not open the Start menu")
    staged_gst = recorder.save_gst("states/start_wrapper_staged.gst")
    staged_state = require_staged_bernhardt(staged_gst)

    before_record = bernhardt_runtime_record(before_gst)
    staged_record = bernhardt_runtime_record(staged_gst)
    changed_offsets = [
        offset
        for offset, (before, after) in enumerate(
            zip(before_record, staged_record, strict=True)
        )
        if before != after
    ]
    if changed_offsets != [RUNTIME_HP_OFFSET]:
        raise RuntimeError(
            "Scenario 27 Start wrapper changed unexpected Bernhardt runtime "
            f"bytes: {changed_offsets}"
        )

    recorder.send(["b"], delay=0.8)
    recorder.send(["c"], delay=0.8)
    command = recorder.capture("battle/turn1_command_staged.png")
    if not sequence.battle_command_menu_visible(command):
        raise RuntimeError(
            "Scenario 27 diagnostic did not reopen Elwin's unit command menu"
        )
    pre_attack_gst = recorder.save_gst("states/pre_bernhardt_attack.gst")
    pre_attack_state = require_staged_bernhardt(pre_attack_gst)
    if bernhardt_runtime_record(pre_attack_gst) != staged_record:
        raise RuntimeError(
            "Scenario 27 Bernhardt runtime record changed while returning "
            "from Start to Elwin's unit command menu"
        )
    return {
        "before_gst": before_gst,
        "before_state": before_state,
        "start_menu": start_menu,
        "staged_gst": staged_gst,
        "staged_state": staged_state,
        "changed_record_offsets": changed_offsets,
        "command": command,
        "pre_attack_gst": pre_attack_gst,
        "pre_attack_state": pre_attack_state,
        "action_sequence": ["b", "start", "b", "c"],
    }


def restore_quicksave(
    recorder: matrix.RuntimeRecorder,
    checkpoint: Path,
    *,
    load_delay: float,
) -> None:
    """Restore a retained pre-attack GST into the isolated BlastEm runtime."""
    candidates = sorted(
        recorder.runtime_home.rglob("quicksave.gst"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    if not candidates:
        raise RuntimeError("BlastEm runtime has no quicksave.gst to restore")
    shutil.copy2(checkpoint, candidates[-1])
    recorder.send(["load"], delay=load_delay)


def advance_battle_until_defeated(
    recorder: matrix.RuntimeRecorder,
    *,
    attempt: int,
    max_frames: int,
    battle_delay: float,
) -> tuple[list[dict[str, object]], Path, dict[str, int | bool], int]:
    """Advance stock combat, stopping confirmations as soon as HP reaches zero."""
    frames = []
    checkpoint = None
    state = None
    for frame in range(1, max_frames + 1):
        battle = recorder.capture(
            f"battle/attempt_{attempt:02d}_advance_{frame:03d}.png"
        )
        frames.append(shared.image_report(battle))
        # Bernhardt selection first opens the stock Elwin/Bernhardt
        # confrontation. Confirm those pages one at a time, then inspect the
        # runtime record. Once HP reaches zero no further confirmation may be
        # sent: one extra key can skip result, epilogue, or the stable Fin page.
        recorder.send(["c"], delay=battle_delay)
        checkpoint = recorder.save_gst(
            f"states/attempt_{attempt:02d}_battle_frame_{frame:03d}.gst"
        )
        state = bernhardt_runtime_state(checkpoint)
        if state["hp"] == 0:
            return frames, checkpoint, state, frame

    assert checkpoint is not None
    assert state is not None
    return frames, checkpoint, state, max_frames


def wait_for_fin(
    recorder: matrix.RuntimeRecorder,
    *,
    max_frames: int,
    settle_delay: float,
    confirmation_delay: float,
) -> tuple[Path, int, list[dict[str, object]]]:
    observations = []
    previous_sha256 = None
    confirmed_caption_sha256 = None
    stable_caption_frames = 0
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(f"ending/advance_{frame:04d}.png")
        fin = fin_visible(capture)
        dialogue = portrait_dialogue_visible(capture)
        caption = ending_caption_visible(capture)
        capture_sha256 = shared.sha256(capture)
        if caption and capture_sha256 == previous_sha256:
            stable_caption_frames += 1
        elif caption:
            stable_caption_frames = 1
        else:
            stable_caption_frames = 0
        observations.append(
            {
                "frame": frame,
                "fin": fin,
                "dialogue": dialogue,
                "caption": caption,
                "capture": shared.relative(capture),
                "sha256": capture_sha256,
                "stable_caption_frames": stable_caption_frames,
            }
        )
        if fin:
            return capture, frame, observations
        # The character epilogues intentionally use a broad navy dialogue
        # panel.  That surface can satisfy the generic title-screen heuristic,
        # so Scenario 27 must use the positive Fin template as its endpoint.
        # max_frames remains the bounded failure condition.
        # Dialogue pages need confirmation, while credits and the final
        # cinematic advance on their own.  The broad caption heuristic can
        # also match a bright scanline at the bottom edge of a moving
        # cinematic.  Confirm a caption-only surface only after the full frame
        # remains byte-identical for three captures; sending C into a moving
        # cinematic skips the stable Fin surface and returns to the title.
        caption_ready = should_confirm_ending_surface(
            dialogue=False,
            caption=caption,
            stable_caption_frames=stable_caption_frames,
        ) and capture_sha256 != confirmed_caption_sha256
        if dialogue or caption_ready:
            recorder.send(["c"], delay=confirmation_delay)
            if caption_ready:
                confirmed_caption_sha256 = capture_sha256
            stable_caption_frames = 0
        previous_sha256 = capture_sha256
    raise RuntimeError("Scenario 27 Fin screen did not appear")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / args.run_id
    if output.exists():
        raise FileExistsError(f"ending output already exists: {output}")
    output.mkdir(parents=True)
    seed = {
        "path": shared.relative(args.seed_gst),
        "sha256": shared.sha256(args.seed_gst),
    }
    runtime_name = f"s27-ending-{args.profile}-{args.run_id}"
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
        wrapper_stage = trigger_and_verify_start_wrapper(recorder)
        pre_attack_gst = wrapper_stage["pre_attack_gst"]
        if not isinstance(pre_attack_gst, Path):
            raise TypeError("Scenario 27 wrapper stage returned an invalid GST")
        staged_bernhardt = wrapper_stage["pre_attack_state"]

        target = None
        post_battle_gst = None
        bernhardt = None
        battle_frames = []
        attack_attempts = []
        for attempt in range(1, args.attack_attempts + 1):
            if attempt > 1:
                restore_quicksave(
                    recorder,
                    pre_attack_gst,
                    load_delay=args.load_delay,
                )

            recorder.send(["down"], delay=0.45)
            recorder.send(["c"], delay=0.65)
            recorder.send(["up"], delay=0.45)
            target = recorder.capture(
                f"battle/attempt_{attempt:02d}_bernhardt_target.png"
            )
            # The diagnostic Start wrapper has already staged HP1. Retain the
            # command-menu state only as bounded recovery if stock input or
            # the battle transition does not complete on the first attempt;
            # the ordinary combat/death handlers themselves stay untouched.
            time.sleep(args.retry_rng_delay * (attempt - 1))
            recorder.send(["c"], delay=0.25)

            (
                attempt_frames,
                post_battle_gst,
                bernhardt,
                stop_frame,
            ) = advance_battle_until_defeated(
                recorder,
                attempt=attempt,
                max_frames=args.battle_frames,
                battle_delay=args.battle_delay,
            )
            battle_frames.extend(attempt_frames)
            attack_attempts.append(
                {
                    "attempt": attempt,
                    "rng_idle_delay_seconds": round(
                        args.retry_rng_delay * (attempt - 1), 3
                    ),
                    "target": shared.image_report(target),
                    "battle_frames": attempt_frames,
                    "stop_frame": stop_frame,
                    "post_battle_gst": shared.relative(post_battle_gst),
                    "post_battle_gst_sha256": shared.sha256(post_battle_gst),
                    "bernhardt_runtime_state": bernhardt,
                }
            )
            if bernhardt["hp"] == 0:
                break

        assert target is not None
        assert post_battle_gst is not None
        assert bernhardt is not None
        # The stock death handler sets HP to zero before the white-fade phase
        # completes and before the defeated flag is committed.  HP zero here
        # proves the ordinary battle succeeded; the ending loop then advances
        # the untouched handler through that pending transition.
        if bernhardt["hp"] != 0:
            raise RuntimeError(
                "adjacent Bernhardt was not defeated by the ordinary attack: "
                f"{bernhardt}"
            )

        fin, fin_frame, observations = wait_for_fin(
            recorder,
            max_frames=args.max_ending_frames,
            settle_delay=args.settle_delay,
            confirmation_delay=args.confirmation_delay,
        )
        fin_gst = recorder.save_gst("states/fin.gst")
        seed_unchanged = shared.sha256(args.seed_gst) == seed["sha256"]
        if not seed_unchanged:
            raise RuntimeError("input seed GST changed during ending capture")
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
            "seed": seed,
            "seed_unchanged": seed_unchanged,
            "scenario_identity": identity,
            "preparation": shared.image_report(preparation),
            "turn1_command": shared.image_report(command),
            "turn1_command_staged": shared.image_report(
                wrapper_stage["command"]
            ),
            "bernhardt_target": shared.image_report(target),
            "pre_attack_gst": shared.relative(pre_attack_gst),
            "pre_attack_gst_sha256": shared.sha256(pre_attack_gst),
            "diagnostic_runtime_stage": {
                "harness_only": True,
                "natural_full_battle_clear": False,
                "product_release_rom_changed": False,
                "start_callback_operand_address": (
                    f"0x{probe_builder.START_MENU_ENTRY_OPERAND:06X}"
                ),
                "start_wrapper_address": (
                    f"0x{probe_builder.RUNTIME_WRAPPER:06X}"
                ),
                "stock_start_entry_address": (
                    f"0x{probe_builder.START_MENU_ENTRY:06X}"
                ),
                "wrapper_sha256": hashlib.sha256(
                    probe_builder.completion_hp_wrapper_code()
                ).hexdigest(),
                "trigger_action_sequence": wrapper_stage["action_sequence"],
                "before_start_menu_gst": shared.relative(
                    wrapper_stage["before_gst"]
                ),
                "before_start_menu_gst_sha256": shared.sha256(
                    wrapper_stage["before_gst"]
                ),
                "start_menu": shared.image_report(
                    wrapper_stage["start_menu"]
                ),
                "staged_gst": shared.relative(wrapper_stage["staged_gst"]),
                "staged_gst_sha256": shared.sha256(
                    wrapper_stage["staged_gst"]
                ),
                "target_runtime_record_changed_offsets": (
                    wrapper_stage["changed_record_offsets"]
                ),
                "before_bernhardt": wrapper_stage["before_state"],
                "runtime_hp_address": (
                    f"0x{probe_builder.BERNHARDT_RUNTIME_HP_ADDRESS:08X}"
                ),
                "bernhardt": staged_bernhardt,
                "ordinary_stock_attack_death_and_ending_handlers": True,
            },
            "attack_attempts": attack_attempts,
            "battle_frames": battle_frames,
            "post_battle_gst": shared.relative(post_battle_gst),
            "post_battle_gst_sha256": shared.sha256(post_battle_gst),
            "bernhardt_runtime_state": bernhardt,
            "fin": shared.image_report(fin),
            "fin_frame": fin_frame,
            "fin_gst": shared.relative(fin_gst),
            "fin_gst_sha256": shared.sha256(fin_gst),
            "ending_observations": observations,
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
            "rom": {
                "path": shared.relative(args.rom),
                "sha256": shared.sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "seed": seed,
            "seed_unchanged": shared.sha256(args.seed_gst) == seed["sha256"],
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
    parser.add_argument("--load-delay", type=float, default=0.8)
    parser.add_argument("--battle-frames", type=int, default=36)
    parser.add_argument("--battle-delay", type=float, default=0.2)
    parser.add_argument(
        "--max-ending-frames",
        type=int,
        default=DEFAULT_MAX_ENDING_FRAMES,
        help=(
            "bounded ending-capture limit; 5200 allows stable-frame caption "
            "confirmation without truncating the terminal cinematic"
        ),
    )
    parser.add_argument("--settle-delay", type=float, default=0.08)
    parser.add_argument("--confirmation-delay", type=float, default=0.14)
    args = parser.parse_args()
    if args.attack_attempts < 1:
        parser.error("--attack-attempts must be at least 1")
    if args.retry_rng_delay < 0:
        parser.error("--retry-rng-delay must not be negative")
    if args.load_delay < 0:
        parser.error("--load-delay must not be negative")
    if args.max_ending_frames < 1:
        parser.error("--max-ending-frames must be at least 1")
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    report = run_capture(args)
    print(
        f"{report['status']}: {args.profile} Scenario 27 Fin at "
        f"frame {report['fin_frame']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
