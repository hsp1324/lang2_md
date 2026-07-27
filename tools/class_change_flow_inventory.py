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
from tools import class_change_inventory as chain_inventory
from tools.run_blastem_sequence import (
    MANUAL_SLOT_COMMANDER_COUNT,
    MANUAL_SLOT_COMMANDER_RECORD_SIZE,
    MANUAL_SLOT_WORK_RAM_SEGMENTS,
)
from tools.verify_class_change_persistence import verify_progress
from tools.verify_natural_class_change_evidence import (
    RuntimeIdentity,
    read_identities,
    verify_all,
)


DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_KOREAN_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
DEFAULT_JSON = ROOT / "localization/class_change_flow_inventory.json"
DEFAULT_MARKDOWN = ROOT / "docs/class_change_flow_inventory.md"

SOURCE_RANGES = (
    (
        "class_application",
        0x01480C,
        0x014D2C,
        "25b205ddb85637f6a9e76f8ecae1f86540aeb13700e957acbc1dbfa28448efc2",
    ),
    (
        "runtime_to_roster",
        0x011C78,
        0x011D7A,
        "e34760c0f8dc90f29130adc14521fc6295477d6521c0ae8eebb6aae748b4c2bd",
    ),
    (
        "runtime_sync_call",
        0x00CEC4,
        0x00CECA,
        "0d8acc27371b7809f2135eb0c49df9a3dd18ed05d1ff47fb4c61d9ff6e10ff68",
    ),
    (
        "roster_to_runtime",
        0x0177D8,
        0x0178F2,
        "a11a7d508860d2b27fed85f071ca794a8371a70670fe94af0c3daaf22630eb54",
    ),
    (
        "manual_save_writer",
        0x01DE40,
        0x01DEB4,
        "6ac1084570252eb82f8e486bb74bfc043726ec8c48409c7a6e8bae9ea987f3e6",
    ),
    (
        "manual_save_reader",
        0x01DEB4,
        0x01DF50,
        "c83bd3f798d95fb8d4be1e52e433daf37375aaa22f9fb71b635672e66cb73fe9",
    ),
    (
        "manual_slot_pointer_table",
        0x01E004,
        0x01E018,
        "55f2372ff6faaa3771f2108844c1eb2a446dd65cc33b40860648235d9369709b",
    ),
    (
        "manual_slot_descriptor",
        0x01E046,
        0x01E05C,
        "3cc7f67f3e37c93927424e379722157840cf6dc2aea22725347d822fed3d4a5d",
    ),
)

SAVE_PROOFS = (
    {
        "transition": "Elwin Fighter 01 -> Lord 04",
        "path": ROOT / "captures/analysis/b213_c1_s01_scenario2_save.sram",
        "commander_id": 1,
        "class_id": 0x04,
        "level": 1,
        "experience": 9,
        "at": 23,
        "df": 18,
        "checksum": 0x211E,
    },
    {
        "transition": "Hein Warlock 03 -> Shaman 0A",
        "path": ROOT / "captures/analysis/b335_c5_s03_scenario2_save.sram",
        "commander_id": 5,
        "class_id": 0x0A,
        "level": 1,
        "experience": 17,
        "at": 23,
        "df": 13,
        "checksum": 0x2330,
    },
    {
        "transition": "Hein Shaman 0A -> Priest 11",
        "path": ROOT / "captures/analysis/b33c_hein_priest_scenario2.sram",
        "commander_id": 5,
        "class_id": 0x11,
        "level": 1,
        "experience": 1,
        "at": 23,
        "df": 14,
        "checksum": 0x457A,
    },
    {
        "transition": "Hein Priest 11 -> Wizard 15",
        "path": ROOT / "captures/analysis/b353_hein_wizard_scenario2.sram",
        "commander_id": 5,
        "class_id": 0x15,
        "level": 1,
        "experience": 9,
        "at": 23,
        "df": 15,
        "checksum": 0xD8C2,
    },
    {
        "transition": "Hein Wizard 15 -> Summoner 28",
        "path": ROOT / "captures/analysis/b36f_hein_summoner_scenario2.sram",
        "commander_id": 5,
        "class_id": 0x28,
        "level": 1,
        "experience": 9,
        "at": 24,
        "df": 16,
        "checksum": 0xF52F,
    },
)

