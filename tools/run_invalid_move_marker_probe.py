#!/usr/bin/env python3
"""Find and verify the real battle invalid-destination X marker."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel
from tools.analyze_preparation_vram_ownership import (
    load_gst,
    sprite_referenced_tiles,
)


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/invalid_move_marker_probe"
ROUTES = (
    ("up",) * 16,
    ("down",) * 16,
    ("left",) * 16,
    ("right",) * 16,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"invalid-move-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        output, args.display, args.runtime_root / runtime_name
    )
    xvfb = parallel.start_xvfb(
        args.xvfb, args.xvfb_library_path, args.display
    )
    started = time.monotonic()
    observations = []
    accepted = None
    try:
        identity = matrix.launch_to_preparation(
            recorder,
            args.rom,
            args.seed_gst,
            args.scenario,
            runtime_name,
            output,
        )
        gray.enter_battle_command(recorder, args.rom, output)
        for route_index, route in enumerate(ROUTES, 1):
            recorder.send(["c"], delay=0.6)
            for step_index, direction in enumerate(route, 1):
                recorder.send([direction], delay=0.18)
                state_path = recorder.save_gst(
                    f"states/route_{route_index:02d}_step_{step_index:02d}.gst"
                )
                referenced = sprite_referenced_tiles(load_gst(state_path))
                invalid_tiles = set(builder.BATTLE_INVALID_TARGET_CURSOR_TILES)
                row = {
                    "route": route_index,
                    "step": step_index,
                    "direction": direction,
                    "invalid_tiles_referenced": sorted(
                        referenced & invalid_tiles
                    ),
                }
                observations.append(row)
                if invalid_tiles <= referenced:
                    capture = recorder.capture("invalid_destination_x.png")
                    accepted = {
                        **row,
                        "capture": str(capture.relative_to(ROOT)),
                        "capture_sha256": sha256(capture),
                        "gst": str(state_path.relative_to(ROOT)),
                        "gst_sha256": sha256(state_path),
                    }
                    break
            if accepted is not None:
                break
            recorder.send(["b"], delay=0.6)

        dynamic_tiles = set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        invalid_tiles = set(builder.BATTLE_INVALID_TARGET_CURSOR_TILES)
        passed = accepted is not None and dynamic_tiles.isdisjoint(invalid_tiles)
        result = {
            "schema_version": 1,
            "status": "pass" if passed else "fail",
            "scenario": args.scenario,
            "scenario_identity": identity,
            "rom": {
                "path": str(args.rom.relative_to(ROOT)),
                "sha256": sha256(args.rom),
                "md_checksum": matrix.md_checksum(args.rom),
            },
            "invalid_marker_tiles": [
                f"0x{tile:04X}"
                for tile in builder.BATTLE_INVALID_TARGET_CURSOR_TILES
            ],
            "battle_dynamic_glyph_tiles_disjoint": dynamic_tiles.isdisjoint(
                invalid_tiles
            ),
            "accepted": accepted,
            "observations": observations,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "actions": recorder.actions,
        }
        (output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    finally:
        matrix.terminate_blastem_processes(display=args.display)
        parallel.stop_process(xvfb)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, required=True)
    parser.add_argument("--scenario", type=matrix.validate_scenario, default=12)
    parser.add_argument("--display", default=":369")
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    args = parser.parse_args()
    for name in (
        "rom", "seed_gst", "xvfb", "xvfb_library_path", "runtime_root",
        "output_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    result = run_probe(args)
    print(f"{result['status']}: invalid destination X marker")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
