#!/usr/bin/env python3
"""Run gray acted-sprite matrices in isolated parallel BlastEm workers."""

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

from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel


def run_one(args: argparse.Namespace, scenario: int, display: str) -> dict[str, object]:
    started = time.monotonic()
    command = [
        sys.executable,
        str(ROOT / "tools/run_gray_acted_surface_matrix.py"),
        "--profile", args.profile,
        "--scenario", str(scenario),
        "--rom", str(args.rom),
        "--seed-gst", str(args.seed_gst),
        "--display", display,
        "--output-root", str(args.output_root),
        "--runtime-root", str(args.runtime_root),
        "--run-id", args.run_id,
        "--directions", ",".join(args.directions),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = (
        args.output_root / args.profile / f"s{scenario:02d}" / args.run_id
    )
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "parallel-worker.log"
    log_path.write_text(completed.stdout, encoding="utf-8")
    evidence_path = output / "evidence.json"
    evidence = (
        json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence_path.is_file()
        else None
    )
    return {
        "scenario": scenario,
        "display": display,
        "returncode": completed.returncode,
        "status": evidence.get("status") if evidence else "failed_attempt",
        "directions_tried": evidence.get("directions_tried") if evidence else None,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "output": relative(output),
        "log": relative(log_path),
    }


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def run_parallel(args: argparse.Namespace) -> dict[str, object]:
    workers = min(args.workers, len(args.scenarios))
    displays = [f":{args.display_base + index}" for index in range(workers)]
    xvfb_processes = []
    available: queue.SimpleQueue[str] = queue.SimpleQueue()
    rows = []
    started = time.monotonic()
    try:
        for display in displays:
            xvfb_processes.append(
                parallel.start_xvfb(args.xvfb, args.xvfb_library_path, display)
            )
            available.put(display)

        def assigned(scenario: int) -> dict[str, object]:
            display = available.get()
            try:
                return run_one(args, scenario, display)
            finally:
                available.put(display)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(assigned, scenario): scenario
                for scenario in args.scenarios
            }
            for future in as_completed(futures):
                scenario = futures[future]
                try:
                    row = future.result()
                except Exception as exc:
                    row = {
                        "scenario": scenario,
                        "status": "orchestrator_error",
                        "returncode": None,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                rows.append(row)
                print(f"scenario {scenario:02d}: {row['status']}", flush=True)
    finally:
        for process in xvfb_processes:
            parallel.stop_process(process)
    rows.sort(key=lambda row: int(row["scenario"]))
    passed = [
        row for row in rows
        if row.get("returncode") == 0 and row.get("status") == "pass"
    ]
    return {
        "schema_version": 1,
        "status": "pass" if len(passed) == len(rows) else "fail",
        "profile": args.profile,
        "rom": {
            "path": relative(args.rom),
            "sha256": gray.sha256(args.rom),
            "md_checksum": matrix.md_checksum(args.rom),
        },
        "run_id": args.run_id,
        "workers": workers,
        "display_base": args.display_base,
        "scenarios": args.scenarios,
        "directions": args.directions,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "passed_scenarios": len(passed),
        "total_scenarios": len(rows),
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--profile", choices=sorted(matrix.PROFILE_ROMS), required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--scenarios", type=parallel.parse_scenarios, default=parallel.parse_scenarios("1-31"))
    parser.add_argument("--directions", type=gray.parse_directions, default=list(gray.DEFAULT_DIRECTIONS))
    parser.add_argument("--workers", type=int, default=parallel.DEFAULT_WORKERS)
    parser.add_argument("--display-base", type=int, default=parallel.DEFAULT_DISPLAY_BASE)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument("--xvfb-library-path", type=Path, default=parallel.DEFAULT_XVFB_LIBRARY_PATH)
    parser.add_argument("--output-root", type=Path, default=gray.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.xvfb = args.xvfb.resolve()
    args.xvfb_library_path = args.xvfb_library_path.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    if not 1 <= args.workers <= parallel.MAX_WORKERS:
        parser.error(f"--workers must be 1..{parallel.MAX_WORKERS}")
    if not 1 <= args.display_base <= 999 - args.workers:
        parser.error("--display-base does not leave room for every worker")
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if args.command == "plan":
        result = {
            "schema_version": 1,
            "status": "pass",
            "command": "plan",
            "profile": args.profile,
            "rom": str(args.rom),
            "workers": min(args.workers, len(args.scenarios)),
            "displays": [
                f":{args.display_base + index}"
                for index in range(min(args.workers, len(args.scenarios)))
            ],
            "scenarios": args.scenarios,
            "directions": args.directions,
            "run_id": args.run_id,
        }
    else:
        result = run_parallel(args)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.summary is None:
        print(encoded, end="")
    else:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(encoded, encoding="utf-8")
        print(args.summary)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
