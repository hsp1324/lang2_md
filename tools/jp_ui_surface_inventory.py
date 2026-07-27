#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import build_korean_jp_probe as builder
from tools import class_change_flow_inventory as class_change_flow_report
from tools import jp_compressed_resource_inventory as compressed_resource_report
from tools import magic_flow_inventory as magic_flow_report
from tools import name_entry_flow_inventory as name_entry_flow_report


RUNTIME_EVIDENCE_BY_ADDRESS = {
    # Scenario 1 preparation, deployment, map status, and four-turn playback.
    **dict.fromkeys(
        (
            0x061AC5,
            0x061ACB,
            0x061AD8,
            0x061AFC,
            0x061B16,
            0x061B1C,
            0x061B54,
            0x061B5C,
            0x061B61,
            0x061B65,
            0x061B71,
            0x061B8D,
        ),
        "docs/runtime_verification_inventory.md#scenario-1",
    ),
    # The complete two-page playable roster was opened through equipment/status
    # panels, so this covers the byte-font names rather than dialogue aliases.
    **dict.fromkeys(
        (
            0x061AD3,
            0x061ADC,
            0x061AE1,
            0x061AE5,
            0x061AEA,
            0x061AEF,
        ),
        "docs/runtime_verification_inventory.md#scenario-25",
    ),
    0x061ACF: "docs/runtime_verification_inventory.md#scenario-26",
    0x061B00: "docs/runtime_verification_inventory.md#scenario-27",
    0x061B28: "docs/runtime_verification_inventory.md#scenario-26",
    **dict.fromkeys(
        (0x061B7E, 0x061B83, 0x061B88),
        "docs/runtime_verification_inventory.md#scenario-28",
    ),
    # Scenario 1 shop/equipment proof includes all three category labels.
    **dict.fromkeys(
        (0x0A18E0, 0x0A18EC, 0x0A18F8),
        "captures/run/212a_s01_equipment_current.png",
    ),
    # Conditions, unit notices, and the preparation/status panel.
    **dict.fromkeys(
        (0x09B26D, 0x09B278, 0x09B2A3, 0x0A1099, 0x0A2DD4, 0x0A2E63),
        "HANDOFF.md#verified-working-areas",
    ),
    **dict.fromkeys(
        (
            0x0A3D15,
            0x09AB36,
            0x09ACA8,
            0x09AB8C,
            0x09ACF0,
            0x09AB22,
            0x09AB2C,
            0x09AB5E,
            0x09AB6C,
            0x09AB7E,
            0x09AC8E,
            0x09AC98,
            0x09ACC8,
            0x09ACD2,
            0x09ACE0,
            0x09ABC2,
            0x0A1896,
        ),
        "captures/run/212a_s01_prep_current.png",
    ),
    0x09706A: "captures/run/ea22_s01_command_magic_fresh.png",
    # Preparation, shop, arrangement, and name-entry fixed records.
    **dict.fromkeys(
        (
            0x09702C,
            0x097034,
            0x09703C,
            0x097048,
            0x097050,
            0x09705A,
            0x09705E,
            0x097062,
        ),
        "docs/runtime_verification_inventory.md#scenario-1",
    ),
    **dict.fromkeys(
        (0x0A2B72, 0x0A2B7C, 0x0A2B86, 0x0A2B8E, 0x0A2B98, 0x0A2BAC),
        "captures/run/212a_s01_arrangement_current.png",
    ),
    **dict.fromkeys(
        (0x0A37A0, 0x0A37AA, 0x0A37B6),
        "HANDOFF.md#verified-working-areas",
    ),
    0x0A10E0: "docs/runtime_verification_inventory.md#scenario-2",
    0x09B1B6: "captures/run/c7ab_s01_title.png",
    # These global glyphs are visibly exercised by the Scenario 1 dagger/shop
    # path and its spaced completion messages.
    **dict.fromkeys(
        (0x043140, 0x042C80, 0x043300),
        "captures/run/212a_s01_shop_buy_popup.png",
    ),
    0x0A3C9C: "captures/run/d1d7_class_change_start_trigger.png",
}


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
    name_entry_flow = name_entry_flow_report.inventory(japanese, korean)
    name_entry_complete = bool(name_entry_flow["complete"])
    class_change_flow = class_change_flow_report.inventory(japanese, korean)
    class_change_scope = class_change_flow["scope"]
    class_change_complete = (
        class_change_scope["source_transition_count"] == 100
        and class_change_scope["live_verified_unique_screen_count"]
        == class_change_scope["unique_screen_combination_count"]
        and class_change_scope[
            "representative_natural_application_commander_count"
        ]
        == 10
        and class_change_scope[
            "structurally_covered_application_transition_count"
        ]
        == 100
        and class_change_scope[
            "structurally_covered_persistence_transition_count"
        ]
        == 100
    )
    magic_flow = magic_flow_report.inventory(
        japanese,
        korean,
        json.loads(
            magic_flow_report.DEFAULT_RUNTIME_INVENTORY.read_text(
                encoding="utf-8"
            )
        ),
    )
    magic_scope = magic_flow["scope"]
    magic_complete = (
        magic_scope["magic_count"] == 22
        and magic_scope["source_natural_learnable_magic_count"] == 21
        and magic_scope["source_unreachable_magic_ids"] == [18]
        and magic_scope["diagnostic_application_evidence_count"] == 22
        and magic_scope["live_natural_learned_magic_count"] == 11
        and all(
            row["production_source_equivalent"]
            for row in magic_flow["source_locked_ranges"]
        )
    )
    compressed_resources = compressed_resource_report.inventory(japanese, korean)
    compressed_resources_complete = (
        compressed_resources["entry_count"] == 429
        and compressed_resources["known_owner_count"] == 429
        and compressed_resources["unknown_owner_count"] == 0
        and compressed_resources["ownership_record_count"] == 763
        and compressed_resources["dynamic_load_call_count"] == 11
        and len(compressed_resources["dynamic_load_call_owners"]) == 11
        and compressed_resources["unreferenced_candidate_count"] == 2
        and all(
            row["structurally_verified"]
            for row in compressed_resources["entries"]
        )
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
    for row in rows:
        if row["address"] == "0x0A37BE":
            row["reviewed"] = True
            row["live_verified"] = True
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
        live_verified = offset in builder.OPENING_TEXT_LIST_LIVE_VERIFIED_ADDRESSES
        rows.append(
            {
                "group": "opening_text_lists",
                "address": f"0x{offset:06X}",
                "size_bytes": capacity * 2,
                "target_korean": text,
                "modified": changed(japanese, korean, offset, capacity * 2),
                "reviewed": reviewed,
                "live_verified": live_verified,
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

    title_logo_payload, _ = builder.build_title_logo_assets()
    title_logo_resource_size = 1 + len(
        builder.compress_9dfe_literals(title_logo_payload)
    )
    for group, offset, size, target in (
        (
            "title_logo_original_resource_pointer",
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.TITLE_LOGO_RESOURCE_INDEX * 4,
            4,
            "localized title logo resource pointer",
        ),
        (
            "title_logo_active_resource_pointer",
            builder.BYTE_UI_EXT_RESOURCE_TABLE
            + builder.TITLE_LOGO_RESOURCE_INDEX * 4,
            4,
            "active localized title logo resource pointer",
        ),
        (
            "title_logo_layout_record",
            builder.TITLE_LOGO_LAYOUT_RECORD,
            builder.TITLE_LOGO_LAYOUT_RECORD_SIZE,
            builder.TITLE_LOGO_TEXT,
        ),
        (
            "title_logo_resource_payload",
            builder.TITLE_LOGO_RESOURCE_RELOC_BASE,
            title_logo_resource_size,
            f"{builder.TITLE_LOGO_TEXT} indexed title tiles",
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

    battle_ui_terrain_resource_size = 1 + len(
        builder.compress_9dfe_literals(
            bytes(builder.BATTLE_UI_TERRAIN_RESOURCE_ORIGINAL_SIZE)
        )
    )
    for group, offset, size, target in (
        (
            "battle_ui_terrain_original_resource_pointer",
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX * 4,
            4,
            "localized battle UI terrain resource pointer",
        ),
        (
            "battle_ui_terrain_active_resource_pointer",
            builder.BYTE_UI_EXT_RESOURCE_TABLE
            + builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX * 4,
            4,
            "active localized battle UI terrain resource pointer",
        ),
        (
            "battle_ui_terrain_resource_payload",
            builder.BATTLE_UI_TERRAIN_RESOURCE_RELOC_BASE,
            battle_ui_terrain_resource_size,
            "전투 중앙 지형 타일",
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
            "shop_inventory_full_glyphs",
            builder.SHOP_INVENTORY_FULL_GLYPH_LIST + 13 * 2,
            4,
            "불가",
        ),
        (
            "shop_inventory_full_message",
            builder.SHOP_INVENTORY_FULL_TOKEN_STREAM,
            len(builder.SHOP_INVENTORY_FULL_SOURCE_TOKENS) * 2,
            builder.SHOP_INVENTORY_FULL_MESSAGE_TEXT,
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

    rows.append(
        {
            "group": "control_settings_glyph_list",
            "address": f"0x{builder.CONTROL_SETTINGS_GLYPH_LIST:06X}",
            "size_bytes": len(builder.CONTROL_SETTINGS_ORIGINAL_GLYPHS) * 2,
            "target_korean": "Korean labels with preserved R/G/B, digits, and A/B/C/S slots",
            "modified": changed(
                japanese,
                korean,
                builder.CONTROL_SETTINGS_GLYPH_LIST,
                len(builder.CONTROL_SETTINGS_ORIGINAL_GLYPHS) * 2,
            ),
            "reviewed": True,
            "live_verified": True,
        }
    )
    for offset, original, replacement in builder.CONTROL_SETTINGS_ROWS:
        rows.append(
            {
                "group": "control_settings_layout_rows",
                "address": f"0x{offset:06X}",
                "size_bytes": len(original) * 2,
                "target_korean": "/".join(str(token) for token in replacement),
                "modified": changed(japanese, korean, offset, len(original) * 2),
                "reviewed": True,
                "live_verified": True,
            }
        )

    for group, offset, size, target in (
        (
            "sound_test_render_hook",
            builder.SOUND_TEST_RENDER_HOOK,
            len(builder.SOUND_TEST_RENDER_HOOK_ORIGINAL),
            "redirect the hidden 77-row sound-test label renderer",
        ),
        (
            "sound_test_render_routine",
            builder.SOUND_TEST_RENDER_ROUTINE,
            len(builder._build_sound_test_renderer()),
            "render a relocated 15-cell tile row while preserving stock sound IDs",
        ),
        (
            "sound_test_tile_table",
            builder.SOUND_TEST_TILE_TABLE,
            builder.SOUND_TEST_ROW_COUNT * builder.SOUND_TEST_LABEL_WIDTH * 2,
            "77 localized hidden sound-test labels",
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
                "live_verified": True,
            }
        )

    for group, offset, size, target in (
        (
            "item_discard_notice_glyph_pointer",
            builder.ITEM_DISCARD_NOTICE_GLYPH_POINTER,
            4,
            "relocated full-inventory notice glyph list pointer",
        ),
        (
            "item_discard_notice_token_pointer",
            builder.ITEM_DISCARD_NOTICE_TOKEN_POINTER,
            4,
            "relocated full-inventory notice token pointer",
        ),
        (
            "item_discard_notice_glyphs",
            builder.ITEM_DISCARD_NOTICE_RELOC_GLYPH_LIST,
            (
                builder.ITEM_DISCARD_NOTICE_RELOC_TOKEN_STREAM
                - builder.ITEM_DISCARD_NOTICE_RELOC_GLYPH_LIST
            ),
            "spaced Korean notice glyph bank",
        ),
        (
            "item_discard_notice_tokens",
            builder.ITEM_DISCARD_NOTICE_RELOC_TOKEN_STREAM,
            (
                builder.ITEM_DISCARD_NOTICE_RELOC_LIMIT
                - builder.ITEM_DISCARD_NOTICE_RELOC_TOKEN_STREAM
            ),
            " / ".join(builder.ITEM_DISCARD_NOTICE_LINES),
        ),
        (
            "shop_item_selection_prompt",
            builder.SHOP_ITEM_SELECTION_TOKEN_STREAM,
            len(builder.SHOP_ITEM_SELECTION_SOURCE_TOKENS) * 2,
            builder.SHOP_ITEM_SELECTION_TEXT,
        ),
        (
            "item_discard_list_hook",
            builder.ITEM_DISCARD_LIST_RENDER_HOOK,
            len(builder.ITEM_DISCARD_LIST_RENDER_HOOK_ORIGINAL),
            "redirect dormant discard list to localized 16x16 renderer",
        ),
        (
            "item_discard_list_routine",
            builder.ITEM_DISCARD_LIST_RENDER_ROUTINE,
            len(builder._build_item_discard_list_render_routine()),
            "five localized item rows, cursor, page arrows, and page number",
        ),
        (
            "item_discard_prompt_tokens",
            builder.ITEM_DISCARD_PROMPT_TOKEN_STREAM,
            (
                builder.ITEM_DISCARD_PROMPT_TOKEN_STREAM_LIMIT
                - builder.ITEM_DISCARD_PROMPT_TOKEN_STREAM
            ),
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
                "live_verified": True,
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
            "render copyright and 한글화: HSP1324",
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

    evidence_addresses = set(RUNTIME_EVIDENCE_BY_ADDRESS)
    declared_addresses = {int(str(row["address"]), 16) for row in rows}
    unknown_evidence = evidence_addresses - declared_addresses
    if unknown_evidence:
        rendered = ", ".join(f"0x{address:06X}" for address in sorted(unknown_evidence))
        raise ValueError(f"runtime evidence references undeclared patches: {rendered}")
    for row in rows:
        address = int(str(row["address"]), 16)
        evidence = RUNTIME_EVIDENCE_BY_ADDRESS.get(address)
        if evidence is None:
            continue
        row["reviewed"] = True
        row["live_verified"] = True
        row["evidence"] = evidence

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
        summary = group_summary.setdefault(
            row["group"],
            {
                "entry_count": 0,
                "modified_count": 0,
                "reviewed_count": 0,
                "live_verified_count": 0,
            },
        )
        summary["entry_count"] += 1
        summary["modified_count"] += bool(row["modified"])
        summary["reviewed_count"] += bool(row["reviewed"])
        summary["live_verified_count"] += bool(row["live_verified"])

    return {
        "declared_patch_count": len(rows),
        "modified_patch_count": sum(bool(row["modified"]) for row in rows),
        "groups": group_summary,
        "compressed_byte_ui_font": compressed,
        "compressed_resource_ownership": {
            "entry_count": compressed_resources["entry_count"],
            "known_owner_count": compressed_resources["known_owner_count"],
            "unknown_owner_count": compressed_resources["unknown_owner_count"],
            "ownership_record_count": compressed_resources[
                "ownership_record_count"
            ],
            "unreferenced_candidate_count": compressed_resources[
                "unreferenced_candidate_count"
            ],
            "complete": compressed_resources_complete,
            "report": "docs/compressed_resource_inventory.md",
        },
        "name_entry_flow": {
            "selectable_syllable_count": name_entry_flow["scope"][
                "selectable_syllable_count"
            ],
            "maximum_name_syllables": name_entry_flow["scope"][
                "maximum_name_syllables"
            ],
            "source_reference_count": name_entry_flow["scope"][
                "source_reference_count"
            ],
            "source_locked_range_count": name_entry_flow["scope"][
                "source_locked_range_count"
            ],
            "complete": name_entry_complete,
            "report": "docs/name_entry_flow_inventory.md",
        },
        "declared_patches": rows,
        "remaining_inventory_gaps": [
            *(
                []
                if name_entry_complete
                else [
                    "the fixed-palette name-entry flow no longer satisfies "
                    "its source, storage, glyph, or confirmation inventory"
                ]
            ),
            *(
                []
                if class_change_complete
                else [
                    "class-change candidate, application, or persistence "
                    "coverage no longer satisfies the source-locked flow "
                    "inventory"
                ]
            ),
            *(
                []
                if magic_complete
                else [
                    "magic ownership, natural reachability exceptions, or "
                    "application coverage no longer satisfies the "
                    "source-locked flow inventory"
                ]
            ),
            *(
                []
                if compressed_resources_complete
                else [
                    "compressed-resource ownership no longer satisfies the "
                    "source-locked 429-entry inventory"
                ]
            ),
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
        "| Group | Entries | Modified | Reviewed | Live verified |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, group in result["groups"].items():
        lines.append(
            f"| {name} | {group['entry_count']} | {group['modified_count']} | "
            f"{group['reviewed_count']} | {group['live_verified_count']} |"
        )
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
    gaps = result["remaining_inventory_gaps"]
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- None.")
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
        default=Path("roms/builds/Langrisser II (Korean).md"),
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
