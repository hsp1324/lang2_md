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
from tools import build_scenario11_clear_probe_rom as result_probe
from tools import run_preparation_surface_matrix as matrix
from tools.scenario_data import (
    FIELD_OFFSETS,
    FIXED_RECORD_SIZE,
    SIDE_OFFSET,
    scenario_layout,
)
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
        / f"captures/run/preparation_surface_matrix/{profile}/s11/current01"
    )
    for profile in ("normal", "hard")
}
GRAY_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_battle_surface/{profile}/s11/gray01"
    )
    for profile in ("normal", "hard")
}
RESULT_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_result_surface/{profile}/s11/result01"
    )
    for profile in ("normal", "hard")
}
REVIEW = ROOT / "localization/preparation_surface_scenario_11_review.json"
OUTPUT = ROOT / "localization/preparation_surface_scenario_11.json"
JAPANESE_ROM = ROOT / builder.IN_ROM
SOURCE_RESULT_STATE = (
    ROOT
    / "captures/runtime/s11-safe-jessica-d091/.local/share/blastem"
    / "Langrisser II (Scenario 11 Safe Jessica Clear Probe)/quicksave.gst"
)
SOURCE_RESULT_ROM = (
    ROOT
    / "roms/builds/Langrisser II (Scenario 11 Safe Jessica Clear Probe).md"
)
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
EXPECTED_SOURCE_RESULT_STATE_SHA256 = (
    "5a8e1f6e777e7119a3fe22efb37e54cf019d6c0da0456a46ddc65d5ac99c1d13"
)
EXPECTED_SOURCE_RESULT_ROM_SHA256 = (
    "51b448d58be8bd8ab02bf6b5fac5bc4b493abced62d306ebf9e7ef9b092874be"
)
EXPECTED = {
    "normal": {
        "plan": (
            "ea2e0a6614902aaa84ef049fff964aa6df678fc2a6986b7ff0efb1e49729417c"
        ),
        "evidence": (
            "6196f55238bee99e19beba92aad8ce6af122165f7a79a93ddc179f401e416503"
        ),
        "active_capture": (
            "5d59d52c49f12e9acea14923ce6bbb25545eeaf27b6fce5c5b9f5fc79f0e97b4"
        ),
        "acted_capture": (
            "846bba8a2c206b4d83a6c58fa2d91a3994e5349d14c1a1b8bb1d887489706cb4"
        ),
        "acted_gst": (
            "24404ac5876947ea7e8c1d2b6ce500be1d175d6510a4accba54789577e0d4e8f"
        ),
        "objective_defeat": (
            "c62bdbccf3a25547fc0d72465ab5d6ce63a5fd636d5f8f25668ccccabee6af8a"
        ),
        "result_capture": (
            "e70bdff4d570b92341fa72805fd4c2e9eeb466de74778bece32fa9b72c669832"
        ),
        "result_gst": (
            "5ce5bf29d67c8afa790cf51ffd15eb44bde1b7d134172fe515c895f2f90bf6db"
        ),
        "result_probe_checksum": "1373",
        "result_probe_sha256": (
            "6293b7fa11b980a64a7250e43b672b259c83edfaf27fe9f9f193e9415120b731"
        ),
    },
    "hard": {
        "plan": (
            "f1ee954dcd3c91f03e353a9963673e669c2b0a0b029bdb879c09278d767d26bc"
        ),
        "evidence": (
            "16e59552336ffbc73094381d2a0e2b2896537b8ea75e1c0c17c947c14b400b3e"
        ),
        "active_capture": (
            "5d59d52c49f12e9acea14923ce6bbb25545eeaf27b6fce5c5b9f5fc79f0e97b4"
        ),
        "acted_capture": (
            "cf8ba20a68cd1116d6e99db0c976a36445388f34ca4af98649e7eacec66ff635"
        ),
        "acted_gst": (
            "ce1f227c70fff579388f5313061f45382eec95baf3464c6b52a889d77c6fe2d5"
        ),
        "objective_defeat": (
            "58450e74026cb59f633637ec212e6f3be867437622e336eea6c93fa20088e4c3"
        ),
        "result_capture": (
            "e70bdff4d570b92341fa72805fd4c2e9eeb466de74778bece32fa9b72c669832"
        ),
        "result_gst": (
            "29db3d421410ef715986bb1eedbbdec6d57d9f97c2c883791aaefe388658f937"
        ),
        "result_probe_checksum": "7654",
        "result_probe_sha256": (
            "53ce6238a692c9463dcb8768e050f6cee0ffcc53f3e8b2c5834625874ca52476"
        ),
    },
}