ELWIN_APPLICATION_STATE = (
    ROOT / "captures/analysis/b213_c1_s01_scenario2_save.gst",
    0,
    RuntimeIdentity(0x04, 1, 1, 9),
)
HEIN_APPLICATION_STATE = (
    ROOT / "captures/analysis/b335_c5_s03_scenario2_save.gst",
    1,
    RuntimeIdentity(0x0A, 5, 1, 17),
)


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def be32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def normalized_korean_range(
    source: bytes,
    korean: bytes,
    start: int,
    end: int,
) -> bytes:
    normalized = bytearray(korean[start:end])
    for offset, original_address in builder.SRAM_LONG_PATCHES.items():
        if not start <= offset < end:
            continue
        if offset + 4 > end:
            raise ValueError(
                f"SRAM long patch at 0x{offset:06X} crosses range boundary"
            )
        source_value = be32(source, offset)
        korean_value = be32(korean, offset)
        if source_value != original_address:
            raise ValueError(
                f"source SRAM address changed at 0x{offset:06X}: "
                f"0x{source_value:08X}"
            )
        expected_korean = original_address + builder.SRAM_ADDRESS_DELTA
        if korean_value != expected_korean:
            raise ValueError(
                f"Korean SRAM address mismatch at 0x{offset:06X}: "
                f"0x{korean_value:08X} != 0x{expected_korean:08X}"
            )
        relative = offset - start
        normalized[relative : relative + 4] = source[offset : offset + 4]
    return bytes(normalized)


def verify_source_ranges(source: bytes, korean: bytes) -> list[dict[str, object]]:
    rows = []
    for name, start, end, expected_sha256 in SOURCE_RANGES:
        source_data = source[start:end]
        actual_sha256 = sha256(source_data)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"{name} source range changed: {actual_sha256} "
                f"!= {expected_sha256}"
            )
        normalized = normalized_korean_range(source, korean, start, end)
        if normalized != source_data:
            mismatch = next(
                index
                for index, (old, new) in enumerate(zip(source_data, normalized))
                if old != new
            )
            raise ValueError(
                f"{name} production logic differs from source at "
                f"0x{start + mismatch:06X}"
            )
        rows.append(
            {
                "name": name,
                "start": f"0x{start:06X}",
                "end": f"0x{end:06X}",
                "size": end - start,
                "source_sha256": actual_sha256,
                "production_source_equivalent": True,
            }
        )
    return rows


def verify_semantic_anchors(source: bytes) -> dict[str, object]:
    anchors = {
        0x01480C: bytes.fromhex("41 F9 00 FF 60 3C"),
        0x014812: bytes.fromhex("43 F9 00 05 ED DC"),
        0x014B3A: bytes.fromhex("45 F9 00 08 25 3A"),
        0x014C36: bytes.fromhex("11 40 00 00"),
        0x014C3A: bytes.fromhex("11 7C 00 01 00 2E"),
        0x011C7C: bytes.fromhex("41 F9 00 FF 60 3C"),
        0x011C82: bytes.fromhex("43 F8 A4 CC"),
        0x011C86: bytes.fromhex("70 13"),
        0x011D6C: bytes.fromhex("D0 FC 00 60"),
        0x011D70: bytes.fromhex("51 C8 FF 16"),
        0x00CEC4: bytes.fromhex("4E B9 00 01 1C 78"),
    }
    for offset, expected in anchors.items():
        actual = source[offset : offset + len(expected)]
        if actual != expected:
            raise ValueError(
                f"class-change semantic anchor changed at 0x{offset:06X}"
            )
    return {
        "runtime_record_base": "0xFF603C",
        "runtime_record_count": 20,
        "runtime_record_size": 0x60,
        "persistent_roster_base": "0xFFA4CC",
        "persistent_commander_count": 10,
        "persistent_record_size": 0x18,
        "class_record_table": "0x05EDDC",
        "commander_chain_pointer_table": "0x08253A",
        "selected_class_write": "0x014C36",
        "runtime_to_roster_call": "0x00CEC4",
        "semantic_anchor_count": len(anchors),
    }


