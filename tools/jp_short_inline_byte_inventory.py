#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.jp_inline_byte_string_inventory import SCAN_END, scan_runs


EXECUTABLE_END = 0x040000
ITEM_NAME_GRAPHICS_BANK_START = 0x060000
ITEM_NAME_GRAPHICS_BANK_END = 0x080000
SYSTEM_GRAPHICS_ENDING_BANK_START = 0x080000
SYSTEM_GRAPHICS_ENDING_BANK_END = 0x090000
ENDING_SCENARIO_BANK_START = 0x090000
ENDING_SCENARIO_BANK_END = 0x0A0000
TEXT_UI_BANK_START = 0x0A0000
TEXT_UI_BANK_END = 0x0B0000
MAX_LOW_SIGNAL = 2
WORD_STREAM_CONTROLS = {
    0xFFF3,
    0xFFF7,
    0xFFF8,
    0xFFFA,
    0xFFFD,
    0xFFFE,
    0xFFFF,
}
SCENARIO_LEVEL_PREFIX = 0x09B2E7
SCENARIO_LEVEL_PREFIX_HOOK = 0x025CDC
SCENARIO_LEVEL_PREFIX_HOOK_BYTES = bytes.fromhex("41 F9 00 09 B2 E7")
SCENARIO_LEVEL_PREFIX_EVIDENCE = "captures/run/1391_s19_canonical_brief_06.png"

HALFWIDTH_ALLOWED = {0x20, *range(0xA1, 0xE0)}
ASCII_ALLOWED = {
    *range(ord("0"), ord("9") + 1),
    *range(ord("A"), ord("Z") + 1),
    0x20,
    ord("."),
    ord("+"),
    ord("-"),
    ord(":"),
}

PACKED_GAME_GRAPHICS_REVIEW_ADDRESSES = {
    0x060D35,
    0x060D39,
    0x060D41,
    0x060D50,
    0x061212,
    0x06121F,
    0x06146D,
}

NAME_POINTER_TABLE_BOUNDARY_REVIEW_ADDRESS = 0x061ABB

PACKED_TILE_SPRITE_GRAPHICS_REVIEW_ADDRESSES = {
    0x06EFF1,
    0x06EFFB,
    0x06F039,
    0x06F043,
    0x06F8F1,
    0x06F8FB,
    0x06F939,
    0x06F943,
    0x0701F1,
    0x0701FB,
    0x070239,
    0x070243,
    0x070AF1,
    0x070AFB,
    0x070B39,
    0x070B43,
    0x070C2A,
    0x0713F1,
    0x0713FB,
    0x071439,
    0x071443,
    0x071CF1,
    0x071CFB,
    0x071D39,
    0x071D43,
    0x0725F1,
    0x0725FB,
    0x072639,
    0x072643,
    0x072EF1,
    0x072EFB,
    0x072F39,
    0x072F43,
    0x0737F1,
    0x0737FB,
    0x073839,
    0x073843,
    0x0740F1,
    0x0740FB,
    0x074139,
    0x074143,
    0x0749F1,
    0x0749FB,
    0x074A39,
    0x074A43,
    0x07542A,
    0x0764F1,
    0x0764FB,
    0x076539,
    0x076543,
    0x076DF1,
    0x076DFB,
    0x076E39,
    0x076E43,
    0x0776F1,
    0x0776FB,
    0x077739,
    0x077743,
    0x0788F1,
    0x0788FB,
    0x078939,
    0x078943,
    0x07A3F1,
    0x07A3FB,
    0x07A439,
    0x07A443,
    0x07B72A,
    0x07BEF1,
    0x07BEFB,
    0x07BF39,
    0x07BF43,
    0x07C7F1,
    0x07C7FB,
    0x07C839,
    0x07C843,
}

ITEM_NAME_GRAPHICS_REVIEWS = {
    **{
        address: (
            "packed_game_graphics_false_positive",
            "packed 4bpp item/system tile bytes",
        )
        for address in PACKED_GAME_GRAPHICS_REVIEW_ADDRESSES
    },
    NAME_POINTER_TABLE_BOUNDARY_REVIEW_ADDRESS: (
        "name_pointer_table_boundary_false_positive",
        "low byte of final name pointer 0x00061ABC plus space padding",
    ),
    **{
        address: (
            "packed_tile_sprite_graphics_false_positive",
            "repeating packed 4bpp tile/sprite bytes",
        )
        for address in PACKED_TILE_SPRITE_GRAPHICS_REVIEW_ADDRESSES
    },
}

