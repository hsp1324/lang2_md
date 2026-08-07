#!/usr/bin/env python3
"""Aggregate the current normal/hard Scenario 1..27 preparation probes.

This is a candidate-surface report, not a release or full acceptance report.
Battle movement, gray acted sprites, results, and scenario-specific class
changes remain owned by their separate runtime evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import run_preparation_surface_matrix as matrix
from tools import verify_b103_preparation_release as hard_release


NORMAL_ROM = ROOT / "tmp/current-preparation-b103-common-normal.md"
HARD_ROM = hard_release.ROM
OUTPUT = ROOT / "localization/current_preparation_profiles_validation.json"
NORMAL_RUN_ID = "current-b103common-full01"
NORMAL_RECHECK_RUN_IDS = {
    8: "current-b103common-focus01",
    16: "current-b103common-focus01",
    24: "current-b103common-focus01",
}
NORMAL_ALL_MERCENARY = (
    ROOT
    / "captures/run/all_mercenary_hire_probe/"
    "normal-current-b103common01/evidence.json"
)
EXPECTED_NORMAL_SHA256 = (
    "3a10c9d9b82f5bc5767a11e3f5b3d5c2e1009fdbe5a4c5ecc96699345caf3031"
)
EXPECTED_HARD_SHA256 = hard_release.EXPECTED_ROM_SHA256
EXPECTED_NORMAL_CHECKSUM = "50E7"
EXPECTED_HARD_CHECKSUM = hard_release.EXPECTED_MD_CHECKSUM


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_path(profile: str, scenario: int) -> Path:
    if profile == "normal":
        run_id = NORMAL_RECHECK_RUN_IDS.get(scenario, NORMAL_RUN_ID)
    elif profile == "hard":
        run_id = hard_release.RECHECK_RUN_IDS.get(
            scenario, hard_release.FULL_RUN_ID
        )
    else:
        raise ValueError(f"unknown profile: {profile}")
    return (
        ROOT
        / "captures/run/preparation_surface_matrix"
        / profile
        / f"s{scenario:02d}"
        / run_id
        / "evidence.json"
    )


def profile_report(profile: str, rom: Path) -> dict[str, object]:
    scenarios = []
    total_pairs = 0
    total_fixed = 0
    for scenario in range(1, 28):
        path = evidence_path(profile, scenario)
        evidence = json.loads(path.read_text(encoding="utf-8"))
        row = {
            "scenario": scenario,
            "status": evidence["status"],
            "actual_pair_count": evidence["actual_pair_count"],
            "expected_pair_count": evidence["expected_pair_count"],
            "distinct_pre_fixed_detail_count": evidence[
                "distinct_pre_fixed_detail_count"
            ],
            "evidence": str(path.relative_to(ROOT)),
            "evidence_sha256": sha256(path),
        }
        scenarios.append(row)
        total_pairs += int(row["actual_pair_count"])
        total_fixed += int(row["distinct_pre_fixed_detail_count"])
    return {
        "rom": str(rom.relative_to(ROOT)),
        "rom_sha256": sha256(rom),
        "md_checksum": matrix.md_checksum(rom),
        "scenarios": scenarios,
        "passed_scenarios": sum(
            row["status"] == "captured_exact_unreviewed"
            and row["actual_pair_count"] == row["expected_pair_count"]
            for row in scenarios
        ),
        "total_scenarios": len(scenarios),
        "total_pre_post_pairs": total_pairs,
        "total_distinct_fixed_details": total_fixed,
    }


def all_mercenary_report(profile: str, path: Path) -> dict[str, object]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    return {
        "profile": profile,
        "status": evidence["status"],
        "mercenary_count": evidence["mercenary_count"],
        "page_count": evidence["page_count"],
        "release_rom_modified": evidence["synthetic_commander"][
            "release_rom_modified"
        ],
        "ballista_icon_cell_restored": evidence[
            "slot_5_collision_regression"
        ]["ballista_icon_cell_restored"],
        "evidence": str(path.relative_to(ROOT)),
        "evidence_sha256": sha256(path),
        "page_capture_sha256": [
            row["capture_sha256"] for row in evidence["pages"]
        ],
    }


def build_report() -> dict[str, object]:
    report = {
        "schema_version": 1,
        "status": "pass",
        "scope": "candidate_preparation_and_shop_surfaces_only",
        "dynamic_tile_ids": [
            f"0x{tile:04X}" for tile in builder.BYTE_UI_DYNAMIC_TILE_IDS
        ],
        "preparation_dynamic_tile_ids": [
            f"0x{tile:04X}"
            for tile in builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS
        ],
        "profiles": {
            "normal": profile_report("normal", NORMAL_ROM),
            "hard": profile_report("hard", HARD_ROM),
        },
        "all_mercenary_probes": [
            all_mercenary_report("normal", NORMAL_ALL_MERCENARY),
            all_mercenary_report("hard", hard_release.ALL_MERCENARY),
        ],
        "normal_focus_regression": {
            "affected_first_run_scenarios": [8, 16, 24],
            "cause": "pre-shop right action focus versus post-shop left commander focus",
            "rom_defect": False,
            "recheck_status": "pass",
        },
        "coverage": [
            "all allied commander root and offered hire pages",
            "all arrangement roster pages and minimaps",
            "all preparation-visible allied/NPC/enemy fixed details",
            "real item-shop round trip in the same emulator process",
            "all 16 mercenary names and icons through an isolated synthetic SRAM",
        ],
        "limitations": [
            "full preparation captures are exact before/after but remain visually unreviewed unless separately recorded",
            "battle movement, gray acted sprites, and result screens are not exercised by this report",
            "class-change choices require separate live seeds where applicable",
            "no release ROM or version is changed by this report",
        ],
    }
    validate(report)
    return report


def validate(report: dict[str, object]) -> None:
    failures = []
    expected = {
        "normal": (EXPECTED_NORMAL_SHA256, EXPECTED_NORMAL_CHECKSUM),
        "hard": (EXPECTED_HARD_SHA256, EXPECTED_HARD_CHECKSUM),
    }
    for profile, (rom_hash, checksum) in expected.items():
        row = report["profiles"][profile]
        if row["rom_sha256"] != rom_hash or row["md_checksum"] != checksum:
            failures.append(f"{profile} ROM identity")
        if row["passed_scenarios"] != 27 or row["total_scenarios"] != 27:
            failures.append(f"{profile} Scenario 1..27 matrix")
        if any(
            scenario["status"] != "captured_exact_unreviewed"
            or scenario["actual_pair_count"] != scenario["expected_pair_count"]
            for scenario in row["scenarios"]
        ):
            failures.append(f"{profile} exact capture pairs")
    if (
        report["profiles"]["normal"]["total_pre_post_pairs"]
        != report["profiles"]["hard"]["total_pre_post_pairs"]
    ):
        failures.append("profile pair-count parity")
    for mercenary in report["all_mercenary_probes"]:
        if (
            mercenary["status"] != "pass"
            or mercenary["mercenary_count"] != 16
            or mercenary["page_count"] != 6
            or mercenary["release_rom_modified"]
            or not mercenary["ballista_icon_cell_restored"]
        ):
            failures.append(f"{mercenary['profile']} all-mercenary probe")
    # Battle surfaces use only the 16 map-safe glyph destinations. The
    # preparation renderer owns ten additional, independently audited slots
    # because its lifetime does not overlap battle map sprites/cursors.
    if len(report["dynamic_tile_ids"]) != 16:
        failures.append("dynamic tile allocation")
    if len(report["preparation_dynamic_tile_ids"]) != 26:
        failures.append("preparation dynamic tile allocation")
    if failures:
        raise ValueError(
            "current preparation profile validation failed: "
            + ", ".join(failures)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if (
            not args.output.is_file()
            or args.output.read_text(encoding="utf-8") != encoded
        ):
            raise ValueError(f"checked profile report is stale: {args.output}")
        print(args.output)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
