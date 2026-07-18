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
from tools.jp_epilogue_inventory import read_record


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_INVENTORY = ROOT / "localization/epilogue_records.json"

GROUP_POINTER_TABLE = 0x08916E
NORMAL_CHARACTER_SLOTS = 14
LIANA_POINTER_TABLE = 0x089572
LIANA_RECORD_COUNT = 8
WORLD_POINTER_TABLE = 0x089592
WORLD_RECORD_COUNT = 4
ENDING_CHARACTER_INDEX_INIT = 0x01C7A8
ENDING_CHARACTER_INDEX_CLEAR = bytes.fromhex("4279 FFFF AE90")

# The normal ending selector reads four inclusive stat bounds followed by a
# 32-bit record pointer. These descriptors live only in an ignored probe ROM.
PROBE_DESCRIPTOR_BASE = 0x3FF000
SKIP_DESCRIPTOR = PROBE_DESCRIPTOR_BASE
FORCE_DESCRIPTOR = PROBE_DESCRIPTOR_BASE + 0x10
DESCRIPTOR_RESERVATION_END = PROBE_DESCRIPTOR_BASE + 0x20
ALL_RECORD_STREAM_BASE = 0x3E0000
ALL_RECORD_STREAM_LIMIT = PROBE_DESCRIPTOR_BASE


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def put16(data: bytearray, offset: int, value: int) -> None:
    data[offset : offset + 2] = value.to_bytes(2, "big")


def put32(data: bytearray, offset: int, value: int) -> None:
    data[offset : offset + 4] = value.to_bytes(4, "big")


