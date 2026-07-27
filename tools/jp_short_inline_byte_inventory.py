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
TEXT_UI_BANK_START = 0x0A0000
TEXT_UI_BANK_END = 0x0B0000
MAX_LOW_SIGNAL = 2

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


def inventory(japanese: bytes) -> dict[str, object]:
    candidates = low_signal_runs(japanese)
    text_ui = [
        row
        for row in candidates
        if TEXT_UI_BANK_START <= int(row["start_int"]) < TEXT_UI_BANK_END
    ]
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
    return {
        "warning": (
            "This scan inventories maximal FF-terminated half-width/uppercase-ASCII "
            "runs with only one or two signal bytes. Most are binary coincidences. "
            "Only the 0x0A0000..0x0AFFFF text/UI-bank candidates are manually "
            "classified here. Zero exact aligned 32-bit or LEA/PEA PC-relative "
            "references does not exclude base-relative, indexed, or dynamic access."
        ),
        "source_sha256": hashlib.sha256(japanese).hexdigest(),
        "scan_end": f"0x{SCAN_END:06X}",
        "candidate_count": len(candidates),
        "kind_counts": dict(sorted(kind_counts.items())),
        "region_counts": region_counts,
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
    result = inventory(args.jp_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    bank = result["text_ui_bank"]
    print(
        f"{result['candidate_count']} low-signal candidates; "
        f"{bank['candidate_count']} text/UI-bank candidates, "
        f"{bank['unclassified_count']} unclassified"
    )


if __name__ == "__main__":
    main()
