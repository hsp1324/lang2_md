#!/usr/bin/env python3
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
from tools import build_scenario3_clear_probe_rom as result_probe
from tools import run_preparation_surface_matrix as matrix
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout
from tools.verify_preparation_surface_evidence import (
    GRAY_TILE_START,
    GRAY_VRAM_BYTES,
    GRAY_VRAM_START,
    RESULT_HEADER_VRAM_BYTES,
    RESULT_HEADER_VRAM_START,
    expected_gray_payload,
    image_report,
    load_gst,
    plane_tile_hits,
    read_json,
    relative,
    result_header_plane_cells,
    runtime_group_zero,
    sha256_path,
)


RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_surface_matrix/{profile}/s03/s03a01"
    )
    for profile in ("normal", "hard")
}
BATTLE_RUNS = {
    profile: ROOT / f"captures/run/preparation_battle_surface/{profile}/s03"
    for profile in ("normal", "hard")
}
REVIEW = ROOT / "localization/preparation_surface_scenario_03_review.json"
OUTPUT = ROOT / "localization/preparation_surface_scenario_03.json"
JAPANESE_ROM = ROOT / builder.IN_ROM
SHOP_CAPTURE_PATHS = (
    "shop/menu.png",
    "shop/item_list.png",
    "shop/returned_unfocused.png",
    "shop/returned_focused.png",
)
EXPECTED_RESULT_HEADER_VRAM_SHA256 = (
    "6b11a3261d70c91d8bb4e6bd8a637ac88172c16ad39948925a769ba127fe28b6"
)
EXPECTED_GRAY_VRAM_SHA256 = (
    "74e404c1c9dad9a31578fcdf25c61158ade1fdb43221941c7b2c3f6e19313b22"
)
EXPECTED = {
    "normal": {
        "active_capture": (
            "49b25ea35060f1884bc6ce44aa06e4fca02ea9b1f6ca14ed9ca5d236c905b5ef"
        ),
        "acted_capture": (
            "b080798961c6b44ac19ad36426c41f734ce408c3daf16811e3981f40974d8593"
        ),
        "acted_gst": (
            "e97e9593bc1532ea5ca8a9b55a6167b4689c78162cf975c5bdf1f293d629641d"
        ),
        "result_capture": (
            "d1a77467e448525d0ed6f45bd546c9baad7bd5ff767b9f9c3be90c92d6a1f0fa"
        ),
        "result_gst": (
            "7ecef3f888a2ccdc5186e5290c2ec966359a9f5bdb989ef9f1292adb80a96a0d"
        ),
        "result_probe_checksum": "FD76",
        "result_probe_sha256": (
            "52e22ee6247800843587ffa5aae85142f1d059c98c0ae061d7a4ac9ee0d3a0b8"
        ),
        "validation_source": "Japanese source ROM",
    },
    "hard": {
        "active_capture": (
            "49b25ea35060f1884bc6ce44aa06e4fca02ea9b1f6ca14ed9ca5d236c905b5ef"
        ),
        "acted_capture": (
            "261b184799b0845b6b4dde875d0a106b1f6d02ce5bbf226cbca610e600864573"
        ),
        "acted_gst": (
            "0b19eb4bb65dca701a6ed18d74544bc5cd2c7eb90a5dcb1811e8ce5f33fce848"
        ),
        "result_capture": (
            "7b89d88e0e80d8d4ccb8c13bea823e4ca41eab9d7de38e72f2d8ccf621e174b4"
        ),
        "result_gst": (
            "0616ef1a98f5eb9029baabbaa68e700ce91de619dc8d05f4c5626856f1a871f0"
        ),
        "result_probe_checksum": "46B4",
        "result_probe_sha256": (
            "dbf129e24bae3d165a37d49e1939b1613167a90ebbb1836db287013e4b626c1e"
        ),
        "validation_source": "hard candidate itself",
    },
}


