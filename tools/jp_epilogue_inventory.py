#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EPILOGUE_ENGLISH_INDEX_RANGE = range(1901, 1991)
EPILOGUE_TEXT_RANGE = (0x0895A2, 0x0954E2)
EPILOGUE_POINTER_SEARCH_RANGE = (0x087000, 0x089600)


def be16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def read_record(data: bytes, address: int, limit: int = 2048) -> list[int]:
    words = []
    for index in range(limit):
        word = be16(data, address + index * 2)
        words.append(word)
        if word == 0xFFFF:
            return words
    raise ValueError(f"unterminated epilogue record at 0x{address:06X}")


def pointer_references(data: bytes, address: int) -> list[int]:
    start, end = EPILOGUE_POINTER_SEARCH_RANGE
    needle = address.to_bytes(4, "big")
    references = []
    cursor = start
    while True:
        cursor = data.find(needle, cursor, end)
        if cursor < 0:
            return references
        references.append(cursor)
        cursor += 1


def dynamic_name_controls(words: list[int]) -> list[str]:
    controls = []
    index = 0
    while index + 1 < len(words):
        if words[index] == 0xFFF7:
            controls.append(f"0x{words[index + 1]:04X}")
            index += 2
        else:
            index += 1
    return controls


def build_inventory(
    japanese: bytes,
    mapping: dict[str, object],
    translations: dict[str, object] | None = None,
) -> dict[str, object]:
    translated_by_address = {
        int(str(row["address"]), 16): row
        for row in (translations or {}).get("records", [])
    }
    source_rows = [
        row
        for row in mapping["outside_event_blocks"]
        if int(row["index"]) in EPILOGUE_ENGLISH_INDEX_RANGE
    ]
    if len(source_rows) != len(EPILOGUE_ENGLISH_INDEX_RANGE):
        raise ValueError(f"expected 90 English epilogue references, got {len(source_rows)}")

    records = []
    seen_addresses = set()
    seen_pointer_references = set()
    for source in source_rows:
        address = int(str(source["continuation_prefix"]), 16)
        if not EPILOGUE_TEXT_RANGE[0] <= address < EPILOGUE_TEXT_RANGE[1]:
            raise ValueError(f"epilogue address outside text range: 0x{address:06X}")
        if address in seen_addresses:
            raise ValueError(f"duplicate epilogue address: 0x{address:06X}")
        seen_addresses.add(address)
        references = pointer_references(japanese, address)
        if len(references) != 1:
            raise ValueError(
                f"epilogue 0x{address:06X} has {len(references)} pointer references"
            )
        pointer_reference = references[0]
        if pointer_reference in seen_pointer_references:
            raise ValueError(f"duplicate pointer owner: 0x{pointer_reference:06X}")
        seen_pointer_references.add(pointer_reference)
        words = read_record(japanese, address)
        raw = japanese[address : address + len(words) * 2]
        record = {
                "address": f"0x{address:06X}",
                "pointer_reference": f"0x{pointer_reference:06X}",
                "english_record": int(source["index"]),
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "capacity_words": len(words),
                "dynamic_name_controls": dynamic_name_controls(words),
                "page_break_count": words.count(0xFFFD),
                "line_break_count": words.count(0xFFFE),
                "english_reference": str(source["english"]),
                "translation_status": "untranslated",
            }
        translated = translated_by_address.get(address)
        if translated is not None:
            if int(translated["english_record"]) != int(source["index"]):
                raise ValueError(f"English reference changed at 0x{address:06X}")
            if translated["source_sha256"] != record["source_sha256"]:
                raise ValueError(f"translation source hash changed at 0x{address:06X}")
            record["translation_status"] = "translated"
            record["target_korean"] = str(translated["text"])
        records.append(record)
    records.sort(key=lambda row: int(str(row["pointer_reference"]), 16))
    return {
        "source": "Japanese Mega Drive ROM records and pointer owners; English is reference only",
        "record_count": len(records),
        "text_range": f"0x{EPILOGUE_TEXT_RANGE[0]:06X}..0x{EPILOGUE_TEXT_RANGE[1]:06X}",
        "pointer_search_range": (
            f"0x{EPILOGUE_POINTER_SEARCH_RANGE[0]:06X}.."
            f"0x{EPILOGUE_POINTER_SEARCH_RANGE[1]:06X}"
        ),
        "translated_record_count": sum(
            row["translation_status"] == "translated" for row in records
        ),
        "records": records,
    }


def markdown_report(result: dict[str, object]) -> str:
    records = result["records"]
    capacities = [int(row["capacity_words"]) for row in records]
    return "\n".join(
        [
            "# Japanese Character Epilogue Inventory",
            "",
            "Generated by `python3 tools/jp_epilogue_inventory.py`.",
            "",
            "Every record start is taken from the external English mapping only as a",
            "candidate, then accepted only after the Japanese ROM proves one exact pointer",
            "owner and a complete `FFFF`-terminated source record. Japanese remains the",
            "translation authority.",
            "",
            f"- Records: {result['record_count']}",
            f"- Translated records: {result['translated_record_count']}",
            f"- Text range: `{result['text_range']}`",
            f"- Pointer search range: `{result['pointer_search_range']}`",
            f"- Capacity range: {min(capacities)}..{max(capacities)} words",
            "- Every record has exactly one Japanese pointer owner.",
            "",
            "Detailed addresses, hashes, controls, capacities, and English references are",
            "in `localization/epilogue_records.json`.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory Japanese character epilogue records")
    parser.add_argument(
        "--jp-rom",
        type=Path,
        default=Path("roms/original/Langrisser II (Japan).md"),
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("localization/english_dialogue_mapping.json"),
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("localization/epilogue_records.json"),
    )
    parser.add_argument(
        "--translations",
        type=Path,
        default=Path("localization/epilogue_dialogue_ko.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("docs/epilogue_inventory.md"),
    )
    args = parser.parse_args()
    translations = (
        json.loads(args.translations.read_text(encoding="utf-8"))
        if args.translations.exists()
        else None
    )
    result = build_inventory(
        args.jp_rom.read_bytes(),
        json.loads(args.mapping.read_text(encoding="utf-8")),
        translations,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(f"{result['record_count']} epilogue records; {result['translated_record_count']} translated")


if __name__ == "__main__":
    main()
