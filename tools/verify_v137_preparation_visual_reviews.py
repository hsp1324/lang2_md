#!/usr/bin/env python3
"""Verify all 93 hash-bound v1.3.7 preparation visual approvals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import record_v137_preparation_visual_review as review  # noqa: E402
from tools import run_preparation_surface_matrix as matrix  # noqa: E402


PROFILES = ("pure", "normal", "hard")
SCENARIOS = tuple(range(1, 32))


def valid_sha256(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise argparse.ArgumentTypeError("SHA-256 must be 64 hexadecimal characters")
    return normalized


def exact_file(
    value: object,
    *,
    expected_path: Path,
    expected_sha256: str,
    label: str,
) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} snapshot is missing")
    path = review.resolve_report_path(value.get("path"))
    if path != expected_path.resolve():
        raise ValueError(f"{label} path differs: {path} != {expected_path}")
    if value.get("sha256") != expected_sha256:
        raise ValueError(f"{label} recorded SHA-256 differs")
    if not path.is_file() or review.sha256(path) != expected_sha256:
        raise ValueError(f"{label} file is missing or changed: {path}")


def verify_one(
    *,
    profile: str,
    scenario: int,
    run_id: str,
    review_root: Path,
    capture_root: Path,
    release_path: Path,
    release_sha256: str,
) -> dict[str, object]:
    manifest_path = (
        review_root / profile / f"s{scenario:02d}" / run_id / "manifest.json"
    )
    manifest = review.load_json(manifest_path)
    if (
        manifest.get("status") != "manual_review_pass"
        or manifest.get("profile") != profile
        or manifest.get("scenario") != scenario
        or manifest.get("run_id") != run_id
    ):
        raise ValueError(f"manual review identity/status failed: {manifest_path}")
    pre_root = capture_root / profile / f"s{scenario:02d}" / run_id / "pre"
    if review.resolve_report_path(manifest.get("capture_root")) != pre_root.resolve():
        raise ValueError(f"manual review capture root differs: {manifest_path}")
    sheet_count, source_count = review.verify_manifest_files(
        manifest,
        pre_root=pre_root,
    )
    decision = manifest.get("review_decision")
    if not isinstance(decision, dict) or decision.get("decision") != "pass":
        raise ValueError(f"manual pass decision is missing: {manifest_path}")
    if decision.get("approved_requirement_ids") != list(review.REQUIREMENT_IDS):
        raise ValueError(f"manual review item coverage is incomplete: {manifest_path}")
    reviewer = decision.get("reviewer")
    reviewed_at = decision.get("reviewed_at")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError(f"manual reviewer is missing: {manifest_path}")
    if not isinstance(reviewed_at, str):
        raise ValueError(f"manual review timestamp is missing: {manifest_path}")
    review.validate_reviewed_at(reviewed_at)
    if decision.get("reviewed_sheet_count") != sheet_count:
        raise ValueError(f"reviewed sheet count changed: {manifest_path}")
    if decision.get("reviewed_source_count") != source_count:
        raise ValueError(f"reviewed source count changed: {manifest_path}")

    evidence_path = pre_root.parent / "evidence.json"
    evidence = review.load_json(evidence_path)
    review.verify_preparation_evidence(
        evidence,
        profile=profile,
        scenario=scenario,
        run_id=run_id,
    )
    exact_file(
        decision.get("preparation_evidence"),
        expected_path=evidence_path,
        expected_sha256=review.sha256(evidence_path),
        label="preparation evidence",
    )
    plan_path = pre_root.parent / "plan.json"
    plan = review.load_json(plan_path)
    exact_file(
        decision.get("preparation_plan"),
        expected_path=plan_path,
        expected_sha256=review.sha256(plan_path),
        label="preparation plan",
    )
    candidate = decision.get("candidate_rom")
    if not isinstance(candidate, dict):
        raise ValueError(f"candidate ROM lineage is missing: {manifest_path}")
    if review.resolve_report_path(candidate.get("path")) != release_path.resolve():
        raise ValueError(f"candidate ROM path differs: {manifest_path}")
    if candidate.get("sha256") != release_sha256:
        raise ValueError(f"candidate ROM SHA-256 differs: {manifest_path}")
    seed = decision.get("seed")
    if not isinstance(seed, dict) or not seed.get("path") or not seed.get("sha256"):
        raise ValueError(f"fresh seed lineage is missing: {manifest_path}")
    seed_path = review.resolve_report_path(seed["path"])
    if not seed_path.is_file() or review.sha256(seed_path) != seed["sha256"]:
        raise ValueError(f"fresh seed changed after review: {manifest_path}")

    return {
        "profile": profile,
        "scenario": scenario,
        "run_id": run_id,
        "status": "pass",
        "manifest": {
            "path": review.report_path(manifest_path),
            "sha256": review.sha256(manifest_path),
        },
        "preparation_evidence": {
            "path": review.report_path(evidence_path),
            "sha256": review.sha256(evidence_path),
        },
        "seed": seed,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "approved_requirement_ids": list(review.REQUIREMENT_IDS),
        "reviewed_sheet_count": sheet_count,
        "reviewed_source_count": source_count,
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    releases = {}
    for profile in PROFILES:
        path = getattr(args, f"{profile}_rom").resolve()
        expected = getattr(args, f"expected_{profile}_sha256")
        if not path.is_file() or review.sha256(path) != expected:
            raise ValueError(f"exact {profile} release ROM changed: {path}")
        releases[profile] = {
            "path": review.report_path(path),
            "sha256": expected,
        }
    rows = [
        verify_one(
            profile=profile,
            scenario=scenario,
            run_id=args.run_id,
            review_root=args.review_root,
            capture_root=args.capture_root,
            release_path=getattr(args, f"{profile}_rom"),
            release_sha256=getattr(args, f"expected_{profile}_sha256"),
        )
        for profile in PROFILES
        for scenario in SCENARIOS
    ]
    return {
        "schema_version": 1,
        "status": "pass",
        "run_id": args.run_id,
        "profiles": list(PROFILES),
        "scenarios": list(SCENARIOS),
        "candidate_roms": releases,
        "review_requirements": list(review.sheets.REVIEW_REQUIREMENTS),
        "reviewed_cases": len(rows),
        "required_cases": len(PROFILES) * len(SCENARIOS),
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    for profile in PROFILES:
        parser.add_argument(f"--{profile}-rom", type=Path, required=True)
        parser.add_argument(
            f"--expected-{profile}-sha256",
            type=valid_sha256,
            required=True,
        )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.review_root = args.review_root.resolve()
    args.capture_root = args.capture_root.resolve()
    args.output = args.output.resolve()
    for profile in PROFILES:
        setattr(args, f"{profile}_rom", getattr(args, f"{profile}_rom").resolve())
    if args.output.exists():
        raise FileExistsError(args.output)
    report = build_report(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
