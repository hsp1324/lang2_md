#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Callable
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import build_korean_jp_probe as builder
from tools.jp_direct_byte_string_inventory import global_string_ownership


SCAN_END = 0x180000
SOUND_TEST_TABLE = 0x05E040
SOUND_TEST_RECORD_SIZE = 16
SOUND_TEST_RECORD_COUNT = 77
SOUND_TEST_END = SOUND_TEST_TABLE + SOUND_TEST_RECORD_SIZE * SOUND_TEST_RECORD_COUNT


def scan_runs(
    data: bytes,
    allowed: set[int],
    minimum_signal: int,
    signal: Callable[[int], bool],
    maximum_length: int = 40,
) -> list[tuple[int, int, bytes]]:
    rows = []
    offset = 0
    end = min(len(data), SCAN_END)
    while offset < end:
        if data[offset] not in allowed:
            offset += 1
            continue
        start = offset
        while offset < end and data[offset] in allowed:
            offset += 1
        raw = data[start:offset]
        if (
            offset < end
            and data[offset] == 0xFF
            and sum(bool(signal(value)) for value in raw) >= minimum_signal
            and len(raw) <= maximum_length
        ):
            rows.append((start, offset + 1, raw))
        offset += 1
    return rows


def halfwidth_runs(data: bytes) -> list[tuple[int, int, bytes]]:
    allowed = {0x20, *range(0xA1, 0xE0)}
    return scan_runs(data, allowed, 4, lambda value: value != 0x20, 32)


def ascii_runs(data: bytes) -> list[tuple[int, int, bytes]]:
    allowed = {
        *range(ord("0"), ord("9") + 1),
        *range(ord("A"), ord("Z") + 1),
        0x20,
        ord("."),
        ord("+"),
        ord("-"),
        ord(":"),
    }
    return scan_runs(
        data,
        allowed,
        4,
        lambda value: ord("A") <= value <= ord("Z"),
        40,
    )


def overlaps(start: int, end: int, intervals: list[tuple[int, int, str]]) -> bool:
    return any(start < owned_end and end > owned_start for owned_start, owned_end, _ in intervals)


def classify_halfwidth(
    start: int,
    end: int,
    global_intervals: list[tuple[int, int, str]],
) -> tuple[str, str]:
    if overlaps(start, end, global_intervals):
        return "global_table_string", "owned by class, item, or commander-name table"
    if start == builder.INLINE_DISCARD_PROMPT_SOURCE:
        return "localized_inline_ui", "fixed 13-cell item discard/replacement prompt"
    if 0x040000 <= start < 0x050000:
        return "global_font_bitmap_false_positive", "packed 16x16 glyph pixels"
    if SOUND_TEST_TABLE <= start < SOUND_TEST_END:
        return "sound_test_label_table", "hidden 77-row sound-test label table"
    if start <= builder.ILLUSION_CLASS_SOURCE_POINTER < end:
        return "special_illusion_class", "run begins in the preceding pointer byte"
    if 0x080000 <= start < 0x090000:
        return "glyph_or_tile_data_false_positive", "packed glyph/tile data"
    if start in (0x0A3B9D, 0x0A3BA6):
        return "internal_secret_name_comparison", "reserved Langrisser/Alhazard name comparison"
    if start in (0x0A50F5, 0x0A5190):
        return "structured_character_resource", "name-entry character/index resource"
    if start >= 0x0B0000:
        return "compressed_resource_data", "compressed-resource table or payload"
    return "unclassified", "requires manual ownership review"


def classify_ascii(start: int) -> tuple[str, str]:
    if start in (0x00811C, 0x00816C):
        return "internal_hardware_signature", "SEGA hardware signature"
    if start in (0x008220, 0x0084AC, 0x02A252):
        return "internal_controller_signature", "PADR controller signature"
    if start == 0x01808C:
        return "retained_compact_english_ui", "PAGE label; compact English is allowed"
    if 0x080000 <= start < 0x090000:
        return "glyph_or_tile_data_false_positive", "packed glyph/tile data"
    if start in (0x0A18DF, 0x0A18EB, 0x0A18F7):
        return "localized_equipment_category_container", "visible labels patched at the next byte"
    if start in (0x0A450E, 0x0A452B):
        return "retained_title_record", "NCS CORP. / PUSH START BUTTON source record"
    if start == 0x0A61A2:
        return "structured_character_resource", "character/index resource"
    if start >= 0x0B0000:
        return "compressed_resource_data", "compressed-resource table or payload"
    return "unclassified", "requires manual ownership review"


