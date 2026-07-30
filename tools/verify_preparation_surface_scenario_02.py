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
from tools import build_scenario2_escape_probe_rom as result_probe
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
        ROOT / "captures/run/preparation_surface_matrix/normal/s02/s02a02"
    ),
    "hard": (
        ROOT / "captures/run/preparation_surface_matrix/hard/s02/s02a01"
    ),
}
BATTLE_RUNS = {
    profile: (
        ROOT / f"captures/run/preparation_battle_surface/{profile}/s02"
    )
    for profile in ("normal", "hard")
}
REVIEW = ROOT / "localization/preparation_surface_scenario_02_review.json"
OUTPUT = ROOT / "localization/preparation_surface_scenario_02.json"
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
            "27f28ad2d02b5090f0d1b062eeb5f06e2fb8be5da6c2e8a1613d115025c4ff9c"
        ),
        "acted_capture": (
            "40c11e8e421787e43798e8dc842ac2558217e77b7a0e40721942866429d98fb0"
        ),
        "acted_gst": (
            "5988f7cc4f1dbf54d7ce625424a541c0f3e9fe2fbc45a96b873db702c2470de5"
        ),
        "acted_xy": [5, 17],
        "plane_origin": [17, 8],
        "result_capture": (
            "0d14f98e924d76d441a99e1710b032a50384b8630fc988ef633f7fb3229a5fbe"
        ),
        "result_gst": (
            "97df1aa64ee5d4a3dc9837af5007fad64a617d2d9d313aaa875bac13ed2d4a54"
        ),
        "result_probe_checksum": "5C26",
        "result_probe_sha256": (
            "8c746b9617f5d3f2d8b86be7e8ef7871f4828df98c1fe5151f9d734599072a73"
        ),
    },
    "hard": {
        "active_capture": (
            "dfd7b07597eb0fb153d0e42815e0def108e446d5405eac085f2720183b1ad997"
        ),
        "acted_capture": (
            "60ea3983a06c191ed6ed0f32c422efc3233dec6649496e846fcfc90ba5305f2f"
        ),
        "acted_gst": (
            "7c9d1f87e10d5c98141f8e310a62d915973650e72d8d0659637d682d259f8473"
        ),
        "acted_xy": [5, 18],
        "plane_origin": [17, 11],
        "result_capture": (
            "d06c9237354a6cfd7b8cd7ef0fcd23569722fb7861abf748f28bff49e4929f6a"
        ),
        "result_gst": (
            "f28bff469c4b75b2d80ef9ea8dfb2bec9a21a838c3a15acdcbbd11548d130175"
        ),
        "result_probe_checksum": "A564",
        "result_probe_sha256": (
            "ecc89fe092546f3bbf786ee3532d66d9bec5922574a101e3e290a449a2060e79"
        ),
    },
}


def event_ranges() -> list[tuple[int, int]]:
    return [
        (offset, offset + len(payload))
        for offset, payload in (
            (
                result_probe.PROTAGONIST_DEATH_TRIGGER,
                result_probe.PROTAGONIST_DEATH_TRIGGER_BYTES,
            ),
            (
                result_probe.PROTAGONIST_DEATH_HANDLER,
                result_probe.PROTAGONIST_DEATH_HANDLER_BYTES,
            ),
            (
                result_probe.LIANA_DEATH_TRIGGER,
                result_probe.LIANA_DEATH_TRIGGER_BYTES,
            ),
            (
                result_probe.LIANA_DEATH_HANDLER,
                result_probe.LIANA_DEATH_HANDLER_BYTES,
            ),
            (
                result_probe.ENEMY_ANNIHILATION_TRIGGER,
                result_probe.ENEMY_ANNIHILATION_TRIGGER_BYTES,
            ),
            (
                result_probe.ENEMY_ANNIHILATION_HANDLER,
                result_probe.ENEMY_ANNIHILATION_HANDLER_BYTES,
            ),
        )
    ]


def unchanged_ranges(
    before: bytes,
    after: bytes,
    ranges: list[tuple[int, int]],
) -> bool:
    return all(before[start:end] == after[start:end] for start, end in ranges)