def gray_plane_expectation() -> list[dict[str, object]]:
    return [
        {
            "tile": f"0x{GRAY_TILE_START + index:04X}",
            "hits": [
                {
                    "plane": "plane_a",
                    "x": 20 + index // 2,
                    "y": 8 + index % 2,
                    "tile_word": f"0x{0xA000 | GRAY_TILE_START + index:04X}",
                }
            ],
        }
        for index in range(4)
    ]


def diagnostic_report(
    profile: str,
    candidate: bytes,
    expected: dict[str, object],
) -> dict[str, object]:
    diagnostic = bytearray(candidate)
    validation_source = (
        JAPANESE_ROM.read_bytes() if profile == "normal" else candidate
    )
    checksum = result_probe.patch_probe(
        diagnostic,
        validation_source,
        enemy_annihilation=True,
    )
    wrapper = result_probe.enemy_annihilation_wrapper_code()
    changed_offsets = [
        offset
        for offset, (before, after) in enumerate(zip(candidate, diagnostic))
        if before != after
    ]
    allowed_offsets = {
        0x18E,
        0x18F,
        *range(
            result_probe.START_MENU_ENTRY_OPERAND,
            result_probe.START_MENU_ENTRY_OPERAND + 4,
        ),
        *range(
            result_probe.RUNTIME_WRAPPER,
            result_probe.RUNTIME_WRAPPER + len(wrapper),
        ),
    }
    layout = scenario_layout(candidate, result_probe.SCENARIO_NUMBER)
    fixed_start = layout.records_offset
    fixed_end = fixed_start + layout.record_count * FIXED_RECORD_SIZE
    deployment_start = result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET
    deployment_end = (
        deployment_start + result_probe.PLAYER_DEPLOYMENT_COUNT * 4
    )
    header_start = builder.BATTLE_RESULT_HEADER_GLYPH_LIST
    header_end = (
        header_start + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2 + 2
    )
    digest = hashlib.sha256(diagnostic).hexdigest()
    return {
        "mode": "enemy_annihilation",
        "validation_source": expected["validation_source"],
        "md_checksum": f"{checksum:04X}",
        "sha256": digest,
        "wrapper_byte_count": len(wrapper),
        "changed_offset_count": len(changed_offsets),
        "changed_offsets": [f"0x{offset:06X}" for offset in changed_offsets],
        "allowed_change_ranges": [
            "ROM checksum 0x00018E..0x00018F",
            "Start-menu entry operand 0x00F2E0..0x00F2E3",
            (
                f"unused wrapper 0x{result_probe.RUNTIME_WRAPPER:06X}.."
                f"0x{result_probe.RUNTIME_WRAPPER + len(wrapper) - 1:06X}"
            ),
        ],
        "changed_only_checksum_start_operand_and_wrapper": (
            bool(changed_offsets) and set(changed_offsets) <= allowed_offsets
        ),
        "scenario_layout_validated_against_source": True,
        "scenario_deployments_unchanged": (
            candidate[deployment_start:deployment_end]
            == diagnostic[deployment_start:deployment_end]
        ),
        "scenario_fixed_records_unchanged": (
            candidate[fixed_start:fixed_end]
            == diagnostic[fixed_start:fixed_end]
        ),
        "scenario_event_block_unchanged": (
            candidate[
                result_probe.EVENT_BLOCK_START : result_probe.EVENT_BLOCK_END
            ]
            == diagnostic[
                result_probe.EVENT_BLOCK_START : result_probe.EVENT_BLOCK_END
            ]
        ),
        "korean_battle_result_header_unchanged": (
            candidate[header_start:header_end]
            == diagnostic[header_start:header_end]
        ),
        "enemy_runtime_groups_marked_defeated": list(
            result_probe.ANNIHILATION_RUNTIME_GROUPS
        ),
        "matches_expected_checksum": (
            f"{checksum:04X}" == expected["result_probe_checksum"]
        ),
        "matches_expected_sha256": digest == expected["result_probe_sha256"],
    }


