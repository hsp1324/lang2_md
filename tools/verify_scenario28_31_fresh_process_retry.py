#!/usr/bin/env python3
"""Verify a failed/pass pair made by two fresh isolated BlastEm processes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("evidence path is missing")
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def load(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"evidence is not an object: {path}")
    return data


def forbidden_load_actions(data: dict[str, object]) -> list[object]:
    forbidden = []
    actions = data.get("actions")
    if not isinstance(actions, list):
        return ["actions_missing"]
    for action in actions:
        if not isinstance(action, dict):
            forbidden.append(action)
            continue
        keys = action.get("keys")
        if not isinstance(keys, list):
            forbidden.append(action)
            continue
        if any(
            isinstance(key, str)
            and (key == "load" or key.startswith("load:"))
            for key in keys
        ):
            forbidden.append(action)
    return forbidden


def verify_pair(failed_path: Path, passed_path: Path) -> dict[str, object]:
    failed = load(failed_path)
    passed = load(passed_path)
    errors = []
    if failed.get("status") != "failed_attempt":
        errors.append("first process did not fail closed")
    if passed.get("status") != "pass":
        errors.append("second process did not pass")
    for label, data, attempt in (
        ("failed", failed, 1),
        ("passed", passed, 2),
    ):
        if data.get("retry_policy") != "external_fresh_process_only":
            errors.append(f"{label} retry policy differs")
        if data.get("fresh_process_attempt") != attempt:
            errors.append(f"{label} fresh-process number differs")
        forbidden = forbidden_load_actions(data)
        if forbidden:
            errors.append(f"{label} contains synthetic load actions: {forbidden}")

    seeds = [data.get("input_seed_gst") for data in (failed, passed)]
    if not all(isinstance(seed, dict) for seed in seeds):
        errors.append("input seed proof is missing")
    elif seeds[0] != seeds[1]:
        errors.append("fresh processes did not use the same input GST")
    else:
        seed = seeds[0]
        seed_path = report_path(seed.get("path"))
        if not seed_path.is_file() or sha256(seed_path) != seed.get("sha256"):
            errors.append("input GST path/hash proof broke")

    sessions = [data.get("runtime_session") for data in (failed, passed)]
    if not all(isinstance(session, dict) for session in sessions):
        errors.append("live runtime-session proof is missing")
    else:
        process_keys = []
        homes = []
        for label, session in zip(("failed", "passed"), sessions):
            process_keys.append(
                (session.get("pid"), session.get("proc_start_time_ticks"))
            )
            homes.append(session.get("runtime_home"))
            if (
                type(session.get("pid")) is not int
                or type(session.get("proc_start_time_ticks")) is not int
                or session.get("runtime_home") != session.get("observed_home")
                or session.get("display") != session.get("observed_display")
                or session.get("isolated_virtual_display") is not True
            ):
                errors.append(f"{label} runtime-session identity differs")
            rom_path = report_path(session.get("probe_rom"))
            if (
                not rom_path.is_file()
                or sha256(rom_path) != session.get("probe_rom_sha256")
            ):
                errors.append(f"{label} probe ROM path/hash proof broke")
        if len(set(process_keys)) != 2:
            errors.append("retry reused one BlastEm process identity")
        if len(set(homes)) != 2:
            errors.append("retry reused one runtime HOME")
        if sessions[0].get("display") != sessions[1].get("display"):
            errors.append("retry did not stay on the assigned virtual display")
        if sessions[0].get("probe_rom_sha256") != sessions[1].get(
            "probe_rom_sha256"
        ):
            errors.append("retry changed the exact probe ROM")

    return {
        "schema_version": 1,
        "status": "pass" if not errors else "fail",
        "policy": "same_input_gst_distinct_fresh_blastem_processes",
        "failed_evidence": {
            "path": str(failed_path.resolve()),
            "sha256": sha256(failed_path),
        },
        "passed_evidence": {
            "path": str(passed_path.resolve()),
            "sha256": sha256(passed_path),
        },
        "same_input_seed": seeds[0] == seeds[1],
        "process_identities": [
            {
                "pid": session.get("pid"),
                "proc_start_time_ticks": session.get("proc_start_time_ticks"),
                "runtime_home": session.get("runtime_home"),
                "display": session.get("display"),
            }
            for session in sessions
            if isinstance(session, dict)
        ],
        "synthetic_load_actions": {
            "failed": forbidden_load_actions(failed),
            "passed": forbidden_load_actions(passed),
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failed", type=Path, required=True)
    parser.add_argument("--passed", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    for name in ("failed", "passed", "summary"):
        setattr(args, name, getattr(args, name).resolve())
    for path in (args.failed, args.passed):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.summary.exists():
        raise FileExistsError(args.summary)
    report = verify_pair(args.failed, args.passed)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.summary)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
