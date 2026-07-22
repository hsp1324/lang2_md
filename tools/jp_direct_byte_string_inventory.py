#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import build_korean_jp_probe as builder
from tools.jp_global_inventory import TABLES


SCAN_END = 0x180000
TARGET_START = 0x040000
MAX_BYTES = 64
MIN_CHARS = 3
MAX_CHARS = 40

ILLUSION_TARGET = 0x05E5CE
ILLUSION_POINTER_SELECTOR = 0x010420
ILLUSION_POINTER_SELECTOR_BYTES = bytes.fromhex("43 F9 00 05 E5 CA")
EQUIPMENT_CATEGORY_CONTAINER = 0x0A18DE
SECRET_NAME_COMPARISON = 0x0A3B9D
NAME_ENTRY_CHARACTER_RESOURCES = {0x0A516E, 0x0A518A}

# These targets were individually reviewed in the Japanese ROM. Their bytes are
# graphics, maps, numeric tables, or compressed data that happen to decode as a
# short CP932/ASCII run before the next FF byte. Pinning the set makes a newly
# introduced candidate fail closed instead of silently inheriting the verdict.
REVIEWED_FALSE_POSITIVE_TARGETS = {
    0x043141, 0x0431FC, 0x045142, 0x04608A, 0x047600, 0x047601, 0x047608, 0x0478FF,
    0x048242, 0x04946E, 0x049F5C, 0x080400, 0x080402, 0x080404, 0x08066E, 0x0808E8,
    0x081006, 0x081008, 0x081828, 0x08363C, 0x083877, 0x084EB9, 0x086100, 0x0B0C2E,
    0x0B80B8, 0x0B80BD, 0x0B80C0, 0x0BABA0, 0x0C001E, 0x0C0020, 0x0C0022, 0x0C0023,
    0x0C0024, 0x0C010B, 0x0C0301, 0x0C08A9, 0x0C15B3, 0x0C204A, 0x0C317C, 0x0C3A1A,
    0x0C4847, 0x0CC2FC, 0x0D0001, 0x0D0002, 0x0D0003, 0x0D0004, 0x0D0043, 0x0D0044,
    0x0D0045, 0x0D1402, 0x0E0807, 0x0E0808, 0x0E11FC, 0x0E1229, 0x0E5279, 0x0F008A,
    0x0F0091, 0x0F0700, 0x0FA6E6, 0x100C68, 0x100C6E, 0x102242, 0x10B268, 0x110022,
    0x11B200, 0x12343C, 0x126700, 0x12D139, 0x12D13C, 0x12E1F9, 0x12E200, 0x130000,
    0x130002, 0x130003, 0x130004, 0x130006, 0x130007, 0x130009, 0x13000A, 0x1301D1,
    0x133131, 0x133137, 0x134000, 0x1343F9,
}


def read_candidate(data: bytes, target: int) -> tuple[str, bytes] | None:
    end = data.find(b"\xff", target, min(len(data), target + MAX_BYTES + 1))
    if end < 0:
        return None
    raw = data[target:end]
    try:
        text = raw.decode("cp932", errors="strict")
    except UnicodeDecodeError:
        return None
    if not MIN_CHARS <= len(text) <= MAX_CHARS:
        return None
    if any(ord(char) < 0x20 or char == "\x7f" for char in text):
        return None
    japanese = any(
        "ぁ" <= char <= "ヿ" or "｡" <= char <= "ﾟ" or "一" <= char <= "龯"
        for char in text
    )
    safe_ascii = all(
        char.isascii() and (char.isalnum() or char in " .,:!?'+-*/&()")
        for char in text
    ) and any(char.isalpha() for char in text)
    return (text, raw) if japanese or safe_ascii else None


def scan_pointer_candidates(data: bytes) -> dict[int, list[int]]:
    references: dict[int, list[int]] = defaultdict(list)
    for offset in range(0, min(len(data), SCAN_END), 2):
        target = int.from_bytes(data[offset : offset + 4], "big")
        if TARGET_START <= target < min(len(data), SCAN_END):
            if read_candidate(data, target) is not None:
                references[target].append(offset)
    return dict(references)


def global_string_ownership(data: bytes) -> tuple[dict[int, list[str]], list[tuple[int, int, str]]]:
    exact: dict[int, list[str]] = defaultdict(list)
    intervals: list[tuple[int, int, str]] = []
    for group, table, count in TABLES:
        for index in range(count):
            target = int.from_bytes(data[table + index * 4 : table + index * 4 + 4], "big")
            end = data.find(b"\xff", target, min(len(data), target + MAX_BYTES + 1))
            if end < 0:
                raise ValueError(f"{group}[{index}] lacks FF terminator")
            exact[target].append(f"{group}[{index}]")
            intervals.append((target, end + 1, f"{group}[{index}]"))
    return dict(exact), intervals


