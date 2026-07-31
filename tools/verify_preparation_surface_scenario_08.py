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
from tools import build_scenario8_clear_probe_rom as result_probe
from tools import run_preparation_surface_matrix as matrix
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout
from tools.verify_preparation_surface_evidence import (
    GRAY_TILE_START,
    GRAY_VRAM_BYTES,
    GRAY_VRAM_START,
    GST_WORK_RAM_OFFSET,
    RESULT_HEADER_VRAM_BYTES,
    RESULT_HEADER_VRAM_START,
    RUNTIME_GROUP_BASE,
    RUNTIME_GROUP_SIZE,
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
        / f"captures/run/preparation_surface_matrix/{profile}/s08/current01"
    )
    for profile in ("normal", "hard")
}
GRAY_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_battle_surface/{profile}/s08/gray01"
    )
    for profile in ("normal", "hard")
}
RESULT_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_battle_surface/{profile}/s08/result02"
    )
    for profile in ("normal", "hard")
}
REINFORCEMENT_RUNS = {
    profile: (
        ROOT
        / (
            "captures/run/preparation_battle_surface/"
            f"{profile}/s08/reinforcement02"
        )
    )
    for profile in ("normal", "hard")
}
REVIEW = ROOT / "localization/preparation_surface_scenario_08_review.json"
OUTPUT = ROOT / "localization/preparation_surface_scenario_08.json"
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
    "b8341f9d5fb532369b3be376abc4c96f8c4d93211ae953762aec8fec8c46691a",
    "9c15fbaf3f6af99584506bb31fa9c64cb0df1ef1714d91cd31986c2f2f170b67",
    "93ad01274d6d41083fa5b05364d9be5a93b42c47f9fabaaaa29ec01978cf370b",
)
EXPECTED = {
    "normal": {
        "active_capture": (
            "73b1ada14a3157c0b01b895ecbf2d01ff9a582c07084ae16e0ac4fdf8a46b1d3"
        ),
        "acted_capture": (
            "1150b0394b0657a8a417d8bde429f9d3129e43f288da77e5f8c80a85c120d43d"
        ),
        "acted_gst": (
            "44d600f8175b5f66e537b9b6cddc74b40c722e60ccb684d723149a3839b6efbd"
        ),
        "class_choice_gsts": (
            "5cc04163c63952cffaed4cd2c19099f8f8a8f5f644fc735fe1ee0c8faa8511d6",
            "9b2103b593e35e2ee5deb09a6f0d78c701ec66593a08618e5bcb44d41b9c7c37",
            "a1057050fa80ed7f4abe956b4d87539c5fcc7eabf4e1c2b3c9a004efd64c242b",
        ),
        "result_capture": (
            "8b8c5c5a34db350f35836f964a0075defa389ab5c6f7813345d51a41f0ed798c"
        ),
        "result_gst": (
            "c04ef3e425a57fb4fd37967f2e925231f1dd418600043e39af9ddbd472bc96eb"
        ),
        "result_probe_checksum": "CA44",
        "result_probe_sha256": (
            "37b6fb0dd9051d79570698af656d0e015490106bafab7bb51fc86a48c04f8ec8"
        ),
        "survival_probe_checksum": "CA52",
        "survival_probe_sha256": (
            "ec033cabd835f9f384394aa812f207dd4804658e58ab36124dd7798e6bb934ea"
        ),
        "reinforcement_captures": (
            "992dc7b9e84c6dbc6cfe1049b050ff609abad0e98389f98eb051fd35113cce5a",
            "0c84a759975fa4f3958204d217b74ce4a901cdf0cabcbbb584331ad59756ad78",
            "7f619d7ec14fc898add5419ad9852e12b188406e660b365dd8531d2f7da8e267",
            "0645fa1b2bd22ad569695319e12a2f7c6fb3ddb3a2eb95ce7a4dac39384f78e6",
            "a9d2b171ee0273b0b714375c777454c96b49f2d00931457069c5aceebc3eabd4",
        ),
        "reinforcement_gsts": (
            "9ebc7bb52ebf66f50b8ae60317b4632360d96878c6922589dde27845d96649f1",
            "0d86ec0c5be9a34d0687c91e903594d107a56b858a810dda7bacad99b4d274d8",
        ),
        "selected_result_class": "세인트",
    },
    "hard": {
        "active_capture": (
            "4db23b161f6e229e56f20405e0515e4032e98a0ad53422c7451b0dda097b5537"
        ),
        "acted_capture": (
            "1081ac3729c0bd4ff0b18c490f3a95d07f658ecfad662ccdea75e3a4fdea3234"
        ),
        "acted_gst": (
            "deca6e93c0f5396b288921e19aba4c51cc8f1a80d16e12c68341c0d533e4d956"
        ),
        "class_choice_gsts": (
            "99ef0d43c64f10f623fe949e867f35e57212ec3a6b57e68aea1cda4b08f3306c",
            "1c6d64b2b7361b5c55a5998b913e22af5e5f52b8d10b4d2a4814916ad9182c4f",
            "5b9c8d007f3cd9fb27ee3a2157995cf6166b14dfd788c729fa403a8fb32078ff",
        ),
        "result_capture": (
            "9726dc4bc9e5ce153c48bfcf9c9c20a12aa0bd1d33850e157d67ac823904b549"
        ),
        "result_gst": (
            "6a55c928b0495d2464856402baa63a0255cdfc78c06f5f91c8709a706dd1ce30"
        ),
        "result_probe_checksum": "2D25",
        "result_probe_sha256": (
            "9a73fd3d15c8a8c92fd3a4ae15d97e66dafebb7c6c21a2f26fff9f910f1609f6"
        ),
        "survival_probe_checksum": "2D33",
        "survival_probe_sha256": (
            "e90a6d1306fa49eb1c1ee6845bcde872be28caee9d9bbbb39ad9927b0d9b6481"
        ),
        "reinforcement_captures": (
            "992dc7b9e84c6dbc6cfe1049b050ff609abad0e98389f98eb051fd35113cce5a",
            "ddbf1080e0e9f97fdff4fa9b278049090a68bf5c3b135bc5ea813328ed60678e",
            "42eb2e43ec6feed693edabbca29f2b2c6aa2414d5546b42ae08f104667530a01",
            "7e1ae5bf26b67297982446d79ce1c4aefdf13ced8091a6f2c5dcfd1dbc9eca29",
            "a9d2b171ee0273b0b714375c777454c96b49f2d00931457069c5aceebc3eabd4",
        ),
        "reinforcement_gsts": (
            "92c63b51450a9fb8f459cf26325dc481802086d5023b89ca9b168193dbfcdc93",
            "c348f8b5ee4f30d8cb610fef5511a9a1c407e0ebedf6dc61db6b883c2c2754e8",
        ),
        "selected_result_class": "로드",
    },
}