def battle_report(
    profile: str,
    root: Path,
    candidate: bytes,
) -> dict[str, object]:
    expected = EXPECTED[profile]
    active = root / "gray01/active_command.png"
    acted = root / "gray01/acted_gray.png"
    acted_gst = root / "gray01/states/acted_gray.gst"
    result = root / "result02/battle_result.png"
    result_gst = root / "result02/states/battle_result.gst"
    acted_state = load_gst(acted_gst)
    result_state = load_gst(result_gst)
    source_record, source_sprite_id, stock_gray = expected_gray_payload()
    gray_payload = acted_state.vram[
        GRAY_VRAM_START : GRAY_VRAM_START + GRAY_VRAM_BYTES
    ]
    header_payload = result_state.vram[
        RESULT_HEADER_VRAM_START :
        RESULT_HEADER_VRAM_START + RESULT_HEADER_VRAM_BYTES
    ]
    return {
        "status": "pass",
        "run_root": relative(root),
        "gray_acted_sprite": {
            "active_capture": image_report(active),
            "acted_capture": image_report(acted),
            "gst": relative(acted_gst),
            "gst_sha256": sha256_path(acted_gst),
            "runtime_group_zero": runtime_group_zero(acted_gst),
            "source_commander_id": 1,
            "source_class_id": 1,
            "source_record_offset": f"0x{source_record:06X}",
            "source_silhouette_id": f"0x{source_sprite_id:04X}",
            "vram_range": "0x9600..0x967F",
            "vram_sha256": hashlib.sha256(gray_payload).hexdigest(),
            "matches_stock_fighter_silhouette_expansion": (
                gray_payload == stock_gray
            ),
            "plane_references": [
                {
                    "tile": f"0x{tile:04X}",
                    "hits": plane_tile_hits(acted_state, tile),
                }
                for tile in range(GRAY_TILE_START, GRAY_TILE_START + 4)
            ],
        },
        "battle_result": {
            "capture": image_report(result),
            "gst": relative(result_gst),
            "gst_sha256": sha256_path(result_gst),
            "header_text": builder.DIRECT_WORD_SEQUENCE_PATCHES[
                builder.BATTLE_RESULT_HEADER_GLYPH_LIST
            ][1],
            "header_vram_range": "0xA000..0xA1FF",
            "header_vram_sha256": hashlib.sha256(header_payload).hexdigest(),
            "header_plane_cells": result_header_plane_cells(result_state),
            "diagnostic_lineage": diagnostic_report(
                profile,
                candidate,
                expected,
            ),
        },
    }


def run_report(
    profile: str,
    run: Path,
    battle_run: Path,
    review: dict[str, object],
) -> dict[str, object]:
    plan_path = run / "plan.json"
    evidence_path = run / "evidence.json"
    plan = read_json(plan_path)
    captured = read_json(evidence_path)
    rom_path = ROOT / plan["rom"]["path"]
    rom = rom_path.read_bytes()
    pairs = matrix.capture_pairs(run)
    expected_pair_count = (
        sum(
            1 + int(commander["hire_page_count"])
            for commander in plan["allied_commanders"]["seed_records"]
        )
        + int(plan["allied_commanders"]["roster_page_count"])
        + len(plan["fixed_records"]["route"])
        + 3
    )
    report = {
        "run": relative(run),
        "status": review["status"],
        "plan": {
            "path": relative(plan_path),
            "sha256": sha256_path(plan_path),
        },
        "captured_evidence": {
            "path": relative(evidence_path),
            "sha256": sha256_path(evidence_path),
            "original_status": captured["status"],
            "elapsed_seconds": captured["elapsed_seconds"],
        },
        "capture_status": "recomputed_exact_reviewed",
        "candidate": {
            "path": relative(rom_path),
            "md_checksum": matrix.md_checksum(rom_path),
            "sha256": sha256_path(rom_path),
        },
        "scenario": plan["scenario"],
        "allied_commander_count": plan["allied_commanders"]["count"],
        "allied_seed_records": plan["allied_commanders"]["seed_records"],
        "fixed_record_count": plan["fixed_records"]["count"],
        "visible_fixed_record_indexes": [
            row["index"] for row in plan["fixed_records"]["route"]
        ],
        "not_applicable_fixed_records": plan["fixed_records"]["not_applicable"],
        "expected_pair_count": expected_pair_count,
        "actual_pair_count": len(pairs),
        "distinct_pre_fixed_detail_count": len(
            {
                row["pre_sha256"]
                for row in pairs
                if row["surface"].startswith("fixed/record_")
            }
        ),
        "capture_pairs": pairs,
        "shop_captures": [
            image_report(run / capture) for capture in SHOP_CAPTURE_PATHS
        ],
        "battle_evidence": battle_report(profile, battle_run, rom),
        "human_review": review,
    }
    validate_run(profile, report, plan, captured)
    return report


