#!/usr/bin/env python3
"""Run clean entry and no-action first-turn playback in parallel Xvfb workers."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import queue
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blastem_sequence as sequence  # noqa: E402
from tools import run_preparation_surface_matrix as matrix  # noqa: E402
from tools import run_preparation_surface_parallel as parallel  # noqa: E402
from tools import run_sequential_campaign_revalidation as campaign  # noqa: E402


DEFAULT_OUTPUT_ROOT = ROOT / "tmp/first_turn_surface_parallel"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_report_path(value: object) -> Path:
    path = Path(str(value))
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def load_campaign_scenario_seeds(
    path: Path,
    *,
    profile: str,
    run_id: str,
    rom_sha256: str,
    fresh_seed: Path,
    fresh_seed_sha256: str,
    rom_path: Path | None = None,
) -> dict[int, dict[str, object]]:
    """Read the verified route inputs that represent natural progression."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") != "pass" or data.get("run_id") != run_id:
        raise ValueError("campaign summary status/run_id does not match")
    if (
        data.get("profiles") != list(campaign.PROFILES)
        or data.get("manual_intervention") is not False
        or data.get("automation_only") is not True
        or data.get("continuous_save_chain") is not True
        or data.get("release_roms_unchanged") is not True
    ):
        raise ValueError("campaign summary identity/policy does not match")
    if data.get("route_order") != list(campaign.FULL_ROUTE_ORDER):
        raise ValueError("campaign summary route order differs")
    for key in ("release_roms", "release_roms_after"):
        snapshots = data.get(key)
        snapshot = snapshots.get(profile) if isinstance(snapshots, dict) else None
        if (
            not isinstance(snapshot, dict)
            or snapshot.get("sha256") != rom_sha256
            or (
                rom_path is not None
                and resolve_report_path(snapshot.get("path"))
                != rom_path.resolve()
            )
        ):
            raise ValueError(f"campaign {key}/{profile} release differs")
    reports = data.get("results")
    matches = [
        report
        for report in reports
        if isinstance(report, dict) and report.get("profile") == profile
    ] if isinstance(reports, list) else []
    if len(matches) != 1:
        raise ValueError(f"campaign summary needs one {profile} report")
    report = matches[0]
    release = report.get("release_rom")
    if (
        report.get("status") != "pass"
        or report.get("run_id") != run_id
        or not isinstance(release, dict)
        or release.get("sha256") != rom_sha256
        or (
            rom_path is not None
            and resolve_report_path(release.get("path")) != rom_path.resolve()
        )
        or report.get("manual_intervention") is not False
        or report.get("passed_steps") != len(campaign.FULL_ROUTE_ORDER)
        or report.get("total_steps") != len(campaign.FULL_ROUTE_ORDER)
    ):
        raise ValueError(f"campaign {profile} report identity differs")
    rows = report.get("results")
    if not isinstance(rows, list) or len(rows) != len(campaign.FULL_ROUTE_ORDER):
        raise ValueError(f"campaign {profile} route rows are incomplete")
    result: dict[int, dict[str, object]] = {}
    for route_index, (scenario, row) in enumerate(
        zip(campaign.FULL_ROUTE_ORDER, rows, strict=True)
    ):
        if (
            not isinstance(row, dict)
            or row.get("scenario") != scenario
            or row.get("status") != "pass"
            or row.get("returncode") != 0
            or row.get("route_index") != route_index
            or row.get("run_id") != run_id
            or row.get("manual_intervention") is not False
        ):
            raise ValueError(
                f"campaign {profile} route row {route_index} differs"
            )
        state = row.get("input_state")
        # Secret scenarios are selected by the probe ROM, not by a distinct
        # serialized scenario number.  Their input saves retain the stock
        # continuation number (X1=13, X2=20, X3=23, X4=27), exactly as the
        # continuous campaign runner already verifies.  Main-route steps use
        # the same rule, which also means Scenario 13 legitimately follows an
        # X1 output whose serialized number is still 13.
        expected_serialized_scenario = campaign.expected_input_scenario(
            route_index
        )
        if (
            not isinstance(state, dict)
            or state.get("scenario") != expected_serialized_scenario
        ):
            raise ValueError(
                f"campaign {profile} S{scenario} input state differs "
                f"(expected serialized Scenario "
                f"{expected_serialized_scenario})"
            )
        state_path = resolve_report_path(state.get("path"))
        state_sha256 = state.get("gst_sha256")
        if (
            not state_path.is_file()
            or not isinstance(state_sha256, str)
            or sha256(state_path) != state_sha256
        ):
            raise ValueError(
                f"campaign {profile} S{scenario} input GST/hash differs"
            )
        result[scenario] = {
            "path": parallel.relative(state_path),
            "sha256": state_sha256,
            "record_sha256": state.get("record_sha256"),
            "route_index": route_index,
            "serialized_scenario": expected_serialized_scenario,
            "source": (
                "fresh_s1_seed"
                if scenario == 1
                else "continuous_campaign_input"
            ),
        }
    scenario_one = result[1]
    if (
        resolve_report_path(scenario_one["path"]) != fresh_seed.resolve()
        or scenario_one["sha256"] != fresh_seed_sha256
    ):
        raise ValueError(
            f"campaign {profile} S1 input is not the exact fresh seed"
        )
    if set(result) != set(range(1, 32)):
        raise ValueError(f"campaign {profile} scenario input set is incomplete")
    return result


