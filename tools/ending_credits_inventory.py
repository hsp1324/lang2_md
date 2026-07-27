#!/usr/bin/env python3
"""Inventory every translated ending and credits text surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]

ENDING_SLOT_INIT_RANGE = (0x01C718, 0x01C7B8)
ENDING_SLOT_ADVANCE_RANGE = (0x01CF96, 0x01CFBE)
ENDING_CREDIT_DISPATCH_RANGE = (0x01D1C0, 0x01D1EA)
CREDIT_GROUP_RENDERER_RANGE = (0x02A626, 0x02A818)

SOURCE_RANGE_SHA256 = {
    "ending_slot_init": "07b6471ebbf8fb6ba26a92719d623c596d39733751fc140d7e95f46f9dd46fd7",
    "ending_slot_advance": "169e2a3892eea05ab3681ebafc999497d131580362d0a51f9308c95b6cd53f18",
    "ending_credit_dispatch": "7d6443e48d19574faf982cec524126ca0e22b544bb61530acba941e6155d29cc",
    "credit_group_renderer": "7f37e4a065d308e7b42d8a256ae983a39a31282cf19b7b49cc6bc2d45f27ed0b",
}

ENDING_SLOT_COUNT = 16
EXPECTED_EPILOGUE_RECORD_COUNT = 90
EXPECTED_EPILOGUE_PAGE_COUNT = 515
EXPECTED_ENDING_VISIT_RECORD_COUNT = 23
EXPECTED_ENDING_VISIT_PAGE_COUNT = 83
EXPECTED_MONTAGE_RECORD_COUNT = 12


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _range_result(
    japanese: bytes,
    korean: bytes,
    name: str,
    bounds: tuple[int, int],
) -> dict[str, object]:
    start, end = bounds
    source = japanese[start:end]
    expected = SOURCE_RANGE_SHA256[name]
    source_hash = _sha256(source)
    if source_hash != expected:
        raise ValueError(f"{name} source changed: {source_hash} != {expected}")
    return {
        "range": f"0x{start:06X}..0x{end:06X}",
        "source_sha256": source_hash,
        "production_source_identical": korean[start:end] == source,
    }


def _parse_credit_sequences(
    data: bytes,
    table: int,
    count: int,
) -> list[dict[str, object]]:
    sequences: list[dict[str, object]] = []
    for index in range(count):
        address = builder.be32(data, table + index * 4)
        entry_count = builder.be16(data, address)
        entries = []
        for entry_index in range(entry_count):
            offset = address + 2 + entry_index * 6
            entries.append(
                {
                    "record_id": data[offset],
                    "motion": data[offset + 1],
                    "x": builder.be16(data, offset + 2),
                    "y": builder.be16(data, offset + 4),
                }
            )
        sequences.append(
            {
                "index": index,
                "address": f"0x{address:06X}",
                "entries": entries,
            }
        )
    return sequences


def _credit_sequence_inventory(
    japanese: bytes,
    korean: bytes,
) -> dict[str, object]:
    source_sequences = _parse_credit_sequences(
        japanese,
        builder.CREDITS_SEQUENCE_POINTER_TABLE,
        builder.CREDITS_SEQUENCE_COUNT,
    )
    production_sequences = _parse_credit_sequences(
        korean,
        builder.CREDITS_SEQUENCE_RELOC_BASE,
        builder.CREDITS_SEQUENCE_COUNT,
    )
    source_ids = [
        int(entry["record_id"])
        for sequence in source_sequences
        for entry in sequence["entries"]
    ]
    production_ids = [
        int(entry["record_id"])
        for sequence in production_sequences
        for entry in sequence["entries"]
    ]

    if source_ids != list(range(builder.CREDITS_SOURCE_RECORD_COUNT)):
        raise ValueError("source credit sequences do not cover record IDs 0..59 once")
    if production_ids != list(range(builder.CREDITS_RECORD_COUNT)):
        raise ValueError("production credit sequences do not cover record IDs 0..60 once")

    for index, (source, production) in enumerate(
        zip(source_sequences, production_sequences, strict=True)
    ):
        source_entries = source["entries"]
        production_entries = production["entries"]
        if index == builder.CREDITS_SEQUENCE_COUNT - 1:
            if production_entries[:-1] != source_entries:
                raise ValueError("final production credit sequence changed source entries")
            if production_entries[-1] != {
                "record_id": builder.CREDITS_RECORD_COUNT - 1,
                "motion": 1,
                "x": 0x40,
                "y": 0x78,
            }:
                raise ValueError("unexpected localization developer credit entry")
        elif production_entries != source_entries:
            raise ValueError(f"production credit sequence {index} changed")

    return {
        "sequence_count": len(source_sequences),
        "source_record_ids": source_ids,
        "production_record_ids": production_ids,
        "source_records_covered_once": source_ids
        == list(range(builder.CREDITS_SOURCE_RECORD_COUNT)),
        "production_records_covered_once": production_ids
        == list(range(builder.CREDITS_RECORD_COUNT)),
        "final_sequence_record_ids": [
            int(entry["record_id"])
            for entry in production_sequences[-1]["entries"]
        ],
        "sequences": production_sequences,
    }


def _validate_credit_renderer(japanese: bytes, korean: bytes) -> dict[str, object]:
    start, end = CREDIT_GROUP_RENDERER_RANGE
    source = japanese[start:end]
    source_hash = _sha256(source)
    expected = SOURCE_RANGE_SHA256["credit_group_renderer"]
    if source_hash != expected:
        raise ValueError(
            f"credit_group_renderer source changed: {source_hash} != {expected}"
        )

    sequence_hook = (
        bytes.fromhex("43 F9")
        + builder.CREDITS_SEQUENCE_RELOC_BASE.to_bytes(4, "big")
    )
    pointer_hook = (
        bytes.fromhex("41 F9")
        + builder.CREDITS_POINTER_RELOC_BASE.to_bytes(4, "big")
    )
    if korean[
        builder.CREDITS_SEQUENCE_TABLE_HOOK :
        builder.CREDITS_SEQUENCE_TABLE_HOOK + 6
    ] != sequence_hook:
        raise ValueError("production credit sequence-table hook changed")
    if korean[
        builder.CREDITS_POINTER_TABLE_HOOK :
        builder.CREDITS_POINTER_TABLE_HOOK + 6
    ] != pointer_hook:
        raise ValueError("production credit pointer-table hook changed")

    normalized = bytearray(korean[start:end])
    for hook in (
        builder.CREDITS_SEQUENCE_TABLE_HOOK,
        builder.CREDITS_POINTER_TABLE_HOOK,
    ):
        relative = hook - start
        normalized[relative : relative + 6] = japanese[hook : hook + 6]
    if bytes(normalized) != source:
        raise ValueError("production credit renderer changed beyond relocated LEA hooks")

    return {
        "range": f"0x{start:06X}..0x{end:06X}",
        "source_sha256": source_hash,
        "only_relocation_hooks_changed": True,
        "sequence_table_hook": f"0x{builder.CREDITS_SEQUENCE_RELOC_BASE:06X}",
        "pointer_table_hook": f"0x{builder.CREDITS_POINTER_RELOC_BASE:06X}",
    }


def _relocated_dialogue_inventory(
    japanese: bytes,
    korean: bytes,
    rows: list[dict[str, object]],
    translations: list[dict[str, object]],
    expected_count: int,
    expected_pages: int,
    reloc_base: int,
    reloc_limit: int,
) -> dict[str, object]:
    if len(rows) != expected_count or len(translations) != expected_count:
        raise ValueError(
            f"expected {expected_count} dialogue rows, got "
            f"{len(rows)}/{len(translations)}"
        )
    translation_by_address = {
        int(row["address_int"]): row for row in translations
    }
    pointers: list[int] = []
    page_count = 0
    for row in rows:
        address = int(row["address_int"])
        source_capacity, _, source_breaks = builder.direct_record_layout(
            japanese, address
        )
        source = japanese[address : address + source_capacity * 2]
        if _sha256(source) != str(row["source_sha256"]):
            raise ValueError(f"dialogue source hash changed at 0x{address:06X}")
        if address not in translation_by_address:
            raise ValueError(f"missing translated dialogue row at 0x{address:06X}")
        pointer_reference = int(row["pointer_reference_int"])
        pointer = builder.be32(korean, pointer_reference)
        if not reloc_base <= pointer < reloc_limit:
            raise ValueError(
                f"dialogue pointer 0x{pointer_reference:06X} is not relocated"
            )
        _, _, production_breaks = builder.direct_record_layout(korean, pointer)
        if production_breaks != source_breaks:
            raise ValueError(f"dialogue page count changed at 0x{address:06X}")
        pointers.append(pointer)
        page_count += production_breaks + 1

    if pointers != sorted(pointers) or len(pointers) != len(set(pointers)):
        raise ValueError("relocated dialogue pointers are not unique and increasing")
    if page_count != expected_pages:
        raise ValueError(f"dialogue page count changed: {page_count} != {expected_pages}")
    return {
        "record_count": len(rows),
        "page_count": page_count,
        "unique_increasing_relocated_pointers": True,
        "relocation_range": f"0x{reloc_base:06X}..0x{reloc_limit:06X}",
    }


def _runtime_evidence(
    runtime: dict[str, object],
    surface: str,
) -> dict[str, object]:
    rows = [
        row
        for row in runtime["global_evidence"]
        if row.get("surface") == surface
    ]
    if len(rows) != 1:
        raise ValueError(f"expected one runtime evidence row for {surface}")
    row = rows[0]
    if row.get("state") not in {"verified_current", "verified_probe"}:
        raise ValueError(f"runtime evidence for {surface} is not verified")
    missing_captures = [
        capture
        for capture in row["captures"]
        if not (ROOT / str(capture)).is_file()
    ]
    if missing_captures:
        raise ValueError(
            f"runtime evidence for {surface} has missing captures: "
            + ", ".join(str(capture) for capture in missing_captures)
        )
    return {
        "state": row["state"],
        "checksum": row["checksum"],
        "capture_count": len(row["captures"]),
        "captures": row["captures"],
    }


def build_inventory(
    japanese: bytes,
    korean: bytes,
    runtime: dict[str, object],
    ui_inventory: dict[str, object],
) -> dict[str, object]:
    epilogue_rows = builder.load_epilogue_record_inventory()
    epilogue_translations = builder.load_epilogue_dialogue_translations()
    ending_rows = builder.load_ending_dialogue_translations()
    credit_payload = builder.load_credits_translations()

    epilogue = _relocated_dialogue_inventory(
        japanese,
        korean,
        epilogue_rows,
        epilogue_translations,
        EXPECTED_EPILOGUE_RECORD_COUNT,
        EXPECTED_EPILOGUE_PAGE_COUNT,
        builder.EPILOGUE_RELOC_BASE,
        builder.EPILOGUE_RELOC_LIMIT,
    )
    ending_visits = _relocated_dialogue_inventory(
        japanese,
        korean,
        ending_rows,
        ending_rows,
        EXPECTED_ENDING_VISIT_RECORD_COUNT,
        EXPECTED_ENDING_VISIT_PAGE_COUNT,
        builder.ENDING_DIALOGUE_RELOC_BASE,
        builder.ENDING_DIALOGUE_RELOC_LIMIT,
    )

    montage_rows = [
        row
        for row in ui_inventory["declared_patches"]
        if 0x0A6B20 <= int(row["address"], 16) <= 0x0A6F02
    ]
    if len(montage_rows) != EXPECTED_MONTAGE_RECORD_COUNT:
        raise ValueError(f"expected {EXPECTED_MONTAGE_RECORD_COUNT} montage rows")
    if not all(
        row["modified"] and row["reviewed"] and row["live_verified"]
        for row in montage_rows
    ):
        raise ValueError("ending montage rows are not all reviewed and live verified")

    credit_rows = credit_payload["records"]
    if len(credit_rows) != builder.CREDITS_RECORD_COUNT:
        raise ValueError("credit translation record count changed")

    result = {
        "source_rom_sha256": _sha256(japanese),
        "production_rom_sha256": _sha256(korean),
        "ending_slot_count": ENDING_SLOT_COUNT,
        "ending_loop": {
            "slot_initialization": _range_result(
                japanese, korean, "ending_slot_init", ENDING_SLOT_INIT_RANGE
            ),
            "slot_advance": _range_result(
                japanese, korean, "ending_slot_advance", ENDING_SLOT_ADVANCE_RANGE
            ),
            "credit_dispatch": _range_result(
                japanese,
                korean,
                "ending_credit_dispatch",
                ENDING_CREDIT_DISPATCH_RANGE,
            ),
            "fin_requires_all_slots": True,
        },
        "ending_montage": {
            "record_count": len(montage_rows),
            "all_modified_reviewed_live": True,
        },
        "epilogues": epilogue,
        "ending_visits": ending_visits,
        "credits": {
            "source_record_count": builder.CREDITS_SOURCE_RECORD_COUNT,
            "production_record_count": len(credit_rows),
            "sequence_inventory": _credit_sequence_inventory(japanese, korean),
            "renderer": _validate_credit_renderer(japanese, korean),
        },
        "runtime_evidence": {
            "complete_ending_credits": _runtime_evidence(
                runtime, "ending_credits_complete"
            ),
            "ending_visit_dialogue": _runtime_evidence(
                runtime, "ending_visit_dialogue"
            ),
        },
    }
    result["complete"] = all(
        (
            result["ending_loop"]["slot_initialization"][
                "production_source_identical"
            ],
            result["ending_loop"]["slot_advance"]["production_source_identical"],
            result["ending_loop"]["credit_dispatch"]["production_source_identical"],
            result["credits"]["sequence_inventory"][
                "source_records_covered_once"
            ],
            result["credits"]["sequence_inventory"][
                "production_records_covered_once"
            ],
            result["credits"]["renderer"]["only_relocation_hooks_changed"],
            result["ending_montage"]["all_modified_reviewed_live"],
            result["epilogues"]["record_count"]
            == EXPECTED_EPILOGUE_RECORD_COUNT,
            result["ending_visits"]["record_count"]
            == EXPECTED_ENDING_VISIT_RECORD_COUNT,
        )
    )
    return result


def markdown_report(result: dict[str, object]) -> str:
    credits = result["credits"]
    sequences = credits["sequence_inventory"]
    runtime = result["runtime_evidence"]
    return "\n".join(
        [
            "# Ending And Credits Surface Inventory",
            "",
            "Generated by `python3 tools/ending_credits_inventory.py`.",
            "",
            f"- Complete: `{result['complete']}`",
            f"- Ending slots: {result['ending_slot_count']}",
            f"- Source credit records: {credits['source_record_count']}",
            f"- Production credit records: {credits['production_record_count']}",
            f"- Credit sequence groups: {sequences['sequence_count']}",
            "- Credit record coverage: source IDs `0..59` exactly once; "
            "production IDs `0..60` exactly once",
            f"- Outcome epilogues: {result['epilogues']['record_count']} records / "
            f"{result['epilogues']['page_count']} pages",
            f"- Ending visits: {result['ending_visits']['record_count']} records / "
            f"{result['ending_visits']['page_count']} pages",
            f"- Source-reviewed ending montage: "
            f"{result['ending_montage']['record_count']} records",
            "",
            "## Control-Flow Proof",
            "",
            "The source-locked ending loop initializes slot 0, advances exactly one slot",
            "at a time, compares against 16, and dispatches that same slot index to the",
            "credit-group renderer. The terminal path is reachable only after all 16",
            "slots. The 16 source groups reference all 60 original credit records exactly",
            "once. Production changes only the two renderer `LEA` operands that point to",
            "the relocated sequence and string tables; the final group appends record 60,",
            "`한국어화 HSP1324`, after the original copyright record.",
            "",
            "Therefore the accepted Scenario 27 playback reaching `Fin` is evidence that",
            "all 16 credit groups ran, not merely a sample of the final group. The all-record",
            "epilogue and ending-visit probes separately cover all authored text pages through",
            "their stock renderers. Selector conditions choose among already inventoried",
            "records and do not introduce another text store or renderer.",
            "",
            "## Runtime Evidence",
            "",
            f"- Complete ending/credits: `{runtime['complete_ending_credits']['state']}` "
            f"({runtime['complete_ending_credits']['checksum']})",
            f"- Ending visits: `{runtime['ending_visit_dialogue']['state']}` "
            f"({runtime['ending_visit_dialogue']['checksum']})",
            "",
            "This closes the former open-ended ending/credits UI-variant inventory gap.",
            "It does not turn diagnostic scenario placement into an original-balance clear",
            "claim; scenario completion evidence remains classified separately.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory all ending and credits text surfaces"
    )
    parser.add_argument("--jp-rom", type=Path, default=ROOT / builder.IN_ROM)
    parser.add_argument("--ko-rom", type=Path, default=ROOT / builder.OUT_ROM)
    parser.add_argument(
        "--runtime",
        type=Path,
        default=ROOT / "localization/runtime_verification.json",
    )
    parser.add_argument(
        "--ui-inventory",
        type=Path,
        default=ROOT / "localization/ui_patch_surfaces.json",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=ROOT / "localization/ending_credits_inventory.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=ROOT / "docs/ending_credits_inventory.md",
    )
    args = parser.parse_args()

    result = build_inventory(
        args.jp_rom.read_bytes(),
        args.ko_rom.read_bytes(),
        json.loads(args.runtime.read_text(encoding="utf-8")),
        json.loads(args.ui_inventory.read_text(encoding="utf-8")),
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['ending_slot_count']} ending slots; "
        f"{result['epilogues']['record_count']} epilogues; "
        f"{result['ending_visits']['record_count']} ending visits; "
        f"complete={result['complete']}"
    )


if __name__ == "__main__":
    main()
