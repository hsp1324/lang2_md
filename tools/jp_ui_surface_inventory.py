#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import build_korean_jp_probe as builder
from tools import class_change_inventory as class_change_report


def changed(japanese: bytes, korean: bytes, offset: int, size: int) -> bool:
    return japanese[offset : offset + size] != korean[offset : offset + size]


def byte_string_size(data: bytes, offset: int, limit: int = 64) -> int:
    end = data.find(b"\xff", offset, offset + limit)
    if end < 0:
        raise ValueError(f"missing FF terminator at 0x{offset:06X}")
    return end - offset + 1


def add_rows(
    rows: list[dict[str, object]],
    japanese: bytes,
    korean: bytes,
    group: str,
    patches: dict[int, object],
    unit: int,
    fixed_width: bool,
) -> None:
    for offset, spec in patches.items():
        if fixed_width:
            width, target = spec
            size = int(width) * unit
        else:
            target = spec
            size = byte_string_size(japanese, offset)
        rows.append(
            {
                "group": group,
                "address": f"0x{offset:06X}",
                "size_bytes": size,
                "target_korean": target,
                "modified": changed(japanese, korean, offset, size),
                "reviewed": False,
                "live_verified": False,
            }
        )


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    class_change = class_change_report.inventory(japanese)
    remaining_class_change = (
        class_change["unique_transition_count"]
        - class_change["live_verified_unique_transition_count"]
    )
    if remaining_class_change:
        class_change_gap = (
            "runtime verification of the remaining "
            f"{remaining_class_change} unique class-change candidate "
            "combinations and non-Elwin application paths"
        )
    else:
        class_change_gap = (
            "natural active-commander and save-persistence verification for "
            "class-change paths beyond the two natural Elwin and Hein proofs"
        )
    rows: list[dict[str, object]] = []
    add_rows(rows, japanese, korean, "byte_ff_strings", builder.BYTE_UI_STRING_PATCHES, 1, False)
    add_rows(rows, japanese, korean, "fixed_byte_strings", builder.BYTE_UI_FIXED_STRING_PATCHES, 1, True)
    add_rows(rows, japanese, korean, "fixed_word_strings", builder.BYTE_UI_WORD_STRING_PATCHES, 2, True)
    add_rows(rows, japanese, korean, "direct_word_sequences", builder.DIRECT_WORD_SEQUENCE_PATCHES, 2, True)
    for row in rows:
        if row["address"] == f"0x{builder.ENDING_STATUS_GLYPH_LIST:06X}":
            row["reviewed"] = True
            row["live_verified"] = True
        elif row["address"] == f"0x{builder.BATTLE_RESULT_HEADER_GLYPH_LIST:06X}":
            row["reviewed"] = True
            row["live_verified"] = True
    add_rows(rows, japanese, korean, "fixed_direct_strings", builder.DIRECT_FIXED_STRING_PATCHES, 2, True)
    add_rows(rows, japanese, korean, "route_titles", builder.DIRECT_FIXED_ROUTE_TITLE_PATCHES, 2, True)
    add_rows(rows, japanese, korean, "scenario_headers", builder.DIRECT_FIXED_SCENARIO_HEADER_PATCHES, 2, True)
    for offset, text in builder.ARRANGE_MENU_GLYPH_LIST_PATCHES.items():
        rows.append(
            {
                "group": "arrange_glyph_lists",
                "address": f"0x{offset:06X}",
                "size_bytes": len(text) * 2,
                "target_korean": text,
                "modified": changed(japanese, korean, offset, len(text) * 2),
                "reviewed": False,
                "live_verified": False,
            }
        )
    for offset, (capacity, text) in builder.OPENING_TEXT_LIST_PATCHES.items():
        reviewed = offset in builder.OPENING_TEXT_LIST_REVIEWED_ADDRESSES
        rows.append(
            {
                "group": "opening_text_lists",
                "address": f"0x{offset:06X}",
                "size_bytes": capacity * 2,
                "target_korean": text,
                "modified": changed(japanese, korean, offset, capacity * 2),
                "reviewed": reviewed,
                "live_verified": False,
            }
        )
    for code, text in builder.WIDE_BYTE_GLYPH_PATCHES.items():
        offset = builder.JP_FONT_BASE + code * builder.GLYPH_BYTES
        rows.append(
            {
                "group": "global_wide_glyphs",
                "address": f"0x{offset:06X}",
                "size_bytes": builder.GLYPH_BYTES,
                "target_korean": text,
                "modified": changed(japanese, korean, offset, builder.GLYPH_BYTES),
                "reviewed": False,
                "live_verified": False,
            }
        )
    rows.append(
        {
            "group": "class_change_glyph_list",
            "address": f"0x{builder.CLASS_CHANGE_GLYPH_LIST:06X}",
            "size_bytes": len(builder.CLASS_CHANGE_EXPECTED_GLYPHS) * 2,
            "target_korean": builder.CLASS_CHANGE_GLYPH_TEXT,
            "modified": changed(
                japanese,
                korean,
                builder.CLASS_CHANGE_GLYPH_LIST,
                len(builder.CLASS_CHANGE_EXPECTED_GLYPHS) * 2,
            ),
            "reviewed": False,
            "live_verified": False,
        }
    )
    for group, offset, size, target in (
        (
            "name_entry_default_buffer",
            builder.NAME_ENTRY_DEFAULT_WORD_OFFSET,
            builder.NAME_ENTRY_DEFAULT_COPY_WORDS * 2,
            "엘윈 + blank cells",
        ),
        (
            "name_entry_glyph_list",
            builder.NAME_ENTRY_GLYPH_LIST,
            builder.NAME_ENTRY_GLYPH_COUNT * 2,
            f"{len(builder.NAME_ENTRY_GRID_CHARS)} selectable Korean syllables",
        ),
        (
            "name_entry_layout",
            builder.NAME_ENTRY_LAYOUT,
            builder.NAME_ENTRY_LAYOUT_END - builder.NAME_ENTRY_LAYOUT,
            "Korean grid and navigation labels",
        ),
        (
            "name_entry_byte_values",
            builder.NAME_ENTRY_BYTE_VALUE_TABLE,
            builder.NAME_ENTRY_GLYPH_COUNT,
            "selection index to Korean byte-font code",
        ),
        (
            "name_entry_confirm_hook",
            builder.NAME_ENTRY_CONFIRM_COPY_HOOK,
            len(builder.NAME_ENTRY_CONFIRM_COPY_ORIGINAL),
            "selection index to dialogue glyph lookup call",
        ),
        (
            "name_entry_confirm_routine",
            builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE,
            len(builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE_BYTES),
            "relocated index-to-glyph conversion routine",
        ),
    ):
        rows.append(
            {
                "group": group,
                "address": f"0x{offset:06X}",
                "size_bytes": size,
                "target_korean": target,
                "modified": changed(japanese, korean, offset, size),
                "reviewed": True,
                "live_verified": True,
            }
        )

    for group, offset, size, target in (
        (
            "inline_discard_prompt_hook",
            builder.INLINE_DISCARD_PROMPT_RENDER_HOOK,
            len(builder.INLINE_DISCARD_PROMPT_RENDER_HOOK_ORIGINAL),
            "redirect fixed item-discard prompt to localized renderer",
        ),
        (
            "inline_discard_prompt_routine",
            builder.INLINE_DISCARD_PROMPT_RENDER_ROUTINE,
            len(builder._build_inline_discard_prompt_renderer()),
            "render 13 full localized tile IDs without consuming base byte-font slots",
        ),
        (
            "inline_discard_prompt_record",
            builder.INLINE_DISCARD_PROMPT_RECORD,
            builder.INLINE_DISCARD_PROMPT_WIDTH,
            builder.INLINE_DISCARD_PROMPT_TEXT,
        ),
    ):
        rows.append(
            {
                "group": group,
                "address": f"0x{offset:06X}",
                "size_bytes": size,
                "target_korean": target,
                "modified": changed(japanese, korean, offset, size),
                "reviewed": True,
                "live_verified": False,
            }
        )

    rows.append(
        {
            "group": "title_load_glyph_list",
            "address": f"0x{builder.TITLE_LOAD_GLYPH_LIST:06X}",
            "size_bytes": builder.TITLE_LOAD_GLYPH_COUNT * 2,
            "target_korean": "title LOAD cursor/digits and Korean local glyph bank",
            "modified": changed(
                japanese,
                korean,
                builder.TITLE_LOAD_GLYPH_LIST,
                builder.TITLE_LOAD_GLYPH_COUNT * 2,
            ),
            "reviewed": True,
            "live_verified": True,
        }
    )
    live_title_load_records = {
        0x0A30D6,  # 이어하기
        0x0A30E8,  # 시나리오
        0x0A30F2,  # 손상된 데이터
        0x0A3106,  # 데이터 없음
        0x0A311A,  # 다음 시나리오 (title SAVE renderer probe)
    }
    for offset, (capacity, target) in builder.TITLE_LOAD_RECORDS.items():
        rows.append(
            {
                "group": "title_load_slot_records",
                "address": f"0x{offset:06X}",
                "size_bytes": (capacity + 1) * 2,
                "target_korean": target,
                "modified": changed(japanese, korean, offset, capacity * 2),
                "reviewed": True,
                "live_verified": offset in live_title_load_records,
            }
        )
    for group, offset, size, target, live_verified in (
        (
            "title_save_header",
            builder.TITLE_SAVE_HEADER_RECORD,
            len(builder.TITLE_SAVE_HEADER_ORIGINAL) * 2,
            "저장",
            True,
        ),
        (
            "title_load_header_fallback",
            builder.TITLE_LOAD_HEADER_RECORD,
            len(builder.TITLE_LOAD_HEADER_ORIGINAL) * 2,
            "로드",
            False,
        ),
        (
            "title_load_header_hook",
            builder.TITLE_LOAD_HEADER_LEA,
            len(builder.TITLE_LOAD_HEADER_LEA_ORIGINAL),
            "relocated 불러오기 header pointer",
            True,
        ),
        (
            "title_load_header_relocation",
            builder.TITLE_LOAD_HEADER_RELOC,
            14,
            "불러오기",
            True,
        ),
    ):
        rows.append(
            {
                "group": group,
                "address": f"0x{offset:06X}",
                "size_bytes": size,
                "target_korean": target,
                "modified": changed(japanese, korean, offset, size),
                "reviewed": True,
                "live_verified": live_verified,
            }
        )

    for group, offset, size, target in (
        (
            "title_main_menu_record",
            builder.TITLE_MAIN_MENU_RECORD,
            len(builder.TITLE_MAIN_MENU_RECORD_ORIGINAL) * 2,
            "새 게임 / 불러오기",
        ),
        (
            "title_credit_font_load_hook",
            builder.TITLE_CREDIT_FONT_LOAD_HOOK,
            len(builder.TITLE_CREDIT_FONT_LOAD_HOOK_ORIGINAL),
            "title-only Korean/ID font resource loader",
        ),
        (
            "title_credit_render_hook",
            builder.TITLE_COPYRIGHT_RENDER_HOOK,
            len(builder.TITLE_COPYRIGHT_RENDER_HOOK_ORIGINAL),
            "copyright plus Korean localization credit renderer",
        ),
        (
            "title_credit_font_load_routine",
            builder.TITLE_CREDIT_FONT_LOAD_ROUTINE,
            len(builder._build_title_credit_font_loader()),
            "load title-only byte-font slice and restore source setup",
        ),
        (
            "title_credit_render_routine",
            builder.TITLE_CREDIT_RENDER_ROUTINE,
            len(builder._build_title_credit_renderer()),
            "render copyright and 한글화: hsp1324",
        ),
        (
            "title_credit_text_record",
            builder.TITLE_CREDIT_TEXT_RECORD,
            len(builder.TITLE_CREDIT_RECORD_BYTES),
            builder.TITLE_CREDIT_TEXT,
        ),
        (
            "title_credit_resource_pointer",
            builder.BYTE_UI_EXT_RESOURCE_TABLE
            + builder.TITLE_CREDIT_RESOURCE_INDEX * 4,
            4,
            f"compressed title byte-font resource {builder.TITLE_CREDIT_RESOURCE_INDEX}",
        ),
    ):
        rows.append(
            {
                "group": group,
                "address": f"0x{offset:06X}",
                "size_bytes": size,
                "target_korean": target,
                "modified": changed(japanese, korean, offset, size),
                "reviewed": True,
                "live_verified": True,
            }
        )

    resource_entry = builder.BYTE_UI_FONT_RESOURCE_TABLE + builder.BYTE_UI_FONT_RESOURCE_INDEX * 4
    original_resource = int.from_bytes(japanese[resource_entry : resource_entry + 4], "big")
    current_resource = int.from_bytes(korean[resource_entry : resource_entry + 4], "big")
    compressed = {
        "resource_table": f"0x{builder.BYTE_UI_FONT_RESOURCE_TABLE:06X}",
        "resource_index": builder.BYTE_UI_FONT_RESOURCE_INDEX,
        "table_entry": f"0x{resource_entry:06X}",
        "original_pointer": f"0x{original_resource:06X}",
        "current_pointer": f"0x{current_resource:06X}",
        "relocated": original_resource != current_resource,
        "reviewed": False,
        "live_verified": False,
    }

    group_summary = {}
    for row in rows:
        summary = group_summary.setdefault(row["group"], {"entry_count": 0, "modified_count": 0})
        summary["entry_count"] += 1
        summary["modified_count"] += bool(row["modified"])

    return {
        "declared_patch_count": len(rows),
        "modified_patch_count": sum(bool(row["modified"]) for row in rows),
        "groups": group_summary,
        "compressed_byte_ui_font": compressed,
        "declared_patches": rows,
        "remaining_inventory_gaps": [
            "arbitrary-Hangul composition beyond the 57 production-safe name-entry syllables",
            class_change_gap,
            "ending and credits UI variants outside the verified Scenario 27, "
            "all-epilogue, ending-visit, and final-credit paths",
            "magic/summon targeting and result paths beyond the production-faithful "
            "Magic Arrow and diagnostic Attack/Elemental probes",
            "ownership and purpose of 427 compressed resources beyond byte-font "
            "resource index 1 and item-icon resource index 391",
            "access-path, translation, and live verification of the hidden 77-row "
            "sound-test label table at 0x05E040",
            "non-pointer byte sequences outside the conservative maximal half-width/"
            "uppercase-ASCII inline scan and the classified direct-word/direct-byte inventories",
        ],
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Declared UI Patch Surface Inventory",
        "",
        "Generated by `python3 tools/jp_ui_surface_inventory.py`.",
        "",
        "This report inventories UI surfaces already declared by the builder. It is not a",
        "complete Japanese-residue scan. The explicit gap list prevents Stage 1 from being",
        "closed merely because every known patch declaration changed bytes.",
        "",
        f"- Declared patches: {result['declared_patch_count']}",
        f"- Byte-modified declarations: {result['modified_patch_count']}",
        "- The unchanged `NPC` declaration is an intentional retained abbreviation.",
        "",
        "| Group | Entries | Modified |",
        "| --- | ---: | ---: |",
    ]
    for name, group in result["groups"].items():
        lines.append(f"| {name} | {group['entry_count']} | {group['modified_count']} |")
    font = result["compressed_byte_ui_font"]
    lines.extend(
        [
            "",
            "## Compressed Byte UI Font",
            "",
            f"Resource table `{font['resource_table']}` index {font['resource_index']} uses entry",
            f"`{font['table_entry']}` and is relocated from `{font['original_pointer']}` to",
            f"`{font['current_pointer']}` in the current build.",
            "",
            "## Remaining Inventory Gaps",
            "",
        ]
    )
    lines.extend(f"- {gap}" for gap in result["remaining_inventory_gaps"])
    lines.extend(
        [
            "",
            "Detailed declarations are in `localization/ui_patch_surfaces.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory UI patches declared by the builder")
    parser.add_argument("--jp-rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean JP Probe).md"),
    )
    parser.add_argument("--json", type=Path, default=Path("localization/ui_patch_surfaces.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/ui_patch_surface_inventory.md"))
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['modified_patch_count']}/{result['declared_patch_count']} declared patches modified; "
        f"{len(result['remaining_inventory_gaps'])} explicit inventory gaps"
    )


if __name__ == "__main__":
    main()