def scenario_row(
    data: dict[str, object],
    scenario: int,
    *,
    label: str,
) -> dict[str, object]:
    rows = data.get("scenarios")
    matches = [
        row
        for row in rows if isinstance(row, dict) and int(row["number"]) == scenario
    ] if isinstance(rows, list) else []
    if len(matches) != 1:
        raise RuntimeError(
            f"{label} must contain exactly one Scenario {scenario} row"
        )
    return matches[0]


def verify_loader_uses_explicit_seed(
    *,
    scenario: int,
    loader_data: dict[str, object],
    seed_gst: Path,
    seed_sha256: str,
    rom_sha256: str,
) -> dict[str, object]:
    """Reject the loader result before first-turn playback can consume it."""
    loader_row = scenario_row(loader_data, scenario, label="loader results")
    loader_rom = loader_data.get("hard_rom")
    loader_rom_sha256 = (
        loader_rom.get("sha256") if isinstance(loader_rom, dict) else None
    )
    loader_gst_path = resolve_report_path(loader_row.get("gst"))
    checks = {
        "explicit_seed_path_match": (
            resolve_report_path(loader_row.get("seed")) == seed_gst.resolve()
        ),
        "explicit_seed_sha256_match": (
            loader_row.get("seed_sha256") == seed_sha256
        ),
        "loader_rom_sha256_match": loader_rom_sha256 == rom_sha256,
        "loader_entry_gst_hash_match": (
            loader_gst_path.is_file()
            and sha256(loader_gst_path) == loader_row.get("gst_sha256")
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(
            "loader explicit-seed preflight failed: " + ", ".join(failed)
        )
    return loader_row


def verify_loader_entry_source_lineage(
    *,
    scenario: int,
    loader_data: dict[str, object],
    first_turn_data: dict[str, object],
    loader_results: Path,
    first_turn_results: Path,
    seed_gst: Path,
    seed_sha256: str,
    rom_sha256: str,
) -> dict[str, object]:
    """Bind one loader and first-turn row to its explicit campaign input."""
    loader_row = verify_loader_uses_explicit_seed(
        scenario=scenario,
        loader_data=loader_data,
        seed_gst=seed_gst,
        seed_sha256=seed_sha256,
        rom_sha256=rom_sha256,
    )
    first_turn_row = scenario_row(
        first_turn_data,
        scenario,
        label="first-turn results",
    )
    entry = first_turn_row.get("entry_evidence")
    if not isinstance(entry, dict):
        raise RuntimeError("first-turn entry_evidence is missing")

    loader_rom = loader_data.get("hard_rom")
    loader_rom_sha256 = (
        loader_rom.get("sha256") if isinstance(loader_rom, dict) else None
    )
    loader_seed = {
        "path": loader_row.get("seed"),
        "sha256": loader_row.get("seed_sha256"),
    }
    loader_gst = {
        "path": loader_row.get("gst"),
        "sha256": loader_row.get("gst_sha256"),
    }
    checks = {
        "explicit_seed_path_match": (
            resolve_report_path(loader_seed["path"]) == seed_gst.resolve()
        ),
        "explicit_seed_sha256_match": loader_seed["sha256"] == seed_sha256,
        "loader_rom_sha256_match": loader_rom_sha256 == rom_sha256,
        "first_turn_entry_kind": entry.get("kind") == "loader_smoke",
        "first_turn_loader_manifest_match": (
            resolve_report_path(entry.get("manifest"))
            == loader_results.resolve()
        ),
        "first_turn_entry_gst_path_match": (
            resolve_report_path(entry.get("gst"))
            == resolve_report_path(loader_gst["path"])
        ),
        "first_turn_entry_gst_sha256_match": (
            entry.get("gst_sha256") == loader_gst["sha256"]
            and entry.get("manifest_gst_sha256") == loader_gst["sha256"]
        ),
        "first_turn_manifest_rom_sha256_match": (
            entry.get("manifest_rom_sha256") == rom_sha256
        ),
    }
    loader_gst_path = resolve_report_path(loader_gst["path"])
    checks["loader_entry_gst_hash_match"] = (
        loader_gst_path.is_file()
        and sha256(loader_gst_path) == loader_gst["sha256"]
    )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(
            "loader entry-source lineage failed: " + ", ".join(failed)
        )
    return {
        "status": "pass",
        "seed": loader_seed,
        "loader_manifest": parallel.relative(loader_results),
        "loader_results_sha256": sha256(loader_results),
        "loader_manifest_rom_sha256": loader_rom_sha256,
        "loader_entry_gst": loader_gst,
        "first_turn_manifest": parallel.relative(first_turn_results),
        "first_turn_results_sha256": sha256(first_turn_results),
        "first_turn_entry": {
            "kind": entry.get("kind"),
            "manifest": entry.get("manifest"),
            "manifest_rom_sha256": entry.get("manifest_rom_sha256"),
            "gst": entry.get("gst"),
            "gst_sha256": entry.get("gst_sha256"),
            "manifest_gst_sha256": entry.get("manifest_gst_sha256"),
        },
        "checks": checks,
        "all_checks_pass": True,
    }


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
    seed_gst: Path,
    seed_sha256: str,
    seed_origin: dict[str, object],
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
                    "--entry-source-gst",
                    str(seed_gst),
                ]
        if profile != "hard":
            loader_command.append("--skip-hard-runtime-check")
        outputs.append(run(loader_command))
        loader_data = json.loads(loader_results.read_text(encoding="utf-8"))
        verify_loader_uses_explicit_seed(
            scenario=scenario,
            loader_data=loader_data,
            seed_gst=seed_gst,
            seed_sha256=seed_sha256,
            rom_sha256=sha256(rom),
        )
        first_turn_command = [
                    sys.executable,
                    str(ROOT / "tools/verify_hard_mode_first_turn.py"),
                    "--scenario",
                    str(scenario),
                    "--profile",
                    profile,
                    "--rom",
                    str(rom),
                    "--results",
                    str(first_turn_results),
                    "--loader-results",
                    str(loader_results),
                    "--require-loader-entry",
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
        lineage = verify_loader_entry_source_lineage(
            scenario=scenario,
            loader_data=loader_data,
            first_turn_data=result,
            loader_results=loader_results,
            first_turn_results=first_turn_results,
            seed_gst=seed_gst,
            seed_sha256=seed_sha256,
            rom_sha256=sha256(rom),
        )
        lineage["source"] = seed_origin
        return {
            "scenario": scenario,
            "display": display,
            "status": "pass",
            "endpoint": row["endpoint"],
            "turn_counter": row["turn_counter"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "loader_results": parallel.relative(loader_results),
            "first_turn_results": parallel.relative(first_turn_results),
            "entry_source_lineage": lineage,
            "loader_results_sha256": lineage["loader_results_sha256"],
            "first_turn_results_sha256": lineage[
                "first_turn_results_sha256"
            ],
            "output": "".join(outputs),
        }
    except Exception as exc:
        return {
            "scenario": scenario,
            "display": display,
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
        "--seed-gst",
        type=Path,
        required=True,
        help=(
            "explicit fresh Scenario 1 preparation GST anchoring the route; "
            "later loaders use its continuous-campaign descendants"
        ),
    )
    parser.add_argument(
        "--campaign-summary",
        type=Path,
        required=True,
        help=(
            "completed continuous-campaign summary whose profile/scenario "
            "input GSTs feed the first-turn loaders"
        ),
    )
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
    parser.add_argument(
        "--run-id",
        type=matrix.validate_run_id,
        required=True,
    )
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
    if not args.seed_gst.is_file():
        raise FileNotFoundError(args.seed_gst)
    if not args.campaign_summary.is_file():
        raise FileNotFoundError(args.campaign_summary)
    if args.output_root.exists():
        raise FileExistsError(args.output_root)
    seed_gst = args.seed_gst.resolve()
    seed_before = {
        "path": parallel.relative(seed_gst),
        "sha256": sha256(seed_gst),
    }
    campaign_summary = args.campaign_summary.resolve()
    campaign_before = {
        "path": parallel.relative(campaign_summary),
        "sha256": sha256(campaign_summary),
    }
    scenario_seeds = load_campaign_scenario_seeds(
        campaign_summary,
        profile=args.profile,
        run_id=args.run_id,
        rom_sha256=sha256(args.rom),
        rom_path=args.rom,
        fresh_seed=seed_gst,
        fresh_seed_sha256=str(seed_before["sha256"]),
    )
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
                scenario_seed = scenario_seeds[scenario]
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
                    seed_gst=resolve_report_path(scenario_seed["path"]),
                    seed_sha256=str(scenario_seed["sha256"]),
                    seed_origin=scenario_seed,
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
    seed_after = {
        "path": parallel.relative(seed_gst),
        "sha256": sha256(seed_gst),
    }
    seed_unchanged = seed_after == seed_before
    campaign_after = {
        "path": parallel.relative(campaign_summary),
        "sha256": sha256(campaign_summary),
    }
    campaign_unchanged = campaign_after == campaign_before
    scenario_seeds_after = {
        str(scenario): {
            **lineage,
            "sha256": sha256(resolve_report_path(lineage["path"])),
        }
        for scenario, lineage in scenario_seeds.items()
    }
    scenario_seeds_before = {
        str(scenario): lineage
        for scenario, lineage in scenario_seeds.items()
    }
    scenario_seeds_unchanged = scenario_seeds_after == scenario_seeds_before
    passed = (
        all(row["status"] == "pass" for row in rows)
        and seed_unchanged
        and campaign_unchanged
        and scenario_seeds_unchanged
    )
    summary = {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "rom": {
            "path": parallel.relative(args.rom),
            "sha256": parallel.sha256(args.rom),
            "md_checksum": matrix.md_checksum(args.rom),
        },
        "profile": args.profile,
        "run_id": args.run_id,
        "seed": seed_before,
        "seed_before": seed_before,
        "seed_after": seed_after,
        "seed_unchanged": seed_unchanged,
        "campaign": campaign_before,
        "campaign_before": campaign_before,
        "campaign_after": campaign_after,
        "campaign_unchanged": campaign_unchanged,
        "scenario_seeds": scenario_seeds_before,
        "scenario_seeds_after": scenario_seeds_after,
        "scenario_seeds_unchanged": scenario_seeds_unchanged,
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
