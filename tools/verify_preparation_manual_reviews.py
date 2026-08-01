#!/usr/bin/env python3
"""Verify every hash-bound preparation-surface manual review as one gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import record_preparation_manual_review as review
from tools import run_preparation_surface_matrix as matrix


DEFAULT_REVIEW_ROOT = ROOT / "tmp/preparation_review_contact_sheets"
DEFAULT_PREPARATION_ROOT = ROOT / "captures/run/preparation_surface_matrix"
DEFAULT_GRAY_ROOT = ROOT / "captures/run/gray_acted_surface_matrix"
DEFAULT_IDENTITY_REPORT = (
    ROOT / "tmp/full_surface_regression/pike-safe-full01/"
    "preparation-scenario-identity.json"
)
DEFAULT_OUTPUT = ROOT / "localization/preparation_manual_review_current_candidate.json"
DEFAULT_NORMAL_ROM = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
DEFAULT_HARD_ROM = ROOT / "tmp/current-glyph-lifetime-fix-hard.md"
PROFILES = ("normal", "hard")
SCENARIOS = tuple(range(1, 28))
DEFAULT_RUN_ID = "pike-safe-full01"


def run_id_for(scenario: int) -> str:
    if scenario == 3:
        return "glyph-lifetime-s03-corrected01"
    return "glyph-lifetime-full01"


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def verify_recorded_decision(
    manifest: dict[str, object],
    *,
    sheet_count: int,
    source_count: int,
    preparation_path: Path,
    preparation_pairs: int,
    identity_report_path: Path,
    identity_row: dict[str, object],
    gray_path: Path,
    gray_attempt: dict[str, object],
) -> dict[str, object]:
    require_equal(manifest.get("status"), "manual_review_pass", "manifest status")
    decision = manifest.get("review_decision")
    if not isinstance(decision, dict):
        raise ValueError("manifest has no recorded review decision")
    require_equal(decision.get("decision"), "pass", "manual review decision")
    require_equal(decision.get("reviewed_sheet_count"), sheet_count, "reviewed sheet count")
    require_equal(decision.get("reviewed_source_count"), source_count, "reviewed source count")

    preparation = decision.get("preparation_evidence")
    if not isinstance(preparation, dict):
        raise ValueError("manual review has no preparation evidence binding")
    require_equal(preparation.get("path"), relative(preparation_path), "preparation evidence path")
    require_equal(preparation.get("sha256"), review.sha256(preparation_path), "preparation evidence hash")
    require_equal(
        preparation.get("byte_identical_pair_count"),
        preparation_pairs,
        "preparation pair count",
    )

    identity = decision.get("scenario_identity_evidence")
    if not isinstance(identity, dict):
        raise ValueError("manual review has no scenario identity binding")
    require_equal(identity.get("path"), relative(identity_report_path), "identity report path")
    require_equal(identity.get("sha256"), review.sha256(identity_report_path), "identity report hash")
    require_equal(identity.get("gst_sha256"), identity_row.get("gst_sha256"), "identity GST hash")
    runtime_identity = identity_row["identity"]
    require_equal(
        identity.get("identified_scenario"),
        runtime_identity.get("identified_scenario"),
        "identified scenario",
    )
    best_match = runtime_identity["best_match"]
    require_equal(identity.get("matched_records"), best_match.get("matched_records"), "matched records")
    require_equal(identity.get("total_records"), best_match.get("total_records"), "total records")

    gray = decision.get("gray_acted_evidence")
    if not isinstance(gray, dict):
        raise ValueError("manual review has no gray acted evidence binding")
    require_equal(gray.get("path"), relative(gray_path), "gray evidence path")
    require_equal(gray.get("sha256"), review.sha256(gray_path), "gray evidence hash")
    require_equal(
        gray.get("active_capture_sha256"),
        gray_attempt["active_capture"]["sha256"],
        "gray active capture hash",
    )
    require_equal(
        gray.get("acted_capture_sha256"),
        gray_attempt["acted_capture"]["sha256"],
        "gray acted capture hash",
    )
    require_equal(gray.get("matches_stock_silhouette"), True, "stock silhouette decision")
    return decision


def verify_one(
    *,
    profile: str,
    scenario: int,
    run_id: str,
    review_root: Path,
    preparation_root: Path,
    gray_root: Path,
    identity_report_path: Path,
    identity_report: dict[str, object],
) -> dict[str, object]:
    manifest_path = review_root / profile / f"s{scenario:02d}" / run_id / "manifest.json"
    preparation_path = preparation_root / profile / f"s{scenario:02d}" / run_id / "evidence.json"
    gray_path = gray_root / profile / f"s{scenario:02d}" / run_id / "evidence.json"
    manifest = review.load_json(manifest_path)
    preparation = review.load_json(preparation_path)
    gray = review.load_json(gray_path)

    review.verify_identity(manifest, profile, scenario, run_id, "manifest")
    review.verify_identity(preparation, profile, scenario, run_id, "preparation evidence")
    review.verify_identity(gray, profile, scenario, run_id, "gray evidence")
    sheet_count, source_count = review.verify_manifest_hashes(manifest)
    preparation_pairs = review.verify_preparation_evidence(preparation)
    gray_attempt = review.verify_gray_evidence(gray)
    identity_row = review.verify_scenario_identity_report(
        identity_report,
        profile=profile,
        scenario=scenario,
        run_id=run_id,
        preparation_path=preparation_path,
    )
    decision = verify_recorded_decision(
        manifest,
        sheet_count=sheet_count,
        source_count=source_count,
        preparation_path=preparation_path,
        preparation_pairs=preparation_pairs,
        identity_report_path=identity_report_path,
        identity_row=identity_row,
        gray_path=gray_path,
        gray_attempt=gray_attempt,
    )
    return {
        "scenario": scenario,
        "run_id": run_id,
        "status": "pass",
        "manifest": relative(manifest_path),
        "manifest_sha256": review.sha256(manifest_path),
        "reviewed_at": decision.get("reviewed_at"),
        "contact_sheets": sheet_count,
        "source_captures": source_count,
        "byte_identical_pre_post_pairs": preparation_pairs,
        "identified_scenario": identity_row["identity"]["identified_scenario"],
        "gray_acted_stock_silhouette": True,
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    identity_report = review.load_json(args.identity_report)
    selected = tuple(args.scenario or SCENARIOS)
    profiles: dict[str, object] = {}
    for profile in PROFILES:
        rows = [
            verify_one(
                profile=profile,
                scenario=scenario,
                run_id=getattr(args, "run_id", DEFAULT_RUN_ID)
                or run_id_for(scenario),
                review_root=args.review_root,
                preparation_root=args.preparation_root,
                gray_root=args.gray_root,
                identity_report_path=args.identity_report,
                identity_report=identity_report,
            )
            for scenario in selected
        ]
        profiles[profile] = {
            "status": "pass",
            "passed": len(rows),
            "required": len(selected),
            "scenarios": rows,
        }
    reviewed_dates = sorted({
        row["reviewed_at"]
        for profile in PROFILES
        for row in profiles[profile]["scenarios"]
    })
    if len(reviewed_dates) != 1:
        raise ValueError(f"manual reviews do not share one review date: {reviewed_dates}")
    return {
        "schema_version": 1,
        "status": "pass",
        "reviewed_on": reviewed_dates[0],
        "candidate_roms": {
            "normal": {
                "path": relative(args.normal_rom),
                "sha256": review.sha256(args.normal_rom),
            },
            "hard": {
                "path": relative(args.hard_rom),
                "sha256": review.sha256(args.hard_rom),
            },
        },
        "scenario_identity_report": {
            "path": relative(args.identity_report),
            "sha256": review.sha256(args.identity_report),
        },
        "requirements": [
            "every reviewed contact sheet and source capture retains its recorded SHA-256",
            "every same-run shop pre/post preparation pair is byte-identical",
            "every runtime save state is identified as the requested scenario",
            "every acted-unit probe performs a real move and matches the stock gray silhouette",
            "both normal and hard profiles pass every requested scenario",
        ],
        "profiles": profiles,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=matrix.validate_scenario, action="append")
    parser.add_argument(
        "--run-id",
        type=matrix.validate_run_id,
        default=DEFAULT_RUN_ID,
    )
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--preparation-root", type=Path, default=DEFAULT_PREPARATION_ROOT)
    parser.add_argument("--gray-root", type=Path, default=DEFAULT_GRAY_ROOT)
    parser.add_argument("--identity-report", type=Path, default=DEFAULT_IDENTITY_REPORT)
    parser.add_argument("--normal-rom", type=Path, default=DEFAULT_NORMAL_ROM)
    parser.add_argument("--hard-rom", type=Path, default=DEFAULT_HARD_ROM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    for name in (
        "review_root",
        "preparation_root",
        "gray_root",
        "identity_report",
        "normal_rom",
        "hard_rom",
        "output",
    ):
        setattr(args, name, getattr(args, name).resolve())
    report = build_report(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for profile in PROFILES:
        summary = report["profiles"][profile]
        print(f"{profile}: {summary['passed']}/{summary['required']} pass")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