def load_records(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 90:
        raise ValueError(f"expected 90 epilogue records in {path}")
    return records


def record_index_for_address(records: list[dict[str, object]], address: int) -> int:
    matches = [
        index
        for index, row in enumerate(records)
        if int(str(row["address"]), 16) == address
    ]
    if len(matches) != 1:
        raise ValueError(f"epilogue address 0x{address:06X} has {len(matches)} matches")
    return matches[0]


def character_slot_for_record(index: int) -> int:
    if not 0 <= index < 90:
        raise ValueError(f"epilogue record index outside 0..89: {index}")
    if index < 72:
        return index // 9
    if index < 78:
        return 8 + (index - 72)
    if index < 86:
        return 14
    return 15


def validate_record_source(
    source: bytes,
    row: dict[str, object],
) -> tuple[int, list[int]]:
    address = int(str(row["address"]), 16)
    words = read_record(source, address)
    raw = source[address : address + len(words) * 2]
    actual_hash = hashlib.sha256(raw).hexdigest()
    expected_hash = str(row["source_sha256"])
    if actual_hash != expected_hash:
        raise ValueError(
            f"Japanese source changed at 0x{address:06X}: "
            f"{actual_hash} != {expected_hash}"
        )
    return address, words


def validate_selector_tables(probe: bytes, source: bytes) -> None:
    normal_end = GROUP_POINTER_TABLE + NORMAL_CHARACTER_SLOTS * 4
    if probe[GROUP_POINTER_TABLE:normal_end] != source[GROUP_POINTER_TABLE:normal_end]:
        raise ValueError("input ROM normal epilogue group table differs from Japanese source")
    reserved = probe[PROBE_DESCRIPTOR_BASE:DESCRIPTOR_RESERVATION_END]
    if reserved != b"\xFF" * len(reserved):
        raise ValueError("probe descriptor reservation is not empty")


def install_probe_descriptors(probe: bytearray, record_address: int) -> None:
    # A first bound of FFFF makes the stock routine return without creating a
    # text object. The selected slot instead accepts the full 16-bit range for
    # both stats and returns the requested original record pointer.
    probe[SKIP_DESCRIPTOR : SKIP_DESCRIPTOR + 12] = bytes.fromhex(
        "FFFF 0000 0000 0000 00000000"
    )
    put16(probe, FORCE_DESCRIPTOR + 0, 0x0000)
    put16(probe, FORCE_DESCRIPTOR + 2, 0xFFFF)
    put16(probe, FORCE_DESCRIPTOR + 4, 0x0000)
    put16(probe, FORCE_DESCRIPTOR + 6, 0xFFFF)
    put32(probe, FORCE_DESCRIPTOR + 8, record_address)


def read_relocated_record(probe: bytes | bytearray, address: int) -> list[int]:
    if not builder.EPILOGUE_RELOC_BASE <= address < builder.EPILOGUE_RELOC_LIMIT:
        raise ValueError(f"epilogue record is not relocated: 0x{address:06X}")
    words: list[int] = []
    cursor = address
    while cursor + 2 <= builder.EPILOGUE_RELOC_LIMIT:
        word = builder.be16(probe, cursor)
        words.append(word)
        cursor += 2
        if word == 0xFFFF:
            return words
    raise ValueError(f"unterminated relocated epilogue record at 0x{address:06X}")


def install_all_record_stream(
    probe: bytearray,
    source: bytes,
    records: list[dict[str, object]],
) -> tuple[int, list[dict[str, object]]]:
    if len(records) != 90:
        raise ValueError(f"expected 90 epilogue records, got {len(records)}")
    validate_selector_tables(probe, source)

    stream_words: list[int] = []
    manifest: list[dict[str, object]] = []
    page_cursor = 0
    for index, row in enumerate(records):
        source_address, _ = validate_record_source(source, row)
        pointer_reference = int(str(row["pointer_reference"]), 16)
        if be32(source, pointer_reference) != source_address:
            raise ValueError(
                f"Japanese pointer 0x{pointer_reference:06X} no longer targets "
                f"0x{source_address:06X}"
            )
        relocated_address = be32(probe, pointer_reference)
        words = read_relocated_record(probe, relocated_address)
        page_count = words.count(0xFFFD) + 1
        expected_pages = int(row["page_break_count"]) + 1
        if page_count != expected_pages:
            raise ValueError(
                f"epilogue record {index} page count changed: "
                f"{page_count} != {expected_pages}"
            )
        start_word = len(stream_words)
        stream_words.extend(words[:-1])
        stream_words.append(0xFFFF if index == len(records) - 1 else 0xFFFD)
        manifest.append(
            {
                "record_index": index,
                "source_address": f"0x{source_address:06X}",
                "relocated_address": f"0x{relocated_address:06X}",
                "english_record": int(row["english_record"]),
                "start_page": page_cursor,
                "page_count": page_count,
                "stream_word_offset": start_word,
                "stream_word_count": len(words),
            }
        )
        page_cursor += page_count

    stream = b"".join(word.to_bytes(2, "big") for word in stream_words)
    stream_end = ALL_RECORD_STREAM_BASE + len(stream)
    if stream_end > ALL_RECORD_STREAM_LIMIT:
        raise ValueError(
            f"all-record stream needs 0x{len(stream):X} bytes, exceeds "
            f"0x{ALL_RECORD_STREAM_LIMIT - ALL_RECORD_STREAM_BASE:X}"
        )
    if probe[ALL_RECORD_STREAM_BASE:stream_end] != b"\xFF" * len(stream):
        raise ValueError("all-record stream reservation is not empty")
    probe[ALL_RECORD_STREAM_BASE:stream_end] = stream

    install_probe_descriptors(probe, ALL_RECORD_STREAM_BASE)
    for slot in range(NORMAL_CHARACTER_SLOTS):
        put32(probe, GROUP_POINTER_TABLE + slot * 4, SKIP_DESCRIPTOR)
    put32(probe, GROUP_POINTER_TABLE, FORCE_DESCRIPTOR)
    return page_cursor, manifest


def patch_start_slot(probe: bytearray, source: bytes, start_slot: int | None) -> None:
    if start_slot is None:
        return
    if not 0 <= start_slot <= 15:
        raise ValueError(f"ending start slot outside 0..15: {start_slot}")
    start = ENDING_CHARACTER_INDEX_INIT
    end = start + len(ENDING_CHARACTER_INDEX_CLEAR)
    if source[start:end] != ENDING_CHARACTER_INDEX_CLEAR:
        raise ValueError("Japanese ending character index initializer changed")
    if probe[start:end] != ENDING_CHARACTER_INDEX_CLEAR:
        raise ValueError(
            "input ending character index initializer differs from Japanese source"
        )

    # MOVE.W #slot,$AE90.W. Absolute-short addressing sign-extends AE90 to
    # FFFFAE90 and fits exactly over the stock CLR.W absolute-long instruction.
    probe[start:end] = (
        bytes.fromhex("31FC")
        + start_slot.to_bytes(2, "big")
        + bytes.fromhex("AE90")
    )


def patch_probe(
    probe: bytearray,
    source: bytes,
    index: int,
    row: dict[str, object],
    start_slot: int | None = None,
) -> int:
    source_address, _ = validate_record_source(source, row)
    validate_selector_tables(probe, source)
    pointer_reference = int(str(row["pointer_reference"]), 16)
    if be32(source, pointer_reference) != source_address:
        raise ValueError(
            f"Japanese pointer 0x{pointer_reference:06X} no longer targets "
            f"0x{source_address:06X}"
        )
    address = be32(probe, pointer_reference)
    if not builder.EPILOGUE_RELOC_BASE <= address < builder.EPILOGUE_RELOC_LIMIT:
        raise ValueError(
            f"input epilogue pointer 0x{pointer_reference:06X} is not relocated: "
            f"0x{address:06X}"
        )
    if address + 2 > len(probe) or builder.be16(probe, address) == 0xFFFF:
        raise ValueError(f"input record 0x{address:06X} is unexpectedly empty")

    install_probe_descriptors(probe, address)
    for slot in range(NORMAL_CHARACTER_SLOTS):
        put32(probe, GROUP_POINTER_TABLE + slot * 4, SKIP_DESCRIPTOR)

    character_slot = character_slot_for_record(index)
    if character_slot < NORMAL_CHARACTER_SLOTS:
        put32(
            probe,
            GROUP_POINTER_TABLE + character_slot * 4,
            FORCE_DESCRIPTOR,
        )
    elif character_slot == 14:
        for item in range(LIANA_RECORD_COUNT):
            put32(probe, LIANA_POINTER_TABLE + item * 4, address)
    else:
        for item in range(WORLD_RECORD_COUNT):
            put32(probe, WORLD_POINTER_TABLE + item * 4, address)

    patch_start_slot(probe, source, start_slot)
    return builder.update_md_checksum(probe)


def patch_all_records_probe(
    probe: bytearray,
    source: bytes,
    records: list[dict[str, object]],
) -> tuple[int, int, list[dict[str, object]]]:
    page_count, manifest = install_all_record_stream(probe, source, records)
    checksum = builder.update_md_checksum(probe)
    return checksum, page_count, manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an ignored ROM that forces one record through the stock ending selector"
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--record-index", type=int)
    selection.add_argument("--address", type=lambda value: int(value, 0))
    selection.add_argument(
        "--all-records",
        action="store_true",
        help="concatenate all 90 relocated records for one 515-page renderer pass",
    )
    parser.add_argument(
        "--start-slot",
        type=int,
        choices=range(16),
        metavar="0..15",
        help="start the stock ending loop at one character slot (14=Liana, 15=world)",
    )
    parser.add_argument("--output-rom", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="all-record page manifest (defaults beside the generated probe ROM)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_records(args.inventory)
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    if args.all_records:
        if args.start_slot is not None:
            raise ValueError("--start-slot cannot be combined with --all-records")
        output = args.output_rom or (
            ROOT / "roms/builds/Langrisser II (Epilogue Probe All).md"
        )
        checksum, page_count, manifest = patch_all_records_probe(
            probe, source, records
        )
    else:
        index = (
            args.record_index
            if args.record_index is not None
            else record_index_for_address(records, args.address)
        )
        if not 0 <= index < len(records):
            raise ValueError(f"record index outside 0..{len(records) - 1}: {index}")
        row = records[index]
        address = int(str(row["address"]), 16)
        output = args.output_rom or (
            ROOT / "roms/builds" / f"Langrisser II (Epilogue Probe {index:02d}).md"
        )
        checksum = patch_probe(probe, source, index, row, args.start_slot)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(probe)
    if args.all_records:
        manifest_path = args.manifest or output.with_suffix(".manifest.json")
        manifest_path.write_text(
            json.dumps(
                {
                    "record_count": len(records),
                    "page_count": page_count,
                    "stream_address": f"0x{ALL_RECORD_STREAM_BASE:06X}",
                    "records": manifest,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"all records: {len(records)} / pages: {page_count}")
        print(f"manifest: {manifest_path}")
    else:
        print(f"record {index:02d}: 0x{address:06X} / E{row['english_record']}")
        print(f"ending character slot: {character_slot_for_record(index)}")
        if args.start_slot is not None:
            print(f"ending loop start slot: {args.start_slot}")
    print(f"checksum: {checksum:04X}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