def gray_plane_expectation() -> list[dict[str, object]]:
    coordinates = ((17, 14), (17, 15), (18, 14), (18, 15))
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
        safe_clear_layout=True,
        safe_jessica=True,
    )
    changed_offsets = {
        offset
        for offset, (before, after) in enumerate(zip(candidate, diagnostic))
        if before != after
    }
    layout = scenario_layout(source, result_probe.SCENARIO_NUMBER)
    allowed = {0x18E, 0x18F}
    allowed.update(
        range(
            result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET,
            result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET
            + result_probe.PLAYER_DEPLOYMENT_COUNT * 4,
        )
    )
    for index in range(
        result_probe.FIRST_ENEMY_RECORD_INDEX,
        result_probe.LAST_ENEMY_RECORD_INDEX + 1,
    ):
        base = layout.records_offset + index * FIXED_RECORD_SIZE
        allowed.update(
            {
                base + FIELD_OFFSETS["level"],
                base + FIELD_OFFSETS["at"],
                base + FIELD_OFFSETS["df"],
                base + FIELD_OFFSETS["class_id"],
                *(
                    base + FIELD_OFFSETS["mercenaries"] + slot
                    for slot in range(6)
                ),
            }
        )
        if index in result_probe.SAFE_CLEAR_VISIBLE_POSITIONS:
            allowed.update(
                {
                    base + FIELD_OFFSETS["x"],
                    base + FIELD_OFFSETS["y"],
                }
            )
    jessica = layout.records_offset + result_probe.JESSICA_RECORD_INDEX * FIXED_RECORD_SIZE
    allowed.update(
        {
            jessica + FIELD_OFFSETS["x"],
            jessica + FIELD_OFFSETS["y"],
        }
    )
    record_start = layout.records_offset
    record_end = record_start + layout.record_count * FIXED_RECORD_SIZE
    header_start = builder.BATTLE_RESULT_HEADER_GLYPH_LIST
    header_end = (
        header_start + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2 + 2
    )
    digest = hashlib.sha256(diagnostic).hexdigest()
    identity_offsets = (SIDE_OFFSET, FIELD_OFFSETS["name_id"])
    return {
        "mode": "safe_clear_layout_plus_stock_final_battle",
        "validation_source": "Japanese source ROM",
        "md_checksum": f"{checksum:04X}",
        "sha256": digest,
        "changed_offset_count": len(changed_offsets),
        "changed_offsets_within_declared_diagnostic_fields": (
            changed_offsets <= allowed
        ),
        "input_all_fixed_records_match_japanese_source": (
            candidate[record_start:record_end] == source[record_start:record_end]
        ),
        "all_fixed_side_and_name_ids_preserved": all(
            diagnostic[record_start + index * FIXED_RECORD_SIZE + field]
            == candidate[record_start + index * FIXED_RECORD_SIZE + field]
            for index in range(layout.record_count)
            for field in identity_offsets
        ),
        "jessica_class_and_mercenaries_preserved": (
            diagnostic[
                jessica + FIELD_OFFSETS["class_id"] :
                jessica + FIXED_RECORD_SIZE
            ]
            == candidate[
                jessica + FIELD_OFFSETS["class_id"] :
                jessica + FIXED_RECORD_SIZE
            ]
        ),
        "hidden_reinforcement_coordinates_preserved": (
            diagnostic[
                record_start
                + result_probe.LAST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
                + FIELD_OFFSETS["x"] :
                record_start
                + result_probe.LAST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
                + FIELD_OFFSETS["y"]
                + 1
            ]
            == b"\xFF\xFF"
        ),
        "all_event_bytes_unchanged_by_declared_delta_confinement": (
            changed_offsets <= allowed
        ),
        "korean_battle_result_header_unchanged": (
            candidate[header_start:header_end]
            == diagnostic[header_start:header_end]
        ),
        "source_result_state": {
            "path": relative(SOURCE_RESULT_STATE),
            "sha256": sha256_path(SOURCE_RESULT_STATE),
            "state_modified_before_current_replay": False,
            "source_probe_rom": relative(SOURCE_RESULT_ROM),
            "source_probe_rom_sha256": sha256_path(SOURCE_RESULT_ROM),
        },
        "current_replay": (
            "The unchanged pre-final-battle GST was loaded under this rebuilt "
            "current-candidate diagnostic. Sherry then used a real stock "
            "normal attack against runtime group 16, after which the stock "
            "defeat/victory/result path ran."
        ),
        "matches_expected_checksum": (
            f"{checksum:04X}" == expected["result_probe_checksum"]
        ),
        "matches_expected_sha256": digest == expected["result_probe_sha256"],
    }


