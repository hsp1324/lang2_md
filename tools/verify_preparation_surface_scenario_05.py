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
from tools import build_scenario5_escape_probe_rom as result_probe
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
    "normal": (
        ROOT / "captures/run/preparation_surface_matrix/normal/s05/current03"
    ),
    "hard": (
        ROOT / "captures/run/preparation_surface_matrix/hard/s05/current01"
    ),
}
GRAY_RUNS = {
    "normal": (
        ROOT / "captures/run/preparation_battle_surface/normal/s05/gray03"
    ),
    "hard": (
        ROOT / "captures/run/preparation_battle_surface/hard/s05/gray02"
    ),
}
GRAY_FILES = {
    "normal": ("acted_gray_final.png", "acted_gray_final.gst"),
    "hard": ("acted_gray.png", "acted_gray.gst"),
}
RESULT_RUNS = {
    profile: (
        ROOT / f"captures/run/preparation_result_surface/{profile}/s05/result01"
    )
    for profile in ("normal", "hard")
}
CLASS_CHOICE_PREFIXES = {
    "normal": "class_candidate",
    "hard": "class_choice",
}
REVIEW = ROOT / "localization/preparation_surface_scenario_05_review.json"
OUTPUT = ROOT / "localization/preparation_surface_scenario_05.json"
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
EXPECTED_CLASS_CHOICE_CAPTURES = (
    "cc64893c7cf1361f514592dd1a2cbe0c5f68cfc798134a8b8ba54c16f64327d3",
    "b3cc67b9c21e4d04e4fdc625c61578ebaedf0d9d44e734b7f5f3fff129d0ec72",
    "18788cf0e44002eb3168afda424fab7b254823d8b223aa4710159773f9d61f1a",
)
CLASS_CHOICE_CONTENT = (
    {
        "class_name": "로드",
        "mercenary_names": ["파이크", "솔저"],
        "magic_names": ["힐", "프로텍션"],
    },
    {
        "class_name": "호크나이트",
        "mercenary_names": ["그리폰"],
        "magic_names": ["토네이도"],
    },
    {
        "class_name": "세인트",
        "mercenary_names": ["가드맨", "파이크"],
        "magic_names": ["썬더", "일루전"],
    },
)
EXPECTED = {
    "normal": {
        "active_capture": (
            "21e2abd5b07c3a2d36c55721d534d477c214126b77058918e49b7dddd14f8134"
        ),
        "acted_capture": (
            "ced973817655796f961efc74507ead96f5b665b39ba5cc4c5043fd460df92cb1"
        ),
        "acted_gst": (
            "8c3c619f347c1371d7f0acc95c10b246aeea9e0118459a8c347a2ead5294b43d"
        ),
        "class_choice_gsts": (
            "6490aa52868cd6ca552e827a59dbe8396686e98a85239bad7357ac361f163dc6",
            "f99bc50428abb53f2c14f9fa4127b980c2bdc3c57f44b1b95c40a8406f110583",
            "d256b1db9f936f967eab889968cb3a2b2c2afa722b4257d8821aaa7b42936ae6",
        ),
        "result_capture": (
            "e76e44821e2ce531963fbca45b1645a4011e1a9408c0e9e9ea2442f3cf7bedf1"
        ),
        "result_gst": (
            "b509150cc1e2edaf32a9fdda67a19cf8f50d68d146c910823337ee51ca5dda5b"
        ),
        "result_probe_checksum": "76A0",
        "result_probe_sha256": (
            "57b2f525b17b4b0521af8e9c84ab101115a0d53d906628eb75c57ead5c2b62f5"
        ),
    },
    "hard": {
        "active_capture": (
            "21e2abd5b07c3a2d36c55721d534d477c214126b77058918e49b7dddd14f8134"
        ),
        "acted_capture": (
            "8dc6146d5c470b38683214d03a0ba6ecce12054d2b026ff3a722dad8ceb1e451"
        ),
        "acted_gst": (
            "d5c016828005f1f07716a035b2c258bc9384c2a217dd8124325e70bf1c751c0b"
        ),
        "class_choice_gsts": (
            "6e4fa7dd0420ccd8e5366f9046c4401ffb0e8cf8fd81dbc8d3f0f9b9d36b615e",
            "25bde71c903f4e44bc670358d965656ed9d5ee38a54253b578c421ceebb6aef4",
            "41ff7a0921f01bb11e9c09061a50f2fb4aa482373c9a84f9a98e6c042ea4689b",
        ),
        "result_capture": (
            "e76e44821e2ce531963fbca45b1645a4011e1a9408c0e9e9ea2442f3cf7bedf1"
        ),
        "result_gst": (
            "475c41e27e569ab73dd065804b30a9ed022add7ab82b41dbf3172756900c9277"
        ),
        "result_probe_checksum": "D981",
        "result_probe_sha256": (
            "8fc2f69eb2e8e55dccc308809011749fb76c83b3fbc963e0793132d3f178f2e0"
        ),
    },
}


