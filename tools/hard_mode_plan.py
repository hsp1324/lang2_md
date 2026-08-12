#!/usr/bin/env python3
"""Generate the exact, reviewable Standard Hard v1 change plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools import hard_mode_approval
from tools import hard_mode_baseline
from tools import hard_mode_npc_survival


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROM = hard_mode_baseline.DEFAULT_SOURCE_ROM
DEFAULT_NORMAL_ROM = hard_mode_baseline.DEFAULT_NORMAL_ROM
DEFAULT_JSON = ROOT / "localization/hard_mode_plan.json"
DEFAULT_MARKDOWN = ROOT / "docs/hard_mode_changes.md"
DEFAULT_BUILD_MANIFEST = ROOT / "localization/hard_mode_build.json"
DEFAULT_RUNTIME_VERIFICATION = (
    ROOT / "localization/hard_mode_runtime_verification.json"
)
DEFAULT_RUNTIME_SMOKE = (
    ROOT / "localization/hard_mode_scenario_smoke.json"
)
DEFAULT_RUNTIME_EXCEPTIONS = (
    ROOT / "localization/hard_mode_runtime_exceptions.json"
)

SECRET_STEP_SOURCE = {
    28: 11,
    29: 16,
    30: 21,
    31: 27,
}

CURATED_SUMMON_REPLACEMENTS = {
    (27, "0x18321A"): (
        {
            "slot": 4,
            "source_class_id": 0x87,
            "target_class_id": 0x8F,
        },
        {
            "slot": 5,
            "source_class_id": 0x87,
            "target_class_id": 0x8F,
        },
    ),
}

# The stock enemy-variant mercenary cache has ten entries.  The Korean build
# reuses the always-preloaded ordinary-hireable cache for 0x62..0x71, so these
# substitutions keep the approved same-family upgrades without allocating a
# new dynamic entry.  Scenario 13's Dark Guard promotion is omitted because
# no same-family ordinary fallback is stronger than Armor Soldier.
MAX_DYNAMIC_ENEMY_MERCENARY_CLASSES = 10
ENEMY_ORDINARY_MERCENARY_FIRST_CLASS = 0x62
ENEMY_ORDINARY_MERCENARY_LAST_CLASS = 0x71
CACHE_SAFE_MERCENARY_OVERRIDES = {
    (13, "0x181814", 0): 0x63,  # Pike 7E -> ordinary Phalanx 63
    (13, "0x181814", 1): 0x63,
    (13, "0x1818C8", 0): None,  # Armor Soldier 73 stays 73
    (13, "0x1818C8", 1): None,
    (15, "0x181CCC", 0): 0x6F,  # Gargoyle 82 -> ordinary Griffon 6F
    (15, "0x181CCC", 1): 0x6F,
}


def proposal_steps() -> dict[int, dict[str, Any]]:
    steps = {
        int(number): dict(step)
        for step in hard_mode_baseline.RECOMMENDED_DISCUSSION_PROPOSAL[
            "scenario_steps"
        ]
        for number in step["scenarios"]
    }
    for scenario, source_scenario in SECRET_STEP_SOURCE.items():
        secret_step = dict(steps[source_scenario])
        secret_step["label"] = f"비밀 X{scenario - 27}"
        secret_step["scenarios"] = [scenario]
        secret_step["mapped_from_scenario"] = source_scenario
        steps[scenario] = secret_step
    return steps


def target_records(
    scenario: dict[str, Any],
) -> list[dict[str, Any]]:
    number = int(scenario["number"])
    special_22 = set(
        hard_mode_baseline.SCENARIO_22_HOSTILE_SIDE_08_OFFSETS
    )
    exclusions = hard_mode_baseline.MAIN_STORY_AUTOMATIC_EXCLUDED_OFFSETS
    result = []
    for record in scenario["records"]:
        offset = str(record["offset"])
        hostile = record["side_id"] == "04"
        if number == 22 and offset in special_22:
            hostile = True
        if not hostile or offset in exclusions:
            continue
        result.append(record)
    return result


def capped_increase(original: int, delta: int, cap: int) -> int:
    # A secret-stage original may already exceed the main-story cap. Never
    # lower source difficulty merely because the mapped band has a lower cap.
    return max(original, min(original + delta, cap))


def proposed_mercenaries(
    original: list[int],
    quota: int,
) -> tuple[list[int], list[dict[str, int]]]:
    upgrade_map = dict(
        hard_mode_baseline.CONSERVATIVE_MERCENARY_UPGRADE_PAIRS
    )
    result = list(original)
    changes = []
    for slot, source_id in enumerate(original):
        if len(changes) >= quota:
            break
        target_id = upgrade_map.get(source_id)
        if target_id is None:
            continue
        result[slot] = target_id
        changes.append({
            "slot": slot,
            "source_class_id": source_id,
            "target_class_id": target_id,
        })
    return result, changes


def proposed_summon_replacements(
    scenario: int,
    offset: str,
    original: list[int],
    planned: list[int],
) -> tuple[list[int], list[dict[str, int]]]:
    changes = CURATED_SUMMON_REPLACEMENTS.get((scenario, offset), ())
    result = list(planned)
    for change in changes:
        slot = int(change["slot"])
        source_id = int(change["source_class_id"])
        target_id = int(change["target_class_id"])
        if original[slot] != source_id:
            raise ValueError(
                f"Scenario {scenario} summon source changed at {offset} "
                f"slot {slot}: expected {source_id:02X}, "
                f"got {original[slot]:02X}"
            )
        if result[slot] != source_id:
            raise ValueError(
                f"Scenario {scenario} conventional mercenary upgrade "
                f"overlaps summon slot {slot} at {offset}"
            )
        result[slot] = target_id
    return result, [dict(change) for change in changes]


def apply_cache_safe_mercenary_overrides(
    scenario: int,
    offset: str,
    original: list[int],
    planned: list[int],
    changes: list[dict[str, int]],
) -> tuple[list[int], list[dict[str, int]]]:
    result = list(planned)
    updated_changes = [dict(change) for change in changes]
    for slot in range(len(original)):
        key = (scenario, offset, slot)
        if key not in CACHE_SAFE_MERCENARY_OVERRIDES:
            continue
        target = CACHE_SAFE_MERCENARY_OVERRIDES[key]
        matching = [
            change for change in updated_changes
            if int(change["slot"]) == slot
        ]
        if len(matching) != 1:
            raise ValueError(
                f"cache-safe mercenary override lost its planned change: "
                f"Scenario {scenario} {offset} slot {slot}"
            )
        if target is None:
            result[slot] = original[slot]
            updated_changes.remove(matching[0])
        else:
            result[slot] = target
            matching[0]["target_class_id"] = target
    return result, updated_changes


def _record_mercenary_ids(record: dict[str, Any]) -> list[int]:
    return [
        0xFF if row is None else int(row["class_id"], 16)
        for row in record["mercenaries"]
    ]


def dynamic_enemy_mercenary_class_ids(
    scenario: dict[str, Any],
    planned_records: list[dict[str, Any]],
) -> list[int]:
    """Return every non-ordinary fixed-record class loaded by the map cache.

    The stock loader does not restrict this cache to side 0x04 enemies. NPC
    side 0x03 and special side 0x08 records share it as well; Scenario 31's
    side 0x08 Ballista is the retained proof. Counting only hostile records
    can therefore understate the ten-row hardware/runtime capacity.
    """
    planned_by_offset = {
        str(record["offset"]): record["mercenaries"]["planned"]
        for record in planned_records
    }
    classes: set[int] = set()
    for record in scenario["records"]:
        offset = str(record["offset"])
        if record["side_id"] == "00":
            continue
        mercenaries = planned_by_offset.get(
            offset,
            _record_mercenary_ids(record),
        )
        classes.update(
            class_id
            for class_id in mercenaries
            if class_id != 0xFF
            and not (
                ENEMY_ORDINARY_MERCENARY_FIRST_CLASS
                <= class_id
                <= ENEMY_ORDINARY_MERCENARY_LAST_CLASS
            )
        )
    return sorted(classes)


def build_plan(
    source_rom: Path = DEFAULT_SOURCE_ROM,
    normal_rom: Path = DEFAULT_NORMAL_ROM,
) -> dict[str, Any]:
    baseline = hard_mode_baseline.build_inventory(source_rom, normal_rom)
    approval_manifest = hard_mode_approval.load_manifest()
    approved = approval_manifest["status"] == "approved"
    steps = proposal_steps()
    caps = hard_mode_baseline.RECOMMENDED_DISCUSSION_PROPOSAL[
        "global_rules"
    ]["main_story_absolute_cap"]

    scenarios = []
    record_count = 0
    commander_change_count = 0
    soldier_correction_count = 0
    mercenary_replacement_count = 0
    summon_replacement_count = 0
    for scenario in baseline["scenarios"]:
        number = int(scenario["number"])
        step = steps[number]
        records = []
        for record in target_records(scenario):
            original_at = int(record["commander_at_modifier"])
            original_df = int(record["commander_df_modifier"])
            original_soldier_at = int(record["soldier_at_correction"])
            original_soldier_df = int(record["soldier_df_correction"])
            proposed_at = capped_increase(
                original_at,
                int(step["commander_at_delta"]),
                int(caps["commander_at"]),
            )
            proposed_df = capped_increase(
                original_df,
                int(step["commander_df_delta"]),
                int(caps["commander_df"]),
            )
            proposed_soldier_at = capped_increase(
                original_soldier_at,
                int(step["soldier_at_correction_delta"]),
                int(caps["soldier_at_correction"]),
            )
            proposed_soldier_df = capped_increase(
                original_soldier_df,
                int(step["soldier_df_correction_delta"]),
                int(caps["soldier_df_correction"]),
            )
            original_mercenaries = _record_mercenary_ids(record)
            mercenaries, mercenary_changes = proposed_mercenaries(
                original_mercenaries,
                int(step["stronger_mercenary_slots_per_six"]),
            )
            mercenaries, mercenary_changes = (
                apply_cache_safe_mercenary_overrides(
                    number,
                    str(record["offset"]),
                    original_mercenaries,
                    mercenaries,
                    mercenary_changes,
                )
            )
            mercenaries, summon_changes = proposed_summon_replacements(
                number,
                str(record["offset"]),
                original_mercenaries,
                mercenaries,
            )
            commander_changed = (
                proposed_at != original_at or proposed_df != original_df
            )
            soldier_changed = (
                proposed_soldier_at != original_soldier_at
                or proposed_soldier_df != original_soldier_df
            )
            commander_change_count += commander_changed
            soldier_correction_count += soldier_changed
            mercenary_replacement_count += len(mercenary_changes)
            summon_replacement_count += len(summon_changes)
            record_count += 1
            records.append({
                "index": int(record["index"]),
                "offset": str(record["offset"]),
                "side_id": str(record["side_id"]),
                "hidden": bool(record["hidden"]),
                "name_id": str(record["name_id"]),
                "name_korean": str(record["name_korean"]),
                "class_id": str(record["class_id"]),
                "class_korean": str(record["class_korean"]),
                "commander": {
                    "at": {"original": original_at, "planned": proposed_at},
                    "df": {"original": original_df, "planned": proposed_df},
                },
                "enemy_soldier_correction": {
                    "at": {
                        "original": original_soldier_at,
                        "planned": proposed_soldier_at,
                    },
                    "df": {
                        "original": original_soldier_df,
                        "planned": proposed_soldier_df,
                    },
                    "implementation": (
                        "expanded-ROM per-record table; shared class records "
                        "remain byte-identical"
                    ),
                },
                "mercenaries": {
                    "original": original_mercenaries,
                    "planned": mercenaries,
                    "changes": mercenary_changes,
                },
                "summon_replacement": {
                    "planned": bool(summon_changes),
                    "changes": summon_changes,
                    "reason": (
                        (
                            "runtime-guarded safe fallback: same-family "
                            "Vampire Bat 87 -> White Dragon 8F; fixed units "
                            "do not rely on natural magic ownership"
                        )
                        if summon_changes
                        else (
                            "keep original: outside the approved Scenario "
                            "26/27 scope or no same-family nondecreasing "
                            "AT/DF candidate passed every runtime guard"
                        )
                    ),
                },
            })
        dynamic_classes = dynamic_enemy_mercenary_class_ids(
            scenario,
            records,
        )
        if len(dynamic_classes) > MAX_DYNAMIC_ENEMY_MERCENARY_CLASSES:
            raise ValueError(
                f"Scenario {number} needs {len(dynamic_classes)} dynamic "
                "enemy mercenary classes; the battle cache holds only "
                f"{MAX_DYNAMIC_ENEMY_MERCENARY_CLASSES}: "
                + ", ".join(f"0x{value:02X}" for value in dynamic_classes)
            )
        scenarios.append({
            "number": number,
            "label": step["label"],
            "mapped_from_scenario": step.get("mapped_from_scenario"),
            "formula": {
                "commander_at_delta": int(step["commander_at_delta"]),
                "commander_df_delta": int(step["commander_df_delta"]),
                "soldier_at_correction_delta": int(
                    step["soldier_at_correction_delta"]
                ),
                "soldier_df_correction_delta": int(
                    step["soldier_df_correction_delta"]
                ),
                "stronger_mercenary_slots_per_six": int(
                    step["stronger_mercenary_slots_per_six"]
                ),
                "summon_slots_per_six": int(
                    step["summon_slots_per_six"]
                ),
            },
            "target_record_count": len(records),
            "enemy_mercenary_cache": {
                "dynamic_capacity": MAX_DYNAMIC_ENEMY_MERCENARY_CLASSES,
                "dynamic_class_ids": dynamic_classes,
                "dynamic_class_count": len(dynamic_classes),
                "ordinary_classes_reuse_fixed_cache": True,
            },
            "records": records,
        })

    return {
        "schema_version": 1,
        "profile_id": hard_mode_baseline.RECOMMENDED_DISCUSSION_PROPOSAL["id"],
        "status": (
            "approved_balance_plan"
            if approved
            else "planned_pending_explicit_approval"
        ),
        "rom_values_applied": False,
        "normal_release": baseline["normal_release"],
        "approval": {
            "manifest": str(
                hard_mode_approval.DEFAULT_APPROVAL.relative_to(ROOT)
            ),
            "status": approval_manifest["status"],
            "proposal_sha256": hard_mode_approval.subject_sha256(),
            "required_confirmation": hard_mode_approval.EXPECTED_CONFIRMATION,
        },
        "implementation_policy": {
            "normal_release_immutable": True,
            "original_release_immutable": True,
            "commander_stats": "fixed scenario records",
            "enemy_soldier_corrections": (
                "expanded-ROM per-record table and loader hook"
            ),
            "shared_class_records_modified": False,
            "mercenary_policy": (
                "conservative same-family replacements first, left-to-right "
                "up to the per-commander quota; empty slots stay empty; "
                "every scenario stays within the ten-entry dynamic battle "
                "sprite cache"
            ),
            "enemy_ordinary_mercenary_cache_reused": True,
            "enemy_dynamic_mercenary_cache_capacity": (
                MAX_DYNAMIC_ENEMY_MERCENARY_CLASSES
            ),
            "conditional_mercenary_pairs_applied": False,
            "summon_units_applied": True,
            "summon_policy": (
                "Scenario 26 keeps the original formation; Scenario 27 "
                "record 0x18321A slots 4-5 replace Vampire Bat 87 with "
                "White Dragon 8F after fixed loading, ordinary movement, "
                "direct attack, and first-turn event verification"
            ),
            "fixed_summon_natural_magic_required": False,
            "npc_survival_protection": (
                "Hard only: loss-condition NPC commander DF offsets the "
                "scenario enemy commander AT delta, and NPC soldier D+ "
                "offsets the enemy soldier A+ delta"
            ),
            "runtime_exception_manifest": str(
                DEFAULT_RUNTIME_EXCEPTIONS.relative_to(ROOT)
            ),
            "runestone_expectation": (
                hard_mode_baseline.RECOMMENDED_DISCUSSION_PROPOSAL[
                    "global_rules"
                ]["runestone_expectation"]
            ),
            "runestone_budget": (
                hard_mode_baseline.RECOMMENDED_DISCUSSION_PROPOSAL[
                    "global_rules"
                ]["runestone_budget"]
            ),
        },
        "summary": {
            "scenario_count": len(scenarios),
            "target_record_count": record_count,
            "commander_change_record_count": commander_change_count,
            "soldier_correction_record_count": soldier_correction_count,
            "mercenary_replacement_slot_count": mercenary_replacement_count,
            "summon_replacement_slot_count": summon_replacement_count,
            "npc_survival_protection_record_count": (
                hard_mode_npc_survival.EXPECTED_RECORD_COUNT
            ),
        },
        "npc_survival_protection": (
            hard_mode_npc_survival.build_section(baseline, steps)
        ),
        "automatic_exclusions": [
            {
                "scenario": 1,
                "offset": "0x1802FC",
                "name": "레온",
                "reason": "연출용 강적",
            },
            {
                "scenario": 1,
                "offset": "0x180320",
                "name": "레아드",
                "reason": "연출용 강적",
            },
            {
                "scenario": 24,
                "offset": "0x182B8A",
                "name": "베른하르트",
                "reason": "원작 이벤트에서 진영 전환",
            },
            {
                "scenario": 25,
                "offset": "0x182D62",
                "name": "제시카",
                "reason": "아군 지원 이벤트",
            },
            {
                "scenario": 31,
                "offset": "0x183902",
                "name": "베른하르트",
                "reason": "X4 원본 AT/DF가 본편 상한보다 높은 특수 보스",
            },
        ],
        "scenarios": scenarios,
    }


def _fmt_mercenaries(values: list[int]) -> str:
    return " ".join("--" if value == 0xFF else f"{value:02X}" for value in values)


def render_markdown(plan: dict[str, Any]) -> str:
    normal = plan["normal_release"]
    summary = plan["summary"]
    npc_protection = plan["npc_survival_protection"]
    build = (
        json.loads(DEFAULT_BUILD_MANIFEST.read_text(encoding="utf-8"))
        if DEFAULT_BUILD_MANIFEST.exists()
        else None
    )
    runtime = (
        json.loads(
            DEFAULT_RUNTIME_VERIFICATION.read_text(encoding="utf-8")
        )
        if DEFAULT_RUNTIME_VERIFICATION.exists()
        else {"scenarios": []}
    )
    runtime_scenarios = {
        int(row["number"]): row for row in runtime["scenarios"]
    }
    runtime_smoke = (
        json.loads(DEFAULT_RUNTIME_SMOKE.read_text(encoding="utf-8"))
        if DEFAULT_RUNTIME_SMOKE.exists()
        else {"scenarios": []}
    )
    smoke_scenarios = {
        int(row["number"]): row for row in runtime_smoke["scenarios"]
    }
    runtime_exceptions = (
        json.loads(
            DEFAULT_RUNTIME_EXCEPTIONS.read_text(encoding="utf-8")
        )
        if DEFAULT_RUNTIME_EXCEPTIONS.exists()
        else {"exceptions": []}
    )
    lines = [
        "# 랑그릿사 II 표준 하드 모드 변경 기록",
        "",
        "> 이 문서는 일반 한국어판과 분리된 하드 모드 전용 기록이다.",
        "> 표준 하드 수치는 승인되어 후보 ROM에 적용되었다. 실제 난이도와",
        "> 진행 가능성은 사용자의 전체 플레이 결과로 계속 조정한다.",
        "",
        "## 기준판과 상태",
        "",
        f"- 기준 ROM: `roms/releases/Langrisser II (Korean v1.0.0).md`",
        f"- 체크섬: `{normal['header_checksum']}`",
        f"- SHA-256: `{normal['sha256']}`",
        f"- 프로필: `{plan['profile_id']}`",
        f"- 상태: `{plan['status']}`",
        f"- 승인 상태: `{plan['approval']['status']}`",
        f"- 필요한 승인 문구: `{plan['approval']['required_confirmation']}`",
        "- 원작 디자인판 수정: 없음",
        "- 일반판 수정: 없음",
    ]
    if build is not None:
        lines.extend([
            (
                "- 하드 후보 ROM: "
                f"`{build['release']['output']}`"
            ),
            f"- 하드 체크섬: `{build['hard']['header_checksum']}`",
            f"- 하드 SHA-256: `{build['hard']['sha256']}`",
        ])
    lines.extend([
        "",
        "## 승인·적용 요약",
        "",
        f"- 시나리오: {summary['scenario_count']}개",
        f"- 대상 적 레코드: {summary['target_record_count']}개",
        f"- 지휘관 AT/DF 변경: {summary['commander_change_record_count']}개",
        f"- 적 전용 병사 A+/D+ 변경: {summary['soldier_correction_record_count']}개",
        (
            "- 패배 조건 NPC 생존 보정: "
            f"{summary['npc_survival_protection_record_count']}명"
        ),
        f"- 보수적 용병 승급: {summary['mercenary_replacement_slot_count']}칸",
        (
            "- 소환물 교체: "
            f"{summary['summon_replacement_slot_count']}칸 "
            "(27장 뱀파이어배트 → 화이트드래곤 안전 대체)"
        ),
        "",
        "## 구현 원칙",
        "",
        "- 지휘관 AT/DF는 시나리오 고정 배치 레코드만 수정한다.",
        "- 병사 A+/D+는 공용 클래스 표를 수정하지 않는다. 확장 ROM의",
        "  적 전용 레코드 표와 로더 훅으로만 적용한다.",
        "- 용병은 채워진 칸만 같은 역할의 보수적 상위 병종으로 바꾼다.",
        "- 고정 소환물은 일반 적 AI의 이동·직접 공격·이벤트 진행을 모두",
        "  통과한 같은 계열 비감소 후보만 사용한다. 고정 레코드에는 자연",
        "  마법 권한이 붙지 않으므로 마법 사용을 전제로 편성하지 않는다.",
        "- 이벤트 진영 전환, 아군 지원, 연출용 강적은 자동 강화에서 뺀다.",
        "- 모든 변경은 주소와 전후 값을 아래 표 및 JSON 원장에 남긴다.",
        "",
        "## 패배 조건 NPC 생존 보정",
        "",
        (
            "- 사용자 제보: [하드판 NPC 생존 난도 문제]("
            f"{npc_protection['source_report']['url']})"
        ),
        (
            "- 적용 범위: 패배 조건에 사망·전멸이 직접 연결된 "
            f"9개 장의 고정 NPC {npc_protection['record_count']}명만 대상이다."
        ),
        "- 원작 디자인판과 최신 디자인 일반판은 0바이트 변경이며, 하드판에만 적용한다.",
        "- NPC 지휘관 DF에는 같은 장의 적 지휘관 AT 강화분을, NPC 병사",
        "  D+에는 같은 장의 적 병사 A+ 강화분을 더해 하드 강화의 비대칭만 상쇄한다.",
        "- NPC AT, 병사 A+, 이름, 클래스, 레벨, AI, 초기 배치, 용병은 바꾸지 않는다.",
        "- 리아나·제시카처럼 원작이 저장된 동료 성장값으로 다시 계산하는 NPC는",
        "  재계산 뒤의 실제 DF/D+에 같은 보정분만 더해 현재 클래스와 레벨을 보존한다.",
        "",
        "| 장 | 패배 조건 | 주소 | NPC/클래스 | 지휘관 DF | 병사 A+/D+ |",
        "|---:|:---|:---:|:---|:---:|:---:|",
    ])
    for scenario in npc_protection["scenarios"]:
        for record in scenario["records"]:
            commander_df = record["commander_df"]
            soldier = record["soldier_correction"]
            lines.append(
                f"| {scenario['number']} | {scenario['loss_condition']} | "
                f"`{record['offset']}` | {record['name_korean']}/"
                f"{record['class_korean']} | {commander_df['original']} → "
                f"{commander_df['planned']} | {soldier['at']}/"
                f"{soldier['df']['original']} → {soldier['at']}/"
                f"{soldier['df']['planned']} |"
            )
    lines.extend([
        "",
        "## 룬스톤 성장 전제",
        "",
        "| 구간 | 플레이어 성장 전제 | 적 지휘관 AT/DF | 병사 A+/D+ | 상위 용병 |",
        "|:---|:---|:---:|:---:|:---:|",
    ])
    for step in hard_mode_baseline.RECOMMENDED_DISCUSSION_PROPOSAL[
        "scenario_steps"
    ]:
        scenarios = step["scenarios"]
        scenario_label = (
            str(scenarios[0])
            if len(scenarios) == 1
            else f"{scenarios[0]}~{scenarios[-1]}"
        )
        lines.append(
            f"| {scenario_label}장 ({step['label']}) | "
            f"{step.get('runestone_assumption', '룬스톤 재육성 없이 진행')} | "
            f"+{step['commander_at_delta']}/+{step['commander_df_delta']} | "
            f"+{step['soldier_at_correction_delta']}/"
            f"+{step['soldier_df_correction_delta']} | "
            f"최대 {step['stronger_mercenary_slots_per_six']}/6칸 |"
        )

    lines.extend([
        "",
        "- 1~15장은 룬스톤을 쓰지 않아도 완주 가능한 성장선을 유지한다.",
        "- 16~20장은 파티 전체 누적 1개 사용을 권장하고, 21장부터는",
        "  정상 입수한 룬스톤을 실제로 사용한 전력을 기준으로 검증한다.",
        "- 25~27장은 파티 전체에서 룬스톤 2개를 사용한 상태를 전제로",
        "  한다. 한 명에게 2개 또는 주력 두 명에게 1개씩 배분할 수 있다.",
        "- 전 캐릭터의 2회 재육성이나 숨겨진 추가 룬스톤은 요구하지 않는다.",
        "  27장은 룬스톤 없이 안정적으로 돌파할 수 없도록 조정한다.",
        "- 비밀 시나리오는 진입 시점에 대응하는 본편 구간의 전제를 따른다.",
        "",
        "## 장별 요약",
        "",
        "| 장 | 구간 | 대상 | AT/DF | 병사 A+/D+ | 용병 칸 | 소환물 | 검증 |",
        "|---:|:---|---:|:---:|:---:|---:|---:|:---|",
    ])
    for scenario in plan["scenarios"]:
        records = scenario["records"]
        commander = sum(
            row["commander"]["at"]["original"]
            != row["commander"]["at"]["planned"]
            or row["commander"]["df"]["original"]
            != row["commander"]["df"]["planned"]
            for row in records
        )
        soldier = sum(
            row["enemy_soldier_correction"]["at"]["original"]
            != row["enemy_soldier_correction"]["at"]["planned"]
            or row["enemy_soldier_correction"]["df"]["original"]
            != row["enemy_soldier_correction"]["df"]["planned"]
            for row in records
        )
        mercenary = sum(
            len(row["mercenaries"]["changes"]) for row in records
        )
        summons = sum(
            len(row["summon_replacement"]["changes"]) for row in records
        )
        verification = runtime_scenarios.get(int(scenario["number"]))
        smoke = smoke_scenarios.get(int(scenario["number"]))
        if (
            verification is not None
            and verification["status"] == "runtime_loader_verified"
        ):
            verification_label = "실기 보존 확인"
        elif (
            smoke is not None
            and smoke["status"] == "runtime_loader_smoke_verified"
        ):
            verification_label = "출격 적재 확인"
        else:
            verification_label = "미시작"
        lines.append(
            f"| {scenario['number']} | {scenario['label']} | "
            f"{len(records)} | {commander} | {soldier} | {mercenary} | "
            f"{summons} | {verification_label} |"
        )

    lines.extend([
        "",
        "## 자동 제외",
        "",
        "| 장 | 주소 | 대상 | 이유 |",
        "|---:|:---:|:---|:---|",
    ])
    for row in plan["automatic_exclusions"]:
        lines.append(
            f"| {row['scenario']} | `{row['offset']}` | {row['name']} | "
            f"{row['reason']} |"
        )

    lines.extend([
        "",
        "## 원작 런타임 재작성 예외",
        "",
        "| 장 | 주소 | 대상 | 엄격 검증 | 동적 필드 | 처리 |",
        "|---:|:---:|:---|:---|:---|:---|",
    ])
    for row in runtime_exceptions["exceptions"]:
        strict_fields = ", ".join(row["strict_runtime_fields"])
        dynamic_fields = ", ".join(row["runtime_overridden_fields"])
        lines.append(
            f"| {row['scenario']} | `{row['fixed_record_offset']}` | "
            f"{row['name_korean']}/{row['class_korean']} | "
            f"`{strict_fields}` | `{dynamic_fields}` | "
            f"{row['balance_policy']} |"
        )
    lines.extend([
        "",
        "- 이 예외는 하드 ROM의 오류를 숨기는 허용 목록이 아니다. 두 개의",
        "  서로 다른 정상 저장 상태에서 같은 고정 레코드가 로스터 성장값으로",
        "  다시 쓰이는 원작 동작을 확인한 경우만 기록한다.",
        "- 예외로 적힌 동적 필드 외의 신원·클래스·용병·나머지 적 레코드는",
        "  계속 바이트 단위로 엄격하게 검사한다.",
    ])

    lines.extend([
        "",
        "## 레코드별 변경",
        "",
        "| 장 | 주소 | 적/클래스 | 지휘관 AT/DF | 병사 A+/D+ | 용병 전 → 후 |",
        "|---:|:---:|:---|:---:|:---:|:---|",
    ])
    for scenario in plan["scenarios"]:
        for row in scenario["records"]:
            commander = row["commander"]
            soldier = row["enemy_soldier_correction"]
            mercenaries = row["mercenaries"]
            lines.append(
                f"| {scenario['number']} | `{row['offset']}` | "
                f"{row['name_korean']}/{row['class_korean']} | "
                f"{commander['at']['original']}/{commander['df']['original']} "
                f"→ {commander['at']['planned']}/{commander['df']['planned']} | "
                f"{soldier['at']['original']}/{soldier['df']['original']} "
                f"→ {soldier['at']['planned']}/{soldier['df']['planned']} | "
                f"`{_fmt_mercenaries(mercenaries['original'])}` → "
                f"`{_fmt_mercenaries(mercenaries['planned'])}` |"
            )

    lines.extend([
        "",
        "## 실기 검증 기록",
        "",
        "- 후보 ROM 생성과 주소·체크섬·SRAM 호환 정적 검사는 완료했다.",
        "- 자동 에뮬레이터 완주 검증은 사용자의 요청에 따라 생략하고,",
        "  장별 진입·런타임 적재·이벤트 진행을 단계적으로 검증한다.",
        "- 실제 난이도, 진행 가능성, 증원·턴 이벤트·승패 조건은 사용자가",
        "  플레이하며 검증하고 발견한 문제를 이 문서에 누적한다.",
        "- 사용자가 명시적으로 릴리스했다고 말하기 전에는 번역과 밸런스",
        "  버전을 `1.0.0/1.0.0`으로 유지하고 후보 ROM만 교체한다.",
        "- 수정본은 같은 파일명에 적용하며 게임 내 SRAM 저장을 유지한다.",
        "  에뮬레이터 상태 저장은 호환을 보장하지 않는다.",
        "- `python3 tools/verify_hard_mode_scenario_runtime.py --scenario N`은",
        "  장별 자동 배치·출격 뒤 모든 하드 대상의 실제 RAM 값을 대조하고",
        "  `localization/hard_mode_scenario_smoke.json`에 즉시 기록한다.",
        "- 원작이 플레이 가능 캐릭터의 성장값으로 적 레코드를 다시 쓰는",
        "  예외는 `localization/hard_mode_runtime_exceptions.json`에서만",
        "  관리하며 검증기가 지정된 동적 필드만 제외한다.",
    ])
    coverage = runtime_smoke.get("coverage")
    if coverage is not None:
        lines.extend([
            (
                "- 장별 런타임 적재 범위: "
                f"`{len(coverage['verified_scenarios'])}/"
                f"{coverage['scenario_count']}`장 확인, "
                f"누락 `{coverage['missing_scenarios']}`."
            ),
            (
                "- 자동 출격 원장과 깊은 보존 증거의 합집합이 31장을 "
                "모두 덮어야 회귀 테스트가 통과한다."
            ),
        ])
    for scenario_number in sorted(runtime_scenarios):
        evidence = runtime_scenarios[scenario_number]
        lines.extend([
            "",
            f"### {scenario_number}장",
            "",
            (
                f"- 하드 후보 `{runtime['hard_rom']['md_checksum']}`을 "
                f"{evidence['entry']} 경로로 실행해 "
                f"{evidence['endpoint']}까지 정상 진입했다."
            ),
            f"- 보존 상태: `{evidence['gst']}`",
            f"- 화면: `{evidence['capture']}`",
        ])
        for group in evidence["verified_groups"]:
            commander_at, commander_df = group["commander_at_df"]
            soldier_at, soldier_df = group["soldier_at_df"]
            mercenaries = " ".join(group["mercenaries"])
            target = "하드 대상" if group["hard_target"] else "자동 강화 제외"
            lines.append(
                f"- {group['name']} 런타임 그룹 "
                f"{group['runtime_group']} ({target})은 지휘관 `AT/DF "
                f"{commander_at}/{commander_df}`, 병사 수정 `A+/D+ "
                f"{soldier_at}/{soldier_df}`, 용병 `{mercenaries}`로 "
                "적재됐다."
            )
        lines.extend([
            (
                "- `python3 tools/verify_hard_mode_runtime_evidence.py`로 "
                "보존 상태의 해시와 런타임 그룹을 재검증할 수 있다."
            ),
            f"- 남은 검증: {evidence['remaining']}",
        ])
    lines.extend([
        "",
        "정확한 변경 원장은 `localization/hard_mode_plan.json`, 실제 빌드",
        "결과는 `localization/hard_mode_build.json`, 실기 상태는",
        "`localization/hard_mode_runtime_verification.json`이다.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Standard Hard v1 per-record change plan"
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--normal-rom", type=Path, default=DEFAULT_NORMAL_ROM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan(args.source_rom, args.normal_rom)
    json_text = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    markdown_text = render_markdown(plan)
    if args.check:
        if args.json.read_text(encoding="utf-8") != json_text:
            raise SystemExit(f"stale hard-mode plan: {args.json}")
        if args.markdown.read_text(encoding="utf-8") != markdown_text:
            raise SystemExit(f"stale hard-mode change log: {args.markdown}")
        print(
            "hard-mode plan is current; plan generation itself does not "
            "write ROM values"
        )
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
