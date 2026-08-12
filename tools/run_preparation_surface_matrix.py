#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Iterable

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.class_hire_data import MERCENARY_CLASS_BASE, MERCENARY_CLASS_COUNT
from tools.jp_byte_table_analyzer import KOREAN_CLASS_LABELS
from tools.run_blastem_sequence import (
    GST_WORK_RAM_FILE_OFFSET,
    MANUAL_SLOT_COMMANDER_CLASS_OFFSET,
    MANUAL_SLOT_COMMANDER_COUNT,
    MANUAL_SLOT_COMMANDER_LEVEL_OFFSET,
    MANUAL_SLOT_COMMANDER_RECORD_SIZE,
    MANUAL_SLOT_COMMANDER_ROSTER_OFFSET,
    MANUAL_SLOT_WORK_RAM_SEGMENTS,
    preparation_screen_visible,
    terminate_blastem_processes,
)
from tools.scenario_data import (
    DEFAULT_REFERENCE_ROM,
    be16,
    read_scenario,
    scenario_layout,
)


SCENARIO_MIN = 1
SCENARIO_MAX = 31
PLAYER_COMMANDER_COUNT_OFFSET = 0x10
MANUAL_SLOT_COMMANDER_HIRE_MASK_OFFSET = 0x0A
COMMANDER_ROSTER_PAGE_SIZE = 5
HIRE_PAGE_SIZE = 3
DEFAULT_DISPLAY = ":104"
DEFAULT_SEED_GST = (
    ROOT
    / "captures/analysis/"
    "hard_mode_current_candidate_first_turn_s27_endpoint.gst"
)
DEFAULT_OUTPUT_ROOT = ROOT / "captures/run/preparation_surface_matrix"
DEFAULT_RUNTIME_ROOT = ROOT / "captures/runtime"
PREPARATION_LAUNCH_ATTEMPTS = 3
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_MEMBER_SIZE = 0x0C
RUNTIME_SIDE_OFFSET = 0x20
RUNTIME_LEVEL_OFFSET = 0x2E
# Opening/event code imports saved progression into only these fixed records.
# Keep this list identity-locked by scenario, record, and name so an arbitrary
# allied/NPC class or level mismatch cannot be waved through as progression.
RUNTIME_FIXED_PROGRESS_OVERRIDES = {
    (1, 1): {"name_id": 0x02, "fields": ("level",)},       # Liana
    (2, 3): {"name_id": 0x02, "fields": ("level",)},       # Liana
    (3, 0): {"name_id": 0x02, "fields": ("level",)},       # Liana
    (4, 0): {"name_id": 0x02, "fields": ("level",)},       # Liana
    (6, 0): {"name_id": 0x08, "fields": ("class_id",)},    # Aaron
    (7, 3): {"name_id": 0x07, "fields": ("level",)},       # Keith
    (10, 1): {"name_id": 0x09, "fields": ("level",)},      # Lester
    (11, 0): {"name_id": 0x0A, "fields": ("class_id", "level")},
    (15, 0): {"name_id": 0x06, "fields": ("class_id", "level")},
    (22, 0): {"name_id": 0x02, "fields": ("class_id", "level")},
    (25, 0): {"name_id": 0x0A, "fields": ("class_id", "level")},
}
# Some legacy-save recovery probes deliberately inject an otherwise impossible
# Fighter LV10/11/12 into the natural join record.  Those probes must opt in
# with the exact class and level they injected; ordinary preparation/result
# runs never receive this exception.  Keep both the target identities and the
# permitted diagnostic values closed here so a caller cannot suppress an
# unrelated fixed-record regression.
RUNTIME_FIXED_DIAGNOSTIC_OVERRIDE_TARGETS = {
    (7, 3): {
        "name_id": 0x07,  # Keith
        "class_ids": (0x01,),
        "levels": (10, 11, 12),
    },
    (10, 1): {
        "name_id": 0x09,  # Lester
        "class_ids": (0x01,),
        "levels": (10, 11, 12),
    },
}
PROFILE_ROMS = {
    "pure": (
        ROOT
        / "tmp/Langrisser II (Korean Original prep-pattern-pool-yal probe).md"
    ),
    "normal": (
        ROOT / "tmp/Langrisser II (Korean prep-pattern-pool-yal probe).md"
    ),
    "hard": (
        ROOT / "tmp/Langrisser II (Korean Hard prep-pattern-pool-yal probe).md"
    ),
}
RUNTIME_CHECKPOINT_CHARS = ("얄", "실")
SEND_KEYS = ROOT / "tools/send_blastem_keys.py"
CAPTURE_WINDOW = ROOT / "tools/capture_blastem_window.py"
RUN_SEQUENCE = ROOT / "tools/run_blastem_sequence.py"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md_checksum(path: Path) -> str:
    data = path.read_bytes()
    if len(data) < 0x190:
        raise ValueError(f"ROM is too short: {path}")
    return f"{int.from_bytes(data[0x18E:0x190], 'big'):04X}"


def runtime_fixed_record_signature(gst: bytes, group_index: int) -> tuple:
    start = (
        GST_WORK_RAM_FILE_OFFSET
        + RUNTIME_GROUP_BASE
        + group_index * RUNTIME_GROUP_SIZE
    )
    end = start + RUNTIME_GROUP_SIZE
    if len(gst) < end:
        raise ValueError(
            f"GST is too short to contain runtime group {group_index}"
        )
    record = gst[start:end]
    return (
        record[0],
        record[1],
        tuple(
            record[index * RUNTIME_MEMBER_SIZE]
            for index in range(1, 7)
        ),
    )


def runtime_fixed_record_layout(
    gst: bytes,
    group_index: int,
) -> dict[str, object]:
    """Read the fixed-record fields that must survive the runtime loader.

    The old scenario-identity score intentionally used only class, name, and
    mercenary IDs.  That was sufficient to distinguish scenarios, but it was
    not a layout-integrity check: a wrong side, level, or placement could pass
    the 75% identity threshold.  Keep the compact signature for scenario
    selection and expose the complete loader-owned subset for the stricter
    check below.
    """
    start = (
        GST_WORK_RAM_FILE_OFFSET
        + RUNTIME_GROUP_BASE
        + group_index * RUNTIME_GROUP_SIZE
    )
    end = start + RUNTIME_GROUP_SIZE
    if len(gst) < end:
        raise ValueError(
            f"GST is too short to contain runtime group {group_index}"
        )
    record = gst[start:end]
    return {
        "class_id": record[0],
        "name_id": record[1],
        "side_id": record[RUNTIME_SIDE_OFFSET],
        "level": record[RUNTIME_LEVEL_OFFSET],
        "x": record[0x06],
        "y": record[0x07],
        "mercenaries": [
            record[index * RUNTIME_MEMBER_SIZE]
            for index in range(1, 7)
        ],
    }


