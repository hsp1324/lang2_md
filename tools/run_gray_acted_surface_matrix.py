#!/usr/bin/env python3
"""Capture and verify one scenario's real-move gray acted sprite surface."""

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

from tools import run_preparation_surface_matrix as matrix
from tools.verify_preparation_surface_evidence import (
    GRAY_TILE_START,
    GRAY_VRAM_BYTES,
    GRAY_VRAM_START,
    expected_gray_payload,
    load_gst,
    plane_tile_hits,
    runtime_group_zero,
)


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/gray_acted_surface_matrix"
DEFAULT_DIRECTIONS = ("down", "right", "left", "up")
VALID_DIRECTIONS = frozenset(DEFAULT_DIRECTIONS)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_directions(value: str) -> list[str]:
    directions = [part.strip().lower() for part in value.split(",") if part.strip()]
    if not directions:
        raise argparse.ArgumentTypeError("at least one movement direction is required")
    invalid = [direction for direction in directions if direction not in VALID_DIRECTIONS]
    if invalid:
        raise argparse.ArgumentTypeError(
            "invalid movement direction(s): " + ", ".join(invalid)
        )
    if len(set(directions)) != len(directions):
        raise argparse.ArgumentTypeError("movement directions must not repeat")
    return directions


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        dimensions = [image.width, image.height]
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "dimensions": dimensions,
    }


def enter_battle_command(
    recorder: matrix.RuntimeRecorder,
    rom: Path,
    output: Path,
) -> None:
    matrix.open_arrangement(recorder, "deploy")
    # Arrangement rows: commander, order, auto, enemy, sortie.
    recorder.send(["down", "down"], delay=0.8)
    recorder.send(["c"], delay=1.4)
    auto = recorder.capture("deployment/after_auto_deploy.png")
    if not matrix.arrangement_menu_visible(auto):
        raise RuntimeError("automatic deployment did not return to arrangement menu")
    recorder.send(["down", "down"], delay=0.8)
    recorder.send(["c"], delay=1.2)
    recorder.capture("deployment/after_sortie_select.png")
    recorder.send(["c"], delay=1.2)
    recorder.capture("deployment/after_sortie_confirm.png")
    recorder.run_command(
        [
            sys.executable,
            str(ROOT / "tools/run_blastem_sequence.py"),
            "detect-command",
            "--rom", str(rom),
            "--no-launch",
            "--open-map-command",
            "--confirmation-delay", "0.8",
            "--max-confirmations", "200",
            "--capture-prefix", str(output / "detect/command.png"),
            "--virtual-display", recorder.display,
            "--send-event",
        ]
    )


