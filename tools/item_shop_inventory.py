#!/usr/bin/env python3
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_item_shop_probe_rom as probe_builder
from tools.jp_global_inventory import decode_cp932, read_ff_string


ITEM_BYTE_POINTER_TABLE = 0x060364
ITEM_BYTE_POINTER_TABLE_END = 0x0603FC
ITEM_PRICE_TABLE = 0x0A1D32
ITEM_PRICE_TABLE_END = 0x0A1D7C
ITEM_ICON_SELECTOR_START = 0x027B44
ITEM_ICON_SELECTOR_END = 0x027B78

ITEM_BYTE_POINTER_TABLE_SHA256 = (
    "c7c28b9ed56ea87441ef1c6899ae691ab3b2508e43c0a52d81b5a56a8b107161"
)
ITEM_PRICE_TABLE_SHA256 = (
    "98146d90d1dfbad83132f85d01a7b04d22076743d38d434a889d458c5412cb17"
)
ITEM_ICON_SELECTOR_SHA256 = (
    "a1240d0083e9471bff109a11789ce58cd8425ccc2a73bf4ba8a20a5b4759ed58"
)


def region_digest(data: bytes, start: int, end: int) -> str:
    return sha256(data[start:end]).hexdigest()


def validate_source(data: bytes) -> list[int]:
    checks = (
        (
            "item byte pointer table",
            ITEM_BYTE_POINTER_TABLE,
            ITEM_BYTE_POINTER_TABLE_END,
            ITEM_BYTE_POINTER_TABLE_SHA256,
        ),
        (
            "item price table",
            ITEM_PRICE_TABLE,
            ITEM_PRICE_TABLE_END,
            ITEM_PRICE_TABLE_SHA256,
        ),
        (
            "item icon selector",
            ITEM_ICON_SELECTOR_START,
            ITEM_ICON_SELECTOR_END,
            ITEM_ICON_SELECTOR_SHA256,
        ),
    )
    for label, start, end, expected in checks:
        actual = region_digest(data, start, end)
        if actual != expected:
            raise ValueError(f"{label} changed: expected {expected}, got {actual}")
    return probe_builder.validate_all_item_list(data)


def item_category(item_id: int) -> str:
    if item_id <= 16:
        return "무기"
    if item_id <= 25:
        return "방어구"
    return "장신구"


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    item_ids = validate_source(japanese)
    icon_source = japanese[ITEM_ICON_SELECTOR_START:ITEM_ICON_SELECTOR_END]
    icon_current = korean[ITEM_ICON_SELECTOR_START:ITEM_ICON_SELECTOR_END]
    if icon_current != icon_source:
        raise ValueError("production ROM changed the stock item ID-to-icon selector")
    if len(builder.ITEM_NAME_PATCHES) < len(item_ids):
        raise ValueError("Korean item-name targets do not cover all 37 item IDs")
    if len(builder.ITEM_DESCRIPTION_PATCHES) != len(item_ids):
        raise ValueError("Korean item descriptions do not cover all 37 item IDs")

    rows = []
    for item_id in item_ids:
        pointer = builder.be32(japanese, ITEM_BYTE_POINTER_TABLE + item_id * 4)
        original_name = decode_cp932(read_ff_string(japanese, pointer))
        price_units = builder.be16(japanese, ITEM_PRICE_TABLE + (item_id - 1) * 2)
        icon_vram = 0x4000 + (item_id - 1) * 0x80
        icon_tile = 0x2000 | (icon_vram >> 5)
        rows.append(
            {
                "id": item_id,
                "category": item_category(item_id),
                "original_name": original_name,
                "target_korean": builder.ITEM_NAME_PATCHES[item_id - 1],
                "target_description": builder.ITEM_DESCRIPTION_PATCHES[item_id - 1],
                "price_table_units": price_units,
                "expected_purchase_price_p": None if item_id == 9 else price_units * 10,
                "price_runtime_note": (
                    "stock renderer skips the dynamic price-number call for item ID 9"
                    if item_id == 9
                    else None
                ),
                "icon_vram_address": f"0x{icon_vram:04X}",
                "icon_tile_base": f"0x{icon_tile:04X}",
                "icon_tile_ids": [f"0x{icon_tile + index:04X}" for index in range(4)],
                "runtime_status": "pending",
            }
        )

    return {
        "warning": (
            "Static source ownership and unchanged icon-selection code do not prove "
            "that Korean names, descriptions, prices, or icons render correctly."
        ),
        "complete_secret_shop_list": {
            "mode_value": 2,
            "pointer_table": f"0x{probe_builder.SHOP_LIST_POINTER_TABLE:06X}",
            "list_number": probe_builder.ALL_ITEM_LIST_INDEX + 1,
            "item_ids": item_ids,
        },
        "source_tables": {
            "item_byte_names": f"0x{ITEM_BYTE_POINTER_TABLE:06X}",
            "prices": f"0x{ITEM_PRICE_TABLE:06X}",
            "icon_selector_code": (
                f"0x{ITEM_ICON_SELECTOR_START:06X}..0x{ITEM_ICON_SELECTOR_END - 1:06X}"
            ),
            "icon_formula": "VRAM 0x4000 + (item_id - 1) * 0x80; four 8x8 tiles",
            "production_icon_selector_unchanged": True,
        },
        "runtime_probe": {
            "rom_checksum": "8374",
            "status": "pending",
            "required_review": [
                "target_korean",
                "target_description",
                "expected_purchase_price_p",
                "icon_tile_ids",
            ],
        },
        "items": rows,
    }


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Complete Item Shop Runtime Matrix",
        "",
        "Generated by `python3 tools/item_shop_inventory.py`.",
        "",
        "The original secret shop list 33 contains exact item IDs `1..37`. The",
        "runtime uses each ID directly for its icon at VRAM",
        "`0x4000 + (item_id - 1) * 0x80`. Production keeps that selector code",
        "byte-identical. This matrix remains pending until checksum `8374` is",
        "captured row by row; static ownership is not visual acceptance.",
        "",
        "Price table values are 10P units. Item ID 9 has a stock special case that",
        "skips the dynamic price-number call and must be interpreted from runtime.",
        "",
        "| ID | Type | Original | Korean target | Price | Icon tile | Runtime |",
        "| ---: | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in result["items"]:
        price = (
            "special"
            if row["expected_purchase_price_p"] is None
            else f"{row['expected_purchase_price_p']}P"
        )
        lines.append(
            f"| {row['id']} | {row['category']} | `{row['original_name']}` | "
            f"{row['target_korean']} | {price} | `{row['icon_tile_base']}` | "
            f"{row['runtime_status']} |"
        )
    lines.extend(
        [
            "",
            "Full three-line Korean descriptions, four icon tile IDs, price-table",
            "units, and per-row status are in `localization/item_shop_inventory.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the original-ID complete item shop runtime matrix"
    )
    parser.add_argument(
        "--jp-rom", type=Path,
        default=ROOT / "roms/original/Langrisser II (Japan).md",
    )
    parser.add_argument(
        "--ko-rom", type=Path,
        default=ROOT / "roms/builds/Langrisser II (Korean JP Probe).md",
    )
    parser.add_argument(
        "--json", type=Path,
        default=ROOT / "localization/item_shop_inventory.json",
    )
    parser.add_argument(
        "--markdown", type=Path,
        default=ROOT / "docs/item_shop_runtime_matrix.md",
    )
    args = parser.parse_args()
    result = inventory(args.jp_rom.read_bytes(), args.ko_rom.read_bytes())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(f"{len(result['items'])} complete-secret-shop items; runtime pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
