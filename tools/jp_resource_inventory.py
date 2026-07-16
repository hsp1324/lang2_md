#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.build_korean_jp_probe import (
    CONDITION_SCREENS,
    DIRECT_STRING_PATCHES,
    ITEM_DESCRIPTION_PATCHES,
    ITEM_NAME_PATCHES,
    SYSTEM_MESSAGE_EXPECTED_WORDS,
    WORD_ITEM_NAME_POINTERS,
    load_scenario_texts,
)
from tools.jp_text_font_analyzer import be16, be32


POINTER_GROUPS = {
    "conditions": (0x098D7A, 32),
    "scenario_descriptions": (0x09CF7C, 31),
    "item_names": (0x0A1902, 38),
    "item_descriptions": (0x0A1D7C, 37),
}

GLYPH_POINTER_GROUPS = {
    "conditions": 0x0986C6,
    "scenario_descriptions": 0x09B2FC,
}

DIRECT_GROUPS = {
    "item_word_names": WORD_ITEM_NAME_POINTERS,
    "level_item_system_messages": tuple(SYSTEM_MESSAGE_EXPECTED_WORDS),
    "magic_names": (
        0x082BFE, 0x082C0E, 0x082C18, 0x082C22, 0x082C34, 0x082C3C,
        0x082C48, 0x082C54, 0x082C66, 0x082C76, 0x082C80, 0x082C8A,
        0x082C9C, 0x082CAE, 0x082CB8, 0x082CC2, 0x082CD2, 0x082CDC,
        0x082CE4, 0x082CF0, 0x082D00, 0x082D0A, 0x082D14,
    ),
    "mercenary_battle_names": (
        0x082D5A, 0x082D62, 0x082D70, 0x082D7C, 0x082D8E, 0x082DA0,
        0x082DAC, 0x082DBE, 0x082DCA, 0x082DD2, 0x082DDC, 0x082DE4,
        0x082DF0, 0x082DFA, 0x082E06,
    ),
    "battle_status_messages": (0x0971F4, 0x097202, 0x097214),
}

# Scenario 2-10 and 23-31 descriptions were transcribed against the rendered
# Japanese records and reviewed statically. They still require live playback.
STATIC_REVIEWED_POINTER_IDS = {
    "scenario_descriptions": frozenset(range(1, 10)) | frozenset(range(22, 31)),
}


def read_word_stream(data: bytes, offset: int, limit: int = 4096) -> list[int]:
    values = []
    for _ in range(limit):
        value = be16(data, offset)
        values.append(value)
        offset += 2
        if value == 0xFFFF:
            return values
    raise ValueError("word stream has no FFFF terminator")


def stream_hex(values: list[int]) -> str:
    return " ".join(f"{value:04X}" for value in values)


def pointer_targets() -> dict[str, list[object]]:
    return {
        # The pointer table has one final preparation-UI record after the 31
        # scenario condition records. Keep it visible in inventory without
        # assigning a translation target.
        "conditions": [*CONDITION_SCREENS, None],
        "scenario_descriptions": load_scenario_texts(),
        "item_names": ITEM_NAME_PATCHES,
        "item_descriptions": ITEM_DESCRIPTION_PATCHES,
    }


