#!/usr/bin/env python3
"""Capture current equipment UI with the five reported item-name cases."""

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

from tools import run_preparation_surface_matrix as matrix


DEFAULT_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
DEFAULT_OUTPUT = ROOT / "captures/run/v132_equipment_item_names"
DEFAULT_RUNTIME_ROOT = ROOT / "captures/runtime"
ITEM_IDS = (26, 27, 28, 29, 30)
ITEM_NAMES = ("룬스톤", "크로스", "넥클리스", "오브", "스피드부츠")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Enter a preparation screen with a runtime-only inventory and "
            "capture the equipment item-name list"
        )
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--scenario", type=int, default=10)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--display", default=":110")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", default="current")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    runtime_name = f"v132-equipment-items-{args.run_id}"
    recorder = matrix.RuntimeRecorder(
        args.output,
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
            args.output,
            [
                "--manual-slot-items",
                ",".join(str(item_id) for item_id in ITEM_IDS),
            ],
        )
        recorder.capture("preparation.png")
        # Preparation action rows are 출병그룹, 장비착용, 상점, 지휘관배치.
        # Select the absolute second row rather than entering arrangement.
        matrix.ensure_action_row(recorder, "equipment", 1)
        # The action first transfers focus to the commander column. Selecting
        # the commander opens its equipment category, and selecting the first
        # category opens the saved item list.
        recorder.send(["c"], delay=1.4)
        recorder.capture("equipment/commander_focus.png")
        recorder.send(["c"], delay=1.4)
        recorder.capture("equipment/category.png")
        equipment = None
        for index in range(1, 9):
            recorder.send(["c"], delay=1.4)
            equipment = recorder.capture(
                f"equipment/cycle_{index:02d}.png"
            )
        if equipment is None:
            raise AssertionError("equipment cycle did not run")
        state = recorder.save_gst("states/equipment_item_names.gst")

        report = {
            "schema_version": 1,
            "status": "captured_unreviewed",
            "scenario": args.scenario,
            "rom": {
                "path": display_path(args.rom),
                "sha256": sha256(args.rom),
                "md_checksum": args.rom.read_bytes()[0x18E:0x190].hex().upper(),
            },
            "scenario_identity": identity,
            "runtime_only_inventory": [
                {"item_id": item_id, "expected_name": name}
                for item_id, name in zip(ITEM_IDS, ITEM_NAMES)
            ],
            "capture": str(equipment.resolve().relative_to(ROOT)),
            "capture_sha256": sha256(equipment),
            "gst": str(state.resolve().relative_to(ROOT)),
            "gst_sha256": sha256(state),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (args.output / "evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        matrix.terminate_blastem_processes(display=args.display)


if __name__ == "__main__":
    raise SystemExit(main())
