#!/usr/bin/env python3
"""Generate the exact, reviewable Standard Hard v1 change plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools import hard_mode_approval
from tools import hard_mode_baseline


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROM = hard_mode_baseline.DEFAULT_SOURCE_ROM
DEFAULT_NORMAL_ROM = hard_mode_baseline.DEFAULT_NORMAL_ROM
DEFAULT_JSON = ROOT / "localization/hard_mode_plan.json"
DEFAULT_MARKDOWN = ROOT / "docs/hard_mode_changes.md"
DEFAULT_BUILD_MANIFEST = ROOT / "localization/hard_mode_build.json"
DEFAULT_RUNTIME_VERIFICATION = (
    ROOT / "localization/hard_mode_runtime_verification.json"
)

SECRET_STEP_SOURCE = {
    28: 11,
    29: 16,
    30: 21,
    31: 27,
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


def _record_mercenary_ids(record: dict[str, Any]) -> list[int]:
    return [
        0xFF if row is None else int(row["class_id"], 16)
        for row in record["mercenaries"]
    ]


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
                    "planned": False,
                    "reason": (
                        "deferred until ordinary fixed-enemy attack and "
                        "natural-magic runtime guards pass"
                    ),
                },
            })
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
            "commander_stats": "fixed scenario records",
            "enemy_soldier_corrections": (
                "expanded-ROM per-record table and loader hook"
            ),
            "shared_class_records_modified": False,
            "mercenary_policy": (
                "conservative same-family replacements first, left-to-right "
                "up to the per-commander quota; empty slots stay empty"
            ),
            "conditional_mercenary_pairs_applied": False,
            "summon_units_applied": False,
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
            "summon_replacement_slot_count": 0,
        },
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
        "- 일반판 수정: 없음",
    ]
    if build is not None:
        lines.extend([
            (
                "- 하드 후보 ROM: "
                f"`roms/releases/{build['release']['rom_filename']}`"
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
        f"- 보수적 용병 승급: {summary['mercenary_replacement_slot_count']}칸",
        "- 소환물 교체: 0칸 (고정 적의 일반 공격·자연 마법 검증 전 보류)",
        "",
        "## 구현 원칙",
        "",
        "- 지휘관 AT/DF는 시나리오 고정 배치 레코드만 수정한다.",
        "- 병사 A+/D+는 공용 클래스 표를 수정하지 않는다. 확장 ROM의",
        "  적 전용 레코드 표와 로더 훅으로만 적용한다.",
        "- 용병은 채워진 칸만 같은 역할의 보수적 상위 병종으로 바꾼다.",
        "- 이벤트 진영 전환, 아군 지원, 연출용 강적은 자동 강화에서 뺀다.",
        "- 모든 변경은 주소와 전후 값을 아래 표 및 JSON 원장에 남긴다.",
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
        verification = runtime_scenarios.get(int(scenario["number"]))
        verification_label = (
            "런타임 적재 확인"
            if verification is not None
            and verification["status"] == "runtime_loader_verified"
            else "미시작"
        )
        lines.append(
            f"| {scenario['number']} | {scenario['label']} | "
            f"{len(records)} | {commander} | {soldier} | {mercenary} | "
            f"0 | {verification_label} |"
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
