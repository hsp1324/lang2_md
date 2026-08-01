#!/usr/bin/env python3
"""Transfer a passed review only when every new source capture is hash-exact."""

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
DEFAULT_SOURCE_AGGREGATE = (
    ROOT / "localization/preparation_manual_review_current_candidate.json"
)


def surface_key(path_text: str) -> str:
    parts = Path(path_text).parts
    try:
        index = parts.index("pre")
    except ValueError as exc:
        raise ValueError(f"review source is not below a pre directory: {path_text}") from exc
    return "/".join(parts[index + 1:])


def source_hashes(manifest: dict[str, object]) -> dict[str, str]:
    result: dict[str, str] = {}
    for group in manifest["groups"]:
        for sheet in group["sheets"]:
            for source in sheet["sources"]:
                key = surface_key(source["path"])
                if key in result:
                    raise ValueError(f"duplicate review source: {key}")
                result[key] = source["sha256"]
    return result


def pair_hashes(evidence: dict[str, object]) -> dict[str, tuple[str, str]]:
    return {
        row["surface"]: (row["pre_sha256"], row["post_sha256"])
        for row in evidence["capture_pairs"]
    }


def source_row(
    aggregate: dict[str, object], profile: str, scenario: int
) -> dict[str, object]:
    rows = [
        row
        for row in aggregate["profiles"][profile]["scenarios"]
        if row["scenario"] == scenario
    ]
    if len(rows) != 1 or rows[0]["status"] != "pass":
        raise ValueError(
            f"source aggregate has no unique pass for {profile} Scenario {scenario}"
        )
    return rows[0]


def transfer(args: argparse.Namespace) -> dict[str, object]:
    aggregate = review.load_json(args.source_aggregate)
    if aggregate.get("status") != "pass":
        raise ValueError("source aggregate did not pass")
    old_row = source_row(aggregate, args.profile, args.scenario)
    old_run_id = old_row["run_id"]
    old_manifest_path = (
        args.review_root
        / args.profile
        / f"s{args.scenario:02d}"
        / old_run_id
        / "manifest.json"
    )
    new_manifest_path = (
        args.review_root
        / args.profile
        / f"s{args.scenario:02d}"
        / args.run_id
        / "manifest.json"
    )
    old_preparation_path = (
        args.preparation_root
        / args.profile
        / f"s{args.scenario:02d}"
        / old_run_id
        / "evidence.json"
    )
    new_preparation_path = (
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

    old_manifest = review.load_json(old_manifest_path)
    new_manifest = review.load_json(new_manifest_path)
    old_preparation = review.load_json(old_preparation_path)
    new_preparation = review.load_json(new_preparation_path)
    gray = review.load_json(gray_path)
    identity_report = review.load_json(args.identity_report)

    if old_manifest.get("status") != "manual_review_pass":
        raise ValueError("source manifest is not a passed manual review")
    if review.sha256(old_manifest_path) != old_row["manifest_sha256"]:
        raise ValueError("source aggregate points at a changed source manifest")
    review.verify_identity(
        new_manifest, args.profile, args.scenario, args.run_id, "target manifest"
    )
    sheet_count, source_count = review.verify_manifest_hashes(new_manifest)
    pair_count = review.verify_preparation_evidence(new_preparation)
    gray_attempt = review.verify_gray_evidence(gray)
    identity_row = review.verify_scenario_identity_report(
        identity_report,
        profile=args.profile,
        scenario=args.scenario,
        run_id=args.run_id,
        preparation_path=new_preparation_path,
    )

    old_sources = source_hashes(old_manifest)
    new_sources = source_hashes(new_manifest)
    if new_sources != old_sources:
        changed = sorted(
            key
            for key in set(old_sources) | set(new_sources)
            if old_sources.get(key) != new_sources.get(key)
        )
        raise ValueError(f"target review sources changed: {changed[:8]}")
    if pair_hashes(new_preparation) != pair_hashes(old_preparation):
        raise ValueError("target before/after capture-pair hashes changed")

    new_manifest["status"] = "manual_review_pass"
    new_manifest["review_decision"] = {
        "decision": "pass",
        "reviewer": "codex_hash_exact_review_transfer",
        "reviewed_at": args.reviewed_at,
        "notes": [
            "Every target source capture is SHA-256 identical to the prior manually reviewed source with the same preparation-surface key.",
            "Every target same-run pre/post-shop pair is SHA-256 identical to the corresponding prior reviewed pair.",
        ],
        "reviewed_sheet_count": sheet_count,
        "reviewed_source_count": source_count,
        "preparation_evidence": {
            "path": str(new_preparation_path.relative_to(ROOT)),
            "sha256": review.sha256(new_preparation_path),
            "byte_identical_pair_count": pair_count,
        },
        "scenario_identity_evidence": {
            "path": str(args.identity_report.relative_to(ROOT)),
            "sha256": review.sha256(args.identity_report),
            "gst_sha256": identity_row["gst_sha256"],
            "identified_scenario": identity_row["identity"]["identified_scenario"],
            "matched_records": identity_row["identity"]["best_match"]["matched_records"],
            "total_records": identity_row["identity"]["best_match"]["total_records"],
        },
        "gray_acted_evidence": {
            "path": str(gray_path.relative_to(ROOT)),
            "sha256": review.sha256(gray_path),
            "active_capture_sha256": gray_attempt["active_capture"]["sha256"],
            "acted_capture_sha256": gray_attempt["acted_capture"]["sha256"],
            "matches_stock_silhouette": True,
        },
        "hash_exact_review_transfer": {
            "source_manifest": str(old_manifest_path.relative_to(ROOT)),
            "source_manifest_sha256": review.sha256(old_manifest_path),
            "source_run_id": old_run_id,
            "source_capture_count": len(old_sources),
            "source_pair_count": len(pair_hashes(old_preparation)),
            "all_source_hashes_equal": True,
            "all_pair_hashes_equal": True,
        },
    }
    new_manifest_path.write_text(
        json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return new_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("normal", "hard"), required=True)
    parser.add_argument("--scenario", type=matrix.validate_scenario, required=True)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--identity-report", type=Path, required=True)
    parser.add_argument("--source-aggregate", type=Path, default=DEFAULT_SOURCE_AGGREGATE)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--preparation-root", type=Path, default=DEFAULT_PREPARATION_ROOT)
    parser.add_argument("--gray-root", type=Path, default=DEFAULT_GRAY_ROOT)
    args = parser.parse_args()
    for name in (
        "identity_report",
        "source_aggregate",
        "review_root",
        "preparation_root",
        "gray_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    manifest = transfer(args)
    decision = manifest["review_decision"]
    print(
        f"{args.profile} Scenario {args.scenario}: hash-exact review transfer pass "
        f"({decision['reviewed_source_count']} sources)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
