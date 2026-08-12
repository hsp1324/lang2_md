#!/usr/bin/env python3
# ruff: noqa: E402
"""Replay every route chapter while carrying one real save record forward.

The ordinary campaign is Scenario 1..27.  Secret Scenarios X1..X4 return to
13, 20, 23, and 27 respectively, so the exhaustive chronological order is
1..12, X1, 13..19, X2, 20..22, X3, 23..26, X4, 27.  Each result runner uses a
minimal runtime-clear probe but all route, preparation, opening, result,
class-change, reward, save, and ending code remains the product code.  Most
importantly, the exact serialized commander/item record captured at one save
menu becomes the next chapter's input instead of resetting to a common seed.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blastem_sequence as sequence
from tools import run_current_result_revalidation_parallel as result_parallel
from tools import run_preparation_surface_matrix as matrix
from tools import run_preparation_surface_parallel as parallel


PROFILES = result_parallel.PROFILES
SECRET_SCENARIOS = (28, 29, 30, 31)
FULL_ROUTE_ORDER = (
    *range(1, 13),
    28,
    *range(13, 20),
    29,
    *range(20, 23),
    30,
    *range(23, 27),
    31,
    27,
)
NEXT_SCENARIO = {
    **{scenario: scenario + 1 for scenario in range(1, 27)},
    28: 13,
    29: 20,
    30: 23,
    31: 27,
    27: None,
}
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/sequential_campaign_revalidation"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/sequential_campaign_runtime"


@dataclass
class XvfbSupervisor:
    """Own one profile display and revive it before a retry if it died."""

    args: argparse.Namespace
    display: str
    process: object
    restarts: int = 0

    @classmethod
    def start(
        cls,
        args: argparse.Namespace,
        display: str,
    ) -> "XvfbSupervisor":
        return cls(
            args=args,
            display=display,
            process=parallel.start_xvfb(
                args.xvfb,
                args.xvfb_library_path,
                display,
            ),
        )

    def ensure_alive(self) -> bool:
        """Return True when a dead display had to be restarted."""
        if self.process.poll() is None:
            return False
        parallel.stop_process(self.process)
        self.process = parallel.start_xvfb(
            self.args.xvfb,
            self.args.xvfb_library_path,
            self.display,
        )
        self.restarts += 1
        return True

    def stop(self) -> None:
        parallel.stop_process(self.process)


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_sha256(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise argparse.ArgumentTypeError("SHA-256 must be 64 hexadecimal characters")
    return normalized


def serialized_record_from_gst(path: Path) -> bytes:
    gst = path.read_bytes()
    parts = []
    for address, size in sequence.MANUAL_SLOT_WORK_RAM_SEGMENTS:
        start = sequence.GST_WORK_RAM_FILE_OFFSET + address
        end = start + size
        if len(gst) < end:
            raise ValueError(f"GST is too short for save data: {path}")
        parts.append(gst[start:end])
    record = b"".join(parts)
    if len(record) != sequence.MANUAL_SLOT_CHECKSUM_DATA_SIZE:
        raise ValueError("serialized save-record size changed")
    return record


def state_snapshot(path: Path) -> dict[str, object]:
    record = serialized_record_from_gst(path)
    scenario_number = int.from_bytes(
        record[
            sequence.MANUAL_SLOT_SCENARIO_OFFSET :
            sequence.MANUAL_SLOT_SCENARIO_OFFSET + 2
        ],
        "big",
    )
    if not 1 <= scenario_number <= 31:
        raise ValueError(
            f"serialized save record has invalid scenario {scenario_number}: {path}"
        )

    commanders = []
    for index in range(sequence.MANUAL_SLOT_COMMANDER_COUNT):
        start = (
            sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
            + index * sequence.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        commanders.append(
            {
                "commander_id": index + 1,
                "class_id": record[
                    start + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET
                ],
                "mp": record[start + sequence.MANUAL_SLOT_COMMANDER_MP_OFFSET],
                "level": record[
                    start + sequence.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET
                ],
                "experience": record[
                    start + sequence.MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET
                ],
                "at": record[start + sequence.MANUAL_SLOT_COMMANDER_AT_OFFSET],
                "df": record[start + sequence.MANUAL_SLOT_COMMANDER_DF_OFFSET],
                "hire_mask": int.from_bytes(
                    record[
                        start + sequence.MANUAL_SLOT_COMMANDER_HIRE_MASK_OFFSET :
                        start + sequence.MANUAL_SLOT_COMMANDER_HIRE_MASK_OFFSET + 2
                    ],
                    "big",
                ),
            }
        )

    inventory = []
    start = sequence.MANUAL_SLOT_ITEM_INVENTORY_OFFSET
    for index in range(sequence.MANUAL_SLOT_ITEM_INVENTORY_COUNT):
        offset = start + index * sequence.MANUAL_SLOT_ITEM_INVENTORY_RECORD_SIZE
        item_id, owner = record[offset : offset + 2]
        if item_id != 0xFF:
            inventory.append(
                {"slot": index, "item_id": item_id, "owner": owner}
            )
    return {
        "path": relative(path),
        "gst_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "record_sha256": hashlib.sha256(record).hexdigest(),
        "scenario": scenario_number,
        "commanders": commanders,
        "inventory": inventory,
    }


def expected_input_scenario(route_index: int) -> int:
    if route_index == 0:
        return 1
    previous = FULL_ROUTE_ORDER[route_index - 1]
    expected = NEXT_SCENARIO[previous]
    if expected is None:
        raise AssertionError("terminal Scenario 27 cannot precede another route step")
    return expected


def save_menu_gst(args: argparse.Namespace, profile: str, scenario: int) -> Path:
    output = result_parallel.task_output(
        args.output_root,
        profile,
        scenario,
        args.run_id,
    )
    return output / "states/save_menu.gst"


def run_profile(
    args: argparse.Namespace,
    profile: str,
    display: str,
    supervisor: XvfbSupervisor | None = None,
) -> dict[str, object]:
    started = time.monotonic()
    seed = args.seed_gsts[profile]
    rows = []
    status = "pass"
    input_snapshot = state_snapshot(seed)
    if input_snapshot["scenario"] != 1:
        raise ValueError(
            f"{profile} initial seed is Scenario {input_snapshot['scenario']}, not 1"
        )
    previous_output_record_sha256: str | None = None

    for route_index, scenario in enumerate(FULL_ROUTE_ORDER):
        wanted_input = expected_input_scenario(route_index)
        input_snapshot = state_snapshot(seed)
        if (
            previous_output_record_sha256 is not None
            and input_snapshot["record_sha256"] != previous_output_record_sha256
        ):
            rows.append(
                {
                    "profile": profile,
                    "scenario": scenario,
                    "status": "save_chain_record_mismatch",
                    "expected_input_record_sha256": previous_output_record_sha256,
                    "input_state": input_snapshot,
                }
            )
            status = "fail"
            break
        if input_snapshot["scenario"] != wanted_input:
            rows.append(
                {
                    "profile": profile,
                    "scenario": scenario,
                    "status": "input_transition_mismatch",
                    "expected_input_scenario": wanted_input,
                    "input_state": input_snapshot,
                }
            )
            status = "fail"
            break

        task_values = vars(args).copy()
        task_values["seed_gst"] = seed
        task_args = argparse.Namespace(**task_values)
        attempts = []
        row = None
        output_snapshot = None
        expected_next = NEXT_SCENARIO[scenario]
        for attempt in range(1, args.attempts + 1):
            display_restarted = (
                supervisor.ensure_alive()
                if supervisor is not None
                else False
            )
            output = result_parallel.task_output(
                args.output_root,
                profile,
                scenario,
                args.run_id,
            )
            if attempt > 1 and output.exists():
                shutil.rmtree(output)
            task_args.fresh_process_attempt = attempt
            row = result_parallel.run_one(task_args, profile, scenario, display)
            output_snapshot = None
            if row.get("returncode") == 0 and row.get("status") == "pass":
                if expected_next is None:
                    row["expected_next_scenario"] = None
                    row["output_state"] = None
                else:
                    produced = save_menu_gst(args, profile, scenario)
                    row["expected_next_scenario"] = expected_next
                    if not produced.is_file():
                        row["status"] = "missing_save_menu_gst"
                    else:
                        try:
                            output_snapshot = state_snapshot(produced)
                        except Exception as exc:
                            row["status"] = "invalid_save_menu_gst"
                            row["output_state_error"] = (
                                f"{type(exc).__name__}: {exc}"
                            )
                        else:
                            row["output_state"] = output_snapshot
                            if output_snapshot["scenario"] != expected_next:
                                row["status"] = "output_transition_mismatch"
            attempts.append(
                {
                    "attempt": attempt,
                    "returncode": row.get("returncode"),
                    "status": row.get("status"),
                    "elapsed_seconds": row.get("elapsed_seconds"),
                    "xvfb_restarted_before_attempt": display_restarted,
                    "fresh_process_attempt": row.get(
                        "fresh_process_attempt"
                    ),
                    "runtime_session": row.get("runtime_session"),
                    "input_seed_gst": row.get("input_seed_gst"),
                }
            )
            if row.get("returncode") == 0 and row.get("status") == "pass":
                break
            matrix.terminate_blastem_processes(display=display)
        assert row is not None
        row["attempt"] = len(attempts)
        row["attempt_history"] = attempts
        row["route_index"] = route_index
        row["run_id"] = args.run_id
        row["manual_intervention"] = False
        row["input_state"] = input_snapshot

        if row.get("returncode") != 0 or row.get("status") != "pass":
            rows.append(row)
            status = "fail"
            print(f"{profile} Scenario {scenario}: {row['status']}", flush=True)
            break

        if expected_next is not None:
            produced = save_menu_gst(args, profile, scenario)
            assert output_snapshot is not None
            previous_output_record_sha256 = str(
                output_snapshot["record_sha256"]
            )
            seed = produced

        rows.append(row)
        print(f"{profile} Scenario {scenario}: pass", flush=True)

    return {
        "profile": profile,
        "status": status,
        "display": display,
        "run_id": args.run_id,
        "release_rom": args.release_roms[profile],
        "initial_seed": state_snapshot(args.seed_gsts[profile]),
        "manual_intervention": False,
        "automation_driver": "run_current_result_revalidation_parallel.run_one",
        "passed_steps": sum(row.get("status") == "pass" for row in rows),
        "total_steps": len(FULL_ROUTE_ORDER),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "xvfb_restarts": (
            supervisor.restarts if supervisor is not None else 0
        ),
        "results": rows,
    }


def run_all(args: argparse.Namespace) -> dict[str, object]:
    displays = {
        profile: f":{args.display_base + index}"
        for index, profile in enumerate(args.profiles)
    }
    supervisors: dict[str, XvfbSupervisor] = {}
    started = time.monotonic()
    reports = []
    try:
        for profile, display in displays.items():
            supervisors[profile] = XvfbSupervisor.start(
                args,
                display,
            )
        with ThreadPoolExecutor(max_workers=len(args.profiles)) as executor:
            futures = {
                executor.submit(
                    run_profile,
                    args,
                    profile,
                    displays[profile],
                    supervisors[profile],
                ): profile
                for profile in args.profiles
            }
            for future in as_completed(futures):
                profile = futures[future]
                try:
                    reports.append(future.result())
                except Exception as exc:
                    reports.append(
                        {
                            "profile": profile,
                            "status": "orchestrator_error",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
    finally:
        for supervisor in supervisors.values():
            supervisor.stop()

    reports.sort(key=lambda row: args.profiles.index(str(row["profile"])))
    passed = sum(
        row.get("status") == "pass"
        and row.get("passed_steps") == len(FULL_ROUTE_ORDER)
        for row in reports
    )
    release_roms_after = {
        profile: {
            "path": relative(args.release_paths[profile]),
            "sha256": sha256_path(args.release_paths[profile]),
        }
        for profile in args.profiles
    }
    release_roms_unchanged = release_roms_after == args.release_roms
    return {
        "schema_version": 1,
        "status": (
            "pass"
            if passed == len(args.profiles) and release_roms_unchanged
            else "fail"
        ),
        "run_id": args.run_id,
        "profiles": args.profiles,
        "release_roms": args.release_roms,
        "release_roms_after": release_roms_after,
        "release_roms_unchanged": release_roms_unchanged,
        "route_order": list(FULL_ROUTE_ORDER),
        "secret_scenario_labels": {"28": "X1", "29": "X2", "30": "X3", "31": "X4"},
        "continuous_save_chain": True,
        "manual_intervention": False,
        "automation_only": True,
        "attempts_per_step": args.attempts,
        "maximum_simultaneous_emulators": len(args.profiles),
        "passed_profiles": passed,
        "total_profiles": len(args.profiles),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "results": reports,
    }


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    tasks = []
    for profile in args.profiles:
        for route_index, scenario in enumerate(FULL_ROUTE_ORDER):
            tasks.append(
                {
                    "profile": profile,
                    "route_index": route_index,
                    "scenario": scenario,
                    "expected_input_scenario": expected_input_scenario(route_index),
                    "expected_next_scenario": NEXT_SCENARIO[scenario],
                    "probe": relative(
                        result_parallel.task_rom(args.probe_root, profile, scenario)
                    ),
                }
            )
    return {
        "schema_version": 1,
        "status": "pass",
        "command": "plan",
        "run_id": args.run_id,
        "profiles": args.profiles,
        "route_order": list(FULL_ROUTE_ORDER),
        "continuous_save_chain": True,
        "tasks": tasks,
    }


def parse_profiles(value: str) -> list[str]:
    return result_parallel.parse_profiles(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--profiles", type=parse_profiles, default=list(PROFILES))
    parser.add_argument("--seed-pure", type=Path)
    parser.add_argument("--seed-normal", type=Path)
    parser.add_argument("--seed-hard", type=Path)
    for profile in PROFILES:
        parser.add_argument(f"--{profile}-rom", type=Path)
        parser.add_argument(
            f"--expected-{profile}-sha256",
            type=valid_sha256,
        )
    parser.add_argument("--probe-root", type=Path, default=result_parallel.DEFAULT_PROBE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--display-base", type=int, default=740)
    parser.add_argument("--xvfb", type=Path, default=parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    for name in (
        "probe_root",
        "output_root",
        "runtime_root",
        "xvfb",
        "xvfb_library_path",
    ):
        setattr(args, name, getattr(args, name).resolve())
    if not 1 <= args.attempts <= 4:
        parser.error("--attempts must be 1..4")
    if not (
        parallel.MIN_ISOLATED_DISPLAY_NUMBER
        <= args.display_base
        <= 999 - len(args.profiles)
    ):
        parser.error(
            "--display-base must reserve only high-numbered isolated Xvfb "
            "displays and leave room for every profile"
        )

    args.seed_gsts = {}
    args.release_paths = {}
    args.release_roms = {}
    for profile in args.profiles:
        seed = getattr(args, f"seed_{profile}")
        if seed is None:
            parser.error(f"--seed-{profile} is required for selected profile")
        seed = seed.resolve()
        if not seed.is_file():
            raise FileNotFoundError(f"{profile} seed GST does not exist: {seed}")
        args.seed_gsts[profile] = seed
        release_path = getattr(args, f"{profile}_rom")
        expected_release_sha256 = getattr(
            args, f"expected_{profile}_sha256"
        )
        if release_path is None or expected_release_sha256 is None:
            parser.error(
                f"--{profile}-rom and --expected-{profile}-sha256 are required"
            )
        release_path = release_path.resolve()
        if not release_path.is_file():
            raise FileNotFoundError(
                f"{profile} release ROM does not exist: {release_path}"
            )
        actual_release_sha256 = sha256_path(release_path)
        if actual_release_sha256 != expected_release_sha256:
            raise ValueError(
                f"{profile} release ROM SHA-256 mismatch: "
                f"{actual_release_sha256} != {expected_release_sha256}"
            )
        args.release_paths[profile] = release_path
        args.release_roms[profile] = {
            "path": relative(release_path),
            "sha256": actual_release_sha256,
        }
    for profile in args.profiles:
        for scenario in FULL_ROUTE_ORDER:
            rom = result_parallel.task_rom(args.probe_root, profile, scenario)
            if not rom.is_file():
                raise FileNotFoundError(f"probe ROM does not exist: {rom}")
            output = result_parallel.task_output(
                args.output_root,
                profile,
                scenario,
                args.run_id,
            )
            if output.exists():
                raise FileExistsError(f"task output already exists: {output}")
    if args.command == "run":
        for label, path in (
            ("Xvfb", args.xvfb),
            ("Xvfb library path", args.xvfb_library_path),
        ):
            if not path.exists():
                raise FileNotFoundError(f"{label} does not exist: {path}")

    report = build_plan(args) if args.command == "plan" else run_all(args)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.summary is None:
        print(encoded, end="")
    else:
        args.summary = args.summary.resolve()
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(encoded, encoding="utf-8")
        print(args.summary)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
