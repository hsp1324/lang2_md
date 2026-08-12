#!/usr/bin/env python3
"""Build the approved Standard Hard ROM without changing the save format."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as korean_builder
from tools import hard_mode_approval
from tools import hard_mode_npc_survival
from tools import rom_update
from tools import scenario_data
from tools.rom_version import get_profile


DEFAULT_OUTPUT = ROOT / "roms/builds" / get_profile("hard")["rom_filename"]
DEFAULT_BUILD_MANIFEST = ROOT / "localization/hard_mode_build.json"
DEFAULT_APPLIED_PLAN = ROOT / "localization/hard_mode_plan.json"

FIXED_RECORD_SIZE = 0x24
SIDE_ID_OFFSET = 0x08
LEVEL_OFFSET = 0x0E
COMMANDER_AT_OFFSET = 0x12
COMMANDER_DF_OFFSET = 0x13
X_OFFSET = 0x18
Y_OFFSET = 0x19
NAME_ID_OFFSET = 0x1A
CLASS_ID_OFFSET = 0x1B
HARD_CORRECTION_INDEX_OFFSET = 0x1D
MERCENARY_OFFSET = 0x1E
MERCENARY_COUNT = 6

SOLDIER_CORRECTION_HOOK = 0x010E90
SOLDIER_CORRECTION_HOOK_SOURCE = bytes.fromhex(
    "13 6A 00 0F 00 46 13 6A 00 10 00 47"
)
SOLDIER_CORRECTION_ROUTINE = 0x300000
SOLDIER_CORRECTION_TABLE = 0x300080
DYNAMIC_NPC_CORRECTION_HOOK = 0x010CFE
DYNAMIC_NPC_CORRECTION_HOOK_SOURCE = bytes.fromhex(
    "4C DF 18 0E 4E 75"
)
DYNAMIC_NPC_CORRECTION_ROUTINE = 0x300120
DYNAMIC_NPC_CORRECTION_TABLE = 0x300160
SOLDIER_CORRECTION_AREA_END = 0x300200


def _signed_byte(value: int) -> int:
    return value if value < 0x80 else value - 0x100


def _encoded_byte(value: int) -> int:
    if not -128 <= value <= 127:
        raise ValueError(f"signed byte value out of range: {value}")
    return value & 0xFF


def correction_routine(table_address: int = SOLDIER_CORRECTION_TABLE) -> bytes:
    """Return a 68000 routine that applies a tagged record correction pair."""
    return (
        bytes.fromhex(
            "2F 00"              # move.l d0,-(sp)
            "2F 0B"              # move.l a3,-(sp)
            "70 00"              # moveq #0,d0
            "10 28 FF FF"        # move.b -1(a0),d0
            "0C 00 00 FF"        # cmpi.b #$ff,d0
            "67 1A"              # beq.b fallback
            "D0 40"              # add.w d0,d0
            "47 F9"
        )
        + table_address.to_bytes(4, "big")
        + bytes.fromhex(
            "13 73 00 00 00 46"  # move.b (a3,d0.w),$46(a1)
            "13 73 00 01 00 47"  # move.b 1(a3,d0.w),$47(a1)
            "26 5F"              # movea.l (sp)+,a3
            "20 1F"              # move.l (sp)+,d0
            "4E 75"              # rts
            "13 6A 00 0F 00 46"  # fallback: class A+
            "13 6A 00 10 00 47"  # fallback: class D+
            "26 5F"
            "20 1F"
            "4E 75"
        )
    )


def correction_hook() -> bytes:
    return (
        bytes.fromhex("4E B9")
        + SOLDIER_CORRECTION_ROUTINE.to_bytes(4, "big")
        + bytes.fromhex("4E 71 4E 71 4E 71")
    )


def dynamic_npc_correction_routine(
    table_address: int = DYNAMIC_NPC_CORRECTION_TABLE,
) -> bytes:
    """Add Hard-only defense deltas after the stock roster rewrite.

    The stock loader takes fixed records whose name ID is playable (1..11)
    through a separate path.  That path preserves the fixed-record tag at
    ``-7(a0)`` but recalculates class, level and combat values from the saved
    roster.  At its epilogue ``a1`` already points one 0x60-byte group beyond
    the rewritten NPC, so only DF/D+ are adjusted relative to that live data.
    """
    return (
        bytes.fromhex(
            "74 00"              # moveq #0,d2
            "14 28 FF F9"        # move.b -7(a0),d2 (record tag)
            "0C 02 00 FF"        # cmpi.b #$ff,d2
            "67 18"              # beq.b restore
            "D4 42"              # add.w d2,d2
            "47 F9"
        )
        + table_address.to_bytes(4, "big")
        + bytes.fromhex(
            "12 33 20 00"        # move.b (a3,d2.w),d1 (DF delta)
            "D3 29 FF DB"        # add.b d1,-$25(a1) (group+$3B)
            "12 33 20 01"        # move.b 1(a3,d2.w),d1 (D+ delta)
            "D3 29 FF E7"        # add.b d1,-$19(a1) (group+$47)
            "4C DF 18 0E"        # stock epilogue: restore d1-d3/a3-a4
            "4E 75"              # rts
        )
    )


def dynamic_npc_correction_hook() -> bytes:
    return bytes.fromhex("4E F9") + DYNAMIC_NPC_CORRECTION_ROUTINE.to_bytes(
        4, "big"
    )


def _planned_records(plan: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    return [
        (int(scenario["number"]), record)
        for scenario in plan["scenarios"]
        for record in scenario["records"]
    ]


def _npc_protection_records(
    plan: dict[str, Any],
) -> list[tuple[int, dict[str, Any]]]:
    section = plan.get("npc_survival_protection", {})
    hard_mode_npc_survival.validate_section(section)
    return list(hard_mode_npc_survival.protection_records(section))


def _correction_pairs(plan: dict[str, Any]) -> list[tuple[int, int]]:
    pairs = {
        (
            int(record["enemy_soldier_correction"]["at"]["planned"]),
            int(record["enemy_soldier_correction"]["df"]["planned"]),
        )
        for _, record in _planned_records(plan)
    }
    pairs.update({
        (
            int(record["soldier_correction"]["at"]),
            int(record["soldier_correction"]["df"]["planned"]),
        )
        for _, record in _npc_protection_records(plan)
    })
    result = sorted(pairs)
    if len(result) >= 0xFF:
        raise ValueError("hard correction table needs more than 254 indexes")
    return result


def _dynamic_npc_delta_table(
    plan: dict[str, Any],
    pairs: list[tuple[int, int]] | None = None,
) -> bytes:
    """Return a tag-indexed table used only by the playable-NPC path."""
    pairs = pairs or _correction_pairs(plan)
    pair_index = {pair: index for index, pair in enumerate(pairs)}
    deltas: dict[int, tuple[int, int]] = {}
    for scenario in plan["npc_survival_protection"]["scenarios"]:
        commander_delta = int(
            scenario["enemy_attack_offset"]["commander_at_delta"]
        )
        soldier_delta = int(
            scenario["enemy_attack_offset"][
                "soldier_at_correction_delta"
            ]
        )
        for record in scenario["records"]:
            if int(str(record["name_id"]), 16) > 0x0B:
                continue
            correction = (
                int(record["soldier_correction"]["at"]),
                int(record["soldier_correction"]["df"]["planned"]),
            )
            index = pair_index[correction]
            delta = (commander_delta, soldier_delta)
            previous = deltas.setdefault(index, delta)
            if previous != delta:
                raise ValueError(
                    "playable NPC correction tag has conflicting deltas: "
                    f"{index}: {previous!r} != {delta!r}"
                )
    table = bytearray(len(pairs) * 2)
    for index, (commander_delta, soldier_delta) in deltas.items():
        table[index * 2:index * 2 + 2] = bytes(
            (_encoded_byte(commander_delta), _encoded_byte(soldier_delta))
        )
    return bytes(table)


def validate_plan_approval(
    plan: dict[str, Any],
    approval: dict[str, Any],
) -> None:
    if approval["status"] != "approved":
        raise PermissionError("hard-mode balance approval is not active")
    if plan["profile_id"] != approval["proposal_id"]:
        raise ValueError("hard-mode plan and approval profile differ")
    if (
        plan["approval"]["proposal_sha256"]
        != approval["proposal_sha256"]
    ):
        raise ValueError("hard-mode plan changed after approval")


def load_applied_plan(path: Path = DEFAULT_APPLIED_PLAN) -> dict[str, Any]:
    """Load the tracked approved plan without requiring an old local ROM."""
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema_version") != 1:
        raise ValueError("unsupported hard-mode plan schema")
    if (
        plan.get("status") != "approved_balance_plan"
        or plan.get("approval", {}).get("status") != "approved"
    ):
        raise ValueError("hard-mode plan is not approved")
    scenarios = plan.get("scenarios", [])
    if [int(row["number"]) for row in scenarios] != list(range(1, 32)):
        raise ValueError("hard-mode plan must contain scenarios 1..31")
    hard_mode_npc_survival.validate_section(
        plan.get("npc_survival_protection", {})
    )
    return plan


def verify_applied_hard_mode(
    payload: bytes,
    plan: dict[str, Any] | None = None,
) -> None:
    """Fail closed unless all approved hard-balance bytes are present."""
    plan = plan or load_applied_plan()
    if payload[
        SOLDIER_CORRECTION_HOOK:
        SOLDIER_CORRECTION_HOOK + len(correction_hook())
    ] != correction_hook():
        raise ValueError("Standard Hard soldier-correction hook is absent")
    routine = correction_routine()
    if payload[
        SOLDIER_CORRECTION_ROUTINE:
        SOLDIER_CORRECTION_ROUTINE + len(routine)
    ] != routine:
        raise ValueError("Standard Hard soldier-correction routine is absent")
    pairs = _correction_pairs(plan)
    table = b"".join(
        bytes((_encoded_byte(at), _encoded_byte(df))) for at, df in pairs
    )
    if payload[
        SOLDIER_CORRECTION_TABLE:
        SOLDIER_CORRECTION_TABLE + len(table)
    ] != table:
        raise ValueError("Standard Hard soldier-correction table differs")
    if payload[
        DYNAMIC_NPC_CORRECTION_HOOK:
        DYNAMIC_NPC_CORRECTION_HOOK
        + len(dynamic_npc_correction_hook())
    ] != dynamic_npc_correction_hook():
        raise ValueError("Hard playable-NPC correction hook is absent")
    dynamic_routine = dynamic_npc_correction_routine()
    if payload[
        DYNAMIC_NPC_CORRECTION_ROUTINE:
        DYNAMIC_NPC_CORRECTION_ROUTINE + len(dynamic_routine)
    ] != dynamic_routine:
        raise ValueError("Hard playable-NPC correction routine is absent")
    dynamic_table = _dynamic_npc_delta_table(plan, pairs)
    if payload[
        DYNAMIC_NPC_CORRECTION_TABLE:
        DYNAMIC_NPC_CORRECTION_TABLE + len(dynamic_table)
    ] != dynamic_table:
        raise ValueError("Hard playable-NPC correction table differs")
    pair_index = {pair: index for index, pair in enumerate(pairs)}
    for scenario_number, record in _planned_records(plan):
        offset = int(str(record["offset"]), 16)
        commander = record["commander"]
        soldier = record["enemy_soldier_correction"]
        expected = {
            "at": _encoded_byte(int(commander["at"]["planned"])),
            "df": _encoded_byte(int(commander["df"]["planned"])),
            "tag": pair_index[(
                int(soldier["at"]["planned"]),
                int(soldier["df"]["planned"]),
            )],
            "mercenaries": bytes(record["mercenaries"]["planned"]),
        }
        actual = {
            "at": payload[offset + COMMANDER_AT_OFFSET],
            "df": payload[offset + COMMANDER_DF_OFFSET],
            "tag": payload[offset + HARD_CORRECTION_INDEX_OFFSET],
            "mercenaries": payload[
                offset + MERCENARY_OFFSET:offset + FIXED_RECORD_SIZE
            ],
        }
        if actual != expected:
            raise ValueError(
                f"Scenario {scenario_number} hard record differs at "
                f"0x{offset:06X}: {actual!r} != {expected!r}"
            )
    for scenario_number, record in _npc_protection_records(plan):
        offset = int(str(record["offset"]), 16)
        layout = scenario_data.scenario_layout(payload, scenario_number)
        indexed_offset = (
            layout.records_offset
            + int(record["index"]) * FIXED_RECORD_SIZE
        )
        if indexed_offset != offset:
            raise ValueError(
                f"Scenario {scenario_number} protected NPC index differs: "
                f"0x{indexed_offset:06X} != 0x{offset:06X}"
            )
        soldier = record["soldier_correction"]
        expected = {
            "side": 0x03,
            "level": int(record["level"]),
            "at": _encoded_byte(int(record["commander_at"])),
            "df": _encoded_byte(int(record["commander_df"]["planned"])),
            "x": int(record["x"]),
            "y": int(record["y"]),
            "name": int(str(record["name_id"]), 16),
            "class": int(str(record["class_id"]), 16),
            "tag": pair_index[(
                int(soldier["at"]),
                int(soldier["df"]["planned"]),
            )],
            "mercenaries": bytes(record["mercenaries"]),
        }
        actual = {
            "side": payload[offset + SIDE_ID_OFFSET],
            "level": payload[offset + LEVEL_OFFSET],
            "at": payload[offset + COMMANDER_AT_OFFSET],
            "df": payload[offset + COMMANDER_DF_OFFSET],
            "x": payload[offset + X_OFFSET],
            "y": payload[offset + Y_OFFSET],
            "name": payload[offset + NAME_ID_OFFSET],
            "class": payload[offset + CLASS_ID_OFFSET],
            "tag": payload[offset + HARD_CORRECTION_INDEX_OFFSET],
            "mercenaries": payload[
                offset + MERCENARY_OFFSET:offset + FIXED_RECORD_SIZE
            ],
        }
        if actual != expected:
            raise ValueError(
                f"Scenario {scenario_number} protected NPC differs at "
                f"0x{offset:06X}: {actual!r} != {expected!r}"
            )


def apply_hard_mode(
    base_payload: bytes,
    plan: dict[str, Any],
    approval: dict[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    """Apply approved per-record balance values to a localized hard base ROM."""
    validate_plan_approval(plan, approval)
    if len(base_payload) != 0x400000:
        raise ValueError("hard-mode base ROM must be exactly 4 MiB")
    data = bytearray(base_payload)
    if (
        data[
            SOLDIER_CORRECTION_HOOK:
            SOLDIER_CORRECTION_HOOK + len(SOLDIER_CORRECTION_HOOK_SOURCE)
        ]
        != SOLDIER_CORRECTION_HOOK_SOURCE
    ):
        raise ValueError("fixed-unit soldier correction hook source changed")
    if (
        data[
            DYNAMIC_NPC_CORRECTION_HOOK:
            DYNAMIC_NPC_CORRECTION_HOOK
            + len(DYNAMIC_NPC_CORRECTION_HOOK_SOURCE)
        ]
        != DYNAMIC_NPC_CORRECTION_HOOK_SOURCE
    ):
        raise ValueError("playable-NPC loader epilogue source changed")
    if any(
        value != 0xFF
        for value in data[
            SOLDIER_CORRECTION_ROUTINE:SOLDIER_CORRECTION_AREA_END
        ]
    ):
        raise ValueError("hard-mode expansion area is not empty")

    pairs = _correction_pairs(plan)
    pair_index = {pair: index for index, pair in enumerate(pairs)}
    target_offsets: set[int] = set()
    commander_changes = 0
    soldier_changes = 0
    mercenary_changes = 0
    summon_changes = 0
    npc_protection_changes = 0
    for scenario_number, record in _planned_records(plan):
        offset = int(str(record["offset"]), 16)
        if offset in target_offsets:
            raise ValueError(f"duplicate hard-mode record: 0x{offset:06X}")
        target_offsets.add(offset)
        commander = record["commander"]
        soldier = record["enemy_soldier_correction"]
        mercenaries = record["mercenaries"]
        summon_replacement = record["summon_replacement"]

        expected_at = int(commander["at"]["original"])
        expected_df = int(commander["df"]["original"])
        expected_class = int(str(record["class_id"]), 16)
        expected_mercenaries = bytes(mercenaries["original"])
        if _signed_byte(data[offset + COMMANDER_AT_OFFSET]) != expected_at:
            raise ValueError(
                f"Scenario {scenario_number} AT source changed at 0x{offset:06X}"
            )
        if _signed_byte(data[offset + COMMANDER_DF_OFFSET]) != expected_df:
            raise ValueError(
                f"Scenario {scenario_number} DF source changed at 0x{offset:06X}"
            )
        if data[offset + CLASS_ID_OFFSET] != expected_class:
            raise ValueError(
                f"Scenario {scenario_number} class source changed at 0x{offset:06X}"
            )
        if (
            data[offset + MERCENARY_OFFSET:offset + FIXED_RECORD_SIZE]
            != expected_mercenaries
        ):
            raise ValueError(
                f"Scenario {scenario_number} mercenary source changed "
                f"at 0x{offset:06X}"
            )
        if data[offset + HARD_CORRECTION_INDEX_OFFSET] != 0xFF:
            raise ValueError(
                f"Scenario {scenario_number} hard correction tag is occupied "
                f"at 0x{offset:06X}"
            )

        planned_at = int(commander["at"]["planned"])
        planned_df = int(commander["df"]["planned"])
        correction = (
            int(soldier["at"]["planned"]),
            int(soldier["df"]["planned"]),
        )
        planned_mercenaries = bytes(mercenaries["planned"])
        conventional_rows = list(mercenaries["changes"])
        summon_rows = list(summon_replacement["changes"])
        declared_rows = conventional_rows + summon_rows
        declared_slots: set[int] = set()
        for change in declared_rows:
            slot = int(change["slot"])
            source_id = int(change["source_class_id"])
            target_id = int(change["target_class_id"])
            if not 0 <= slot < MERCENARY_COUNT:
                raise ValueError(
                    f"Scenario {scenario_number} invalid mercenary slot "
                    f"{slot} at 0x{offset:06X}"
                )
            if slot in declared_slots:
                raise ValueError(
                    f"Scenario {scenario_number} duplicate mercenary slot "
                    f"{slot} at 0x{offset:06X}"
                )
            declared_slots.add(slot)
            if (
                expected_mercenaries[slot] != source_id
                or planned_mercenaries[slot] != target_id
            ):
                raise ValueError(
                    f"Scenario {scenario_number} declared mercenary change "
                    f"does not match slot {slot} at 0x{offset:06X}"
                )
        actual_slots = {
            slot
            for slot, (before, after) in enumerate(
                zip(expected_mercenaries, planned_mercenaries)
            )
            if before != after
        }
        if actual_slots != declared_slots:
            raise ValueError(
                f"Scenario {scenario_number} undeclared mercenary changes "
                f"at 0x{offset:06X}: actual={sorted(actual_slots)!r}, "
                f"declared={sorted(declared_slots)!r}"
            )
        data[offset + COMMANDER_AT_OFFSET] = _encoded_byte(planned_at)
        data[offset + COMMANDER_DF_OFFSET] = _encoded_byte(planned_df)
        data[offset + HARD_CORRECTION_INDEX_OFFSET] = pair_index[correction]
        data[
            offset + MERCENARY_OFFSET:offset + FIXED_RECORD_SIZE
        ] = planned_mercenaries

        commander_changes += (
            planned_at != expected_at or planned_df != expected_df
        )
        soldier_changes += correction != (
            int(soldier["at"]["original"]),
            int(soldier["df"]["original"]),
        )
        mercenary_changes += len(conventional_rows)
        summon_changes += len(summon_rows)

    for scenario_number, record in _npc_protection_records(plan):
        offset = int(str(record["offset"]), 16)
        layout = scenario_data.scenario_layout(data, scenario_number)
        indexed_offset = (
            layout.records_offset
            + int(record["index"]) * FIXED_RECORD_SIZE
        )
        if indexed_offset != offset:
            raise ValueError(
                f"Scenario {scenario_number} protected NPC index differs: "
                f"0x{indexed_offset:06X} != 0x{offset:06X}"
            )
        if offset in target_offsets:
            raise ValueError(
                f"duplicate protected NPC hard-mode record: 0x{offset:06X}"
            )
        target_offsets.add(offset)
        expected = {
            "side": 0x03,
            "level": int(record["level"]),
            "at": _encoded_byte(int(record["commander_at"])),
            "df": _encoded_byte(int(record["commander_df"]["original"])),
            "x": int(record["x"]),
            "y": int(record["y"]),
            "name": int(str(record["name_id"]), 16),
            "class": int(str(record["class_id"]), 16),
            "tag": 0xFF,
            "mercenaries": bytes(record["mercenaries"]),
        }
        actual = {
            "side": data[offset + SIDE_ID_OFFSET],
            "level": data[offset + LEVEL_OFFSET],
            "at": data[offset + COMMANDER_AT_OFFSET],
            "df": data[offset + COMMANDER_DF_OFFSET],
            "x": data[offset + X_OFFSET],
            "y": data[offset + Y_OFFSET],
            "name": data[offset + NAME_ID_OFFSET],
            "class": data[offset + CLASS_ID_OFFSET],
            "tag": data[offset + HARD_CORRECTION_INDEX_OFFSET],
            "mercenaries": bytes(data[
                offset + MERCENARY_OFFSET:offset + FIXED_RECORD_SIZE
            ]),
        }
        if actual != expected:
            raise ValueError(
                f"Scenario {scenario_number} protected NPC source differs "
                f"at 0x{offset:06X}: {actual!r} != {expected!r}"
            )
        soldier = record["soldier_correction"]
        correction = (
            int(soldier["at"]),
            int(soldier["df"]["planned"]),
        )
        data[offset + COMMANDER_DF_OFFSET] = _encoded_byte(
            int(record["commander_df"]["planned"])
        )
        data[offset + HARD_CORRECTION_INDEX_OFFSET] = pair_index[correction]
        npc_protection_changes += 1

    routine = correction_routine()
    hook = correction_hook()
    table = b"".join(
        bytes((_encoded_byte(at), _encoded_byte(df)))
        for at, df in pairs
    )
    dynamic_routine = dynamic_npc_correction_routine()
    dynamic_hook = dynamic_npc_correction_hook()
    dynamic_table = _dynamic_npc_delta_table(plan, pairs)
    data[
        SOLDIER_CORRECTION_HOOK:
        SOLDIER_CORRECTION_HOOK + len(hook)
    ] = hook
    data[
        SOLDIER_CORRECTION_ROUTINE:
        SOLDIER_CORRECTION_ROUTINE + len(routine)
    ] = routine
    data[
        SOLDIER_CORRECTION_TABLE:
        SOLDIER_CORRECTION_TABLE + len(table)
    ] = table
    data[
        DYNAMIC_NPC_CORRECTION_HOOK:
        DYNAMIC_NPC_CORRECTION_HOOK + len(dynamic_hook)
    ] = dynamic_hook
    data[
        DYNAMIC_NPC_CORRECTION_ROUTINE:
        DYNAMIC_NPC_CORRECTION_ROUTINE + len(dynamic_routine)
    ] = dynamic_routine
    data[
        DYNAMIC_NPC_CORRECTION_TABLE:
        DYNAMIC_NPC_CORRECTION_TABLE + len(dynamic_table)
    ] = dynamic_table

    checksum = korean_builder.update_md_checksum(data)
    payload = bytes(data)
    if (
        rom_update.md_sram_descriptor(payload)
        != rom_update.md_sram_descriptor(base_payload)
    ):
        raise AssertionError("hard-mode build changed the SRAM descriptor")
    model = {
        "schema_version": 1,
        "status": "release_candidate",
        "profile_id": plan["profile_id"],
        "approval_confirmation": approval["approval"]["confirmation"],
        "base": {
            "size": len(base_payload),
            "sha256": hashlib.sha256(base_payload).hexdigest(),
            "sram_descriptor": rom_update.md_sram_descriptor(
                base_payload
            ).hex().upper(),
        },
        "hard": {
            "size": len(payload),
            "header_checksum": f"{checksum:04X}",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "sram_descriptor": rom_update.md_sram_descriptor(
                payload
            ).hex().upper(),
        },
        "implementation": {
            "target_record_count": len(_planned_records(plan)),
            "npc_survival_protection_record_count": (
                npc_protection_changes
            ),
            "total_fixed_record_count": len(target_offsets),
            "commander_change_record_count": commander_changes,
            "soldier_correction_record_count": soldier_changes,
            "mercenary_replacement_slot_count": mercenary_changes,
            "summon_replacement_slot_count": summon_changes,
            "total_mercenary_slot_change_count": (
                mercenary_changes + summon_changes
            ),
            "correction_pair_count": len(pairs),
            "record_tag_offset": f"0x{HARD_CORRECTION_INDEX_OFFSET:02X}",
            "loader_hook": f"0x{SOLDIER_CORRECTION_HOOK:06X}",
            "loader_routine": f"0x{SOLDIER_CORRECTION_ROUTINE:06X}",
            "correction_table": f"0x{SOLDIER_CORRECTION_TABLE:06X}",
            "dynamic_npc_loader_hook": (
                f"0x{DYNAMIC_NPC_CORRECTION_HOOK:06X}"
            ),
            "dynamic_npc_loader_routine": (
                f"0x{DYNAMIC_NPC_CORRECTION_ROUTINE:06X}"
            ),
            "dynamic_npc_delta_table": (
                f"0x{DYNAMIC_NPC_CORRECTION_TABLE:06X}"
            ),
            "dynamic_npc_delta_record_count": sum(
                1
                for index in range(0, len(dynamic_table), 2)
                if dynamic_table[index:index + 2] != b"\x00\x00"
            ),
            "shared_class_records_modified": False,
            "original_profile_modified": False,
            "normal_profile_modified": False,
            "custom_class_map_sprites": {
                "count": len(
                    korean_builder.AI_CLASS_MAP_SPRITE_SPECS
                ),
                "class_ids": [
                    f"0x{class_id:02X}"
                    for class_id in sorted({
                        class_id
                        for _, class_id, _ in (
                            korean_builder.AI_CLASS_MAP_SPRITE_SPECS
                        )
                    })
                ],
                "sprite_id_range": [
                    (
                        "0x"
                        f"{korean_builder.AI_CLASS_MAP_SPRITE_SPECS[0][2]:04X}"
                    ),
                    (
                        "0x"
                        f"{korean_builder.AI_CLASS_MAP_SPRITE_SPECS[-1][2]:04X}"
                    ),
                ],
                "animation_frames": 2,
                "source": "editor/static/ai-class-sprites",
            },
            "title_identity": {
                "new_game_label": korean_builder.TITLE_HARD_MAIN_MENU_START_TEXT,
                "marker": korean_builder.TITLE_HARD_MARKER_TEXT,
                "logo_palette": "amber_gold",
                "normal_title_unchanged": True,
            },
        },
        "save_compatibility": {
            "save_format": "lang2-ko-sram-v1",
            "sram_descriptor_unchanged": True,
            "update_rom_in_place": True,
            "save_states_supported": False,
        },
    }
    return payload, model


def _build_localized_hard_base(
    output: Path,
    version_registry: Path | None = None,
) -> None:
    command = [
        sys.executable,
        str(ROOT / "scripts/build_korean_jp_probe.py"),
        "--rom-profile",
        "hard",
        "--out",
        str(output),
    ]
    if version_registry is not None:
        command.extend(
            ["--rom-version-registry", str(version_registry.resolve())]
        )
    subprocess.run(
        command,
        cwd=ROOT,
        check=True,
    )


def build_hard_rom(
    output: Path = DEFAULT_OUTPUT,
    manifest_path: Path = DEFAULT_BUILD_MANIFEST,
    base_rom: Path | None = None,
    version_registry: Path | None = None,
) -> dict[str, Any]:
    output = output.resolve()
    manifest_path = manifest_path.resolve()
    if base_rom is not None:
        base_rom = base_rom.resolve()
    approval = hard_mode_approval.require_approved()
    plan = load_applied_plan()
    profile = (
        get_profile("hard")
        if version_registry is None
        else get_profile("hard", version_registry.resolve())
    )
    with tempfile.TemporaryDirectory(prefix="lang2-hard-") as directory:
        if base_rom is None:
            base_path = Path(directory) / "localized-hard-base.md"
            _build_localized_hard_base(base_path, version_registry)
        else:
            base_path = base_rom
        payload, model = apply_hard_mode(
            base_path.read_bytes(),
            plan,
            approval,
        )
    verify_applied_hard_mode(payload, plan)
    model["release"] = {
        "release_id": profile["release_id"],
        "translation_version": profile["translation_version"],
        "balance_version": profile["balance_version"],
        "rom_filename": profile["rom_filename"],
        "header_title": profile["header_title"],
        "output": str(output.relative_to(ROOT)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(model, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the approved Langrisser II Standard Hard ROM"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_BUILD_MANIFEST,
    )
    parser.add_argument(
        "--base-rom",
        type=Path,
        help="use an already localized hard-profile ROM",
    )
    parser.add_argument(
        "--rom-version-registry",
        type=Path,
        help="alternate version registry for preview or release builds",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model = build_hard_rom(
        args.out,
        args.manifest,
        args.base_rom,
        args.rom_version_registry,
    )
    print(args.out)
    print(args.manifest)
    print(
        f"checksum={model['hard']['header_checksum']} "
        f"sha256={model['hard']['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