def verify_runtime_fixed_record_layout(
    gst: bytes,
    rom: bytes,
    reference: bytes,
    scenario_number: int,
    diagnostic_exact_overrides: (
        dict[tuple[int, int], dict[str, int]] | None
    ) = None,
) -> dict[str, object]:
    """Require every loaded fixed record to retain its structural identity.

    A small identity-locked set of opening/event records legitimately imports
    a commander's saved class and/or level. Those declared fields are reported
    rather than source-locked. Names, sides, coordinates, and mercenary
    composition remain mandatory for every record; every undeclared class and
    level remains mandatory as well.
    """
    model = read_scenario(rom, reference, scenario_number)
    player_groups = player_commander_count(rom, scenario_number)
    requested_diagnostics = diagnostic_exact_overrides or {}
    normalized_diagnostics: dict[tuple[int, int], dict[str, int]] = {}
    for key, requested in requested_diagnostics.items():
        if not (
            isinstance(key, tuple)
            and len(key) == 2
            and all(isinstance(value, int) for value in key)
        ):
            raise ValueError(
                "runtime diagnostic override keys must be "
                "(scenario, fixed_record) integer tuples"
            )
        if key[0] != scenario_number:
            raise ValueError(
                "runtime diagnostic override scenario does not match the "
                f"requested Scenario {scenario_number}: {key}"
            )
        policy = RUNTIME_FIXED_DIAGNOSTIC_OVERRIDE_TARGETS.get(key)
        if policy is None:
            raise ValueError(
                "runtime diagnostic override target is not permitted: "
                f"Scenario {key[0]} record {key[1]}"
            )
        if set(requested) != {"name_id", "class_id", "level"}:
            raise ValueError(
                "runtime diagnostic override must specify exactly name_id, "
                "class_id, and level"
            )
        normalized = {
            field: int(requested[field])
            for field in ("name_id", "class_id", "level")
        }
        if normalized["name_id"] != int(policy["name_id"]):
            raise ValueError(
                "runtime diagnostic override name identity is not permitted: "
                f"0x{normalized['name_id']:02X}"
            )
        if normalized["class_id"] not in policy["class_ids"]:
            raise ValueError(
                "runtime diagnostic override class is not permitted: "
                f"0x{normalized['class_id']:02X}"
            )
        if normalized["level"] not in policy["levels"]:
            raise ValueError(
                "runtime diagnostic override level is not permitted: "
                f"{normalized['level']}"
            )
        normalized_diagnostics[key] = normalized

    manual_slot = b"".join(
        gst[
            GST_WORK_RAM_FILE_OFFSET + address:
            GST_WORK_RAM_FILE_OFFSET + address + size
        ]
        for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS
    )
    if len(manual_slot) != sum(
        size for _, size in MANUAL_SLOT_WORK_RAM_SEGMENTS
    ):
        raise ValueError("GST is too short to contain the manual-slot record")
    rows = []
    mismatches = []
    used_diagnostics = []
    for row in model["records"]:
        index = int(row["index"])
        expected = {
            "class_id": int(row["class_id"]),
            "name_id": int(row["name"]["id"]),
            "side_id": int(row["side_id"]),
            "level": int(row["level"]),
            "x": int(row["x"]),
            "y": int(row["y"]),
            "mercenaries": [int(value) for value in row["mercenaries"]],
        }
        actual = runtime_fixed_record_layout(gst, player_groups + index)
        diagnostic = normalized_diagnostics.get((scenario_number, index))
        override = RUNTIME_FIXED_PROGRESS_OVERRIDES.get(
            (scenario_number, index)
        )
        progression_fields = []
        saved_progression_expected = {}
        if diagnostic is not None:
            if expected["name_id"] != diagnostic["name_id"]:
                raise RuntimeError(
                    "declared runtime diagnostic identity changed: "
                    f"Scenario {scenario_number} record {index} name "
                    f"0x{expected['name_id']:02X}"
                )
            progression_fields = ["class_id", "level"]
            used_diagnostics.append({
                "scenario": scenario_number,
                "fixed_record_index": index,
                **diagnostic,
            })
        elif override is not None:
            if expected["name_id"] != int(override["name_id"]):
                raise RuntimeError(
                    "declared runtime progression identity changed: "
                    f"Scenario {scenario_number} record {index} name "
                    f"0x{expected['name_id']:02X}"
                )
            progression_fields = list(override["fields"])
            commander_id = int(override["name_id"])
            commander = (
                MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
                + (commander_id - 1) * MANUAL_SLOT_COMMANDER_RECORD_SIZE
            )
            saved_progression_expected = {
                "class_id": manual_slot[
                    commander + MANUAL_SLOT_COMMANDER_CLASS_OFFSET
                ],
                "level": manual_slot[
                    commander + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET
                ],
            }
        protected_fields = [
            field for field in expected if field not in progression_fields
        ]
        changed = {
            field: {"expected": expected[field], "actual": actual[field]}
            for field in protected_fields
            if actual[field] != expected[field]
        }
        for field in progression_fields:
            progression_expected = (
                diagnostic[field]
                if diagnostic is not None
                else saved_progression_expected[field]
            )
            if actual[field] != progression_expected:
                changed[field] = {
                    "expected": progression_expected,
                    "actual": actual[field],
                    "source": (
                        "caller_exact_diagnostic"
                        if diagnostic is not None
                        else "serialized_commander_save"
                    ),
                }
        progression_overrides = {
            field: {
                "source": expected[field],
                "runtime": actual[field],
                "required_runtime": (
                    diagnostic[field]
                    if diagnostic is not None
                    else saved_progression_expected[field]
                ),
            }
            for field in progression_fields
            if actual[field] != expected[field]
        }
        result_row = {
            "fixed_record_index": index,
            "runtime_group": player_groups + index,
            "expected": expected,
            "actual": actual,
            "allowed_progression_fields": progression_fields,
            "saved_progression_expected": saved_progression_expected,
            "diagnostic_exact_override": diagnostic,
            "progression_overrides": progression_overrides,
            "protected_mismatches": changed,
        }
        rows.append(result_row)
        if changed:
            mismatches.append(result_row)

    result = {
        "status": "pass" if not mismatches else "fail",
        "scenario": scenario_number,
        "player_runtime_group_count": player_groups,
        "fixed_record_count": len(rows),
        "checked_fields": [
            "class_id",
            "name_id",
            "side_id",
            "level",
            "x",
            "y",
            "mercenaries",
        ],
        "allied_progression_policy": (
            "only the scenario/record/name entries in "
            "RUNTIME_FIXED_PROGRESS_OVERRIDES may import the exact serialized "
            "commander class_id and/or level; Keith/Lester legacy diagnostics "
            "must additionally opt in to an exact closed override"
        ),
        "diagnostic_exact_overrides_requested": [
            {
                "scenario": scenario,
                "fixed_record_index": record,
                **values,
            }
            for (scenario, record), values in normalized_diagnostics.items()
        ],
        "diagnostic_exact_overrides_used": used_diagnostics,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "records": rows,
    }
    if mismatches:
        first = mismatches[0]
        raise RuntimeError(
            "runtime fixed-record layout mismatch: Scenario "
            f"{scenario_number} record {first['fixed_record_index']} "
            f"{first['protected_mismatches']}"
        )
    return result