def manual_descriptor(source: bytes) -> dict[str, object]:
    cursor = 0x01E046
    segments = []
    while True:
        address = be32(source, cursor)
        cursor += 4
        if address == 0xFFFFFFFF:
            break
        size = int.from_bytes(source[cursor : cursor + 2], "big")
        cursor += 2
        segments.append((address, size))
    expected = tuple(
        ((0xFFFF0000 | address), size)
        for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS
    )
    if tuple(segments) != expected or cursor != 0x01E05C:
        raise ValueError(
            f"manual save descriptor changed: {segments!r} != {expected!r}"
        )

    roster_start = 0xFFFFA4CC
    roster_end = (
        roster_start
        + MANUAL_SLOT_COMMANDER_COUNT * MANUAL_SLOT_COMMANDER_RECORD_SIZE
    )
    containing = [
        (address, size)
        for address, size in segments
        if address <= roster_start and roster_end <= address + size
    ]
    if containing != [(0xFFFFA49C, 0x154)]:
        raise ValueError("persistent commander roster is not wholly saved")
    return {
        "descriptor": "0x01E046",
        "segments": [
            {
                "work_ram_address": f"0x{address:08X}",
                "size": size,
            }
            for address, size in segments
        ],
        "persistent_roster_start": f"0x{roster_start:08X}",
        "persistent_roster_end": f"0x{roster_end:08X}",
        "persistent_roster_size": roster_end - roster_start,
        "roster_wholly_inside_first_segment": True,
    }


def verify_application_evidence() -> dict[str, object]:
    paired = verify_all()
    snapshot_rows = []
    for path, record, expected in (
        ELWIN_APPLICATION_STATE,
        HEIN_APPLICATION_STATE,
    ):
        actual = read_identities(path.read_bytes())[record]
        if actual != expected:
            raise ValueError(
                f"application snapshot mismatch in {path}: "
                f"{actual!r} != {expected!r}"
            )
        snapshot_rows.append(
            {
                "path": str(path.relative_to(ROOT)),
                "runtime_record": record,
                "class_id": expected.class_id,
                "commander_id": expected.commander_id,
                "level": expected.level,
                "experience": expected.experience,
            }
        )
    return {
        "paired_before_after_proof_count": len(paired),
        "paired_commanders": [proof.character for proof in paired],
        "single_after_snapshot_count": len(snapshot_rows),
        "single_after_snapshots": snapshot_rows,
        "representative_commander_count": len(paired) + len(snapshot_rows),
    }


def verify_save_evidence() -> list[dict[str, object]]:
    rows = []
    for proof in SAVE_PROOFS:
        progress = verify_progress(
            proof["path"],
            slot_index=0,
            commander_id=proof["commander_id"],
            expected_scenario=2,
            expected_class=proof["class_id"],
            expected_level=proof["level"],
            expected_experience=proof["experience"],
            expected_at=proof["at"],
            expected_df=proof["df"],
            expected_checksum=proof["checksum"],
        )
        if progress["checksum"] != progress["calculated_checksum"]:
            raise ValueError(f"invalid checksum in {proof['path']}")
        rows.append(
            {
                "transition": proof["transition"],
                "path": str(proof["path"].relative_to(ROOT)),
                **progress,
            }
        )
    return rows


def inventory(source: bytes, korean: bytes) -> dict[str, object]:
    chains = chain_inventory.inventory(source)
    ranges = verify_source_ranges(source, korean)
    anchors = verify_semantic_anchors(source)
    descriptor = manual_descriptor(source)
    applications = verify_application_evidence()
    saves = verify_save_evidence()

    if chains["transition_count"] != 100:
        raise ValueError("source class-change transition count changed")
    if (
        chains["live_verified_unique_transition_count"]
        != chains["unique_transition_count"]
    ):
        raise ValueError("not every unique class-change screen is live verified")
    if applications["representative_commander_count"] != 10:
        raise ValueError("natural application proof is missing for a commander")
    if len(saves) != 5:
        raise ValueError("expected five ordinary save-persistence artifacts")

    return {
        "scope": {
            "source_transition_count": chains["transition_count"],
            "unique_screen_combination_count": chains["unique_transition_count"],
            "live_verified_source_row_count": chains[
                "live_verified_transition_count"
            ],
            "live_verified_unique_screen_count": chains[
                "live_verified_unique_transition_count"
            ],
            "representative_natural_application_commander_count": applications[
                "representative_commander_count"
            ],
            "ordinary_save_persistence_proof_count": len(saves),
            "structurally_covered_application_transition_count": chains[
                "transition_count"
            ],
            "structurally_covered_persistence_transition_count": chains[
                "transition_count"
            ],
        },
        "conclusion": (
            "All 100 source transitions share the source-locked production "
            "application, runtime-roster synchronization, and manual-save "
            "path. This is structural coverage, not a claim that every branch "
            "was naturally played and saved."
        ),
        "source_locked_ranges": ranges,
        "control_flow": anchors,
        "manual_save_descriptor": descriptor,
        "natural_application_evidence": applications,
        "ordinary_save_evidence": saves,
    }


