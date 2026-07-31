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
from tools import build_scenario7_clear_probe_rom as result_probe
from tools import run_preparation_surface_matrix as matrix
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout
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
        / f"captures/run/preparation_surface_matrix/{profile}/s07/current01"
    )
    for profile in ("normal", "hard")
}
GRAY_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_battle_surface/{profile}/s07/gray01"
    )
    for profile in ("normal", "hard")
}
RESULT_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_battle_surface/{profile}/s07/result01"
    )
    for profile in ("normal", "hard")
}
REVIEW = ROOT / "localization/preparation_surface_scenario_07_review.json"
OUTPUT = ROOT / "localization/preparation_surface_scenario_07.json"
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
    "c5d6c1de3e29a2127c4a8600e0a636ac0905c9f53f4c01a2b7fe58f990f56ba9",
    "15979a50e70afe54001034e37ad2b71bca983d3845c1a778e1f748bf389b34e7",
    "57d4a5e914ba98310717e9b20dd292bd5d7971fbc2d1e0a70385bf637c4d0fb5",
)
EXPECTED = {
    "normal": {
        "active_capture": (
            "8645189263e1677c2e13b7c22b2f68df4832620fcc2e0691670b27e5ea0cfbee"
        ),
        "acted_capture": (
            "cd001ad62ab4687d74faeda1606a4b82b6a2f17842705cd92f7d22cea9dbd77d"
        ),
        "acted_gst": (
            "7b2490295db8408face05326f9de5484733099a97ea8c8c94916569acb24971d"
        ),
        "class_choice_gsts": (
            "c1f0ded5e4dd88cc86f1e51e59225612499e3e0233b788596e6c2a50ca1d439b",
            "96c6addc036f11fb6f024d8579daa042175927d95db0865bea949c38b34cc231",
            "d793905836bb3aa5c9ddd59e23fed6ca71d28a4fd11bb18d151a34a108823ce8",
        ),
        "result_capture": (
            "cf53872a75ca3eb2d583a1f4e0085b430ec5cbaaa79c808f211ec195acc6383d"
        ),
        "result_gst": (
            "e2fb131c6cad9cc8e22d839551cc68b17e0ca35a7f441eed4ab093c27bafba92"
        ),
        "result_probe_checksum": "D145",
        "result_probe_sha256": (
            "11340bd58e362475ebacc22ad99dd53a331582707ab73afeb026bed587acd123"
        ),
        "selected_result_class": "세인트",
    },
    "hard": {
        "active_capture": (
            "8645189263e1677c2e13b7c22b2f68df4832620fcc2e0691670b27e5ea0cfbee"
        ),
        "acted_capture": (
            "5b85829721606ec2c35424cbb905b19f0d266f2b3accf17e86aff6ba9ef6c9ee"
        ),
        "acted_gst": (
            "d73086edf9e15e3b6337a17651de5a8f0afc715cc42a5c7f60065f851eb8f3fe"
        ),
        "class_choice_gsts": (
            "30103a0ee5c435a4411e1ad524eb287055684ecb671d16d7098469faed573bb9",
            "d730a026c50aebe4a7d2ed07426c51bdcef2cbbda3bdd6f20ce727eb17dffe78",
            "02819c763ecb84c41e279d33e0029b186f9fed9536e578897b8910f911a629a9",
        ),
        "result_capture": (
            "ee2f5672df941b51ec32bfb4bb3057570d62ba359d16752c68f766f6fe7e6f72"
        ),
        "result_gst": (
            "cf9b604a271c72f4776170f2d24280ff47b1aabc923d1d00f30fae331edc2d31"
        ),
        "result_probe_checksum": "3426",
        "result_probe_sha256": (
            "eac2e200843e2f866b06eecbfb45d68b84f71f4822e836f5f1af713b188a91b4"
        ),
        "selected_result_class": "로드",
    },
}


