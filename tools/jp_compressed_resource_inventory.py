#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import build_korean_jp_probe as builder


RESOURCE_TABLE = builder.BYTE_UI_FONT_RESOURCE_TABLE
RESOURCE_LOAD_ROUTINE = 0x0099B2
RESOURCE_DISPATCH_ROUTINE = 0x0099FA
RESOURCE_LOOKUP_ROUTINE = 0x009A0E
RESOURCE_DECODER_ROUTINES = {
    0: 0x009A20,
    1: 0x009A38,
    2: 0x009C10,
    3: 0x009DFE,
    4: 0x009AAA,
}
KNOWN_OWNERS = {
    builder.BYTE_UI_FONT_RESOURCE_INDEX: "byte_ui_font",
    391: "item_icons",
    builder.TITLE_LOGO_RESOURCE_INDEX: "title_logo",
}
LIVE_VERIFIED_OWNERS = frozenset(
    {builder.BYTE_UI_FONT_RESOURCE_INDEX, 391, builder.TITLE_LOGO_RESOURCE_INDEX}
)


def be32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def be16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def resource_pointers(data: bytes) -> list[int]:
    first_pointer = be32(data, RESOURCE_TABLE) & 0x00FFFFFF
    table_size = first_pointer - RESOURCE_TABLE
    if table_size <= 0 or table_size % 4:
        raise ValueError(
            f"invalid compressed resource table boundary: 0x{first_pointer:06X}"
        )
    count = table_size // 4
    pointers = [
        be32(data, RESOURCE_TABLE + index * 4) & 0x00FFFFFF
        for index in range(count)
    ]
    if pointers[0] != RESOURCE_TABLE + count * 4:
        raise ValueError("first compressed resource does not immediately follow its table")
    if any(left >= right for left, right in zip(pointers, pointers[1:])):
        raise ValueError("compressed resource pointers are not strictly increasing")
    if pointers[-1] >= len(data):
        raise ValueError("compressed resource table points beyond the ROM")
    return pointers


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resource_output_size(data: bytes, pointer: int) -> int:
    resource_type = data[pointer]
    if resource_type in (1, 3):
        return be16(data, pointer + 1)
    if resource_type == 2:
        header = data[pointer + 1]
        width = header & 0x7F
        length_offset = pointer + 2 + (8 if header & 0x80 else 0)
        encoded_plane_length = be16(data, length_offset)
        return width * encoded_plane_length * 8
    raise ValueError(f"unsupported resource type {resource_type} at 0x{pointer:06X}")


def decompress_type1(data: bytes, pointer: int) -> bytes:
    expected_size = be16(data, pointer + 1)
    pos = pointer + 3
    high_nibble = True
    previous = 0x7F
    nibbles: list[int] = []

    def read_nibble() -> int:
        nonlocal pos, high_nibble
        if high_nibble:
            value = data[pos] >> 4
            high_nibble = False
        else:
            value = data[pos] & 0x0F
            pos += 1
            high_nibble = True
        return value

    while len(nibbles) < expected_size * 2:
        value = read_nibble()
        if value == previous:
            nibbles.extend([previous] * (read_nibble() + 1))
        else:
            previous = value
            nibbles.append(value)
    if len(nibbles) != expected_size * 2:
        raise ValueError(f"type 1 resource at 0x{pointer:06X} overruns its output size")
    return bytes(
        (nibbles[index] << 4) | nibbles[index + 1]
        for index in range(0, len(nibbles), 2)
    )


