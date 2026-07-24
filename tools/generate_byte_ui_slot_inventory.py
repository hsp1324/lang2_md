#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT = ROOT / "localization/byte_ui_slot_inventory.json"


def hex_word(value: int) -> str:
    return f"0x{value:04X}"


def build_inventory(source_rom: bytes) -> dict[str, object]:
    data = bytearray(source_rom)
    builder.expand_rom(data)
    code_by_char = builder.patch_byte_ui_strings(data)
    index_by_char, tile_by_index = builder.build_byte_ui_local_mapping(code_by_char)
    char_by_index = {index: char for char, index in index_by_char.items()}
    active_char_by_tile = {
        tile_by_index[index]: char_by_index[index]
        for index in range(len(tile_by_index))
    }
    stable_char_by_tile = {
        tile: char
        for char, tile in builder.BYTE_UI_BATTLE_STABLE_FULL_EXT_TILE_BY_CHAR.items()
    }
    retired_char_by_tile = {
        tile: char
        for char, tile in builder.BYTE_UI_RETIRED_FULL_EXT_TILE_BY_STABLE_CHAR.items()
    }
    extension_tiles = [
        tile
        for start, count in builder.BYTE_UI_FULL_EXT_VRAM_SEGMENTS
        for tile in range(start, start + count)
    ]

    local_indexes = []
    for index, tile in enumerate(tile_by_index):
        char = char_by_index[index]
        code = code_by_char.get(char)
        if char == " ":
            allocation = "space"
        elif char in builder.BYTE_UI_BATTLE_STABLE_FULL_EXT_TILE_BY_CHAR:
            allocation = "battle_stable"
        elif code is not None:
            allocation = (
                "escape_code"
                if builder.BYTE_UI_EXT_CODE_FIRST
                <= code
                <= builder.BYTE_UI_EXT_CODE_LAST
                else "base_byte_code"
            )
        else:
            allocation = "extension"
        local_indexes.append(
            {
                "local_index": f"0x{index:02X}",
                "char": char,
                "vram_tile": hex_word(tile),
                "allocation": allocation,
                "byte_code": None if code is None else f"0x{code:02X}",
            }
        )

    extension_slots = []
    for tile in extension_tiles:
        if tile in active_char_by_tile:
            status = "active"
            char = active_char_by_tile[tile]
            reason = (
                "explicit battle-stable assignment"
                if tile in stable_char_by_tile
                else "ordered extension allocation"
            )
        elif tile in retired_char_by_tile:
            status = "retired_unsafe"
            char = retired_char_by_tile[tile]
            reason = builder.BYTE_UI_RETIRED_FULL_EXT_TILE_REASON[tile]
        else:
            status = "unassigned"
            char = None
            reason = "available only after runtime ownership is verified"
        extension_slots.append(
            {
                "vram_tile": hex_word(tile),
                "status": status,
                "char": char,
                "reason": reason,
            }
        )

    return {
        "format": 1,
        "description": (
            "Deterministic inventory of the byte-UI local indexes and VRAM "
            "tiles. Unassigned does not mean safe until live ownership is verified."
        ),
        "local_index_count": len(local_indexes),
        "extension_capacity": len(extension_tiles),
        "extension_segments": [
            {"start": hex_word(start), "count": count}
            for start, count in builder.BYTE_UI_FULL_EXT_VRAM_SEGMENTS
        ],
        "local_indexes": local_indexes,
        "extension_slots": extension_slots,
        "unsafe_byte_codes": [
            {"byte_code": f"0x{code:02X}", "reason": reason}
            for code, reason in sorted(builder.BYTE_UI_UNSAFE_CODE_REASON.items())
        ],
        "dynamic_map_cache_tiles": [
            hex_word(tile) for tile in builder.BYTE_UI_DYNAMIC_TILE_IDS
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic byte-UI glyph/tile ownership inventory"
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(args.source_rom.read_bytes())
    rendered = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale byte-UI slot inventory: {args.output}")
        print(f"byte-UI slot inventory is current: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(
        f"wrote {inventory['local_index_count']} local indexes and "
        f"{inventory['extension_capacity']} extension slots to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