def verify_runtime_scenario_identity(
    gst_path: Path,
    rom_path: Path,
    scenario_number: int,
    diagnostic_exact_overrides: (
        dict[tuple[int, int], dict[str, int]] | None
    ) = None,
) -> dict[str, object]:
    """Identify the selected scenario from its loaded fixed-record groups.

    A few opening events legitimately alter one or two source records before
    preparation.  Comparing every scenario and selecting the strongest match
    is therefore more robust than requiring every byte of the target records
    to remain unchanged.
    """
    gst = gst_path.read_bytes()
    rom = rom_path.read_bytes()
    reference = DEFAULT_REFERENCE_ROM.read_bytes()
    scores = []
    for candidate in range(SCENARIO_MIN, SCENARIO_MAX + 1):
        model = read_scenario(rom, reference, candidate)
        player_groups = player_commander_count(rom, candidate)
        matched = 0
        for row in model["records"]:
            actual = runtime_fixed_record_signature(
                gst,
                player_groups + int(row["index"]),
            )
            expected = (
                int(row["class_id"]),
                int(row["name"]["id"]),
                tuple(int(value) for value in row["mercenaries"]),
            )
            matched += actual == expected
        total = len(model["records"])
        scores.append({
            "scenario": candidate,
            "matched_records": matched,
            "total_records": total,
            "match_ratio": matched / total,
        })
    scores.sort(
        key=lambda row: (
            float(row["match_ratio"]),
            int(row["matched_records"]),
        ),
        reverse=True,
    )
    best = scores[0]
    runner_up = scores[1]
    passed = (
        int(best["scenario"]) == scenario_number
        and float(best["match_ratio"]) >= 0.75
        and (
            float(best["match_ratio"]),
            int(best["matched_records"]),
        )
        > (
            float(runner_up["match_ratio"]),
            int(runner_up["matched_records"]),
        )
    )
    result = {
        "status": "pass" if passed else "fail",
        "requested_scenario": scenario_number,
        "identified_scenario": int(best["scenario"]),
        "best_match": best,
        "runner_up": runner_up,
        "gst": str(gst_path),
    }
    if not passed:
        raise RuntimeError(
            "scenario selector identity mismatch: requested "
            f"{scenario_number}, identified {best['scenario']} "
            f"({best['matched_records']}/{best['total_records']} records)"
        )
    result["fixed_record_layout"] = verify_runtime_fixed_record_layout(
        gst,
        rom,
        reference,
        scenario_number,
        diagnostic_exact_overrides=diagnostic_exact_overrides,
    )
    return result


def player_commander_count(data: bytes, scenario_number: int) -> int:
    layout = scenario_layout(data, scenario_number)
    count = be16(data, layout.header_offset + PLAYER_COMMANDER_COUNT_OFFSET)
    if not 1 <= count <= MANUAL_SLOT_COMMANDER_COUNT:
        raise ValueError(
            f"Scenario {scenario_number} has invalid player commander count {count}"
        )
    return count


def player_commander_ids(data: bytes, scenario_number: int) -> list[int]:
    layout = scenario_layout(data, scenario_number)
    count = player_commander_count(data, scenario_number)
    start = layout.header_offset + PLAYER_COMMANDER_COUNT_OFFSET + 2
    commander_ids = [
        be16(data, start + index * 2)
        for index in range(count)
    ]
    if any(
        not 1 <= commander_id <= MANUAL_SLOT_COMMANDER_COUNT
        for commander_id in commander_ids
    ):
        raise ValueError(
            f"Scenario {scenario_number} has an invalid player commander ID"
        )
    if len(set(commander_ids)) != len(commander_ids):
        raise ValueError(
            f"Scenario {scenario_number} repeats a player commander ID"
        )
    return commander_ids


def manual_slot_record_from_gst(gst_path: Path) -> bytes:
    gst = gst_path.read_bytes()
    parts: list[bytes] = []
    for address, size in MANUAL_SLOT_WORK_RAM_SEGMENTS:
        start = GST_WORK_RAM_FILE_OFFSET + address
        end = start + size
        if len(gst) < end:
            raise ValueError(
                f"GST is too short for manual-slot RAM segment 0x{address:04X}"
            )
        parts.append(gst[start:end])
    return b"".join(parts)


def manual_slot_scenario_from_gst(gst_path: Path) -> int:
    record = manual_slot_record_from_gst(gst_path)
    scenario = int.from_bytes(record[:2], "big")
    if not SCENARIO_MIN <= scenario <= SCENARIO_MAX:
        raise ValueError(
            f"manual-slot runtime record has invalid scenario {scenario}: "
            f"{gst_path}"
        )
    return scenario


def hire_rows(mask: int) -> list[dict[str, object]]:
    if not 0 <= mask <= 0xFFFF:
        raise ValueError("hire mask must fit one word")
    rows = []
    for bit in range(MERCENARY_CLASS_COUNT):
        if not mask & (1 << bit):
            continue
        class_id = MERCENARY_CLASS_BASE + bit
        rows.append(
            {
                "bit": bit,
                "class_id": class_id,
                "class_id_hex": f"0x{class_id:02X}",
                "korean": KOREAN_CLASS_LABELS[class_id],
            }
        )
    return rows


