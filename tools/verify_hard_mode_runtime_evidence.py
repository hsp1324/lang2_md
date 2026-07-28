#!/usr/bin/env python3
"""Verify retained emulator evidence for the Standard Hard runtime loader."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GST = ROOT / "captures/analysis/0718_hard_s01_turn1_command.gst"

GST_WORK_RAM_FILE_OFFSET = 0x2478
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
RUNTIME_MEMBER_SIZE = 0x0C
RUNTIME_LEVEL_OFFSET = 0x2E
RUNTIME_COMMANDER_AT_OFFSET = 0x3A
RUNTIME_COMMANDER_DF_OFFSET = 0x3B
RUNTIME_SOLDIER_AT_OFFSET = 0x46
RUNTIME_SOLDIER_DF_OFFSET = 0x47

SCENARIO_ONE_PLAYER_GROUPS = 2
SCENARIO_ONE_EXPECTED_GST_SHA256 = (
    "a9be34a13f38616617ce806f6b63821d1c15433b44e4e9e5d1ef1394b09a9256"
)


@dataclass(frozen=True)
class ExpectedRuntimeGroup:
    fixed_record_index: int
    fixed_record_offset: int
    name: str
    class_id: int
    name_id: int
    level: int
    commander_at: int
    commander_df: int
    soldier_at: int
    soldier_df: int
    mercenaries: tuple[int, ...]
    hard_target: bool

    @property
    def runtime_group_index(self) -> int:
        return SCENARIO_ONE_PLAYER_GROUPS + self.fixed_record_index


@dataclass(frozen=True)
class RuntimeGroup:
    class_id: int
    name_id: int
    level: int
    commander_at: int
    commander_df: int
    soldier_at: int
    soldier_df: int
    mercenaries: tuple[int, ...]


SCENARIO_ONE_GROUPS = (
    ExpectedRuntimeGroup(
        fixed_record_index=8,
        fixed_record_offset=0x1802D8,
        name="발드",
        class_id=0x2E,
        name_id=0x12,
        level=4,
        commander_at=23,
        commander_df=19,
        soldier_at=3,
        soldier_df=1,
        mercenaries=(0x72,) * 6,
        hard_target=True,
    ),
    ExpectedRuntimeGroup(
        fixed_record_index=9,
        fixed_record_offset=0x1802FC,
        name="레온",
        class_id=0x45,
        name_id=0x0D,
        level=4,
        commander_at=40,
        commander_df=31,
        soldier_at=11,
        soldier_df=8,
        mercenaries=(0x7B, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF),
        hard_target=False,
    ),
    ExpectedRuntimeGroup(
        fixed_record_index=10,
        fixed_record_offset=0x180320,
        name="레아드",
        class_id=0x37,
        name_id=0x11,
        level=6,
        commander_at=33,
        commander_df=25,
        soldier_at=6,
        soldier_df=4,
        mercenaries=(0x7A, 0x7A, 0xFF, 0xFF, 0xFF, 0xFF),
        hard_target=False,
    ),
    ExpectedRuntimeGroup(
        fixed_record_index=11,
        fixed_record_offset=0x180344,
        name="제국지휘관",
        class_id=0x2D,
        name_id=0x2A,
        level=1,
        commander_at=21,
        commander_df=19,
        soldier_at=1,
        soldier_df=3,
        mercenaries=(0x72,) * 6,
        hard_target=True,
    ),
)


def read_runtime_group(gst: bytes, group_index: int) -> RuntimeGroup:
    if group_index < 0:
        raise ValueError("runtime group index must be non-negative")
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
    return RuntimeGroup(
        class_id=record[0],
        name_id=record[1],
        level=record[RUNTIME_LEVEL_OFFSET],
        commander_at=record[RUNTIME_COMMANDER_AT_OFFSET],
        commander_df=record[RUNTIME_COMMANDER_DF_OFFSET],
        soldier_at=record[RUNTIME_SOLDIER_AT_OFFSET],
        soldier_df=record[RUNTIME_SOLDIER_DF_OFFSET],
        mercenaries=tuple(
            record[member_index * RUNTIME_MEMBER_SIZE]
            for member_index in range(1, 7)
        ),
    )


def expected_runtime_group(expected: ExpectedRuntimeGroup) -> RuntimeGroup:
    return RuntimeGroup(
        class_id=expected.class_id,
        name_id=expected.name_id,
        level=expected.level,
        commander_at=expected.commander_at,
        commander_df=expected.commander_df,
        soldier_at=expected.soldier_at,
        soldier_df=expected.soldier_df,
        mercenaries=expected.mercenaries,
    )


def verify_scenario_one(gst: bytes) -> tuple[RuntimeGroup, ...]:
    actual_groups = []
    for expected in SCENARIO_ONE_GROUPS:
        actual = read_runtime_group(gst, expected.runtime_group_index)
        wanted = expected_runtime_group(expected)
        if actual != wanted:
            raise ValueError(
                f"Scenario 1 {expected.name} runtime group "
                f"{expected.runtime_group_index} differs: "
                f"expected {wanted!r}, found {actual!r}"
            )
        actual_groups.append(actual)
    return tuple(actual_groups)


def verify_evidence(path: Path = DEFAULT_GST) -> tuple[RuntimeGroup, ...]:
    gst = path.read_bytes()
    digest = hashlib.sha256(gst).hexdigest()
    if path.resolve() == DEFAULT_GST.resolve():
        if digest != SCENARIO_ONE_EXPECTED_GST_SHA256:
            raise ValueError(
                "retained Scenario 1 GST hash changed: "
                f"{digest} != {SCENARIO_ONE_EXPECTED_GST_SHA256}"
            )
    return verify_scenario_one(gst)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the Standard Hard Scenario 1 runtime AT/DF, soldier "
            "corrections, mercenaries, and excluded scripted commanders"
        )
    )
    parser.add_argument("--gst", type=Path, default=DEFAULT_GST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    groups = verify_evidence(args.gst)
    for expected, actual in zip(SCENARIO_ONE_GROUPS, groups):
        target = "hard target" if expected.hard_target else "excluded"
        print(
            f"S1 group {expected.runtime_group_index:02d} "
            f"{expected.name} ({target}): "
            f"AT/DF {actual.commander_at}/{actual.commander_df}, "
            f"soldier {actual.soldier_at}/{actual.soldier_df}, "
            "mercs "
            + " ".join(f"{value:02X}" for value in actual.mercenaries)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
