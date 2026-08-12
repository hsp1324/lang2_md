#!/usr/bin/env python3
"""Record one hash-bound v1.3.7 preparation-screen visual review."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_preparation_review_contact_sheets as sheets  # noqa: E402
from tools import run_preparation_surface_matrix as matrix  # noqa: E402


REQUIREMENT_IDS = tuple(row["id"] for row in sheets.REVIEW_REQUIREMENTS)


def sha256(path: Path) -> str:
    return sheets.sha256(path)


def report_path(path: Path) -> str:
    return sheets.relative(path)


def resolve_report_path(value: object) -> Path:
    path = Path(str(value))
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON document is not an object: {path}")
    return value


def validate_reviewed_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--reviewed-at must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError(
            "--reviewed-at must include an explicit timezone"
        )
    return value


def verify_manifest_files(
    manifest: dict[str, object],
    *,
    pre_root: Path,
) -> tuple[int, int]:
    if manifest.get("review_requirements") != list(sheets.REVIEW_REQUIREMENTS):
        raise ValueError("review requirement set changed")
    groups = manifest.get("groups")
    if not isinstance(groups, list):
        raise ValueError("contact-sheet groups are missing")
    by_group = {
        row.get("group"): row for row in groups if isinstance(row, dict)
    }
    if set(by_group) != set(sheets.GROUPS) or len(groups) != len(sheets.GROUPS):
        raise ValueError("contact-sheet group coverage is incomplete")

    sheet_count = 0
    source_count = 0
    for group in sheets.GROUPS:
        row = by_group[group]
        expected_sources = [path.resolve() for path in sheets.sources_for(pre_root, group)]
        listed_sources: list[Path] = []
        sheet_rows = row.get("sheets")
        if not isinstance(sheet_rows, list):
            raise ValueError(f"{group} contact sheets are missing")
        for sheet in sheet_rows:
            if not isinstance(sheet, dict):
                raise ValueError(f"{group} contact sheet entry is invalid")
            sheet_path = resolve_report_path(sheet.get("path"))
            if not sheet_path.is_file() or sha256(sheet_path) != sheet.get("sha256"):
                raise ValueError(f"contact sheet changed or is missing: {sheet_path}")
            sheet_count += 1
            sources = sheet.get("sources")
            if not isinstance(sources, list):
                raise ValueError(f"contact sheet source list is missing: {sheet_path}")
            current_sheet_sources: list[Path] = []
            for source in sources:
                if not isinstance(source, dict):
                    raise ValueError("contact sheet source entry is invalid")
                source_path = resolve_report_path(source.get("path"))
                if (
                    not source_path.is_file()
                    or sha256(source_path) != source.get("sha256")
                ):
                    raise ValueError(
                        f"review source changed or is missing: {source_path}"
                    )
                listed_sources.append(source_path)
                current_sheet_sources.append(source_path)
                source_count += 1
            if not sheets.sheet_matches_sources(
                sheet_path,
                current_sheet_sources,
            ):
                raise ValueError(
                    f"contact sheet pixels differ from its sources: {sheet_path}"
                )
        if listed_sources != expected_sources:
            raise ValueError(f"{group} review source coverage is incomplete")
        if row.get("source_count") != len(expected_sources):
            raise ValueError(f"{group} source count is stale")
        if row.get("sheet_count") != len(sheet_rows):
            raise ValueError(f"{group} sheet count is stale")
        if not expected_sources:
            raise ValueError(f"{group} has no captured review surface")
    return sheet_count, source_count


def verify_preparation_evidence(
    evidence: dict[str, object],
    *,
    profile: str,
    scenario: int,
    run_id: str,
) -> None:
    expected_identity = (profile, scenario, run_id)
    actual_identity = (
        evidence.get("profile"),
        evidence.get("scenario"),
        evidence.get("run_id"),
    )
    if actual_identity != expected_identity:
        raise ValueError(
            f"preparation evidence identity {actual_identity} != {expected_identity}"
        )
    if evidence.get("status") != "captured_exact_unreviewed":
        raise ValueError("preparation evidence is not an exact capture")
    expected_pairs = evidence.get("expected_pair_count")
    pairs = evidence.get("capture_pairs")
    if (
        not isinstance(expected_pairs, int)
        or expected_pairs < 1
        or not isinstance(pairs, list)
        or len(pairs) != expected_pairs
        or evidence.get("actual_pair_count") != expected_pairs
        or not all(isinstance(row, dict) and row.get("byte_identical") for row in pairs)
    ):
        raise ValueError("preparation pre/post pair proof is incomplete")
    identity = evidence.get("scenario_identity")
    if (
        not isinstance(identity, dict)
        or identity.get("status") != "pass"
        or identity.get("requested_scenario") != scenario
        or identity.get("identified_scenario") != scenario
    ):
        raise ValueError("runtime scenario identity proof is incomplete")


def record_review(args: argparse.Namespace) -> dict[str, object]:
    manifest_path = (
        args.review_root
        / args.profile
        / f"s{args.scenario:02d}"
        / args.run_id
        / "manifest.json"
    )
    manifest = load_json(manifest_path)
    expected_identity = (args.profile, args.scenario, args.run_id)
    actual_identity = (
        manifest.get("profile"),
        manifest.get("scenario"),
        manifest.get("run_id"),
    )
    if actual_identity != expected_identity:
        raise ValueError(
            f"review manifest identity {actual_identity} != {expected_identity}"
        )
    pre_root = (
        args.capture_root
        / args.profile
        / f"s{args.scenario:02d}"
        / args.run_id
        / "pre"
    )
    if resolve_report_path(manifest.get("capture_root")) != pre_root.resolve():
        raise ValueError("review manifest points at a different capture root")
    sheet_count, source_count = verify_manifest_files(manifest, pre_root=pre_root)

    evidence_path = pre_root.parent / "evidence.json"
    evidence = load_json(evidence_path)
    verify_preparation_evidence(
        evidence,
        profile=args.profile,
        scenario=args.scenario,
        run_id=args.run_id,
    )
    plan_path = pre_root.parent / "plan.json"
    plan = load_json(plan_path)
    if plan.get("scenario") != args.scenario:
        raise ValueError("preparation plan scenario differs from the review")
    if tuple(args.approve) != REQUIREMENT_IDS:
        raise ValueError(
            "--approve must list every requirement once in canonical order: "
            + ", ".join(REQUIREMENT_IDS)
        )
    if not args.reviewer.strip():
        raise ValueError("--reviewer must not be empty")

    manifest["status"] = "manual_review_pass"
    manifest["review_decision"] = {
        "decision": "pass",
        "reviewer": args.reviewer,
        "reviewed_at": args.reviewed_at,
        "notes": args.note,
        "approved_requirement_ids": list(args.approve),
        "reviewed_sheet_count": sheet_count,
        "reviewed_source_count": source_count,
        "preparation_evidence": {
            "path": report_path(evidence_path),
            "sha256": sha256(evidence_path),
        },
        "preparation_plan": {
            "path": report_path(plan_path),
            "sha256": sha256(plan_path),
        },
        "candidate_rom": plan.get("rom"),
        "seed": plan.get("seed_gst"),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", choices=("pure", "normal", "hard"), required=True
    )
    parser.add_argument("--scenario", type=matrix.validate_scenario, required=True)
    parser.add_argument("--run-id", type=matrix.validate_run_id, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reviewed-at", type=validate_reviewed_at, required=True)
    parser.add_argument(
        "--approve",
        action="append",
        choices=REQUIREMENT_IDS,
        required=True,
        help="repeat in the displayed canonical order for every reviewed item",
    )
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    args = parser.parse_args()
    args.review_root = args.review_root.resolve()
    args.capture_root = args.capture_root.resolve()
    result = record_review(args)
    print(
        f"{args.profile} Scenario {args.scenario}: {result['status']} "
        f"({result['review_decision']['reviewed_source_count']} sources)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
