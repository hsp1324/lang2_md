#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.class_ability_data import (
    ABILITY_MASK_TABLE,
    ABILITY_REQUIREMENT_TABLE,
    CLASS_ABILITY_OFFSETS,
    MAGIC_COMMAND_MASK,
    SUMMON_ABILITY_ID,
    SUMMON_COMMAND_MASK,
    ability_ids_for_classes,
    all_class_ability_unlocks,
    natural_class_paths,
    read_ability_definitions,
)
from tools.class_change_data import COMMANDER_COUNT
from tools.scenario_data import (
    KOREAN_NAME_BY_ID,
    SCENARIO_COUNT,
    class_names,
    read_scenario,
)


DEFAULT_SOURCE_ROM = Path("roms/original/Langrisser II (Japan).md")
DEFAULT_JSON = Path("localization/class_abilities.json")
DEFAULT_MARKDOWN = Path("docs/class_ability_inventory.md")


def _ability_summary(
    ability_ids: tuple[int, ...],
    abilities: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "id": ability_id,
            "name": abilities[ability_id]["name"],
            "required_level": abilities[ability_id]["required_level"],
            "runtime_mask": abilities[ability_id]["runtime_mask"],
        }
        for ability_id in ability_ids
    ]


def inventory(source: bytes) -> dict[str, object]:
    definitions = read_ability_definitions(source)
    names = builder.MAGIC_LIST_NAMES[: SUMMON_ABILITY_ID + 1]
    if len(names) != len(definitions):
        raise ValueError("localized magic/summon name count changed")
    abilities = [
        {
            "id": definition.ability_id,
            "name": names[definition.ability_id],
            "kind": definition.kind,
            "required_level": definition.required_level,
            "runtime_bit": definition.ability_id + 1,
            "runtime_mask": f"0x{definition.runtime_mask:08X}",
        }
        for definition in definitions
    ]

    classes = class_names(source)
    fixed_usage = Counter()
    for scenario_number in range(1, SCENARIO_COUNT + 1):
        for record in read_scenario(
            source,
            source,
            scenario_number,
        )["records"]:
            fixed_usage[record["class_id"]] += 1

    commander_rows = []
    all_natural_classes: set[int] = set()
    all_natural_abilities: set[int] = set()
    for commander_id in range(1, COMMANDER_COUNT + 1):
        paths = natural_class_paths(source, commander_id)
        reachable_classes = tuple(sorted({value for path in paths for value in path}))
        reachable_abilities = ability_ids_for_classes(source, reachable_classes)
        all_natural_classes.update(reachable_classes)
        all_natural_abilities.update(reachable_abilities)

        path_rows = []
        max_ability_count = 0
        for path in paths:
            path_ability_ids = ability_ids_for_classes(source, path)
            max_ability_count = max(max_ability_count, len(path_ability_ids))
            path_rows.append((path, path_ability_ids))
        max_paths = [
            {
                "class_ids": list(path),
                "classes": [classes[class_id]["ko"] for class_id in path],
                "ability_ids": list(ability_ids),
                "abilities": [
                    names[ability_id]
                    for ability_id in ability_ids
                ],
            }
            for path, ability_ids in path_rows
            if len(ability_ids) == max_ability_count
        ]
        commander_rows.append(
            {
                "commander_id": commander_id,
                "name": KOREAN_NAME_BY_ID[commander_id],
                "path_count": len(paths),
                "reachable_class_ids": list(reachable_classes),
                "ability_ids": list(reachable_abilities),
                "abilities": [
                    names[ability_id]
                    for ability_id in reachable_abilities
                ],
                "max_path_ability_count": max_ability_count,
                "max_paths": max_paths,
            }
        )

    class_rows = []
    for unlocks in all_class_ability_unlocks(source):
        class_info = classes[unlocks.class_id]
        class_rows.append(
            {
                "class_id": unlocks.class_id,
                "class": class_info,
                "record_offset": f"0x{unlocks.offset - CLASS_ABILITY_OFFSETS[0]:06X}",
                "ability_offset": f"0x{unlocks.offset:06X}",
                "ability_ids": list(unlocks.ability_ids),
                "abilities": _ability_summary(unlocks.ability_ids, abilities),
                "natural_chain_reachable": unlocks.class_id in all_natural_classes,
                "fixed_scenario_record_count": fixed_usage[unlocks.class_id],
            }
        )

    missing_natural = tuple(
        definition.ability_id
        for definition in definitions
        if definition.ability_id not in all_natural_abilities
    )
    return {
        "source_tables": {
            "class_records": "0x05EDDC",
            "class_record_size": "0x1C",
            "class_ability_offsets": [
                f"0x{offset:02X}" for offset in CLASS_ABILITY_OFFSETS
            ],
            "ability_requirements": f"0x{ABILITY_REQUIREMENT_TABLE:06X}",
            "ability_masks": f"0x{ABILITY_MASK_TABLE:06X}",
        },
        "runtime_contract": {
            "magic_command_mask": f"0x{MAGIC_COMMAND_MASK:08X}",
            "summon_command_mask": f"0x{SUMMON_COMMAND_MASK:08X}",
            "ability_scan": "0x014946..0x01498A",
            "magic_command_gate": "0x020DAE",
            "summon_command_gate": "0x020DFA",
            "magic_list_builder": "0x0211A2..0x02125A",
            "semantics": (
                "A stock level-up learns each current-class ability whose "
                "required level is not greater than the new level. Class "
                "change alone does not scan the new class."
            ),
        },
        "ability_count": len(abilities),
        "abilities": abilities,
        "class_count": len(class_rows),
        "classes": class_rows,
        "commander_count": len(commander_rows),
        "commanders": commander_rows,
        "natural_chain_ability_ids": sorted(all_natural_abilities),
        "natural_chain_missing_ability_ids": list(missing_natural),
        "natural_chain_missing_abilities": [
            names[ability_id] for ability_id in missing_natural
        ],
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Class Ability Inventory",
        "",
        "Generated from the Japanese REV00 ROM by "
        "`python3 tools/class_ability_inventory.py`.",
        "Class IDs, ability IDs, requirements, masks, and paths are source data; "
        "Korean names are localization targets.",
        "",
        "## Runtime Contract",
        "",
        f"- Class records: `{result['source_tables']['class_records']}`, "
        f"stride `{result['source_tables']['class_record_size']}`, ability bytes "
        f"{', '.join(f'`{value}`' for value in result['source_tables']['class_ability_offsets'])}",
        f"- Ability requirements: `{result['source_tables']['ability_requirements']}`",
        f"- Ability masks: `{result['source_tables']['ability_masks']}`",
        f"- Magic command mask: `{result['runtime_contract']['magic_command_mask']}`",
        f"- Summon command mask: `{result['runtime_contract']['summon_command_mask']}`",
        f"- Level-up scan: `{result['runtime_contract']['ability_scan']}`",
        f"- Magic list builder: `{result['runtime_contract']['magic_list_builder']}`",
        f"- Semantics: {result['runtime_contract']['semantics']}",
        "",
        "## Abilities",
        "",
        "| ID | Name | Kind | Required LV | Runtime bit | Mask |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for ability in result["abilities"]:
        lines.append(
            f"| `{ability['id']:02X}` | {ability['name']} | "
            f"{ability['kind']} | {ability['required_level']} | "
            f"{ability['runtime_bit']} | `{ability['runtime_mask']}` |"
        )
    lines.extend(
        [
            "",
            "Across all ten source class-change trees, the only absent ability is "
            + ", ".join(
                f"`{ability_id:02X}` {name}"
                for ability_id, name in zip(
                    result["natural_chain_missing_ability_ids"],
                    result["natural_chain_missing_abilities"],
                )
            )
            + ". This is a source reachability statement, not a claim that the "
            "ability is unused by every debug or secret mechanism.",
            "",
            "## Commander Coverage",
            "",
            "| ID | Commander | Paths | Reachable abilities | Largest path |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for commander in result["commanders"]:
        lines.append(
            f"| {commander['commander_id']} | {commander['name']} | "
            f"{commander['path_count']} | {len(commander['ability_ids'])} | "
            f"{commander['max_path_ability_count']} |"
        )
    lines.extend(
        [
            "",
            "## Classes With Abilities",
            "",
            "| ID | Class | JP | Ability slots | Natural chain | Scenario records |",
            "| --- | --- | --- | --- | --- | ---: |",
        ]
    )
    for class_row in result["classes"]:
        if not class_row["ability_ids"]:
            continue
        slots = " / ".join(
            f"`{ability['id']:02X}` {ability['name']}@LV{ability['required_level']}"
            for ability in class_row["abilities"]
        )
        lines.append(
            f"| `{class_row['class_id']:02X}` | {class_row['class']['ko']} | "
            f"{class_row['class']['jp']} | {slots} | "
            f"{'yes' if class_row['natural_chain_reachable'] else 'no'} | "
            f"{class_row['fixed_scenario_record_count']} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Japanese-ROM class ability inventory"
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = inventory(args.source_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['ability_count']} abilities, "
        f"{result['class_count']} classes, "
        f"{result['commander_count']} commander trees"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