def validate_run(
    profile: str,
    report: dict[str, object],
    plan: dict[str, object],
    captured: dict[str, object],
) -> None:
    gray = report["battle_evidence"]["gray_acted_sprite"]
    result = report["battle_evidence"]["battle_result"]
    diagnostic = result["diagnostic_lineage"]
    expected = EXPECTED[profile]
    checks = {
        "scenario/profile": (
            report["scenario"] == 3
            and f"/{profile}/s03/" in f"/{report['run']}/"
        ),
        "candidate matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
            and report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "selected evidence is exact": (
            captured["status"] == "captured_exact_unreviewed"
            and captured["acceptance_updated"] is False
            and captured["profile"] == profile
            and captured["scenario"] == 3
            and captured["capture_pairs"] == report["capture_pairs"]
        ),
        "all 15 pairs exact": (
            report["expected_pair_count"]
            == report["actual_pair_count"]
            == 15
            and all(row["byte_identical"] for row in report["capture_pairs"])
        ),
        "five visible records distinct": (
            report["visible_fixed_record_indexes"] == [0, 2, 3, 4, 5]
            and report["distinct_pre_fixed_detail_count"] == 5
        ),
        "five hidden records reasoned": (
            [
                row["index"]
                for row in report["not_applicable_fixed_records"]
            ]
            == [1, 6, 7, 8, 9]
            and all(
                "(255,255)" in row["reason"]
                for row in report["not_applicable_fixed_records"]
            )
        ),
        "review and dimensions": (
            report["status"] == "scenario_3_surface_pass"
            and all(
                value == "pass"
                for value in report["human_review"]["checks"].values()
            )
            and all(
                capture["dimensions"] == [320, 240]
                for capture in report["shop_captures"]
            )
            and gray["active_capture"]["dimensions"] == [320, 240]
            and gray["acted_capture"]["dimensions"] == [320, 240]
            and result["capture"]["dimensions"] == [320, 240]
        ),
        "battle hashes locked": (
            gray["active_capture"]["sha256"] == expected["active_capture"]
            and gray["acted_capture"]["sha256"] == expected["acted_capture"]
            and gray["gst_sha256"] == expected["acted_gst"]
            and result["capture"]["sha256"] == expected["result_capture"]
            and result["gst_sha256"] == expected["result_gst"]
        ),
        "acted Elwin Fighter": (
            gray["runtime_group_zero"]["class_id"] == 1
            and gray["runtime_group_zero"]["commander_id"] == 1
            and gray["runtime_group_zero"]["acted_flag"] == 1
            and [
                gray["runtime_group_zero"]["x"],
                gray["runtime_group_zero"]["y"],
            ]
            == [17, 15]
        ),
        "stock gray silhouette": (
            gray["source_record_offset"] == "0x05DBA8"
            and gray["source_silhouette_id"] == "0x001E"
            and gray["matches_stock_fighter_silhouette_expansion"]
            and gray["vram_sha256"] == EXPECTED_GRAY_VRAM_SHA256
            and gray["plane_references"] == gray_plane_expectation()
        ),
        "result header intact": (
            result["header_text"] == "전과보고"
            and result["header_vram_sha256"]
            == EXPECTED_RESULT_HEADER_VRAM_SHA256
            and all(cell["matches"] for cell in result["header_plane_cells"])
        ),
        "diagnostic narrow": (
            diagnostic["changed_only_checksum_start_operand_and_wrapper"]
            and diagnostic["scenario_layout_validated_against_source"]
            and diagnostic["scenario_deployments_unchanged"]
            and diagnostic["scenario_fixed_records_unchanged"]
            and diagnostic["scenario_event_block_unchanged"]
            and diagnostic["korean_battle_result_header_unchanged"]
            and diagnostic["enemy_runtime_groups_marked_defeated"]
            == list(range(5, 13))
            and diagnostic["matches_expected_checksum"]
            and diagnostic["matches_expected_sha256"]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} Scenario 3 evidence failed: " + ", ".join(failed)
        )


