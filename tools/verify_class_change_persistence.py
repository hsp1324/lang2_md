#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_blastem_sequence import (
    MANUAL_SLOT_BASES,
    MANUAL_SLOT_CHECKSUM_OFFSET,
    MANUAL_SLOT_COMMANDER_AT_OFFSET,
    MANUAL_SLOT_COMMANDER_CLASS_OFFSET,
    MANUAL_SLOT_COMMANDER_DF_OFFSET,
    MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET,
    MANUAL_SLOT_COMMANDER_LEVEL_OFFSET,
    MANUAL_SLOT_COMMANDER_RECORD_SIZE,
    MANUAL_SLOT_COMMANDER_ROSTER_OFFSET,
    manual_slot_checksum,
    manual_slot_scenario_number,
)


def commander_progress(
    sram_path: Path,
    *,
    slot_index: int,
    commander_id: int,
) -> dict[str, int]:
    if not 1 <= commander_id <= 10:
        raise ValueError("commander ID must be 1..10")
    scenario = manual_slot_scenario_number(sram_path, slot_index)
    data = sram_path.read_bytes()
    base = MANUAL_SLOT_BASES[slot_index]
    record = (
        base
        + MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        + (commander_id - 1) * MANUAL_SLOT_COMMANDER_RECORD_SIZE
    )
    checksum_offset = base + MANUAL_SLOT_CHECKSUM_OFFSET
    return {
        "slot": slot_index + 1,
        "scenario": scenario,
        "commander_id": commander_id,
        "class_id": data[record + MANUAL_SLOT_COMMANDER_CLASS_OFFSET],
        "level": data[record + MANUAL_SLOT_COMMANDER_LEVEL_OFFSET],
        "experience": data[record + MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET],
        "at": data[record + MANUAL_SLOT_COMMANDER_AT_OFFSET],
        "df": data[record + MANUAL_SLOT_COMMANDER_DF_OFFSET],
        "checksum": int.from_bytes(
            data[checksum_offset : checksum_offset + 2],
            "big",
        ),
        "calculated_checksum": manual_slot_checksum(data, base),
    }


def verify_progress(
    sram_path: Path,
    *,
    slot_index: int,
    commander_id: int,
    expected_scenario: int,
    expected_class: int,
    expected_level: int | None = None,
    expected_experience: int | None = None,
) -> dict[str, int]:
    progress = commander_progress(
        sram_path,
        slot_index=slot_index,
        commander_id=commander_id,
    )
    expected = {
        "scenario": expected_scenario,
        "class_id": expected_class,
    }
    if expected_level is not None:
        expected["level"] = expected_level
    if expected_experience is not None:
        expected["experience"] = expected_experience
    mismatches = [
        f"{field}={progress[field]} (expected {value})"
        for field, value in expected.items()
        if progress[field] != value
    ]
    if mismatches:
        raise ValueError("class-change save mismatch: " + ", ".join(mismatches))
    return progress


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that a class-change result survived a valid manual "
            "scenario-clear save"
        )
    )
    parser.add_argument("--sram", type=Path, required=True)
    parser.add_argument("--slot", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--commander-id", type=int, required=True)
    parser.add_argument("--scenario", type=int, required=True)
    parser.add_argument("--class-id", type=parse_int, required=True)
    parser.add_argument("--level", type=int)
    parser.add_argument("--experience", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    progress = verify_progress(
        args.sram,
        slot_index=args.slot - 1,
        commander_id=args.commander_id,
        expected_scenario=args.scenario,
        expected_class=args.class_id,
        expected_level=args.level,
        expected_experience=args.experience,
    )
    print(json.dumps(progress, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