def markdown_report(result: dict[str, object]) -> str:
    scope = result["scope"]
    lines = [
        "# Class-Change Application And Persistence Inventory",
        "",
        "Generated by `python3 tools/class_change_flow_inventory.py`.",
        "",
        "## Coverage",
        "",
        f"- Source transitions: {scope['source_transition_count']}/100",
        "- Live candidate screens: "
        f"{scope['live_verified_unique_screen_count']}/"
        f"{scope['unique_screen_combination_count']} unique combinations "
        f"({scope['live_verified_source_row_count']} source rows)",
        "- Representative natural application: "
        f"{scope['representative_natural_application_commander_count']}/10 "
        "player commanders",
        "- Ordinary Scenario 2 save artifacts: "
        f"{scope['ordinary_save_persistence_proof_count']}",
        "- Structurally covered application and persistence paths: "
        f"{scope['structurally_covered_application_transition_count']}/100",
        "",
        result["conclusion"],
        "",
        "## Source-Locked Control Flow",
        "",
        "| Range | Address | Bytes | Production |",
        "| --- | --- | ---: | --- |",
    ]
    for row in result["source_locked_ranges"]:
        lines.append(
            f"| {row['name']} | `{row['start']}..{row['end']}` | "
            f"{row['size']} | source-equivalent |"
        )
    lines.extend(
        [
            "",
            "The production comparison normalizes only the declared "
            "`+0x200000` SRAM absolute-address relocation. Every other byte "
            "in these ranges must match the Japanese source.",
            "",
            "The stock handler reads commander ID and current class from the "
            "20-record runtime array, follows the commander chain table at "
            "`0x08253A`, writes the selected class at `0x014C36`, resets LV to "
            "1, and applies class stats and mercenary unlocks. Routine "
            "`0x011C78` then copies eligible runtime records into the ten "
            "persistent `0x18`-byte roster records through one generic loop.",
            "",
            "## Manual Save Ownership",
            "",
        ]
    )
    descriptor = result["manual_save_descriptor"]
    for segment in descriptor["segments"]:
        lines.append(
            f"- `{segment['work_ram_address']}` + "
            f"`0x{segment['size']:X}` bytes"
        )
    lines.extend(
        [
            "",
            "The complete persistent roster "
            f"`{descriptor['persistent_roster_start']}.."
            f"{descriptor['persistent_roster_end']}` "
            f"({descriptor['persistent_roster_size']} bytes) is inside the "
            "first descriptor segment. The same descriptor drives the stock "
            "save writer and checksum-checked load reader.",
            "",
            "## Retained Runtime Evidence",
            "",
            "Eight commanders have controlled same-ROM before/after GST "
            "pairs. Elwin and Hein have exact runtime identities in tracked "
            "ordinary Scenario 2 save GSTs, giving one natural application "
            "proof for every player commander.",
            "",
            "## Ordinary Save Evidence",
            "",
            "| Transition | Class | LV | EXP | AT | DF | Checksum |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in result["ordinary_save_evidence"]:
        lines.append(
            f"| {row['transition']} | `{row['class_id']:02X}` | "
            f"{row['level']} | {row['experience']} | {row['at']} | "
            f"{row['df']} | `{row['checksum']:04X}` |"
        )
    lines.extend(
        [
            "",
            "These five SRAM files came from the ordinary Scenario 1 result, "
            "SAVE, and Scenario 2 slot path. They exercise five distinct "
            "transitions through Hein's Summoner branch plus Elwin's initial "
            "branch. The generic source-locked writer proves ownership for the "
            "remaining transition results; it does not replace screen evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the shared class-change application, synchronization, "
            "and save-persistence control flow"
        )
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
        f"{scope['source_transition_count']} source transitions, "
        f"{scope['live_verified_unique_screen_count']} unique screens, "
        f"{scope['representative_natural_application_commander_count']} "
        "commanders, "
        f"{scope['ordinary_save_persistence_proof_count']} saves verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
