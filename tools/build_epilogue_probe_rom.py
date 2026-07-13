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

# The normal ending selector reads four inclusive stat bounds followed by a
# 32-bit record pointer. These descriptors live only in an ignored probe ROM.
PROBE_DESCRIPTOR_BASE = 0x3FF000
SKIP_DESCRIPTOR = PROBE_DESCRIPTOR_BASE
FORCE_DESCRIPTOR = PROBE_DESCRIPTOR_BASE + 0x10
DESCRIPTOR_RESERVATION_END = PROBE_DESCRIPTOR_BASE + 0x20


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
    liana_end = LIANA_POINTER_TABLE + LIANA_RECORD_COUNT * 4
    if probe[LIANA_POINTER_TABLE:liana_end] != source[LIANA_POINTER_TABLE:liana_end]:
        raise ValueError("input ROM Liana epilogue table differs from Japanese source")
    world_end = WORLD_POINTER_TABLE + WORLD_RECORD_COUNT * 4
    if probe[WORLD_POINTER_TABLE:world_end] != source[WORLD_POINTER_TABLE:world_end]:
        raise ValueError("input ROM world epilogue table differs from Japanese source")
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


def patch_probe(probe: bytearray, source: bytes, index: int, row: dict[str, object]) -> int:
    address, _ = validate_record_source(source, row)
    validate_selector_tables(probe, source)
    if address + 2 > len(probe):
        raise ValueError(f"record 0x{address:06X} lies outside input ROM")
    if builder.be16(probe, address) == 0xFFFF:
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

    return builder.update_md_checksum(probe)


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
    parser.add_argument("--output-rom", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_records(args.inventory)
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

    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(probe, source, index, row)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(probe)
    print(f"record {index:02d}: 0x{address:06X} / E{row['english_record']}")
    print(f"ending character slot: {character_slot_for_record(index)}")
    print(f"checksum: {checksum:04X}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
