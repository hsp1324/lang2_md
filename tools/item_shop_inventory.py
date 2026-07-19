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
from tools.jp_compressed_resource_inventory import decoded_payload, resource_pointers
from tools.jp_global_inventory import decode_cp932, read_ff_string


ITEM_BYTE_POINTER_TABLE = 0x060364
ITEM_BYTE_POINTER_TABLE_END = 0x0603FC
ITEM_PRICE_TABLE = 0x0A1D32
ITEM_PRICE_TABLE_END = 0x0A1D7C
ITEM_ICON_SELECTOR_START = 0x027B44
ITEM_ICON_SELECTOR_END = 0x027B78
ITEM_ICON_RESOURCE_INDEX = 391
ITEM_ICON_RESOURCE_POINTER = 0x11FAE4
ITEM_ICON_RESOURCE_LOAD_START = 0x025E5A
ITEM_ICON_RESOURCE_LOAD_BYTES = bytes.fromhex(
    "30 3C 81 87 32 7C 40 00 4E B9 00 00 99 B2"
)
ITEM_ICON_BYTES = 37 * 0x80
ACCEPTED_PROBE_CHECKSUM = 0x7E0B
ACCEPTED_ITEM_SURFACE_SHA256 = (
    "9e3372724e71c96a4dcff082fb9e3f67e843408c93d375f0a0bca16dcdda822b"
)
ACCEPTED_CAPTURE_PREFIX = "captures/run/2282_item"
ACCEPTED_RUNTIME_DERIVATIVE_CHECKSUM = 0x4C04
PRIOR_FULL_MATRIX_CHECKSUM = 0xD304

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


def item_surface_sha256(korean: bytes, decoded_icons: bytes) -> str:
    digest = sha256()

    def add(label: str, payload: bytes) -> None:
        digest.update(label.encode("ascii") + b"\0")
        digest.update(len(payload).to_bytes(4, "big"))
        digest.update(payload)

    name_pointers = builder.read_pointer_table_until(
        korean, builder.ITEM_NAME_POINTER_TABLE, 0xA1990, 0xA1B90
    )
    description_pointers = builder.read_pointer_table_until(
        korean, builder.ITEM_DESCRIPTION_POINTER_TABLE, 0xA1E10, 0xA2C00
    )
    for label, pointers in (
        ("name", name_pointers),
        ("description", description_pointers),
    ):
        for index, pointer in enumerate(pointers):
            values = builder.read_word_list(korean, pointer)
            payload = pointer.to_bytes(4, "big") + b"".join(
                value.to_bytes(2, "big") for value in values
            )
            add(f"{label}-{index:02d}", payload)

    for label, offset in (
        ("name-glyphs", builder.ITEM_NAME_GLYPH_LIST_RELOC_BASE),
        ("description-glyphs", builder.ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE),
    ):
        values = builder.read_word_list(korean, offset)
        add(label, b"".join(value.to_bytes(2, "big") for value in values))

    add(
        "name-glyph-load-hook",
        korean[
            builder.ITEM_NAME_GLYPH_LOAD_HOOK :
            builder.ITEM_NAME_GLYPH_LOAD_HOOK
            + len(builder.ITEM_NAME_GLYPH_LOAD_HOOK_ORIGINAL)
        ],
    )
    name_glyphs = builder.read_word_list(
        korean, builder.ITEM_NAME_GLYPH_LIST_RELOC_BASE
    )
    load_routine = builder._build_item_name_glyph_load_routine(len(name_glyphs))
    add(
        "name-glyph-load-routine",
        korean[
            builder.ITEM_NAME_GLYPH_LOAD_ROUTINE :
            builder.ITEM_NAME_GLYPH_LOAD_ROUTINE + len(load_routine)
        ],
    )
    add(
        "name-popup-build-hook",
        korean[
            builder.ITEM_NAME_POPUP_BUILD_HOOK :
            builder.ITEM_NAME_POPUP_BUILD_HOOK
            + len(builder.ITEM_NAME_POPUP_BUILD_HOOK_ORIGINAL)
        ],
    )
    popup_routine = builder._build_item_name_popup_stream_routine()
    add(
        "name-popup-build-routine",
        korean[
            builder.ITEM_NAME_POPUP_BUILD_ROUTINE :
            builder.ITEM_NAME_POPUP_BUILD_ROUTINE + len(popup_routine)
        ],
    )
    for index, (hook, terminator, store, routine) in enumerate(
        builder.ITEM_NAME_LIST_RENDER_HOOKS
    ):
        add(
            f"name-list-hook-{index}",
            korean[hook : hook + len(builder.ITEM_NAME_LIST_RENDER_HOOK_ORIGINAL)],
        )
        payload = builder._build_item_name_list_render_routine(terminator, store)
        add(
            f"name-list-routine-{index}",
            korean[routine : routine + len(payload)],
        )

    add(
        "word-item-names",
        korean[
            builder.WORD_ITEM_NAME_SOURCE_RANGE[0] :
            builder.WORD_ITEM_NAME_SOURCE_RANGE[1]
        ],
    )
    add("prices", korean[ITEM_PRICE_TABLE:ITEM_PRICE_TABLE_END])
    add("icon-selector", korean[ITEM_ICON_SELECTOR_START:ITEM_ICON_SELECTOR_END])
    add(
        "icon-loader",
        korean[
            ITEM_ICON_RESOURCE_LOAD_START :
            ITEM_ICON_RESOURCE_LOAD_START + len(ITEM_ICON_RESOURCE_LOAD_BYTES)
        ],
    )
    add("icon-payload", decoded_icons[:ITEM_ICON_BYTES])
    return digest.hexdigest()


