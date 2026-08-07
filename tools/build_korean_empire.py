#!/usr/bin/env python3
"""Build the separately maintained Korean Empire V2.0 (96%) edition.

This builder must never use the normal/hard ``main`` pipeline: the Empire
edit reorders character/class tables and inserts code into the original ROM.
Only localization-owned data is relocated; campaign, class, unit, item and
battle-balance bytes remain sourced from the Empire ROM.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_korean_jp_probe import (
    EXPANDED_ROM_SIZE,
    GLYPH_BYTES,
    JP_FONT_BASE,
    SPACE_GLYPH,
    collect_chars,
    install_custom_glyphs,
    put16,
    put32,
)
import scripts.build_korean_jp_probe as jp_builder
from tools.empire_profile import (
    DEFAULT_EMPIRE_ROM,
    EMPIRE_SOURCE_SHA256,
    load_empire_labels,
    validate_empire_source,
)
from tools.jp_event_inventory import inventory as event_inventory
from tools.scenario_data import update_checksum


DEFAULT_REVIEWED_SCRIPT = ROOT / "localization/empire/reviewed/script_ko.json"
DEFAULT_DRAFT_SCRIPT = ROOT / "localization/empire/draft/script_ko.json"
DEFAULT_OUTPUT = ROOT / "roms/builds/Langrisser II (Korean Empire).md"

ORIGINAL_SRAM_START = 0x200001
ORIGINAL_SRAM_END = 0x203FFF
RELOCATED_SRAM_START = 0x400001
RELOCATED_SRAM_END = 0x403FFF
SRAM_DELTA = RELOCATED_SRAM_START - ORIGINAL_SRAM_START
EMPIRE_SRAM_LONG_PATCHES = {
    0x01DE28: 0x203FE1,
    0x01DE5A: 0x203FDD,
    0x01DE6C: 0x200001,
    0x01DE84: 0x203FDD,
    0x01DEF4: 0x203FE1,
    0x01DFAA: 0x203FE1,
    0x01E000: 0x203FE1,
    0x01E058: 0x200009,
    0x01E05C: 0x20329D,
    0x01E060: 0x2035ED,
    0x01E064: 0x20393D,
    0x01E068: 0x203C8D,
    0x01E0BE: 0x203FE1,
}

EMPIRE_FONT_BASE = 0x031200
EMPIRE_FONT_BASE_PATCHES = {
    0x02C3FA: EMPIRE_FONT_BASE,
    0x02C56A: EMPIRE_FONT_BASE,
}

# Normal/hard custom sprites and common localized resources end below this
# bank.  The Empire dialogue occupies roughly 0x30300 bytes, leaving ample
# audited headroom before the reserved upper diagnostic area.
EVENT_RELOC_BASE = 0x320000
# Keep the relocated event bank strictly below the indirect-text glyph bank.
# The draft currently ends near 0x350300, but this hard boundary prevents a
# future translation expansion from silently overwriting the 0x360000 bank.
EVENT_RELOC_LIMIT = 0x360000
INDIRECT_GLYPH_RELOC_BASE = 0x360000
INDIRECT_GLYPH_RELOC_LIMIT = 0x370000
INDIRECT_TOKEN_RELOC_BASE = 0x370000
INDIRECT_TOKEN_RELOC_LIMIT = 0x380000

CONDITION_POINTER_TABLE = 0x098D7A
CONDITION_GLYPH_POINTER_TABLE = 0x0986C6
CONDITION_COUNT = 32
SCENARIO_POINTER_TABLE = 0x09CF7C
SCENARIO_GLYPH_POINTER_TABLE = 0x09B2FC
SCENARIO_COUNT = 31

CONTROL_RE = re.compile(r"\{([0-9A-F]{4})\}")

EMPIRE_INLINE_DISCARD_PROMPT_SOURCE = 0x0180AC
EMPIRE_INLINE_DISCARD_PROMPT_RENDER_HOOK = 0x01807A
EMPIRE_SOUND_TEST_SOURCE_SHA256 = (
    "35f36eb846b971f239649201878a2d518d468b489ef2a43bb5a5e77f2de2b92a"
)
EMPIRE_SOUND_TEST_RENDER_HOOK = 0x00FC74
EMPIRE_BYTE_UI_FONT_LOAD_CALLS = (
    0x00C92A,
    0x00CA7A,
    0x00CC8A,
    0x029DF2,
    0x02D6C8,
    0x02F77C,
)
EMPIRE_BYTE_UI_PREP_FONT_LOAD_CALLS = frozenset({0x029DF2})

# Keys are stable Japanese-edition hook identifiers; values are their exact
# Empire V2.0 (96%) locations.  The edit inserted code in several regions, so
# there is deliberately no global offset assumption here.
EMPIRE_BYTE_UI_SOURCE_OFFSET_MAP = {
    jp_builder.TITLE_CREDIT_FONT_LOAD_HOOK: 0x02D6CE,
    jp_builder.TITLE_COPYRIGHT_RENDER_HOOK: 0x02D776,
    0x0292CA: 0x02932E,
    0x029308: 0x02936C,
    0x029444: 0x0294A8,
    0x02C1C8: 0x02C22C,
    0x02C256: 0x02C2BA,
    0x0254EC: 0x025540,
    0x02BEE4: 0x02BF48,
    0x02C004: 0x02C068,
    0x02C040: 0x02C0A4,
    0x020EDA: 0x020F2E,
    0x020F08: 0x020F5C,
    0x01B546: 0x01B598,
    0x01CBA6: 0x01CBFA,
    0x01CBBC: 0x01CC10,
    jp_builder.BYTE_UI_ENDING_RESULT_FINAL_BANK_HOOK: 0x01CE94,
    jp_builder.BYTE_UI_DIRECT_MAP_RENDER_HOOK: 0x01071C,
    jp_builder.BYTE_UI_PREP_SELECTED_NAME_RENDER_HOOK: 0x027AC8,
    jp_builder.BYTE_UI_PREP_SELECTED_PANEL_RENDER_HOOK: 0x022A48,
    jp_builder.BYTE_UI_PREP_HIRE_CLASS_RENDER_HOOK: 0x022B50,
    0x025CF6: 0x025D5A,
    0x0222A4: 0x0222F8,
    0x0222C6: 0x02231A,
    jp_builder.BYTE_UI_PREP_ROSTER_HOOK: 0x022556,
    jp_builder.BYTE_UI_ROSTER_RENDER_HOOK: 0x029614,
    jp_builder.BYTE_UI_STATUS_RENDER_HOOK: 0x029B88,
    # The Chinese script compacts four shared UI records immediately before
    # the item tables, shifting these labels ten bytes earlier.
    0x0A1099: 0x0A1089,
    0x0A1896: 0x0A1886,
    0x0A18E0: 0x0A18D0,
    0x0A18EC: 0x0A18DC,
    0x0A18F8: 0x0A18E8,
    0x0A2DD4: 0x0A2DC4,
    0x0A2E63: 0x0A2E53,
    0x0A3D15: 0x0A3D05,
}

EMPIRE_BYTE_UI_SOURCE_BYTES_BY_OFFSET = {
    jp_builder.TITLE_COPYRIGHT_RENDER_HOOK: bytes.fromhex(
        "22 78 81 C4 48 E7 9F 9E"
    ),
    **{
        offset: bytes.fromhex("4E B9 00 02 42 C6")
        for offset in jp_builder.BYTE_UI_WORD_RENDER_CALLS
    },
    **{
        offset: bytes.fromhex("4E B9 00 02 55 4A")
        for offset in jp_builder.BYTE_UI_TILE_RENDER_CALLS
    },
    **{
        offset: bytes.fromhex("4E B9 00 02 11 B2")
        for offset in jp_builder.BYTE_UI_MAP_INFO_RENDER_CALLS
    },
    **{
        offset: bytes.fromhex("4E B9 00 01 07 1C")
        for offset in jp_builder.BYTE_UI_DIRECT_MAP_RENDER_CALLS
    },
    **{
        offset: bytes.fromhex("4E B9 00 02 43 DA")
        for offset in jp_builder.BYTE_UI_PLANE_RENDER_CALLS
    },
}

# Exact source-region fingerprint produced by ``patch_empire_byte_ui`` after
# ROM expansion/SRAM relocation and the Empire font-base patch.  The common
# UI installer also writes new tables and renderers into the expanded banks;
# those banks are localization-owned.  This fingerprint keeps every edit in
# the original 2 MiB region explicit so a future shared-UI change cannot
# silently touch Empire gameplay or balance data.
EMPIRE_BYTE_UI_SOURCE_DELTA_COUNT = 1208
EMPIRE_BYTE_UI_SOURCE_DELTA_SHA256 = (
    "1c14a71308e04be12fcd2957b4e16c53a1d2d2a456a16d4971b7fcc01a710458"
)
EMPIRE_COMMON_UI_SOURCE_DELTA_COUNT = 12204
EMPIRE_COMMON_UI_SOURCE_DELTA_SHA256 = (
    "c3d800ffda4e61c04d0f8d0a2ac956fdc70b1ebb87af87f5172bcce96e6963b7"
)
EMPIRE_TITLE_LOGO_LAYOUT_RECORD = 0x0A428E
EMPIRE_BATTLE_UI_TERRAIN_RESOURCE_POINTER = 0x1F7C02
EMPIRE_BATTLE_UI_TERRAIN_RESOURCE_SHA256 = (
    "975fa8f6995b6ff3e7949abd48103372cb35370795bf87812230ef1d14c28e7d"
)
EMPIRE_MAGIC_LIST_GLYPH_SOURCE_SHA256 = (
    "e674b29858fd5bb80b7347701d759fcaed590c5b30dd563cd9040529626df521"
)
EMPIRE_CONTROL_SETTINGS_ORIGINAL_GLYPHS = (
    325, 326, 327, 328, 84, 122, 118, 329, 94, 85,
    86, 87, 88, 89, 90, 91, 330, 103, 256, 255,
    331, 332, 84, 260, 141, 142, 84, 84, 333, 334,
    300, 301, 335, 336, 337, 338, 301, 312, 282, 84,
)
EMPIRE_CONTROL_SETTINGS_ROWS = (
    (0x09AFD4, (0, 1, 2, 3, 4), (0, 1, 2, 3, 32)),
    (0x09AFE4, (16, 20, 2, 3), (4, 32, 2, 3)),
    (0x09B00A, (24, 25, 28, 29, 26, 26), (20, 21, 22, 0, 32, 32)),
    (0x09B01C, (37, 38, 26, 26, 26), (23, 24, 32, 32, 32)),
    (0x09B02C, (21, 26, 23, 26), (28, 29, 30, 32)),
    (0x09B03A, (35, 36, 32, 33, 34, 26, 26), (25, 3, 31, 26, 27, 32, 32)),
    (0x09B04E, (30, 31, 33, 34, 26, 26), (2, 3, 26, 27, 32, 32)),
)
EMPIRE_TITLE_LOAD_GLYPH_LIST = 0x0A2F04
EMPIRE_TITLE_LOAD_GLYPH_LIST_ORIGINAL = (
    252, 94, 85, 86, 87, 88, 89, 90, 91, 92, 93,
    358, 320, 84, 317, 318, 359, 214, 247, 319, 84,
    360, 361, 324, 316, 281, 320, 321, 125, 322, 323,
    84, 84, 311, 312, 256, 120, 254, 104, 257, 253, 119,
)
EMPIRE_TITLE_LOAD_RECORDS = {
    0x0A30C6: (8, "이어하기"),
    0x0A30D8: (4, "시나리오"),
    0x0A30E2: (9, "손상된 데이터"),
    0x0A30F6: (9, "데이터 없음"),
    0x0A310A: (7, "다음 시나리오"),
}
EMPIRE_TITLE_LOAD_RECORD_ORIGINALS = {
    0x0A30C6: (35, 36, 37, 38, 39, 37, 40, 41),
    0x0A30D8: (18, 13, 19, 13),
    0x0A30E2: (23, 24, 28, 29, 30, 13, 13, 13, 13),
    0x0A30F6: (23, 24, 25, 26, 27, 13, 13, 13, 13),
    0x0A310A: (14, 15, 16, 17, 18, 13, 13),
}
EMPIRE_TITLE_SAVE_HEADER_RECORD = 0x0A311A
EMPIRE_TITLE_SAVE_HEADER_ORIGINAL = (17, 6, 11, 13, 12, 0xFFFF)
EMPIRE_TITLE_LOAD_HEADER_RECORD = 0x0A3128
EMPIRE_TITLE_LOAD_HEADER_ORIGINAL = (17, 6, 33, 13, 34, 0xFFFF)
EMPIRE_TITLE_LOAD_HEADER_LEA = 0x029E4A
EMPIRE_TITLE_LOAD_HEADER_LEA_ORIGINAL = bytes.fromhex(
    "41 F9 00 0A 31 28"
)
EMPIRE_TITLE_MAIN_MENU_RECORD = 0x0A3136
EMPIRE_TITLE_MAIN_MENU_START_OFFSET = 0x0A3148
EMPIRE_TITLE_MAIN_MENU_LOAD_OFFSET = 0x0A3154
EMPIRE_TITLE_MAIN_MENU_RECORD_LEA = 0x02A2D2
EMPIRE_TITLE_MAIN_MENU_RECORD_LEA_ORIGINAL = bytes.fromhex(
    "41 F9 00 0A 31 36"
)
EMPIRE_TITLE_MAIN_MENU_WINDOW_WIDTH_OFFSETS = (0x02A2DA, 0x02A2F4)

# The Chinese Empire edit keeps the stock 37 gameplay item IDs, but moves
# both UI pointer tables and their glyph banks 0x10 bytes earlier.  Several
# renderer routines are shifted independently by inserted Empire code.  Keep
# every one of those locations explicit; the shared localization routines
# validate the original bytes before changing them.
EMPIRE_ITEM_GLYPH_LIST_BASE = 0x0A149C
EMPIRE_ITEM_GLYPH_LIST_REFS = (0x026988,)
EMPIRE_ITEM_NAME_POINTER_TABLE = 0x0A18F2
EMPIRE_ITEM_NAME_GLYPH_LOAD_HOOK = 0x021CC0
EMPIRE_ITEM_NAME_GLYPH_LOAD_TARGET = 0x02C328
EMPIRE_ITEM_NAME_POPUP_BUILD_HOOK = 0x027954
EMPIRE_ITEM_NAME_POPUP_RETURN_TARGET = 0x02797A
EMPIRE_ITEM_NAME_LIST_RENDER_HOOKS = (
    (0x02701C, 0x0270A8, 0x027032, jp_builder.ITEM_NAME_LIST_RENDER_HOOKS[0][3]),
    (0x027A42, 0x027A80, 0x027A58, jp_builder.ITEM_NAME_LIST_RENDER_HOOKS[1][3]),
)
EMPIRE_ITEM_DISCARD_LIST_RENDER_HOOK = 0x017F36
EMPIRE_ITEM_DESCRIPTION_GLYPH_LIST_BASE = 0x0A151E
EMPIRE_ITEM_DESCRIPTION_GLYPH_LIST_REF = 0x027320
EMPIRE_ITEM_DESCRIPTION_GLYPH_LOAD_COUNT_OFFSET = 0x027326
EMPIRE_ITEM_DESCRIPTION_POINTER_TABLE = 0x0A1D6C
EMPIRE_WORD_ITEM_NAME_POINTER_TABLE = 0x001068
EMPIRE_WORD_ITEM_NAME_SOURCE_RANGE = (0x001068, 0x0012F6)
EMPIRE_WORD_ITEM_NAME_SOURCE_SHA256 = (
    "435c3ab8c6efe9f21181a7b3f6f6fca98e5b31269bba445e0f8531e156f49b74"
)
EMPIRE_WORD_ITEM_NAME_RELOC_BASE = 0x381000
EMPIRE_WORD_ITEM_NAME_RELOC_LIMIT = 0x382000
EMPIRE_ITEM_NAME_TOKEN_RELOC_BASE = 0x382000
EMPIRE_ITEM_NAME_TOKEN_RELOC_LIMIT = 0x383000
EMPIRE_SHOP_PURCHASE_SUFFIX = 0x0A17B8
EMPIRE_SHOP_SELL_SUFFIX = 0x0A17C8
EMPIRE_SHOP_PURCHASE_SUFFIX_SOURCE = (2, 4, 5, 3, 16, 16, 16)
EMPIRE_SHOP_SELL_SUFFIX_SOURCE = (2, 6, 7, 3, 16, 16, 16)
EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_LIST = 0x0A16A0
EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_SOURCE = (
    0x010A, 0x010B, 0x0153, 0x0154, 0x0155, 0x007D,
    0x0156, 0x0157, 0x0158, 0x0159, 0x00D6, 0x0128,
    0x0054, 0x0054, 0x0054, 0x0054, 0x0054,
)
EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_POINTER = 0x02621C
EMPIRE_ITEM_DISCARD_NOTICE_TOKEN_POINTER = 0x026230
EMPIRE_ITEM_DISCARD_NOTICE_TOKEN_STREAM = 0x0A17D8
EMPIRE_ITEM_DISCARD_NOTICE_SOURCE_TOKENS = (
    0xFFFB, 0x0001, 0x0001,
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006,
    0x000C, 0x000C, 0x000C, 0x000C, 0xFFFE,
    0x0007, 0x0008, 0x0009, 0x000A, 0x000B,
    0x000C, 0x000C, 0x000C, 0x000C, 0xFFFE, 0xFFFF,
)
EMPIRE_ITEM_DISCARD_CONFIRM_GLYPH_LIST = 0x0A16E2
EMPIRE_ITEM_DISCARD_CONFIRM_GLYPH_SOURCE = (
    0x0158, 0x0159, 0x015C, 0x0074, 0x015D, 0x015E,
    0x00FC, 0x0054, 0x01D0, 0x016C, 0x0054, 0x0054,
    0x0102, 0x0077, 0x00FF, 0x00FE, 0x0078,
)
EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_STREAM = 0x0A1834
EMPIRE_ITEM_DISCARD_CONFIRM_SOURCE_TOKENS = (
    0x0000, 0x0001, 0x0002, 0x0007, 0x0007, 0xFFFE,
    0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x0007, 0x0007,
    0xFFFF,
)
EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_POINTER = 0x0264EC
EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_RELOC = 0x383000
EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_RELOC_LIMIT = 0x383100
EMPIRE_SHOP_POSSESSION_GLYPH_LIST = 0x0A1706
EMPIRE_SHOP_INVENTORY_FULL_TOKEN_STREAM = 0x0A177A
EMPIRE_SHOP_SELL_GLYPH_LIST = 0x0A16C4
EMPIRE_SHOP_ITEM_SELECTION_TOKEN_STREAM = 0x0A180C
EMPIRE_SHOP_SELL_TITLE_TOKEN_STREAM = 0x0A17A8
EMPIRE_SHOP_SELL_TITLE_SOURCE_TOKENS = (0, 1, 6, 7, 16, 16)

# Direct-word battle/arrangement resources use the same renderer geometry as
# the Japanese ROM, but the Empire edit replaces the glyph IDs with Chinese
# and compacts the 0xA2xxxx/0xA3xxxx data blocks by 0x10 bytes.  Validate the
# complete source records before localizing them so a table move cannot turn
# UI work into a campaign-data mutation.
EMPIRE_BATTLE_COMMAND_GLYPH_LIST = 0x09706A
EMPIRE_BATTLE_COMMAND_GLYPH_SOURCE = (
    276, 277, 149, 48, 12, 5, 158, 159, 278, 279, 78, 280, 108,
    109, 281, 242, 84, 84, 282, 283, 284, 4, 80, 285, 97, 147,
    286, 287, 288, 281, 116, 117, 83, 84, 84, 84, 289, 84,
    290, 141, 142, 84, 84, 291, 174, 292, 293, 150, 84, 84,
    254, 256,
)
EMPIRE_BATTLE_RESULT_HEADER_GLYPH_LIST = 0x0A2D78
EMPIRE_BATTLE_RESULT_HEADER_GLYPH_SOURCE = (80, 434, 1135, 683)
EMPIRE_ENDING_STATUS_GLYPH_LIST = 0x089146
EMPIRE_ENDING_STATUS_GLYPH_SOURCE = (
    291, 48, 561, 1436, 677, 332, 139, 1436,
)
EMPIRE_CLASS_CHANGE_GLYPH_LIST = 0x0A3C8C
EMPIRE_CLASS_CHANGE_GLYPH_SOURCE = (
    116, 349, 1498, 1668, 364, 84, 84, 84, 84, 84, 84,
    1137, 161, 12, 5,
)
EMPIRE_ARRANGE_WARNING_GLYPH_OFFSET = 0x0A2B8C
EMPIRE_ARRANGE_WARNING_GLYPH_SOURCE = (
    293, 150, 356, 5, 1112, 327, 84, 84,
)
EMPIRE_ARRANGE_MENU_GLYPH_LIST = 0x0A2B9C
EMPIRE_ARRANGE_MENU_GLYPH_SOURCE = (357, 727, 327, 328, 222, 277)
EMPIRE_ARRANGE_WARNING_TOKEN_OFFSET = 0x0A2C1E
EMPIRE_ARRANGE_WARNING_TOKEN_SOURCE = (
    1, 11, 12, 13, 14, 15, 28, 29,
    30, 31, 34, 35, 21, 22, 39, 39,
)

_EMPIRE_SHERRY_ENDING = jp_builder.OPENING_TEXT_LIST_PATCHES[0x0A6DB8][1]
_EMPIRE_TRAVEL_ENDING = jp_builder.OPENING_TEXT_LIST_PATCHES[0x0A6DFE][1].ljust(64)
EMPIRE_OPENING_TEXT_LIST_PATCHES = OrderedDict(
    jp_builder.OPENING_TEXT_LIST_PATCHES
)
# Unlike the Japanese source, the Chinese edit removes Sherry's early FFFF
# and overlaps 29 words of the following speaker's line.  Preserve that exact
# renderer geometry while reusing the already reviewed Korean ending text.
EMPIRE_OPENING_TEXT_LIST_PATCHES[0x0A6DB8] = (
    0x40,
    _EMPIRE_SHERRY_ENDING.ljust(35) + _EMPIRE_TRAVEL_ENDING[:29],
)
EMPIRE_OPENING_TEXT_LIST_PATCHES[0x0A6DFE] = (0x40, _EMPIRE_TRAVEL_ENDING)
EMPIRE_OPENING_TEXT_LIST_OVERLAPS = {
    **jp_builder.OPENING_TEXT_LIST_OVERLAPS,
    (0x0A6DB8, 0x0A6DFE): 29,
}
EMPIRE_OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES = {
    **jp_builder.OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES,
    0x0A6DB8: None,
    0x0A6DFE: 64,
}


def empire_sound_test_labels() -> tuple[str, ...]:
    labels = list(jp_builder.SOUND_TEST_LABELS)
    labels[71:75] = (
        "남자 SCREAM 5",
        "BOMB HIGH",
        "BOMB NORMAL",
        "BOMB LOW",
    )
    return tuple(labels)


def patch_empire_byte_ui(
    data: bytearray,
    *,
    install_title_credit_hooks: bool = True,
) -> dict[str, int]:
    """Install the common Korean UI using Empire-specific IDs and hooks."""

    class_labels, name_labels = load_empire_labels()
    string_patches = dict(jp_builder.BYTE_UI_STRING_PATCHES)
    # The normal edition stores Bald here; Empire replaces the same compact
    # backing slot with Klaus.  The complete relocated name table already
    # supplies the edition-correct label, so do not overwrite this source
    # scratch record with the normal-edition name.
    string_patches.pop(0x061B1C)
    return jp_builder.patch_byte_ui_strings(
        data,
        title_version_text="EMPIRE PREVIEW",
        class_labels=class_labels,
        name_labels=name_labels,
        validate_sources=False,
        inline_discard_prompt_source=EMPIRE_INLINE_DISCARD_PROMPT_SOURCE,
        inline_discard_prompt_render_hook=(
            EMPIRE_INLINE_DISCARD_PROMPT_RENDER_HOOK
        ),
        sound_test_source_sha256=EMPIRE_SOUND_TEST_SOURCE_SHA256,
        sound_test_labels=empire_sound_test_labels(),
        sound_test_render_hook=EMPIRE_SOUND_TEST_RENDER_HOOK,
        byte_ui_font_load_calls=EMPIRE_BYTE_UI_FONT_LOAD_CALLS,
        byte_ui_prep_font_load_calls=EMPIRE_BYTE_UI_PREP_FONT_LOAD_CALLS,
        source_offset_map=EMPIRE_BYTE_UI_SOURCE_OFFSET_MAP,
        source_bytes_by_offset=EMPIRE_BYTE_UI_SOURCE_BYTES_BY_OFFSET,
        byte_ui_string_patches=string_patches,
        install_title_credit_hooks=install_title_credit_hooks,
        title_credit_text_render_routine=0x02D9EA,
        # Empire renders its existing copyright record in the immediately
        # preceding routine.  This hook replaces only the edition/version
        # renderer that originally jumped to the Chinese extension at 0x6900.
        title_credit_copyright_record=None,
    )


def validate_empire_byte_ui_delta(
    baseline: bytes | bytearray,
    patched: bytes | bytearray,
    *,
    source_size: int,
) -> set[int]:
    """Return the exact, fingerprinted Empire byte-UI source offsets."""

    if len(baseline) != len(patched):
        raise ValueError("Empire byte-UI validation requires equal ROM sizes")
    if source_size > len(baseline):
        raise ValueError("Empire source size exceeds expanded ROM size")
    changed = {
        offset
        for offset, (before, after) in enumerate(
            zip(baseline[:source_size], patched[:source_size])
        )
        if before != after
    }
    digest = hashlib.sha256()
    for offset in sorted(changed):
        digest.update(offset.to_bytes(4, "big"))
        digest.update(bytes((patched[offset],)))
    actual_sha256 = digest.hexdigest()
    if len(changed) != EMPIRE_BYTE_UI_SOURCE_DELTA_COUNT:
        raise ValueError(
            "Empire byte-UI source delta count changed: "
            f"{len(changed)} != {EMPIRE_BYTE_UI_SOURCE_DELTA_COUNT}"
        )
    if actual_sha256 != EMPIRE_BYTE_UI_SOURCE_DELTA_SHA256:
        raise ValueError(
            "Empire byte-UI source delta fingerprint changed: "
            f"{actual_sha256} != {EMPIRE_BYTE_UI_SOURCE_DELTA_SHA256}"
        )
    return changed


def validate_empire_common_ui_delta(
    baseline: bytes | bytearray,
    patched: bytes | bytearray,
    *,
    source_size: int,
    patched_variants: tuple[bytes | bytearray, ...] = (),
) -> set[int]:
    """Validate the source-region delta of the directly reusable UI set."""

    if len(baseline) != len(patched):
        raise ValueError("Empire common-UI validation requires equal ROM sizes")
    changed = {
        offset
        for offset, (before, after) in enumerate(
            zip(baseline[:source_size], patched[:source_size])
        )
        if before != after
    }
    for variant in patched_variants:
        changed.update(
            offset
            for offset, (before, after) in enumerate(
                zip(baseline[:source_size], variant[:source_size])
            )
            if before != after
        )
    # Some of these records contain 16x16 glyph IDs.  Their values are
    # intentionally allowed to change as reviewed dialogue adds or removes
    # glyphs, while the source offsets must stay invariant.  Every individual
    # patch routine validates its exact source record before writing; hash the
    # complete offset set here to guard the localization/gameplay boundary.
    digest = hashlib.sha256()
    for offset in sorted(changed):
        digest.update(offset.to_bytes(4, "big"))
    actual_sha256 = digest.hexdigest()
    if len(changed) != EMPIRE_COMMON_UI_SOURCE_DELTA_COUNT:
        raise ValueError(
            "Empire common-UI source delta count changed: "
            f"{len(changed)} != {EMPIRE_COMMON_UI_SOURCE_DELTA_COUNT}"
        )
    if actual_sha256 != EMPIRE_COMMON_UI_SOURCE_DELTA_SHA256:
        raise ValueError(
            "Empire common-UI source delta fingerprint changed: "
            f"{actual_sha256} != {EMPIRE_COMMON_UI_SOURCE_DELTA_SHA256}"
        )
    return changed


def _apply_empire_common_ui_direct_patches(
    data: bytearray,
    glyph_by_char: dict[str, int],
    *,
    include_opening_text: bool = True,
    include_title_logo: bool = True,
    include_title_screens: bool = True,
) -> None:
    """Apply the direct/common UI patch set without fingerprinting it."""

    jp_builder.patch_raw_byte_strings(data)
    jp_builder.patch_wide_byte_glyphs(data)
    jp_builder.patch_start_menu(data, glyph_by_char)
    jp_builder.patch_start_submenus(data, glyph_by_char)
    jp_builder.patch_prep_menu_trailing_cells(data)
    jp_builder.patch_route_title(data, glyph_by_char)
    jp_builder.patch_scenario_header(data, glyph_by_char)
    patch_empire_direct_word_sequences(data, glyph_by_char)
    patch_empire_direct_token_streams(data)
    if include_opening_text:
        jp_builder.patch_opening_text_lists(
            data,
            glyph_by_char,
            offset_delta=-0x10,
            patches=EMPIRE_OPENING_TEXT_LIST_PATCHES,
            overlaps=EMPIRE_OPENING_TEXT_LIST_OVERLAPS,
            source_terminator_indices=(
                EMPIRE_OPENING_TEXT_LIST_SOURCE_TERMINATOR_INDICES
            ),
        )
    if include_title_logo:
        jp_builder.patch_title_logo_resource(
            data,
            layout_record_offset=EMPIRE_TITLE_LOGO_LAYOUT_RECORD,
        )
    jp_builder.patch_battle_ui_terrain_resource(
        data,
        source_pointer=EMPIRE_BATTLE_UI_TERRAIN_RESOURCE_POINTER,
        source_sha256=EMPIRE_BATTLE_UI_TERRAIN_RESOURCE_SHA256,
    )
    jp_builder.patch_magic_list_names(
        data,
        glyph_source_sha256=EMPIRE_MAGIC_LIST_GLYPH_SOURCE_SHA256,
    )
    jp_builder.patch_control_settings_screen(
        data,
        glyph_by_char,
        original_glyphs=EMPIRE_CONTROL_SETTINGS_ORIGINAL_GLYPHS,
        rows=EMPIRE_CONTROL_SETTINGS_ROWS,
    )
    if include_title_screens:
        jp_builder.patch_title_load_screen(
            data,
            glyph_by_char,
            glyph_list_offset=EMPIRE_TITLE_LOAD_GLYPH_LIST,
            glyph_list_original=EMPIRE_TITLE_LOAD_GLYPH_LIST_ORIGINAL,
            records=EMPIRE_TITLE_LOAD_RECORDS,
            record_originals=EMPIRE_TITLE_LOAD_RECORD_ORIGINALS,
            save_header_record=EMPIRE_TITLE_SAVE_HEADER_RECORD,
            save_header_original=EMPIRE_TITLE_SAVE_HEADER_ORIGINAL,
            load_header_record=EMPIRE_TITLE_LOAD_HEADER_RECORD,
            load_header_original=EMPIRE_TITLE_LOAD_HEADER_ORIGINAL,
            load_header_lea=EMPIRE_TITLE_LOAD_HEADER_LEA,
            load_header_lea_original=EMPIRE_TITLE_LOAD_HEADER_LEA_ORIGINAL,
        )
        jp_builder.patch_title_main_menu(
            data,
            record_offset=EMPIRE_TITLE_MAIN_MENU_RECORD,
            start_offset=EMPIRE_TITLE_MAIN_MENU_START_OFFSET,
            load_offset=EMPIRE_TITLE_MAIN_MENU_LOAD_OFFSET,
            record_lea=EMPIRE_TITLE_MAIN_MENU_RECORD_LEA,
            record_lea_original=EMPIRE_TITLE_MAIN_MENU_RECORD_LEA_ORIGINAL,
            window_width_offsets=EMPIRE_TITLE_MAIN_MENU_WINDOW_WIDTH_OFFSETS,
        )
    patch_empire_items(data, glyph_by_char)


def patch_empire_common_ui_isolation(
    data: bytearray,
    glyph_by_char: dict[str, int],
    *,
    source_size: int,
    variant: str,
) -> set[int]:
    """Build one explicitly non-release UI isolation variant."""

    before = bytearray(data)
    if variant not in {"direct-only"}:
        patch_empire_byte_ui(
            data,
            install_title_credit_hooks=(
                variant != "byte-no-title-credit"
            ),
        )
    if variant not in {"byte-only", "byte-no-title-credit"}:
        _apply_empire_common_ui_direct_patches(
            data,
            glyph_by_char,
            include_opening_text=variant != "no-opening",
            include_title_logo=variant != "no-title-logo",
            include_title_screens=variant != "no-title-screens",
        )
    return {
        offset
        for offset, (old, new) in enumerate(
            zip(before[:source_size], data[:source_size])
        )
        if old != new
    }


def patch_empire_common_ui(
    data: bytearray,
    glyph_by_char: dict[str, int],
    *,
    source_size: int,
) -> tuple[dict[str, int], set[int]]:
    """Install only common UI surfaces proven identical in the Empire edit."""

    before_byte_ui = bytearray(data)
    byte_ui_code_by_char = patch_empire_byte_ui(data)
    byte_ui_offsets = validate_empire_byte_ui_delta(
        before_byte_ui,
        data,
        source_size=source_size,
    )

    before_direct_ui = bytearray(data)
    _apply_empire_common_ui_direct_patches(data, glyph_by_char)

    # A translated script changes the installed glyph IDs as new Hangul is
    # added.  A real UI write can consequently become a byte-for-byte no-op
    # against the source, making a diff-only offset fingerprint fluctuate as
    # review progresses.  Validate the patch surface with a deterministic,
    # per-character probe mapping instead; use the real delta only as an
    # additional allow-list for the final localization-boundary check.
    probe = bytearray(before_direct_ui)
    probe_glyphs = {
        char: 0x0200 + (ord(char) % 0x7000)
        for char in glyph_by_char
    }
    _apply_empire_common_ui_direct_patches(probe, probe_glyphs)
    inverse_probe = bytearray(before_direct_ui)
    inverse_probe_glyphs = {
        char: code ^ 0xFFFF for char, code in probe_glyphs.items()
    }
    _apply_empire_common_ui_direct_patches(
        inverse_probe,
        inverse_probe_glyphs,
    )
    direct_ui_offsets = validate_empire_common_ui_delta(
        before_direct_ui,
        probe,
        source_size=source_size,
        patched_variants=(inverse_probe,),
    )
    actual_direct_offsets = {
        offset
        for offset, (before, after) in enumerate(
            zip(before_direct_ui[:source_size], data[:source_size])
        )
        if before != after
    }
    unexpected_actual_offsets = actual_direct_offsets - direct_ui_offsets
    if unexpected_actual_offsets:
        raise ValueError(
            "Empire common-UI actual write escaped deterministic surface: "
            f"0x{min(unexpected_actual_offsets):06X}"
        )
    return byte_ui_code_by_char, byte_ui_offsets | direct_ui_offsets


def patch_empire_direct_token_streams(data: bytearray) -> None:
    """Patch the two shop suffixes at their Empire-shifted locations."""

    rows = (
        (
            EMPIRE_SHOP_PURCHASE_SUFFIX,
            EMPIRE_SHOP_PURCHASE_SUFFIX_SOURCE,
            (6, 7, 8, 9, 10),
        ),
        (
            EMPIRE_SHOP_SELL_SUFFIX,
            EMPIRE_SHOP_SELL_SUFFIX_SOURCE,
            (6, 7, 11, 12, 10),
        ),
    )
    for offset, expected, target in rows:
        actual = tuple(jp_builder.read_word_list(data, offset))
        if actual != expected:
            raise ValueError(
                f"Empire shop suffix at 0x{offset:06X} changed: "
                f"{actual!r} != {expected!r}"
            )
        jp_builder.write_token_stream(
            data,
            offset,
            list(target),
            len(expected) + 1,
        )


def patch_empire_direct_word_sequences(
    data: bytearray,
    glyph_by_char: dict[str, int],
) -> None:
    """Localize Empire battle/arrangement records at their proven offsets."""

    def validate_words(
        offset: int,
        expected: tuple[int, ...],
        label: str,
    ) -> None:
        actual = tuple(
            jp_builder.be16(data, offset + index * 2)
            for index in range(len(expected))
        )
        if actual != expected:
            raise ValueError(
                f"Empire {label} source changed: {actual!r} != {expected!r}"
            )

    def write_text(offset: int, text: str, capacity: int) -> None:
        values = [
            SPACE_GLYPH if char == " " else glyph_by_char[char]
            for char in text
        ]
        if len(values) > capacity:
            raise ValueError(
                f"Empire direct word text needs {len(values)} slots, "
                f"only {capacity}: {text!r}"
            )
        values.extend([SPACE_GLYPH] * (capacity - len(values)))
        for index, value in enumerate(values):
            put16(data, offset + index * 2, value)

    validate_words(
        EMPIRE_BATTLE_COMMAND_GLYPH_LIST,
        EMPIRE_BATTLE_COMMAND_GLYPH_SOURCE,
        "battle-command glyph list",
    )
    validate_words(
        EMPIRE_BATTLE_RESULT_HEADER_GLYPH_LIST,
        EMPIRE_BATTLE_RESULT_HEADER_GLYPH_SOURCE,
        "battle-result header",
    )
    validate_words(
        EMPIRE_ENDING_STATUS_GLYPH_LIST,
        EMPIRE_ENDING_STATUS_GLYPH_SOURCE,
        "ending-status glyph list",
    )
    validate_words(
        EMPIRE_CLASS_CHANGE_GLYPH_LIST,
        EMPIRE_CLASS_CHANGE_GLYPH_SOURCE,
        "class-change glyph list",
    )
    validate_words(
        EMPIRE_ARRANGE_WARNING_GLYPH_OFFSET,
        EMPIRE_ARRANGE_WARNING_GLYPH_SOURCE,
        "arrangement-warning glyph list",
    )
    validate_words(
        EMPIRE_ARRANGE_MENU_GLYPH_LIST,
        EMPIRE_ARRANGE_MENU_GLYPH_SOURCE,
        "arrangement-menu glyph list",
    )
    validate_words(
        EMPIRE_ARRANGE_WARNING_TOKEN_OFFSET,
        EMPIRE_ARRANGE_WARNING_TOKEN_SOURCE,
        "arrangement-warning token stream",
    )

    write_text(EMPIRE_BATTLE_COMMAND_GLYPH_LIST, "이동공격마법소환치료명령", 12)
    write_text(EMPIRE_BATTLE_RESULT_HEADER_GLYPH_LIST, "전과보고", 4)
    write_text(EMPIRE_ENDING_STATUS_GLYPH_LIST, "격파횟수퇴각횟수", 8)
    write_text(
        EMPIRE_CLASS_CHANGE_GLYPH_LIST,
        jp_builder.CLASS_CHANGE_GLYPH_TEXT,
        len(EMPIRE_CLASS_CHANGE_GLYPH_SOURCE),
    )

    # The command rows and unit notices share the 52-slot battle glyph bank.
    for slot, char in jp_builder.ORDER_SUBMENU_GLYPH_SLOTS.items():
        put16(data, EMPIRE_BATTLE_COMMAND_GLYPH_LIST + slot * 2, glyph_by_char[char])
    order_rows = ([0, 1], [2, 3], [22, 23], [24, 1])
    for row, tokens in enumerate(order_rows):
        row_offset = jp_builder.ORDER_SUBMENU_TOKEN_STREAM + row * 6
        put16(data, row_offset, tokens[0])
        put16(data, row_offset + 2, tokens[1])
    for slot, char in jp_builder.UNIT_NOTICE_GLYPH_SLOTS.items():
        put16(data, EMPIRE_BATTLE_COMMAND_GLYPH_LIST + slot * 2, glyph_by_char[char])
    for slot in jp_builder.UNIT_NOTICE_BLANK_GLYPH_SLOTS:
        put16(data, EMPIRE_BATTLE_COMMAND_GLYPH_LIST + slot * 2, SPACE_GLYPH)

    notice_rows = (
        (
            jp_builder.ENEMY_UNIT_NOTICE_TOKEN_STREAM,
            (43, 38, 39, 40, 41, 42, 16, 17),
            (43, 38, 0x3F, 39, 40, 41, 42, 16),
        ),
        (
            jp_builder.NPC_UNIT_NOTICE_TOKEN_STREAM,
            (50, 13, 51, 39, 40, 41, 42, 16, 17),
            (50, 13, 51, 0x3F, 39, 40, 41, 42, 16),
        ),
        (
            jp_builder.ACTED_UNIT_NOTICE_TOKEN_STREAM,
            (45, 1, 48, 49, 39, 40, 41, 42, 16, 17),
            (45, 1, 48, 49, 0x3F, 39, 40, 41, 42, 16),
        ),
    )
    for offset, expected, target in notice_rows:
        validate_words(offset, expected, "unit-notice token stream")
        for index, value in enumerate(target):
            put16(data, offset + index * 2, value)

    write_text(
        EMPIRE_ARRANGE_MENU_GLYPH_LIST,
        "이동순변경자",
        len(EMPIRE_ARRANGE_MENU_GLYPH_SOURCE),
    )
    for index, char in enumerate(jp_builder.ARRANGE_WARNING_GLYPH_TEXT):
        put16(
            data,
            EMPIRE_ARRANGE_WARNING_GLYPH_OFFSET + index * 2,
            glyph_by_char[char],
        )
    for index, token in enumerate(jp_builder.ARRANGE_WARNING_KOREAN_TOKENS):
        put16(data, EMPIRE_ARRANGE_WARNING_TOKEN_OFFSET + index * 2, token)


def patch_empire_word_item_names(
    data: bytearray,
    glyph_by_char: dict[str, int],
) -> None:
    """Relocate the Chinese edit's compact word-rendered item names."""

    start, end = EMPIRE_WORD_ITEM_NAME_SOURCE_RANGE
    digest = hashlib.sha256(bytes(data[start:end])).hexdigest()
    if digest != EMPIRE_WORD_ITEM_NAME_SOURCE_SHA256:
        raise ValueError(
            "Empire word item-name source changed: "
            f"{digest} != {EMPIRE_WORD_ITEM_NAME_SOURCE_SHA256}"
        )
    pointers = tuple(
        jp_builder.word_swapped_pointer(
            data, EMPIRE_WORD_ITEM_NAME_POINTER_TABLE + index * 4
        )
        for index in range(37)
    )
    if pointers != jp_builder.WORD_ITEM_NAME_POINTERS:
        raise ValueError("Empire word item-name pointer table changed")
    cursor = EMPIRE_WORD_ITEM_NAME_RELOC_BASE
    for index, text in enumerate(jp_builder.ITEM_NAME_PATCHES[:37]):
        values = [glyph_by_char[char] for char in text if char != " "]
        byte_length = (len(values) + 1) * 2
        if cursor + byte_length > EMPIRE_WORD_ITEM_NAME_RELOC_LIMIT:
            raise ValueError("Empire word item-name relocation overflowed")
        if any(value != 0xFF for value in data[cursor : cursor + byte_length]):
            raise ValueError("Empire word item-name relocation area is occupied")
        pointer_offset = EMPIRE_WORD_ITEM_NAME_POINTER_TABLE + index * 4
        put16(data, pointer_offset, cursor & 0xFFFF)
        put16(data, pointer_offset + 2, cursor >> 16)
        for value in values:
            put16(data, cursor, value)
            cursor += 2
        put16(data, cursor, 0xFFFF)
        cursor += 2


