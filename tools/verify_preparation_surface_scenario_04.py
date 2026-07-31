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
from tools import build_scenario4_clear_probe_rom as result_probe
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
        / f"captures/run/preparation_surface_matrix/{profile}/s04/classfix04"
    )
    for profile in ("normal", "hard")
}
GRAY_RUNS = {
    "normal": (
        ROOT / "captures/run/preparation_battle_surface/normal/s04/gray02"
    ),
    "hard": (
        ROOT / "captures/run/preparation_battle_surface/hard/s04/gray01"
    ),
}
RESULT_RUNS = {
    "normal": (
        ROOT / "captures/run/preparation_result_surface/normal/s04/result02"
    ),
    "hard": (
        ROOT / "captures/run/preparation_result_surface/hard/s04/result01"
    ),
}
PREVIOUS_CANDIDATES = {
    "normal": (
        ROOT / "tmp/Langrisser II (Korean shop-overflow+prep-guarded probe).md"
    ),
    "hard": (
        ROOT
        / "tmp/Langrisser II (Korean Hard shop-overflow+prep-guarded probe).md"
    ),
}
REVIEW = ROOT / "localization/preparation_surface_scenario_04_review.json"
OUTPUT = ROOT / "localization/preparation_surface_scenario_04.json"
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
            "54d556ceeb715bebc59d8472737cade72ab2c250f34ff8d028692b7f269c9693"
        ),
        "acted_capture": (
            "01af7c2f1f906c0719c340b7c4bc7be3640a8578fd319a6a99b9d2658f093cab"
        ),
        "acted_gst": (
            "1075cb91973975658f16c896a2c3e312c1d8517f81ed0670d8f42b886a5884d3"
        ),
        "result_capture": (
            "1e493f7bdb8589ca317efb249f126ed8e799a5ef2e9ad9fc4df9cb1a212359da"
        ),
        "result_gst": (
            "443037f6f4a8d303b05818f3db66da6bc08661524127ab42ddd1bd2b44a25ec1"
        ),
        "result_probe_checksum": "FA4D",
        "result_probe_sha256": (
            "e962bfdc5be4599fc656443e5d68774fd99f8de10dc3b61a65f09c8458996c1d"
        ),
    },
    "hard": {
        "active_capture": (
            "54d556ceeb715bebc59d8472737cade72ab2c250f34ff8d028692b7f269c9693"
        ),
        "acted_capture": (
            "0f1aad8f3e0473027bdb5cb7b513675474d1aaafd4f26b86b6d3dcaf291f45c3"
        ),
        "acted_gst": (
            "d8dfbecde4aed34a1b9f57d70a69372cd32c8e8095e244f98fedfcba53d34170"
        ),
        "result_capture": (
            "1e493f7bdb8589ca317efb249f126ed8e799a5ef2e9ad9fc4df9cb1a212359da"
        ),
        "result_gst": (
            "8b8918df48a52628391f07dec15ad9bf4859100e8a7638e73611164b04a20515"
        ),
        "result_probe_checksum": "5D2E",
        "result_probe_sha256": (
            "6364dce1b03e40dbe3d56de41b2ee265989da42b2aba3f6a301f5e78cf37ed17"
        ),
    },
}


def gray_plane_expectation() -> list[dict[str, object]]:
    return [
        {
            "tile": f"0x{GRAY_TILE_START + index:04X}",
            "hits": [
                {
                    "plane": "plane_a",
                    "x": 17 + index // 2,
                    "y": (31 + index % 2) % 32,
                    "tile_word": f"0x{0xA000 | GRAY_TILE_START + index:04X}",
                }
            ],
        }
        for index in range(4)
    ]