def run_direction_attempt(
    *,
    profile: str,
    scenario: int,
    rom: Path,
    seed_gst: Path,
    display: str,
    output: Path,
    runtime_root: Path,
    run_id: str,
    direction: str,
    attempt: int,
) -> dict[str, object]:
    runtime_name = (
        f"gray-acted-{profile}-s{scenario:02d}-{run_id}-"
        f"a{attempt:02d}-{direction}"
    )
    if len(runtime_name) > 120 or Path(runtime_name).name != runtime_name:
        raise ValueError("gray acted runtime name is unsafe")
    runtime_home = runtime_root / runtime_name
    recorder = matrix.RuntimeRecorder(output, display, runtime_home)
    started = time.monotonic()
    try:
        scenario_identity = matrix.launch_to_preparation(
            recorder,
            rom,
            seed_gst,
            scenario,
            runtime_name,
            output,
        )
        recorder.capture("preparation.png")
        enter_battle_command(recorder, rom, output)
        active = recorder.capture("active_command.png")
        active_gst = recorder.save_gst("states/active_command.gst")
        before = runtime_group_zero(active_gst)

        # First C chooses Move, the directional key changes the destination,
        # and the two final confirmations apply the preview and end the action.
        recorder.send(["c"], delay=0.8)
        recorder.send([direction], delay=0.6)
        recorder.send(["c"], delay=0.8)
        recorder.send(["c"], delay=1.4)
        acted = recorder.capture("acted_gray.png")
        acted_gst = recorder.save_gst("states/acted_gray.gst")
        after = runtime_group_zero(acted_gst)

        state = load_gst(acted_gst)
        source_record, source_sprite_id, stock_gray = expected_gray_payload()
        gray_payload = state.vram[
            GRAY_VRAM_START : GRAY_VRAM_START + GRAY_VRAM_BYTES
        ]
        plane_references = [
            {
                "tile": f"0x{tile:04X}",
                "hits": plane_tile_hits(state, tile),
            }
            for tile in range(GRAY_TILE_START, GRAY_TILE_START + 4)
        ]
        coordinate_changed = (before["x"], before["y"]) != (
            after["x"], after["y"]
        )
        passed = (
            before["commander_id"] == after["commander_id"] == 1
            and before["class_id"] == after["class_id"] == 1
            and before["acted_flag"] == 0
            and after["acted_flag"] == 1
            and coordinate_changed
            and gray_payload == stock_gray
            and all(row["hits"] for row in plane_references)
        )
        return {
            "status": "pass" if passed else "fail",
            "direction": direction,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "scenario_identity": scenario_identity,
            "active_capture": image_report(active),
            "acted_capture": image_report(acted),
            "active_gst": relative(active_gst),
            "active_gst_sha256": sha256(active_gst),
            "acted_gst": relative(acted_gst),
            "acted_gst_sha256": sha256(acted_gst),
            "runtime_before": before,
            "runtime_after": after,
            "coordinate_changed": coordinate_changed,
            "source_record_offset": f"0x{source_record:06X}",
            "source_silhouette_id": f"0x{source_sprite_id:04X}",
            "gray_vram_range": "0x9600..0x967F",
            "gray_vram_sha256": hashlib.sha256(gray_payload).hexdigest(),
            "matches_stock_fighter_silhouette_expansion": gray_payload == stock_gray,
            "plane_references": plane_references,
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
    finally:
        matrix.terminate_blastem_processes(display=display)


def run_matrix(args: argparse.Namespace) -> dict[str, object]:
    output = (
        args.output_root / args.profile / f"s{args.scenario:02d}" / args.run_id
    )
    if output.exists():
        raise FileExistsError(f"gray acted output already exists: {output}")
    output.mkdir(parents=True)
    started = time.monotonic()
    attempts = []
    accepted = None
    for attempt, direction in enumerate(args.directions, 1):
        attempt_output = output / "attempts" / f"{attempt:02d}_{direction}"
        attempt_output.mkdir(parents=True)
        try:
            row = run_direction_attempt(
                profile=args.profile,
                scenario=args.scenario,
                rom=args.rom,
                seed_gst=args.seed_gst,
                display=args.display,
                output=attempt_output,
                runtime_root=args.runtime_root,
                run_id=args.run_id,
                direction=direction,
                attempt=attempt,
            )
        except Exception as exc:
            matrix.terminate_blastem_processes(display=args.display)
            row = {
                "status": "error",
                "direction": direction,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        attempts.append(row)
        if row["status"] == "pass":
            accepted = row
            break
    result = {
        "schema_version": 1,
        "status": "pass" if accepted is not None else "fail",
        "profile": args.profile,
        "scenario": args.scenario,
        "run_id": args.run_id,
        "rom": {
            "path": relative(args.rom),
            "sha256": sha256(args.rom),
            "md_checksum": matrix.md_checksum(args.rom),
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "directions_tried": [row["direction"] for row in attempts],
        "accepted_attempt": accepted,
        "attempts": attempts,
        "acceptance_updated": False,
        "limitations": [
            "This run covers a real Elwin/Fighter move and gray acted sprite only.",
            "Preparation/shop surfaces and non-Fighter custom silhouettes are separate gates.",
        ],
    }
    (output / "evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(matrix.PROFILE_ROMS), required=True)
    parser.add_argument("--scenario", type=matrix.validate_scenario, required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=matrix.DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument(
        "--directions",
        type=parse_directions,
        default=list(DEFAULT_DIRECTIONS),
    )
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    result = run_matrix(args)
    print(
        f"scenario {args.scenario:02d}: {result['status']} "
        f"({','.join(result['directions_tried'])})"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
