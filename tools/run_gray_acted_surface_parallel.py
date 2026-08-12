#!/usr/bin/env python3
"""Run gray acted-sprite matrices in isolated parallel BlastEm workers."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import queue
import signal
import shutil
import socket
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_gray_acted_surface_matrix as gray  # noqa: E402
from tools import run_first_turn_surface_parallel as first_turn  # noqa: E402
from tools import run_preparation_surface_matrix as matrix  # noqa: E402
from tools import run_preparation_surface_parallel as parallel  # noqa: E402


def require_displays_available(displays: list[str]) -> None:
    occupied = []
    for display in displays:
        port = 6000 + parallel.display_number(display)
        try:
            connection = socket.create_connection(
                ("127.0.0.1", port),
                timeout=0.15,
            )
        except OSError:
            connection = None
        if connection is not None:
            connection.close()
            occupied.append(display)
            continue
        if gray.sequence.running_blastem_pids(display=display):
            occupied.append(display)
    if occupied:
        raise RuntimeError(
            "refusing occupied Xvfb display(s): " + ", ".join(occupied)
        )


def scenario_seed(
    args: argparse.Namespace,
    scenario: int,
) -> tuple[dict[str, object], Path, bool]:
    scenario_seeds = getattr(args, "scenario_seeds", None)
    seed_origin = (
        scenario_seeds[scenario]
        if isinstance(scenario_seeds, dict)
        else {
            "path": relative(args.seed_gst),
            "sha256": gray.sha256(args.seed_gst),
            "record_sha256": None,
            "route_index": None,
            "source": "shared_diagnostic_seed",
        }
    )
    seed_path = first_turn.resolve_report_path(seed_origin["path"])
    return seed_origin, seed_path, isinstance(scenario_seeds, dict)


def worker_command(
    args: argparse.Namespace,
    scenario: int,
    display: str,
) -> tuple[list[str], dict[str, object], Path, bool]:
    seed_origin, seed_path, campaign_bound = scenario_seed(args, scenario)
    command = [
        sys.executable,
        str(ROOT / "tools/run_gray_acted_surface_matrix.py"),
        "--profile", args.profile,
        "--scenario", str(scenario),
        "--rom", str(args.rom),
        "--seed-gst", str(seed_path),
        "--display", display,
        "--output-root", str(args.output_root),
        "--runtime-root", str(args.runtime_root),
        "--run-id", args.run_id,
        "--directions", ",".join(args.directions),
        "--commander-id", str(args.commander_id),
        "--commander-class", f"0x{args.commander_class:02X}",
        "--commander-level", str(args.commander_level),
        "--commander-experience", str(args.commander_experience),
    ]
    if campaign_bound:
        command.append("--preserve-seed-roster")
    return command, seed_origin, seed_path, campaign_bound


def run_one(args: argparse.Namespace, scenario: int, display: str) -> dict[str, object]:
    started = time.monotonic()
    command, seed_origin, seed_path, campaign_bound = worker_command(
        args,
        scenario,
        display,
    )
    output = (
        args.output_root / args.profile / f"s{scenario:02d}" / args.run_id
    )
    log_path = output / "parallel-worker.log"
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        stdout, _ = process.communicate(timeout=args.worker_timeout)
        completed = subprocess.CompletedProcess(command, process.returncode, stdout)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        output_text = exc.stdout if isinstance(exc.stdout, str) else ""
        output.mkdir(parents=True, exist_ok=True)
        log_path.write_text(output_text, encoding="utf-8")
        return {
            "scenario": scenario,
            "display": display,
            "returncode": 124,
            "status": "worker_timeout",
            "directions_tried": None,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "output": relative(output),
            "log": relative(log_path),
            "timeout_seconds": args.worker_timeout,
        }
    output.mkdir(parents=True, exist_ok=True)
    log_path.write_text(completed.stdout, encoding="utf-8")
    evidence_path = output / "evidence.json"
    evidence = (
        json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence_path.is_file()
        else None
    )
    expected_seed_policy = (
        "preserve_exact_campaign_roster"
        if campaign_bound
        else "manual_diagnostic_commander_override"
    )
    if evidence is not None:
        evidence_seed = evidence.get("seed")
        evidence_valid = (
            evidence.get("seed_policy") == expected_seed_policy
            and evidence.get("seed_unchanged") is True
            and isinstance(evidence_seed, dict)
            and first_turn.resolve_report_path(evidence_seed.get("path"))
            == seed_path.resolve()
            and evidence_seed.get("sha256") == seed_origin["sha256"]
        )
        if not evidence_valid:
            completed = subprocess.CompletedProcess(
                command,
                1,
                completed.stdout + "\nseed lineage/policy mismatch\n",
            )
    return {
        "scenario": scenario,
        "display": display,
        "returncode": completed.returncode,
        "status": evidence.get("status") if evidence else "failed_attempt",
        "directions_tried": evidence.get("directions_tried") if evidence else None,
        "selection_policy": (
            evidence.get("selection_policy") if evidence else None
        ),
        "seed_policy": evidence.get("seed_policy") if evidence else None,
        "seed_source": seed_origin,
        "fixed_record_runtime_coverage": (
            evidence.get("accepted_attempt", {}).get(
                "fixed_record_runtime_coverage"
            )
            if evidence and isinstance(evidence.get("accepted_attempt"), dict)
            else None
        ),
        "player_runtime_coverage": (
            evidence.get("accepted_attempt", {}).get("player_runtime_coverage")
            if evidence and isinstance(evidence.get("accepted_attempt"), dict)
            else None
        ),
        "selected_commander": (
            evidence.get("selected_commander") if evidence else None
        ),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "output": relative(output),
        "log": relative(log_path),
    }


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def verify_summary_contract(
    summary: dict[str, object],
    *,
    expected_profile: str,
    expected_run_id: str,
    expected_rom_sha256: str,
    require_campaign_bound: bool = True,
) -> dict[str, object]:
    """Fail closed on campaign lineage, structural coverage, and UI scope."""

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)

    require(summary.get("status") == "pass", "gray summary did not pass")
    require(summary.get("profile") == expected_profile, "gray profile changed")
    require(summary.get("run_id") == expected_run_id, "gray run_id changed")
    rom = summary.get("rom")
    require(
        isinstance(rom, dict) and rom.get("sha256") == expected_rom_sha256,
        "gray release ROM identity changed",
    )
    campaign_bound = summary.get("campaign_bound") is True
    require(
        campaign_bound or not require_campaign_bound,
        "gray summary is not bound to exact campaign inputs",
    )
    if campaign_bound:
        require(
            summary.get("seed_policy") == "exact_continuous_campaign_inputs",
            "gray campaign seed policy changed",
        )
        require(summary.get("campaign_unchanged") is True, "campaign summary changed")
        require(
            summary.get("scenario_seeds_unchanged") is True,
            "campaign scenario inputs changed",
        )
        campaign = summary.get("campaign")
        require(isinstance(campaign, dict), "campaign lineage is missing")
        campaign_path = first_turn.resolve_report_path(campaign.get("path"))
        require(
            campaign_path.is_file()
            and gray.sha256(campaign_path) == campaign.get("sha256"),
            "campaign lineage file/hash changed",
        )

    expected_ui_claims = {
        "selected_allied_real_move_and_gray_sprite": True,
        "all_fixed_and_event_record_identity_fields": True,
        "every_side_bottom_status_opened": False,
        "every_side_detail_popup_opened": False,
        "every_side_combat_animation_opened": False,
    }
    coverage = summary.get("source_runtime_coverage")
    require(
        isinstance(coverage, dict)
        and coverage.get("status") == "pass"
        and coverage.get("ui_surface_claims") == expected_ui_claims,
        "gray source/runtime coverage contract changed",
    )
    require(
        coverage.get("all_deployed_allied_runtime_identities_asserted") is True,
        "gray deployed-allied identity coverage changed",
    )
    scenarios = summary.get("scenarios")
    rows = summary.get("results")
    require(
        isinstance(scenarios, list)
        and isinstance(rows, list)
        and len(rows) == len(scenarios)
        and all(isinstance(row, dict) for row in rows)
        and [row.get("scenario") for row in rows] == scenarios,
        "gray scenario rows are incomplete or reordered",
    )
    require(
        coverage.get("scenario_rows_checked") == len(scenarios)
        and coverage.get("selected_allied_real_moves_checked") == len(scenarios),
        "gray aggregate scenario coverage count changed",
    )
    scenario_seeds = summary.get("scenario_seeds")
    if campaign_bound:
        require(isinstance(scenario_seeds, dict), "campaign scenario lineage is missing")

    selected_identities = set()
    fixed_records_checked = 0
    player_records_checked = 0
    for row in rows:
        scenario = int(row["scenario"])
        require(
            row.get("status") == "pass"
            and row.get("returncode") == 0
            and row.get("selection_policy") == gray.SELECTION_POLICY,
            f"gray Scenario {scenario} runtime result changed",
        )
        selected = row.get("selected_commander")
        require(isinstance(selected, dict), f"gray Scenario {scenario} selection is missing")
        selected_identities.add(
            (int(selected["commander_id"]), int(selected["class_id"]))
        )
        fixed = row.get("fixed_record_runtime_coverage")
        require(
            isinstance(fixed, dict)
            and fixed.get("status") == "pass"
            and fixed.get("runtime_structural_identity_asserted") is True
            and fixed.get("ui_surface_claims") == expected_ui_claims
            and fixed.get("reference_rom_sha256") == gray.REFERENCE_ROM_SHA256,
            f"gray Scenario {scenario} fixed/event coverage changed",
        )
        fixed_records_checked += int(fixed["runtime_records_checked"])
        players = row.get("player_runtime_coverage")
        require(
            isinstance(players, dict)
            and players.get("status") == "pass"
            and players.get("all_player_runtime_identities_asserted") is True,
            f"gray Scenario {scenario} deployed-allied coverage changed",
        )
        player_records_checked += int(players["player_runtime_groups_checked"])
        if campaign_bound:
            expected_seed = scenario_seeds.get(str(scenario))
            require(
                isinstance(expected_seed, dict)
                and row.get("seed_policy") == "preserve_exact_campaign_roster"
                and row.get("seed_source") == expected_seed,
                f"gray Scenario {scenario} campaign seed lineage changed",
            )
            seed_path = first_turn.resolve_report_path(expected_seed.get("path"))
            require(
                seed_path.is_file()
                and gray.sha256(seed_path) == expected_seed.get("sha256"),
                f"gray Scenario {scenario} campaign input file/hash changed",
            )
    require(
        fixed_records_checked
        == coverage.get("fixed_and_event_runtime_records_checked"),
        "gray aggregate fixed/event record count changed",
    )
    require(
        player_records_checked
        == coverage.get("deployed_allied_runtime_records_checked"),
        "gray aggregate deployed-allied record count changed",
    )
    return {
        "status": "pass",
        "profile": expected_profile,
        "scenarios_checked": len(scenarios),
        "fixed_and_event_runtime_records_checked": fixed_records_checked,
        "deployed_allied_runtime_records_checked": player_records_checked,
        "selected_commander_class_identities": [
            {"commander_id": commander_id, "class_id": class_id}
            for commander_id, class_id in sorted(selected_identities)
        ],
        "ui_surface_claims": expected_ui_claims,
        "scope_note": coverage.get("scope_note"),
    }


def run_parallel(args: argparse.Namespace) -> dict[str, object]:
    seed = {
        "path": relative(args.seed_gst),
        "sha256": gray.sha256(args.seed_gst),
    }
    scenario_seeds = getattr(args, "scenario_seeds", None)
    campaign_summary = getattr(args, "campaign_summary", None)
    campaign_bound = isinstance(scenario_seeds, dict)
    campaign_before = (
        {
            "path": relative(campaign_summary),
            "sha256": gray.sha256(campaign_summary),
        }
        if campaign_bound and isinstance(campaign_summary, Path)
        else None
    )
    scenario_seeds_before = (
        {str(scenario): dict(lineage) for scenario, lineage in scenario_seeds.items()}
        if campaign_bound
        else None
    )
    workers = min(args.workers, len(args.scenarios))
    displays = [f":{args.display_base + index}" for index in range(workers)]
    require_displays_available(displays)
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
                    row = run_one(args, scenario, display)
                    row["attempt"] = attempt
                    attempts.append({
                        "attempt": attempt,
                        "returncode": row.get("returncode"),
                        "status": row.get("status"),
                        "elapsed_seconds": row.get("elapsed_seconds"),
                    })
                    if (
                        row.get("returncode") == 0
                        and row.get("status") == "pass"
                    ):
                        break
                row["attempt_history"] = attempts
                return row
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
    seed_unchanged = gray.sha256(args.seed_gst) == seed["sha256"]
    campaign_after = (
        {
            "path": relative(campaign_summary),
            "sha256": gray.sha256(campaign_summary),
        }
        if campaign_bound and isinstance(campaign_summary, Path)
        else None
    )
    campaign_unchanged = (
        campaign_after == campaign_before if campaign_bound else None
    )
    scenario_seeds_after = (
        {
            str(scenario): {
                **lineage,
                "sha256": gray.sha256(
                    first_turn.resolve_report_path(lineage["path"])
                ),
            }
            for scenario, lineage in scenario_seeds.items()
        }
        if campaign_bound
        else None
    )
    scenario_seeds_unchanged = (
        scenario_seeds_after == scenario_seeds_before if campaign_bound else None
    )
    fixed_coverage_rows = [
        row.get("fixed_record_runtime_coverage")
        for row in rows
        if row.get("returncode") == 0 and row.get("status") == "pass"
    ]
    fixed_runtime_records = sum(
        int(coverage.get("runtime_records_checked", 0))
        for coverage in fixed_coverage_rows
        if isinstance(coverage, dict)
    )
    player_coverage_rows = [
        row.get("player_runtime_coverage")
        for row in rows
        if row.get("returncode") == 0 and row.get("status") == "pass"
    ]
    player_runtime_records = sum(
        int(coverage.get("player_runtime_groups_checked", 0))
        for coverage in player_coverage_rows
        if isinstance(coverage, dict)
    )
    player_runtime_coverage_ok = (
        len(player_coverage_rows) == len(rows)
        and all(
            isinstance(coverage, dict)
            and coverage.get("status") == "pass"
            and coverage.get("all_player_runtime_identities_asserted") is True
            for coverage in player_coverage_rows
        )
    )
    side_record_counts: dict[str, int] = {}
    for coverage in fixed_coverage_rows:
        if not isinstance(coverage, dict):
            continue
        counts = coverage.get("side_record_counts")
        if not isinstance(counts, dict):
            continue
        for side, count in counts.items():
            side_record_counts[str(side)] = side_record_counts.get(str(side), 0) + int(count)
    source_runtime_coverage_ok = (
        len(fixed_coverage_rows) == len(rows)
        and all(
            isinstance(coverage, dict)
            and coverage.get("status") == "pass"
            and coverage.get("runtime_structural_identity_asserted") is True
            and coverage.get("ui_surface_claims")
            == {
                "selected_allied_real_move_and_gray_sprite": True,
                "all_fixed_and_event_record_identity_fields": True,
                "every_side_bottom_status_opened": False,
                "every_side_detail_popup_opened": False,
                "every_side_combat_animation_opened": False,
            }
            for coverage in fixed_coverage_rows
        )
        and player_runtime_coverage_ok
    )
    return {
        "schema_version": 1,
        "status": (
            "pass"
            if (
                len(passed) == len(rows)
                and seed_unchanged
                and source_runtime_coverage_ok
                and (not campaign_bound or (campaign_unchanged and scenario_seeds_unchanged))
            )
            else "fail"
        ),
        "profile": args.profile,
        "rom": {
            "path": relative(args.rom),
            "sha256": gray.sha256(args.rom),
            "md_checksum": matrix.md_checksum(args.rom),
        },
        "seed": seed,
        "seed_unchanged": seed_unchanged,
        "seed_policy": (
            "exact_continuous_campaign_inputs"
            if campaign_bound
            else "shared_manual_diagnostic_seed"
        ),
        "campaign_bound": campaign_bound,
        "campaign": campaign_before,
        "campaign_after": campaign_after,
        "campaign_unchanged": campaign_unchanged,
        "scenario_seeds": scenario_seeds_before,
        "scenario_seeds_after": scenario_seeds_after,
        "scenario_seeds_unchanged": scenario_seeds_unchanged,
        "run_id": args.run_id,
        "workers": workers,
        "attempts_per_scenario": args.attempts,
        "display_base": args.display_base,
        "scenarios": args.scenarios,
        "directions": args.directions,
        "selection_policy": gray.SELECTION_POLICY,
        "commander_id": args.commander_id,
        "commander_class_id": f"0x{args.commander_class:02X}",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "passed_scenarios": len(passed),
        "total_scenarios": len(rows),
        "source_runtime_coverage": {
            "status": "pass" if source_runtime_coverage_ok else "fail",
            "scenario_rows_checked": len(fixed_coverage_rows),
            "fixed_and_event_runtime_records_checked": fixed_runtime_records,
            "deployed_allied_runtime_records_checked": player_runtime_records,
            "side_record_counts": side_record_counts,
            "selected_allied_real_moves_checked": len(passed),
            "all_deployed_allied_runtime_identities_asserted": (
                player_runtime_coverage_ok
            ),
            "ui_surface_claims": {
                "selected_allied_real_move_and_gray_sprite": True,
                "all_fixed_and_event_record_identity_fields": True,
                "every_side_bottom_status_opened": False,
                "every_side_detail_popup_opened": False,
                "every_side_combat_animation_opened": False,
            },
            "scope_note": (
                "Fixed/event identities are source/runtime structural checks. "
                "This matrix does not claim that each side's bottom-status, "
                "detail, or combat surface was opened."
            ),
        },
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--profile", choices=sorted(matrix.PROFILE_ROMS), required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--seed-gst", type=Path, default=matrix.DEFAULT_SEED_GST)
    parser.add_argument(
        "--campaign-summary",
        type=Path,
        help=(
            "optional completed continuous-campaign summary; when supplied, "
            "each scenario uses its exact profile input GST and no diagnostic "
            "commander/class override is applied"
        ),
    )
    parser.add_argument("--scenarios", type=parallel.parse_scenarios, default=parallel.parse_scenarios("1-31"))
    parser.add_argument("--directions", type=gray.parse_directions, default=list(gray.DEFAULT_DIRECTIONS))
    parser.add_argument("--workers", type=int, default=parallel.DEFAULT_WORKERS)
    parser.add_argument(
        "--attempts",
        type=int,
        default=2,
        help="isolated retry attempts for transient emulator startup failures",
    )
    parser.add_argument(
        "--worker-timeout",
        type=int,
        default=900,
        help="maximum seconds for one scenario worker before recording a timeout",
    )
    parser.add_argument("--display-base", type=int, default=parallel.DEFAULT_DISPLAY_BASE)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument("--xvfb-library-path", type=Path, default=parallel.DEFAULT_XVFB_LIBRARY_PATH)
    parser.add_argument("--output-root", type=Path, default=gray.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=matrix.DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--commander-id", type=int, default=1)
    parser.add_argument(
        "--commander-class", type=lambda value: int(value, 0), default=1
    )
    parser.add_argument("--commander-level", type=int, default=1)
    parser.add_argument("--commander-experience", type=int, default=0)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    args.seed_gst = args.seed_gst.resolve()
    if args.campaign_summary is not None:
        args.campaign_summary = args.campaign_summary.resolve()
    args.xvfb = args.xvfb.resolve()
    args.xvfb_library_path = args.xvfb_library_path.resolve()
    args.output_root = args.output_root.resolve()
    args.runtime_root = args.runtime_root.resolve()
    if not 1 <= args.workers <= parallel.MAX_WORKERS:
        parser.error(f"--workers must be 1..{parallel.MAX_WORKERS}")
    if not 1 <= args.attempts <= 4:
        parser.error("--attempts must be 1..4")
    if args.worker_timeout < 60:
        parser.error("--worker-timeout must be at least 60 seconds")
    if not 1 <= args.display_base <= 999 - args.workers:
        parser.error("--display-base does not leave room for every worker")
    if not 1 <= args.commander_id <= matrix.MANUAL_SLOT_COMMANDER_COUNT:
        parser.error("--commander-id is outside the saved roster")
    if not 0 <= args.commander_class < len(gray.builder.KOREAN_CLASS_LABELS):
        parser.error("--commander-class is outside the class table")
    for label, path in (("ROM", args.rom), ("seed GST", args.seed_gst)):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")
    if args.campaign_summary is not None and not args.campaign_summary.is_file():
        raise FileNotFoundError(
            f"campaign summary does not exist: {args.campaign_summary}"
        )
    args.scenario_seeds = None
    if args.command == "run" and args.campaign_summary is not None:
        args.scenario_seeds = first_turn.load_campaign_scenario_seeds(
            args.campaign_summary,
            profile=args.profile,
            run_id=args.run_id,
            rom_sha256=gray.sha256(args.rom),
            rom_path=args.rom,
            fresh_seed=args.seed_gst,
            fresh_seed_sha256=gray.sha256(args.seed_gst),
        )
    if args.command == "plan":
        result = {
            "schema_version": 1,
            "status": "pass",
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
            "directions": args.directions,
            "selection_policy": gray.SELECTION_POLICY,
            "seed_policy": (
                "exact_continuous_campaign_inputs"
                if args.campaign_summary is not None
                else "shared_manual_diagnostic_seed"
            ),
            "campaign_summary": (
                str(args.campaign_summary)
                if args.campaign_summary is not None
                else None
            ),
            "commander_id": args.commander_id,
            "commander_class_id": f"0x{args.commander_class:02X}",
            "run_id": args.run_id,
        }
    else:
        result = run_parallel(args)
        if result["status"] == "pass":
            result["contract_verification"] = verify_summary_contract(
                result,
                expected_profile=args.profile,
                expected_run_id=args.run_id,
                expected_rom_sha256=gray.sha256(args.rom),
                require_campaign_bound=args.campaign_summary is not None,
            )
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