def build_report() -> dict[str, object]:
    review = read_json(REVIEW)
    profiles = {
        profile: run_report(
            profile,
            RUNS[profile],
            BATTLE_RUNS[profile],
            review["profiles"][profile],
        )
        for profile in ("normal", "hard")
    }
    return {
        "schema_version": 1,
        "status": "scenario_3_complete_pass",
        "review": {
            "path": relative(REVIEW),
            "sha256": sha256_path(REVIEW),
            "reviewed_on": review["reviewed_on"],
            "scope": review["scope"],
            "class_change": review["class_change"],
            "acceptance_effect": review["acceptance_effect"],
        },
        "profiles": profiles,
        "matrix_progress_after_acceptance": {
            "required_profile_scenario_runs": 54,
            "preparation_surface_runs_reviewed": 6,
            "battle_surface_runs_reviewed": 6,
            "fully_accepted_profile_scenario_runs": 6,
            "fully_accepted_scenarios": 3,
            "remaining_requirement": (
                "Complete every required surface in Scenarios 4 through 27 "
                "for both profiles."
            ),
        },
        "rejected_attempts": [
            {
                "surface": "matrix plan",
                "result": (
                    "Relative --rom paths raised Path.relative_to ValueError; "
                    "absolute repository-local candidate paths succeeded."
                ),
            },
            {
                "profile": "normal",
                "surface": "gray acted sprite",
                "result": (
                    "The first move save was a preview with acted flag 0 and "
                    "no Plane A gray references. A second C confirmed the move "
                    "and replaced it with the accepted acted state."
                ),
            },
            {
                "profile": "normal",
                "surface": "battle result",
                "run_id": "result01",
                "result": (
                    "The selector attempt stopped on the load screen; result02 "
                    "is the accepted stock-path result."
                ),
            },
            {
                "profile": "hard",
                "surface": "battle result",
                "result": (
                    "The first diagnostic build was rejected because Japanese "
                    "fixed records do not contain intended hard stats. It was "
                    "rebuilt with the hard candidate as its validation source."
                ),
            },
        ],
        "navigation_disclosures": [
            (
                "Scenario 3 requires Auto Deploy before Sortie; the first "
                "normal attempt correctly displayed the incomplete-placement "
                "warning and then recovered through Auto Deploy."
            ),
            (
                "The hard scenario selector initially missed the cheat and "
                "was recovered in the same runtime through the visible "
                "Scenario 27 selector."
            ),
            (
                "The first hard Start attempt left the commander status pane "
                "open. Closing it exposed the stock Start menu before selecting "
                "End turn and reaching the accepted result."
            ),
        ],
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_3_complete_pass":
        raise ValueError("Scenario 3 report must record its complete pass")
    progress = report["matrix_progress_after_acceptance"]
    if progress["fully_accepted_profile_scenario_runs"] != 6:
        raise ValueError("Scenarios 1 through 3 must yield six accepted runs")
    if progress["fully_accepted_scenarios"] != 3:
        raise ValueError("Scenarios 1 through 3 must be fully accepted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed normal/hard Scenario 3 preparation, shop, gray "
            "acted-sprite, and stock-path battle-result evidence."
        )
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report()
    validate_report(report)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file():
            raise FileNotFoundError(f"checked report does not exist: {args.output}")
        if args.output.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"checked report is stale: {args.output}")
        print(f"verified {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