def manual_slot_roster(gst_path: Path) -> list[dict[str, object]]:
    record = manual_slot_record_from_gst(gst_path)
    rows = []
    for index in range(MANUAL_SLOT_COMMANDER_COUNT):
        offset = (
            MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
            + index * MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        class_id = record[offset + MANUAL_SLOT_COMMANDER_CLASS_OFFSET]
        level = record[offset + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET]
        mask_offset = offset + MANUAL_SLOT_COMMANDER_HIRE_MASK_OFFSET
        mask = int.from_bytes(record[mask_offset : mask_offset + 2], "big")
        offered = hire_rows(mask)
        rows.append(
            {
                "commander_id": index + 1,
                "class_id": class_id,
                "class_id_hex": f"0x{class_id:02X}",
                "class_korean": KOREAN_CLASS_LABELS[class_id],
                "level": level,
                "hire_mask": f"0x{mask:04X}",
                "hire_rows": offered,
                "hire_page_count": max(1, math.ceil(len(offered) / HIRE_PAGE_SIZE)),
            }
        )
    return rows


def visible_fixed_records(model: dict[str, object]) -> list[dict[str, object]]:
    return [
        row
        for row in model["records"]
        if not row["hidden"] and row["x"] != 0xFF and row["y"] != 0xFF
    ]


def fixed_record_not_applicable(model: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for record in model["records"]:
        reasons = []
        if record["hidden"]:
            reasons.append("source record is hidden at preparation time")
        if record["x"] == 0xFF or record["y"] == 0xFF:
            reasons.append("source coordinates are (255,255)")
        if reasons:
            rows.append(
                {
                    "index": record["index"],
                    "name_korean": record["name"]["ko"],
                    "class_korean": record["class"]["ko"],
                    "reason": "; ".join(reasons),
                }
            )
    return rows


def manhattan(left: dict[str, object], right: dict[str, object]) -> int:
    return abs(int(left["x"]) - int(right["x"])) + abs(
        int(left["y"]) - int(right["y"])
    )


def greedy_fixed_record_route(
    records: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    remaining = list(records)
    if not remaining:
        return []
    route = [remaining.pop(0)]
    while remaining:
        current = route[-1]
        next_record = min(
            remaining,
            key=lambda row: (manhattan(current, row), int(row["index"])),
        )
        remaining.remove(next_record)
        route.append(next_record)
    return route


def directional_keys(
    start: tuple[int, int],
    end: tuple[int, int],
) -> list[str]:
    start_x, start_y = start
    end_x, end_y = end
    keys: list[str] = []
    if end_x < start_x:
        keys.extend(["left"] * (start_x - end_x))
    else:
        keys.extend(["right"] * (end_x - start_x))
    if end_y < start_y:
        keys.extend(["up"] * (start_y - end_y))
    else:
        keys.extend(["down"] * (end_y - start_y))
    return keys


def record_slug(record: dict[str, object]) -> str:
    return f"record_{int(record['index']):02d}"


def build_plan(
    rom_path: Path,
    reference_rom_path: Path,
    seed_gst: Path,
    scenario_number: int,
) -> dict[str, object]:
    data = rom_path.read_bytes()
    reference = reference_rom_path.read_bytes()
    commander_count = player_commander_count(data, scenario_number)
    seed_roster = manual_slot_roster(seed_gst)
    seed_by_commander_id = {
        int(row["commander_id"]): row for row in seed_roster
    }
    commander_ids = player_commander_ids(data, scenario_number)
    commander_rows = [
        {
            **seed_by_commander_id[commander_id],
            "position": position,
        }
        for position, commander_id in enumerate(commander_ids, 1)
    ]
    model = read_scenario(data, reference, scenario_number)
    visible = visible_fixed_records(model)
    # The in-game 적군보기 surface advances preparation-visible fixed records
    # with one held Right in source-record order, skipping hidden entries.
    route = visible
    return {
        "schema_version": 1,
        "scenario": scenario_number,
        "rom": {
            "path": str(rom_path.relative_to(ROOT)),
            "md_checksum": md_checksum(rom_path),
            "sha256": sha256_path(rom_path),
        },
        "seed_gst": {
            "path": str(seed_gst.relative_to(ROOT)),
            "sha256": sha256_path(seed_gst),
            "policy": (
                "preserve the seed's actual class and offered-hire masks; "
                "do not OR diagnostic FFFF masks into acceptance runs"
            ),
        },
        "allied_commanders": {
            "count": commander_count,
            "roster_page_count": math.ceil(
                commander_count / COMMANDER_ROSTER_PAGE_SIZE
            ),
            "seed_records": commander_rows,
        },
        "fixed_records": {
            "count": model["record_count"],
            "visible_count": len(visible),
            "route": [
                {
                    "index": row["index"],
                    "name_korean": row["name"]["ko"],
                    "class_korean": row["class"]["ko"],
                    "mercenary_classes_korean": sorted(
                        {
                            KOREAN_CLASS_LABELS[class_id]
                            for class_id in row["mercenaries"]
                            if class_id != 0xFF
                        }
                    ),
                    "runtime_checkpoint_chars": [
                        char
                        for char in RUNTIME_CHECKPOINT_CHARS
                        if char
                        in (
                            row["name"]["ko"]
                            + row["class"]["ko"]
                            + "".join(
                                KOREAN_CLASS_LABELS[class_id]
                                for class_id in row["mercenaries"]
                                if class_id != 0xFF
                            )
                        )
                    ],
                    "side_id": f"0x{int(row['side_id']):02X}",
                    "x": row["x"],
                    "y": row["y"],
                }
                for row in route
            ],
            "not_applicable": fixed_record_not_applicable(model),
            "route_assumption": (
                "The arrangement detail cursor begins on the first visible "
                "source record; after explicitly closing its popup, one held "
                "Right advances to the next visible source record."
            ),
            "navigation": "right_cycle_source_record_order",
        },
        "required_runtime_checks": [
            "every allied commander root/status panel before and after shop",
            "every offered hire row before and after shop",
            "every arrangement roster page before and after shop",
            "every preparation-visible fixed commander detail before and after shop",
            "real shop item-list round trip in the same emulator process",
            "full-screen byte comparison plus human sprite/minimap/text review",
        ],
        "acceptance_policy": (
            "This plan and its runtime captures never change "
            "localization/preparation_surface_acceptance.json automatically."
        ),
    }


def fixed_detail_visible(path: Path) -> bool:
    with Image.open(path) as source:
        frame = source.convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    panel = frame.crop(
        (
            round(8 * scale_x),
            round(30 * scale_y),
            round(190 * scale_x),
            round(125 * scale_y),
        )
    )
    map_side = frame.crop(
        (
            round(192 * scale_x),
            round(30 * scale_y),
            round(315 * scale_x),
            round(200 * scale_y),
        )
    )
    right_border = frame.crop(
        (
            round(185 * scale_x),
            round(28 * scale_y),
            round(193 * scale_x),
            round(130 * scale_y),
        )
    )
    pixels = list(panel.get_flattened_data())
    map_pixels = list(map_side.get_flattened_data())
    border_pixels = list(right_border.get_flattened_data())
    dark_blue = sum(
        1
        for red, green, blue in pixels
        if 45 <= blue <= 180
        and red < 50
        and green < 70
        and blue > red * 1.8
        and blue > green * 1.5
    )
    white = sum(
        1
        for red, green, blue in pixels
        if red > 155 and green > 155 and blue > 155
    )
    map_blue = sum(
        1
        for red, green, blue in map_pixels
        if 45 <= blue <= 180
        and red < 50
        and green < 70
        and blue > red * 1.8
        and blue > green * 1.5
    )
    border_gold = sum(
        1
        for red, green, blue in border_pixels
        if red > 100
        and green > 70
        and blue < 80
        and red > blue * 1.5
    )
    # Detail panels use the upper-left blue box over the arrangement map.
    # Equipment/status panels can look similar inside the box, but their
    # entire right side remains blue instead of exposing the map.
    return (
        white / len(pixels) > 0.025
        and map_blue / len(map_pixels) < 0.10
        # Late-scenario one-row detail panels have the same valid gold edge,
        # but only part of it falls inside this fixed-width probe box.
        and border_gold / len(border_pixels) > 0.05
    )


def crop_ratios(
    path: Path,
    box: tuple[int, int, int, int],
) -> tuple[float, float, float]:
    with Image.open(path) as source:
        frame = source.convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    left, top, right, bottom = box
    crop = frame.crop(
        (
            round(left * scale_x),
            round(top * scale_y),
            round(right * scale_x),
            round(bottom * scale_y),
        )
    )
    pixels = list(crop.get_flattened_data())
    dark_blue = sum(
        1
        for red, green, blue in pixels
        if 45 <= blue <= 180
        and red < 50
        and green < 70
        and blue > red * 1.8
        and blue > green * 1.5
    )
    white = sum(
        1
        for red, green, blue in pixels
        if red > 155 and green > 155 and blue > 155
    )
    gold = sum(
        1
        for red, green, blue in pixels
        if red > 100
        and green > 70
        and blue < 80
        and red > blue * 1.5
    )
    size = len(pixels)
    return dark_blue / size, white / size, gold / size


def hire_screen_visible(path: Path) -> bool:
    if not preparation_screen_visible(path):
        return False
    _, white, _ = crop_ratios(path, (145, 115, 318, 214))
    # The active hire list contains white class/stat rows and END. The main
    # command list is dim gray, while equipment/status has only sparse white
    # labels in this same lower-right panel.
    return white > 0.025


def arrangement_menu_visible(path: Path) -> bool:
    map_blue, _, _ = crop_ratios(path, (192, 30, 315, 200))
    panel_blue, panel_white, _ = crop_ratios(path, (8, 30, 142, 140))
    detail_tail_blue, _, _ = crop_ratios(path, (145, 30, 185, 125))
    return (
        map_blue < 0.10
        and 0.55 < panel_blue < 0.70
        and panel_white > 0.10
        # Arrangement panels end near x=142. Fixed-record detail boxes extend
        # through this tail even when their left-side color ratios happen to
        # match a five-row Scenario 5 arrangement menu.
        and detail_tail_blue < 0.10
    )


def arrangement_roster_visible(path: Path) -> bool:
    map_blue, _, _ = crop_ratios(path, (192, 30, 315, 200))
    panel_blue, panel_white, _ = crop_ratios(path, (8, 30, 142, 140))
    detail_tail_blue, _, _ = crop_ratios(path, (145, 30, 185, 125))
    return (
        map_blue < 0.10
        and 0.75 < panel_blue < 0.90
        and 0.015 < panel_white < 0.085
        and detail_tail_blue < 0.10
    )


def status_dhash(path: Path) -> tuple[bool, ...]:
    with Image.open(path) as source:
        status = source.convert("L").crop((145, 32, 315, 115))
    resized = status.resize((17, 16), Image.Resampling.BILINEAR)
    pixels = list(resized.get_flattened_data())
    return tuple(
        pixels[y * 17 + x] > pixels[y * 17 + x + 1]
        for y in range(16)
        for x in range(16)
    )


def hash_distance(left: tuple[bool, ...], right: tuple[bool, ...]) -> int:
    if len(left) != len(right):
        raise ValueError("perceptual hashes must have the same length")
    return sum(a != b for a, b in zip(left, right))


def bright_ratio(
    path: Path,
    box: tuple[int, int, int, int],
) -> float:
    with Image.open(path) as source:
        frame = source.convert("RGB")
    scale_x = frame.width / 320
    scale_y = frame.height / 240
    left, top, right, bottom = box
    crop = frame.crop(
        (
            round(left * scale_x),
            round(top * scale_y),
            round(right * scale_x),
            round(bottom * scale_y),
        )
    )
    pixels = list(crop.get_flattened_data())
    return sum(
        1
        for red, green, blue in pixels
        if red > 180 and green > 180 and blue > 180
    ) / len(pixels)


def preparation_focus_side(path: Path) -> str | None:
    left = bright_ratio(path, (12, 35, 28, 130))
    right = bright_ratio(path, (145, 112, 162, 214))
    if right > 0.025:
        return "right"
    if left > 0.018 and right < 0.015:
        return "left"
    return None


def preparation_action_row(path: Path) -> int | None:
    if preparation_focus_side(path) != "right":
        return None
    ratios = [
        bright_ratio(path, (148, top, 160, top + 18))
        for top in (118, 143, 168, 193)
    ]
    row = max(range(len(ratios)), key=ratios.__getitem__)
    return row if ratios[row] > 0.025 else None


class RuntimeRecorder:
    def __init__(
        self,
        output: Path,
        display: str,
        runtime_home: Path,
    ) -> None:
        self.output = output
        self.display = display
        self.runtime_home = runtime_home
        self.captures: list[dict[str, object]] = []
        self.actions: list[dict[str, object]] = []
        self.environment = os.environ.copy()
        self.environment["DISPLAY"] = display
        self.environment.pop("WAYLAND_DISPLAY", None)
        self.environment["SDL_VIDEODRIVER"] = "x11"

    def run_command(self, command: list[str]) -> None:
        subprocess.check_call(command, cwd=ROOT, env=self.environment)

    def send(
        self,
        keys: Iterable[str],
        *,
        delay: float = 0.75,
        batched: bool = False,
    ) -> None:
        key_list = list(keys)
        if not key_list:
            return
        specs = [
            key if ":" in key or "@" in key else f"{key}:{delay}"
            for key in key_list
        ]
        commands = [specs] if batched else [[spec] for spec in specs]
        for command_specs in commands:
            self.run_command(
                [
                    sys.executable,
                    str(SEND_KEYS),
                    "--send-event",
                    "--hold",
                    "0.08",
                    *command_specs,
                ]
            )
        self.actions.append(
            {
                "keys": key_list,
                "delay_seconds": delay,
                "batched": batched,
            }
        )

    def capture(self, relative: str) -> Path:
        path = self.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        self.run_command(
            [
                sys.executable,
                str(CAPTURE_WINDOW),
                str(path),
                "--xlib-only",
            ]
        )
        with Image.open(path) as image:
            dimensions = [image.width, image.height]
        self.captures.append(
            {
                "path": relative,
                "sha256": sha256_path(path),
                "bytes": path.stat().st_size,
                "dimensions": dimensions,
            }
        )
        return path

    def capture_brightest(
        self,
        relative: str,
        *,
        attempts: int = 10,
        interval: float = 0.25,
    ) -> Path:
        """Capture a deterministic bright phase of a blinking status panel."""
        if attempts < 1:
            raise ValueError("bright-phase capture needs at least one attempt")
        destination = Path(relative)
        candidates: list[tuple[int, Path]] = []
        for attempt in range(1, attempts + 1):
            candidate_relative = (
                Path("transitions/blink")
                / destination.parent
                / f"{destination.stem}_candidate_{attempt:02d}{destination.suffix}"
            )
            candidate = self.capture(str(candidate_relative))
            with Image.open(candidate) as source:
                pixels = source.convert("RGB").get_flattened_data()
                score = sum(
                    red * 299 + green * 587 + blue * 114
                    for red, green, blue in pixels
                )
            candidates.append((score, candidate))
            if attempt < attempts:
                time.sleep(interval)

        _, selected = max(candidates, key=lambda row: row[0])
        path = self.output / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(selected, path)
        with Image.open(path) as image:
            dimensions = [image.width, image.height]
        self.captures.append(
            {
                "path": str(destination),
                "sha256": sha256_path(path),
                "bytes": path.stat().st_size,
                "dimensions": dimensions,
                "blink_phase": "brightest_of_ten",
            }
        )
        return path

    def save_gst(self, relative: str) -> Path:
        self.send(["save:1.0"])
        candidates = sorted(
            self.runtime_home.rglob("quicksave.gst"),
            key=lambda path: path.stat().st_mtime_ns,
        )
        if not candidates:
            raise RuntimeError("BlastEm did not create quicksave.gst")
        destination = self.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidates[-1], destination)
        return destination


def ensure_action_row(
    recorder: RuntimeRecorder,
    phase: str,
    target_row: int,
) -> None:
    if not 0 <= target_row <= 3:
        raise ValueError("preparation action row must be 0..3")

    row: int | None = None
    # Hire END returns to the left commander column. B transfers from that
    # column to the right action list; unlike an unconditional direction tap,
    # inspecting the cursor first cannot move an already focused action row.
    for attempt in range(1, 9):
        probe = recorder.capture(
            f"transitions/{phase}/action_focus_attempt_{attempt}.png"
        )
        row = preparation_action_row(probe)
        if row is not None:
            break
        if preparation_focus_side(probe) == "left":
            recorder.send(["b"], delay=1.1)
        else:
            time.sleep(0.35)
    if row is None:
        raise RuntimeError(f"{phase}: could not focus preparation action list")

    moves = 0
    while row != target_row and moves < 8:
        recorder.send(["down@0.2:0.9"])
        moves += 1
        for blink in range(1, 4):
            probe = recorder.capture(
                f"transitions/{phase}/action_row_move_{moves}_"
                f"blink_{blink}.png"
            )
            detected = preparation_action_row(probe)
            if detected is not None:
                row = detected
                break
            time.sleep(0.2)
    if row != target_row:
        raise RuntimeError(
            f"{phase}: action row {target_row} was not reached (last {row})"
        )


def ensure_commander_column_focus(
    recorder: RuntimeRecorder,
    phase: str,
) -> None:
    """Normalize the preparation root to the left commander column.

    Scenario entry can leave the right action list focused, while returning
    from the shop leaves the left commander column focused.  Both states are
    valid and render every label correctly, but comparing them produces a
    full-panel mismatch. Confirming the selected action transfers focus to
    the commander column without opening a hire/arrangement sub-screen yet.
    """
    last_side: str | None = None
    for attempt in range(1, 5):
        # The cursor and selected-commander palette share a blink cycle. A
        # single fixed-delay capture can repeatedly land on the invisible
        # phase and make menu text look like right-side focus. Sample a full
        # cycle before deciding whether B is needed.
        probe = recorder.capture_brightest(
            f"transitions/{phase}/commander_focus_attempt_{attempt}.png",
            attempts=10,
            interval=0.25,
        )
        last_side = preparation_focus_side(probe)
        if last_side == "left":
            return
        if last_side == "right":
            recorder.send(["c"], delay=1.1)
        else:
            time.sleep(0.35)
    raise RuntimeError(
        f"{phase}: could not focus commander column (last {last_side})"
    )


def scan_allied(
    recorder: RuntimeRecorder,
    phase: str,
    commander_rows: list[dict[str, object]],
) -> None:
    if any(int(row["hire_page_count"]) != 1 for row in commander_rows):
        raise RuntimeError(
            "the preserved canonical seed unexpectedly needs multi-page "
            "hire navigation"
        )
    ensure_commander_column_focus(recorder, phase)
    previous_status: tuple[bool, ...] | None = None
    for index, commander in enumerate(commander_rows):
        position = int(commander["position"])
        commander_id = int(commander["commander_id"])
        relative = f"{phase}/allied/commander_{position:02d}_root.png"
        # The first root can be captured immediately after a long briefing or
        # shop return. Its roster arrows and selected commander palette share
        # a roughly two-second blink cycle, so sample a full cycle. Later rows
        # already have a one-second navigation delay and remain deterministic.
        root = (
            recorder.capture_brightest(relative)
            if position == 1
            else recorder.capture(relative)
        )
        current_status = status_dhash(root)
        if previous_status is not None and hash_distance(
            previous_status, current_status
        ) < 15:
            raise RuntimeError(
                f"{phase}: commander {commander_id} status did not change"
            )

        page: Path | None = None
        for attempt in range(1, 4):
            recorder.send(["c"], delay=1.1)
            probe = recorder.capture(
                f"transitions/{phase}/commander_{position:02d}_"
                f"hire_attempt_{attempt}.png"
            )
            if hire_screen_visible(probe):
                page = recorder.capture(
                    f"{phase}/allied/"
                    f"commander_{position:02d}_hire_page_01.png"
                )
                break
        if page is None:
            raise RuntimeError(
                f"{phase}: commander {commander_id} hire surface did not open"
            )
        if not hire_screen_visible(page):
            raise RuntimeError(
                f"{phase}: commander {commander_id} hire surface was not visible"
            )

        # The first offered row is selected on entry. Up reaches explicit END.
        # If the following C is ignored, retrying C is safe because focus is
        # still on END.
        recorder.send(["up"], delay=1.0)
        exited = False
        for attempt in range(1, 4):
            recorder.send(["c"], delay=1.1)
            probe = recorder.capture(
                f"transitions/{phase}/commander_{position:02d}_"
                f"exit_attempt_{attempt}.png"
            )
            if not hire_screen_visible(probe):
                exited = True
                break
        if not exited:
            raise RuntimeError(
                f"{phase}: commander {commander_id} hire END did not exit"
            )

        previous_status = current_status
        if index + 1 < len(commander_rows):
            selected = False
            for attempt in range(1, 4):
                recorder.send(
                    allied_next_navigation(position, len(commander_rows)),
                    delay=1.0,
                )
                probe = recorder.capture(
                    f"transitions/{phase}/commander_{position + 1:02d}_"
                    f"select_attempt_{attempt}.png"
                )
                if hash_distance(current_status, status_dhash(probe)) >= 15:
                    selected = True
                    break
            if not selected:
                raise RuntimeError(
                    f"{phase}: commander position {position + 1} could not be selected"
                )


def allied_next_navigation(position: int, commander_count: int) -> list[str]:
    if position < 1 or commander_count <= position:
        raise ValueError("commander navigation requires a following position")
    if position % COMMANDER_ROSTER_PAGE_SIZE == 0:
        next_page_rows = min(
            COMMANDER_ROSTER_PAGE_SIZE,
            commander_count - position,
        )
        return ["right"] + ["up"] * (next_page_rows - 1)
    return ["down"]


def open_arrangement(recorder: RuntimeRecorder, phase: str) -> None:
    # Hire END returns to the commander column. Select the absolute 배치 row
    # from observed cursor geometry instead of assuming that every transition
    # key was accepted.
    ensure_action_row(recorder, f"{phase}_arrangement", 3)
    menu: Path | None = None
    for attempt in range(1, 4):
        recorder.send(["c"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/arrangement_open_attempt_{attempt}.png"
        )
        if arrangement_menu_visible(probe):
            menu = recorder.capture(f"{phase}/arrangement/menu.png")
            break
    if menu is None:
        raise RuntimeError(f"{phase}: arrangement menu was not visible")


def scan_arrangement_roster(
    recorder: RuntimeRecorder,
    phase: str,
    roster_page_count: int,
) -> None:
    roster: Path | None = None
    for attempt in range(1, 4):
        recorder.send(["c"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/roster_open_attempt_{attempt}.png"
        )
        if arrangement_roster_visible(probe):
            roster = probe
            break
    if roster is None:
        raise RuntimeError(f"{phase}: arrangement roster did not open")
    for page in range(1, roster_page_count + 1):
        roster = recorder.capture(
            f"{phase}/arrangement/roster_page_{page:02d}.png"
        )
        if not arrangement_roster_visible(roster):
            raise RuntimeError(
                f"{phase}: arrangement roster page {page} was not visible"
            )
        if page < roster_page_count:
            recorder.send(["right"])
    returned = False
    for attempt in range(1, 4):
        recorder.send(["b"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/roster_return_attempt_{attempt}.png"
        )
        if arrangement_menu_visible(probe):
            returned = True
            break
    if not returned:
        raise RuntimeError(f"{phase}: arrangement roster did not return")


def close_fixed_detail(
    recorder: RuntimeRecorder,
    phase: str,
    label: str,
) -> None:
    for attempt in range(1, 4):
        recorder.send(["b"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/{label}_close_attempt_{attempt}.png"
        )
        if not fixed_detail_visible(probe):
            return
    raise RuntimeError(f"{phase}: {label} detail popup did not close")


def open_current_fixed_detail(
    recorder: RuntimeRecorder,
    phase: str,
    record: dict[str, object],
) -> Path:
    for attempt in range(1, 4):
        recorder.send(["c"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/{record_slug(record)}_"
            f"open_attempt_{attempt}.png"
        )
        if fixed_detail_visible(probe):
            detail = recorder.capture(
                f"{phase}/fixed/{record_slug(record)}.png"
            )
            if fixed_detail_visible(detail):
                return detail
    raise RuntimeError(
        f"{phase}: fixed record {record['index']} detail popup did not open"
    )


def save_fixed_detail_checkpoint(
    recorder: RuntimeRecorder,
    phase: str,
    record: dict[str, object],
) -> Path | None:
    if (
        not record.get("runtime_checkpoint_chars")
        and os.environ.get("LANG2_SAVE_ALL_FIXED_DETAIL_GST") != "1"
    ):
        return None
    return recorder.save_gst(
        f"states/{phase}_fixed_{record_slug(record)}.gst"
    )


def scan_fixed_records(
    recorder: RuntimeRecorder,
    phase: str,
    route: list[dict[str, object]],
) -> None:
    if not route:
        return
    # The fourth arrangement row is 적군보기.
    recorder.send(["down", "down", "down"], delay=0.9)
    recorder.send(["c"], delay=1.1)
    entry = recorder.capture(f"{phase}/fixed/map_entry.png")
    first = route[0]
    if fixed_detail_visible(entry):
        first_path = recorder.capture(
            f"{phase}/fixed/{record_slug(first)}.png"
        )
    else:
        first_path = open_current_fixed_detail(recorder, phase, first)
    if not fixed_detail_visible(first_path):
        raise RuntimeError(f"{phase}: first fixed-record detail was not visible")
    save_fixed_detail_checkpoint(recorder, phase, first)

    prior = first
    for record in route[1:]:
        close_fixed_detail(
            recorder,
            phase,
            record_slug(prior),
        )
        recorder.send(["right@0.2:0.8"])
        open_current_fixed_detail(recorder, phase, record)
        save_fixed_detail_checkpoint(recorder, phase, record)
        prior = record

    # Close the detail, then return from the map to the arrangement submenu.
    close_fixed_detail(recorder, phase, record_slug(route[-1]))
    returned: Path | None = None
    for attempt in range(1, 4):
        recorder.send(["b"], delay=1.1)
        probe = recorder.capture(
            f"transitions/{phase}/arrangement_return_attempt_{attempt}.png"
        )
        if arrangement_menu_visible(probe):
            returned = recorder.capture(
                f"{phase}/arrangement/returned_menu.png"
            )
            break
    if returned is None:
        raise RuntimeError(f"{phase}: arrangement menu did not return")
    # The submenu-to-preparation transition includes a black redraw.
    recorder.send(["b"], delay=2.0)


def shop_round_trip(recorder: RuntimeRecorder) -> None:
    ensure_action_row(recorder, "shop", 2)
    recorder.send(["c"], delay=1.2)
    recorder.capture("shop/menu.png")
    recorder.send(["c"], delay=2.5)
    item_list = recorder.capture("shop/item_list.png")
    if bright_ratio(item_list, (8, 24, 312, 215)) < 0.01:
        raise RuntimeError("shop item list was captured before it finished drawing")
    recorder.save_gst("states/shop_item_list.gst")

    returned: Path | None = None
    for attempt in range(1, 4):
        recorder.send(["b"], delay=2.5)
        probe = recorder.capture(
            f"transitions/shop/return_attempt_{attempt}.png"
        )
        if preparation_screen_visible(probe):
            returned = recorder.capture("shop/returned_unfocused.png")
            break
    if returned is None:
        raise RuntimeError("shop B did not return to the preparation surface")

    # The observed source transition returns with right-side 용병고용 focus.
    # C transfers to the commander column. Retry only while the cursor is
    # positively still on the right; an unknown blink phase gets recaptured
    # without another input so it cannot open hire accidentally.
    focused: Path | None = None
    sent_c = False
    for attempt in range(1, 7):
        if not sent_c:
            recorder.send(["c"], delay=1.5)
            sent_c = True
        probe = recorder.capture(
            f"transitions/shop/focus_attempt_{attempt}.png"
        )
        side = preparation_focus_side(probe)
        if side == "left":
            focused = recorder.capture("shop/returned_focused.png")
            break
        if side == "right":
            sent_c = False
        else:
            time.sleep(0.3)
    if focused is None or not preparation_screen_visible(focused):
        raise RuntimeError("shop return did not restore preparation focus")


def capture_pairs(output: Path) -> list[dict[str, object]]:
    rows = []
    for pre in sorted((output / "pre").rglob("*.png")):
        relative = pre.relative_to(output / "pre")
        post = output / "post" / relative
        if not post.exists():
            continue
        pre_sha = sha256_path(pre)
        post_sha = sha256_path(post)
        rows.append(
            {
                "surface": str(relative),
                "pre_sha256": pre_sha,
                "post_sha256": post_sha,
                "byte_identical": pre_sha == post_sha,
            }
        )
    return rows


def launch_to_preparation(
    recorder: RuntimeRecorder,
    rom: Path,
    seed_gst: Path,
    scenario_number: int,
    runtime_name: str,
    output: Path,
    manual_slot_args: list[str] | None = None,
    diagnostic_exact_overrides: (
        dict[tuple[int, int], dict[str, int]] | None
    ) = None,
) -> dict[str, object]:
    last_error: Exception | None = None
    for attempt in range(1, PREPARATION_LAUNCH_ATTEMPTS + 1):
        command = [
                sys.executable,
                str(RUN_SEQUENCE),
                "scenario-select",
                "--rom",
                str(rom),
                "--scenario-number",
                str(scenario_number),
                "--runtime-name",
                runtime_name,
                "--runtime-root",
                str(recorder.runtime_home.parent),
                "--manual-slot-gst",
                str(seed_gst),
                "--initial-delay",
                "6.0",
                "--virtual-display",
                recorder.display,
                "--replace-existing",
                "--send-event",
            ]
        if manual_slot_args:
            command.extend(manual_slot_args)
        recorder.run_command(command)
        try:
            recorder.run_command(
                [
                    sys.executable,
                    str(RUN_SEQUENCE),
                    "detect-prep",
                    "--rom",
                    str(rom),
                    "--no-launch",
                    "--confirmation-delay",
                    "0.8",
                    "--max-confirmations",
                    "80",
                    "--capture-prefix",
                    str(output / f"briefing/attempt_{attempt}/detect.png"),
                    "--virtual-display",
                    recorder.display,
                    "--send-event",
                ]
            )
            identity_gst = recorder.save_gst(
                f"briefing/attempt_{attempt}/scenario_identity.gst"
            )
            identity = verify_runtime_scenario_identity(
                identity_gst,
                rom,
                scenario_number,
                diagnostic_exact_overrides=diagnostic_exact_overrides,
            )
            identity["attempt"] = attempt
            return identity
        except (subprocess.CalledProcessError, RuntimeError, ValueError) as exc:
            last_error = exc
            terminate_blastem_processes(display=recorder.display)
    if last_error is None:
        raise AssertionError("preparation launch retry loop did not run")
    raise last_error


def run_matrix_capture(
    profile: str,
    rom: Path,
    reference_rom: Path,
    seed_gst: Path,
    scenario_number: int,
    display: str,
    output_root: Path,
    runtime_root: Path,
    run_id: str,
) -> dict[str, object]:
    output = output_root / profile / f"s{scenario_number:02d}" / run_id
    if output.exists():
        raise FileExistsError(
            f"output already exists; choose a new --run-id: {output}"
        )
    output.mkdir(parents=True)
    runtime_name = (
        f"prep-surface-{profile}-s{scenario_number:02d}-{run_id}"
    )
    if Path(runtime_name).name != runtime_name:
        raise ValueError("--run-id must produce one safe runtime directory name")
    runtime_home = runtime_root / runtime_name
    recorder = RuntimeRecorder(output, display, runtime_home)
    plan = build_plan(rom, reference_rom, seed_gst, scenario_number)
    (output / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    commander_rows = plan["allied_commanders"]["seed_records"]
    route = plan["fixed_records"]["route"]
    roster_pages = int(plan["allied_commanders"]["roster_page_count"])
    started = time.time()
    try:
        scenario_identity = launch_to_preparation(
            recorder,
            rom,
            seed_gst,
            scenario_number,
            runtime_name,
            output,
        )
        recorder.capture("pre/root.png")
        scan_allied(recorder, "pre", commander_rows)
        open_arrangement(recorder, "pre")
        scan_arrangement_roster(recorder, "pre", roster_pages)
        scan_fixed_records(recorder, "pre", route)
        recorder.save_gst("states/pre_shop.gst")

        shop_round_trip(recorder)
        recorder.save_gst("states/shop_returned.gst")

        scan_allied(recorder, "post", commander_rows)
        open_arrangement(recorder, "post")
        scan_arrangement_roster(recorder, "post", roster_pages)
        scan_fixed_records(recorder, "post", route)
        recorder.save_gst("states/post_shop.gst")

        pairs = capture_pairs(output)
        expected_pair_count = (
            sum(
                1 + int(commander["hire_page_count"])
                for commander in commander_rows
            )
            + roster_pages
            + len(route)
            + 3  # arrangement menu, map entry, and returned submenu
        )
        fixed_hashes = {
            sha256_path(output / "pre/fixed" / f"{record_slug(row)}.png")
            for row in route
        }
        all_exact = (
            len(pairs) == expected_pair_count
            and all(row["byte_identical"] for row in pairs)
        )
        result = {
            "schema_version": 1,
            "status": (
                "captured_exact_unreviewed"
                if all_exact
                else "captured_mismatch_unreviewed"
            ),
            "acceptance_updated": False,
            "profile": profile,
            "scenario": scenario_number,
            "run_id": run_id,
            "elapsed_seconds": round(time.time() - started, 3),
            "scenario_identity": scenario_identity,
            "expected_pair_count": expected_pair_count,
            "actual_pair_count": len(pairs),
            "distinct_pre_fixed_detail_count": len(fixed_hashes),
            "capture_pairs": pairs,
            "captures": recorder.captures,
            "actions": recorder.actions,
            "required_human_review": [
                "all Korean commander, class, and offered mercenary labels",
                "full minimap and tile-row integrity",
                "all commander and mercenary sprites",
                "gray acted sprites and result screens in a separate battle run",
            ],
            "limitations": [
                "class-change choices are only applicable when the live seed exposes them",
                "hidden or (255,255) fixed records are source-not-applicable here",
                "gray acted sprites and battle result screens are not exercised by this preparation run",
            ],
        }
        (output / "evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result
    except Exception as exc:
        failure_gst: str | None = None
        try:
            failure_state = recorder.save_gst("states/failure.gst")
            failure_gst = str(failure_state.relative_to(output))
        except Exception:
            pass
        failure = {
            "schema_version": 1,
            "status": "failed_attempt",
            "acceptance_updated": False,
            "profile": profile,
            "scenario": scenario_number,
            "run_id": run_id,
            "elapsed_seconds": round(time.time() - started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failure_gst": failure_gst,
            "captures": recorder.captures,
            "actions": recorder.actions,
        }
        (output / "failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        terminate_blastem_processes(display=display)


def validate_scenario(value: str) -> int:
    number = int(value)
    if not SCENARIO_MIN <= number <= SCENARIO_MAX:
        raise argparse.ArgumentTypeError(
            f"scenario must be {SCENARIO_MIN}..{SCENARIO_MAX}"
        )
    return number


def validate_run_id(value: str) -> str:
    if not value or Path(value).name != value or value in {".", ".."}:
        raise argparse.ArgumentTypeError("run ID must be one directory name")
    if not all(character.isalnum() or character in "-_" for character in value):
        raise argparse.ArgumentTypeError(
            "run ID may contain only letters, digits, '-' and '_'"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or capture the same-run Korean preparation/shop surface matrix. "
            "Runtime output remains unreviewed and never changes acceptance state."
        )
    )
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--profile", choices=sorted(PROFILE_ROMS), required=True)
    parser.add_argument("--scenario", type=validate_scenario, required=True)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--reference-rom", type=Path, default=DEFAULT_REFERENCE_ROM)
    parser.add_argument("--seed-gst", type=Path, default=DEFAULT_SEED_GST)
    parser.add_argument("--display", default=DEFAULT_DISPLAY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--run-id", type=validate_run_id)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rom = args.rom or PROFILE_ROMS[args.profile]
    for label, path in (
        ("ROM", rom),
        ("reference ROM", args.reference_rom),
        ("seed GST", args.seed_gst),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")

    if args.command == "plan":
        plan = build_plan(
            rom,
            args.reference_rom,
            args.seed_gst,
            args.scenario,
        )
        encoded = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            print(encoded, end="")
        else:
            if args.output.exists():
                raise FileExistsError(f"refusing to overwrite {args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        return 0

    if args.run_id is None:
        parser.error("run requires --run-id")
    if args.output is not None:
        parser.error("--output is only valid with plan")
    result = run_matrix_capture(
        args.profile,
        rom,
        args.reference_rom,
        args.seed_gst,
        args.scenario,
        args.display,
        args.output_root,
        args.runtime_root,
        args.run_id,
    )
    print(
        f"{result['status']}: {result['actual_pair_count']}/"
        f"{result['expected_pair_count']} pre/post pairs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
