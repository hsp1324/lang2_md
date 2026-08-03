#!/usr/bin/env python3
"""Verify retained fixed-enemy summon loading and ordinary-AI evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GST = ROOT / "captures/analysis/a205_s27_fixed_summon_loaded.gst"
DEFAULT_AI_PRE_GST = (
    ROOT
    / "captures/analysis/9a15_s26_fixed_white_dragon_pre_enemy_turn.gst"
)
DEFAULT_AI_POST_GST = (
    ROOT
    / "captures/analysis/9a15_s26_fixed_white_dragon_post_gameover.gst"
)
DEFAULT_ATTACK_CAPTURE = (
    ROOT
    / "captures/run/d947_s26_fixed_white_dragon_direct_attack.png"
)
ATTACK_CAPTURE_SHA256 = (
    "b3b3880f9246529465ea7044d90d35a5a14bd1ab6421d0d1e57ed9fe28d4cf27"
)
ATTACK_PROBE_CHECKSUM = "D947"
ATTACK_PROBE_SHA256 = (
    "b4b2023243f001d13df16d8b3cc8c5e764de914be00d4ace9985ee6a41505a7c"
)

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
AI_RUNTIME_GROUP = 10
AI_COMMANDER_CLASS = 0x42
AI_COMMANDER_NAME_ID = 0x2A
AI_COMMANDER_LEVEL = 5
AI_WHITE_DRAGON_MEMBER_INDEX = 6
AI_EXPECTED_PRE_MEMBERS = (
    (0x42, 24, 20),
    (0x76, 23, 20),
    (0x76, 25, 20),
    (0x76, 24, 19),
    (0x76, 24, 21),
    (0x77, 23, 21),
    (0x8F, 25, 19),
    (0xFF, 0, 0),
)
AI_EXPECTED_POST_MEMBERS = (
    (0x42, 24, 20),
    (0x76, 23, 20),
    (0x76, 23, 17),
    (0x76, 25, 20),
    (0x76, 24, 19),
    (0x77, 25, 21),
    (0x8F, 24, 21),
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


def _member_tuples(group: RuntimeGroup) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (member.class_id, member.x, member.y) for member in group.members
    )


def verify_ordinary_ai_evidence(
    before: RuntimeGroup,
    after: RuntimeGroup,
) -> None:
    expected_identity = (
        AI_COMMANDER_CLASS,
        AI_COMMANDER_NAME_ID,
        AI_COMMANDER_LEVEL,
    )
    for label, group in (("pre-turn", before), ("post-event", after)):
        identity = (group.class_id, group.name_id, group.level)
        if identity != expected_identity:
            raise ValueError(
                f"{label} ordinary-AI identity changed: "
                f"expected {expected_identity!r}, found {identity!r}"
            )

    before_members = _member_tuples(before)
    after_members = _member_tuples(after)
    if before_members != AI_EXPECTED_PRE_MEMBERS:
        raise ValueError(
            "ordinary-AI pre-turn members differ from accepted Scenario 26 "
            f"evidence: {before_members!r}"
        )
    if after_members != AI_EXPECTED_POST_MEMBERS:
        raise ValueError(
            "ordinary-AI post-event members differ from accepted Scenario 26 "
            f"evidence: {after_members!r}"
        )

    before_dragon = before.members[AI_WHITE_DRAGON_MEMBER_INDEX]
    after_dragon = after.members[AI_WHITE_DRAGON_MEMBER_INDEX]
    if before_dragon.class_id != 0x8F or after_dragon.class_id != 0x8F:
        raise ValueError("ordinary-AI evidence lost the fixed White Dragon")
    if (before_dragon.x, before_dragon.y) == (
        after_dragon.x,
        after_dragon.y,
    ):
        raise ValueError("fixed White Dragon did not move under ordinary AI")


def verify_attack_capture(path: Path = DEFAULT_ATTACK_CAPTURE) -> None:
    if not path.is_file():
        raise ValueError(f"fixed White Dragon attack capture is missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != ATTACK_CAPTURE_SHA256:
        raise ValueError(
            "fixed White Dragon attack capture changed: "
            f"{digest} != {ATTACK_CAPTURE_SHA256}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gst", type=Path, default=DEFAULT_GST)
    parser.add_argument(
        "--ai-pre-gst",
        type=Path,
        default=DEFAULT_AI_PRE_GST,
    )
    parser.add_argument(
        "--ai-post-gst",
        type=Path,
        default=DEFAULT_AI_POST_GST,
    )
    parser.add_argument(
        "--attack-capture",
        type=Path,
        default=DEFAULT_ATTACK_CAPTURE,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    group = read_runtime_group(args.gst.read_bytes())
    verify_runtime_group(group)
    before = read_runtime_group(
        args.ai_pre_gst.read_bytes(),
        AI_RUNTIME_GROUP,
    )
    after = read_runtime_group(
        args.ai_post_gst.read_bytes(),
        AI_RUNTIME_GROUP,
    )
    verify_ordinary_ai_evidence(before, after)
    verify_attack_capture(args.attack_capture)
    print(
        "verified Scenario 27 runtime group 17: "
        "Vampire Lord with four Arc Demons and two fixed White Dragons; "
        "verified Scenario 26 runtime group 10: fixed White Dragon moved "
        "from (25,19) to (24,21) under ordinary enemy AI; "
        "verified D947 direct-attack capture"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