def gray_plane_expectation() -> list[dict[str, object]]:
    coordinates = ((32, 7), (32, 8), (33, 7), (33, 8))
    return [
        {
            "tile": f"0x{GRAY_TILE_START + index:04X}",
            "hits": [
                {
                    "plane": "plane_a",
                    "x": x,
                    "y": y,
                    "tile_word": f"0x{0xA000 | GRAY_TILE_START + index:04X}",
                }
            ],
        }
        for index, (x, y) in enumerate(coordinates)
    ]


def diagnostic_report(
    candidate: bytes,
    expected: dict[str, object],
) -> dict[str, object]:
    diagnostic = bytearray(candidate)
    checksum = result_probe.patch_probe(
        diagnostic,
        JAPANESE_ROM.read_bytes(),
    )
    changed_offsets = [
        offset
        for offset, (before, after) in enumerate(zip(candidate, diagnostic))
        if before != after
    ]
    layout = scenario_layout(candidate, result_probe.SCENARIO_NUMBER)
    record_start = layout.records_offset
    record_end = record_start + layout.record_count * FIXED_RECORD_SIZE
    deployment_start = result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET
    deployment_end = (
        deployment_start + len(result_probe.SOURCE_PLAYER_DEPLOYMENTS) * 4
    )
    first_y = deployment_start + 2
    header_start = builder.BATTLE_RESULT_HEADER_GLYPH_LIST
    header_end = (
        header_start + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2 + 2
    )
    digest = hashlib.sha256(diagnostic).hexdigest()
    return {
        "mode": "stock_north_escape",
        "validation_source": "Japanese source ROM",
        "md_checksum": f"{checksum:04X}",
        "sha256": digest,
        "changed_offset_count": len(changed_offsets),
        "changed_offsets": [f"0x{offset:06X}" for offset in changed_offsets],
        "allowed_change_ranges": [
            "ROM checksum 0x00018E..0x00018F",
            "Elwin first deployment Y 0x18085C..0x18085D",
        ],
        "changed_only_checksum_and_elwin_y": (
            changed_offsets == [0x00018F, first_y + 1]
            and candidate[first_y : first_y + 2]
            == result_probe.SOURCE_FIRST_PLAYER_Y.to_bytes(2, "big")
            and diagnostic[first_y : first_y + 2]
            == result_probe.PROBE_FIRST_PLAYER_Y.to_bytes(2, "big")
        ),
        "scenario_layout_validated_against_source": True,
        "all_fixed_records_unchanged": (
            candidate[record_start:record_end]
            == diagnostic[record_start:record_end]
        ),
        "all_other_player_deployments_unchanged": (
            candidate[deployment_start + 4 : deployment_end]
            == diagnostic[deployment_start + 4 : deployment_end]
        ),
        "first_deployment_x_unchanged": (
            candidate[deployment_start:first_y]
            == diagnostic[deployment_start:first_y]
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
        "matches_expected_checksum": (
            f"{checksum:04X}" == expected["result_probe_checksum"]
        ),
        "matches_expected_sha256": digest == expected["result_probe_sha256"],
    }


def class_change_report(
    profile: str,
    result_root: Path,
) -> list[dict[str, object]]:
    prefix = CLASS_CHOICE_PREFIXES[profile]
    return [
        {
            "choice": index,
            **CLASS_CHOICE_CONTENT[index - 1],
            "capture": image_report(result_root / f"{prefix}_{index:02}.png"),
            "gst": relative(
                result_root / f"states/{prefix}_{index:02}.gst"
            ),
            "gst_sha256": sha256_path(
                result_root / f"states/{prefix}_{index:02}.gst"
            ),
        }
        for index in range(1, 4)
    ]


def battle_report(
    profile: str,
    candidate: bytes,
) -> dict[str, object]:
    expected = EXPECTED[profile]
    gray_root = GRAY_RUNS[profile]
    result_root = RESULT_RUNS[profile]
    acted_name, acted_gst_name = GRAY_FILES[profile]
    active = gray_root / "active_command.png"
    acted = gray_root / acted_name
    acted_gst = gray_root / acted_gst_name
    result = result_root / "battle_result.png"
    result_gst = result_root / "states/battle_result.gst"
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
        "gray_acted_sprite": {
            "run_root": relative(gray_root),
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
        "class_change": {
            "trigger": (
                "Natural Sherry level-up on the stock Scenario 5 north-escape "
                "completion path"
            ),
            "status": "pass",
            "choices": class_change_report(profile, result_root),
            "selected_choice_for_continuation": 3,
        },
        "battle_result": {
            "run_root": relative(result_root),
            "capture": image_report(result),
            "gst": relative(result_gst),
            "gst_sha256": sha256_path(result_gst),
            "header_text": builder.DIRECT_WORD_SEQUENCE_PATCHES[
                builder.BATTLE_RESULT_HEADER_GLYPH_LIST
            ][1],
            "header_vram_range": "0xA000..0xA1FF",
            "header_vram_sha256": hashlib.sha256(header_payload).hexdigest(),
            "header_plane_cells": result_header_plane_cells(result_state),
            "diagnostic_lineage": diagnostic_report(candidate, expected),
        },
    }


def run_report(
    profile: str,
    run: Path,
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
        "battle_evidence": battle_report(profile, rom),
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
    expected = EXPECTED[profile]
    battle = report["battle_evidence"]
    gray = battle["gray_acted_sprite"]
    class_change = battle["class_change"]
    result = battle["battle_result"]
    diagnostic = result["diagnostic_lineage"]
    choices = class_change["choices"]
    checks = {
        "scenario/profile": (
            report["scenario"] == 5
            and f"/{profile}/s05/" in f"/{report['run']}/"
        ),
        "candidate matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
            and report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "selected evidence is exact": (
            captured["status"] == "captured_exact_unreviewed"
            and captured["acceptance_updated"] is False
            and captured["profile"] == profile
            and captured["scenario"] == 5
            and captured["capture_pairs"] == report["capture_pairs"]
        ),
        "all 19 pairs exact": (
            report["expected_pair_count"]
            == report["actual_pair_count"]
            == 19
            and all(row["byte_identical"] for row in report["capture_pairs"])
        ),
        "all fixed records accounted": (
            report["fixed_record_count"] == 9
            and report["visible_fixed_record_indexes"] == [0, 1, 2, 3, 4]
            and report["distinct_pre_fixed_detail_count"] == 5
            and [
                row["index"]
                for row in report["not_applicable_fixed_records"]
            ]
            == [5, 6, 7, 8]
            and all(
                "(255,255)" in row["reason"]
                for row in report["not_applicable_fixed_records"]
            )
        ),
        "review and dimensions": (
            report["status"] == "scenario_5_surface_pass"
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
            and all(
                choice["capture"]["dimensions"] == [320, 240]
                for choice in choices
            )
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
            and gray["runtime_group_zero"]["hp"] == 10
            and [
                gray["runtime_group_zero"]["x"],
                gray["runtime_group_zero"]["y"],
            ]
            == [14, 51]
        ),
        "stock gray silhouette": (
            gray["source_record_offset"] == "0x05DBA8"
            and gray["source_silhouette_id"] == "0x001E"
            and gray["matches_stock_fighter_silhouette_expansion"]
            and gray["vram_sha256"] == EXPECTED_GRAY_VRAM_SHA256
            and gray["plane_references"] == gray_plane_expectation()
        ),
        "natural class change complete": (
            class_change["status"] == "pass"
            and len(choices) == 3
            and tuple(
                choice["capture"]["sha256"] for choice in choices
            )
            == EXPECTED_CLASS_CHOICE_CAPTURES
            and tuple(choice["gst_sha256"] for choice in choices)
            == expected["class_choice_gsts"]
            and all(
                choice["class_name"]
                == CLASS_CHOICE_CONTENT[index]["class_name"]
                and choice["mercenary_names"]
                == CLASS_CHOICE_CONTENT[index]["mercenary_names"]
                and choice["magic_names"]
                == CLASS_CHOICE_CONTENT[index]["magic_names"]
                for index, choice in enumerate(choices)
            )
        ),
        "result header intact": (
            result["header_text"] == "전과보고"
            and result["header_vram_sha256"]
            == EXPECTED_RESULT_HEADER_VRAM_SHA256
            and all(cell["matches"] for cell in result["header_plane_cells"])
        ),
        "diagnostic narrow": (
            diagnostic["changed_only_checksum_and_elwin_y"]
            and diagnostic["scenario_layout_validated_against_source"]
            and diagnostic["all_fixed_records_unchanged"]
            and diagnostic["all_other_player_deployments_unchanged"]
            and diagnostic["first_deployment_x_unchanged"]
            and diagnostic["scenario_event_block_unchanged"]
            and diagnostic["korean_battle_result_header_unchanged"]
            and diagnostic["matches_expected_checksum"]
            and diagnostic["matches_expected_sha256"]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} Scenario 5 evidence failed: " + ", ".join(failed)
        )


def build_report() -> dict[str, object]:
    review = read_json(REVIEW)
    profiles = {
        profile: run_report(
            profile,
            RUNS[profile],
            review["profiles"][profile],
        )
        for profile in ("normal", "hard")
    }
    return {
        "schema_version": 1,
        "status": "scenario_5_complete_pass",
        "review": {
            "path": relative(REVIEW),
            "sha256": sha256_path(REVIEW),
            "reviewed_on": review["reviewed_on"],
            "scope": review["scope"],
            "class_change": review["class_change"],
            "acceptance_effect": review["acceptance_effect"],
        },
        "profiles": profiles,
        "cross_profile_identity": {
            "all_important_preparation_and_shop_frames_identical": all(
                left["pre_sha256"] == right["pre_sha256"]
                and left["post_sha256"] == right["post_sha256"]
                for left, right in zip(
                    profiles["normal"]["capture_pairs"],
                    profiles["hard"]["capture_pairs"],
                    strict=True,
                )
            )
            and all(
                left["sha256"] == right["sha256"]
                for left, right in zip(
                    profiles["normal"]["shop_captures"],
                    profiles["hard"]["shop_captures"],
                    strict=True,
                )
            ),
            "all_three_class_change_frames_identical": (
                [
                    row["capture"]["sha256"]
                    for row in profiles["normal"]["battle_evidence"][
                        "class_change"
                    ]["choices"]
                ]
                == [
                    row["capture"]["sha256"]
                    for row in profiles["hard"]["battle_evidence"][
                        "class_change"
                    ]["choices"]
                ]
            ),
            "battle_result_frame_identical": (
                profiles["normal"]["battle_evidence"]["battle_result"][
                    "capture"
                ]["sha256"]
                == profiles["hard"]["battle_evidence"]["battle_result"][
                    "capture"
                ]["sha256"]
            ),
        },
        "matrix_progress_after_acceptance": {
            "required_profile_scenario_runs": 54,
            "preparation_surface_runs_reviewed": 12,
            "battle_surface_runs_reviewed": 12,
            "fully_accepted_profile_scenario_runs": 12,
            "fully_accepted_scenarios": 6,
            "remaining_requirement": (
                "Complete every required surface in Scenarios 6 through 8 "
                "and 10 through 27 for both profiles."
            ),
        },
        "rejected_attempts": [
            {
                "profile": "normal",
                "surface": "matrix",
                "run_id": "current01",
                "result": (
                    "The broad detail-shape detector mistook Scenario 5's "
                    "five-row arrangement menu for a fixed-detail panel. The "
                    "accepted detector uses the panel's right-edge width."
                ),
            },
            {
                "profile": "normal",
                "surface": "matrix launch",
                "run_id": "current02",
                "result": (
                    "The scenario-selector Down input missed and entered name "
                    "entry. current03 is the accepted run."
                ),
            },
            {
                "surface": "gray launch",
                "run_ids": [
                    "normal/gray01",
                    "normal/gray02",
                    "hard/gray01",
                ],
                "result": (
                    "Title/intro timing caused rejected selector or opening "
                    "states. Screen-guided launches produced normal gray03 "
                    "and hard gray02."
                ),
            },
            {
                "profile": "normal",
                "surface": "gray acted sprite",
                "run_id": "gray03/acted_gray",
                "result": (
                    "A Right move targeted an invalid red-X tile and left "
                    "acted flag 0. acted_gray_final uses the valid southeast "
                    "tile and is the only accepted normal gray state."
                ),
            },
            {
                "profile": "hard",
                "surface": "class change",
                "run_id": "result01/class_candidate_01",
                "result": (
                    "This file is the preceding extra Hein level-up page, not "
                    "a Sherry class choice. class_choice_01..03 are accepted."
                ),
            },
        ],
        "navigation_disclosures": [
            (
                "The result diagnostic changes only Elwin's first deployment "
                "Y coordinate from 50 to 1. Actual Move Up crosses the stock "
                "north escape threshold; all fixed records and event bytes "
                "remain unchanged."
            ),
            (
                "The stock completion naturally opens all three Sherry class "
                "choices. The hard profile has one additional Hein level-up "
                "page before the same byte-identical choices and result."
            ),
            (
                "Four fixed records at source coordinates (255,255) are "
                "explicitly not applicable during preparation; all five "
                "visible fixed records were captured before and after shop."
            ),
        ],
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_5_complete_pass":
        raise ValueError("Scenario 5 report must record its complete pass")
    progress = report["matrix_progress_after_acceptance"]
    if progress["fully_accepted_profile_scenario_runs"] != 12:
        raise ValueError("Six accepted scenarios must yield twelve runs")
    if progress["fully_accepted_scenarios"] != 6:
        raise ValueError("Scenarios 1 through 5 and 9 must be accepted")
    if not all(report["cross_profile_identity"].values()):
        raise ValueError("Scenario 5 cross-profile frames must be identical")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed normal/hard Scenario 5 preparation, shop, gray "
            "acted-sprite, natural class-change, and result evidence."
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