def result_report(
    profile: str,
    candidate: bytes,
) -> dict[str, object]:
    expected = EXPECTED[profile]
    root = RESULT_RUNS[profile]
    result = root / "final_report.png"
    result_gst = root / "final_report.gst"
    state = load_gst(result_gst)
    header_payload = state.vram[
        RESULT_HEADER_VRAM_START :
        RESULT_HEADER_VRAM_START + RESULT_HEADER_VRAM_BYTES
    ]
    dialogue = [
        image_report(root / f"victory_dialogue_{index:02d}.png")
        for index in range(1, 19)
    ]
    return {
        "run_root": relative(root),
        "objective_defeat": image_report(root / "objective_defeat.png"),
        "victory_dialogue": dialogue,
        "victory_dialogue_count": len(dialogue),
        "capture": image_report(result),
        "gst": relative(result_gst),
        "gst_sha256": sha256_path(result_gst),
        "header_text": builder.DIRECT_WORD_SEQUENCE_PATCHES[
            builder.BATTLE_RESULT_HEADER_GLYPH_LIST
        ][1],
        "point_text": "3770P",
        "header_vram_range": "0xA000..0xA1FF",
        "header_vram_sha256": hashlib.sha256(header_payload).hexdigest(),
        "header_plane_cells": result_header_plane_cells(state),
        "class_change": {
            "status": "not_applicable",
            "reason": (
                "The retained pre-final-battle state has already progressed "
                "all six allied commanders beyond a class-choice boundary; "
                "the final stock attack exposes no class selection."
            ),
        },
        "diagnostic_lineage": diagnostic_report(candidate, expected),
    }