def patch_empire_items(
    data: bytearray,
    glyph_by_char: dict[str, int],
) -> None:
    """Localize the stock item set through Empire-specific table locations."""

    patch_empire_word_item_names(data, glyph_by_char)
    jp_builder.patch_item_names(
        data,
        glyph_by_char,
        pointer_table=EMPIRE_ITEM_NAME_POINTER_TABLE,
        pointer_min=0x0A1980,
        pointer_max=0x0A1B90,
        glyph_list_base=EMPIRE_ITEM_GLYPH_LIST_BASE,
        glyph_list_source_count=0x3F,
        glyph_list_refs=EMPIRE_ITEM_GLYPH_LIST_REFS,
        glyph_load_hook=EMPIRE_ITEM_NAME_GLYPH_LOAD_HOOK,
        glyph_load_target=EMPIRE_ITEM_NAME_GLYPH_LOAD_TARGET,
        popup_build_hook=EMPIRE_ITEM_NAME_POPUP_BUILD_HOOK,
        popup_return_target=EMPIRE_ITEM_NAME_POPUP_RETURN_TARGET,
        list_render_hooks=EMPIRE_ITEM_NAME_LIST_RENDER_HOOKS,
        discard_list_render_hook=EMPIRE_ITEM_DISCARD_LIST_RENDER_HOOK,
        token_reloc_base=EMPIRE_ITEM_NAME_TOKEN_RELOC_BASE,
        token_reloc_limit=EMPIRE_ITEM_NAME_TOKEN_RELOC_LIMIT,
    )
    jp_builder.patch_item_descriptions(
        data,
        glyph_by_char,
        pointer_table=EMPIRE_ITEM_DESCRIPTION_POINTER_TABLE,
        pointer_min=0x0A1E00,
        pointer_max=0x0A2C00,
        glyph_list_base=EMPIRE_ITEM_DESCRIPTION_GLYPH_LIST_BASE,
        glyph_list_source_count=120,
        glyph_list_ref=EMPIRE_ITEM_DESCRIPTION_GLYPH_LIST_REF,
        glyph_load_count_offset=(
            EMPIRE_ITEM_DESCRIPTION_GLYPH_LOAD_COUNT_OFFSET
        ),
    )
    jp_builder.patch_shop_title_glyph_loaders(
        data,
        glyph_by_char,
        notice_glyph_list=EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_LIST,
        notice_glyph_source=EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_SOURCE,
        notice_glyph_pointer=EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_POINTER,
        notice_glyph_pointer_source=(
            EMPIRE_ITEM_DISCARD_NOTICE_GLYPH_LIST
        ),
        notice_token_pointer=EMPIRE_ITEM_DISCARD_NOTICE_TOKEN_POINTER,
        notice_token_pointer_source=(
            EMPIRE_ITEM_DISCARD_NOTICE_TOKEN_STREAM
        ),
        notice_token_stream=EMPIRE_ITEM_DISCARD_NOTICE_TOKEN_STREAM,
        notice_source_tokens=EMPIRE_ITEM_DISCARD_NOTICE_SOURCE_TOKENS,
        confirm_glyph_list=EMPIRE_ITEM_DISCARD_CONFIRM_GLYPH_LIST,
        confirm_glyph_source=EMPIRE_ITEM_DISCARD_CONFIRM_GLYPH_SOURCE,
        confirm_token_stream=EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_STREAM,
        confirm_source_tokens=EMPIRE_ITEM_DISCARD_CONFIRM_SOURCE_TOKENS,
        confirm_token_pointer=EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_POINTER,
        confirm_token_pointer_source=(
            EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_STREAM
        ),
        confirm_token_reloc=EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_RELOC,
        confirm_token_reloc_limit=(
            EMPIRE_ITEM_DISCARD_CONFIRM_TOKEN_RELOC_LIMIT
        ),
        validate_confirm_source=True,
        possession_glyph_list=EMPIRE_SHOP_POSSESSION_GLYPH_LIST,
        inventory_full_token_stream=(
            EMPIRE_SHOP_INVENTORY_FULL_TOKEN_STREAM
        ),
        sell_glyph_list=EMPIRE_SHOP_SELL_GLYPH_LIST,
        selection_token_stream=(
            EMPIRE_SHOP_ITEM_SELECTION_TOKEN_STREAM
        ),
        sell_title_token_stream=EMPIRE_SHOP_SELL_TITLE_TOKEN_STREAM,
        sell_title_source_tokens=EMPIRE_SHOP_SELL_TITLE_SOURCE_TOKENS,
    )


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def expand_empire_rom(data: bytearray) -> None:
    """Expand the exact Empire source and relocate its shifted SRAM code."""

    validate_empire_source(bytes(data))
    if len(data) > EXPANDED_ROM_SIZE:
        raise ValueError(f"Empire ROM exceeds 4 MiB: 0x{len(data):X}")
    data.extend(b"\xFF" * (EXPANDED_ROM_SIZE - len(data)))
    put32(data, 0x01A4, EXPANDED_ROM_SIZE - 1)
    if be32(data, 0x01B4) != ORIGINAL_SRAM_START:
        raise ValueError("unexpected Empire SRAM start")
    if be32(data, 0x01B8) != ORIGINAL_SRAM_END:
        raise ValueError("unexpected Empire SRAM end")
    put32(data, 0x01B4, RELOCATED_SRAM_START)
    put32(data, 0x01B8, RELOCATED_SRAM_END)
    for offset, expected in EMPIRE_SRAM_LONG_PATCHES.items():
        actual = be32(data, offset)
        if actual != expected:
            raise ValueError(
                f"Empire SRAM operand at 0x{offset:06X} is "
                f"0x{actual:06X}, expected 0x{expected:06X}"
            )
        put32(data, offset, expected + SRAM_DELTA)


