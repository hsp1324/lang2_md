#!/usr/bin/env python3
"""Verify that every preparation capture opened its requested scenario."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_preparation_surface_matrix as matrix
from tools.run_preparation_surface_parallel import parse_scenarios
from tools.verify_battle_mercenary_sprite_cache import parse_run_id_overrides


DEFAULT_CAPTURE_ROOT = ROOT / "captures/run/preparation_surface_matrix"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def profile_report(
    *,
    profile: str,
    rom: Path,
    scenarios: list[int],
    capture_root: Path,
    run_id: str,
    run_id_overrides: dict[int, str],
) -> dict[str, object]:
    rows = []
    for scenario in scenarios:
        scenario_run_id = run_id_overrides.get(scenario, run_id)
        output = capture_root / profile / f"s{scenario:02d}" / scenario_run_id
        evidence_path = output / "evidence.json"
        gst_path = output / "states/pre_shop.gst"
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            identity = matrix.verify_runtime_scenario_identity(
                gst_path,
                rom,
                scenario,
            )
            passed = (
                str(evidence["status"]).startswith("captured_exact")
                and identity["status"] == "pass"
            )
            error = None
        except Exception as exc:
            identity = None
            passed = False
            error = f"{type(exc).__name__}: {exc}"
        rows.append({
            "scenario": scenario,
            "run_id": scenario_run_id,
            "status": "pass" if passed else "fail",
            "evidence": relative(evidence_path),
            "evidence_sha256": (
                sha256(evidence_path) if evidence_path.is_file() else None
            ),
            "gst": relative(gst_path),
            "gst_sha256": sha256(gst_path) if gst_path.is_file() else None,
            "identity": identity,
            "error": error,
        })
    return {
        "profile": profile,
        "rom": {
            "path": relative(rom),
            "sha256": sha256(rom),
            "md_checksum": matrix.md_checksum(rom),
        },
        "run_id": run_id,
        "run_id_overrides": {
            str(scenario): override
            for scenario, override in sorted(run_id_overrides.items())
        },
        "passed_scenarios": sum(row["status"] == "pass" for row in rows),
        "total_scenarios": len(rows),
        "scenarios": rows,
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    profiles = {
        "normal": profile_report(
            profile="normal",
            rom=args.normal_rom,
            scenarios=args.scenarios,
            capture_root=args.capture_root,
            run_id=args.normal_run_id,
            run_id_overrides=args.normal_run_id_overrides,
        ),
        "hard": profile_report(
            profile="hard",
            rom=args.hard_rom,
            scenarios=args.scenarios,
            capture_root=args.capture_root,
            run_id=args.hard_run_id,
            run_id_overrides=args.hard_run_id_overrides,
        ),
    }
    passed = all(
        row["passed_scenarios"] == row["total_scenarios"]
        for row in profiles.values()
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": "requested_scenario_identity_for_every_preparation_capture",
        "profiles": profiles,
        "release_rom_modified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal-rom", type=Path, required=True)
    parser.add_argument("--hard-rom", type=Path, required=True)
    parser.add_argument("--normal-run-id", required=True)
    parser.add_argument("--hard-run-id", required=True)
    parser.add_argument(
        "--normal-run-id-overrides",
        type=parse_run_id_overrides,
        default={},
    )
    parser.add_argument(
        "--hard-run-id-overrides",
        type=parse_run_id_overrides,
        default={},
    )
    parser.add_argument(
        "--scenarios",
        type=parse_scenarios,
        default=parse_scenarios("1-31"),
    )
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.normal_rom = args.normal_rom.resolve()
    args.hard_rom = args.hard_rom.resolve()
    args.capture_root = args.capture_root.resolve()
    args.output = args.output.resolve()
    report = build_report(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