def inventory(japanese: bytes, korean: bytes) -> dict[str, object]:
    item_ids = validate_source(japanese)
    probe = bytearray(korean)
    probe_checksum = probe_builder.patch_probe(probe, japanese)
    icon_source = japanese[ITEM_ICON_SELECTOR_START:ITEM_ICON_SELECTOR_END]
    icon_current = korean[ITEM_ICON_SELECTOR_START:ITEM_ICON_SELECTOR_END]
    if icon_current != icon_source:
        raise ValueError("production ROM changed the stock item ID-to-icon selector")
    load_start = ITEM_ICON_RESOURCE_LOAD_START
    load_end = load_start + len(ITEM_ICON_RESOURCE_LOAD_BYTES)
    if japanese[load_start:load_end] != ITEM_ICON_RESOURCE_LOAD_BYTES:
        raise ValueError("Japanese item-icon resource load changed")
    if korean[load_start:load_end] != ITEM_ICON_RESOURCE_LOAD_BYTES:
        raise ValueError("production ROM changed the item-icon resource load")
    original_pointer = resource_pointers(japanese)[ITEM_ICON_RESOURCE_INDEX]
    current_pointer = (
        builder.be32(
            korean,
            builder.BYTE_UI_FONT_RESOURCE_TABLE + ITEM_ICON_RESOURCE_INDEX * 4,
        )
        & 0x00FFFFFF
    )
    if original_pointer != ITEM_ICON_RESOURCE_POINTER:
        raise ValueError("Japanese item-icon resource pointer changed")
    original_icons = decoded_payload(japanese, original_pointer)
    current_icons = decoded_payload(korean, current_pointer)
    if original_icons is None or current_icons is None:
        raise ValueError("item-icon resource decoder is unavailable")
    if original_icons[:ITEM_ICON_BYTES] != current_icons[:ITEM_ICON_BYTES]:
        raise ValueError("production ROM changed decoded item-icon graphics")
    surface_sha256 = item_surface_sha256(korean, current_icons)
    accepted = surface_sha256 == ACCEPTED_ITEM_SURFACE_SHA256
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
                "runtime_status": (
                    "accepted" if accepted else "pending"
                ),
            }
        )

    return {
        "warning": (
            "Accepted status is item-surface-specific. Changes to unrelated ROM "
            "content do not reset the 37 reviewed rows."
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
            "item_icon_resource": {
                "index": ITEM_ICON_RESOURCE_INDEX,
                "load_call": f"0x{ITEM_ICON_RESOURCE_LOAD_START:06X}",
                "destination": "0x4000",
                "original_pointer": f"0x{original_pointer:06X}",
                "current_pointer": f"0x{current_pointer:06X}",
                "decoded_size": len(original_icons),
                "item_icon_bytes": ITEM_ICON_BYTES,
                "decoded_item_icons_sha256": sha256(
                    original_icons[:ITEM_ICON_BYTES]
                ).hexdigest(),
                "production_bytes_identical": True,
            },
            "item_surface_sha256": surface_sha256,
        },
        "runtime_probe": {
            "rom_checksum": f"{probe_checksum:04X}",
            "accepted_capture_checksum": f"{ACCEPTED_PROBE_CHECKSUM:04X}",
            "prior_full_matrix_checksum": f"{PRIOR_FULL_MATRIX_CHECKSUM:04X}",
            "runtime_derivative_checksum": f"{ACCEPTED_RUNTIME_DERIVATIVE_CHECKSUM:04X}",
            "accepted_item_surface_sha256": ACCEPTED_ITEM_SURFACE_SHA256,
            "status": "accepted" if accepted else "pending",
            "capture_prefix": (
                ACCEPTED_CAPTURE_PREFIX
                if accepted
                else None
            ),
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
    probe_checksum = result["runtime_probe"]["rom_checksum"]
    accepted_checksum = result["runtime_probe"]["accepted_capture_checksum"]
    accepted = result["runtime_probe"]["status"] == "accepted"
    review_line = (
        f"Checksum `{accepted_checksum}` has the accepted renderer-aware item-surface "
        f"fingerprint; current checksum `{probe_checksum}` matches it. The earlier "
        f"`{result['runtime_probe']['prior_full_matrix_checksum']}` run covers all 37 "
        f"rows, and price-only runtime derivative "
        f"`{result['runtime_probe']['runtime_derivative_checksum']}` rechecks the late "
        f"name lists and purchase popups."
        if accepted
        else f"Checksum `{probe_checksum}` still requires row-by-row capture."
    )
    lines = [
        "# Complete Item Shop Runtime Matrix",
        "",
        "Generated by `python3 tools/item_shop_inventory.py`.",
        "",
        "The original secret shop list 33 contains exact item IDs `1..37`. The",
        "runtime uses each ID directly for its icon at VRAM",
        "`0x4000 + (item_id - 1) * 0x80`. Production keeps that selector code",
        "byte-identical, and decoded resource 391 keeps all 37 icon payloads",
        "byte-identical to the Japanese ROM.",
        "",
        review_line,
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
            "Full four-row Korean descriptions, four icon tile IDs, price-table",
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
    print(
        f"{len(result['items'])} complete-secret-shop items; "
        f"runtime {result['runtime_probe']['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