def candidate_delta_from_gray_evidence(
    profile: str,
    candidate: bytes,
) -> dict[str, object]:
    previous_path = PREVIOUS_CANDIDATES[profile]
    previous = previous_path.read_bytes()
    changed_offsets = [
        offset
        for offset, (before, after) in enumerate(zip(previous, candidate))
        if before != after
    ]
    return {
        "previous_candidate": {
            "path": relative(previous_path),
            "md_checksum": matrix.md_checksum(previous_path),
            "sha256": sha256_path(previous_path),
        },
        "changed_offset_count": len(changed_offsets),
        "changed_offsets": [f"0x{offset:06X}" for offset in changed_offsets],
        "only_checksum_and_class_change_renderer_dispatch_changed": (
            changed_offsets == [0x00018F, 0x2B7121]
            and previous[0x2B7121] == 0x00
            and candidate[0x2B7121] == 0xB0
        ),
        "gray_silhouette_expansion_code_unchanged": (
            previous[
                builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE :
                builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE_LIMIT
            ]
            == candidate[
                builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE :
                builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE_LIMIT
            ]
        ),
    }


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
    base = result_probe.MORGAN_RECORD_OFFSET
    allowed_offsets = {
        0x18E,
        0x18F,
        *range(
            result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET,
            result_probe.FIRST_PLAYER_DEPLOYMENT_OFFSET + 4,
        ),
        base + FIELD_OFFSETS["at"],
        base + FIELD_OFFSETS["df"],
        *range(
            base + FIELD_OFFSETS["mercenaries"],
            base + FIELD_OFFSETS["mercenaries"] + 6,
        ),
    }
    layout = scenario_layout(candidate, result_probe.SCENARIO_NUMBER)
    records = [
        (
            layout.records_offset + index * FIXED_RECORD_SIZE,
            layout.records_offset + (index + 1) * FIXED_RECORD_SIZE,
        )
        for index in range(layout.record_count)
    ]
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
        "mode": "adjacent_unguarded_morgan",
        "validation_source": "Japanese source ROM",
        "md_checksum": f"{checksum:04X}",
        "sha256": digest,
        "changed_offset_count": len(changed_offsets),
        "changed_offsets": [f"0x{offset:06X}" for offset in changed_offsets],
        "allowed_change_ranges": [
            "ROM checksum 0x00018E..0x00018F",
            "Elwin deployment coordinate 0x1806A2..0x1806A5",
            "Morgan AT/DF 0x1807BE..0x1807BF",
            "Morgan mercenaries 0x1807CA..0x1807CF",
        ],
        "changed_only_declared_diagnostic_fields": (
            len(changed_offsets) == 11
            and set(changed_offsets) <= allowed_offsets
        ),
        "scenario_layout_validated_against_source": True,
        "other_player_deployments_unchanged": (
            candidate[deployment_start + 4 : deployment_end]
            == diagnostic[deployment_start + 4 : deployment_end]
        ),
        "all_non_morgan_fixed_records_unchanged": all(
            candidate[start:end] == diagnostic[start:end]
            for index, (start, end) in enumerate(records)
            if index != result_probe.MORGAN_RECORD_INDEX
        ),
        "morgan_identity_level_coordinates_unchanged": all(
            candidate[base + offset] == diagnostic[base + offset]
            for offset in (
                0,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["x"],
                FIELD_OFFSETS["y"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
            )
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


def battle_report(
    profile: str,
    candidate: bytes,
) -> dict[str, object]:
    expected = EXPECTED[profile]
    gray_root = GRAY_RUNS[profile]
    result_root = RESULT_RUNS[profile]
    active = gray_root / "active_command.png"
    acted = gray_root / "acted_gray.png"
    acted_gst = gray_root / "acted_gray.gst"
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
            "candidate_lineage": candidate_delta_from_gray_evidence(
                profile,
                candidate,
            ),
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
    gray = report["battle_evidence"]["gray_acted_sprite"]
    result = report["battle_evidence"]["battle_result"]
    diagnostic = result["diagnostic_lineage"]
    lineage = gray["candidate_lineage"]
    expected = EXPECTED[profile]
    checks = {
        "scenario/profile": (
            report["scenario"] == 4
            and f"/{profile}/s04/" in f"/{report['run']}/"
        ),
        "candidate matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
            and report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "selected evidence is exact": (
            captured["status"] == "captured_exact_unreviewed"
            and captured["acceptance_updated"] is False
            and captured["profile"] == profile
            and captured["scenario"] == 4
            and captured["capture_pairs"] == report["capture_pairs"]
        ),
        "all 20 pairs exact": (
            report["expected_pair_count"]
            == report["actual_pair_count"]
            == 20
            and all(row["byte_identical"] for row in report["capture_pairs"])
        ),
        "ten visible records distinct": (
            report["visible_fixed_record_indexes"]
            == [0, 1, 2, 3, 5, 6, 7, 8, 9, 10]
            and report["distinct_pre_fixed_detail_count"] == 10
        ),
        "hidden masked knight reasoned": (
            [
                row["index"]
                for row in report["not_applicable_fixed_records"]
            ]
            == [4]
            and "(255,255)"
            in report["not_applicable_fixed_records"][0]["reason"]
        ),
        "review and dimensions": (
            report["status"] == "scenario_4_surface_pass"
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
            == [8, 38]
        ),
        "stock gray silhouette": (
            gray["source_record_offset"] == "0x05DBA8"
            and gray["source_silhouette_id"] == "0x001E"
            and gray["matches_stock_fighter_silhouette_expansion"]
            and gray["vram_sha256"] == EXPECTED_GRAY_VRAM_SHA256
            and gray["plane_references"] == gray_plane_expectation()
        ),
        "gray evidence applies to current candidate": (
            lineage[
                "only_checksum_and_class_change_renderer_dispatch_changed"
            ]
            and lineage["gray_silhouette_expansion_code_unchanged"]
        ),
        "result header intact": (
            result["header_text"] == "전과보고"
            and result["header_vram_sha256"]
            == EXPECTED_RESULT_HEADER_VRAM_SHA256
            and all(cell["matches"] for cell in result["header_plane_cells"])
        ),
        "diagnostic narrow": (
            diagnostic["changed_only_declared_diagnostic_fields"]
            and diagnostic["scenario_layout_validated_against_source"]
            and diagnostic["other_player_deployments_unchanged"]
            and diagnostic["all_non_morgan_fixed_records_unchanged"]
            and diagnostic["morgan_identity_level_coordinates_unchanged"]
            and diagnostic["scenario_event_block_unchanged"]
            and diagnostic["korean_battle_result_header_unchanged"]
            and diagnostic["matches_expected_checksum"]
            and diagnostic["matches_expected_sha256"]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} Scenario 4 evidence failed: " + ", ".join(failed)
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
        "status": "scenario_4_complete_pass",
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
            "preparation_surface_runs_reviewed": 10,
            "battle_surface_runs_reviewed": 10,
            "fully_accepted_profile_scenario_runs": 10,
            "fully_accepted_scenarios": 5,
            "remaining_requirement": (
                "Complete every required surface in Scenarios 5 through 8 "
                "and 10 through 27 for both profiles."
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
                "run_id": "gray01",
                "result": (
                    "The scenario selector missed its initial-delay window "
                    "and entered name entry. gray02 is the accepted run."
                ),
            },
            {
                "profile": "normal",
                "surface": "battle result",
                "run_id": "result01",
                "result": (
                    "The input batch advanced beyond the result to the save "
                    "menu without retaining a result GST. result02 is accepted."
                ),
            },
            {
                "profile": "normal",
                "surface": "battle result dialogue",
                "result": (
                    "One 60-second host command ended during post-battle page "
                    "10. The isolated emulator remained live and shorter "
                    "batches completed the same stock path."
                ),
            },
            {
                "profile": "normal",
                "surface": "new-candidate matrix",
                "run_id": "classfix01",
                "result": (
                    "The foreground host command was terminated at its "
                    "120-second limit during post-shop commander capture. "
                    "classfix04 is the complete accepted rerun."
                ),
            },
            {
                "profile": "normal",
                "surface": "new-candidate matrix launch",
                "run_ids": ["classfix02", "classfix03"],
                "result": (
                    "classfix02 was reaped with its parent process; classfix03 "
                    "used a wrong captures/run seed path and exited before "
                    "launch. Neither produced acceptance evidence."
                ),
            },
        ],
        "navigation_disclosures": [
            (
                "The accepted result uses the stock Attack command against "
                "Morgan. The diagnostic only moves Elwin adjacent, clears "
                "Morgan AT/DF and mercenaries, and preserves every event byte."
            ),
            (
                "The hard result includes one additional level-up page before "
                "the same byte-identical result frame."
            ),
            (
                "The preserved Scenario 4 seed exposes no live class-change "
                "choice. The separate current-candidate class-change "
                "regression covers 팔랑크스 and 발리스타."
            ),
        ],
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_4_complete_pass":
        raise ValueError("Scenario 4 report must record its complete pass")
    progress = report["matrix_progress_after_acceptance"]
    if progress["fully_accepted_profile_scenario_runs"] != 10:
        raise ValueError("Five accepted scenarios must yield ten runs")
    if progress["fully_accepted_scenarios"] != 5:
        raise ValueError("Scenarios 1 through 4 and 9 must be accepted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed normal/hard Scenario 4 preparation, shop, gray "
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