def inventory_pointer_group(
    japanese: bytes,
    korean: bytes,
    name: str,
    pointer_table: int,
    count: int,
    targets: list[object],
) -> dict[str, object]:
    if len(targets) != count:
        raise ValueError(f"{name} has {len(targets)} targets, expected {count}")
    glyph_table = GLYPH_POINTER_GROUPS.get(name)
    rows = []
    reviewed_ids = STATIC_REVIEWED_POINTER_IDS.get(name, frozenset())
    for index in range(count):
        original_pointer = be32(japanese, pointer_table + index * 4)
        current_pointer = be32(korean, pointer_table + index * 4)
        original_tokens = read_word_stream(japanese, original_pointer)
        current_tokens = read_word_stream(korean, current_pointer)
        glyph_pointer_modified = False
        original_glyph_pointer = None
        current_glyph_pointer = None
        if glyph_table is not None:
            original_glyph_pointer = be32(japanese, glyph_table + index * 4)
            current_glyph_pointer = be32(korean, glyph_table + index * 4)
            glyph_pointer_modified = original_glyph_pointer != current_glyph_pointer
        modified = (
            original_pointer != current_pointer
            or original_tokens != current_tokens
            or glyph_pointer_modified
        )
        reviewed = index in reviewed_ids
        rows.append(
            {
                "id": index,
                "pointer": f"0x{original_pointer:06X}",
                "current_pointer": f"0x{current_pointer:06X}",
                "glyph_pointer": None if original_glyph_pointer is None else f"0x{original_glyph_pointer:06X}",
                "current_glyph_pointer": None if current_glyph_pointer is None else f"0x{current_glyph_pointer:06X}",
                "original_word_count": len(original_tokens),
                "current_word_count": len(current_tokens),
                "original_tokens": stream_hex(original_tokens),
                "target_korean": targets[index],
                "modified": modified,
                "reviewed": reviewed,
                "live_verified": False,
            }
        )
    return {
        "pointer_table": f"0x{pointer_table:06X}",
        "glyph_pointer_table": None if glyph_table is None else f"0x{glyph_table:06X}",
        "entry_count": count,
        "modified_count": sum(bool(row["modified"]) for row in rows),
        "reviewed_count": sum(bool(row["reviewed"]) for row in rows),
        "live_verified_count": 0,
        "entries": rows,
    }


def inventory_direct_group(
    japanese: bytes,
    korean: bytes,
    name: str,
    offsets: tuple[int, ...],
) -> dict[str, object]:
    rows = []
    for index, offset in enumerate(offsets):
        original = read_word_stream(japanese, offset)
        current = read_word_stream(korean, offset)
        rows.append(
            {
                "id": index,
                "pointer": f"0x{offset:06X}",
                "original_word_count": len(original),
                "current_word_count": len(current),
                "original_tokens": stream_hex(original),
                "target_korean": DIRECT_STRING_PATCHES.get(offset),
                "modified": original != current,
                "reviewed": False,
                "live_verified": False,
            }
        )
    return {
        "entry_count": len(rows),
        "modified_count": sum(bool(row["modified"]) for row in rows),
        "reviewed_count": 0,
        "live_verified_count": 0,
        "entries": rows,
    }


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    targets = pointer_targets()
    groups = {
        name: inventory_pointer_group(japanese, korean, name, table, count, targets[name])
        for name, (table, count) in POINTER_GROUPS.items()
    }
    groups.update(
        {
            name: inventory_direct_group(japanese, korean, name, offsets)
            for name, offsets in DIRECT_GROUPS.items()
        }
    )
    return {
        "warning": (
            "modified only means the current ROM differs from the Japanese ROM. "
            "reviewed and live_verified remain false until explicit checks are recorded."
        ),
        "groups": groups,
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Shared Word-Resource Inventory",
        "",
        "Generated by `python3 tools/jp_resource_inventory.py`.",
        "",
        "A modified entry is not automatically a correct translation. Scenario 2-10 and 23-31",
        "descriptions are statically reviewed against the rendered Japanese records;",
        "the remaining unreviewed entries and all live playback checks stay separate.",
        "",
        "| Resource | Entries | Modified | Reviewed | Live verified |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, group in result["groups"].items():
        lines.append(
            f"| {name} | {group['entry_count']} | {group['modified_count']} | "
            f"{group['reviewed_count']} | {group['live_verified_count']} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Conditions use 32 records: the builder patches Scenario 1-31 and preserves the final preparation-UI record.",
            "- Summoned creatures are class-table IDs and are tracked in `localization/global_strings.json`.",
            "- `mercenary_battle_names` is a separate direct-word path from the shared byte class table.",
            "- Detailed pointers, original tokens, targets, and explicit review flags are in",
            "  `localization/shared_word_resources.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory shared 16-bit word resources")
    parser.add_argument("--jp-rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean JP Probe).md"),
    )
    parser.add_argument(
        "--json", type=Path, default=Path("localization/shared_word_resources.json")
    )
    parser.add_argument(
        "--markdown", type=Path, default=Path("docs/shared_word_resource_inventory.md")
    )
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        ", ".join(
            f"{name} {group['modified_count']}/{group['entry_count']} modified"
            for name, group in result["groups"].items()
        )
    )


if __name__ == "__main__":
    main()