# The aligned four-byte scanner deliberately over-approximates. These three
# apparent references are pinned with their decoded context so they cannot be
# mistaken for live pointers merely because their four bytes equal a candidate
# address.
ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS = {
    (0x06121F, 0x0A4440): (
        "coincidental_data_window",
        "numeric/graphics index row `00 06 12 1F 2E 3C`",
    ),
    (0x070C2A, 0x01F0A6): (
        "cross_instruction_window",
        "`MOVE.W #$0007,D7` immediate followed by `CMPI.B` opcode `0C2A`",
    ),
    (0x070C2A, 0x01F1A8): (
        "cross_instruction_window",
        "`MOVE.W #$0007,D7` immediate followed by `CMPI.B` opcode `0C2A`",
    ),
}

# Each address was reviewed as an address within the containing 16-bit
# word/layout record. Pinning the exact set makes a new text/UI-bank candidate
# fail closed instead of inheriting a broad false-positive label.
WORD_STREAM_REVIEWS = {
    0x0A02A9: "screen-local 16-bit glyph stream",
    0x0A02C3: "screen-local 16-bit glyph stream",
    0x0A0813: "screen-local 16-bit glyph stream",
    0x0A0B1F: "screen-local 16-bit glyph stream",
    0x0A152B: "item/shop 16-bit glyph stream",
    0x0A16AD: "item/shop 16-bit glyph stream",
    0x0A16D1: "item/shop 16-bit glyph stream",
    0x0A1713: "item/shop 16-bit glyph stream",
    0x0A3161: "title START/LOAD 16-bit glyph stream",
    0x0A316B: "title START/LOAD 16-bit glyph stream",
    0x0A3447: "credits 16-bit glyph stream",
    0x0A34E1: "credits 16-bit glyph stream",
    0x0A3509: "credits 16-bit glyph stream",
    0x0A3513: "credits 16-bit glyph stream",
    0x0A353D: "credits 16-bit glyph stream",
    0x0A356D: "credits 16-bit glyph stream",
    0x0A35C9: "credits 16-bit glyph stream",
    0x0A3601: "credits 16-bit glyph stream",
    0x0A3639: "credits 16-bit glyph stream",
    0x0A368F: "credits 16-bit glyph stream",
    0x0A369B: "credits 16-bit glyph stream",
    0x0A3703: "credits 16-bit glyph stream",
    0x0A3733: "credits 16-bit glyph stream",
    0x0A3741: "credits 16-bit glyph stream",
    0x0A37B3: "declared scenario/total/turn UI glyph stream",
    0x0A37E3: "name-entry prompt glyph stream",
    0x0A3C99: "name-entry character glyph list",
    0x0A6F27: "opening text 16-bit glyph stream",
}

STRUCTURED_LAYOUT_REVIEWS = {
    0x0A1427: "item/shop structured word record",
    0x0A1437: "item/shop structured word record",
    0x0A143B: "item/shop structured word record",
    0x0A14A5: "item/shop structured word record",
    0x0A14A9: "item/shop structured word record",
    0x0A3B08: "name-entry byte/layout resource",
    0x0A46F4: "graphics/layout record immediately before referenced 0x0A46F6",
    0x0A4A36: "layout record terminator immediately before referenced 0x0A4A38",
    0x0A4F39: "layout record terminator immediately before referenced 0x0A4F3C",
    0x0A4FB3: "layout record terminator immediately before referenced 0x0A4FB6",
}

TEXT_UI_REVIEWS = {
    **{
        address: ("word_stream_byte_false_positive", owner)
        for address, owner in WORD_STREAM_REVIEWS.items()
    },
    **{
        address: ("structured_layout_false_positive", owner)
        for address, owner in STRUCTURED_LAYOUT_REVIEWS.items()
    },
}

ENDING_SCENARIO_STRUCTURED_REVIEWS = {
    0x096C75: "ending graphics/numeric record",
    0x096C8F: "ending graphics/numeric record",
    0x096CA3: "ending graphics/numeric record",
    0x096CA5: "ending graphics/numeric record",
    0x096CA7: "ending graphics/numeric record",
    0x096D77: "ending signed coordinate/layout table",
    0x096D7B: "ending signed coordinate/layout table",
    0x096D7F: "ending signed coordinate/layout table",
    0x096DD1: "ending signed coordinate/layout table",
    0x096DD5: "ending signed coordinate/layout table",
    0x096DD9: "ending signed coordinate/layout table",
    0x096DDD: "ending signed coordinate/layout table",
    0x096DE3: "ending signed coordinate/layout table",
    0x096DE7: "ending signed coordinate/layout table",
    0x096DEB: "ending signed coordinate/layout table",
    0x096DFF: "ending signed coordinate/layout table",
    0x09B0C6: "system-local byte lookup/layout record",
    0x09B0CE: "system-local byte lookup/layout record",
    0x09B0D2: "system-local byte lookup/layout record",
    0x09B0D6: "system-local byte lookup/layout record",
    0x09CFF7: "scenario token/layout word",
}

