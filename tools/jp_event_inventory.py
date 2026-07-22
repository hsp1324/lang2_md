#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


EVENT_POINTER_TABLE = 0x18011A
SCENARIO_COUNT = 31
EVENT_DATA_END = 0x1B9000
TEXT_CONTROLS = {0xFFF7, 0xFFFE}
TEXT_TERMINATORS = {0xFFFD, 0xFFFF}
MAX_GLYPH_ID = 0x07FF

# These pointer targets pass the broad glyph-range heuristic but are event
# metadata, not dialogue. Match the full original word stream so a changed ROM
# cannot silently inherit the exclusion.
KNOWN_STRUCTURED_RECORDS = {
    0x18F610: (
        0x0202, 0x0601, 0x0019, 0x0200, 0x0201, 0x0101, 0x0019,
        0x020C, 0x0202, 0x0601, 0x0019, 0x0242, 0xFFFF,
    ),
    0x1B0518: (
        0x0001, 0x0001, 0x001B, 0x0544, 0x0104, 0x0002, 0x001B,
        0x05E4, 0x0204, 0x0001, 0x001B, 0x05F4, 0x0301, 0x0002,
        0x001B, 0x062A, 0xFFFF,
    ),
}


def be16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def be32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def read_text_page(data: bytes, offset: int, limit: int) -> list[int] | None:
    words: list[int] = []
    glyph_count = 0
    for _ in range(256):
        if offset + 2 > limit:
            return None
        word = be16(data, offset)
        words.append(word)
        offset += 2
        if word in TEXT_TERMINATORS:
            return words if glyph_count >= 3 else None
        if word in TEXT_CONTROLS:
            continue
        if word > MAX_GLYPH_ID:
            return None
        glyph_count += 1
    return None


def read_physical_segments(data: bytes, start: int, limit: int) -> list[tuple[int, list[int]]] | None:
    segments: list[tuple[int, list[int]]] = []
    offset = start
    while offset < limit:
        segment_start = offset
        words: list[int] = []
        for _ in range(256):
            if offset + 2 > limit:
                return None
            word = be16(data, offset)
            words.append(word)
            offset += 2
            if word in TEXT_TERMINATORS:
                segments.append((segment_start, words))
                break
            if word in TEXT_CONTROLS or word <= MAX_GLYPH_ID:
                continue
            return None
        else:
            return None
    return segments if offset == limit else None


def final_record_chain_end(data: bytes, start: int, block_end: int) -> int:
    offset = start
    for _ in range(4096):
        if offset + 2 > block_end:
            return start
        word = be16(data, offset)
        offset += 2
        if word == 0xFFFF:
            return offset
        if word == 0xFFFD or word in TEXT_CONTROLS or word <= MAX_GLYPH_ID:
            continue
        return start
    return start


def event_block_starts(data: bytes) -> list[int]:
    starts = [
        be32(data, EVENT_POINTER_TABLE + index * 4)
        for index in range(SCENARIO_COUNT)
    ]
    if starts != sorted(starts) or not all(0x180000 <= value < EVENT_DATA_END for value in starts):
        raise ValueError("invalid or unordered event pointer table")
    return starts