def patch_empire_font_base(data: bytearray) -> None:
    """Point both Empire 16x16 loaders at the Korean-compatible font bank."""

    for offset, expected in EMPIRE_FONT_BASE_PATCHES.items():
        actual = be32(data, offset)
        if actual != expected:
            raise ValueError(
                f"Empire font-base operand at 0x{offset:06X} is "
                f"0x{actual:06X}, expected 0x{expected:06X}"
            )
        put32(data, offset, JP_FONT_BASE)

    source_blank = EMPIRE_FONT_BASE + SPACE_GLYPH * GLYPH_BYTES
    target_blank = JP_FONT_BASE + SPACE_GLYPH * GLYPH_BYTES
    blank = bytes(data[source_blank : source_blank + GLYPH_BYTES])
    if len(blank) != GLYPH_BYTES or set(blank) - {0x00, 0xFF}:
        raise ValueError("Empire blank glyph template is malformed")
    data[target_blank : target_blank + GLYPH_BYTES] = blank


def encode_direct_text(text: str, glyph_by_char: dict[str, int]) -> list[int]:
    values: list[int] = []
    cursor = 0
    for match in CONTROL_RE.finditer(text):
        for char in text[cursor : match.start()]:
            if char == "\n":
                values.append(0xFFFE)
            elif char == " ":
                values.append(SPACE_GLYPH)
            elif char == "\f":
                values.append(0xFFFD)
            elif unicodedata.category(char).startswith("C"):
                continue
            else:
                values.append(glyph_by_char[char])
        values.extend((0xFFF7, int(match.group(1), 16)))
        cursor = match.end()
    for char in text[cursor:]:
        if char == "\n":
            values.append(0xFFFE)
        elif char == " ":
            values.append(SPACE_GLYPH)
        elif char == "\f":
            values.append(0xFFFD)
        elif unicodedata.category(char).startswith("C"):
            continue
        else:
            values.append(glyph_by_char[char])
    return values


