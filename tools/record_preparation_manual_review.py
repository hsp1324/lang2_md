#!/usr/bin/env python3
"""Record a hash-bound manual review of preparation-surface contact sheets."""

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


DEFAULT_REVIEW_ROOT = ROOT / "tmp/preparation_review_contact_sheets"
DEFAULT_PREPARATION_ROOT = ROOT / "captures/run/preparation_surface_matrix"
DEFAULT_GRAY_ROOT = ROOT / "captures/run/gray_acted_surface_matrix"
DEFAULT_IDENTITY_REPORT = ROOT / "tmp/preparation-scenario-identity-corrected.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def root_path(relative_path: str) -> Path:
    path = (ROOT / relative_path).resolve()
    path.relative_to(ROOT)
    return path


def verify_manifest_hashes(manifest: dict[str, object]) -> tuple[int, int]:
    sheet_count = 0
    source_count = 0
    for group in manifest["groups"]:
        for sheet in group["sheets"]:
            path = root_path(sheet["path"])
            if sha256(path) != sheet["sha256"]:
                raise ValueError(f"contact sheet changed after generation: {path}")
            sheet_count += 1
            for source in sheet["sources"]:
                path = root_path(source["path"])
                if sha256(path) != source["sha256"]:
                    raise ValueError(f"source capture changed after generation: {path}")
                source_count += 1
    return sheet_count, source_count


def verify_identity(
    document: dict[str, object], profile: str, scenario: int, run_id: str, label: str
) -> None:
    expected = (profile, scenario, run_id)
    actual = (document.get("profile"), document.get("scenario"), document.get("run_id"))
    if actual != expected:
        raise ValueError(f"{label} identity mismatch: expected {expected}, got {actual}")


def verify_preparation_evidence(evidence: dict[str, object]) -> int:
    pairs = evidence.get("capture_pairs", [])
    if evidence.get("status") != "captured_exact_unreviewed":
        raise ValueError(f"preparation evidence is not exact/unreviewed: {evidence.get('status')}")
    if len(pairs) != evidence.get("expected_pair_count"):
        raise ValueError("preparation evidence pair count is incomplete")
    if not pairs or not all(pair.get("byte_identical") for pair in pairs):
        raise ValueError("preparation evidence contains a non-identical pre/post pair")
    return len(pairs)


def verify_gray_evidence(evidence: dict[str, object]) -> dict[str, object]:
    if evidence.get("status") != "pass":
        raise ValueError(f"gray acted evidence did not pass: {evidence.get('status')}")
    attempt = evidence.get("accepted_attempt")
    if not isinstance(attempt, dict):
        raise ValueError("gray acted evidence has no accepted attempt")
    if not attempt.get("matches_stock_fighter_silhouette_expansion"):
        raise ValueError("gray acted sprite does not match the stock silhouette expansion")
    if not attempt.get("coordinate_changed"):
        raise ValueError("gray acted probe did not perform a real movement")
    for key in ("active_capture", "acted_capture"):
        capture = attempt.get(key)
        if not isinstance(capture, dict):
            raise ValueError(f"gray acted evidence is missing {key}")
        path = root_path(capture["path"])
        if sha256(path) != capture["sha256"]:
            raise ValueError(f"gray acted capture changed after verification: {path}")
    return attempt


def verify_scenario_identity_report(
    report: dict[str, object],
    *,
    profile: str,
    scenario: int,
    run_id: str,
    preparation_path: Path,
) -> dict[str, object]:
    if report.get("status") != "pass":
        raise ValueError("scenario identity report did not pass")
    profile_report = report.get("profiles", {}).get(profile)
    if not isinstance(profile_report, dict):
        raise ValueError(f"scenario identity report has no {profile} profile")
    rows = [row for row in profile_report.get("scenarios", []) if row.get("scenario") == scenario]
    if len(rows) != 1:
        raise ValueError(f"scenario identity report has {len(rows)} rows for Scenario {scenario}")
    row = rows[0]
    if row.get("status") != "pass":
        raise ValueError(f"scenario identity did not pass for Scenario {scenario}")
    if row.get("run_id") != run_id:
        raise ValueError(
            f"scenario identity run mismatch: expected {run_id}, got {row.get('run_id')}"
        )
    expected_evidence = str(preparation_path.resolve().relative_to(ROOT))
    if row.get("evidence") != expected_evidence:
        raise ValueError("scenario identity report points at different preparation evidence")
    if row.get("evidence_sha256") != sha256(preparation_path):
        raise ValueError("scenario identity report is stale for the preparation evidence")
    identity = row.get("identity")
    if not isinstance(identity, dict):
        raise ValueError("scenario identity row has no runtime identity")
    if identity.get("identified_scenario") != scenario:
        raise ValueError(
            f"runtime capture is Scenario {identity.get('identified_scenario')}, not {scenario}"
        )
    return row