def record_classification(address: int, words: list[int]) -> str:
    expected = KNOWN_STRUCTURED_RECORDS.get(address)
    if expected is None:
        return "text"
    if tuple(words) != expected:
        raise ValueError(f"known structured record changed at 0x{address:06X}")
    return "structured_non_text"


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    starts = event_block_starts(japanese)
    scenarios: list[dict[str, object]] = []
    for number, (start, end) in enumerate(zip(starts, starts[1:] + [EVENT_DATA_END]), 1):
        pages: dict[int, dict[str, object]] = {}
        for source in range(start, end - 3, 2):
            target = be32(japanese, source)
            if not (start <= target < end) or target & 1:
                continue
            words = read_text_page(japanese, target, end)
            if words is None:
                continue
            page_data = {
                "address": f"0x{target:06X}",
                "word_count": len(words),
                "terminator": f"0x{words[-1]:04X}",
                "tokens": " ".join(f"{word:04X}" for word in words),
                "source_refs": [],
            }
            classification = record_classification(target, words)
            if classification != "text":
                page_data["classification"] = classification
            page = pages.setdefault(target, page_data)
            page["source_refs"].append(f"0x{source:06X}")

        modified = 0
        for target, page in pages.items():
            byte_count = int(page["word_count"]) * 2
            original = japanese[target : target + byte_count]
            patched = korean[target : target + byte_count]
            changed_words = sum(
                original[index : index + 2] != patched[index : index + 2]
                for index in range(0, byte_count, 2)
            )
            page["modified"] = bool(changed_words)
            page["modified_word_count"] = changed_words
            modified += bool(changed_words)

        ordered_addresses = sorted(pages)
        ordered_pages = [pages[address] for address in ordered_addresses]
        physical_page_count = 0
        modified_physical_page_count = 0
        for page_index, (target, page) in enumerate(zip(ordered_addresses, ordered_pages)):
            next_target = (
                ordered_addresses[page_index + 1]
                if page_index + 1 < len(ordered_addresses)
                else final_record_chain_end(japanese, target, end)
            )
            first_end = target + int(page["word_count"]) * 2
            segments = (
                read_physical_segments(japanese, target, next_target)
                if next_target >= first_end
                else None
            )
            if segments is None:
                original_words = [int(word, 16) for word in str(page["tokens"]).split()]
                segments = [(target, original_words)]
            segment_rows: list[dict[str, object]] = []
            for segment_start, words in segments:
                byte_count = len(words) * 2
                original = japanese[segment_start : segment_start + byte_count]
                patched = korean[segment_start : segment_start + byte_count]
                changed_words = sum(
                    original[index : index + 2] != patched[index : index + 2]
                    for index in range(0, byte_count, 2)
                )
                segment_data = {
                    "address": f"0x{segment_start:06X}",
                    "word_count": len(words),
                    "terminator": f"0x{words[-1]:04X}",
                    "tokens": " ".join(f"{word:04X}" for word in words),
                    "modified": bool(changed_words),
                    "modified_word_count": changed_words,
                }
                if "classification" in page:
                    segment_data["classification"] = page["classification"]
                segment_rows.append(segment_data)
                modified_physical_page_count += bool(changed_words)
            page["physical_page_count"] = len(segment_rows)
            page["physical_pages"] = segment_rows
            physical_page_count += len(segment_rows)
        text_pages = [
            page for page in ordered_pages
            if page.get("classification", "text") == "text"
        ]
        text_physical_pages = [
            physical
            for page in text_pages
            for physical in page["physical_pages"]
        ]
        scenarios.append(
            {
                "scenario": number,
                "block_start": f"0x{start:06X}",
                "block_end": f"0x{end:06X}",
                "page_count": len(ordered_pages),
                "modified_page_count": modified,
                "unchanged_page_count": len(ordered_pages) - modified,
                "text_page_count": len(text_pages),
                "modified_text_page_count": sum(bool(page["modified"]) for page in text_pages),
                "structured_non_text_count": len(ordered_pages) - len(text_pages),
                "physical_page_count": physical_page_count,
                "modified_physical_page_count": modified_physical_page_count,
                "unchanged_physical_page_count": physical_page_count - modified_physical_page_count,
                "text_physical_page_count": len(text_physical_pages),
                "modified_text_physical_page_count": sum(
                    bool(page["modified"]) for page in text_physical_pages
                ),
                "pages": ordered_pages,
            }
        )

    return {
        "event_pointer_table": f"0x{EVENT_POINTER_TABLE:06X}",
        "event_data_end": f"0x{EVENT_DATA_END:06X}",
        "scenario_count": SCENARIO_COUNT,
        "page_count": sum(int(item["page_count"]) for item in scenarios),
        "modified_page_count": sum(int(item["modified_page_count"]) for item in scenarios),
        "text_page_count": sum(int(item["text_page_count"]) for item in scenarios),
        "modified_text_page_count": sum(
            int(item["modified_text_page_count"]) for item in scenarios
        ),
        "structured_non_text_count": sum(
            int(item["structured_non_text_count"]) for item in scenarios
        ),
        "physical_page_count": sum(int(item["physical_page_count"]) for item in scenarios),
        "modified_physical_page_count": sum(
            int(item["modified_physical_page_count"]) for item in scenarios
        ),
        "text_physical_page_count": sum(
            int(item["text_physical_page_count"]) for item in scenarios
        ),
        "modified_text_physical_page_count": sum(
            int(item["modified_text_physical_page_count"]) for item in scenarios
        ),
        "scenarios": scenarios,
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Full Localization Event Inventory",
        "",
        "Generated by `python3 tools/jp_event_inventory.py`.",
        "",
        "`modified` means that the current Korean build differs from the Japanese ROM at",
        "that page. It does not by itself prove that the whole page is translated or live-verified.",
        "",
        f"- Event pointer table: `{result['event_pointer_table']}`",
        f"- Scenarios: {result['scenario_count']}",
        f"- Pointer candidates: {result['page_count']}",
        f"- Structured non-text exclusions: {result['structured_non_text_count']}",
        f"- Text records: {result['text_page_count']}",
        f"- Modified text records: {result['modified_text_page_count']}",
        f"- Physical text pages: {result['text_physical_page_count']}",
        f"- Modified physical text pages: {result['modified_text_physical_page_count']}",
        "",
        "| Scenario | Event block | Text records | Physical text | Modified physical | Excluded | Status |",
        "| ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in result["scenarios"]:
        modified = int(item["modified_text_physical_page_count"])
        total = int(item["text_physical_page_count"])
        status = "unstarted" if modified == 0 else ("modified" if modified < total else "all modified")
        lines.append(
            f"| {item['scenario']} | `{item['block_start']}..{item['block_end']}` | "
            f"{item['text_page_count']} | {total} | {modified} | "
            f"{item['structured_non_text_count']} | {status} |"
        )
    lines.extend(
        [
            "",
            "Detailed addresses, source references, terminators, and original glyph-token streams",
            "are stored in `localization/event_pages.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory Japanese event text pages by scenario")
    parser.add_argument("--jp-rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean).md"),
    )
    parser.add_argument("--json", type=Path, default=Path("localization/event_pages.json"))
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/full_localization_inventory.md"),
    )
    args = parser.parse_args()

    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['page_count']} candidate pages, "
        f"{result['modified_page_count']} modified; wrote {args.json} and {args.markdown}"
    )


if __name__ == "__main__":
    main()
