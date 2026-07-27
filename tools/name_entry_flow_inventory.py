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


DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_KOREAN_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
DEFAULT_JSON = ROOT / "localization/name_entry_flow_inventory.json"
DEFAULT_MARKDOWN = ROOT / "docs/name_entry_flow_inventory.md"

SOURCE_REFERENCES = {
    0x02ABF8: bytes.fromhex("45 F9 00 0A 38 E0"),
    0x02AC0E: bytes.fromhex("41 F9 00 0A 37 BE"),
    0x02AC22: bytes.fromhex("41 F9 00 0A 38 A6"),
    0x02AC3E: bytes.fromhex("41 F9 00 0A 3B 0C"),
    0x02AC52: bytes.fromhex("41 F9 00 0A 37 E6"),
    0x02B060: bytes.fromhex("45 F9 00 0A 3B 3E"),
    0x02B4BE: bytes.fromhex("45 F9 00 0A 3B B0"),
    0x02B67A: bytes.fromhex("41 F9 00 0A 3B B0"),
    0x02B68E: bytes.fromhex("41 F9 00 0A 3B C0"),
}

SOURCE_RANGES = (
    (
        "selectable_glyph_list",
        builder.NAME_ENTRY_GLYPH_LIST,
        builder.NAME_ENTRY_GLYPH_LIST
        + builder.NAME_ENTRY_GLYPH_COUNT * 2
        + 2,
        "0cc6a50297cf8cc222ebaefb73053b62e90479b4b05a2ef311a39ea5b372331b",
    ),
    (
        "screen_layout",
        builder.NAME_ENTRY_LAYOUT,
        builder.NAME_ENTRY_LAYOUT_END,
        builder.NAME_ENTRY_LAYOUT_SHA256,
    ),
    (
        "default_name_buffer",
        builder.NAME_ENTRY_DEFAULT_WORD_OFFSET,
        builder.NAME_ENTRY_DEFAULT_WORD_OFFSET
        + builder.NAME_ENTRY_DEFAULT_COPY_WORDS * 2,
        "c073d03089c690e53530eabc2842bc02d84f6d6082e33987b7a35b487e52ef7d",
    ),
    (
        "selection_to_byte_table",
        builder.NAME_ENTRY_BYTE_VALUE_TABLE,
        builder.NAME_ENTRY_BYTE_VALUE_TABLE + builder.NAME_ENTRY_GLYPH_COUNT,
        builder.NAME_ENTRY_BYTE_VALUE_SHA256,
    ),
    (
        "confirmation_copy_hook",
        builder.NAME_ENTRY_CONFIRM_COPY_HOOK,
        builder.NAME_ENTRY_CONFIRM_COPY_HOOK
        + len(builder.NAME_ENTRY_CONFIRM_COPY_ORIGINAL),
        "c6a4d632a185a672fc1ee21ac90ddd1599219fd9e97df84e8c461c890ab8315c",
    ),
)

REPRESENTATIVE_NAMES = (
    "엘윈",
    "리아나",
    "헤인",
    "레온",
    "베른하르트",
    "에그베르트",
    "발드",
    "레스터",
)

LIVE_EVIDENCE = (
    {
        "role": "production-safe 57-syllable grid and default name",
        "path": "captures/run/0267_name_entry.png",
    },
    {
        "role": "default-name confirmation",
        "path": "captures/run/0267_name_confirm.png",
    },
    {
        "role": "confirmed name carried into route screen",
        "path": "captures/run/0267_name_confirm_route.png",
    },
    {
        "role": "extended word-font build retained the grid",
        "path": "captures/run/69d4_name_entry.png",
    },
    {
        "role": "extended word-font build retained confirmation",
        "path": "captures/run/69d4_name_confirm.png",
    },
    {
        "role": "index-to-glyph hook carried a manually selected custom name",
        "path": "captures/run/0e8a_pol_dialogue_3.png",
        "historical_palette": True,
    },
)


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def be16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def source_locks(source: bytes) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    references = []
    for offset, expected in SOURCE_REFERENCES.items():
        actual = source[offset : offset + len(expected)]
        if actual != expected:
            raise ValueError(f"name-entry source reference changed at 0x{offset:06X}")
        references.append(
            {
                "offset": f"0x{offset:06X}",
                "bytes": expected.hex(" ").upper(),
                "verified": True,
            }
        )

    ranges = []
    for name, start, end, expected_hash in SOURCE_RANGES:
        actual_hash = sha256(source[start:end])
        if actual_hash != expected_hash:
            raise ValueError(
                f"name-entry {name} source range changed: "
                f"{actual_hash} != {expected_hash}"
            )
        ranges.append(
            {
                "name": name,
                "start": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "size": end - start,
                "source_sha256": actual_hash,
                "verified": True,
            }
        )
    return references, ranges


def expected_structure(source: bytes) -> tuple[bytes, dict[str, int]]:
    expected = bytearray(source)
    builder.expand_rom(expected)
    builder.install_blank_custom_space(expected)
    scratch_glyphs = builder.install_custom_glyphs(
        expected,
        builder.collect_chars(builder.NAME_ENTRY_GRID_CHARS),
    )
    byte_codes = builder.patch_byte_ui_strings(expected)
    builder.patch_name_entry_grid(expected, scratch_glyphs, byte_codes)
    return bytes(expected), byte_codes


