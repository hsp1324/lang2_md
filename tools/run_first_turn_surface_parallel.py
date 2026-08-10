#!/usr/bin/env python3
"""Run clean entry and no-action first-turn playback in parallel Xvfb workers."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import queue
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blastem_sequence as sequence
from tools import run_preparation_surface_parallel as parallel


DEFAULT_OUTPUT_ROOT = ROOT / "tmp/first_turn_surface_parallel"


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"command exited {completed.returncode}: "
            f"{' '.join(command)}\n{completed.stdout}"
        )
    return completed.stdout


def run_one(
    scenario: int,
    *,
    rom: Path,
    display: str,
    output_root: Path,
    evidence_prefix: str,
    xvfb: Path,
    xvfb_library_path: Path,
    emulator_speed: int,
    profile: str,
    allow_unapproved_defeat: bool,
) -> dict[str, object]:
    started = time.monotonic()
    scenario_text = f"{scenario:02d}"
    scenario_root = output_root / f"s{scenario_text}"
    scenario_root.mkdir(parents=True, exist_ok=True)
    loader_results = scenario_root / "loader.json"
    first_turn_results = scenario_root / "first_turn.json"
    prefix = f"{evidence_prefix}-{scenario_text}"
    xvfb_process = parallel.start_xvfb(
        xvfb,
        xvfb_library_path,
        display,
    )
    outputs: list[str] = []
    try:
        loader_command = [
                    sys.executable,
                    str(ROOT / "tools/verify_hard_mode_scenario_runtime.py"),
                    "--scenario",
                    str(scenario),
                    "--rom",
                    str(rom),
                    "--results",
                    str(loader_results),
                    "--virtual-display",
                    display,
                    "--evidence-prefix",
                    f"{prefix}-loader",
                ]
        if profile != "hard":
            loader_command.append("--skip-hard-runtime-check")
        outputs.append(run(loader_command))
        first_turn_command = [
                    sys.executable,
                    str(ROOT / "tools/verify_hard_mode_first_turn.py"),
                    "--scenario",
                    str(scenario),
                    "--rom",
                    str(rom),
                    "--results",
                    str(first_turn_results),
                    "--loader-results",
                    str(loader_results),
                    "--require-entry-rom-match",
                    "--resume-running",
                    "--virtual-display",
                    display,
                    "--opening-checks",
                    "240",
                    "--phase-checks",
                    "700",
                    "--confirmation-delay",
                    "0.15",
                    "--initial-delay",
                    "1.0",
                    "--emulator-speed",
                    str(emulator_speed),
                    "--pre-turn-move-direction",
                    "down",
                    "--evidence-prefix",
                    f"{prefix}-first-turn",
                ]
        if profile != "hard":
            first_turn_command.append("--skip-hard-runtime-check")
        if allow_unapproved_defeat:
            first_turn_command.append("--allow-unapproved-defeat")
        outputs.append(run(first_turn_command))
        result = json.loads(first_turn_results.read_text(encoding="utf-8"))
        row = next(
            row
            for row in result["scenarios"]
            if int(row["number"]) == scenario
        )
        return {
            "scenario": scenario,
            "status": "pass",
            "endpoint": row["endpoint"],
            "turn_counter": row["turn_counter"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "loader_results": str(loader_results.relative_to(ROOT)),
            "first_turn_results": str(first_turn_results.relative_to(ROOT)),
            "output": "".join(outputs),
        }
    except Exception as exc:
        return {
            "scenario": scenario,
            "status": "fail",
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "error": str(exc),
            "output": "".join(outputs),
        }
    finally:
        pids = sequence.running_blastem_pids(display=display)
        if pids:
            sequence.terminate_blastem_processes(display=display)
        parallel.stop_process(xvfb_process)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument(
        "--profile",
        choices=("normal", "hard", "pure"),
        required=True,
    )
    parser.add_argument(
        "--scenarios",
        type=parallel.parse_scenarios,
        default=list(range(1, 32)),
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--display-base", type=int, default=520)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--evidence-prefix", default="first-turn-surface")
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--emulator-speed", type=int, default=4)
    parser.add_argument(
        "--attempts",
        type=int,
        default=2,
        help="isolated emulator attempts per scenario for transient startup failures",
    )
    parser.add_argument(
        "--allow-unapproved-defeat",
        action="store_true",
        help="record natural defeat endpoints for cross-profile diagnosis",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.workers <= parallel.MAX_WORKERS:
        raise ValueError(
            f"--workers must be 1..{parallel.MAX_WORKERS}"
        )
    if not 1 <= args.attempts <= 4:
        raise ValueError("--attempts must be 1..4")
    if not args.rom.is_file():
        raise FileNotFoundError(args.rom)
    if args.output_root.exists():
        raise FileExistsError(args.output_root)
    args.output_root.mkdir(parents=True)
    displays: queue.Queue[str] = queue.Queue()
    for index in range(args.workers):
        displays.put(f":{args.display_base + index}")

    started = time.monotonic()
    rows: list[dict[str, object]] = []

    def assigned(scenario: int) -> dict[str, object]:
        display = displays.get()
        try:
            errors: list[str] = []
            for attempt in range(1, args.attempts + 1):
                row = run_one(
                    scenario,
                    rom=args.rom.resolve(),
                    display=display,
                    output_root=args.output_root.resolve(),
                    evidence_prefix=args.evidence_prefix,
                    xvfb=args.xvfb,
                    xvfb_library_path=args.xvfb_library_path,
                    emulator_speed=args.emulator_speed,
                    profile=args.profile,
                    allow_unapproved_defeat=args.allow_unapproved_defeat,
                )
                row["attempt"] = attempt
                if row["status"] == "pass":
                    if errors:
                        row["previous_errors"] = errors
                    return row
                errors.append(str(row.get("error", "unknown failure")))
                if attempt < args.attempts:
                    time.sleep(1.0)
            row["previous_errors"] = errors[:-1]
            return row
        finally:
            displays.put(display)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(assigned, scenario): scenario
            for scenario in args.scenarios
        }
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"Scenario {row['scenario']:02d}: {row['status']} "
                f"{row.get('endpoint', row.get('error', ''))}",
                flush=True,
            )

    rows.sort(key=lambda row: int(row["scenario"]))
    passed = all(row["status"] == "pass" for row in rows)
    summary = {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "rom": str(args.rom.resolve().relative_to(ROOT)),
        "profile": args.profile,
        "attempts_per_scenario": args.attempts,
        "scenarios": rows,
        "coverage": {
            "requested": args.scenarios,
            "passed": [
                row["scenario"] for row in rows if row["status"] == "pass"
            ],
            "failed": [
                row["scenario"] for row in rows if row["status"] != "pass"
            ],
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    (args.output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