def gray_plane_expectation() -> list[dict[str, object]]:
    coordinates = ((20, 11), (20, 12), (21, 11), (21, 12))
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
    checksum = result_probe.patch_probe(diagnostic, source)
    changed_offsets = {
        offset
        for offset, (before, after) in enumerate(zip(candidate, diagnostic))
        if before != after
    }
    ginam = result_probe.GINAM_RECORD_OFFSET
    allowed = {0x18E, 0x18F}
    allowed.update(
        {
            ginam + FIELD_OFFSETS[field]
            for field in ("at", "df", "x", "y")
        }
    )
    allowed.update(
        range(
            ginam + FIELD_OFFSETS["mercenaries"],
            ginam + FIELD_OFFSETS["mercenaries"] + 6,
        )
    )
    layout = scenario_layout(candidate, result_probe.SCENARIO_NUMBER)
    deployment_start = result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET
    deployment_end = (
        deployment_start + len(result_probe.SOURCE_PLAYER_DEPLOYMENTS)
    )
    fixed_ranges = [
        (
            layout.records_offset + index * FIXED_RECORD_SIZE,
            layout.records_offset + (index + 1) * FIXED_RECORD_SIZE,
        )
        for index in range(layout.record_count)
        if index != result_probe.GINAM_RECORD_INDEX
    ]
    event_end = (
        result_probe.RESIDENT_DEATH_EVENT_TABLE
        + len(result_probe.SOURCE_RESIDENT_DEATH_EVENTS)
    )
    turn_end = result_probe.TURN_EVENT_TABLE + len(
        result_probe.TURN_EVENT_TABLE_BYTES
    )
    header_start = builder.BATTLE_RESULT_HEADER_GLYPH_LIST
    header_end = (
        header_start + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2 + 2
    )
    digest = hashlib.sha256(diagnostic).hexdigest()
    return {
        "mode": "source_record_isolated_real_attack_then_stock_victory",
        "validation_source": "Japanese source ROM",
        "md_checksum": f"{checksum:04X}",
        "sha256": digest,
        "changed_offset_count": len(changed_offsets),
        "changed_offsets_within_declared_ranges": changed_offsets <= allowed,
        "ginam_source_coordinates": [
            result_probe.SOURCE_GINAM_X,
            result_probe.SOURCE_GINAM_Y,
        ],
        "ginam_probe_coordinates": [
            result_probe.PROBE_GINAM_X,
            result_probe.PROBE_GINAM_Y,
        ],
        "ginam_probe_at_df": [
            result_probe.PROBE_GINAM_AT,
            result_probe.PROBE_GINAM_DF,
        ],
        "ginam_probe_mercenaries_removed": (
            diagnostic[
                ginam + FIELD_OFFSETS["mercenaries"] :
                ginam + FIELD_OFFSETS["mercenaries"] + 6
            ]
            == b"\xFF" * 6
        ),
        "all_player_deployments_unchanged": (
            candidate[deployment_start:deployment_end]
            == diagnostic[deployment_start:deployment_end]
            == source[deployment_start:deployment_end]
        ),
        "all_non_ginam_fixed_records_unchanged": all(
            candidate[start:end]
            == diagnostic[start:end]
            == source[start:end]
            for start, end in fixed_ranges
        ),
        "resident_death_events_unchanged": (
            candidate[result_probe.RESIDENT_DEATH_EVENT_TABLE:event_end]
            == diagnostic[result_probe.RESIDENT_DEATH_EVENT_TABLE:event_end]
            == source[result_probe.RESIDENT_DEATH_EVENT_TABLE:event_end]
        ),
        "scheduled_turn_table_unchanged": (
            candidate[result_probe.TURN_EVENT_TABLE:turn_end]
            == diagnostic[result_probe.TURN_EVENT_TABLE:turn_end]
            == source[result_probe.TURN_EVENT_TABLE:turn_end]
        ),
        "scheduled_turn_handlers_unchanged": all(
            candidate[offset : offset + len(expected_bytes)]
            == diagnostic[offset : offset + len(expected_bytes)]
            == source[offset : offset + len(expected_bytes)]
            for handler, offset in result_probe.TURN_EVENT_HANDLERS.items()
            for expected_bytes in (
                result_probe.TURN_EVENT_HANDLER_BYTES[handler],
            )
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


def class_change_report(profile: str) -> list[dict[str, object]]:
    root = RESULT_RUNS[profile]
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
                "Natural Sherry level-up during the stock Scenario 7 "
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
        "expected_pair_count": 27,
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
    expected_visible = [0, 1, 2, 4, 5, 6, 7, 8, 9, 10]
    checks = {
        "scenario/profile": (
            report["scenario"] == 7
            and f"/{profile}/s07/" in f"/{report['run']}/"
        ),
        "candidate matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
            and report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "selected matrix evidence exact": (
            captured["status"] == "captured_exact_unreviewed"
            and captured["acceptance_updated"] is False
            and captured["profile"] == profile
            and captured["scenario"] == 7
            and captured["capture_pairs"] == report["capture_pairs"]
        ),
        "all 27 pairs exact": (
            report["expected_pair_count"]
            == report["actual_pair_count"]
            == 27
            and all(row["byte_identical"] for row in report["capture_pairs"])
        ),
        "every fixed record accounted": (
            report["fixed_record_count"] == 12
            and report["visible_fixed_record_indexes"] == expected_visible
            and [
                row["index"]
                for row in report["not_applicable_fixed_records"]
            ]
            == [3, 11]
            and all(
                "(255,255)" in row["reason"]
                for row in report["not_applicable_fixed_records"]
            )
        ),
        "human review complete": (
            report["status"] == "scenario_7_surface_pass"
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
            == [8, 20]
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
            and diagnostic["ginam_probe_mercenaries_removed"]
            and diagnostic["all_player_deployments_unchanged"]
            and diagnostic["all_non_ginam_fixed_records_unchanged"]
            and diagnostic["resident_death_events_unchanged"]
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
            f"{profile} Scenario 7 evidence failed: " + ", ".join(failed)
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
        "status": "scenario_7_complete_pass",
        "review": {
            "path": relative(REVIEW),
            "sha256": sha256_path(REVIEW),
            "reviewed_on": review["reviewed_on"],
            "scope": review["scope"],
            "allied_scope": review["allied_scope"],
            "fixed_record_scope": review["fixed_record_scope"],
            "shop_scope": review["shop_scope"],
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
                [row["capture"]["sha256"] for row in normal_choices]
                == [row["capture"]["sha256"] for row in hard_choices]
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
            "preparation_surface_runs_reviewed": 18,
            "battle_surface_runs_reviewed": 18,
            "fully_accepted_profile_scenario_runs": 18,
            "fully_accepted_scenarios": 9,
            "remaining_requirement": (
                "Complete every required surface in Scenarios 8, 10, "
                "and 12 through 27 for both profiles."
            ),
        },
        "rejected_attempts": [
            {
                "profile": "normal",
                "surface": "battle command detection",
                "result": (
                    "The first detector invocation omitted --open-map-command "
                    "and stopped on the Scenario 7 banner without sending any "
                    "confirmation. It changed no game state and its detector "
                    "frames are excluded; the accepted run resumed with the "
                    "map-aware detector."
                ),
            },
            {
                "profile": "normal",
                "surface": "attack target navigation",
                "result": (
                    "The first target attempt left the cursor on Elwin and "
                    "returned to his command menu. It is excluded. The accepted "
                    "attempt explicitly moved Up to Ginam before confirming."
                ),
            },
        ],
        "navigation_disclosures": [
            (
                "The accepted selector path is scenario-select, detect-prep, "
                "automatic arrangement, deploy, then map-aware detect-command. "
                "All X11 input was sent directly to the isolated :104 window."
            ),
            (
                "The result diagnostic changes only Ginam's source AT/DF, six "
                "mercenary slots, and coordinates, placing him directly above "
                "the stock Elwin deployment. A real Elwin Attack then enters "
                "the unchanged civilian-safe stock victory aftermath."
            ),
            (
                "Normal result evidence continues with Saint and hard result "
                "evidence with Lord, so the final sprite grids legitimately "
                "differ. Both retain identical 전과보고 VRAM and intact full "
                "screen content; all three choice frames are byte-identical."
            ),
            (
                "Fixed records 3 and 11 are explicitly N/A in preparation "
                "because both source records are hidden at coordinates "
                "(255,255)."
            ),
        ],
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_7_complete_pass":
        raise ValueError("Scenario 7 report must record its complete pass")
    progress = report["matrix_progress_after_acceptance"]
    if progress["fully_accepted_profile_scenario_runs"] != 18:
        raise ValueError("Nine accepted scenarios must yield eighteen runs")
    if progress["fully_accepted_scenarios"] != 9:
        raise ValueError("Nine scenarios must be accepted")
    if not all(report["cross_profile_identity"].values()):
        raise ValueError("Scenario 7 cross-profile invariants must all pass")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed normal/hard Scenario 7 preparation, shop, every "
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
            raise FileNotFoundError(
                f"checked report does not exist: {args.output}"
            )
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