def sound_test_rows(data: bytes) -> list[dict[str, object]]:
    rows = []
    for index in range(SOUND_TEST_RECORD_COUNT):
        start = SOUND_TEST_TABLE + index * SOUND_TEST_RECORD_SIZE
        raw = data[start : start + SOUND_TEST_RECORD_SIZE]
        label = raw[1:].decode("cp932", errors="strict").rstrip()
        rows.append(
            {
                "index": index,
                "address": f"0x{start:06X}",
                "sound_id": f"0x{raw[0]:02X}",
                "original_label": label,
                "contains_japanese": any("｡" <= char <= "ﾟ" for char in label),
                "target_korean": None,
                "live_verified": False,
            }
        )
    return rows


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    _, global_intervals = global_string_ownership(japanese)
    candidates = []
    for kind, runs in (
        ("halfwidth", halfwidth_runs(japanese)),
        ("ascii", ascii_runs(japanese)),
    ):
        for start, end, raw in runs:
            category, owner = (
                classify_halfwidth(start, end, global_intervals)
                if kind == "halfwidth"
                else classify_ascii(start)
            )
            candidates.append(
                {
                    "kind": kind,
                    "address": f"0x{start:06X}",
                    "end": f"0x{end:06X}",
                    "original_text": raw.decode("cp932" if kind == "halfwidth" else "ascii"),
                    "raw_hex": raw.hex(" ").upper(),
                    "category": category,
                    "owner": owner,
                }
            )
    candidates.sort(key=lambda row: (int(str(row["address"]), 16), str(row["kind"])))
    counts = Counter(str(row["category"]) for row in candidates)
    sound_rows = sound_test_rows(japanese)
    hook = bytes.fromhex("4E F9") + builder.INLINE_DISCARD_PROMPT_RENDER_ROUTINE.to_bytes(4, "big")
    return {
        "warning": (
            "This conservative scan covers maximal half-width-Japanese and uppercase-ASCII "
            "FF-terminated runs. It does not claim arbitrary executable bytes are text."
        ),
        "source_sha256": hashlib.sha256(japanese).hexdigest(),
        "halfwidth_candidate_count": sum(row["kind"] == "halfwidth" for row in candidates),
        "ascii_candidate_count": sum(row["kind"] == "ascii" for row in candidates),
        "candidate_count": len(candidates),
        "category_counts": dict(sorted(counts.items())),
        "unclassified_count": counts.get("unclassified", 0),
        "discard_prompt": {
            "source": f"0x{builder.INLINE_DISCARD_PROMPT_SOURCE:06X}",
            "hook": f"0x{builder.INLINE_DISCARD_PROMPT_RENDER_HOOK:06X}",
            "record": f"0x{builder.INLINE_DISCARD_PROMPT_RECORD:06X}",
            "target_korean": builder.INLINE_DISCARD_PROMPT_TEXT,
            "hook_installed": korean[
                builder.INLINE_DISCARD_PROMPT_RENDER_HOOK :
                builder.INLINE_DISCARD_PROMPT_RENDER_HOOK + len(hook)
            ] == hook,
            "live_verified": False,
        },
        "sound_test": {
            "table": f"0x{SOUND_TEST_TABLE:06X}",
            "end": f"0x{SOUND_TEST_END:06X}",
            "record_count": len(sound_rows),
            "japanese_label_count": sum(bool(row["contains_japanese"]) for row in sound_rows),
            "localized_count": sum(row["target_korean"] is not None for row in sound_rows),
            "live_verified": False,
            "rows": sound_rows,
        },
        "candidates": candidates,
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Inline Byte String Inventory",
        "",
        "Generated by `python3 tools/jp_inline_byte_string_inventory.py`.",
        "",
        str(result["warning"]),
        "",
        f"- Half-width candidates: {result['halfwidth_candidate_count']}",
        f"- Uppercase ASCII candidates: {result['ascii_candidate_count']}",
        f"- Total: {result['candidate_count']}",
        f"- Unclassified: {result['unclassified_count']}",
        "",
        "| Classification | Candidates |",
        "| --- | ---: |",
    ]
    for category, count in result["category_counts"].items():
        lines.append(f"| `{category}` | {count} |")
    prompt = result["discard_prompt"]
    sound = result["sound_test"]
    lines.extend(
        [
            "",
            "## User-Facing Findings",
            "",
            f"- `{prompt['source']}` is the 13-cell `ｽﾃﾙ ｱｲﾃﾑ ｾﾝﾀｸ` record. The code at",
            f"  `{prompt['hook']}` loads it directly and draws exactly 13 cells. Production now",
            f"  redirects that path to `{prompt['record']}` and renders `{prompt['target_korean']}`",
            "  through the full byte-UI tile table. Runtime verification is still pending.",
            f"- `{sound['table']}..{sound['end']}` is a 77-row hidden sound-test label table.",
            f"  {sound['japanese_label_count']} rows contain half-width Japanese. It is a real",
            "  structured UI/debug surface, not an item, class, summon, or compressed asset.",
            "  Its access path and live appearance must be verified before translation.",
            "- `PAGE`, `NCS CORP.`, and `PUSH START BUTTON` are intentionally retained compact",
            "  English/title text. `SEGA` and `PADR` are internal hardware/controller signatures.",
            "",
            "Full candidate bytes and all sound-test rows are in",
            "`localization/inline_byte_strings.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory non-pointer inline byte strings")
    parser.add_argument("--jp-rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean JP Probe).md"),
    )
    parser.add_argument(
        "--json", type=Path, default=Path("localization/inline_byte_strings.json")
    )
    parser.add_argument(
        "--markdown", type=Path, default=Path("docs/inline_byte_string_inventory.md")
    )
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['candidate_count']} candidates, "
        f"{result['unclassified_count']} unclassified; "
        f"{result['sound_test']['record_count']} sound-test rows"
    )


if __name__ == "__main__":
    main()
