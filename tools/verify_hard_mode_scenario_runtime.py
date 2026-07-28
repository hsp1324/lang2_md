#!/usr/bin/env python3
"""Enter hard-mode scenarios and verify every planned fixed enemy in RAM."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import hard_mode_plan
from tools import verify_hard_mode_runtime_evidence as runtime_evidence


DEFAULT_ROM = (
    ROOT
    / "roms/releases/Langrisser II (Korean Hard T1.0.0 B1.0.0).md"
)
DEFAULT_RESULTS = ROOT / "localization/hard_mode_scenario_smoke.json"
MIDGAME_SEED = ROOT / "captures/analysis/733a_s16_result_fixed_stable.gst"
LATEGAME_SEED = ROOT / "captures/analysis/a205_s27_fixed_summon_loaded.gst"
RUNNER = ROOT / "tools/run_blastem_sequence.py"
KEY_SENDER = ROOT / "tools/send_blastem_keys.py"
CAPTURE = ROOT / "tools/capture_blastem_window.py"
RUNTIME_ROOT = ROOT / "captures/runtime"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_for_scenario(scenario_number: int) -> Path:
    return LATEGAME_SEED if scenario_number >= 25 else MIDGAME_SEED


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.check_call(command, cwd=ROOT, env=env)


def locate_quicksave(runtime_name: str) -> Path:
    matches = list((RUNTIME_ROOT / runtime_name).rglob("quicksave.gst"))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one quicksave for {runtime_name}, found {len(matches)}"
        )
    return matches[0]


def matching_player_group_count(gst: bytes, scenario_number: int) -> int:
    matches = []
    for player_group_count in range(11):
        try:
            runtime_evidence.verify_planned_scenario(
                gst,
                scenario_number,
                player_group_count,
            )
        except ValueError:
            continue
        matches.append(player_group_count)
    if len(matches) != 1:
        raise RuntimeError(
            f"Scenario {scenario_number} has ambiguous player-group "
            f"alignment: {matches}"
        )
    return matches[0]


def scenario_record_indexes(scenario_number: int) -> list[int]:
    plan = hard_mode_plan.build_plan()
    scenario = next(
        row for row in plan["scenarios"]
        if int(row["number"]) == scenario_number
    )
    return [int(record["index"]) for record in scenario["records"]]


def load_results(path: Path, rom: Path) -> dict:
    if path.exists():
        results = json.loads(path.read_text(encoding="utf-8"))
    else:
        results = {
            "schema_version": 1,
            "status": "in_progress",
            "hard_rom": {},
            "scenarios": [],
        }
    results["hard_rom"] = {
        "path": str(rom.relative_to(ROOT)),
        "sha256": sha256(rom),
    }
    return results


def save_result(path: Path, results: dict, result: dict) -> None:
    by_number = {
        int(entry["number"]): entry for entry in results.get("scenarios", [])
    }
    by_number[int(result["number"])] = result
    results["scenarios"] = [by_number[number] for number in sorted(by_number)]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def verify_scenario(
    scenario_number: int,
    *,
    rom: Path,
    display: str,
) -> dict:
    runtime_name = f"hard-matrix-s{scenario_number:02d}"
    seed = seed_for_scenario(scenario_number)
    run([
        sys.executable,
        str(RUNNER),
        "scenario-select",
        "--scenario-number",
        str(scenario_number),
        "--rom",
        str(rom),
        "--manual-slot-gst",
        str(seed),
        "--runtime-name",
        runtime_name,
        "--virtual-display",
        display,
        "--replace-existing",
        "--send-event",
    ])
    run([
        sys.executable,
        str(RUNNER),
        "detect-prep",
        "--no-launch",
        "--send-event",
        "--virtual-display",
        display,
        "--max-confirmations",
        "180",
        "--confirmation-delay",
        "0.4",
    ])

    env = os.environ.copy()
    env["DISPLAY"] = display
    run([
        sys.executable,
        str(KEY_SENDER),
        "--send-event",
        "down:0.25",
        "down:0.25",
        "down:0.25",
        "c:0.8",
        "down:0.25",
        "down:0.25",
        "c:1.0",
        "down:0.25",
        "down:0.25",
        "c:3.0",
        "save:1.0",
    ], env=env)

    capture = ROOT / f"captures/run/hard_matrix_s{scenario_number:02d}.png"
    run([
        sys.executable,
        str(CAPTURE),
        str(capture),
        "--xlib-only",
    ], env=env)
    gst = locate_quicksave(runtime_name)
    gst_bytes = gst.read_bytes()
    player_group_count = matching_player_group_count(
        gst_bytes,
        scenario_number,
    )
    indexes = scenario_record_indexes(scenario_number)
    return {
        "number": scenario_number,
        "status": "runtime_loader_smoke_verified",
        "endpoint": "자동 배치 후 출격",
        "player_group_count": player_group_count,
        "target_record_count": len(indexes),
        "runtime_group_range": [
            player_group_count + min(indexes),
            player_group_count + max(indexes),
        ],
        "gst": str(gst.relative_to(ROOT)),
        "gst_sha256": hashlib.sha256(gst_bytes).hexdigest(),
        "capture": str(capture.relative_to(ROOT)),
        "capture_sha256": sha256(capture),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        type=int,
        action="append",
        required=True,
        help="scenario number to verify; repeat for multiple scenarios",
    )
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--virtual-display", default=":114")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scenarios = list(dict.fromkeys(args.scenario))
    if any(not 1 <= number <= 31 for number in scenarios):
        raise ValueError("--scenario must be 1..31")
    rom = args.rom.resolve()
    results_path = args.results.resolve()
    results = load_results(results_path, rom)
    for scenario_number in scenarios:
        result = verify_scenario(
            scenario_number,
            rom=rom,
            display=args.virtual_display,
        )
        save_result(results_path, results, result)
        first_group, last_group = result["runtime_group_range"]
        print(
            f"Scenario {scenario_number}: {result['target_record_count']} "
            f"targets match in runtime groups {first_group}..{last_group}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