def decompress_type2(data: bytes, pointer: int) -> bytes:
    header = data[pointer + 1]
    width = header & 0x7F
    if width not in (1, 2, 4):
        raise ValueError(f"unsupported type 2 width {width} at 0x{pointer:06X}")
    pos = pointer + 2
    palette = None
    if header & 0x80:
        palette = []
        for value in data[pos : pos + 8]:
            palette.extend((value >> 4, value & 0x0F))
        pos += 8
    mask_length = be16(data, pos)
    pos += 2
    mask_pos = pos
    mask_end = mask_pos + mask_length
    value_pos = mask_end
    groups_per_tile = {1: 4, 2: 2, 4: 1}[width]
    output = bytearray()

    def shift_word(workspace: bytearray, offset: int) -> int:
        value = (workspace[offset] << 8) | workspace[offset + 1]
        carry = (value >> 15) & 1
        value = (value << 1) & 0xFFFF
        workspace[offset] = value >> 8
        workspace[offset + 1] = value & 0xFF
        return carry

    while mask_pos < mask_end:
        workspace = bytearray()
        for _ in range(groups_per_tile):
            mask = data[mask_pos]
            mask_pos += 1
            for _ in range(8):
                if mask & 0x80:
                    workspace.extend(data[value_pos : value_pos + width])
                    value_pos += width
                else:
                    workspace.extend(bytes(width))
                mask = (mask << 1) & 0xFF
        if len(workspace) != 32:
            raise ValueError(f"type 2 workspace length mismatch at 0x{pointer:06X}")

        for base in range(0, 8, 2):
            if palette is None:
                for _ in range(4):
                    value = 0
                    for _ in range(4):
                        for plane_offset in (24, 8, 16, 0):
                            value = (value << 1) | shift_word(workspace, base + plane_offset)
                    output.extend(value.to_bytes(2, "big"))
            else:
                for _ in range(4):
                    value = 0
                    for _ in range(4):
                        palette_index = 0
                        for plane_offset in (24, 8, 16, 0):
                            palette_index = (
                                (palette_index << 1)
                                | shift_word(workspace, base + plane_offset)
                            )
                        value = (value << 4) | palette[palette_index]
                    output.extend(value.to_bytes(2, "big"))

    expected_size = resource_output_size(data, pointer)
    if len(output) != expected_size:
        raise ValueError(
            f"type 2 resource at 0x{pointer:06X} produced {len(output)}, expected {expected_size}"
        )
    return bytes(output)


def decoded_payload(data: bytes, pointer: int) -> bytes | None:
    resource_type = data[pointer]
    if resource_type == 1:
        return decompress_type1(data, pointer)
    if resource_type == 2:
        return decompress_type2(data, pointer)
    if resource_type == 3:
        return builder.decompress_9dfe(data, pointer + 1)
    return None


