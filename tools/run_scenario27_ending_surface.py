#!/usr/bin/env python3
"""Capture current Scenario 27 preparation, Bernhardt battle, and ending."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario27_ending_probe_rom as probe_builder
from tools.capture_magic_application import portrait_dialogue_visible
from tools import run_blastem_sequence as sequence
from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario21_result_surface as shared


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_s27_ending"
FIN_REFERENCE = ROOT / "captures/run/e93e_s27_ending_watch/875.png"
GST_WORK_RAM_OFFSET = 0x2478
WORK_RAM_BYTES = 0x10000
RUNTIME_GROUP_BASE = 0xFFFF603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_DEFEATED_FLAG_OFFSET = 0x02
RUNTIME_HP_OFFSET = 0x03
RUNTIME_X_OFFSET = 0x06
BERNHARDT_RUNTIME_GROUP = 18


def fin_template_pixels() -> tuple[tuple[int, int], ...]:
    with Image.open(FIN_REFERENCE).convert("RGB") as source:
        return tuple(
            (x, y)
            for y in range(40, 170)
            for x in range(90, 230)
            if (
                source.getpixel((x, y))[0] >= 240
                and source.getpixel((x, y))[1] >= 220
                and source.getpixel((x, y))[2] <= 40
            )
        )


FIN_TEMPLATE_PIXELS = fin_template_pixels()


def fin_visible(path: Path) -> bool:
    with Image.open(path).convert("RGB") as source:
        if source.size != (320, 240):
            return False
        matches = sum(
            source.getpixel(point)[0] >= 240
            and source.getpixel(point)[1] >= 220
            and source.getpixel(point)[2] <= 40
            for point in FIN_TEMPLATE_PIXELS
        )
    return bool(FIN_TEMPLATE_PIXELS) and matches * 100 >= len(FIN_TEMPLATE_PIXELS) * 98


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


def bernhardt_runtime_state(path: Path) -> dict[str, int | bool]:
    payload = path.read_bytes()
    ram = payload[GST_WORK_RAM_OFFSET:GST_WORK_RAM_OFFSET + WORK_RAM_BYTES]
    if len(ram) != WORK_RAM_BYTES:
        raise ValueError(f"GST is missing work RAM: {path}")
    record = (
        (RUNTIME_GROUP_BASE & 0xFFFF)
        + BERNHARDT_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
    )
    flag = ram[record + RUNTIME_DEFEATED_FLAG_OFFSET]
    return {
        "class_id": ram[record],
        "name_id": ram[record + 1],
        "defeated_flag": flag,
        "defeated": bool(flag & 0x80),
        "hp": ram[record + RUNTIME_HP_OFFSET],
        "x": ram[record + RUNTIME_X_OFFSET],
        "y": ram[record + RUNTIME_X_OFFSET + 1],
    }


def wait_for_fin(
    recorder: matrix.RuntimeRecorder,
    *,
    max_frames: int,
    settle_delay: float,
    confirmation_delay: float,
) -> tuple[Path, int, list[dict[str, object]]]:
    observations = []
    for frame in range(1, max_frames + 1):
        time.sleep(settle_delay)
        capture = recorder.capture(f"ending/advance_{frame:04d}.png")
        fin = fin_visible(capture)
        dialogue = portrait_dialogue_visible(capture)
        caption = ending_caption_visible(capture)
        observations.append(
            {
                "frame": frame,
                "fin": fin,
                "dialogue": dialogue,
                "caption": caption,
                "capture": shared.relative(capture),
                "sha256": shared.sha256(capture),
            }
        )
        if fin:
            return capture, frame, observations
        # The character epilogues intentionally use a broad navy dialogue
        # panel.  That surface can satisfy the generic title-screen heuristic,
        # so Scenario 27 must use the positive Fin template as its endpoint.
        # max_frames remains the bounded failure condition.
        # Dialogue/result pages need confirmation, while credits and the final
        # cinematic advance on their own. Sending C into the cinematic skips
        # the stable Fin surface and returns directly to the title screen.
        if dialogue or caption:
            recorder.send(["c"], delay=confirmation_delay)
    raise RuntimeError("Scenario 27 Fin screen did not appear")


def run_capture(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.profile / args.run_id
    if output.exists():
        raise FileExistsError(f"ending output already exists: {output}")
    output.mkdir(parents=True)
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

        recorder.send(["down"], delay=0.45)
        recorder.send(["c"], delay=0.65)
        recorder.send(["up"], delay=0.45)
        target = recorder.capture("battle/bernhardt_target.png")
        recorder.send(["c"], delay=0.25)

        battle_frames = []
        for frame in range(1, args.battle_frames + 1):
            battle = recorder.capture(f"battle/advance_{frame:03d}.png")
            battle_frames.append(shared.image_report(battle))
            # Bernhardt selection first opens the stock Elwin/Bernhardt
            # confrontation. Confirmations advance those pages; once the
            # ordinary battle starts they are harmless until control returns.
            recorder.send(["c"], delay=args.battle_delay)
        post_battle_gst = recorder.save_gst("states/post_bernhardt_battle.gst")
        bernhardt = bernhardt_runtime_state(post_battle_gst)
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
            "scenario_identity": identity,
            "preparation": shared.image_report(preparation),
            "turn1_command": shared.image_report(command),
            "bernhardt_target": shared.image_report(target),
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
    parser.add_argument("--battle-frames", type=int, default=36)
    parser.add_argument("--battle-delay", type=float, default=0.2)
    parser.add_argument("--max-ending-frames", type=int, default=3200)
    parser.add_argument("--settle-delay", type=float, default=0.08)
    parser.add_argument("--confirmation-delay", type=float, default=0.14)
    args = parser.parse_args()
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