def diagnostic_report(
    candidate: bytes,
    expected: dict[str, object],
) -> dict[str, object]:
    diagnostic = bytearray(candidate)
    checksum = result_probe.patch_probe(
        diagnostic,
        candidate,
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
    deployment_start = result_probe.DEPLOYMENT_TABLE
    deployment_end = (
        result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET
        + result_probe.PLAYER_DEPLOYMENT_COUNT * 4
    )
    header_start = builder.BATTLE_RESULT_HEADER_GLYPH_LIST
    header_end = (
        header_start + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2 + 2
    )
    digest = hashlib.sha256(diagnostic).hexdigest()
    return {
        "mode": "enemy_annihilation",
        "md_checksum": f"{checksum:04X}",
        "sha256": digest,
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
        "scenario_result_events_unchanged": unchanged_ranges(
            candidate,
            diagnostic,
            event_ranges(),
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
        "matches_expected_sha256": (
            digest == expected["result_probe_sha256"]
        ),
    }


def gray_plane_expectation(origin: list[int]) -> list[dict[str, object]]:
    x, y = origin
    return [
        {
            "tile": f"0x{GRAY_TILE_START + index:04X}",
            "hits": [
                {
                    "plane": "plane_a",
                    "x": x + index // 2,
                    "y": y + index % 2,
                    "tile_word": f"0x{0xA000 | GRAY_TILE_START + index:04X}",
                }
            ],
        }
        for index in range(4)
    ]


def battle_report(
    profile: str,
    root: Path,
    candidate: bytes,
) -> dict[str, object]:
    expected = EXPECTED[profile]
    active = root / "gray01/active_command.png"
    acted = root / "gray01/acted_gray.png"
    acted_gst = root / "gray01/states/acted_gray.gst"
    result = root / "result01/battle_result.png"
    result_gst = root / "result01/states/battle_result.gst"
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
            "scope_note": (
                "The normal gray-only diagnostic accidentally hired Soldiers; "
                "the accepted clean preparation run separately covers hiring "
                "names and unchanged before/after state. The acted-sprite proof "
                "uses only runtime group 0, its Plane A references, and its "
                "stock Fighter silhouette payload."
                if profile == "normal"
                else (
                    "The hard gray diagnostic used the preserved seed without "
                    "additional hires."
                )
            ),
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
            "diagnostic_lineage": diagnostic_report(candidate, expected),
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
    result = {
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
    validate_run(profile, result, plan, captured)
    return result


def validate_run(
    profile: str,
    report: dict[str, object],
    plan: dict[str, object],
    captured: dict[str, object],
) -> None:
    battle = report["battle_evidence"]
    gray = battle["gray_acted_sprite"]
    result = battle["battle_result"]
    diagnostic = result["diagnostic_lineage"]
    expected = EXPECTED[profile]
    checks = {
        "scenario is 2": report["scenario"] == 2,
        "profile path is correct": f"/{profile}/s02/" in f"/{report['run']}/",
        "candidate checksum matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
        ),
        "candidate hash matches plan": (
            report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "captured evidence is the selected exact run": (
            captured["status"] == "captured_exact_unreviewed"
            and captured["acceptance_updated"] is False
            and captured["profile"] == profile
            and captured["scenario"] == 2
            and captured["capture_pairs"] == report["capture_pairs"]
        ),
        "all 18 pairs are present": (
            report["expected_pair_count"]
            == report["actual_pair_count"]
            == 18
        ),
        "all before/after pairs are exact": all(
            row["byte_identical"] for row in report["capture_pairs"]
        ),
        "all eight visible fixed records are distinct and routed": (
            report["visible_fixed_record_indexes"] == list(range(8))
            and report["distinct_pre_fixed_detail_count"] == 8
        ),
        "hidden fixed records have explicit reasons": (
            [
                row["index"]
                for row in report["not_applicable_fixed_records"]
            ]
            == [8, 9]
            and all(
                "(255,255)" in row["reason"]
                for row in report["not_applicable_fixed_records"]
            )
        ),
        "shop captures are full-screen": all(
            capture["dimensions"] == [320, 240]
            for capture in report["shop_captures"]
        ),
        "human review passes": (
            report["status"] == "scenario_2_surface_pass"
            and all(
                value == "pass"
                for value in report["human_review"]["checks"].values()
            )
        ),
        "battle captures are full-screen": (
            gray["active_capture"]["dimensions"] == [320, 240]
            and gray["acted_capture"]["dimensions"] == [320, 240]
            and result["capture"]["dimensions"] == [320, 240]
        ),
        "battle hashes are locked": (
            gray["active_capture"]["sha256"] == expected["active_capture"]
            and gray["acted_capture"]["sha256"] == expected["acted_capture"]
            and gray["gst_sha256"] == expected["acted_gst"]
            and result["capture"]["sha256"] == expected["result_capture"]
            and result["gst_sha256"] == expected["result_gst"]
        ),
        "runtime group 0 is acted Elwin Fighter": (
            gray["runtime_group_zero"]["class_id"] == 1
            and gray["runtime_group_zero"]["commander_id"] == 1
            and gray["runtime_group_zero"]["acted_flag"] == 1
            and [
                gray["runtime_group_zero"]["x"],
                gray["runtime_group_zero"]["y"],
            ]
            == expected["acted_xy"]
        ),
        "gray payload is stock Fighter": (
            gray["source_record_offset"] == "0x05DBA8"
            and gray["source_silhouette_id"] == "0x001E"
            and gray["matches_stock_fighter_silhouette_expansion"]
            and gray["vram_sha256"] == EXPECTED_GRAY_VRAM_SHA256
        ),
        "gray tiles are visible on Plane A": (
            gray["plane_references"]
            == gray_plane_expectation(expected["plane_origin"])
        ),
        "result header is intact Korean": (
            result["header_text"] == "전과보고"
            and result["header_vram_sha256"]
            == EXPECTED_RESULT_HEADER_VRAM_SHA256
            and all(cell["matches"] for cell in result["header_plane_cells"])
        ),
        "result diagnostic is narrowly derived": (
            diagnostic["changed_only_checksum_start_operand_and_wrapper"]
            and diagnostic["scenario_layout_validated_against_source"]
            and diagnostic["scenario_deployments_unchanged"]
            and diagnostic["scenario_fixed_records_unchanged"]
            and diagnostic["scenario_result_events_unchanged"]
            and diagnostic["korean_battle_result_header_unchanged"]
            and diagnostic["matches_expected_checksum"]
            and diagnostic["matches_expected_sha256"]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} Scenario 2 evidence failed: " + ", ".join(failed)
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
        "status": "scenario_2_complete_pass",
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
            "preparation_surface_runs_reviewed": 4,
            "battle_surface_runs_reviewed": 4,
            "fully_accepted_profile_scenario_runs": 4,
            "fully_accepted_scenarios": 2,
            "remaining_requirement": (
                "Complete every required surface in Scenarios 3 through 27 "
                "for both profiles."
            ),
        },
        "rejected_attempts": [
            {
                "profile": "normal",
                "run_id": "s02a01",
                "result": (
                    "The long foreground parent was terminated around 70 "
                    "seconds; its orphaned BlastEm process was stopped and no "
                    "capture from the attempt is accepted."
                ),
                "replacement": (
                    "s02a02 completed 18/18 exact pairs and passed review."
                ),
            }
        ],
        "diagnostic_disclosures": [
            {
                "profile": "normal",
                "surface": "gray_acted_sprite",
                "result": (
                    "An obsolete deployment sequence hired Soldiers before "
                    "the gray-only movement capture. The accepted clean s02a02 "
                    "preparation run covers hiring; gray01 is accepted only for "
                    "runtime group 0 acted state, Plane A references, and exact "
                    "stock Fighter silhouette expansion."
                ),
            }
        ],
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_2_complete_pass":
        raise ValueError("Scenario 2 report must record its complete pass")
    progress = report["matrix_progress_after_acceptance"]
    if progress["fully_accepted_profile_scenario_runs"] != 4:
        raise ValueError("Scenarios 1 and 2 must yield four accepted runs")
    if progress["fully_accepted_scenarios"] != 2:
        raise ValueError("Scenarios 1 and 2 must be fully accepted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed normal/hard Scenario 2 preparation, shop, gray "
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
