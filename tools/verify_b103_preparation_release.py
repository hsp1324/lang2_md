#!/usr/bin/env python3
"""Aggregate B1.0.3 full preparation and all-mercenary release evidence."""

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


ROM = ROOT / "roms/releases/Langrisser II (Korean Hard T1.0.1 B1.0.3).md"
DESKTOP_ROM = Path("/mnt/c/Users/hsp13/Desktop/Langrisser II (Korean Hard T1.0.1 B1.0.3).md")
DESKTOP_SRAM = Path("/mnt/c/Users/hsp13/Desktop/Langrisser II (Korean Hard T1.0.1 B1.0.3).srm")
OUTPUT = ROOT / "localization/b103_preparation_parallel_validation.json"
FULL_RUN_ID = "b103parallel-full01"
RECHECK_RUN_IDS = {
    3: "b103parallel-recheck01",
    11: "b103parallel-recheck01",
    20: "b103parallel-recheck01",
    22: "b103parallel-recheck01",
    23: "b103parallel-recheck01",
    25: "b103parallel-recheck02",
}
ALL_MERCENARY = (
    ROOT / "captures/run/all_mercenary_hire_probe/b103-release01/evidence.json"
)
TITLE_CAPTURE = (
    ROOT / "captures/run/b103_vram_collision_regression/b103_title.png"
)
BEFORE_CAPTURE = (
    ROOT / "captures/run/b103_vram_collision_regression/"
    "b102_royal_guard_allmerc_page04.png"
)
AFTER_CAPTURE = (
    ROOT / "captures/run/b103_vram_collision_regression/"
    "b103_royal_guard_allmerc_page04.png"
)
EXPECTED_ROM_SHA256 = "bc742e5c4c3964af9371feeb1203a9f2417fcea31d58a6dc0df0b1643101cb50"
EXPECTED_SRAM_SHA256 = "fe1001788d55851cdb0e9e36f56b49b06f18d2d35af2e0fa58923f3a92b84f4d"
EXPECTED_MD_CHECKSUM = "5F7B"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scenario_evidence_path(scenario: int) -> Path:
    run_id = RECHECK_RUN_IDS.get(scenario, FULL_RUN_ID)
    return (
        ROOT
        / "captures/run/preparation_surface_matrix/hard"
        / f"s{scenario:02d}"
        / run_id
        / "evidence.json"
    )


def build_report() -> dict[str, object]:
    rom = ROM.read_bytes()
    scenarios = []
    total_pairs = 0
    total_fixed = 0
    for scenario in range(1, 28):
        path = scenario_evidence_path(scenario)
        evidence = json.loads(path.read_text(encoding="utf-8"))
        scenarios.append(
            {
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
        )
        total_pairs += int(evidence["actual_pair_count"])
        total_fixed += int(evidence["distinct_pre_fixed_detail_count"])

    all_mercenary = json.loads(ALL_MERCENARY.read_text(encoding="utf-8"))
    translation_record = builder.build_title_version_record("번역:1.0.1")
    balance_record = builder.build_title_version_record("하드:1.0.3")
    report = {
        "schema_version": 1,
        "status": "pass",
        "release": {
            "rom": str(ROM.relative_to(ROOT)),
            "rom_sha256": sha256(ROM),
            "desktop_rom": str(DESKTOP_ROM),
            "desktop_rom_sha256": sha256(DESKTOP_ROM),
            "md_checksum": matrix.md_checksum(ROM),
            "header_title": rom[0x150:0x180].decode("ascii").rstrip(),
            "translation_title_record_sha256": hashlib.sha256(
                translation_record
            ).hexdigest(),
            "balance_title_record_sha256": hashlib.sha256(
                balance_record
            ).hexdigest(),
            "desktop_sram": str(DESKTOP_SRAM),
            "desktop_sram_sha256": sha256(DESKTOP_SRAM),
            "save_format_changed": False,
        },
        "full_preparation_matrix": {
            "profile": "hard",
            "scenarios": scenarios,
            "passed_scenarios": sum(
                row["status"] == "captured_exact_unreviewed"
                and row["actual_pair_count"] == row["expected_pair_count"]
                for row in scenarios
            ),
            "total_scenarios": len(scenarios),
            "total_pre_post_pairs": total_pairs,
            "total_distinct_fixed_details": total_fixed,
            "coverage": [
                "all allied commander roots and actual offered hire pages",
                "all arrangement roster pages",
                "all preparation-visible allied/NPC/enemy fixed details",
                "real shop item-list round trip in the same emulator process",
            ],
        },
        "all_mercenary_probe": {
            "evidence": str(ALL_MERCENARY.relative_to(ROOT)),
            "evidence_sha256": sha256(ALL_MERCENARY),
            "status": all_mercenary["status"],
            "mercenary_count": all_mercenary["mercenary_count"],
            "page_count": all_mercenary["page_count"],
            "release_rom_modified": all_mercenary["synthetic_commander"][
                "release_rom_modified"
            ],
            "ballista_icon_cell_restored": all_mercenary[
                "slot_5_collision_regression"
            ]["ballista_icon_cell_restored"],
        },
        "visual_regression": {
            "b102_collision_capture": str(BEFORE_CAPTURE.relative_to(ROOT)),
            "b102_collision_capture_sha256": sha256(BEFORE_CAPTURE),
            "b103_fixed_capture": str(AFTER_CAPTURE.relative_to(ROOT)),
            "b103_fixed_capture_sha256": sha256(AFTER_CAPTURE),
            "title_capture": str(TITLE_CAPTURE.relative_to(ROOT)),
            "title_capture_sha256": sha256(TITLE_CAPTURE),
        },
        "limitations": [
            "capture evidence remains visually unreviewed unless explicitly stated",
            "battle movement/acted sprites and battle-result screens are covered by their separate existing runtime suites",
        ],
    }
    validate(report)
    return report


def validate(report: dict[str, object]) -> None:
    matrix_report = report["full_preparation_matrix"]
    failures = []
    if report["status"] != "pass":
        failures.append("release status")
    if report["release"]["rom_sha256"] != report["release"]["desktop_rom_sha256"]:
        failures.append("desktop ROM copy")
    if report["release"]["rom_sha256"] != EXPECTED_ROM_SHA256:
        failures.append("release ROM hash")
    if report["release"]["desktop_sram_sha256"] != EXPECTED_SRAM_SHA256:
        failures.append("release SRAM hash")
    if report["release"]["md_checksum"] != EXPECTED_MD_CHECKSUM:
        failures.append("Mega Drive checksum")
    if matrix_report["passed_scenarios"] != 27:
        failures.append("all 27 scenarios")
    if any(
        row["status"] != "captured_exact_unreviewed"
        or row["actual_pair_count"] != row["expected_pair_count"]
        for row in matrix_report["scenarios"]
    ):
        failures.append("pre/post pairs")
    mercenary = report["all_mercenary_probe"]
    if (
        mercenary["status"] != "pass"
        or mercenary["mercenary_count"] != 16
        or mercenary["page_count"] != 6
        or not mercenary["ballista_icon_cell_restored"]
        or mercenary["release_rom_modified"]
    ):
        failures.append("all-mercenary probe")
    if report["release"]["header_title"] != (
        "LANGRISSER II KOREAN T1.0.1 B1.0.3 BY HSP1324"
    ):
        failures.append("ROM header title")
    if failures:
        raise ValueError("B1.0.3 release validation failed: " + ", ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            raise ValueError(f"checked B1.0.3 report is stale: {args.output}")
        print(args.output)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
