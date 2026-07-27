#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_class_change_probe_rom as class_probe
from tools.capture_magic_application import (
    CURRENT_MP_OFFSET,
    MAX_MP_OFFSET,
)
from tools.capture_summon_application import (
    MEMBER_RECORD_SIZE,
    SUMMONED_MEMBER_INDEX,
)
from tools.run_blastem_sequence import GST_WORK_RAM_FILE_OFFSET


DEFAULT_BEFORE = ROOT / "captures/analysis/7256_natural_summon_before.gst"
DEFAULT_AFTER = ROOT / "captures/analysis/7256_natural_summon_brother_after.gst"
HEIN_RUNTIME_RECORD = 1
SUMMONER_CLASS = 0x28
HEIN_COMMANDER_ID = 5
SUMMON_ABILITY_MASK = 1 << 23
IRON_DUMBBELL_ITEM_ID = 0x0B
BROTHER_CLASS = 0x94


@dataclass(frozen=True)
class SummonRuntime:
    class_id: int
    commander_id: int
    level: int
    experience: int
    current_mp: int
    max_mp: int
    equipment: tuple[int, int, int]
    command_flags: int
    summoned_class: int
    summoned_x: int
    summoned_y: int


def read_runtime(gst: bytes) -> SummonRuntime:
    record = class_probe.runtime_record_address(HEIN_RUNTIME_RECORD) & 0xFFFF
    offset = GST_WORK_RAM_FILE_OFFSET + record
    end = offset + class_probe.RUNTIME_RECORD_SIZE
    if len(gst) < end:
        raise ValueError("GST is too short to contain Hein's runtime group")
    data = gst[offset:end]
    member = SUMMONED_MEMBER_INDEX * MEMBER_RECORD_SIZE
    return SummonRuntime(
        class_id=data[class_probe.ELWIN_CLASS_OFFSET],
        commander_id=data[0x01],
        level=data[class_probe.ELWIN_LEVEL_OFFSET],
        experience=data[class_probe.ELWIN_EXPERIENCE_OFFSET],
        current_mp=data[CURRENT_MP_OFFSET],
        max_mp=data[MAX_MP_OFFSET],
        equipment=(data[0x09], data[0x0A], data[0x0B]),
        command_flags=int.from_bytes(data[0x50:0x54], "big"),
        summoned_class=data[member],
        summoned_x=data[member + 0x06],
        summoned_y=data[member + 0x07],
    )


def verify(before: SummonRuntime, after: SummonRuntime) -> None:
    expected_identity = (SUMMONER_CLASS, HEIN_COMMANDER_ID, 2, 0)
    before_identity = (
        before.class_id,
        before.commander_id,
        before.level,
        before.experience,
    )
    after_identity = (
        after.class_id,
        after.commander_id,
        after.level,
        after.experience,
    )
    if before_identity != expected_identity or after_identity != expected_identity:
        raise ValueError(
            "expected Hein Summoner LV2/EXP0 before and after summon, found "
            f"{before_identity!r} and {after_identity!r}"
        )
    if not before.command_flags & SUMMON_ABILITY_MASK:
        raise ValueError("natural pre-summon state is missing command bit 23")
    if not after.command_flags & SUMMON_ABILITY_MASK:
        raise ValueError("post-summon state lost command bit 23")
    if before.current_mp != 16 or before.max_mp != 18:
        raise ValueError(
            f"expected pre-summon MP 16/18, found {before.current_mp}/{before.max_mp}"
        )
    if after.current_mp != 1 or after.max_mp != 20:
        raise ValueError(
            f"expected post-summon MP 1/20, found {after.current_mp}/{after.max_mp}"
        )
    if after.equipment[0] != IRON_DUMBBELL_ITEM_ID:
        raise ValueError(
            f"expected iron dumbbell item 0x0B, found {after.equipment!r}"
        )
    summoned = (
        after.summoned_class,
        after.summoned_x,
        after.summoned_y,
    )
    if summoned != (BROTHER_CLASS, 14, 20):
        raise ValueError(
            "expected Brother class 0x94 at (14,20), found "
            f"(0x{summoned[0]:02X},{summoned[1]},{summoned[2]})"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify retained GST evidence for natural Summoner ownership and "
            "the stock 15-MP Brother application path."
        )
    )
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    parser.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    before = read_runtime(args.before.read_bytes())
    after = read_runtime(args.after.read_bytes())
    verify(before, after)
    print(
        "verified natural summon bit 23, iron dumbbell 0x0B, "
        "MP 16->1, and Brother class 0x94 at (14,20)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
