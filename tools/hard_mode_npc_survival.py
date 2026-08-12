#!/usr/bin/env python3
"""Describe and validate the Hard-only fixed-NPC survival compensation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator


REPORT_URL = "https://arca.live/b/langrisser/179646819"


@dataclass(frozen=True)
class ProtectionTarget:
    scenario: int
    loss_condition: str
    commander_df_delta: int
    soldier_df_delta: int
    offsets: tuple[str, ...]


# Only fixed side-03 NPCs whose death (or group annihilation) directly causes
# defeat are in scope.  Support units without a loss condition stay untouched.
TARGETS = (
    ProtectionTarget(1, "리아나 사망", 2, 1, ("0x1801DC",)),
    ProtectionTarget(2, "리아나 사망", 2, 1, ("0x1803FC",)),
    ProtectionTarget(3, "리아나 사망", 2, 1, ("0x180520",)),
    ProtectionTarget(
        4,
        "리아나 사망 또는 사제 전멸",
        2,
        1,
        ("0x1806B0", "0x1806D4", "0x1806F8", "0x18071C"),
    ),
    ProtectionTarget(
        6,
        "주민 전멸",
        3,
        1,
        ("0x180A0C", "0x180A30", "0x180A54"),
    ),
    ProtectionTarget(
        7,
        "주민 전멸",
        3,
        1,
        ("0x180BF6", "0x180C1A", "0x180C3E"),
    ),
    ProtectionTarget(
        9,
        "NPC 지휘관 전멸",
        3,
        1,
        ("0x180FB2", "0x180FD6", "0x180FFA"),
    ),
    ProtectionTarget(11, "제시카 사망", 5, 2, ("0x1813C8",)),
    ProtectionTarget(
        18,
        "주민 전멸",
        8,
        4,
        ("0x1820B6", "0x1820DA"),
    ),
)

EXPECTED_OFFSETS = tuple(
    offset for target in TARGETS for offset in target.offsets
)
EXPECTED_RECORD_COUNT = 19


def protection_records(
    section: dict[str, Any],
) -> Iterator[tuple[int, dict[str, Any]]]:
    for scenario in section["scenarios"]:
        number = int(scenario["number"])
        for record in scenario["records"]:
            yield number, record


def _mercenary_ids(record: dict[str, Any]) -> list[int]:
    return [
        0xFF if row is None else int(row["class_id"], 16)
        for row in record["mercenaries"]
    ]


def build_section(
    baseline: dict[str, Any],
    steps: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Build the independently authorized NPC bug-fix ledger."""
    baseline_scenarios = {
        int(scenario["number"]): scenario
        for scenario in baseline["scenarios"]
    }
    scenarios = []
    for target in TARGETS:
        step = steps[target.scenario]
        if int(step["commander_at_delta"]) != target.commander_df_delta:
            raise ValueError(
                f"Scenario {target.scenario} enemy commander AT step changed"
            )
        if (
            int(step["soldier_at_correction_delta"])
            != target.soldier_df_delta
        ):
            raise ValueError(
                f"Scenario {target.scenario} enemy soldier A+ step changed"
            )
        source = baseline_scenarios[target.scenario]
        by_offset = {
            str(record["offset"]): record for record in source["records"]
        }
        records = []
        for expected_offset in target.offsets:
            record = by_offset.get(expected_offset)
            if record is None:
                raise ValueError(
                    f"Scenario {target.scenario} NPC record disappeared: "
                    f"{expected_offset}"
                )
            if str(record["side_id"]) != "03":
                raise ValueError(
                    f"Scenario {target.scenario} protection target is not "
                    f"side 03: {expected_offset}"
                )
            original_df = int(record["commander_df_modifier"])
            original_soldier_df = int(record["soldier_df_correction"])
            records.append({
                "index": int(record["index"]),
                "offset": expected_offset,
                "side_id": "03",
                "name_id": str(record["name_id"]),
                "name_korean": str(record["name_korean"]),
                "class_id": str(record["class_id"]),
                "class_korean": str(record["class_korean"]),
                "level": int(record["level"]),
                "x": int(record["x"]),
                "y": int(record["y"]),
                "commander_at": int(record["commander_at_modifier"]),
                "commander_df": {
                    "original": original_df,
                    "planned": original_df + target.commander_df_delta,
                },
                "soldier_correction": {
                    "at": int(record["soldier_at_correction"]),
                    "df": {
                        "original": original_soldier_df,
                        "planned": (
                            original_soldier_df + target.soldier_df_delta
                        ),
                    },
                },
                "mercenaries": _mercenary_ids(record),
            })
        scenarios.append({
            "number": target.scenario,
            "loss_condition": target.loss_condition,
            "enemy_attack_offset": {
                "commander_at_delta": target.commander_df_delta,
                "soldier_at_correction_delta": target.soldier_df_delta,
            },
            "record_count": len(records),
            "records": records,
        })

    section = {
        "schema_version": 1,
        "status": "authorized_hard_only_balance_bugfix",
        "source_report": {
            "url": REPORT_URL,
            "summary": (
                "하드판의 강화된 적 CPU 공격 때문에 공성전·마을의 "
                "NPC가 쉽게 전멸하여 일부 장의 진행 난도가 과도해짐"
            ),
        },
        "scope": (
            "패배 조건에 사망 또는 전멸이 직접 연결된 고정 side-03 NPC"
        ),
        "profile_impact": {
            "original": "byte_identical",
            "normal": "byte_identical",
            "hard": "defense_compensation_only",
        },
        "policy": {
            "commander_df": (
                "원본 DF + 같은 장의 하드 적 지휘관 AT 강화분"
            ),
            "soldier_df_correction": (
                "원본 D+ + 같은 장의 하드 적 병사 A+ 강화분"
            ),
            "unchanged": [
                "commander_at",
                "soldier_at_correction",
                "name",
                "class",
                "level",
                "ai",
                "placement",
                "mercenaries",
            ],
        },
        "scenario_count": len(scenarios),
        "record_count": sum(row["record_count"] for row in scenarios),
        "scenarios": scenarios,
    }
    validate_section(section)
    return section


