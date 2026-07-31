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
from tools import build_scenario6_clear_probe_rom as result_probe
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
        / f"captures/run/preparation_surface_matrix/{profile}/s06/current01"
    )
    for profile in ("normal", "hard")
}
GRAY_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_battle_surface/{profile}/s06/gray02"
    )
    for profile in ("normal", "hard")
}
CLASS_RUNS = {
    "normal": (
        ROOT
        / "captures/run/preparation_battle_surface/normal/s06/result05"
    ),
    "hard": (
        ROOT
        / "captures/run/preparation_battle_surface/hard/s06/result02"
    ),
}
RESULT_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_battle_surface/{profile}/s06/result02"
    )
    for profile in ("normal", "hard")
}
REVIEW = ROOT / "localization/preparation_surface_scenario_06_review.json"
OUTPUT = ROOT / "localization/preparation_surface_scenario_06.json"
JAPANESE_ROM = ROOT / builder.IN_ROM
SHOP_CAPTURE_PATHS = (
    "shop/menu.png",
    "shop/item_list.png",
    "shop/returned_unfocused.png",
    "shop/returned_focused.png",
)
EXPECTED_GRAY_VRAM_SHA256 = (
    "74e404c1c9dad9a31578fcdf25c61158ade1fdb43221941c7b2c3f6e19313b22"
)
EXPECTED_RESULT_HEADER_VRAM_SHA256 = (
    "6b11a3261d70c91d8bb4e6bd8a637ac88172c16ad39948925a769ba127fe28b6"
)
CLASS_CHOICE_FILENAMES = (
    "class_change_choice_01_lord",
    "class_change_choice_02_hawk_knight",
    "class_change_choice_03_saint",
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
EXPECTED_CLASS_CHOICE_CAPTURES = (
    "7d30afd633241af4c565992037f0078a9788afbaef4c6280af3efce91595e560",
    "70e59bc0f4187484af31a03945423a7e0ee45c514cf4bba113df23f32d68d099",
    "e1010a597d4d4f43dbf53a913037dd27e227dce8399630c2993b3a18ed060880",
)
EXPECTED = {
    "normal": {
        "active_capture": (
            "9f020d9af4ad6ea3bf8b7008e917bb22282c48aeb29f49080a69f7297b07d6e2"
        ),
        "acted_capture": (
            "8ada4a6358450ae9e24a15ca8944857bf89b9f32d72defdddb2cabd7a09b89cb"
        ),
        "acted_gst": (
            "5a0a47546de162a815020b4194c9ce262f51c4ba0b751d23185d093bb1e0be8e"
        ),
        "class_choice_gsts": (
            "919eba96ce42fe7b752c069f7b488af6d08069e23047df1ef014531a4bb135ba",
            "05afc50902f5cd07ce3909007f97bf316557827622beba845f0f1ab396d13eea",
            "ac1a4d6d7f0d93a6e4638431490dfabc3667cf6e6d315c75c6daad5e88897951",
        ),
        "result_capture": (
            "aa287f932be6ed664f3f85aa4f8d98d0ebaf6fbd7d7ae411009c182d85c66f6f"
        ),
        "result_gst": (
            "ac13bc33612c15ff3d3c0528259f6d846535a495583cd8abd7ff5196d3178fbe"
        ),
        "result_probe_checksum": "4500",
        "result_probe_sha256": (
            "41aa35eee176ac51d46c52b18a2a0cf0ddb755c164dd8d37ab485e066055fb08"
        ),
        "selected_result_class": "로드",
    },
    "hard": {
        "active_capture": (
            "9f020d9af4ad6ea3bf8b7008e917bb22282c48aeb29f49080a69f7297b07d6e2"
        ),
        "acted_capture": (
            "fc570d4cb17f4f06dde913bc2820a755118a3a1066885c3ba044223a33970d1b"
        ),
        "acted_gst": (
            "d804e2653e1305b757e85042e0c4088c54a816271e71645f386eba1370bcabfd"
        ),
        "class_choice_gsts": (
            "b169e548200127181014b6d1bb2457a1465b2cbe106dce4b7050cff228ee9841",
            "70479a3bcf78c11b578bab8f96313eca7ebc787cfcbe331d2072c15eb8cd94bd",
            "b8894f4f5ab0ca6ac7513bbde491473125bbe31d7708097cf986fe8a8b43856b",
        ),
        "result_capture": (
            "c720cacffa072a0541d9a9f15fac40866b331429fae0249976a3322c73e6fb78"
        ),
        "result_gst": (
            "5c05833f30728d78496e3bf3f968de625899151d3eb9f0f775cc765f87c0b3f3"
        ),
        "result_probe_checksum": "A7E1",
        "result_probe_sha256": (
            "05d07c56ba2b8e6ee90224311adb006422ca76143a14f6cdec6fcef21288bb5e"
        ),
        "selected_result_class": "세인트",
    },
}


def gray_plane_expectation() -> list[dict[str, object]]:
    coordinates = ((54, 27), (54, 28), (55, 27), (55, 28))
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
    source = JAPANESE_ROM.read_bytes()
    diagnostic = bytearray(candidate)
    checksum = result_probe.patch_probe(
        diagnostic,
        source,
        enemy_annihilation=True,
    )
    changed_offsets = [
        offset
        for offset, (before, after) in enumerate(zip(candidate, diagnostic))
        if before != after
    ]
    wrapper = result_probe.enemy_annihilation_wrapper_code()
    allowed = {0x18E, 0x18F}
    allowed.update(
        range(
            result_probe.START_MENU_ENTRY_OPERAND,
            result_probe.START_MENU_ENTRY_OPERAND + 4,
        )
    )
    allowed.update(
        range(
            result_probe.PARTIAL_LOSS_WRAPPER,
            result_probe.PARTIAL_LOSS_WRAPPER + len(wrapper),
        )
    )
    layout = scenario_layout(candidate, result_probe.SCENARIO_NUMBER)
    fixed_start = layout.records_offset
    fixed_end = fixed_start + layout.record_count * FIXED_RECORD_SIZE
    deployment_start = result_probe.DEPLOYMENT_TABLE
    deployment_end = (
        result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET
        + result_probe.PLAYER_DEPLOYMENT_COUNT * 4
    )
    turn_table_end = (
        result_probe.TURN_EVENT_TABLE
        + len(result_probe.TURN_EVENT_TABLE_BYTES)
    )
    header_start = builder.BATTLE_RESULT_HEADER_GLYPH_LIST
    header_end = (
        header_start + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2 + 2
    )
    digest = hashlib.sha256(diagnostic).hexdigest()
    return {
        "mode": "runtime_enemy_annihilation_then_stock_victory",
        "validation_source": "Japanese source ROM",
        "md_checksum": f"{checksum:04X}",
        "sha256": digest,
        "changed_offset_count": len(changed_offsets),
        "changed_offsets_within_declared_ranges": set(changed_offsets) <= allowed,
        "runtime_groups_marked_defeated": list(
            result_probe.ENEMY_ANNIHILATION_RUNTIME_GROUPS
        ),
        "all_player_deployments_unchanged": (
            candidate[deployment_start:deployment_end]
            == diagnostic[deployment_start:deployment_end]
        ),
        "all_thirteen_fixed_records_unchanged": (
            candidate[fixed_start:fixed_end]
            == diagnostic[fixed_start:fixed_end]
        ),
        "scheduled_turn_table_unchanged": (
            candidate[result_probe.TURN_EVENT_TABLE:turn_table_end]
            == diagnostic[result_probe.TURN_EVENT_TABLE:turn_table_end]
            == source[result_probe.TURN_EVENT_TABLE:turn_table_end]
        ),
        "scheduled_turn_handlers_unchanged": all(
            candidate[offset : offset + len(expected_bytes)]
            == diagnostic[offset : offset + len(expected_bytes)]
            == source[offset : offset + len(expected_bytes)]
            for turn, offset in result_probe.TURN_EVENT_HANDLERS.items()
            for expected_bytes in (result_probe.TURN_EVENT_HANDLER_BYTES[turn],)
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
) -> list[dict[str, object]]:
    root = CLASS_RUNS[profile]
    return [
        {
            "choice": index,
            **CLASS_CHOICE_CONTENT[index - 1],
            "capture": image_report(root / f"{stem}.png"),
            "gst": relative(root / f"states/{stem}.gst"),
            "gst_sha256": sha256_path(root / f"states/{stem}.gst"),
        }
        for index, stem in enumerate(CLASS_CHOICE_FILENAMES, start=1)
    ]


def battle_report(
    profile: str,
    candidate: bytes,
) -> dict[str, object]:
    expected = EXPECTED[profile]
    gray_root = GRAY_RUNS[profile]
    result_root = RESULT_RUNS[profile]
    acted_gst = gray_root / "states/acted_gray.gst"
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
            "active_capture": image_report(gray_root / "active_command.png"),
            "acted_capture": image_report(gray_root / "acted_gray.png"),
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
                "Natural Sherry level-up during the stock Scenario 6 "
                "civilian-safe victory aftermath"
            ),
            "status": "pass",
            "choices": class_change_report(profile),
        },
        "battle_result": {
            "run_root": relative(result_root),
            "capture": image_report(result_root / "battle_result.png"),
            "gst": relative(result_gst),
            "gst_sha256": sha256_path(result_gst),
            "selected_sherry_class": expected["selected_result_class"],
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
    review: dict[str, object],
) -> dict[str, object]:
    run = RUNS[profile]
    plan_path = run / "plan.json"
    evidence_path = run / "evidence.json"
    plan = read_json(plan_path)
    captured = read_json(evidence_path)
    rom_path = ROOT / plan["rom"]["path"]
    rom = rom_path.read_bytes()
    pairs = matrix.capture_pairs(run)
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
        "visible_fixed_records": plan["fixed_records"]["route"],
        "not_applicable_fixed_records": plan["fixed_records"]["not_applicable"],
        "expected_pair_count": 26,
        "actual_pair_count": len(pairs),
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
    choices = battle["class_change"]["choices"]
    result = battle["battle_result"]
    diagnostic = result["diagnostic_lineage"]
    checks = {
        "scenario/profile": (
            report["scenario"] == 6
            and f"/{profile}/s06/" in f"/{report['run']}/"
        ),
        "candidate matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
            and report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "selected matrix evidence exact": (
            captured["status"] == "captured_exact_unreviewed"
            and captured["acceptance_updated"] is False
            and captured["profile"] == profile
            and captured["scenario"] == 6
            and captured["capture_pairs"] == report["capture_pairs"]
        ),
        "all 26 pairs exact": (
            report["expected_pair_count"]
            == report["actual_pair_count"]
            == 26
            and all(row["byte_identical"] for row in report["capture_pairs"])
        ),
        "every fixed record accounted": (
            report["fixed_record_count"] == 13
            and report["visible_fixed_record_indexes"] == list(range(12))
            and [
                row["index"]
                for row in report["not_applicable_fixed_records"]
            ]
            == [12]
            and "(255,255)"
            in report["not_applicable_fixed_records"][0]["reason"]
        ),
        "human review complete": (
            report["status"] == "scenario_6_surface_pass"
            and all(
                value == "pass"
                for value in report["human_review"]["checks"].values()
            )
        ),
        "battle hashes locked": (
            gray["active_capture"]["sha256"] == expected["active_capture"]
            and gray["acted_capture"]["sha256"] == expected["acted_capture"]
            and gray["gst_sha256"] == expected["acted_gst"]
            and result["capture"]["sha256"] == expected["result_capture"]
            and result["gst_sha256"] == expected["result_gst"]
        ),
        "all dimensions full screen": (
            all(
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
        "acted Elwin Fighter": (
            gray["runtime_group_zero"]["class_id"] == 1
            and gray["runtime_group_zero"]["commander_id"] == 1
            and gray["runtime_group_zero"]["acted_flag"] == 1
            and gray["runtime_group_zero"]["hp"] == 10
            and [
                gray["runtime_group_zero"]["x"],
                gray["runtime_group_zero"]["y"],
            ]
            == [5, 26]
        ),
        "stock gray silhouette": (
            gray["source_record_offset"] == "0x05DBA8"
            and gray["source_silhouette_id"] == "0x001E"
            and gray["matches_stock_fighter_silhouette_expansion"]
            and gray["vram_sha256"] == EXPECTED_GRAY_VRAM_SHA256
            and gray["plane_references"] == gray_plane_expectation()
        ),
        "natural class change complete": (
            battle["class_change"]["status"] == "pass"
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
            diagnostic["changed_offsets_within_declared_ranges"]
            and diagnostic["runtime_groups_marked_defeated"]
            == list(range(9, 18))
            and diagnostic["all_player_deployments_unchanged"]
            and diagnostic["all_thirteen_fixed_records_unchanged"]
            and diagnostic["scheduled_turn_table_unchanged"]
            and diagnostic["scheduled_turn_handlers_unchanged"]
            and diagnostic["korean_battle_result_header_unchanged"]
            and diagnostic["matches_expected_checksum"]
            and diagnostic["matches_expected_sha256"]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} Scenario 6 evidence failed: " + ", ".join(failed)
        )


def build_report() -> dict[str, object]:
    review = read_json(REVIEW)
    profiles = {
        profile: run_report(profile, review["profiles"][profile])
        for profile in ("normal", "hard")
    }
    normal_choices = profiles["normal"]["battle_evidence"]["class_change"][
        "choices"
    ]
    hard_choices = profiles["hard"]["battle_evidence"]["class_change"][
        "choices"
    ]
    return {
        "schema_version": 1,
        "status": "scenario_6_complete_pass",
        "review": {
            "path": relative(REVIEW),
            "sha256": sha256_path(REVIEW),
            "reviewed_on": review["reviewed_on"],
            "scope": review["scope"],
            "allied_scope": review["allied_scope"],
            "fixed_record_scope": review["fixed_record_scope"],
            "class_change": review["class_change"],
            "not_applicable": review["not_applicable"],
            "acceptance_effect": review["acceptance_effect"],
        },
        "profiles": profiles,
        "cross_profile_identity": {
            "all_preparation_and_shop_frames_identical": all(
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
            "active_command_frame_identical": (
                profiles["normal"]["battle_evidence"]["gray_acted_sprite"][
                    "active_capture"
                ]["sha256"]
                == profiles["hard"]["battle_evidence"]["gray_acted_sprite"][
                    "active_capture"
                ]["sha256"]
            ),
            "gray_runtime_record_and_vram_identical": (
                profiles["normal"]["battle_evidence"]["gray_acted_sprite"][
                    "runtime_group_zero"
                ]
                == profiles["hard"]["battle_evidence"]["gray_acted_sprite"][
                    "runtime_group_zero"
                ]
                and profiles["normal"]["battle_evidence"]["gray_acted_sprite"][
                    "vram_sha256"
                ]
                == profiles["hard"]["battle_evidence"]["gray_acted_sprite"][
                    "vram_sha256"
                ]
            ),
            "all_three_class_change_frames_identical": (
                [
                    row["capture"]["sha256"] for row in normal_choices
                ]
                == [
                    row["capture"]["sha256"] for row in hard_choices
                ]
            ),
            "result_header_vram_identical": (
                profiles["normal"]["battle_evidence"]["battle_result"][
                    "header_vram_sha256"
                ]
                == profiles["hard"]["battle_evidence"]["battle_result"][
                    "header_vram_sha256"
                ]
            ),
        },
        "matrix_progress_after_acceptance": {
            "required_profile_scenario_runs": 54,
            "preparation_surface_runs_reviewed": 16,
            "battle_surface_runs_reviewed": 16,
            "fully_accepted_profile_scenario_runs": 16,
            "fully_accepted_scenarios": 8,
            "remaining_requirement": (
                "Complete every required surface in Scenarios 7, 8, 10, "
                "and 12 through 27 for both profiles."
            ),
        },
        "rejected_attempts": [
            {
                "surface": "gray and result launch",
                "run_ids": ["normal/gray01", "hard/gray01", "normal/result01"],
                "result": (
                    "The legacy battle-command preset ignores --scenario-number "
                    "and entered Scenario 1. These files are not Scenario 6 "
                    "evidence; gray02/result02 use the screen-detected selector."
                ),
            },
            {
                "profile": "normal",
                "surface": "class-change launch",
                "run_id": "result03",
                "result": (
                    "An intermittent selector miss entered new-game name entry. "
                    "The run is rejected; result05 is the accepted class run."
                ),
            },
            {
                "profile": "normal",
                "surface": "class-change navigation",
                "run_id": "result04",
                "result": (
                    "The fixed confirmation count selected the default class "
                    "before cycling choices. It confirms the root/result only; "
                    "result05 supplies all accepted choice PNGs and GSTs."
                ),
            },
            {
                "profile": "hard",
                "surface": "result class replay",
                "run_id": "result02/battle_result_lord",
                "result": (
                    "A later quicksave replacement reset on load. The original "
                    "Saint continuation battle_result.png/GST remains accepted; "
                    "the replay files are excluded."
                ),
            },
        ],
        "navigation_disclosures": [
            (
                "The accepted selector path is scenario-select, detect-prep, "
                "automatic arrangement, deploy, then detect-command. The "
                "legacy Scenario 1 battle-command preset is explicitly rejected."
            ),
            (
                "The result diagnostic preserves every deployment and all "
                "thirteen fixed records. Opening Start marks only runtime enemy "
                "groups 9 through 17 defeated; stock turn-end victory logic, "
                "dialogue, class change, and result rendering remain in control."
            ),
            (
                "Normal result evidence continues with Lord and hard result "
                "evidence with Saint, so the final sprite grids legitimately "
                "differ. Both retain identical 전과보고 VRAM and intact full "
                "screen content; all three choice frames are byte-identical."
            ),
            (
                "Fixed record 12 is explicitly N/A in preparation because the "
                "source record is hidden at coordinates (255,255)."
            ),
        ],
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_6_complete_pass":
        raise ValueError("Scenario 6 report must record its complete pass")
    progress = report["matrix_progress_after_acceptance"]
    if progress["fully_accepted_profile_scenario_runs"] != 16:
        raise ValueError("Eight accepted scenarios must yield sixteen runs")
    if progress["fully_accepted_scenarios"] != 8:
        raise ValueError("Eight scenarios must be accepted")
    if not all(report["cross_profile_identity"].values()):
        raise ValueError("Scenario 6 cross-profile invariants must all pass")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed normal/hard Scenario 6 preparation, shop, every "
            "visible allied/NPC/enemy record, gray acted-sprite, natural class "
            "change, and result evidence."
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
