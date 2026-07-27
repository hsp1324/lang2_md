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
CLASS_SOLDIER_AT_CORRECTION_OFFSET = 0x0F
CLASS_SOLDIER_DF_CORRECTION_OFFSET = 0x10
FIXED_COMMANDER_AT_MODIFIER_OFFSET = 0x12
FIXED_COMMANDER_DF_MODIFIER_OFFSET = 0x13
FIXED_RECORD_LOADER = 0x010E46
FIXED_RECORD_LOADER_END = 0x010ED8


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
            "records": [record_row(row, classes, source) for row in records],
        })

    return {
        "schema_version": 2,
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
                "soldier_at_correction_offset": (
                    f"0x{CLASS_SOLDIER_AT_CORRECTION_OFFSET:02X}"
                ),
                "soldier_df_correction_offset": (
                    f"0x{CLASS_SOLDIER_DF_CORRECTION_OFFSET:02X}"
                ),
                "scope": "global_per_class",
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
                    "not represented by the 340 fixed records and must be "
                    "inventoried separately before scenario approval"
                ),
            },
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
        "## 기술적으로 확정된 능력치 구조",
        "",
        "- 36바이트 고정 배치 레코드의 `+0x12/+0x13`은 지휘관",
        "  `AT/DF` 부호 있는 보정값이다. 원본 로더 `0x010E46..0x010ED6`가",
        "  이를 런타임 레코드 `+0x3A/+0x3B`로 복사한다.",
        "- 병사 상태창의 `A+/D+`는 고정 배치 레코드가 아니라 28바이트",
        "  클래스 레코드 `0x05EDDC + class_id * 0x1C`의",
        "  `+0x0F/+0x10`에서 온다.",
        "- 클래스 레코드는 아군·적군·NPC가 공유할 수 있다. 따라서 이 두",
        "  바이트를 전역으로 올리면 같은 클래스를 쓰는 일반판 아군까지",
        "  강해질 수 있으므로 하드 모드 구현에는 사용하지 않는다.",
        "- 승인 후에는 확장 ROM에 시나리오·배치별 적 전용 병사 보정표를",
        "  두고 고정 배치 로더 직후에만 적용한다. 일반 한국어판과 원본",
        "  클래스 표는 그대로 보존한다.",
        "- 아래 340개는 고정 배치만 포함한다. 턴 이벤트로 생성되는 지원군과",
        "  증원은 별도 소유권 조사 후 같은 승인표에 추가해야 한다.",
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
