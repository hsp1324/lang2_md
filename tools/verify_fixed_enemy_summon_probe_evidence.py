#!/usr/bin/env python3
"""Verify the retained Scenario 27 fixed-enemy summon runtime evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GST = ROOT / "captures/analysis/a205_s27_fixed_summon_loaded.gst"

GST_WORK_RAM_FILE_OFFSET = 0x2478
RUNTIME_RECORD_BASE = 0x603C
RUNTIME_RECORD_SIZE = 0x60
MEMBER_RECORD_SIZE = 0x0C
TARGET_RUNTIME_GROUP = 17
TARGET_COMMANDER_CLASS = 0x5F
TARGET_COMMANDER_NAME_ID = 0x4A
TARGET_COMMANDER_LEVEL = 10
EXPECTED_MEMBERS = (
    (0x5F, 15, 8),
    (0x89, 14, 8),
    (0x89, 16, 8),
    (0x89, 15, 7),
    (0x89, 15, 9),
    (0x8F, 14, 9),
    (0x8F, 16, 7),
    (0xFF, 0, 0),
)


@dataclass(frozen=True)
class RuntimeMember:
    class_id: int
    x: int
    y: int


@dataclass(frozen=True)
class RuntimeGroup:
    class_id: int
    name_id: int
    level: int
    members: tuple[RuntimeMember, ...]


def read_runtime_group(
    gst: bytes,
    group_index: int = TARGET_RUNTIME_GROUP,
) -> RuntimeGroup:
    if group_index < 0:
        raise ValueError("runtime group index must be non-negative")
    offset = (
        GST_WORK_RAM_FILE_OFFSET
        + RUNTIME_RECORD_BASE
        + group_index * RUNTIME_RECORD_SIZE
    )
    end = offset + RUNTIME_RECORD_SIZE
    if len(gst) < end:
        raise ValueError(
            f"GST is too short to contain runtime group {group_index}"
        )
    data = gst[offset:end]
    members = tuple(
        RuntimeMember(
            class_id=data[index * MEMBER_RECORD_SIZE],
            x=data[index * MEMBER_RECORD_SIZE + 6],
            y=data[index * MEMBER_RECORD_SIZE + 7],
        )
        for index in range(RUNTIME_RECORD_SIZE // MEMBER_RECORD_SIZE)
    )
    return RuntimeGroup(
        class_id=data[0],
        name_id=data[1],
        level=data[0x2E],
        members=members,
    )


def verify_runtime_group(group: RuntimeGroup) -> None:
    identity = (group.class_id, group.name_id, group.level)
    expected_identity = (
        TARGET_COMMANDER_CLASS,
        TARGET_COMMANDER_NAME_ID,
        TARGET_COMMANDER_LEVEL,
    )
    if identity != expected_identity:
        raise ValueError(
            "expected Vampire Lord runtime identity "
            f"{expected_identity!r}, found {identity!r}"
        )
    actual_members = tuple(
        (member.class_id, member.x, member.y) for member in group.members
    )
    if actual_members != EXPECTED_MEMBERS:
        raise ValueError(
            "fixed-enemy summon runtime members differ from the accepted "
            f"Scenario 27 evidence: {actual_members!r}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gst", type=Path, default=DEFAULT_GST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    group = read_runtime_group(args.gst.read_bytes())
    verify_runtime_group(group)
    print(
        "verified Scenario 27 runtime group 17: "
        "Vampire Lord with four Arc Demons and two fixed White Dragons"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
