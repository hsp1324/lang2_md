#!/usr/bin/env python3
"""Run current-source result-surface probes in isolated parallel emulators."""

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

from tools import build_current_result_probe_matrix as probes
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel


DEFAULT_PROBE_ROOT = probes.DEFAULT_OUTPUT_ROOT
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/current_source_result_revalidation"
DEFAULT_SUMMARY_ROOT = ROOT / "tmp/current_source_result_revalidation"

RUNNERS: dict[int, str] = {
    10: "run_scenario10_result_surface.py",
    14: "run_scenario14_15_result_surface.py",
    15: "run_scenario14_15_result_surface.py",
    16: "run_scenario14_15_result_surface.py",
    17: "run_scenario17_result_surface.py",
    21: "run_scenario21_result_surface.py",
    22: "run_scenario22_result_surface.py",
    23: "run_scenario23_result_surface.py",
    24: "run_scenario24_result_surface.py",
    25: "run_scenario25_result_surface.py",
    26: "run_scenario26_result_surface.py",
    27: "run_scenario27_ending_surface.py",
}
SCENARIOS = tuple(RUNNERS)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def task_rom(probe_root: Path, profile: str, scenario: int) -> Path:
    filename = str(probes.PROBE_DEFINITIONS[scenario]["filename"])
    return probe_root / profile / filename


def runner_output_root(output_root: Path, scenario: int) -> Path:
    if scenario in (14, 15, 16):
        return output_root
    return output_root / f"s{scenario:02d}"


def task_output(
    output_root: Path,
    profile: str,
    scenario: int,
    run_id: str,
) -> Path:
    root = runner_output_root(output_root, scenario)
    if scenario in (14, 15, 16):
        return root / profile / f"s{scenario:02d}" / run_id
    return root / profile / run_id


def task_command(
    args: argparse.Namespace,
    profile: str,
    scenario: int,
    display: str,
) -> list[str]:
    command = [
        sys.executable,
        str(ROOT / "tools" / RUNNERS[scenario]),
        "--profile",
        profile,
        "--rom",
        str(task_rom(args.probe_root, profile, scenario)),
        "--seed-gst",
        str(args.seed_gst),
        "--display",
        display,
        "--output-root",
        str(runner_output_root(args.output_root, scenario)),
        "--runtime-root",
        str(args.runtime_root),
        "--run-id",
        args.run_id,
    ]
    if scenario in (14, 15, 16):
        command.extend(("--scenario", str(scenario)))
    return command


def run_one(
    args: argparse.Namespace,
    profile: str,
    scenario: int,
    display: str,
) -> dict[str, object]:
    output = task_output(
        args.output_root,
        profile,
        scenario,
        args.run_id,
    )
    command = task_command(args, profile, scenario, display)
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output.mkdir(parents=True, exist_ok=True)
    log = output / "parallel-worker.log"
    log.write_text(completed.stdout, encoding="utf-8")
    evidence = output / "evidence.json"
    failure = output / "failure.json"
    payload = None
    source = evidence if evidence.is_file() else failure
    if source.is_file():
        payload = json.loads(source.read_text(encoding="utf-8"))
    return {
        "profile": profile,
        "scenario": scenario,
        "display": display,
        "rom": relative(task_rom(args.probe_root, profile, scenario)),
        "command": [relative(Path(command[1])), *command[2:]],
        "returncode": completed.returncode,
        "status": payload.get("status") if payload else "missing_evidence",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "output": relative(output),
        "evidence": relative(evidence) if evidence.is_file() else None,
        "failure": relative(failure) if failure.is_file() else None,
        "log": relative(log),
    }