def validate_section(section: dict[str, Any]) -> None:
    """Fail closed if the protection expands beyond its exact safe scope."""
    if section.get("schema_version") != 1:
        raise ValueError("unsupported NPC survival protection schema")
    if section.get("status") != "authorized_hard_only_balance_bugfix":
        raise ValueError("NPC survival protection is not authorized")
    if section.get("source_report", {}).get("url") != REPORT_URL:
        raise ValueError("NPC survival protection source report differs")
    impact = section.get("profile_impact", {})
    if (
        impact.get("original") != "byte_identical"
        or impact.get("normal") != "byte_identical"
        or impact.get("hard") != "defense_compensation_only"
    ):
        raise ValueError("NPC survival profile scope differs")

    scenarios = section.get("scenarios", [])
    if [int(row["number"]) for row in scenarios] != [
        target.scenario for target in TARGETS
    ]:
        raise ValueError("NPC survival scenario scope differs")
    if int(section.get("scenario_count", -1)) != len(TARGETS):
        raise ValueError("NPC survival scenario count differs")

    actual_offsets: list[str] = []
    for scenario, target in zip(scenarios, TARGETS):
        if scenario.get("loss_condition") != target.loss_condition:
            raise ValueError(
                f"Scenario {target.scenario} NPC loss condition differs"
            )
        offset_formula = scenario.get("enemy_attack_offset", {})
        if (
            int(offset_formula.get("commander_at_delta", -1))
            != target.commander_df_delta
            or int(
                offset_formula.get("soldier_at_correction_delta", -1)
            )
            != target.soldier_df_delta
        ):
            raise ValueError(
                f"Scenario {target.scenario} NPC compensation differs"
            )
        records = scenario.get("records", [])
        if int(scenario.get("record_count", -1)) != len(target.offsets):
            raise ValueError(
                f"Scenario {target.scenario} NPC record count differs"
            )
        if [str(row["offset"]) for row in records] != list(target.offsets):
            raise ValueError(
                f"Scenario {target.scenario} NPC offsets differ"
            )
        for record in records:
            actual_offsets.append(str(record["offset"]))
            if str(record.get("side_id")) != "03":
                raise ValueError("NPC survival target must remain side 03")
            commander_df = record["commander_df"]
            if (
                int(commander_df["planned"])
                - int(commander_df["original"])
                != target.commander_df_delta
            ):
                raise ValueError("NPC commander DF compensation differs")
            soldier_df = record["soldier_correction"]["df"]
            if (
                int(soldier_df["planned"])
                - int(soldier_df["original"])
                != target.soldier_df_delta
            ):
                raise ValueError("NPC soldier D+ compensation differs")
            mercenaries = record.get("mercenaries", [])
            if len(mercenaries) != 6:
                raise ValueError("NPC protection record needs six slots")

    if tuple(actual_offsets) != EXPECTED_OFFSETS:
        raise ValueError("NPC survival fixed-record scope differs")
    if int(section.get("record_count", -1)) != EXPECTED_RECORD_COUNT:
        raise ValueError("NPC survival record count must be exactly 18")
    if len(set(actual_offsets)) != EXPECTED_RECORD_COUNT:
        raise ValueError("NPC survival records must be unique")
