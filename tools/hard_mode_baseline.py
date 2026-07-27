#!/usr/bin/env python3
"""Inventory the immutable normal release and original scenario balance data."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.scenario_data import SCENARIO_COUNT, class_names, read_scenario


DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_NORMAL_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
DEFAULT_JSON = ROOT / "localization/hard_mode_baseline.json"
DEFAULT_MARKDOWN = ROOT / "docs/hard_mode_balance_discussion.md"

NORMAL_SIZE = 0x400000
NORMAL_CHECKSUM = "99FD"
NORMAL_SHA256 = "526237277c8f46a4400c00980da704e6ebea23e74d967d89b6d223db28dd54d3"
CLASS_RECORD_TABLE = 0x05EDDC
CLASS_RECORD_SIZE = 0x1C
CLASS_BASE_AT_OFFSET = 0x0B
CLASS_BASE_DF_OFFSET = 0x0C
CLASS_MOVEMENT_OFFSET = 0x0D
CLASS_SOLDIER_AT_CORRECTION_OFFSET = 0x0F
CLASS_SOLDIER_DF_CORRECTION_OFFSET = 0x10
FIXED_COMMANDER_AT_MODIFIER_OFFSET = 0x12
FIXED_COMMANDER_DF_MODIFIER_OFFSET = 0x13
FIXED_RECORD_LOADER = 0x010E46
FIXED_RECORD_LOADER_END = 0x010ED8

DISCUSSION_SCENARIO_BANDS = (
    {
        "id": "opening",
        "label": "초반",
        "scenarios": tuple(range(1, 6)),
        "rationale": "초기 성장과 기본 병종 중심의 시나리오",
    },
    {
        "id": "early_campaign",
        "label": "전반",
        "scenarios": tuple(range(6, 11)),
        "rationale": "첫 증원·시간 제한·몬스터 공개가 섞이는 시나리오",
    },
    {
        "id": "mid_campaign",
        "label": "중반",
        "scenarios": tuple(range(11, 16)),
        "rationale": "이벤트와 특수 목표 비중이 커지는 시나리오",
    },
    {
        "id": "late_campaign",
        "label": "후반",
        "scenarios": tuple(range(16, 21)),
        "rationale": "상위 클래스와 장기 목표가 본격화되는 시나리오",
    },
    {
        "id": "endgame",
        "label": "종반",
        "scenarios": tuple(range(21, 28)),
        "rationale": "주요 보스와 본편 결말을 포함하는 시나리오",
    },
    {
        "id": "secret",
        "label": "비밀",
        "scenarios": tuple(range(28, 32)),
        "rationale": "진입 시점이 다른 선택형 X1~X4 시나리오",
    },
)

RECOMMENDED_DISCUSSION_PROPOSAL = {
    "id": "standard_hard_ramp_v1",
    "status": "unapproved_discussion_only",
    "target_difficulty": "standard_hard",
    "design_intent": (
        "비기와 노가다 없이 완주할 수 있지만 상성과 진형을 활용해야 하는 "
        "숙련자용 점증 하드"
    ),
    "global_rules": {
        "enemy_level_delta": 0,
        "enemy_hp_mp_delta": 0,
        "commander_formula": (
            "min(original + scenario_delta, main_story_absolute_cap)"
        ),
        "main_story_absolute_cap": {
            "commander_at": 64,
            "commander_df": 46,
            "soldier_at_correction": 15,
            "soldier_df_correction": 12,
        },
        "mercenary_replacement_rule": (
            "occupied slots only; preserve combat role, movement constraints, "
            "and scenario terrain unless individually approved"
        ),
        "secret_scenario_rule": (
            "X1-X4 are tuned individually because entry timing and original "
            "stats differ too much for the main-story formula"
        ),
    },
    "scenario_steps": [
        {
            "label": "초반",
            "scenarios": [1, 2, 3, 4, 5],
            "commander_at_delta": 2,
            "commander_df_delta": 1,
            "soldier_at_correction_delta": 1,
            "soldier_df_correction_delta": 1,
            "stronger_mercenary_slots_per_six": 0,
            "summon_slots_per_six": 0,
        },
        {
            "label": "전반",
            "scenarios": [6, 7, 8, 9, 10],
            "commander_at_delta": 3,
            "commander_df_delta": 2,
            "soldier_at_correction_delta": 1,
            "soldier_df_correction_delta": 1,
            "stronger_mercenary_slots_per_six": 1,
            "summon_slots_per_six": 0,
        },
        {
            "label": "중반",
            "scenarios": [11, 12, 13, 14, 15],
            "commander_at_delta": 4,
            "commander_df_delta": 3,
            "soldier_at_correction_delta": 2,
            "soldier_df_correction_delta": 2,
            "stronger_mercenary_slots_per_six": 2,
            "summon_slots_per_six": 0,
        },
        {
            "label": "후반",
            "scenarios": [16, 17, 18, 19, 20],
            "commander_at_delta": 5,
            "commander_df_delta": 4,
            "soldier_at_correction_delta": 3,
            "soldier_df_correction_delta": 3,
            "stronger_mercenary_slots_per_six": 3,
            "summon_slots_per_six": 0,
        },
        {
            "label": "종반 전반",
            "scenarios": [21, 22, 23, 24],
            "commander_at_delta": 6,
            "commander_df_delta": 4,
            "soldier_at_correction_delta": 4,
            "soldier_df_correction_delta": 3,
            "stronger_mercenary_slots_per_six": 3,
            "summon_slots_per_six": 0,
        },
        {
            "label": "종반 후반",
            "scenarios": [25],
            "commander_at_delta": 6,
            "commander_df_delta": 5,
            "soldier_at_correction_delta": 4,
            "soldier_df_correction_delta": 4,
            "stronger_mercenary_slots_per_six": 4,
            "summon_slots_per_six": 0,
        },
        {
            "label": "최종장 직전",
            "scenarios": [26],
            "commander_at_delta": 6,
            "commander_df_delta": 5,
            "soldier_at_correction_delta": 4,
            "soldier_df_correction_delta": 4,
            "stronger_mercenary_slots_per_six": 4,
            "summon_slots_per_six": 1,
            "summon_scope": "named enemy commanders only",
        },
        {
            "label": "본편 최종장",
            "scenarios": [27],
            "commander_at_delta": 6,
            "commander_df_delta": 5,
            "soldier_at_correction_delta": 5,
            "soldier_df_correction_delta": 4,
            "stronger_mercenary_slots_per_six": 6,
            "summon_slots_per_six": 4,
            "summon_scope": (
                "four of six slots for major commanders; at most two of six "
                "for ordinary commanders"
            ),
        },
    ],
    "summon_policy": {
        "candidate_class_ids": [
            f"{class_id:02X}" for class_id in range(0x8D, 0x94)
        ],
        "excluded_class_ids": ["94"],
        "excluded_reason": "아니키는 비기·개그 성격이므로 기본 하드 편성에서 제외",
    },
    "exception_candidates": [
        {
            "scenario": 1,
            "offsets": ["0x1802FC", "0x180320"],
            "names": ["레온", "레아드"],
            "rule": "연출용 강적이므로 자동 능력치·용병 강화에서 제외",
        },
        {
            "scenario": 22,
            "offsets": [
                "0x1827DA",
                "0x1827FE",
                "0x182846",
                "0x18286A",
                "0x18288E",
                "0x1828B2",
                "0x1828D6",
                "0x1828FA",
                "0x18291E",
                "0x182942",
            ],
            "rule": (
                "실기에서 적대 대상으로 확인된 진영 08 열 개를 21~24장 "
                "공식 대상에 포함하되 원본 진영 08은 보존"
            ),
        },
        {
            "scenario": 24,
            "offsets": ["0x182B8A"],
            "names": ["베른하르트"],
            "rule": (
                "원작 이벤트가 진영을 바꾸는 특수 레코드이므로 고정 "
                "레코드 자동 강화에서 제외"
            ),
        },
        {
            "scenario": 25,
            "offsets": ["0x182D62"],
            "names": ["제시카"],
            "rule": "아군 지원 이벤트이므로 모든 적 전용 보너스에서 제외",
        },
        {
            "scenario": 30,
            "offsets": ["0x183724", "0x183748"],
            "names": ["미나 1단계", "미나 2단계"],
            "rule": "한 보스의 두 단계로 취급하고 중복 누적 금지",
        },
        {
            "scenario": 31,
            "offsets": ["0x183902"],
            "names": ["베른하르트"],
            "rule": (
                "적대 최종 보스지만 X4 원본 수치가 본편 상한보다 높으므로 "
                "본편 공식·상한을 적용하지 않고 X4에서 개별 조정"
            ),
        },
        {
            "scenarios": [28, 29, 30, 31],
            "rule": "비밀 시나리오는 본편 공식에서 제외하고 개별 조정",
        },
    ],
}


def rom_identity(data: bytes) -> dict[str, object]:
    return {
        "size": len(data),
        "header_checksum": data[0x18E:0x190].hex().upper(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def signed_byte(value: int) -> int:
    return value if value < 0x80 else value - 0x100


def class_corrections(source: bytes, class_id: int) -> tuple[int, int]:
    base = CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE
    return (
        signed_byte(source[base + CLASS_SOLDIER_AT_CORRECTION_OFFSET]),
        signed_byte(source[base + CLASS_SOLDIER_DF_CORRECTION_OFFSET]),
    )


def combat_class_group(class_id: int) -> str:
    if 0x62 <= class_id <= 0x71:
        return "ordinary_hireable"
    if 0x72 <= class_id <= 0x8C:
        return "scenario_enemy_variant_or_monster"
    if 0x8D <= class_id <= 0x94:
        return "summon_class"
    raise ValueError(f"class 0x{class_id:02X} is not a combat-unit class")


def combat_class_rows(
    source: bytes,
    classes: list[dict[str, object]],
    scenarios: list[dict[str, object]],
) -> list[dict[str, object]]:
    result = []
    for class_id in range(0x62, 0x95):
        base = CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE
        all_scenarios = []
        enemy_scenarios = []
        all_slot_count = 0
        enemy_slot_count = 0
        for scenario in scenarios:
            scenario_all = 0
            scenario_enemy = 0
            for record in scenario["records"]:
                occurrences = sum(
                    mercenary is not None
                    and mercenary["class_id"] == f"{class_id:02X}"
                    for mercenary in record["mercenaries"]
                )
                scenario_all += occurrences
                if record["side_id"] == "04":
                    scenario_enemy += occurrences
            if scenario_all:
                all_scenarios.append(int(scenario["number"]))
                all_slot_count += scenario_all
            if scenario_enemy:
                enemy_scenarios.append(int(scenario["number"]))
                enemy_slot_count += scenario_enemy
        result.append({
            "class_id": f"{class_id:02X}",
            "japanese": classes[class_id]["jp"],
            "korean": classes[class_id]["ko"],
            "group": combat_class_group(class_id),
            "base_at": source[base + CLASS_BASE_AT_OFFSET],
            "base_df": source[base + CLASS_BASE_DF_OFFSET],
            "movement": source[base + CLASS_MOVEMENT_OFFSET],
            "all_fixed_slot_count": all_slot_count,
            "enemy_side_04_slot_count": enemy_slot_count,
            "first_fixed_scenario": all_scenarios[0] if all_scenarios else None,
            "first_enemy_scenario": (
                enemy_scenarios[0] if enemy_scenarios else None
            ),
        })
    return result


def stat_summary(records: list[dict[str, object]], field: str) -> dict[str, object] | None:
    if not records:
        return None
    values = [int(row[field]) for row in records]
    return {
        "minimum": min(values),
        "maximum": max(values),
        "mean": round(statistics.mean(values), 1),
    }


def discussion_band_rows(scenarios: list[dict[str, object]]) -> list[dict[str, object]]:
    by_number = {int(row["number"]): row for row in scenarios}
    result = []
    for band in DISCUSSION_SCENARIO_BANDS:
        numbers = list(band["scenarios"])
        selected = [by_number[number] for number in numbers]
        enemies = [
            record
            for scenario in selected
            for record in scenario["records"]
            if record["side_id"] == "04"
        ]
        result.append({
            "id": band["id"],
            "label": band["label"],
            "scenarios": numbers,
            "rationale": band["rationale"],
            "user_approved": False,
            "original_side_04_summary": {
                "record_count": len(enemies),
                "hidden_record_count": sum(
                    bool(record["hidden"]) for record in enemies
                ),
                "side_08_record_count": sum(
                    int(scenario["side_counts"].get("08", 0))
                    for scenario in selected
                ),
                "level": stat_summary(enemies, "level"),
                "commander_at_modifier": stat_summary(
                    enemies, "commander_at_modifier"
                ),
                "commander_df_modifier": stat_summary(
                    enemies, "commander_df_modifier"
                ),
                "filled_mercenary_slots": sum(
                    mercenary is not None
                    for record in enemies
                    for mercenary in record["mercenaries"]
                ),
            },
        })
    return result


def mercenary_row(class_id: int, classes: list[dict[str, object]]) -> dict[str, object] | None:
    if class_id == 0xFF:
        return None
    row = classes[class_id]
    return {
        "class_id": f"{class_id:02X}",
        "japanese": row["jp"],
        "korean": row["ko"],
    }


def record_row(
    row: dict[str, object],
    classes: list[dict[str, object]],
    source: bytes,
) -> dict[str, object]:
    class_id = int(row["class_id"])
    soldier_at, soldier_df = class_corrections(source, class_id)
    return {
        "index": row["index"],
        "offset": f"0x{int(row['offset']):06X}",
        "side_id": f"{int(row['side_id']):02X}",
        "role": row["role"],
        "label": row["label"],
        "hidden": row["hidden"],
        "name_id": f"{int(row['name']['id']):02X}",
        "name_japanese": row["name"]["jp"],
        "name_korean": row["name"]["ko"],
        "class_id": f"{class_id:02X}",
        "class_japanese": row["class"]["jp"],
        "class_korean": row["class"]["ko"],
        "level": row["level"],
        "at": row["at"],
        "df": row["df"],
        "commander_at_modifier": signed_byte(int(row["at"])),
        "commander_df_modifier": signed_byte(int(row["df"])),
        "soldier_at_correction": soldier_at,
        "soldier_df_correction": soldier_df,
        "x": row["x"],
        "y": row["y"],
        "mercenaries": [
            mercenary_row(int(class_id), classes)
            for class_id in row["mercenaries"]
        ],
    }


def build_inventory(
    source_rom: Path = DEFAULT_SOURCE_ROM,
    normal_rom: Path = DEFAULT_NORMAL_ROM,
) -> dict[str, object]:
    source = source_rom.read_bytes()
    normal = normal_rom.read_bytes()
    normal_identity = rom_identity(normal)
    expected_normal = {
        "size": NORMAL_SIZE,
        "header_checksum": NORMAL_CHECKSUM,
        "sha256": NORMAL_SHA256,
    }
    if normal_identity != expected_normal:
        raise ValueError(
            "normal Korean release is not the immutable 99FD baseline: "
            f"{normal_identity}"
        )

    classes = class_names(source)
    scenarios = []
    all_sides: Counter[int] = Counter()
    all_mercenaries: Counter[int] = Counter()
    hidden_fixed_records = 0
    hidden_enemy_fixed_records = 0
    for number in range(1, SCENARIO_COUNT + 1):
        model = read_scenario(source, source, number)
        records = list(model["records"])
        enemies = [row for row in records if int(row["side_id"]) == 0x04]
        side_counts = Counter(int(row["side_id"]) for row in records)
        mercenary_counts: Counter[int] = Counter()
        for row in records:
            side_id = int(row["side_id"])
            all_sides[side_id] += 1
            if bool(row["hidden"]):
                hidden_fixed_records += 1
                if side_id == 0x04:
                    hidden_enemy_fixed_records += 1
            for class_id in row["mercenaries"]:
                if int(class_id) != 0xFF:
                    mercenary_counts[int(class_id)] += 1
                    all_mercenaries[int(class_id)] += 1
        scenarios.append({
            "number": number,
            "header_offset": f"0x{int(model['header_offset']):06X}",
            "record_list_offset": f"0x{int(model['record_list_offset']):06X}",
            "record_count": len(records),
            "side_counts": {
                f"{side_id:02X}": count
                for side_id, count in sorted(side_counts.items())
            },
            "hidden_record_count": sum(bool(row["hidden"]) for row in records),
            "enemy_summary": {
                "record_count": len(enemies),
                "level": stat_summary(enemies, "level"),
                "at": stat_summary(enemies, "at"),
                "df": stat_summary(enemies, "df"),
                "filled_mercenary_slots": sum(
                    int(class_id) != 0xFF
                    for row in enemies
                    for class_id in row["mercenaries"]
                ),
                "names": list(dict.fromkeys(
                    str(row["name"]["ko"]) for row in enemies
                )),
            },
            "mercenary_distribution": [
                {
                    **mercenary_row(class_id, classes),
                    "slot_count": count,
                }
                for class_id, count in sorted(mercenary_counts.items())
            ],
            "records": [record_row(row, classes, source) for row in records],
        })

    return {
        "schema_version": 7,
        "status": "balance_discussion_required",
        "approval_gate": {
            "user_approved": False,
            "implementation_started": False,
            "rom_values_may_be_applied": False,
            "required_decisions": [
                "scenario_band_target_difficulty",
                "enemy_commander_at_df_formula_and_caps",
                "stronger_mercenary_start_and_replacement_ratio",
                "late_summon_unit_start_and_ratio",
                "boss_reinforcement_branch_ending_exceptions",
            ],
        },
        "balance_discussion": {
            "user_selections": {
                "difficulty_target": None,
                "scenario_band_policy": None,
                "enemy_commander_and_soldier_formula": None,
                "stronger_mercenary_policy": None,
                "late_summon_unit_policy": None,
                "exception_policy": None,
            },
            "difficulty_options": [
                {
                    "id": "standard_hard",
                    "label": "숙련자용 표준 하드",
                    "recommended": True,
                    "expected_retries_per_major_battle": [1, 3],
                    "assumption": "비기·노가다 없이 기본적인 클래스와 장비 운용",
                },
                {
                    "id": "high_difficulty",
                    "label": "고난도",
                    "recommended": False,
                    "expected_retries_per_major_battle": [3, 5],
                    "assumption": "클래스·장비·용병 상성 최적화",
                },
                {
                    "id": "extreme",
                    "label": "극한",
                    "recommended": False,
                    "expected_retries_per_major_battle": [5, None],
                    "assumption": "비기·세이브 로드·사전 공략 지식을 허용",
                },
            ],
            "candidate_scenario_bands": discussion_band_rows(scenarios),
            "recommended_unapproved_proposal": RECOMMENDED_DISCUSSION_PROPOSAL,
        },
        "normal_release": {
            **normal_identity,
            "immutable": True,
        },
        "source_rom": rom_identity(source),
        "source_model": {
            "scenario_count": SCENARIO_COUNT,
            "record_size": 0x24,
            "fixed_record_loader": {
                "start": f"0x{FIXED_RECORD_LOADER:06X}",
                "end": f"0x{FIXED_RECORD_LOADER_END:06X}",
                "commander_at_modifier_offset": (
                    f"0x{FIXED_COMMANDER_AT_MODIFIER_OFFSET:02X}"
                ),
                "commander_df_modifier_offset": (
                    f"0x{FIXED_COMMANDER_DF_MODIFIER_OFFSET:02X}"
                ),
                "value_encoding": "signed_byte",
            },
            "class_record_model": {
                "table": f"0x{CLASS_RECORD_TABLE:06X}",
                "record_size": CLASS_RECORD_SIZE,
                "base_at_offset": f"0x{CLASS_BASE_AT_OFFSET:02X}",
                "base_df_offset": f"0x{CLASS_BASE_DF_OFFSET:02X}",
                "movement_offset": f"0x{CLASS_MOVEMENT_OFFSET:02X}",
                "soldier_at_correction_offset": (
                    f"0x{CLASS_SOLDIER_AT_CORRECTION_OFFSET:02X}"
                ),
                "soldier_df_correction_offset": (
                    f"0x{CLASS_SOLDIER_DF_CORRECTION_OFFSET:02X}"
                ),
                "scope": "global_per_class",
            },
            "combat_class_catalog": combat_class_rows(
                source,
                classes,
                scenarios,
            ),
            "reinforcement_model": {
                "hidden_fixed_records_included": True,
                "total_hidden_fixed_records": hidden_fixed_records,
                "hidden_enemy_fixed_records": hidden_enemy_fixed_records,
                "hidden_non_enemy_fixed_records": (
                    hidden_fixed_records - hidden_enemy_fixed_records
                ),
                "runtime_event_rewrites_require_audit": True,
            },
            "hard_mode_implementation_rule": {
                "commander_stats": (
                    "patch fixed-record signed modifiers after approval"
                ),
                "soldier_corrections": (
                    "do not patch shared class records globally; after approval "
                    "use a separate enemy-only expanded-ROM correction table "
                    "applied after the fixed-record loader"
                ),
                "dynamic_event_spawns": (
                    "all 63 hidden fixed records, including 53 side-04 enemy "
                    "records, are represented by the 340 fixed records; event "
                    "handlers can reveal or rewrite runtime records, so known "
                    "rewrites and any true non-fixed spawns require an explicit "
                    "exception audit before scenario approval"
                ),
            },
            "known_runtime_exceptions": [
                {
                    "scenario": 22,
                    "kind": "verified_hostile_special_faction",
                    "side_08_record_count": 10,
                    "verified_hostile_side_08_offsets": [
                        "0x1827DA",
                        "0x1827FE",
                        "0x182846",
                        "0x18286A",
                        "0x18288E",
                        "0x1828B2",
                        "0x1828D6",
                        "0x1828FA",
                        "0x18291E",
                        "0x182942",
                    ],
                    "hidden_boss": {
                        "offset": "0x182822",
                        "side_id": "04",
                        "name_korean": "베른하르트",
                        "class_id": "4E",
                        "class_korean": "엠퍼러",
                    },
                    "rule": (
                        "treat all ten side-08 records as hostile hard-mode targets "
                        "after balance approval, but preserve side 08 and all stock "
                        "event ownership"
                    ),
                },
                {
                    "scenario": 24,
                    "kind": "stock_allegiance_transition",
                    "fixed_record": {
                        "offset": "0x182B8A",
                        "side_id": "08",
                        "name_korean": "베른하르트",
                        "class_id": "4E",
                        "class_korean": "엠퍼러",
                        "at": 58,
                        "df": 41,
                        "mercenary_slots": 0,
                    },
                    "rule": (
                        "exclude this fixed record from automatic enemy bonuses "
                        "because stock events change its allegiance; any hard-mode "
                        "change must be runtime-event-specific and separately approved"
                    ),
                },
                {
                    "scenario": 25,
                    "kind": "allied_runtime_class_rewrite",
                    "fixed_record": {
                        "offset": "0x182D62",
                        "side_id": "03",
                        "name_korean": "제시카",
                        "class_id": "03",
                        "class_korean": "워록",
                    },
                    "verified_runtime_result": {
                        "class_id": "09",
                        "class_korean": "소서러",
                        "level": 5,
                        "at": 29,
                        "df": 17,
                    },
                    "rule": (
                        "always exclude allied Jessica from enemy hard-mode "
                        "bonuses even after the event rewrites her runtime record"
                    ),
                },
                {
                    "scenario": 30,
                    "kind": "two_phase_boss",
                    "phases": [
                        {
                            "offset": "0x183724",
                            "side_id": "04",
                            "hidden": False,
                            "class_id": "3F",
                            "class_korean": "메이지",
                        },
                        {
                            "offset": "0x183748",
                            "side_id": "04",
                            "hidden": True,
                            "class_id": "48",
                            "class_korean": "세인트",
                        },
                    ],
                    "rule": (
                        "treat both Mina records as one transformation route and "
                        "apply the approved boss rule per phase without accidental "
                        "stacking"
                    ),
                },
                {
                    "scenario": 31,
                    "kind": "secret_final_boss_special_faction",
                    "fixed_record": {
                        "offset": "0x183902",
                        "side_id": "08",
                        "name_korean": "베른하르트",
                        "class_id": "4E",
                        "class_korean": "엠퍼러",
                        "at": 87,
                        "df": 61,
                        "mercenaries": [
                            "7C",
                            "7C",
                            "7C",
                            "7C",
                            "77",
                            "77",
                        ],
                    },
                    "completion_target": True,
                    "rule": (
                        "keep as a hostile final boss, but exclude it from the "
                        "main-story formula and cap; tune only in the approved X4 "
                        "individual policy"
                    ),
                },
            ],
            "editable_fields_after_approval": [
                "level",
                "at",
                "df",
                "class_id",
                "mercenaries",
            ],
            "preserved_by_default": [
                "side_id",
                "hidden",
                "name_id",
                "x",
                "y",
                "events",
                "ai",
                "victory_and_defeat_conditions",
                "routes_and_endings",
            ],
            "side_counts": {
                f"{side_id:02X}": count
                for side_id, count in sorted(all_sides.items())
            },
            "mercenary_distribution": [
                {
                    **mercenary_row(class_id, classes),
                    "slot_count": count,
                }
                for class_id, count in all_mercenaries.most_common()
            ],
        },
        "scenarios": scenarios,
    }


def _stat_cell(summary: dict[str, object] | None) -> str:
    if summary is None:
        return "-"
    return (
        f"{summary['minimum']}-{summary['maximum']} "
        f"(평균 {summary['mean']})"
    )


def render_markdown(inventory: dict[str, object]) -> str:
    normal = inventory["normal_release"]
    source = inventory["source_rom"]
    lines = [
        "# 하드 모드 밸런스 협의 기준표",
        "",
        "> 상태: 사용자 밸런스 승인 대기. 이 문서는 원판 값을 읽기만 하며,",
        "> 합의 전에는 하드 모드 수치나 병종을 어떤 ROM에도 적용하지 않는다.",
        "",
        "## 잠긴 기준판",
        "",
        f"- 일반 한국어판: `{normal['header_checksum']}`, "
        f"`{normal['sha256']}`",
        f"- 일본 원판: `{source['header_checksum']}`, `{source['sha256']}`",
        "- 일반 한국어판은 변경 불가 기준판이며 하드 모드는 별도 파일로 만든다.",
        "",
        "## 합의가 필요한 항목",
        "",
        "1. 시나리오 구간별 목표 난이도와 허용 재도전 횟수",
        "2. 적 지휘관 AT/DF 및 병사 수정 AT/DF 증가 공식과 상한",
        "3. 상위 용병 투입 시점과 기존 용병 교체 비율",
        "4. 후반 소환물 계열 병사 투입 시점과 편성 비율",
        "5. 보스·지원군·분기·엔딩·비기 시나리오 예외",
        "",
        "## 첫 결정: 목표 난이도",
        "",
        "| 선택 | 플레이 전제 | 주요 전투 예상 재도전 | 권장 |",
        "|:---|:---|:---:|:---:|",
    ]
    for option in inventory["balance_discussion"]["difficulty_options"]:
        retries = option["expected_retries_per_major_battle"]
        retry_text = (
            f"{retries[0]}회 이상"
            if retries[1] is None
            else f"{retries[0]}~{retries[1]}회"
        )
        lines.append(
            f"| {option['label']} | {option['assumption']} | "
            f"{retry_text} | {'예' if option['recommended'] else '-'} |"
        )

    lines.extend([
        "",
        "## 협의용 시나리오 구간 후보",
        "",
        "> 아래 구간은 비교를 위한 후보이며 아직 승인되지 않았다. 수치는",
        "> 일본 원판의 적군 진영 `04` 고정 레코드를 합산한 값이다.",
        "",
        "| 구간 | 장 | 적 | 숨김 | 특수 08 | LV | AT 보정 | DF 보정 | 용병 칸 |",
        "|:---|:---|---:|---:|---:|:---|:---|:---|---:|",
    ])
    for band in inventory["balance_discussion"]["candidate_scenario_bands"]:
        summary = band["original_side_04_summary"]
        numbers = band["scenarios"]
        scenario_text = (
            f"X1~X4"
            if band["id"] == "secret"
            else f"{numbers[0]}~{numbers[-1]}"
        )
        lines.append(
            f"| {band['label']} | {scenario_text} | "
            f"{summary['record_count']} | {summary['hidden_record_count']} | "
            f"{summary['side_08_record_count']} | "
            f"{_stat_cell(summary['level'])} | "
            f"{_stat_cell(summary['commander_at_modifier'])} | "
            f"{_stat_cell(summary['commander_df_modifier'])} | "
            f"{summary['filled_mercenary_slots']} |"
        )
    lines.extend([
        "",
        "각 구간의 승인 상태와 모든 사용자 선택은 현재 비어 있다. 목표",
        "난이도와 아래 협의 초안을 사용자가 명시적으로 승인하기 전에는",
        "어떤 값도 ROM에 적용하지 않는다.",
        "",
        "## 권장 협의 초안: 숙련자용 점증 하드",
        "",
        "> 상태: **미승인 제안**. 구현값이 아니며 일반판과 다른 ROM에도",
        "> 아직 적용되지 않았다.",
        "",
        "비기·노가다 없이 완주할 수 있되 상성·진형·장비 선택을 요구하는",
        "난이도를 목표로 한다. 적 LV는 올리지 않아 경험치와 성장 속도를",
        "바꾸지 않고, HP·MP도 원판을 유지한다.",
        "",
        "| 구간 | 장 | 지휘관 AT/DF | 병사 A+/D+ | 상위 용병 | 소환물 |",
        "|:---|:---:|:---:|:---:|:---:|:---:|",
    ])
    proposal = inventory["balance_discussion"]["recommended_unapproved_proposal"]
    for step in proposal["scenario_steps"]:
        scenarios = step["scenarios"]
        scenario_text = (
            str(scenarios[0])
            if len(scenarios) == 1
            else f"{scenarios[0]}~{scenarios[-1]}"
        )
        lines.append(
            f"| {step['label']} | {scenario_text} | "
            f"+{step['commander_at_delta']}/+{step['commander_df_delta']} | "
            f"+{step['soldier_at_correction_delta']}/"
            f"+{step['soldier_df_correction_delta']} | "
            f"{step['stronger_mercenary_slots_per_six']}/6 | "
            f"{step['summon_slots_per_six']}/6 |"
        )
    caps = proposal["global_rules"]["main_story_absolute_cap"]
    lines.extend([
        "",
        f"- 본편 지휘관 상한 후보: AT {caps['commander_at']}, "
        f"DF {caps['commander_df']}",
        f"- 본편 병사 보정 상한 후보: A+ {caps['soldier_at_correction']}, "
        f"D+ {caps['soldier_df_correction']}",
        "- 상위 용병은 빈칸을 채우지 않고 기존 용병 칸만 교체하며,",
        "  보병·창병·기병 등 상성과 수상·비행 같은 지형 역할을 보존한다.",
        "- 26장은 이름 있는 적 지휘관만 최대 1/6을 소환물로 교체한다.",
        "- 27장은 주요 지휘관 4/6, 일반 지휘관 최대 2/6만 소환물로",
        "  교체한다. 아니키(`94`)는 기본 하드 편성에서 제외한다.",
        "- X1~X4는 진입 시점과 원본 수치 차이가 커 본편 공식을 적용하지",
        "  않고 각각 조정한다.",
        "",
        "### 제안된 예외",
        "",
        "- 1장 레온(`0x1802FC`)·레아드(`0x180320`): 쓰러뜨리기 위한",
        "  일반 적이 아닌 연출용 강적이므로 자동 강화에서 제외한다.",
        "- 22장 진영 `08` 10개: 적대 대상으로 확인되었으므로 21~24장",
        "  공식에 포함하되 진영 `08`과 원작 이벤트 소유권은 보존한다.",
        "- 24장 베른하르트(`0x182B8A`): 이벤트 중 진영이 바뀌므로 고정",
        "  레코드 자동 강화에서 제외한다.",
        "- 25장 제시카(`0x182D62`): 아군 지원 이벤트이므로 제외한다.",
        "- 30장 미나의 메이지·세인트 두 레코드는 한 보스의 2단계로",
        "  취급하고 보너스를 중복 누적하지 않는다.",
        "- X4 베른하르트(`0x183902`): 적대 최종 보스지만 원본 AT87/DF61이",
        "  본편 상한보다 높아 X4 개별 조정만 적용한다.",
        "",
        "## 기술적으로 확정된 능력치 구조",
        "",
        "- 36바이트 고정 배치 레코드의 `+0x12/+0x13`은 지휘관",
        "  `AT/DF` 부호 있는 보정값이다. 원본 로더 `0x010E46..0x010ED6`가",
        "  이를 런타임 레코드 `+0x3A/+0x3B`로 복사한다.",
        "- 병사 상태창의 `A+/D+`는 고정 배치 레코드가 아니라 28바이트",
        "  클래스 레코드 `0x05EDDC + class_id * 0x1C`의",
        "  `+0x0F/+0x10`에서 온다.",
        "- 같은 클래스 레코드의 `+0x0B/+0x0C`는 병사의 기본 AT/DF,",
        "  `+0x0D`는 MV다. 아래 병종 비교는 이 원판 값을 사용한다.",
        "- 클래스 레코드는 아군·적군·NPC가 공유할 수 있다. 따라서 이 두",
        "  바이트를 전역으로 올리면 같은 클래스를 쓰는 일반판 아군까지",
        "  강해질 수 있으므로 하드 모드 구현에는 사용하지 않는다.",
        "- 승인 후에는 확장 ROM에 시나리오·배치별 적 전용 병사 보정표를",
        "  두고 고정 배치 로더 직후에만 적용한다. 일반 한국어판과 원본",
        "  클래스 표는 그대로 보존한다.",
        "- 아래 340개에는 처음에 숨겨진 고정 레코드 63개도 포함된다.",
        "  그중 53개는 적군 진영 `04`다. 원판의 증원 대부분은 새 레코드를",
        "  생성하지 않고 이 숨김 레코드를 이벤트로 공개한다.",
        "- 이벤트가 런타임 레코드의 클래스나 진영을 다시 쓰는 경우와 실제",
        "  비고정 생성이 있는지는 시나리오별 예외로 계속 감사한다.",
        "",
        "## 일본 원판 시나리오 분포",
        "",
        "| 장 | 전체 | 적군(04) | 기타 진영 | 숨김 | 적 LV | 적 AT | 적 DF | 적 용병 칸 |",
        "|---:|---:|---:|:---|---:|:---|:---|:---|---:|",
    ])
    for scenario in inventory["scenarios"]:
        summary = scenario["enemy_summary"]
        other_sides = ", ".join(
            f"{side}:{count}"
            for side, count in scenario["side_counts"].items()
            if side != "04"
        ) or "-"
        lines.append(
            f"| {scenario['number']} | {scenario['record_count']} | "
            f"{summary['record_count']} | {other_sides} | "
            f"{scenario['hidden_record_count']} | "
            f"{_stat_cell(summary['level'])} | "
            f"{_stat_cell(summary['at'])} | "
            f"{_stat_cell(summary['df'])} | "
            f"{summary['filled_mercenary_slots']} |"
        )

    lines.extend([
        "",
        "시나리오 22는 고정 레코드상 적군 진영 `04`가 1개뿐이고 특수 진영",
        "`08`이 10개다. 실기 진행과 클리어 프로브에서 이 10개가 모두 적대",
        "대상임을 확인했다. 승인 후 적 전용 공식에는 포함하되 진영 `08`과",
        "원작 이벤트 소유권은 그대로 보존한다.",
        "",
        "## 확인된 이벤트 예외",
        "",
        "- 시나리오 22: `08` 진영 10개와 숨김 베른하르트/엠퍼러",
        "  (`0x182822`, 진영 `04`)를 분리한다. 전자는 적대 대상으로",
        "  강화하되 진영값을 바꾸지 않는다.",
        "- 시나리오 24: `0x182B8A` 베른하르트/엠퍼러는 원작 이벤트가",
        "  진영을 바꾸는 레코드다. 고정 레코드 자동 강화에서 제외하고,",
        "  필요하면 런타임 이벤트 단계별 변경을 별도로 승인받는다.",
        "- 시나리오 25: 고정 레코드 `0x182D62`의 아군 제시카/워록은",
        "  이벤트 후 런타임에서 소서러 LV5, AT29, DF17로 바뀐다. 런타임",
        "  변경 뒤에도 적군 하드 모드 보너스 대상에서 제외한다.",
        "- 시나리오 30: `0x183724` 메이지와 숨김 `0x183748` 세인트는",
        "  미나의 2단계 변신 경로다. 별개의 보스로 중복 계산하지 않고,",
        "  승인된 보스 규칙을 각 단계에 의도한 만큼만 적용한다.",
        "- 비밀 시나리오 X4(31장): `0x183902` 진영 `08` 베른하르트는",
        "  클리어에 필요한 적대 최종 보스다. AT87/DF61로 본편 상한보다",
        "  이미 높으므로 본편 공식에서 제외하고 X4 안에서 개별 조정한다.",
        "",
        "## 원판 용병 슬롯 사용량",
        "",
        "| ID | 일본어 | 한국어 | 기본 AT/DF | MV | 첫 적군 장 | 적군 칸 | 전체 칸 |",
        "|:---:|:---|:---|:---:|---:|:---:|---:|---:|",
    ])
    combat_classes = {
        row["class_id"]: row
        for row in inventory["source_model"]["combat_class_catalog"]
    }
    for usage in inventory["source_model"]["mercenary_distribution"]:
        row = combat_classes[usage["class_id"]]
        lines.append(
            f"| `{row['class_id']}` | {row['japanese']} | {row['korean']} | "
            f"{row['base_at']}/{row['base_df']} | {row['movement']} | "
            f"{row['first_enemy_scenario'] or '-'} | "
            f"{row['enemy_side_04_slot_count']} | {row['all_fixed_slot_count']} |"
        )
    lines.extend([
        "",
        "## 소환물 원판 수치",
        "",
        "소환물 클래스 `8D..94`는 원판의 고정 배치 용병 6칸에서는 사용되지",
        "않는다. 하드 모드에 넣으면 단순 수치 상승뿐 아니라 이동·마법·상성도",
        "달라지므로 별도 투입 시점과 비율 승인이 필요하다.",
        "",
        "| ID | 한국어 | 기본 AT/DF | MV | 원판 적군 용병 칸 |",
        "|:---:|:---|:---:|---:|---:|",
    ])
    for row in inventory["source_model"]["combat_class_catalog"]:
        if row["group"] != "summon_class":
            continue
        lines.append(
            f"| `{row['class_id']}` | {row['korean']} | "
            f"{row['base_at']}/{row['base_df']} | {row['movement']} | "
            f"{row['enemy_side_04_slot_count']} |"
        )
    lines.extend([
        "",
        "각 레코드의 정확한 원본 주소와 6개 용병 칸은",
        "`localization/hard_mode_baseline.json`에 기록한다. 협의 초안과",
        "실제 승인값은 분리하며, 승인 전에는 빌드 프로필을 만들지 않는다.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the read-only hard-mode balance baseline"
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--normal-rom", type=Path, default=DEFAULT_NORMAL_ROM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when checked-in artifacts differ from generated output",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(args.source_rom, args.normal_rom)
    json_text = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    markdown_text = render_markdown(inventory)
    if args.check:
        if args.json.read_text(encoding="utf-8") != json_text:
            raise SystemExit(f"stale hard-mode baseline: {args.json}")
        if args.markdown.read_text(encoding="utf-8") != markdown_text:
            raise SystemExit(f"stale hard-mode discussion table: {args.markdown}")
        print("hard-mode baseline is current; normal release remains 99FD")
        return 0
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json_text, encoding="utf-8")
    args.markdown.write_text(markdown_text, encoding="utf-8")
    print(args.json)
    print(args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