def controls(tokens: list[int]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(tokens):
        if tokens[cursor] == 0xFFF7:
            if cursor + 1 >= len(tokens):
                raise ValueError("truncated FFF7 actor control")
            result.append((0xFFF7, tokens[cursor + 1]))
            cursor += 2
        else:
            cursor += 1
    return result


def encode_indirect_text(
    text: str,
    glyph_by_char: dict[str, int],
) -> tuple[list[int], list[int]]:
    glyphs = [SPACE_GLYPH]
    local_by_glyph = {SPACE_GLYPH: 0}
    tokens: list[int] = []

    def append_fragment(fragment: str) -> None:
        for char in fragment:
            if char == "\n":
                tokens.append(0xFFFE)
                continue
            if char == "\f":
                raise ValueError("unexpected form feed in Empire indirect text")
            if unicodedata.category(char).startswith("C"):
                continue
            glyph = SPACE_GLYPH if char == " " else glyph_by_char[char]
            local = local_by_glyph.get(glyph)
            if local is None:
                local = len(glyphs)
                local_by_glyph[glyph] = local
                glyphs.append(glyph)
            tokens.append(local)

    cursor = 0
    for match in CONTROL_RE.finditer(text):
        append_fragment(text[cursor : match.start()])
        tokens.extend((0xFFF7, int(match.group(1), 16)))
        cursor = match.end()
    append_fragment(text[cursor:])
    return glyphs, tokens


def relocate_indirect_text(
    data: bytearray,
    script: dict[str, object],
    glyph_by_char: dict[str, int],
) -> dict[str, object]:
    glyph_cursor = INDIRECT_GLYPH_RELOC_BASE
    token_cursor = INDIRECT_TOKEN_RELOC_BASE
    record_count = 0
    tables = (
        (
            "condition_records",
            CONDITION_POINTER_TABLE,
            CONDITION_GLYPH_POINTER_TABLE,
            CONDITION_COUNT,
        ),
        (
            "scenario_description_records",
            SCENARIO_POINTER_TABLE,
            SCENARIO_GLYPH_POINTER_TABLE,
            SCENARIO_COUNT,
        ),
    )
    for key, token_table, glyph_table, count in tables:
        rows = script.get(key)
        if not isinstance(rows, list) or len(rows) != count:
            raise ValueError(f"Empire {key} needs exactly {count} rows")
        by_id = {int(row["id"]): row for row in rows}
        if set(by_id) != set(range(count)):
            raise ValueError(f"Empire {key} IDs are incomplete")
        for index in range(count):
            row = by_id[index]
            expected_text = int(str(row["text_pointer"]), 16)
            expected_glyph = int(str(row["glyph_pointer"]), 16)
            if be32(data, token_table + index * 4) != expected_text:
                raise ValueError(f"Empire {key}[{index}] text pointer changed")
            if be32(data, glyph_table + index * 4) != expected_glyph:
                raise ValueError(f"Empire {key}[{index}] glyph pointer changed")

            source_tokens = [
                int(value, 16) for value in str(row["tokens"]).split()
            ]
            target_text = str(row["draft_korean"])
            glyphs, tokens = encode_indirect_text(
                target_text,
                glyph_by_char,
            )
            if controls(source_tokens[:-1]) != controls(tokens):
                raise ValueError(
                    f"Empire {key}[{index}] actor controls changed"
                )
            glyph_bytes = (len(glyphs) + 1) * 2
            token_bytes = (len(tokens) + 1) * 2
            if glyph_cursor + glyph_bytes > INDIRECT_GLYPH_RELOC_LIMIT:
                raise ValueError("Empire indirect glyph bank overflowed")
            if token_cursor + token_bytes > INDIRECT_TOKEN_RELOC_LIMIT:
                raise ValueError("Empire indirect token bank overflowed")
            if any(
                value != 0xFF
                for value in data[glyph_cursor : glyph_cursor + glyph_bytes]
            ):
                raise ValueError("Empire indirect glyph bank is occupied")
            if any(
                value != 0xFF
                for value in data[token_cursor : token_cursor + token_bytes]
            ):
                raise ValueError("Empire indirect token bank is occupied")

            put32(data, glyph_table + index * 4, glyph_cursor)
            for glyph in glyphs:
                put16(data, glyph_cursor, glyph)
                glyph_cursor += 2
            put16(data, glyph_cursor, 0xFFFF)
            glyph_cursor += 2

            put32(data, token_table + index * 4, token_cursor)
            for token in tokens:
                put16(data, token_cursor, token)
                token_cursor += 2
            put16(data, token_cursor, 0xFFFF)
            token_cursor += 2
            record_count += 1

    return {
        "records": record_count,
        "glyph_start": f"0x{INDIRECT_GLYPH_RELOC_BASE:06X}",
        "glyph_end": f"0x{glyph_cursor:06X}",
        "token_start": f"0x{INDIRECT_TOKEN_RELOC_BASE:06X}",
        "token_end": f"0x{token_cursor:06X}",
    }


def event_rows(script: dict[str, object]) -> dict[int, dict[str, object]]:
    result: dict[int, dict[str, object]] = {}
    scenarios = script.get("event_scenarios")
    if not isinstance(scenarios, dict):
        raise ValueError("Empire script has no event_scenarios object")
    for rows in scenarios.values():
        if not isinstance(rows, list):
            raise ValueError("Empire event scenario is not a list")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Empire event row is not an object")
            address = int(str(row["address"]), 16)
            if address in result:
                raise ValueError(f"duplicate Empire physical page 0x{address:06X}")
            result[address] = row
    return result


def relocate_event_dialogue(
    data: bytearray,
    source: bytes,
    script: dict[str, object],
    glyph_by_char: dict[str, int],
) -> dict[str, object]:
    """Relocate every physical event page and retarget all source refs."""

    inventory = event_inventory(source, source)
    translated = event_rows(script)
    cursor = EVENT_RELOC_BASE
    physical_count = 0
    logical_count = 0
    referenced_addresses: set[int] = set()

    for scenario in inventory["scenarios"]:
        for page in scenario["pages"]:
            if page.get("classification", "text") != "text":
                continue
            physical_pages = page["physical_pages"]
            chain_start = cursor
            for physical in physical_pages:
                address = int(str(physical["address"]), 16)
                referenced_addresses.add(address)
                row = translated.get(address)
                if row is None:
                    raise ValueError(
                        f"missing Korean Empire page for 0x{address:06X}"
                    )
                original_tokens = [
                    int(value, 16)
                    for value in str(physical["tokens"]).split()
                ]
                terminator = original_tokens[-1]
                if terminator not in (0xFFFD, 0xFFFF):
                    raise ValueError(
                        f"unexpected page terminator 0x{terminator:04X} "
                        f"at 0x{address:06X}"
                    )
                target_tokens = encode_direct_text(
                    str(row["draft_korean"]), glyph_by_char
                )
                if controls(original_tokens[:-1]) != controls(target_tokens):
                    raise ValueError(
                        f"actor controls changed at Empire page 0x{address:06X}"
                    )
                target_tokens.append(terminator)
                byte_length = len(target_tokens) * 2
                if cursor + byte_length > EVENT_RELOC_LIMIT:
                    raise ValueError("relocated Empire event bank overflowed")
                if any(
                    value != 0xFF
                    for value in data[cursor : cursor + byte_length]
                ):
                    raise ValueError(
                        f"Empire event bank at 0x{cursor:06X} is occupied"
                    )
                for value in target_tokens:
                    put16(data, cursor, value)
                    cursor += 2
                physical_count += 1

            for source_ref in page["source_refs"]:
                pointer_offset = int(str(source_ref), 16)
                expected = int(str(page["address"]), 16)
                actual = be32(data, pointer_offset)
                if actual != expected:
                    raise ValueError(
                        f"Empire event ref 0x{pointer_offset:06X} points to "
                        f"0x{actual:06X}, expected 0x{expected:06X}"
                    )
                put32(data, pointer_offset, chain_start)
            logical_count += 1

    unreferenced = set(translated) - referenced_addresses
    if unreferenced:
        first = min(unreferenced)
        raise ValueError(
            f"Korean Empire script contains unreferenced page 0x{first:06X}"
        )
    return {
        "logical_pages": logical_count,
        "physical_pages": physical_count,
        "start": f"0x{EVENT_RELOC_BASE:06X}",
        "end": f"0x{cursor:06X}",
        "bytes": cursor - EVENT_RELOC_BASE,
    }


def script_texts(script: dict[str, object]) -> list[str]:
    texts: list[str] = []
    for key in ("condition_records", "scenario_description_records"):
        rows = script.get(key, [])
        if isinstance(rows, list):
            texts.extend(str(row["draft_korean"]) for row in rows)
    scenarios = script.get("event_scenarios", {})
    if isinstance(scenarios, dict):
        for rows in scenarios.values():
            texts.extend(str(row["draft_korean"]) for row in rows)
    return texts


def collect_empire_glyph_chars(script: dict[str, object]) -> list[str]:
    """Keep reviewed-script glyph IDs stable against the frozen draft seed."""

    seed = load_script(DEFAULT_DRAFT_SCRIPT, allow_draft=True)
    return collect_chars(
        *script_texts(seed),
        *script_texts(script),
        *jp_builder.START_MENU_TEXTS,
        *jp_builder.START_SUBMENU_TEXTS,
        *jp_builder.CONTROL_SETTINGS_TEXTS,
        *jp_builder.TITLE_LOAD_TEXTS,
        *jp_builder.TITLE_MAIN_MENU_TEXTS,
        *(text for _, text in jp_builder.DIRECT_WORD_SEQUENCE_PATCHES.values()),
        jp_builder.CLASS_CHANGE_GLYPH_TEXT,
        "방어자적군행완료유닛입니다",
        "이동순변경자",
        jp_builder.ARRANGE_WARNING_GLYPH_TEXT,
        *(text for _, text in EMPIRE_OPENING_TEXT_LIST_PATCHES.values()),
        *jp_builder.ITEM_NAME_PATCHES,
        *jp_builder.ITEM_DESCRIPTION_PATCHES,
        jp_builder.INLINE_DISCARD_PROMPT_TEXT,
        jp_builder.ITEM_POSSESSION_TITLE_TEXT,
        jp_builder.ITEM_DISCARD_CONFIRM_SUFFIX,
        *jp_builder.ITEM_DISCARD_CONFIRM_CHOICES,
        *jp_builder.ITEM_DISCARD_NOTICE_LINES,
        jp_builder.SHOP_ITEM_SELECTION_TEXT,
        jp_builder.SHOP_INVENTORY_FULL_MESSAGE_TEXT,
        jp_builder.SHOP_PURCHASE_MESSAGE_TEXT,
        jp_builder.SHOP_SELL_MESSAGE_TEXT,
        *(text for _, text in jp_builder.DIRECT_FIXED_ROUTE_TITLE_PATCHES.values()),
        *(text for _, text in jp_builder.DIRECT_FIXED_SCENARIO_HEADER_PATCHES.values()),
    )


def validate_localization_only_delta(
    source: bytes,
    data: bytes | bytearray,
    *,
    additional_allowed_offsets: set[int] | None = None,
) -> int:
    """Reject any accidental edit to Empire gameplay/balance-owned bytes."""

    allowed: set[int] = set()

    def allow(offset: int, size: int) -> None:
        allowed.update(range(offset, offset + size))

    allow(0x018E, 2)  # Mega Drive checksum
    allow(0x01A4, 4)  # expanded ROM end
    allow(0x01B4, 8)  # relocated SRAM window
    for offset in EMPIRE_SRAM_LONG_PATCHES:
        allow(offset, 4)
    for offset in EMPIRE_FONT_BASE_PATCHES:
        allow(offset, 4)
    allow(JP_FONT_BASE + SPACE_GLYPH * GLYPH_BYTES, GLYPH_BYTES)
    for table, count in (
        (CONDITION_POINTER_TABLE, CONDITION_COUNT),
        (CONDITION_GLYPH_POINTER_TABLE, CONDITION_COUNT),
        (SCENARIO_POINTER_TABLE, SCENARIO_COUNT),
        (SCENARIO_GLYPH_POINTER_TABLE, SCENARIO_COUNT),
    ):
        allow(table, count * 4)
    inventory = event_inventory(source, source)
    for scenario in inventory["scenarios"]:
        for page in scenario["pages"]:
            for source_ref in page["source_refs"]:
                allow(int(str(source_ref), 16), 4)
    if additional_allowed_offsets:
        allowed.update(additional_allowed_offsets)

    changed = [
        offset
        for offset, (before, after) in enumerate(zip(source, data))
        if before != after
    ]
    unexpected = [offset for offset in changed if offset not in allowed]
    if unexpected:
        first = unexpected[0]
        raise ValueError(
            f"Empire localization changed gameplay-owned byte 0x{first:06X}"
        )
    return len(changed)


def load_script(path: Path, allow_draft: bool) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("source_sha256") != EMPIRE_SOURCE_SHA256:
        raise ValueError("Empire script source hash does not match the ROM")
    status = str(payload.get("status", ""))
    if status != "human reviewed; release ready" and not allow_draft:
        raise ValueError(
            "Empire script is not fully human reviewed and release ready; "
            "pass --allow-draft only for a non-release diagnostic build"
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_EMPIRE_ROM)
    parser.add_argument("--script", type=Path, default=DEFAULT_REVIEWED_SCRIPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument(
        "--events-only",
        action="store_true",
        help="diagnostic build: relocate event dialogue before condition/UI work",
    )
    parser.add_argument(
        "--common-ui-diagnostic",
        action="store_true",
        help=(
            "diagnostic build: also install the fingerprinted common Korean "
            "UI subset whose Empire sources have been verified"
        ),
    )
    parser.add_argument(
        "--common-ui-isolation",
        choices=(
            "full",
            "byte-only",
            "direct-only",
            "no-opening",
            "no-title-logo",
            "no-title-screens",
            "byte-no-title-credit",
        ),
        default="full",
        help="non-release binary-isolation variant for common-UI runtime faults",
    )
    args = parser.parse_args()

    source = args.rom.read_bytes()
    validate_empire_source(source)
    # ``--allow-draft`` relaxes the release-status gate; it must not silently
    # swap the requested reviewed-in-progress script back to the frozen raw
    # machine draft.  That made diagnostic ROMs ignore newly reviewed lines.
    script_path = args.script
    script = load_script(script_path, args.allow_draft)
    data = bytearray(source)
    expand_empire_rom(data)
    patch_empire_font_base(data)
    chars = collect_empire_glyph_chars(script)
    glyph_by_char = install_custom_glyphs(data, chars)
    manifest = relocate_event_dialogue(data, source, script, glyph_by_char)
    manifest["indirect_text"] = relocate_indirect_text(
        data, script, glyph_by_char
    )

    common_ui_offsets: set[int] = set()
    if args.common_ui_diagnostic:
        if args.common_ui_isolation == "full":
            _, common_ui_offsets = patch_empire_common_ui(
                data,
                glyph_by_char,
                source_size=len(source),
            )
        else:
            common_ui_offsets = patch_empire_common_ui_isolation(
                data,
                glyph_by_char,
                source_size=len(source),
                variant=args.common_ui_isolation,
            )
        manifest["common_ui"] = {
            "source_region_offsets": len(common_ui_offsets),
            "status": (
                "fingerprinted reusable subset"
                if args.common_ui_isolation == "full"
                else f"unfingerprinted isolation: {args.common_ui_isolation}"
            ),
        }

    if not args.events_only and not args.common_ui_diagnostic:
        raise ValueError(
            "Empire condition/description/common-UI relocation is not complete; "
            "release build intentionally refused"
        )
    update_checksum(data)
    manifest["source_region_changed_bytes"] = validate_localization_only_delta(
        source,
        data,
        additional_allowed_offsets=common_ui_offsets,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    manifest.update(
        {
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "output_sha256": hashlib.sha256(data).hexdigest(),
            "script": str(script_path),
            "status": (
                "diagnostic common-UI draft; not for release"
                if args.common_ui_diagnostic
                else "diagnostic events-only draft; not for release"
            ),
        }
    )
    manifest_path = args.out.with_suffix(args.out.suffix + ".json")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