PACKED_TILE_RESOURCE_REVIEW_ADDRESSES = {
    0x083F76,
    0x084401,
    0x0845E6,
    0x08546B,
    0x08554C,
    0x0859F4,
    0x0860B4,
}

STRUCTURED_GRAPHICS_REVIEW_ADDRESSES = {
    0x0861AD,
    0x0861BB,
    0x0861CD,
    0x08664D,
    0x086689,
    0x086717,
    0x086771,
    0x08679B,
    0x08681B,
    0x08687B,
    0x08689F,
    0x0869A7,
    0x086A1D,
    0x086A9F,
    0x086B3F,
    0x086B61,
    0x086B6F,
    0x086B9F,
    0x086BA9,
    0x086C99,
    0x086CB7,
    0x086CC7,
    0x086CE9,
    0x086CF7,
    0x086D27,
    0x086D45,
    0x086D55,
    0x086D67,
    0x086F79,
    0x086F9B,
    0x086FB3,
    0x086FBD,
    0x086FD5,
    0x08709B,
    0x0870BD,
    0x0870D7,
    0x087185,
    0x0871B7,
    0x0871E9,
    0x08721B,
    0x08724D,
    0x08727F,
    0x0872B1,
    0x0872E3,
    0x0873B1,
    0x0873DB,
    0x087405,
    0x08742F,
    0x087459,
    0x087483,
    0x0874AD,
    0x0874D7,
    0x08767B,
}

ENDING_SELECTOR_REVIEW_ADDRESSES = {
    0x08913E,
    0x089286,
    0x0892F4,
    0x0893D1,
    0x089545,
    0x089552,
    0x089561,
}

SYSTEM_GRAPHICS_ENDING_REVIEWS = {
    **{
        address: (
            "packed_tile_resource_false_positive",
            "packed tilemap/render-script bytes",
        )
        for address in PACKED_TILE_RESOURCE_REVIEW_ADDRESSES
    },
    **{
        address: (
            "structured_graphics_false_positive",
            "sprite frame, coordinate, or animation record",
        )
        for address in STRUCTURED_GRAPHICS_REVIEW_ADDRESSES
    },
    **{
        address: (
            "ending_selector_false_positive",
            "character-epilogue pointer or selector record",
        )
        for address in ENDING_SELECTOR_REVIEW_ADDRESSES
    },
}


def region_name(address: int) -> str:
    if address < 0x040000:
        return "executable_or_numeric"
    if address < 0x050000:
        return "font_bitmap"
    if address < 0x060000:
        return "other_50000"
    if address < 0x061000:
        return "structured_game_data"
    if address < 0x080000:
        return "other_61000_7ffff"
    if address < 0x090000:
        return "glyph_tile"
    if address < 0x0A0000:
        return "other_90000_9ffff"
    if address < 0x0B0000:
        return "text_ui_bank"
    return "compressed"


def low_signal_runs(data: bytes) -> list[dict[str, object]]:
    rows = []
    specs = (
        (
            "halfwidth",
            HALFWIDTH_ALLOWED,
            lambda value: value != 0x20,
            32,
            "cp932",
        ),
        (
            "ascii",
            ASCII_ALLOWED,
            lambda value: ord("A") <= value <= ord("Z"),
            40,
            "ascii",
        ),
    )
    for kind, allowed, signal, maximum_length, encoding in specs:
        for start, end, raw in scan_runs(
            data,
            allowed,
            minimum_signal=1,
            signal=signal,
            maximum_length=maximum_length,
        ):
            signal_count = sum(bool(signal(value)) for value in raw)
            if signal_count > MAX_LOW_SIGNAL:
                continue
            rows.append(
                {
                    "kind": kind,
                    "start_int": start,
                    "end_int": end,
                    "signal_count": signal_count,
                    "raw": raw,
                    "text": raw.decode(encoding),
                    "region": region_name(start),
                }
            )
    rows.sort(key=lambda row: (int(row["start_int"]), str(row["kind"])))
    return rows


def aligned_absolute_references(
    data: bytes, targets: set[int]
) -> dict[int, list[int]]:
    references: dict[int, list[int]] = defaultdict(list)
    end = min(len(data), SCAN_END)
    for offset in range(0, end - 3, 2):
        target = int.from_bytes(data[offset : offset + 4], "big")
        if target in targets:
            references[target].append(offset)
    return dict(references)