def run_parallel(args: argparse.Namespace) -> dict[str, object]:
    tasks = [
        (profile, scenario)
        for profile in args.profiles
        for scenario in args.scenarios
    ]
    workers = min(args.workers, len(tasks))
    displays = [f":{args.display_base + index}" for index in range(workers)]
    xvfb_processes: list[subprocess.Popen[bytes]] = []
    available: queue.SimpleQueue[str] = queue.SimpleQueue()
    rows: list[dict[str, object]] = []
    started = time.monotonic()
    try:
        for display in displays:
            xvfb_processes.append(
                parallel.start_xvfb(args.xvfb, args.xvfb_library_path, display)
            )
            available.put(display)

        def assigned(profile: str, scenario: int) -> dict[str, object]:
            display = available.get()
            try:
                return run_one(args, profile, scenario, display)
            finally:
                available.put(display)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(assigned, profile, scenario): (profile, scenario)
                for profile, scenario in tasks
            }
            for future in as_completed(futures):
                profile, scenario = futures[future]
                try:
                    row = future.result()
                except Exception as exc:
                    row = {
                        "profile": profile,
                        "scenario": scenario,
                        "status": "orchestrator_error",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                rows.append(row)
                print(f"{profile} Scenario {scenario}: {row['status']}", flush=True)
    finally:
        for process in xvfb_processes:
            parallel.stop_process(process)

    rows.sort(key=lambda row: (str(row["profile"]), int(row["scenario"])))
    passed = [
        row
        for row in rows
        if row.get("returncode") == 0 and row.get("status") == "pass"
    ]
    return {
        "schema_version": 1,
        "status": "pass" if len(passed) == len(rows) else "fail",
        "run_id": args.run_id,
        "profiles": args.profiles,
        "scenarios": args.scenarios,
        "workers": workers,
        "maximum_simultaneous_emulators": workers,
        "displays": displays,
        "passed_tasks": len(passed),
        "total_tasks": len(rows),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "release_promoted": False,
        "version_bumped": False,
        "results": rows,
    }


def parse_profiles(value: str) -> list[str]:
    profiles = [part.strip() for part in value.split(",") if part.strip()]
    if not profiles or any(profile not in {"normal", "hard"} for profile in profiles):
        raise argparse.ArgumentTypeError("profiles must be normal and/or hard")
    if len(set(profiles)) != len(profiles):
        raise argparse.ArgumentTypeError("profiles must not repeat")
    return profiles


def parse_scenarios(value: str) -> list[int]:
    scenarios = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not scenarios or any(scenario not in RUNNERS for scenario in scenarios):
        allowed = ",".join(str(scenario) for scenario in SCENARIOS)
        raise argparse.ArgumentTypeError(f"scenarios must be selected from {allowed}")
    if len(set(scenarios)) != len(scenarios):
        raise argparse.ArgumentTypeError("scenarios must not repeat")
    return scenarios


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    tasks = []
    for profile in args.profiles:
        for scenario in args.scenarios:
            tasks.append(
                {
                    "profile": profile,
                    "scenario": scenario,
                    "rom": relative(task_rom(args.probe_root, profile, scenario)),
                    "output": relative(
                        task_output(
                            args.output_root,
                            profile,
                            scenario,
                            args.run_id,
                        )
                    ),
                }
            )
    return {
        "schema_version": 1,
        "status": "pass",
        "command": "plan",
        "run_id": args.run_id,
        "workers": min(args.workers, len(tasks)),
        "tasks": tasks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--profiles", type=parse_profiles, default=["normal", "hard"])
    parser.add_argument("--scenarios", type=parse_scenarios, default=list(SCENARIOS))
    parser.add_argument("--probe-root", type=Path, default=DEFAULT_PROBE_ROOT)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--display-base", type=int, default=500)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    for name in (
        "probe_root",
        "seed_gst",
        "xvfb",
        "xvfb_library_path",
        "output_root",
        "runtime_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    tasks = [
        (profile, scenario)
        for profile in args.profiles
        for scenario in args.scenarios
    ]
    if not 1 <= args.workers <= parallel.MAX_WORKERS:
        parser.error(f"--workers must be 1..{parallel.MAX_WORKERS}")
    if not 1 <= args.display_base <= 999 - min(args.workers, len(tasks)):
        parser.error("--display-base does not leave room for every worker")
    for profile, scenario in tasks:
        rom = task_rom(args.probe_root, profile, scenario)
        if not rom.is_file():
            raise FileNotFoundError(f"probe ROM does not exist: {rom}")
        output = task_output(args.output_root, profile, scenario, args.run_id)
        if output.exists():
            raise FileExistsError(f"task output already exists: {output}")
    for label, path in (
        ("seed GST", args.seed_gst),
        ("Xvfb", args.xvfb),
        ("Xvfb library path", args.xvfb_library_path),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} does not exist: {path}")

    report = build_plan(args) if args.command == "plan" else run_parallel(args)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.summary is None:
        print(encoded, end="")
    else:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(encoded, encoding="utf-8")
        print(args.summary)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