def verify_structure(
    source: bytes,
    korean: bytes,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    expected, byte_codes = expected_structure(source)
    regions = (
        (
            "default_name_buffer",
            builder.NAME_ENTRY_DEFAULT_WORD_OFFSET,
            builder.NAME_ENTRY_DEFAULT_COPY_WORDS * 2,
        ),
        (
            "screen_layout",
            builder.NAME_ENTRY_LAYOUT,
            builder.NAME_ENTRY_LAYOUT_END - builder.NAME_ENTRY_LAYOUT,
        ),
        (
            "selection_to_byte_table",
            builder.NAME_ENTRY_BYTE_VALUE_TABLE,
            builder.NAME_ENTRY_GLYPH_COUNT,
        ),
        (
            "confirmation_hook",
            builder.NAME_ENTRY_CONFIRM_COPY_HOOK,
            len(builder.NAME_ENTRY_CONFIRM_COPY_ORIGINAL),
        ),
        (
            "confirmation_routine",
            builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE,
            len(builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE_BYTES),
        ),
    )
    region_rows = []
    for name, offset, size in regions:
        exact = korean[offset : offset + size] == expected[offset : offset + size]
        if not exact:
            raise ValueError(f"name-entry {name} differs from the builder contract")
        region_rows.append(
            {
                "name": name,
                "offset": f"0x{offset:06X}",
                "size": size,
                "builder_exact": True,
            }
        )

    glyph_ids = [
        be16(korean, builder.NAME_ENTRY_GLYPH_LIST + index * 2)
        for index in range(builder.NAME_ENTRY_GLYPH_COUNT)
    ]
    terminator = be16(
        korean,
        builder.NAME_ENTRY_GLYPH_LIST + builder.NAME_ENTRY_GLYPH_COUNT * 2,
    )
    if terminator != 0xFFFF:
        raise ValueError("name-entry glyph list terminator changed")

    used_indexes = set(builder.NAME_ENTRY_GRID_INDICES)
    if 70 in used_indexes or builder.SPACE_GLYPH in used_indexes:
        raise ValueError("name-entry reserved indexes were reused")
    for index, glyph_id in enumerate(glyph_ids):
        if index not in used_indexes and glyph_id != builder.SPACE_GLYPH:
            raise ValueError(f"name-entry unused index {index} is not blank")

    font = builder.ImageFont.truetype(str(ROOT / builder.FONT_PATH), 16)
    blank_offset = builder.glyph_data_offset(builder.SPACE_GLYPH)
    blank = source[blank_offset : blank_offset + builder.GLYPH_BYTES]
    glyph_rows = []
    for index, char in zip(
        builder.NAME_ENTRY_GRID_INDICES,
        builder.NAME_ENTRY_GRID_CHARS,
    ):
        glyph_id = glyph_ids[index]
        if glyph_id > builder.NAME_ENTRY_MAX_SAFE_CUSTOM_GLYPH:
            raise ValueError(
                f"name-entry glyph for {char!r} exceeds the safe bank: "
                f"0x{glyph_id:04X}"
            )
        start = builder.glyph_data_offset(glyph_id)
        actual_bitmap = korean[start : start + builder.GLYPH_BYTES]
        expected_bitmap = builder.render_hangul_glyph(char, font, blank)
        if actual_bitmap != expected_bitmap:
            raise ValueError(f"name-entry glyph bitmap differs for {char!r}")
        actual_byte = korean[builder.NAME_ENTRY_BYTE_VALUE_TABLE + index]
        if actual_byte != byte_codes[char]:
            raise ValueError(f"name-entry byte mapping differs for {char!r}")
        glyph_rows.append(
            {
                "index": index,
                "syllable": char,
                "glyph_id": f"0x{glyph_id:04X}",
                "byte_code": f"0x{actual_byte:02X}",
                "safe_glyph_bank": True,
                "bitmap_verified": True,
            }
        )

    default_indexes = [
        builder.NAME_ENTRY_GRID_INDICES[
            builder.NAME_ENTRY_GRID_CHARS.index(char)
        ]
        for char in "엘윈"
    ]
    default_words = [
        be16(korean, builder.NAME_ENTRY_DEFAULT_WORD_OFFSET + index * 2)
        for index in range(builder.NAME_ENTRY_DEFAULT_COPY_WORDS)
    ]
    if default_words != [
        *default_indexes,
        *([builder.SPACE_GLYPH] * 6),
    ]:
        raise ValueError("name-entry default buffer no longer encodes 엘윈")

    controls = {
        "maximum_name_syllables": builder.NAME_ENTRY_DEFAULT_COPY_WORDS,
        "blank_delete_index": builder.SPACE_GLYPH,
        "japanese_composite_reserved_index": 70,
        "unused_index_count": builder.NAME_ENTRY_GLYPH_COUNT - len(glyph_rows),
        "unused_indexes_blank": True,
        "glyph_list_terminator": "0xFFFF",
        "confirmation_hook_exact": True,
        "confirmation_routine_exact": True,
    }
    return glyph_rows, {"regions": region_rows, "controls": controls}


def inventory(source: bytes, korean: bytes) -> dict[str, object]:
    references, ranges = source_locks(source)
    glyphs, structure = verify_structure(source, korean)

    representative_names = []
    selectable = set(builder.NAME_ENTRY_GRID_CHARS)
    for name in REPRESENTATIVE_NAMES:
        missing = sorted(set(name) - selectable)
        if missing:
            raise ValueError(
                f"representative name {name!r} lost syllables: {missing!r}"
            )
        if len(name) > builder.NAME_ENTRY_DEFAULT_COPY_WORDS:
            raise ValueError(f"representative name {name!r} exceeds the name buffer")
        representative_names.append(
            {
                "name": name,
                "syllable_count": len(name),
                "selectable": True,
            }
        )

    evidence = []
    for row in LIVE_EVIDENCE:
        path = ROOT / str(row["path"])
        if not path.is_file():
            raise ValueError(f"name-entry live evidence is missing: {path}")
        evidence.append({**row, "exists": True})

    scope = {
        "source_input_model": "fixed 95-glyph palette",
        "localized_input_model": "fixed 57-syllable Korean palette",
        "selectable_syllable_count": len(glyphs),
        "unique_selectable_syllable_count": len(
            set(builder.NAME_ENTRY_GRID_CHARS)
        ),
        "maximum_name_syllables": builder.NAME_ENTRY_DEFAULT_COPY_WORDS,
        "source_reference_count": len(references),
        "source_locked_range_count": len(ranges),
        "representative_name_count": len(representative_names),
        "live_evidence_count": len(evidence),
        "arbitrary_hangul_composition_required_for_localization": False,
        "optional_future_extension": (
            "screen-local font paging or a composition engine, without "
            "reusing shared status/icon byte-font codes"
        ),
    }
    complete = (
        scope["selectable_syllable_count"] == 57
        and scope["unique_selectable_syllable_count"] == 57
        and scope["maximum_name_syllables"] == 8
        and all(row["verified"] for row in references)
        and all(row["verified"] for row in ranges)
        and all(row["builder_exact"] for row in structure["regions"])
        and all(row["safe_glyph_bank"] and row["bitmap_verified"] for row in glyphs)
        and all(row["selectable"] for row in representative_names)
        and all(row["exists"] for row in evidence)
    )
    return {
        "scope": scope,
        "complete": complete,
        "acceptance": (
            "The Japanese game provides a fixed character palette rather than "
            "a general text composer. The Korean screen preserves that input, "
            "delete, confirmation, storage, route, and dialogue behavior with "
            "57 production-safe syllables. Arbitrary Hangul composition is an "
            "optional feature, not an untranslated UI surface."
        ),
        "source_references": references,
        "source_locked_ranges": ranges,
        "structure": structure,
        "representative_names": representative_names,
        "glyphs": glyphs,
        "live_evidence": evidence,
    }


def markdown_report(result: dict[str, object]) -> str:
    scope = result["scope"]
    lines = [
        "# Name-Entry Flow Inventory",
        "",
        "Generated by `python3 tools/name_entry_flow_inventory.py`.",
        "",
        result["acceptance"],
        "",
        f"- Source input model: {scope['source_input_model']}",
        f"- Localized input model: {scope['localized_input_model']}",
        f"- Selectable Korean syllables: {scope['selectable_syllable_count']}",
        f"- Maximum stored name length: {scope['maximum_name_syllables']} syllables",
        f"- Source references locked: {scope['source_reference_count']}",
        f"- Source ranges locked: {scope['source_locked_range_count']}",
        f"- Live evidence files: {scope['live_evidence_count']}",
        f"- Flow complete: {result['complete']}",
        "",
        "## Representative Names",
        "",
        "| Name | Syllables | Selectable |",
        "| --- | ---: | --- |",
    ]
    for row in result["representative_names"]:
        lines.append(
            f"| {row['name']} | {row['syllable_count']} | "
            f"{'yes' if row['selectable'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Reserved Controls",
            "",
            "- Index `0x54` remains the engine's blank/delete value.",
            "- Index 70 remains reserved for the original Japanese composite path.",
            "- All non-selectable cells are blank and the glyph list still ends in `FFFF`.",
            "- The confirmation hook converts selection indexes to relocated 16-bit glyph IDs.",
            "",
            "## Optional Future Extension",
            "",
            scope["optional_future_extension"],
            "",
            "Detailed glyph IDs, byte codes, source locks, and evidence paths are in",
            "`localization/name_entry_flow_inventory.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the Japanese-ROM Korean name-entry flow"
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--korean-rom", type=Path, default=DEFAULT_KOREAN_ROM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = inventory(
        args.source_rom.read_bytes(),
        args.korean_rom.read_bytes(),
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    scope = result["scope"]
    print(
        f"{scope['selectable_syllable_count']} syllables, "
        f"{scope['source_reference_count']} references, "
        f"{scope['source_locked_range_count']} ranges verified; "
        f"complete={result['complete']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
