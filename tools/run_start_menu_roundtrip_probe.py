#!/usr/bin/env python3
"""Verify START menu glyphs survive save/load submenu round trips."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel


DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/start_menu_roundtrip_probe"
MENU_CROP = (40, 40, 170, 170)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        image.crop(MENU_CROP).save(destination)


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    output = args.output_root / args.run_id
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    runtime_name = f"start-roundtrip-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        output, args.display, args.runtime_root / runtime_name
    )
    xvfb = parallel.start_xvfb(
        args.xvfb, args.xvfb_library_path, args.display
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
        gray.enter_battle_command(recorder, args.rom, output)
        recorder.send(["b"], delay=0.8)

        recorder.send(["start"], delay=1.0)
        before = recorder.capture("start/main_before.png")
        before_crop = output / "start/main_before_crop.png"
        crop(before, before_crop)

        recorder.send(["down"], delay=0.5)
        recorder.send(["c"], delay=1.0)
        load_menu = recorder.capture("start/load_submenu.png")
        recorder.send(["b"], delay=0.8)
        recorder.send(["up"], delay=0.5)
        after_load = recorder.capture("start/main_after_load.png")
        after_load_crop = output / "start/main_after_load_crop.png"
        crop(after_load, after_load_crop)

        recorder.send(["c"], delay=1.0)
        save_menu = recorder.capture("start/save_submenu.png")
        recorder.send(["b"], delay=0.8)
        after_save = recorder.capture("start/main_after_save.png")
        after_save_crop = output / "start/main_after_save_crop.png"
        crop(after_save, after_save_crop)

        main_crops = (before_crop, after_load_crop, after_save_crop)
        main_sha = [sha256(path) for path in main_crops]
        passed = len(set(main_sha)) == 1
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
            "menu_crop": list(MENU_CROP),
            "main_crops_pixel_exact": passed,
            "main_crop_sha256": main_sha,
            "captures": {
                "main_before": str(before.relative_to(ROOT)),
                "load_submenu": str(load_menu.relative_to(ROOT)),
                "main_after_load": str(after_load.relative_to(ROOT)),
                "save_submenu": str(save_menu.relative_to(ROOT)),
                "main_after_save": str(after_save.relative_to(ROOT)),
            },
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
    parser.add_argument("--display", default=":367")
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
    print(
        f"{result['status']}: START main menu before/after load/save round trips"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
