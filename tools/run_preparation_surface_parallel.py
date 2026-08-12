#!/usr/bin/env python3
"""Run preparation/shop surface matrices in isolated parallel BlastEm workers."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_preparation_surface_matrix as matrix


DEFAULT_XVFB = Path("/tmp/lang2-Xvfb")
DEFAULT_XVFB_LIBRARY_PATH = Path(
    "/tmp/lang2-xvfb-root/usr/lib/x86_64-linux-gnu"
)
DEFAULT_DISPLAY_BASE = 120
MIN_ISOLATED_DISPLAY_NUMBER = 100
DEFAULT_WORKERS = 6
MAX_WORKERS = 12


def parse_scenarios(value: str) -> list[int]:
    scenarios: set[int] = set()
    for part in value.split(","):
        token = part.strip()
        if not token:
            raise argparse.ArgumentTypeError("empty scenario token")
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = matrix.validate_scenario(start_text)
            end = matrix.validate_scenario(end_text)
            if end < start:
                raise argparse.ArgumentTypeError(
                    f"scenario range runs backwards: {token}"
                )
            scenarios.update(range(start, end + 1))
        else:
            scenarios.add(matrix.validate_scenario(token))
    if not scenarios:
        raise argparse.ArgumentTypeError("no scenarios selected")
    return sorted(scenarios)


def display_number(display: str) -> int:
    if not display.startswith(":") or not display[1:].isdigit():
        raise ValueError(f"parallel worker needs a simple X display: {display}")
    number = int(display[1:])
    if number < MIN_ISOLATED_DISPLAY_NUMBER:
        raise ValueError(
            "refusing a low-numbered/possibly physical X display; isolated "
            f"Xvfb displays must be :{MIN_ISOLATED_DISPLAY_NUMBER} or higher: "
            f"{display}"
        )
    return number


def wait_for_xvfb(display: str, process: subprocess.Popen[bytes]) -> None:
    port = 6000 + display_number(display)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = b""
            if process.stderr is not None:
                stderr = process.stderr.read()
            raise RuntimeError(
                f"Xvfb {display} exited with status {process.returncode}: "
                f"{stderr.decode('utf-8', errors='replace').strip()}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Xvfb {display} did not accept connections")


def start_xvfb(
    executable: Path,
    library_path: Path,
    display: str,
) -> subprocess.Popen[bytes]:
    # Validate before spawning anything.  A post-launch check could already
    # have attempted to claim the user's physical X server number.
    display_number(display)
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(library_path)
    process = subprocess.Popen(
        [
            str(executable),
            display,
            "-screen", "0", "960x720x24",
            "-ac", "-noreset", "-nolisten", "unix", "-listen", "tcp",
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    wait_for_xvfb(display, process)
    return process


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def run_one(
    *,
    profile: str,
    scenario: int,
    rom: Path,
    reference_rom: Path,
    seed_gst: Path,
    display: str,
    output_root: Path,
    runtime_root: Path,
    run_id: str,
) -> dict[str, object]:
    started = time.monotonic()
    command = [
        sys.executable,
        str(ROOT / "tools/run_preparation_surface_matrix.py"),
        "run",
        "--profile", profile,
        "--scenario", str(scenario),
        "--rom", str(rom),
        "--reference-rom", str(reference_rom),
        "--seed-gst", str(seed_gst),
        "--display", display,
        "--output-root", str(output_root),
        "--runtime-root", str(runtime_root),
        "--run-id", run_id,
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = output_root / profile / f"s{scenario:02d}" / run_id
    log_path = output / "parallel-worker.log"
    output.mkdir(parents=True, exist_ok=True)
    log_path.write_text(completed.stdout, encoding="utf-8")
    evidence_path = output / "evidence.json"
    evidence = None
    if evidence_path.is_file():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    return {
        "scenario": scenario,
        "display": display,
        "returncode": completed.returncode,
        "status": (
            evidence.get("status")
            if isinstance(evidence, dict)
            else "failed_attempt"
        ),
        "actual_pair_count": (
            evidence.get("actual_pair_count")
            if isinstance(evidence, dict)
            else None
        ),
        "expected_pair_count": (
            evidence.get("expected_pair_count")
            if isinstance(evidence, dict)
            else None
        ),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "output": str(output.relative_to(ROOT)),
        "log": str(log_path.relative_to(ROOT)),
    }


def run_parallel(args: argparse.Namespace) -> dict[str, object]:
    seed = {
        "path": relative(args.seed_gst),
        "sha256": sha256(args.seed_gst),
    }
    workers = min(args.workers, len(args.scenarios))
    displays = [f":{args.display_base + index}" for index in range(workers)]
    xvfb_processes: list[subprocess.Popen[bytes]] = []
    available: queue.SimpleQueue[str] = queue.SimpleQueue()
    started = time.monotonic()
    rows: list[dict[str, object]] = []
    try:
        for display in displays:
            xvfb_processes.append(
                start_xvfb(args.xvfb, args.xvfb_library_path, display)
            )
            available.put(display)

        def assigned(scenario: int) -> dict[str, object]:
            display = available.get()
            try:
                attempts = []
                for attempt in range(1, args.attempts + 1):
                    output = (
                        args.output_root
                        / args.profile
                        / f"s{scenario:02d}"
                        / args.run_id
                    )
                    if attempt > 1 and output.exists():
                        shutil.rmtree(output)
                    row = run_one(
                        profile=args.profile,
                        scenario=scenario,
                        rom=args.rom,
                        reference_rom=args.reference_rom,
                        seed_gst=args.seed_gst,
                        display=display,
                        output_root=args.output_root,
                        runtime_root=args.runtime_root,
                        run_id=args.run_id,
                    )
                    row["attempt"] = attempt
                    attempts.append({
                        "attempt": attempt,
                        "returncode": row.get("returncode"),
                        "status": row.get("status"),
                        "elapsed_seconds": row.get("elapsed_seconds"),
                    })
                    if (
                        row.get("returncode") == 0
                        and row.get("status") == "captured_exact_unreviewed"
                    ):
                        break
                row["attempt_history"] = attempts
                return row
            finally:
                available.put(display)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_by_scenario = {
                executor.submit(assigned, scenario): scenario
                for scenario in args.scenarios
            }
            for future in as_completed(future_by_scenario):
                scenario = future_by_scenario[future]
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
                print(
                    f"scenario {scenario:02d}: {row['status']}",
                    flush=True,
                )
    finally:
        for process in xvfb_processes:
            stop_process(process)

    rows.sort(key=lambda row: int(row["scenario"]))
    passed = [
        row for row in rows
        if row.get("returncode") == 0
        and row.get("status") == "captured_exact_unreviewed"
    ]
    seed_unchanged = sha256(args.seed_gst) == seed["sha256"]
    return {
        "schema_version": 1,
        "status": (
            "pass"
            if len(passed) == len(rows) and seed_unchanged
            else "fail"
        ),
        "profile": args.profile,
        "rom": {
            "path": relative(args.rom),
            "sha256": sha256(args.rom),
            "md_checksum": matrix.md_checksum(args.rom),
        },
        "seed": seed,
        "seed_unchanged": seed_unchanged,
        "run_id": args.run_id,
        "workers": workers,
        "attempts_per_scenario": args.attempts,
        "display_base": args.display_base,
        "scenarios": args.scenarios,
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
    parser.add_argument("--reference-rom", type=Path, default=matrix.DEFAULT_REFERENCE_ROM)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument("--scenarios", type=parse_scenarios, default=parse_scenarios("1-31"))
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--attempts",
        type=int,
        default=2,
        help="isolated retry attempts for transient emulator startup failures",
    )
    parser.add_argument("--display-base", type=int, default=DEFAULT_DISPLAY_BASE)
    parser.add_argument("--xvfb", type=Path, default=DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--output-root", type=Path, default=matrix.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    args.rom = args.rom.resolve()
    args.reference_rom = args.reference_rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    args.xvfb = args.xvfb.resolve()
    args.xvfb_library_path = args.xvfb_library_path.resolve()

    if not 1 <= args.workers <= MAX_WORKERS:
        parser.error(f"--workers must be 1..{MAX_WORKERS}")
    if not 1 <= args.attempts <= 4:
        parser.error("--attempts must be 1..4")
    if not MIN_ISOLATED_DISPLAY_NUMBER <= args.display_base <= 999 - args.workers:
        parser.error(
            "--display-base must be at least 100 and leave room for every worker"
        )
    for label, path in (
        ("ROM", args.rom),
        ("reference ROM", args.reference_rom),
        ("seed GST", args.seed_gst),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if args.command == "run" and not args.xvfb.is_file():
        raise FileNotFoundError(f"Xvfb executable does not exist: {args.xvfb}")
    if args.command == "run" and not args.xvfb_library_path.is_dir():
        raise FileNotFoundError(
            f"Xvfb library directory does not exist: {args.xvfb_library_path}"
        )

    if args.command == "plan":
        result = {
            "schema_version": 1,
            "command": "plan",
            "profile": args.profile,
            "rom": str(args.rom),
            "workers": min(args.workers, len(args.scenarios)),
            "attempts": args.attempts,
            "displays": [
                f":{args.display_base + index}"
                for index in range(min(args.workers, len(args.scenarios)))
            ],
            "scenarios": args.scenarios,
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
    return 0 if result.get("status", "pass") != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