def gray_plane_expectation() -> list[dict[str, object]]:
    coordinates = ((18, 13), (18, 14), (19, 13), (19, 14))
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
    *,
    boss_survival: bool = False,
) -> dict[str, object]:
    source = JAPANESE_ROM.read_bytes()
    diagnostic = bytearray(candidate)
    checksum = result_probe.patch_probe(
        diagnostic,
        source,
        boss_survival=boss_survival,
    )
    changed_offsets = {
        offset
        for offset, (before, after) in enumerate(zip(candidate, diagnostic))
        if before != after
    }
    kramer = result_probe.KRAMER_RECORD_OFFSET
    allowed = {0x18E, 0x18F}
    allowed.update(
        {
            kramer + FIELD_OFFSETS[field]
            for field in ("at", "df", "x", "y")
        }
    )
    allowed.update(
        range(
            kramer + FIELD_OFFSETS["mercenaries"],
            kramer + FIELD_OFFSETS["mercenaries"] + 6,
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
        if index != result_probe.KRAMER_RECORD_INDEX
    ]
    turn_end = result_probe.TURN_EVENT_TABLE + len(
        result_probe.TURN_EVENT_TABLE_BYTES
    )
    header_start = builder.BATTLE_RESULT_HEADER_GLYPH_LIST
    header_end = (
        header_start + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2 + 2
    )
    digest = hashlib.sha256(diagnostic).hexdigest()
    expected_checksum = (
        expected["survival_probe_checksum"]
        if boss_survival
        else expected["result_probe_checksum"]
    )
    expected_sha256 = (
        expected["survival_probe_sha256"]
        if boss_survival
        else expected["result_probe_sha256"]
    )
    return {
        "mode": (
            "source_record_isolated_real_attack_then_stock_reinforcement"
            if boss_survival
            else "source_record_isolated_real_attack_then_stock_victory"
        ),
        "validation_source": "Japanese source ROM",
        "md_checksum": f"{checksum:04X}",
        "sha256": digest,
        "changed_offset_count": len(changed_offsets),
        "changed_offsets_within_declared_ranges": changed_offsets <= allowed,
        "kramer_source_coordinates": [
            result_probe.SOURCE_KRAMER_X,
            result_probe.SOURCE_KRAMER_Y,
        ],
        "kramer_probe_coordinates": [
            result_probe.PROBE_KRAMER_X,
            result_probe.PROBE_KRAMER_Y,
        ],
        "kramer_probe_at_df": [
            result_probe.PROBE_KRAMER_AT,
            (
                result_probe.PROBE_KRAMER_SURVIVAL_DF
                if boss_survival
                else result_probe.PROBE_KRAMER_DF
            ),
        ],
        "kramer_probe_mercenaries_removed": (
            diagnostic[
                kramer + FIELD_OFFSETS["mercenaries"] :
                kramer + FIELD_OFFSETS["mercenaries"] + 6
            ]
            == b"\xFF" * 6
        ),
        "all_player_deployments_unchanged": (
            candidate[deployment_start:deployment_end]
            == diagnostic[deployment_start:deployment_end]
            == source[deployment_start:deployment_end]
        ),
        "all_non_kramer_fixed_records_unchanged": all(
            candidate[start:end]
            == diagnostic[start:end]
            == source[start:end]
            for start, end in fixed_ranges
        ),
        "hidden_vargas_record_unchanged": (
            candidate[
                layout.records_offset + 9 * FIXED_RECORD_SIZE :
                layout.records_offset + 10 * FIXED_RECORD_SIZE
            ]
            == diagnostic[
                layout.records_offset + 9 * FIXED_RECORD_SIZE :
                layout.records_offset + 10 * FIXED_RECORD_SIZE
            ]
            == source[
                layout.records_offset + 9 * FIXED_RECORD_SIZE :
                layout.records_offset + 10 * FIXED_RECORD_SIZE
            ]
        ),
        "hidden_zolm_record_unchanged": (
            candidate[
                layout.records_offset + 10 * FIXED_RECORD_SIZE :
                layout.records_offset + 11 * FIXED_RECORD_SIZE
            ]
            == diagnostic[
                layout.records_offset + 10 * FIXED_RECORD_SIZE :
                layout.records_offset + 11 * FIXED_RECORD_SIZE
            ]
            == source[
                layout.records_offset + 10 * FIXED_RECORD_SIZE :
                layout.records_offset + 11 * FIXED_RECORD_SIZE
            ]
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
        "matches_expected_checksum": f"{checksum:04X}" == expected_checksum,
        "matches_expected_sha256": digest == expected_sha256,
    }


def runtime_group(path: Path, group: int) -> dict[str, object]:
    data = path.read_bytes()
    start = (
        GST_WORK_RAM_OFFSET
        + RUNTIME_GROUP_BASE
        + group * RUNTIME_GROUP_SIZE
    )
    record = data[start : start + RUNTIME_GROUP_SIZE]
    if len(record) != RUNTIME_GROUP_SIZE:
        raise ValueError(f"{path} has a truncated runtime group {group}")
    return {
        "group": group,
        "class_id": record[0],
        "commander_id": record[1],
        "acted_flag": record[2],
        "hp": record[3],
        "x": record[6],
        "y": record[7],
        "at": record[0x3A],
        "df": record[0x3B],
        "record_prefix": record[:16].hex(),
    }


def reinforcement_report(
    profile: str,
    candidate: bytes,
) -> dict[str, object]:
    root = REINFORCEMENT_RUNS[profile]
    vargas_gst = root / "states/vargas_status.gst"
    zolm_gst = root / "states/zolm_status.gst"
    return {
        "status": "pass",
        "run_root": relative(root),
        "trigger": (
            "A real Elwin Attack leaves the isolated Kramer at HP 1; the "
            "unchanged stock event places hidden source records 9 and 10."
        ),
        "kramer_hp_one_capture": image_report(root / "post_battle_wait.png"),
        "vargas_dialogue_captures": [
            image_report(root / "event_02.png"),
            image_report(root / "event_03.png"),
        ],
        "vargas": {
            "name": "발가스",
            "class_name": "제너럴",
            "capture": image_report(root / "vargas_status.png"),
            "gst": relative(vargas_gst),
            "gst_sha256": sha256_path(vargas_gst),
            "runtime_group": runtime_group(vargas_gst, 16),
        },
        "zolm": {
            "name": "조름",
            "class_name": "로드",
            "capture": image_report(root / "zolm_status.png"),
            "gst": relative(zolm_gst),
            "gst_sha256": sha256_path(zolm_gst),
            "runtime_group": runtime_group(zolm_gst, 17),
        },
        "diagnostic_lineage": diagnostic_report(
            candidate,
            EXPECTED[profile],
            boss_survival=True,
        ),
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
        "hidden_reinforcements": reinforcement_report(profile, candidate),
        "class_change": {
            "trigger": (
                "Natural Sherry level-up during the stock Scenario 8 "
                "victory aftermath"
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
        "expected_pair_count": 28,
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
    reinforcements = battle["hidden_reinforcements"]
    choices = battle["class_change"]["choices"]
    result = battle["battle_result"]
    diagnostic = result["diagnostic_lineage"]
    survival = reinforcements["diagnostic_lineage"]
    expected_visible = list(range(9))
    reinforcement_captures = (
        reinforcements["kramer_hp_one_capture"],
        *reinforcements["vargas_dialogue_captures"],
        reinforcements["vargas"]["capture"],
        reinforcements["zolm"]["capture"],
    )
    checks = {
        "scenario/profile": (
            report["scenario"] == 8
            and f"/{profile}/s08/" in f"/{report['run']}/"
        ),
        "candidate matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
            and report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "selected matrix evidence exact": (
            captured["status"] == "captured_exact_unreviewed"
            and captured["acceptance_updated"] is False
            and captured["profile"] == profile
            and captured["scenario"] == 8
            and captured["capture_pairs"] == report["capture_pairs"]
        ),
        "all 28 pairs exact": (
            report["expected_pair_count"]
            == report["actual_pair_count"]
            == 28
            and all(row["byte_identical"] for row in report["capture_pairs"])
        ),
        "every fixed record accounted": (
            report["fixed_record_count"] == 11
            and report["visible_fixed_record_indexes"] == expected_visible
            and [
                row["index"]
                for row in report["not_applicable_fixed_records"]
            ]
            == [9, 10]
            and all(
                "(255,255)" in row["reason"]
                for row in report["not_applicable_fixed_records"]
            )
        ),
        "human review complete": (
            report["status"] == "scenario_8_surface_pass"
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
            and tuple(
                capture["sha256"] for capture in reinforcement_captures
            )
            == expected["reinforcement_captures"]
            and (
                reinforcements["vargas"]["gst_sha256"],
                reinforcements["zolm"]["gst_sha256"],
            )
            == expected["reinforcement_gsts"]
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
            and all(
                capture["dimensions"] == [320, 240]
                for capture in reinforcement_captures
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
            == [3, 7]
        ),
        "stock gray silhouette": (
            gray["source_record_offset"] == "0x05DBA8"
            and gray["source_silhouette_id"] == "0x001E"
            and gray["matches_stock_fighter_silhouette_expansion"]
            and gray["vram_sha256"] == EXPECTED_GRAY_VRAM_SHA256
            and gray["plane_references"] == gray_plane_expectation()
        ),
        "stock hidden reinforcements complete": (
            reinforcements["status"] == "pass"
            and reinforcements["vargas"]["name"] == "발가스"
            and reinforcements["vargas"]["class_name"] == "제너럴"
            and reinforcements["vargas"]["runtime_group"]
            == {
                "group": 16,
                "class_id": 73,
                "commander_id": 15,
                "acted_flag": 0,
                "hp": 10,
                "x": 2,
                "y": 11,
                "at": 40,
                "df": 30,
                "record_prefix": "490f000a1000020b000000007e0f000a",
            }
            and reinforcements["zolm"]["name"] == "조름"
            and reinforcements["zolm"]["class_name"] == "로드"
            and reinforcements["zolm"]["runtime_group"]
            == {
                "group": 17,
                "class_id": 50,
                "commander_id": 19,
                "acted_flag": 0,
                "hp": 10,
                "x": 3,
                "y": 8,
                "at": 24,
                "df": 23,
                "record_prefix": "3213000a11000308000000007213000a",
            }
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
            and diagnostic["kramer_probe_mercenaries_removed"]
            and diagnostic["all_player_deployments_unchanged"]
            and diagnostic["all_non_kramer_fixed_records_unchanged"]
            and diagnostic["hidden_vargas_record_unchanged"]
            and diagnostic["hidden_zolm_record_unchanged"]
            and diagnostic["scheduled_turn_table_unchanged"]
            and diagnostic["scheduled_turn_handlers_unchanged"]
            and diagnostic["korean_battle_result_header_unchanged"]
            and diagnostic["matches_expected_checksum"]
            and diagnostic["matches_expected_sha256"]
        ),
        "survival diagnostic narrow": (
            survival["changed_offsets_within_declared_ranges"]
            and survival["kramer_probe_at_df"] == [0, 14]
            and survival["kramer_probe_mercenaries_removed"]
            and survival["all_player_deployments_unchanged"]
            and survival["all_non_kramer_fixed_records_unchanged"]
            and survival["hidden_vargas_record_unchanged"]
            and survival["hidden_zolm_record_unchanged"]
            and survival["scheduled_turn_table_unchanged"]
            and survival["scheduled_turn_handlers_unchanged"]
            and survival["korean_battle_result_header_unchanged"]
            and survival["matches_expected_checksum"]
            and survival["matches_expected_sha256"]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} Scenario 8 evidence failed: " + ", ".join(failed)
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
        "status": "scenario_8_complete_pass",
        "review": {
            "path": relative(REVIEW),
            "sha256": sha256_path(REVIEW),
            "reviewed_on": review["reviewed_on"],
            "scope": review["scope"],
            "allied_scope": review["allied_scope"],
            "fixed_record_scope": review["fixed_record_scope"],
            "shop_scope": review["shop_scope"],
            "class_change": review["class_change"],
            "preparation_not_applicable_but_runtime_covered": review[
                "preparation_not_applicable_but_runtime_covered"
            ],
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
            "hidden_reinforcement_runtime_records_identical": (
                profiles["normal"]["battle_evidence"][
                    "hidden_reinforcements"
                ]["vargas"]["runtime_group"]
                == profiles["hard"]["battle_evidence"][
                    "hidden_reinforcements"
                ]["vargas"]["runtime_group"]
                and profiles["normal"]["battle_evidence"][
                    "hidden_reinforcements"
                ]["zolm"]["runtime_group"]
                == profiles["hard"]["battle_evidence"][
                    "hidden_reinforcements"
                ]["zolm"]["runtime_group"]
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
            "preparation_surface_runs_reviewed": 20,
            "battle_surface_runs_reviewed": 20,
            "fully_accepted_profile_scenario_runs": 20,
            "fully_accepted_scenarios": 10,
            "remaining_requirement": (
                "Complete every required surface in Scenario 10 and "
                "Scenarios 12 through 27 for both profiles."
            ),
        },
        "rejected_attempts": [
            {
                "profile": "normal",
                "surface": "result-state retention",
                "result": (
                    "The first completion run reached the result but did not "
                    "retain an accepted result GST; loading the target quicksave "
                    "then reset to the Sega/title screen. The complete run is "
                    "excluded in favor of normal result02."
                ),
            },
            {
                "profile": "hard",
                "surface": "scenario-selector entry",
                "result": (
                    "The first hard completion attempt missed the selector and "
                    "entered name entry. The complete run is excluded in favor "
                    "of hard result02."
                ),
            },
            {
                "profile": "normal",
                "surface": "hidden-reinforcement branch",
                "result": (
                    "The first branch attempt reused the DF-0 clear probe, so "
                    "the capped attack still reduced Kramer to HP 0 and never "
                    "spawned the reinforcements. It is excluded in favor of "
                    "the source-isolated DF-14 survival probe."
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
                "The result diagnostic changes only Kramer's source AT/DF, six "
                "mercenary slots, and coordinates, placing him directly above "
                "the stock Elwin deployment. A real Elwin Attack then enters "
                "the unchanged stock victory aftermath."
            ),
            (
                "The reinforcement diagnostic changes the same isolated "
                "Kramer fields but uses DF 14. A real Elwin Attack leaves HP "
                "1 and the stock event places unchanged hidden source records "
                "9 and 10 as 발가스/제너럴 and 조름/로드 runtime groups."
            ),
            (
                "Normal result evidence continues with Saint and hard result "
                "evidence with Lord, so the final sprite grids legitimately "
                "differ. Both retain identical 전과보고 VRAM and intact full "
                "screen content; all three choice frames are byte-identical."
            ),
            (
                "Fixed records 9 and 10 are explicitly N/A only on the "
                "preparation surface because both begin at (255,255); both are "
                "fully covered after their stock reinforcement placement."
            ),
        ],
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_8_complete_pass":
        raise ValueError("Scenario 8 report must record its complete pass")
    progress = report["matrix_progress_after_acceptance"]
    if progress["fully_accepted_profile_scenario_runs"] != 20:
        raise ValueError("Ten accepted scenarios must yield twenty runs")
    if progress["fully_accepted_scenarios"] != 10:
        raise ValueError("Ten scenarios must be accepted")
    if not all(report["cross_profile_identity"].values()):
        raise ValueError("Scenario 8 cross-profile invariants must all pass")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed normal/hard Scenario 8 preparation, shop, every "
            "allied/enemy record including hidden stock reinforcements, gray "
            "acted-sprite, natural class change, and result evidence."
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