def direct_load_calls(data: bytes) -> list[dict[str, object]]:
    jsr = bytes.fromhex("4E B9") + RESOURCE_LOAD_ROUTINE.to_bytes(4, "big")
    calls = []
    offset = 0
    while True:
        call_site = data.find(jsr, offset)
        if call_site < 0:
            return calls
        prefix = data[call_site - 8 : call_site]
        row: dict[str, object] = {
            "call_site": f"0x{call_site:06X}",
            "immediate_resource": False,
            "resource_index": None,
            "raw_resource_id": None,
            "high_bit_flag": None,
            "destination": None,
        }
        if (
            len(prefix) == 8
            and prefix[0:2] == bytes.fromhex("30 3C")
            and prefix[4:6] == bytes.fromhex("32 7C")
        ):
            raw_id = int.from_bytes(prefix[2:4], "big")
            row.update(
                {
                    "immediate_resource": True,
                    "resource_index": raw_id & 0x7FFF,
                    "raw_resource_id": f"0x{raw_id:04X}",
                    "high_bit_flag": bool(raw_id & 0x8000),
                    "destination": f"0x{int.from_bytes(prefix[6:8], 'big'):04X}",
                }
            )
        calls.append(row)
        offset = call_site + 1


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    original_pointers = resource_pointers(japanese)
    count = len(original_pointers)
    calls = direct_load_calls(japanese)
    calls_by_index: dict[int, list[dict[str, object]]] = {}
    for call in calls:
        if call["immediate_resource"]:
            calls_by_index.setdefault(int(call["resource_index"]), []).append(call)
    current_pointers = [
        be32(korean, RESOURCE_TABLE + index * 4) & 0x00FFFFFF
        for index in range(count)
    ]
    entries = []
    type_counts: dict[str, int] = {}
    total_output_bytes = 0
    decoded_counts: dict[str, int] = {}
    for index, (original_pointer, current_pointer) in enumerate(
        zip(original_pointers, current_pointers)
    ):
        original_type = japanese[original_pointer]
        current_type = korean[current_pointer]
        original_size = resource_output_size(japanese, original_pointer)
        current_size = resource_output_size(korean, current_pointer)
        original_payload = decoded_payload(japanese, original_pointer)
        current_payload = decoded_payload(korean, current_pointer)
        original_hash = None if original_payload is None else sha256(original_payload)
        current_hash = None if current_payload is None else sha256(current_payload)
        if original_payload is not None:
            if len(original_payload) != original_size:
                raise ValueError(f"resource {index} output length mismatch")
            type_key = str(original_type)
            decoded_counts[type_key] = decoded_counts.get(type_key, 0) + 1
        if current_payload is not None and len(current_payload) != current_size:
            raise ValueError(f"current resource {index} output length mismatch")
        pointer_modified = original_pointer != current_pointer
        if original_type != current_type or original_size != current_size:
            content_modified: bool | None = True
        elif original_hash is not None and current_hash is not None:
            content_modified = original_hash != current_hash
        elif pointer_modified:
            content_modified = None
        else:
            block_end = (
                original_pointers[index + 1]
                if index + 1 < count
                else len(japanese)
            )
            content_modified = (
                japanese[original_pointer:block_end]
                != korean[original_pointer:block_end]
            )
        type_key = str(original_type)
        type_counts[type_key] = type_counts.get(type_key, 0) + 1
        total_output_bytes += original_size
        entries.append(
            {
                "index": index,
                "table_entry": f"0x{RESOURCE_TABLE + index * 4:06X}",
                "original_pointer": f"0x{original_pointer:06X}",
                "current_pointer": f"0x{current_pointer:06X}",
                "original_type": original_type,
                "current_type": current_type,
                "decoder_routine": f"0x{RESOURCE_DECODER_ROUTINES[original_type]:06X}",
                "original_output_size": original_size,
                "current_output_size": current_size,
                "original_decoded_sha256": original_hash,
                "current_decoded_sha256": current_hash,
                "pointer_modified": pointer_modified,
                "content_modified": content_modified,
                "modified": pointer_modified or content_modified is True,
                "owner": KNOWN_OWNERS.get(index),
                "direct_immediate_call_count": len(calls_by_index.get(index, [])),
                "direct_immediate_calls": calls_by_index.get(index, []),
                "reviewed": index in LIVE_VERIFIED_OWNERS,
                "live_verified": index in LIVE_VERIFIED_OWNERS,
            }
        )
    return {
        "warning": (
            "A valid resource record is not necessarily text or UI. Type 1 RLE, "
            "type 2 tile-plane, and type 3 LZSS records are decoded by this tool. "
            "Ownership is recorded only when established independently."
        ),
        "resource_table": f"0x{RESOURCE_TABLE:06X}",
        "table_end": f"0x{original_pointers[0]:06X}",
        "entry_count": count,
        "type_counts": type_counts,
        "total_original_output_bytes": total_output_bytes,
        "decoded_counts": decoded_counts,
        "modified_count": sum(bool(entry["modified"]) for entry in entries),
        "known_owner_count": sum(entry["owner"] is not None for entry in entries),
        "unknown_owner_count": sum(entry["owner"] is None for entry in entries),
        "loader_routines": {
            "load": f"0x{RESOURCE_LOAD_ROUTINE:06X}",
            "dispatch": f"0x{RESOURCE_DISPATCH_ROUTINE:06X}",
            "lookup": f"0x{RESOURCE_LOOKUP_ROUTINE:06X}",
            "decoders": {
                str(resource_type): f"0x{routine:06X}"
                for resource_type, routine in RESOURCE_DECODER_ROUTINES.items()
            },
        },
        "direct_load_call_count": len(calls),
        "immediate_load_call_count": sum(bool(call["immediate_resource"]) for call in calls),
        "dynamic_load_call_count": sum(not bool(call["immediate_resource"]) for call in calls),
        "immediate_referenced_resource_count": len(calls_by_index),
        "direct_load_calls": calls,
        "entries": entries,
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Compressed Resource Inventory",
        "",
        "Generated by `python3 tools/jp_compressed_resource_inventory.py`.",
        "",
        "The table boundary is derived from its first pointer. All records have a valid",
        "type and output size. Type 1 RLE, type 2 tile-plane, and type 3 `0x9DFE`",
        "records are all decoded and hashed with their format-specific routines.",
        "A valid record does not establish that it contains text or UI data.",
        "",
        f"- Resource table: `{result['resource_table']}`",
        f"- Table end / first resource: `{result['table_end']}`",
        f"- Entries: {result['entry_count']}",
        f"- Total calculated output bytes: {result['total_original_output_bytes']:,}",
        "- Decoded and hashed by type: "
        + ", ".join(
            f"type {resource_type}: {count}"
            for resource_type, count in sorted(result["decoded_counts"].items())
        ),
        f"- Modified resources in current build: {result['modified_count']}",
        f"- Known owners: {result['known_owner_count']}",
        f"- Unknown owners: {result['unknown_owner_count']}",
        f"- Direct loader calls: {result['direct_load_call_count']}",
        f"- Immediate-ID calls: {result['immediate_load_call_count']}",
        f"- Dynamic-ID calls: {result['dynamic_load_call_count']}",
        f"- Resources reached by immediate ID: {result['immediate_referenced_resource_count']}",
        "",
        "## Loader Code",
        "",
        f"- Load wrapper: `{result['loader_routines']['load']}`",
        f"- Type dispatcher: `{result['loader_routines']['dispatch']}`",
        f"- Table lookup: `{result['loader_routines']['lookup']}`",
        "- Decoder routines: "
        + ", ".join(
            f"type {resource_type} `{address}`"
            for resource_type, address in result["loader_routines"]["decoders"].items()
        ),
        "",
        "The lookup routine masks the high flag bit, multiplies the remaining ID by four,",
        "and reads `0x0B0000[index]`. Immediate calls are linked to resource entries; dynamic",
        "calls remain listed by code address without a guessed resource owner.",
        "",
        "## Type Distribution",
        "",
        "| Type byte | Entries |",
        "| ---: | ---: |",
    ]
    for resource_type, count in sorted(
        result["type_counts"].items(), key=lambda item: int(item[0])
    ):
        lines.append(f"| `0x{int(resource_type):02X}` | {count} |")
    lines.extend(
        [
            "",
            "## Known And Modified Resources",
            "",
            "| Index | Owner | Original | Current | Type | Size | Pointer changed | Content changed |",
            "| ---: | --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    selected = [
        entry
        for entry in result["entries"]
        if entry["owner"] is not None or entry["modified"]
    ]
    for entry in selected:
        lines.append(
            f"| {entry['index']} | {entry['owner'] or ''} | `{entry['original_pointer']}` | "
            f"`{entry['current_pointer']}` | `0x{entry['original_type']:02X}` | "
            f"{entry['original_output_size']} | {entry['pointer_modified']} | "
            f"{entry['content_modified']} |"
        )
    lines.extend(
        [
            "",
            "All pointers, output sizes, decoded hashes, ownership fields, and review flags",
            "are in `localization/compressed_resources.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory the typed compressed resource table")
    parser.add_argument("--jp-rom", type=Path, default=Path("roms/original/Langrisser II (Japan).md"))
    parser.add_argument(
        "--ko-rom",
        type=Path,
        default=Path("roms/builds/Langrisser II (Korean JP Probe).md"),
    )
    parser.add_argument("--json", type=Path, default=Path("localization/compressed_resources.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/compressed_resource_inventory.md"))
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['entry_count']} resources inventoried; "
        f"{sum(result['decoded_counts'].values())} decoded; "
        f"{result['modified_count']} modified; {result['unknown_owner_count']} owners unknown"
    )


if __name__ == "__main__":
    main()
