#!/usr/bin/env python3
"""Verify one hard-mode scenario through its no-action first turn."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blastem_sequence as sequence_runner
from tools import verify_hard_mode_scenario_runtime as loader_verifier


DEFAULT_ROM = (
    ROOT
    / "roms/releases/Langrisser II (Korean Hard T1.0.0 B1.0.0).md"
)
DEFAULT_RESULTS = ROOT / "localization/hard_mode_first_turn_smoke.json"
DEFAULT_DOCUMENTATION = ROOT / "docs/hard_mode_first_turn_verification.md"
LOADER_SMOKE_RESULTS = ROOT / "localization/hard_mode_scenario_smoke.json"
DEEP_RESULTS = ROOT / "localization/hard_mode_runtime_verification.json"
RUNNER = ROOT / "tools/run_blastem_sequence.py"
KEY_SENDER = ROOT / "tools/send_blastem_keys.py"
CAPTURE = ROOT / "tools/capture_blastem_window.py"
RUNTIME_ROOT = ROOT / "captures/runtime"
CAPTURE_ROOT = ROOT / "captures/run"
GST_WORK_RAM_FILE_OFFSET = 0x2478
TURN_COUNTER_WORK_RAM_OFFSET = 0xA5F1
TURN_COUNTER_FILE_OFFSET = (
    GST_WORK_RAM_FILE_OFFSET + TURN_COUNTER_WORK_RAM_OFFSET
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def entry_evidence(
    scenario_number: int,
    *,
    loader_results_path: Path = LOADER_SMOKE_RESULTS,
    deep_results_path: Path = DEEP_RESULTS,
) -> dict:
    loader = load_json(loader_results_path)
    for row in loader.get("scenarios", []):
        if int(row["number"]) == scenario_number:
            return {
                "kind": "loader_smoke",
                "path": ROOT / row["gst"],
                "sha256": row["gst_sha256"],
            }
    deep = load_json(deep_results_path)
    for row in deep.get("scenarios", []):
        if (
            int(row["number"]) == scenario_number
            and row["status"] == "runtime_loader_verified"
        ):
            return {
                "kind": "deep_runtime",
                "path": ROOT / row["gst"],
                "sha256": row["gst_sha256"],
            }
    raise ValueError(
        f"Scenario {scenario_number} has no verified hard-mode entry GST"
    )


def validate_entry_evidence(
    scenario_number: int,
    evidence: dict,
) -> tuple[Path, str, int | None]:
    path = Path(evidence["path"])
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path)
    gst = path.read_bytes()
    if turn_counter(gst) != 1:
        raise ValueError(
            f"Scenario {scenario_number} entry GST is on turn "
            f"{turn_counter(gst)}, not turn 1"
        )
    if evidence["kind"] == "deep_runtime" and actual != evidence["sha256"]:
        raise ValueError(
            f"entry GST hash changed for {path}: "
            f"{actual} != {evidence['sha256']}"
        )
    player_group_count = None
    if evidence["kind"] == "loader_smoke":
        player_group_count = loader_verifier.matching_player_group_count(
            gst,
            scenario_number,
        )
    return path, actual, player_group_count


def runtime_quicksave(runtime_name: str, rom: Path) -> Path:
    return (
        RUNTIME_ROOT
        / runtime_name
        / ".local/share/blastem"
        / rom.stem
        / "quicksave.gst"
    )


def prepare_runtime(
    scenario_number: int,
    *,
    rom: Path,
    evidence: dict,
) -> tuple[str, Path, str, int | None]:
    runtime_name = f"hard-first-turn-s{scenario_number:02d}"
    runtime_home = RUNTIME_ROOT / runtime_name
    shutil.rmtree(runtime_home, ignore_errors=True)
    destination = runtime_quicksave(runtime_name, rom)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source, digest, player_group_count = validate_entry_evidence(
        scenario_number,
        evidence,
    )
    shutil.copy2(source, destination)
    return runtime_name, destination, digest, player_group_count


def run_command(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    allowed: set[int] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="", flush=True)
    accepted = {0} if allowed is None else allowed
    if completed.returncode not in accepted:
        raise RuntimeError(
            f"command exited {completed.returncode}: {' '.join(command)}\n"
            f"{completed.stdout}"
        )
    return completed


def run_detector(
    *,
    display: str,
    max_checks: int,
    delay: float,
) -> tuple[str, int]:
    command = [
        sys.executable,
        str(RUNNER),
        "detect-command",
        "--no-launch",
        "--send-event",
        "--virtual-display",
        display,
        "--open-map-command",
        "--max-confirmations",
        str(max_checks),
        "--confirmation-delay",
        str(delay),
    ]
    for attempt in range(4):
        completed = run_command(command, allowed={0, 1, 2})
        if completed.returncode != 1:
            break
        if (
            "dialogue disappeared before its text stabilized"
            not in completed.stdout
            or attempt == 3
        ):
            raise RuntimeError(
                "screen detector failed while the emulator was running"
            )
        print(
            "dialogue advanced automatically during stability check; "
            "resuming detection",
            flush=True,
        )
    match = re.search(r"detected after (\d+) confirmations", completed.stdout)
    if match is None:
        raise RuntimeError(
            "screen detector exited without a confirmation count"
        )
    endpoint = (
        "turn_command"
        if completed.returncode == 0
        else "game_over"
    )
    return endpoint, int(match.group(1))


def capture(path: Path, *, env: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            sys.executable,
            str(CAPTURE),
            str(path),
            "--xlib-only",
        ],
        env=env,
    )


def turn_counter(gst: bytes) -> int:
    if len(gst) <= TURN_COUNTER_FILE_OFFSET:
        raise ValueError("GST is too short to contain the turn counter")
    return gst[TURN_COUNTER_FILE_OFFSET]


def classify_endpoint(detector_endpoint: str, counter: int) -> str:
    if detector_endpoint == "turn_command":
        if counter != 2:
            raise ValueError(
                f"command menu returned with turn counter {counter}, not 2"
            )
        return "turn_2_command"
    if detector_endpoint == "game_over":
        if counter not in (1, 2):
            raise ValueError(
                f"first-turn GAME OVER has unexpected turn counter {counter}"
            )
        return f"game_over_turn_{counter}"
    raise ValueError(f"unknown detector endpoint: {detector_endpoint}")


def load_results(path: Path, rom: Path) -> dict:
    if path.exists():
        results = load_json(path)
    else:
        results = {
            "schema_version": 1,
            "status": "in_progress",
            "hard_rom": {},
            "scenarios": [],
        }
    results["hard_rom"] = {
        "path": relative(rom),
        "sha256": sha256(rom),
    }
    return results


def update_coverage(results: dict) -> None:
    verified = sorted(
        int(row["number"])
        for row in results.get("scenarios", [])
        if row["status"] == "first_turn_runtime_verified"
    )
    missing = sorted(set(range(1, 32)) - set(verified))
    results["coverage"] = {
        "scenario_count": 31,
        "verified_scenarios": verified,
        "missing_scenarios": missing,
    }
    results["status"] = (
        "all_scenarios_first_turn_verified"
        if not missing
        else "in_progress"
    )


def save_result(path: Path, results: dict, result: dict) -> None:
    by_number = {
        int(row["number"]): row for row in results.get("scenarios", [])
    }
    by_number[int(result["number"])] = result
    results["scenarios"] = [by_number[number] for number in sorted(by_number)]
    update_coverage(results)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def render_document(results: dict) -> str:
    coverage = results.get("coverage", {})
    verified = coverage.get("verified_scenarios", [])
    missing = coverage.get("missing_scenarios", list(range(1, 32)))
    lines = [
        "# Hard Mode First-Turn Verification",
        "",
        "This document records no-action first-turn playback on the separate "
        "Standard Hard ROM. It is generated from "
        "`localization/hard_mode_first_turn_smoke.json`.",
        "",
        "## Method",
        "",
        "- Revalidate the source GST as Turn 1 and confirm every planned hard "
        "enemy runtime group before input.",
        "- Copy the source GST into an isolated `hard-first-turn-sXX` runtime; "
        "never advance the loader evidence in place.",
        "- Advance completed dialogue one page at a time, choose the stock "
        "`턴 종료` command, and wait through event, AI, movement, and battle "
        "animation frames.",
        "- Accept only a real Turn 2 command menu or the scenario's normal "
        "GAME OVER path. The Turn 2 endpoint is also checked against work-RAM "
        "counter `$FFFFA5F1`.",
        "- Store endpoint screenshots, GST paths, and SHA-256 values in the "
        "JSON manifest. Runtime captures are local evidence and are not "
        "release ROM inputs.",
        "",
        "BlastEm rewrites its mutable runtime `quicksave.gst` when a process "
        "closes. Loader-smoke entry files are therefore revalidated from RAM "
        "content and the live digest is recorded instead of trusting an older "
        "manifest digest alone. Retained deep-evidence GST files remain "
        "strictly hash-locked.",
        "",
        "## Coverage",
        "",
        f"- Status: `{results.get('status', 'in_progress')}`",
        f"- Verified: {len(verified)}/31",
        "- Verified scenarios: "
        + (", ".join(str(number) for number in verified) or "none"),
        "- Missing scenarios: "
        + (", ".join(str(number) for number in missing) or "none"),
        "",
        "## Results",
        "",
        "| Scenario | Endpoint | Opening confirmations | Phase confirmations | "
        "Elapsed |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in results.get("scenarios", []):
        lines.append(
            f"| {row['number']} | `{row['endpoint']}` | "
            f"{row['opening_confirmations']} | "
            f"{row['phase_dialogue_confirmations']} | "
            f"{row['elapsed_seconds']:.1f}s |"
        )
    lines.extend(
        [
            "",
            "`turn_2_command` proves that the stock first-turn event and "
            "faction phases returned to a playable command state. "
            "`game_over_turn_1` is accepted only where the no-action route "
            "naturally defeats the party; it does not claim a successful "
            "scenario clear.",
            "",
        ]
    )
    return "\n".join(lines)


def save_document(path: Path, results: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(render_document(results), encoding="utf-8")
    temporary.replace(path)


def verify_scenario(
    scenario_number: int,
    *,
    rom: Path,
    display: str,
    opening_checks: int,
    phase_checks: int,
    delay: float,
    initial_delay: float,
    keep_running: bool,
) -> dict:
    evidence = entry_evidence(scenario_number)
    (
        runtime_name,
        quicksave,
        entry_digest,
        player_group_count,
    ) = prepare_runtime(
        scenario_number,
        rom=rom,
        evidence=evidence,
    )
    env = os.environ.copy()
    env["DISPLAY"] = display
    started = time.monotonic()
    try:
        run_command([
            sys.executable,
            str(RUNNER),
            "launch-only",
            "--rom",
            str(rom),
            "--runtime-name",
            runtime_name,
            "--reuse-runtime-state",
            "--virtual-display",
            display,
            "--replace-existing",
            "--send-event",
            "--initial-delay",
            str(initial_delay),
        ])
        run_command(
            [
                sys.executable,
                str(KEY_SENDER),
                "--send-event",
                "load:2.0",
            ],
            env=env,
        )
        opening_endpoint, opening_confirmations = run_detector(
            display=display,
            max_checks=opening_checks,
            delay=delay,
        )
        if opening_endpoint != "turn_command":
            raise RuntimeError(
                f"Scenario {scenario_number} ended before player turn"
            )

        opening_capture = (
            CAPTURE_ROOT
            / f"hard_first_turn_s{scenario_number:02d}_command.png"
        )
        capture(opening_capture, env=env)
        run_command(
            [
                sys.executable,
                str(KEY_SENDER),
                "--send-event",
                "b:0.8",
                "start:1.0",
                "down:0.5",
                "down:0.5",
                "down:0.5",
                "down:0.8",
                "c:3.0",
            ],
            env=env,
        )
        detector_endpoint, phase_confirmations = run_detector(
            display=display,
            max_checks=phase_checks,
            delay=delay,
        )
        endpoint_capture = (
            CAPTURE_ROOT
            / f"hard_first_turn_s{scenario_number:02d}_endpoint.png"
        )
        capture(endpoint_capture, env=env)
        run_command(
            [
                sys.executable,
                str(KEY_SENDER),
                "--send-event",
                "save:1.0",
            ],
            env=env,
        )
        gst_bytes = quicksave.read_bytes()
        counter = turn_counter(gst_bytes)
        endpoint = classify_endpoint(detector_endpoint, counter)
        return {
            "number": scenario_number,
            "status": "first_turn_runtime_verified",
            "endpoint": endpoint,
            "turn_counter": counter,
            "opening_confirmations": opening_confirmations,
            "phase_dialogue_confirmations": phase_confirmations,
            "elapsed_seconds": round(time.monotonic() - started, 1),
            "entry_evidence": {
                "kind": evidence["kind"],
                "gst": relative(Path(evidence["path"])),
                "gst_sha256": entry_digest,
                "manifest_gst_sha256": evidence["sha256"],
                "player_group_count": player_group_count,
            },
            "opening_capture": relative(opening_capture),
            "opening_capture_sha256": sha256(opening_capture),
            "endpoint_capture": relative(endpoint_capture),
            "endpoint_capture_sha256": sha256(endpoint_capture),
            "endpoint_gst": relative(quicksave),
            "endpoint_gst_sha256": hashlib.sha256(gst_bytes).hexdigest(),
        }
    finally:
        if not keep_running:
            pids = sequence_runner.running_blastem_pids(display=display)
            if pids:
                sequence_runner.terminate_blastem_processes(
                    display=display
                )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=int, required=True)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--virtual-display", default=":114")
    parser.add_argument("--opening-checks", type=int, default=240)
    parser.add_argument("--phase-checks", type=int, default=700)
    parser.add_argument("--confirmation-delay", type=float, default=0.3)
    parser.add_argument("--initial-delay", type=float, default=3.0)
    parser.add_argument("--keep-running", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.scenario <= 31:
        raise ValueError("--scenario must be 1..31")
    if args.confirmation_delay < 0:
        raise ValueError("--confirmation-delay must be non-negative")
    rom = args.rom.resolve()
    results_path = args.results.resolve()
    results = load_results(results_path, rom)
    result = verify_scenario(
        args.scenario,
        rom=rom,
        display=args.virtual_display,
        opening_checks=args.opening_checks,
        phase_checks=args.phase_checks,
        delay=args.confirmation_delay,
        initial_delay=args.initial_delay,
        keep_running=args.keep_running,
    )
    save_result(results_path, results, result)
    if results_path == DEFAULT_RESULTS.resolve():
        save_document(DEFAULT_DOCUMENTATION, results)
    print(
        f"Scenario {args.scenario}: {result['endpoint']} after "
        f"{result['phase_dialogue_confirmations']} phase confirmations",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
