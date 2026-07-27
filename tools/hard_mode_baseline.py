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


def rom_identity(data: bytes) -> dict[str, object]:
    return {
        "size": len(data),
        "header_checksum": data[0x18E:0x190].hex().upper(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def stat_summary(records: list[dict[str, object]], field: str) -> dict[str, object] | None:
    if not records:
        return None
    values = [int(row[field]) for row in records]
    return {
        "minimum": min(values),
        "maximum": max(values),
        "mean": round(statistics.mean(values), 1),
    }


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
) -> dict[str, object]:
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
        "class_id": f"{int(row['class_id']):02X}",
        "class_japanese": row["class"]["jp"],
        "class_korean": row["class"]["ko"],
        "level": row["level"],
        "at": row["at"],
        "df": row["df"],
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
    for number in range(1, SCENARIO_COUNT + 1):
        model = read_scenario(source, source, number)
        records = list(model["records"])
        enemies = [row for row in records if int(row["side_id"]) == 0x04]
        side_counts = Counter(int(row["side_id"]) for row in records)
        mercenary_counts: Counter[int] = Counter()
        for row in records:
            all_sides[int(row["side_id"])] += 1
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
            "records": [record_row(row, classes) for row in records],
        })

    return {
        "schema_version": 1,
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
        "normal_release": {
            **normal_identity,
            "immutable": True,
        },
        "source_rom": rom_identity(source),
        "source_model": {
            "scenario_count": SCENARIO_COUNT,
            "record_size": 0x24,
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
        "## 일본 원판 시나리오 분포",
        "",
        "| 장 | 전체 | 적군(04) | 기타 진영 | 숨김 | 적 LV | 적 AT | 적 DF | 적 용병 칸 |",
        "|---:|---:|---:|:---|---:|:---|:---|:---|---:|",
    ]
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
        "`08`이 10개다. 따라서 단순히 `04`에만 일괄 공식을 적용하면 주요",
        "배치를 놓칠 수 있으며, 시나리오별 예외 검토가 필요하다.",
        "",
        "## 원판 용병 슬롯 사용량",
        "",
        "| 클래스 ID | 일본어 | 한국어 | 사용 칸 |",
        "|:---:|:---|:---|---:|",
    ])
    for row in inventory["source_model"]["mercenary_distribution"]:
        lines.append(
            f"| `{row['class_id']}` | {row['japanese']} | "
            f"{row['korean']} | {row['slot_count']} |"
        )
    lines.extend([
        "",
        "각 레코드의 정확한 원본 주소와 6개 용병 칸은",
        "`localization/hard_mode_baseline.json`에 기록한다. 이 기준표에는",
        "제안 수치나 승인되지 않은 교체 병종을 넣지 않는다.",
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