def classify(
    target: int,
    exact: dict[int, list[str]],
    intervals: list[tuple[int, int, str]],
) -> tuple[str, str]:
    if target in exact:
        return "global_table_string", ", ".join(exact[target])
    interior = [owner for start, end, owner in intervals if start < target < end]
    if interior:
        return "global_table_interior", ", ".join(interior)
    if target == ILLUSION_TARGET:
        return "special_illusion_class", "status alternate class pointer 0x05E5CA"
    if target == EQUIPMENT_CATEGORY_CONTAINER:
        return "declared_equipment_category_ui", "control prefix plus WEPON/PROTECTER/ITEM labels"
    if target == SECRET_NAME_COMPARISON:
        return "internal_secret_name_comparison", "Langrisser/Alhazard name-entry comparison block"
    if target in NAME_ENTRY_CHARACTER_RESOURCES:
        return "structured_name_entry_resource", "byte character/index resource, not rendered as one string"
    if target in REVIEWED_FALSE_POSITIVE_TARGETS:
        return "reviewed_binary_false_positive", "binary data ending at a coincidental FF byte"
    return "unclassified", "requires manual ownership review"


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    references = scan_pointer_candidates(japanese)
    exact, intervals = global_string_ownership(japanese)
    rows = []
    for target in sorted(references):
        candidate = read_candidate(japanese, target)
        if candidate is None:
            raise AssertionError(f"candidate vanished at 0x{target:06X}")
        text, raw = candidate
        category, owner = classify(target, exact, intervals)
        rows.append(
            {
                "target": f"0x{target:06X}",
                "references": [f"0x{offset:06X}" for offset in references[target]],
                "text": text,
                "raw_hex": raw.hex(" ").upper(),
                "preceded_by_ff": target > 0 and japanese[target - 1] == 0xFF,
                "category": category,
                "owner": owner,
            }
        )
    counts = {
        category: sum(row["category"] == category for row in rows)
        for category in sorted({str(row["category"]) for row in rows})
    }
    current_illusion_pointer = int.from_bytes(
        korean[builder.ILLUSION_CLASS_POINTER : builder.ILLUSION_CLASS_POINTER + 4], "big"
    )
    return {
        "source_sha256": hashlib.sha256(japanese).hexdigest(),
        "scan_end": f"0x{SCAN_END:06X}",
        "candidate_count": len(rows),
        "reference_count": sum(len(row["references"]) for row in rows),
        "category_counts": counts,
        "unclassified_count": counts.get("unclassified", 0),
        "special_illusion": {
            "selector_instruction": f"0x{ILLUSION_POINTER_SELECTOR:06X}",
            "selector_bytes": ILLUSION_POINTER_SELECTOR_BYTES.hex(" ").upper(),
            "selector_valid": japanese[
                ILLUSION_POINTER_SELECTOR :
                ILLUSION_POINTER_SELECTOR + len(ILLUSION_POINTER_SELECTOR_BYTES)
            ] == ILLUSION_POINTER_SELECTOR_BYTES,
            "pointer_field": f"0x{builder.ILLUSION_CLASS_POINTER:06X}",
            "original_pointer": f"0x{ILLUSION_TARGET:06X}",
            "current_pointer": f"0x{current_illusion_pointer:06X}",
            "target_korean": builder.ILLUSION_CLASS_LABEL,
            "relocated": current_illusion_pointer != ILLUSION_TARGET,
        },
        "entries": rows,
    }


def markdown_report(result: dict[str, object]) -> str:
    counts = result["category_counts"]
    lines = [
        "# Direct Byte String Candidate Inventory",
        "",
        "Generated by `python3 tools/jp_direct_byte_string_inventory.py`.",
        "",
        "This inventory scans every even ROM offset as a possible big-endian 32-bit pointer,",
        "then accepts only strict CP932/ASCII `FF`-terminated targets. It complements the",
        "16-bit word-stream inventory; it does not replace event or compressed-resource scans.",
        "",
        f"- candidates: {result['candidate_count']}",
        f"- pointer references: {result['reference_count']}",
        f"- unclassified: {result['unclassified_count']}",
        "",
        "| Classification | Targets |",
        "| --- | ---: |",
    ]
    for category, count in counts.items():
        lines.append(f"| `{category}` | {count} |")
    illusion = result["special_illusion"]
    lines.extend(
        [
            "",
            "## User-facing exception found",
            "",
            f"The status routine at `{illusion['selector_instruction']}` selects the one-entry pointer at",
            f"`{illusion['pointer_field']}` for illusion units instead of the normal class table.",
            f"Its Japanese `{ILLUSION_TARGET:06X}` target (`ｲﾘｭｰｼﾞｮﾝ`) is relocated as",
            f"`{illusion['target_korean']}` at `{illusion['current_pointer']}`.",
            "",
            "## Retained internal strings",
            "",
            "- `0x0A3B9D` contains `ﾗﾝｸﾞﾘｯｻｰ` followed by `ｱﾙﾊｻﾞｰﾄﾞ`. Routine `0x02B1D8`",
            "  compares these reserved names against the name-entry buffer; it does not render them.",
            "- `0x0A18DE` is a control-prefixed equipment-category container. Its three visible",
            "  labels are already owned by `BYTE_UI_STRING_PATCHES` at `0x0A18E0/EC/F8`.",
            "- The 84 reviewed binary false positives are pinned by address. Any new strict",
            "  pointer candidate remains `unclassified` and fails the regression test.",
            "",
            "Full references, source bytes, decoded text, and ownership are in",
            "`localization/direct_byte_string_candidates.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory pointer-referenced FF byte strings")
    parser.add_argument("--jp-rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean).md"),
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("localization/direct_byte_string_candidates.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/direct_byte_string_candidate_inventory.md"),
    )
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['candidate_count']} candidates, {result['reference_count']} references, "
        f"{result['unclassified_count']} unclassified"
    )


if __name__ == "__main__":
    main()