def pc_relative_lea_pea_references(
    data: bytes, targets: set[int]
) -> dict[int, list[dict[str, object]]]:
    references: dict[int, list[dict[str, object]]] = defaultdict(list)
    end = min(len(data), EXECUTABLE_END)
    for offset in range(0, end - 3, 2):
        opcode = int.from_bytes(data[offset : offset + 2], "big")
        if opcode == 0x487A:
            instruction = "PEA"
        elif opcode & 0xF1FF == 0x41FA:
            instruction = "LEA"
        else:
            continue
        displacement = int.from_bytes(
            data[offset + 2 : offset + 4], "big", signed=True
        )
        target = offset + 2 + displacement
        if target in targets:
            references[target].append(
                {
                    "instruction": instruction,
                    "address": offset,
                    "displacement": displacement,
                }
            )
    return dict(references)


def word_context(data: bytes, start: int, end: int) -> tuple[int, str]:
    context_start = max(0, (start - 16) & ~1)
    context_end = min(len(data), (end + 17) & ~1)
    words = [
        int.from_bytes(data[offset : offset + 2], "big")
        for offset in range(context_start, context_end, 2)
    ]
    return context_start, " ".join(f"{word:04X}" for word in words)


def is_word_stream_byte_lane(data: bytes, start: int, end: int) -> bool:
    if start % 2 != 1 or (end - 1) % 2 != 0:
        return False
    containing_word = int.from_bytes(data[start - 1 : start + 1], "big")
    following_control = int.from_bytes(data[end - 1 : end + 1], "big")
    return containing_word <= 0x07FF and following_control in WORD_STREAM_CONTROLS


def ending_scenario_owner(address: int) -> str:
    if address < 0x0954E2:
        return "epilogue 16-bit text record"
    if address < 0x096D00:
        return "ending 16-bit text or graphics record"
    if address < 0x096F00:
        return "ending structured layout data"
    if address < 0x098000:
        return "shared UI/name/layout data"
    if address < 0x09A000:
        return "condition/scenario-description resource"
    if address < 0x09B000:
        return "battle-local UI resource"
    if address < 0x09B2FC:
        return "system-local UI resource"
    return "scenario-description glyph/token resource"


