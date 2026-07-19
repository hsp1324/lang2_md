#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Ending Dialogue Probe All).md"
)
ALL_DIALOGUE_STREAM_BASE = 0x3D0000
ALL_DIALOGUE_STREAM_LIMIT = 0x3E0000


def read_record(
    data: bytes | bytearray,
    start: int,
    limit: int,
) -> list[int]:
    words: list[int] = []
    cursor = start
    while cursor + 2 <= limit:
        word = builder.be16(data, cursor)
        words.append(word)
        cursor += 2
        if word == 0xFFFF:
            return words
    raise ValueError(f"unterminated ending dialogue record at 0x{start:06X}")


def install_all_dialogue_stream(
    probe: bytearray,
    source: bytes,
    rows: list[dict[str, object]],
) -> tuple[int, list[dict[str, object]]]:
    if len(rows) != 23:
        raise ValueError(f"expected 23 ending dialogue records, got {len(rows)}")

    stream_words: list[int] = []
    manifest: list[dict[str, object]] = []
    page_cursor = 0
    for index, row in enumerate(rows):
        source_address = int(row["address_int"])
        pointer_reference = int(row["pointer_reference_int"])
        capacity, original_controls, original_page_breaks = (
            builder.direct_record_layout(source, source_address)
        )
        source_bytes = source[source_address : source_address + capacity * 2]
        if hashlib.sha256(source_bytes).hexdigest() != row["source_sha256"]:
            raise ValueError(
                f"Japanese ending dialogue changed at 0x{source_address:06X}"
            )
        if builder.be32(source, pointer_reference) != source_address:
            raise ValueError(
                f"Japanese pointer 0x{pointer_reference:06X} no longer targets "
                f"0x{source_address:06X}"
            )

        relocated = builder.be32(probe, pointer_reference)
        if not (
            builder.ENDING_DIALOGUE_RELOC_BASE
            <= relocated
            < builder.ENDING_DIALOGUE_RELOC_LIMIT
        ):
            raise ValueError(
                f"input ending dialogue pointer 0x{pointer_reference:06X} "
                f"is not relocated: 0x{relocated:06X}"
            )
        words = read_record(probe, relocated, builder.ENDING_DIALOGUE_RELOC_LIMIT)
        translated_controls = []
        cursor = 0
        while cursor < len(words):
            if words[cursor] == 0xFFF7:
                translated_controls.append((0xFFF7, words[cursor + 1]))
                cursor += 2
            else:
                cursor += 1
        if translated_controls != original_controls:
            raise ValueError(
                f"ending dialogue controls changed at 0x{source_address:06X}"
            )
        page_count = words.count(0xFFFD) + 1
        if page_count != original_page_breaks + 1:
            raise ValueError(
                f"ending dialogue page count changed at 0x{source_address:06X}"
            )

        start_word = len(stream_words)
        stream_words.extend(words[:-1])
        stream_words.append(0xFFFF if index == len(rows) - 1 else 0xFFFD)
        manifest.append(
            {
                "record_index": index,
                "source_address": f"0x{source_address:06X}",
                "pointer_reference": f"0x{pointer_reference:06X}",
                "relocated_address": f"0x{relocated:06X}",
                "english_record": int(row["english_record"]),
                "start_page": page_cursor,
                "page_count": page_count,
                "stream_word_offset": start_word,
                "stream_word_count": len(words),
            }
        )
        page_cursor += page_count

    stream = b"".join(word.to_bytes(2, "big") for word in stream_words)
    stream_end = ALL_DIALOGUE_STREAM_BASE + len(stream)
    if stream_end > ALL_DIALOGUE_STREAM_LIMIT:
        raise ValueError(
            f"ending dialogue stream needs 0x{len(stream):X} bytes, exceeds "
            f"0x{ALL_DIALOGUE_STREAM_LIMIT - ALL_DIALOGUE_STREAM_BASE:X}"
        )
    if probe[ALL_DIALOGUE_STREAM_BASE:stream_end] != b"\xFF" * len(stream):
        raise ValueError("ending dialogue stream reservation is not empty")
    probe[ALL_DIALOGUE_STREAM_BASE:stream_end] = stream
    for row in rows:
        builder.put32(
            probe,
            int(row["pointer_reference_int"]),
            ALL_DIALOGUE_STREAM_BASE,
        )
    return page_cursor, manifest


def patch_probe(
    probe: bytearray,
    source: bytes,
    rows: list[dict[str, object]],
) -> tuple[int, int, list[dict[str, object]]]:
    page_count, manifest = install_all_dialogue_stream(probe, source, rows)
    checksum = builder.update_md_checksum(probe)
    return checksum, page_count, manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored ROM that joins all 23 relocated ending dialogue "
            "records for one stock-renderer pass"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    rows = builder.load_ending_dialogue_translations()
    checksum, page_count, manifest = patch_probe(probe, source, rows)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    manifest_path = args.manifest or args.output_rom.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(
            {
                "record_count": len(rows),
                "page_count": page_count,
                "stream_address": f"0x{ALL_DIALOGUE_STREAM_BASE:06X}",
                "records": manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"ending dialogue records: {len(rows)} / pages: {page_count}")
    print(f"checksum: {checksum:04X}")
    print(f"manifest: {manifest_path}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