def battle_report(
    profile: str,
    candidate: bytes,
) -> dict[str, object]:
    expected = EXPECTED[profile]
    gray_root = GRAY_RUNS[profile]
    active = gray_root / "active_command.png"
    acted = gray_root / "acted_gray.png"
    acted_gst = gray_root / "acted_gray.gst"
    acted_state = load_gst(acted_gst)
    source_record, source_sprite_id, stock_gray = expected_gray_payload()
    gray_payload = acted_state.vram[
        GRAY_VRAM_START : GRAY_VRAM_START + GRAY_VRAM_BYTES
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
        "battle_result": result_report(profile, candidate),
        "expected_hashes": {
            "active_capture": expected["active_capture"],
            "acted_capture": expected["acted_capture"],
            "acted_gst": expected["acted_gst"],
            "objective_defeat": expected["objective_defeat"],
            "result_capture": expected["result_capture"],
            "result_gst": expected["result_gst"],
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
        "visible_fixed_records": plan["fixed_records"]["route"],
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
    result = battle["battle_result"]
    diagnostic = result["diagnostic_lineage"]
    checks = {
        "scenario/profile": (
            report["scenario"] == 11
            and f"/{profile}/s11/" in f"/{report['run']}/"
        ),
        "candidate matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
            and report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "selected evidence is exact": (
            captured["status"] == "captured_exact_unreviewed"
            and captured["acceptance_updated"] is False
            and captured["profile"] == profile
            and captured["scenario"] == 11
            and captured["capture_pairs"] == report["capture_pairs"]
            and report["plan"]["sha256"] == expected["plan"]
            and report["captured_evidence"]["sha256"] == expected["evidence"]
        ),
        "all 27 pairs exact": (
            report["expected_pair_count"]
            == report["actual_pair_count"]
            == 27
            and all(row["byte_identical"] for row in report["capture_pairs"])
        ),
        "all fixed records accounted": (
            report["fixed_record_count"] == 11
            and report["visible_fixed_record_indexes"] == list(range(10))
            and report["distinct_pre_fixed_detail_count"] == 10
            and [
                row["index"]
                for row in report["not_applicable_fixed_records"]
            ]
            == [10]
            and "(255,255)"
            in report["not_applicable_fixed_records"][0]["reason"]
        ),
        "all sides represented": (
            report["visible_fixed_records"][0]["side_id"] == "0x03"
            and all(
                row["side_id"] == "0x04"
                for row in report["visible_fixed_records"][1:]
            )
        ),
        "review and dimensions": (
            report["status"] == "scenario_11_surface_pass"
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
            and result["objective_defeat"]["dimensions"] == [320, 240]
            and result["capture"]["dimensions"] == [320, 240]
            and all(
                capture["dimensions"] == [320, 240]
                for capture in result["victory_dialogue"]
            )
        ),
        "battle hashes locked": (
            gray["active_capture"]["sha256"] == expected["active_capture"]
            and gray["acted_capture"]["sha256"] == expected["acted_capture"]
            and gray["gst_sha256"] == expected["acted_gst"]
            and result["objective_defeat"]["sha256"]
            == expected["objective_defeat"]
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
            == [14, 11]
        ),
        "stock gray silhouette": (
            gray["source_record_offset"] == "0x05DBA8"
            and gray["source_silhouette_id"] == "0x001E"
            and gray["matches_stock_fighter_silhouette_expansion"]
            and gray["vram_sha256"] == EXPECTED_GRAY_VRAM_SHA256
            and gray["plane_references"] == gray_plane_expectation()
        ),
        "result complete": (
            result["victory_dialogue_count"] == 18
            and result["header_text"] == "전과보고"
            and result["point_text"] == "3770P"
            and result["header_vram_sha256"]
            == EXPECTED_RESULT_HEADER_VRAM_SHA256
            and all(cell["matches"] for cell in result["header_plane_cells"])
            and result["class_change"]["status"] == "not_applicable"
        ),
        "diagnostic narrow and source-owned": (
            diagnostic["changed_offsets_within_declared_diagnostic_fields"]
            and diagnostic["input_all_fixed_records_match_japanese_source"]
            and diagnostic["all_fixed_side_and_name_ids_preserved"]
            and diagnostic["jessica_class_and_mercenaries_preserved"]
            and diagnostic["hidden_reinforcement_coordinates_preserved"]
            and diagnostic[
                "all_event_bytes_unchanged_by_declared_delta_confinement"
            ]
            and diagnostic["korean_battle_result_header_unchanged"]
            and diagnostic["matches_expected_checksum"]
            and diagnostic["matches_expected_sha256"]
            and diagnostic["source_result_state"]["sha256"]
            == EXPECTED_SOURCE_RESULT_STATE_SHA256
            and diagnostic["source_result_state"]["source_probe_rom_sha256"]
            == EXPECTED_SOURCE_RESULT_ROM_SHA256
            and diagnostic["source_result_state"][
                "state_modified_before_current_replay"
            ]
            is False
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} Scenario 11 evidence failed: " + ", ".join(failed)
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
    normal_result = profiles["normal"]["battle_evidence"]["battle_result"]
    hard_result = profiles["hard"]["battle_evidence"]["battle_result"]
    return {
        "schema_version": 1,
        "status": "scenario_11_complete_pass",
        "review": {
            "path": relative(REVIEW),
            "sha256": sha256_path(REVIEW),
            "reviewed_on": review["reviewed_on"],
            "scope": review["scope"],
            "reported_failures_closed": review["reported_failures_closed"],
            "class_change": review["class_change"],
            "result_lineage": review["result_lineage"],
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
            "active_command_frame_identical": (
                profiles["normal"]["battle_evidence"]["gray_acted_sprite"][
                    "active_capture"
                ]["sha256"]
                == profiles["hard"]["battle_evidence"]["gray_acted_sprite"][
                    "active_capture"
                ]["sha256"]
            ),
            "gray_vram_payload_identical": (
                profiles["normal"]["battle_evidence"]["gray_acted_sprite"][
                    "vram_sha256"
                ]
                == profiles["hard"]["battle_evidence"]["gray_acted_sprite"][
                    "vram_sha256"
                ]
            ),
            "battle_result_frame_identical": (
                normal_result["capture"]["sha256"]
                == hard_result["capture"]["sha256"]
            ),
        },
        "matrix_progress_after_acceptance": {
            "required_profile_scenario_runs": 54,
            "preparation_surface_runs_reviewed": 14,
            "battle_surface_runs_reviewed": 14,
            "fully_accepted_profile_scenario_runs": 14,
            "fully_accepted_scenarios": 7,
            "remaining_requirement": (
                "Complete every required surface in Scenarios 6 through 8, "
                "10, and 12 through 27 for both profiles."
            ),
        },
        "rejected_attempts": [
            {
                "surface": "result shortcut",
                "result": (
                    "Runtime wrappers that directly marked enemy groups "
                    "defeated or changed Egbert HP/position reset before a "
                    "valid stock battle outcome. They were rejected and no "
                    "such code remains in the source."
                ),
            },
            {
                "surface": "result state mutation",
                "result": (
                    "Directly edited GST variants were rejected because the "
                    "runtime battle bookkeeping was inconsistent. Accepted "
                    "result evidence uses an unchanged stock pre-final-battle "
                    "GST and a real normal attack."
                ),
            },
        ],
        "navigation_disclosures": [
            (
                "All six allied commanders, all ten visible fixed records "
                "(one NPC and nine enemies), and every hiring/detail surface "
                "were captured before and after the same-run shop visit."
            ),
            (
                "Fixed record 10 is the only preparation-time N/A record and "
                "is source-locked at (255,255). It later appears as the stock "
                "final reinforcement and is defeated by the accepted real "
                "Sherry attack."
            ),
            (
                "The result continuation begins from the unchanged D091 "
                "pre-final-battle GST produced by the previously verified "
                "stock turn-event route, then runs under freshly rebuilt "
                "normal and hard diagnostics of the current candidates."
            ),
        ],
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_11_complete_pass":
        raise ValueError("Scenario 11 report must record its complete pass")
    progress = report["matrix_progress_after_acceptance"]
    if progress["fully_accepted_profile_scenario_runs"] != 14:
        raise ValueError("Seven accepted scenarios must yield fourteen runs")
    if progress["fully_accepted_scenarios"] != 7:
        raise ValueError("Scenarios 1 through 5, 9, and 11 must be accepted")
    if not all(report["cross_profile_identity"].values()):
        raise ValueError(
            "Scenario 11 preparation, gray payload, and result identity failed"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed normal/hard Scenario 11 preparation, shop, gray "
            "acted-sprite, all allied/NPC/enemy fixed records, stock final "
            "battle, victory dialogue, and result evidence."
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