def system_graphics_word_owner(address: int) -> str:
    if address < 0x082BFE:
        return "shared system-message 16-bit glyph stream"
    if address < 0x082D5A:
        return "magic-name 16-bit glyph stream"
    return "mercenary-name 16-bit glyph stream"


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    candidates = low_signal_runs(japanese)
    item_name_graphics = [
        row
        for row in candidates
        if ITEM_NAME_GRAPHICS_BANK_START
        <= int(row["start_int"])
        < ITEM_NAME_GRAPHICS_BANK_END
    ]
    system_graphics_ending = [
        row
        for row in candidates
        if SYSTEM_GRAPHICS_ENDING_BANK_START
        <= int(row["start_int"])
        < SYSTEM_GRAPHICS_ENDING_BANK_END
    ]
    ending_scenario = [
        row
        for row in candidates
        if ENDING_SCENARIO_BANK_START
        <= int(row["start_int"])
        < ENDING_SCENARIO_BANK_END
    ]
    text_ui = [
        row
        for row in candidates
        if TEXT_UI_BANK_START <= int(row["start_int"]) < TEXT_UI_BANK_END
    ]

    item_name_graphics_addresses = {
        int(row["start_int"]) for row in item_name_graphics
    }
    item_name_graphics_absolute = aligned_absolute_references(
        japanese, item_name_graphics_addresses
    )
    item_name_graphics_pc_relative = pc_relative_lea_pea_references(
        japanese, item_name_graphics_addresses
    )
    item_name_graphics_rows = []
    item_name_graphics_reference_reviews = []
    for row in item_name_graphics:
        start = int(row["start_int"])
        end = int(row["end_int"])
        category, owner = ITEM_NAME_GRAPHICS_REVIEWS.get(
            start, ("unclassified", "requires manual ownership review")
        )
        context_start, context = word_context(japanese, start, end)
        item_name_graphics_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in item_name_graphics_absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in item_name_graphics_pc_relative.get(
                        start, []
                    )
                ],
            }
        )
        for reference in item_name_graphics_absolute.get(start, []):
            review = ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS.get(
                (start, reference)
            )
            if review is None:
                classification = "unclassified"
                evidence = "requires instruction/data-boundary review"
            else:
                classification, evidence = review
            item_name_graphics_reference_reviews.append(
                {
                    "target": f"0x{start:06X}",
                    "address": f"0x{reference:06X}",
                    "classification": classification,
                    "evidence": evidence,
                }
            )

    system_graphics_ending_addresses = {
        int(row["start_int"]) for row in system_graphics_ending
    }
    system_graphics_ending_absolute = aligned_absolute_references(
        japanese, system_graphics_ending_addresses
    )
    system_graphics_ending_pc_relative = pc_relative_lea_pea_references(
        japanese, system_graphics_ending_addresses
    )
    system_graphics_ending_rows = []
    for row in system_graphics_ending:
        start = int(row["start_int"])
        end = int(row["end_int"])
        if is_word_stream_byte_lane(japanese, start, end):
            category = "word_stream_byte_false_positive"
            owner = system_graphics_word_owner(start)
        elif start in SYSTEM_GRAPHICS_ENDING_REVIEWS:
            category, owner = SYSTEM_GRAPHICS_ENDING_REVIEWS[start]
        else:
            category = "unclassified"
            owner = "requires manual ownership review"
        context_start, context = word_context(japanese, start, end)
        system_graphics_ending_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in system_graphics_ending_absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in system_graphics_ending_pc_relative.get(
                        start, []
                    )
                ],
            }
        )

    addresses = {int(row["start_int"]) for row in text_ui}
    reviewed_addresses = set(TEXT_UI_REVIEWS)
    missing_reviews = sorted(addresses - reviewed_addresses)
    stale_reviews = sorted(reviewed_addresses - addresses)

    absolute = aligned_absolute_references(japanese, addresses)
    pc_relative = pc_relative_lea_pea_references(japanese, addresses)
    detailed_rows = []
    for row in text_ui:
        start = int(row["start_int"])
        end = int(row["end_int"])
        category, owner = TEXT_UI_REVIEWS.get(
            start, ("unclassified", "requires manual ownership review")
        )
        context_start, context = word_context(japanese, start, end)
        detailed_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}" for offset in absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in pc_relative.get(start, [])
                ],
            }
        )

    ending_scenario_addresses = {
        int(row["start_int"]) for row in ending_scenario
    }
    ending_scenario_absolute = aligned_absolute_references(
        japanese, ending_scenario_addresses
    )
    ending_scenario_pc_relative = pc_relative_lea_pea_references(
        japanese, ending_scenario_addresses
    )
    ending_scenario_rows = []
    for row in ending_scenario:
        start = int(row["start_int"])
        end = int(row["end_int"])
        if start == SCENARIO_LEVEL_PREFIX:
            category = "retained_compact_english_ui"
            owner = "scenario briefing unit-level prefix"
        elif is_word_stream_byte_lane(japanese, start, end):
            category = "word_stream_byte_false_positive"
            owner = ending_scenario_owner(start)
        elif start in ENDING_SCENARIO_STRUCTURED_REVIEWS:
            category = "structured_layout_false_positive"
            owner = ENDING_SCENARIO_STRUCTURED_REVIEWS[start]
        else:
            category = "unclassified"
            owner = "requires manual ownership review"
        context_start, context = word_context(japanese, start, end)
        ending_scenario_rows.append(
            {
                "kind": row["kind"],
                "address": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "signal_count": row["signal_count"],
                "original_text": row["text"],
                "raw_hex": bytes(row["raw"]).hex(" ").upper(),
                "category": category,
                "owner": owner,
                "containing_word_address": f"0x{start & ~1:06X}",
                "containing_word": (
                    f"0x{int.from_bytes(japanese[start & ~1 : (start & ~1) + 2], 'big'):04X}"
                ),
                "context_start": f"0x{context_start:06X}",
                "context_words": context,
                "aligned_absolute_32_references": [
                    f"0x{offset:06X}"
                    for offset in ending_scenario_absolute.get(start, [])
                ],
                "pc_relative_lea_pea_references": [
                    {
                        "instruction": reference["instruction"],
                        "address": f"0x{int(reference['address']):06X}",
                        "displacement": reference["displacement"],
                    }
                    for reference in ending_scenario_pc_relative.get(start, [])
                ],
            }
        )

    kind_counts = Counter(str(row["kind"]) for row in candidates)
    region_counts = {
        kind: dict(
            sorted(
                Counter(
                    str(row["region"])
                    for row in candidates
                    if row["kind"] == kind
                ).items()
            )
        )
        for kind in ("halfwidth", "ascii")
    }
    category_counts = Counter(str(row["category"]) for row in detailed_rows)
    item_name_graphics_category_counts = Counter(
        str(row["category"]) for row in item_name_graphics_rows
    )
    ending_scenario_category_counts = Counter(
        str(row["category"]) for row in ending_scenario_rows
    )
    system_graphics_ending_category_counts = Counter(
        str(row["category"]) for row in system_graphics_ending_rows
    )
    system_graphics_ending_reviewed_addresses = (
        set(SYSTEM_GRAPHICS_ENDING_REVIEWS)
        | {
            int(row["address"], 16)
            for row in system_graphics_ending_rows
            if row["category"] == "word_stream_byte_false_positive"
        }
    )
    item_name_graphics_reference_pairs = {
        (target, reference)
        for target, references in item_name_graphics_absolute.items()
        for reference in references
    }
    ending_scenario_reviewed_addresses = (
        set(ENDING_SCENARIO_STRUCTURED_REVIEWS)
        | {SCENARIO_LEVEL_PREFIX}
        | {
            int(row["address"], 16)
            for row in ending_scenario_rows
            if row["category"] == "word_stream_byte_false_positive"
        }
    )
    return {
        "warning": (
            "This scan inventories maximal FF-terminated half-width/uppercase-ASCII "
            "runs with only one or two signal bytes. Most are binary coincidences. "
            "The 0x060000..0x0AFFFF item/name/graphics/system/ending/scenario/"
            "text/UI-bank "
            "candidates are classified here. Exact aligned 32-bit and LEA/PEA "
            "PC-relative references do not exclude base-relative, indexed, or "
            "dynamic access."
        ),
        "source_sha256": hashlib.sha256(japanese).hexdigest(),
        "scan_end": f"0x{SCAN_END:06X}",
        "candidate_count": len(candidates),
        "kind_counts": dict(sorted(kind_counts.items())),
        "region_counts": region_counts,
        "item_name_graphics_bank": {
            "range": "0x060000..0x080000",
            "candidate_count": len(item_name_graphics_rows),
            "category_counts": dict(
                sorted(item_name_graphics_category_counts.items())
            ),
            "unclassified_count": item_name_graphics_category_counts.get(
                "unclassified", 0
            ),
            "missing_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    item_name_graphics_addresses
                    - set(ITEM_NAME_GRAPHICS_REVIEWS)
                )
            ],
            "stale_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    set(ITEM_NAME_GRAPHICS_REVIEWS)
                    - item_name_graphics_addresses
                )
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in item_name_graphics_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in item_name_graphics_rows
            ),
            "aligned_reference_reviews": item_name_graphics_reference_reviews,
            "missing_aligned_reference_reviews": [
                {
                    "target": f"0x{target:06X}",
                    "address": f"0x{reference:06X}",
                }
                for target, reference in sorted(
                    item_name_graphics_reference_pairs
                    - set(ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
                )
            ],
            "stale_aligned_reference_reviews": [
                {
                    "target": f"0x{target:06X}",
                    "address": f"0x{reference:06X}",
                }
                for target, reference in sorted(
                    set(ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
                    - item_name_graphics_reference_pairs
                )
            ],
            "candidates": item_name_graphics_rows,
        },
        "system_graphics_ending_bank": {
            "range": "0x080000..0x090000",
            "candidate_count": len(system_graphics_ending_rows),
            "category_counts": dict(
                sorted(system_graphics_ending_category_counts.items())
            ),
            "unclassified_count": system_graphics_ending_category_counts.get(
                "unclassified", 0
            ),
            "missing_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    system_graphics_ending_addresses
                    - system_graphics_ending_reviewed_addresses
                )
            ],
            "stale_structured_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    set(SYSTEM_GRAPHICS_ENDING_REVIEWS)
                    - system_graphics_ending_addresses
                )
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in system_graphics_ending_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in system_graphics_ending_rows
            ),
            "candidates": system_graphics_ending_rows,
        },
        "ending_scenario_bank": {
            "range": "0x090000..0x0A0000",
            "candidate_count": len(ending_scenario_rows),
            "category_counts": dict(
                sorted(ending_scenario_category_counts.items())
            ),
            "unclassified_count": ending_scenario_category_counts.get(
                "unclassified", 0
            ),
            "missing_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    ending_scenario_addresses
                    - ending_scenario_reviewed_addresses
                )
            ],
            "stale_structured_review_addresses": [
                f"0x{address:06X}"
                for address in sorted(
                    set(ENDING_SCENARIO_STRUCTURED_REVIEWS)
                    - ending_scenario_addresses
                )
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in ending_scenario_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in ending_scenario_rows
            ),
            "retained_level_prefix": {
                "address": f"0x{SCENARIO_LEVEL_PREFIX:06X}",
                "source_bytes": japanese[
                    SCENARIO_LEVEL_PREFIX : SCENARIO_LEVEL_PREFIX + 3
                ].hex(" ").upper(),
                "current_bytes": korean[
                    SCENARIO_LEVEL_PREFIX : SCENARIO_LEVEL_PREFIX + 3
                ].hex(" ").upper(),
                "text": "L-",
                "hook": f"0x{SCENARIO_LEVEL_PREFIX_HOOK:06X}",
                "hook_bytes": japanese[
                    SCENARIO_LEVEL_PREFIX_HOOK :
                    SCENARIO_LEVEL_PREFIX_HOOK
                    + len(SCENARIO_LEVEL_PREFIX_HOOK_BYTES)
                ].hex(" ").upper(),
                "source_hook_valid": japanese[
                    SCENARIO_LEVEL_PREFIX_HOOK :
                    SCENARIO_LEVEL_PREFIX_HOOK
                    + len(SCENARIO_LEVEL_PREFIX_HOOK_BYTES)
                ]
                == SCENARIO_LEVEL_PREFIX_HOOK_BYTES,
                "current_hook_preserved": korean[
                    SCENARIO_LEVEL_PREFIX_HOOK :
                    SCENARIO_LEVEL_PREFIX_HOOK
                    + len(SCENARIO_LEVEL_PREFIX_HOOK_BYTES)
                ]
                == SCENARIO_LEVEL_PREFIX_HOOK_BYTES,
                "current_record_preserved": korean[
                    SCENARIO_LEVEL_PREFIX : SCENARIO_LEVEL_PREFIX + 3
                ]
                == b"L-\xFF",
                "live_verified": True,
                "evidence": SCENARIO_LEVEL_PREFIX_EVIDENCE,
            },
            "candidates": ending_scenario_rows,
        },
        "text_ui_bank": {
            "range": "0x0A0000..0x0B0000",
            "candidate_count": len(detailed_rows),
            "category_counts": dict(sorted(category_counts.items())),
            "unclassified_count": category_counts.get("unclassified", 0),
            "missing_review_addresses": [
                f"0x{address:06X}" for address in missing_reviews
            ],
            "stale_review_addresses": [
                f"0x{address:06X}" for address in stale_reviews
            ],
            "aligned_absolute_32_reference_count": sum(
                len(row["aligned_absolute_32_references"])
                for row in detailed_rows
            ),
            "pc_relative_lea_pea_reference_count": sum(
                len(row["pc_relative_lea_pea_references"])
                for row in detailed_rows
            ),
            "candidates": detailed_rows,
        },
    }