def record_review(args: argparse.Namespace) -> dict[str, object]:
    review_directory = (
        args.review_root / args.profile / f"s{args.scenario:02d}" / args.run_id
    )
    manifest_path = review_directory / "manifest.json"
    manifest = load_json(manifest_path)
    verify_identity(manifest, args.profile, args.scenario, args.run_id, "manifest")
    sheet_count, source_count = verify_manifest_hashes(manifest)

    preparation_path = (
        args.preparation_root
        / args.profile
        / f"s{args.scenario:02d}"
        / args.run_id
        / "evidence.json"
    )
    gray_path = (
        args.gray_root
        / args.profile
        / f"s{args.scenario:02d}"
        / args.run_id
        / "evidence.json"
    )
    preparation = load_json(preparation_path)
    gray = load_json(gray_path)
    identity_report = load_json(args.identity_report)
    verify_identity(preparation, args.profile, args.scenario, args.run_id, "preparation evidence")
    verify_identity(gray, args.profile, args.scenario, args.run_id, "gray evidence")
    pair_count = verify_preparation_evidence(preparation)
    gray_attempt = verify_gray_evidence(gray)
    identity_row = verify_scenario_identity_report(
        identity_report,
        profile=args.profile,
        scenario=args.scenario,
        run_id=args.run_id,
        preparation_path=preparation_path,
    )

    manifest["status"] = f"manual_review_{args.decision}"
    manifest["review_decision"] = {
        "decision": args.decision,
        "reviewer": args.reviewer,
        "reviewed_at": args.reviewed_at,
        "notes": args.note,
        "reviewed_sheet_count": sheet_count,
        "reviewed_source_count": source_count,
        "preparation_evidence": {
            "path": str(preparation_path.resolve().relative_to(ROOT)),
            "sha256": sha256(preparation_path),
            "byte_identical_pair_count": pair_count,
        },
        "scenario_identity_evidence": {
            "path": str(args.identity_report.resolve().relative_to(ROOT)),
            "sha256": sha256(args.identity_report),
            "gst_sha256": identity_row["gst_sha256"],
            "identified_scenario": identity_row["identity"]["identified_scenario"],
            "matched_records": identity_row["identity"]["best_match"]["matched_records"],
            "total_records": identity_row["identity"]["best_match"]["total_records"],
        },
        "gray_acted_evidence": {
            "path": str(gray_path.resolve().relative_to(ROOT)),
            "sha256": sha256(gray_path),
            "active_capture_sha256": gray_attempt["active_capture"]["sha256"],
            "acted_capture_sha256": gray_attempt["acted_capture"]["sha256"],
            "matches_stock_silhouette": True,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("normal", "hard"), required=True)
    parser.add_argument("--scenario", type=matrix.validate_scenario, required=True)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--decision", choices=("pass", "fail"), required=True)
    parser.add_argument("--reviewer", default="codex_manual_screen_review")
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--preparation-root", type=Path, default=DEFAULT_PREPARATION_ROOT)
    parser.add_argument("--gray-root", type=Path, default=DEFAULT_GRAY_ROOT)
    parser.add_argument(
        "--identity-report",
        type=Path,
        default=DEFAULT_IDENTITY_REPORT,
    )
    args = parser.parse_args()
    args.review_root = args.review_root.resolve()
    args.preparation_root = args.preparation_root.resolve()
    args.gray_root = args.gray_root.resolve()
    args.identity_report = args.identity_report.resolve()
    manifest = record_review(args)
    decision = manifest["review_decision"]
    print(
        f"{args.profile} Scenario {args.scenario}: {manifest['status']} "
        f"({decision['reviewed_sheet_count']} sheets, "
        f"{decision['reviewed_source_count']} sources)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