def markdown_report(result: dict[str, object]) -> str:
    item_bank = result["item_name_graphics_bank"]
    system_bank = result["system_graphics_ending_bank"]
    ending_bank = result["ending_scenario_bank"]
    level_prefix = ending_bank["retained_level_prefix"]
    bank = result["text_ui_bank"]
    lines = [
        "# Short Inline Byte Candidate Inventory",
        "",
        "Generated by `python3 tools/jp_short_inline_byte_inventory.py`.",
        "",
        str(result["warning"]),
        "",
        f"- Low-signal candidates: {result['candidate_count']}",
        f"- Half-width candidates: {result['kind_counts']['halfwidth']}",
        f"- Uppercase ASCII candidates: {result['kind_counts']['ascii']}",
        (
            "- Item/name/graphics-bank candidates: "
            f"{item_bank['candidate_count']}"
        ),
        (
            "- Item/name/graphics-bank unclassified: "
            f"{item_bank['unclassified_count']}"
        ),
        (
            "- System/graphics/ending-bank candidates: "
            f"{system_bank['candidate_count']}"
        ),
        (
            "- System/graphics/ending-bank unclassified: "
            f"{system_bank['unclassified_count']}"
        ),
        (
            "- Ending/scenario-bank candidates: "
            f"{ending_bank['candidate_count']}"
        ),
        (
            "- Ending/scenario-bank unclassified: "
            f"{ending_bank['unclassified_count']}"
        ),
        f"- Text/UI-bank candidates: {bank['candidate_count']}",
        f"- Text/UI-bank unclassified: {bank['unclassified_count']}",
        (
            "- Exact aligned 32-bit references to text/UI-bank candidates: "
            f"{bank['aligned_absolute_32_reference_count']}"
        ),
        (
            "- Exact `LEA d16(PC)`/`PEA d16(PC)` references to text/UI-bank "
            f"candidates: {bank['pc_relative_lea_pea_reference_count']}"
        ),
        "",
        "## Region Counts",
        "",
        "| Region | Half-width | ASCII |",
        "| --- | ---: | ---: |",
    ]
    regions = sorted(
        set(result["region_counts"]["halfwidth"])
        | set(result["region_counts"]["ascii"])
    )
    for region in regions:
        lines.append(
            f"| `{region}` | "
            f"{result['region_counts']['halfwidth'].get(region, 0)} | "
            f"{result['region_counts']['ascii'].get(region, 0)} |"
        )
    lines.extend(
        [
            "",
            "## Reviewed Item/Name/Graphics-Bank Candidates",
            "",
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in item_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned four-byte windows: "
                f"{item_bank['aligned_absolute_32_reference_count']}; all are "
                "reviewed below as non-pointer coincidences."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{item_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Address | Kind | Raw | Classification | Owner |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in item_bank["candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['kind']}` | `{row['raw_hex']}` | "
            f"`{row['category']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "The seven early rows are packed 4bpp item/system graphics. "
            "`0x061ABB` is the low byte of the final name-table pointer "
            "`0x00061ABC` followed by eight padding spaces. The remaining "
            "75 rows repeat inside packed 4bpp tile/sprite blocks; they are "
            "pixel nibbles, not half-width or ASCII text.",
            "",
            "| Apparent target | Four-byte window | Classification | Evidence |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in item_bank["aligned_reference_reviews"]:
        lines.append(
            f"| `{row['target']}` | `{row['address']}` | "
            f"`{row['classification']}` | {row['evidence']} |"
        )
    lines.extend(
        [
            "",
            "The `0x06121F` match is a sliding four-byte window inside a numeric/",
            "graphics index row. Both `0x070C2A` matches cross a 68000 instruction",
            "boundary: immediate value `0007` is followed by opcode `0C2A`.",
            "They are not absolute pointers.",
            "",
            "## Reviewed System/Graphics/Ending-Bank Candidates",
            "",
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in system_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned 32-bit references: "
                f"{system_bank['aligned_absolute_32_reference_count']}."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{system_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Address | Kind | Raw | Classification | Owner |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in system_bank["candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['kind']}` | `{row['raw_hex']}` | "
            f"`{row['category']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "The 13 word-stream rows are low-byte lanes of shared system, magic,",
            "or mercenary-name glyph words. The other 67 addresses are pinned",
            "tilemap/render scripts, sprite frame/coordinate/animation records,",
            "or character-epilogue pointer/selector fields. None is a standalone",
            "user-facing Japanese byte string.",
            "",
            "## Reviewed Ending/Scenario-Bank Candidates",
            "",
            f"- `{level_prefix['address']}` is the byte record `{level_prefix['text']}`.",
            f"  The stock code at `{level_prefix['hook']}` loads it directly before",
            "  drawing each unit's numeric level in the scrolling scenario briefing.",
            "  It is an intentional compact level abbreviation, not untranslated",
            "  Japanese. The current ROM preserves both record and hook, and",
            f"  `{level_prefix['evidence']}` visibly shows `L-5`, `L-4`, and other",
            "  unit levels.",
            (
                "- Category totals: "
                + ", ".join(
                    f"`{category}` {count}"
                    for category, count in ending_bank[
                        "category_counts"
                    ].items()
                )
                + "."
            ),
            (
                "- Exact aligned 32-bit references: "
                f"{ending_bank['aligned_absolute_32_reference_count']}; "
                "the sole reference is the retained `L-` load."
            ),
            (
                "- Exact `LEA d16(PC)`/`PEA d16(PC)` references: "
                f"{ending_bank['pc_relative_lea_pea_reference_count']}."
            ),
            "",
            "| Structured address | Raw | Owner |",
            "| --- | --- | --- |",
        ]
    )
    for row in ending_bank["candidates"]:
        if row["category"] != "structured_layout_false_positive":
            continue
        lines.append(
            f"| `{row['address']}` | `{row['raw_hex']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "## Reviewed Text/UI-Bank Candidates",
            "",
            "| Address | Kind | Raw | Classification | Owner |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in bank["candidates"]:
        lines.append(
            f"| `{row['address']}` | `{row['kind']}` | `{row['raw_hex']}` | "
            f"`{row['category']}` | {row['owner']} |"
        )
    lines.extend(
        [
            "",
            "The 28 word-stream rows begin on one byte lane of an existing 16-bit glyph",
            "or token word. The remaining 10 rows end at a structured layout boundary.",
            "They are not standalone user-facing Japanese strings and must not be patched",
            "as byte strings. Full word contexts and reference lists are in",
            "`localization/short_inline_byte_candidates.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory one/two-signal FF-terminated inline byte candidates"
    )
    parser.add_argument(
        "--jp-rom",
        type=Path,
        default=Path("roms/original/Langrisser II (Japan).md"),
    )
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean).md"),
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("localization/short_inline_byte_candidates.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/short_inline_byte_candidate_inventory.md"),
    )
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    item_bank = result["item_name_graphics_bank"]
    system_bank = result["system_graphics_ending_bank"]
    ending_bank = result["ending_scenario_bank"]
    bank = result["text_ui_bank"]
    print(
        f"{result['candidate_count']} low-signal candidates; "
        f"{item_bank['candidate_count']} item/name/graphics-bank, "
        f"{system_bank['candidate_count']} system/graphics/ending-bank, "
        f"{ending_bank['candidate_count']} ending/scenario-bank, and "
        f"{bank['candidate_count']} text/UI-bank candidates, "
        f"{item_bank['unclassified_count'] + system_bank['unclassified_count'] + ending_bank['unclassified_count'] + bank['unclassified_count']} "
        "unclassified"
    )


if __name__ == "__main__":
    main()
