#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_magic_application_probe_rom as magic_probe
from tools import build_natural_summon_probe_rom as natural_probe
from tools.class_ability_data import (
    SUMMON_ABILITY_ID,
    ability_ids_from_runtime_mask,
)
from tools.verify_natural_summon_evidence import (
    BROTHER_CLASS,
    DEFAULT_BEFORE,
    HEIN_COMMANDER_ID,
    SUMMONER_CLASS,
    SummonRuntime,
    read_runtime,
)


DEFAULT_AFTER = ROOT / "captures/analysis/7256_natural_magic_attack_after.gst"
DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
PROBE_CHECKSUM = 0x7256
NATURAL_MAGIC_IDS = (0, 1, 2, 4, 7, 10, 14, 16, 17, 19, 20)
ATTACK_MAGIC_ID = 16
ATTACK_MP_COST = 2


def validate_stock_magic_path(
    probe: bytes | bytearray,
    source: bytes | bytearray,
) -> None:
    regions = (
        (
            magic_probe.ALL_MAGIC_BRANCH_OFFSET,
            magic_probe.ALL_MAGIC_BRANCH_SOURCE,
        ),
        (
            magic_probe.MAGIC_MP_BRANCH_OFFSET,
            magic_probe.MAGIC_MP_BRANCH_SOURCE,
        ),
    )
    for offset, expected in regions:
        if source[offset : offset + len(expected)] != expected:
            raise ValueError(
                f"Japanese magic path changed at 0x{offset:06X}"
            )
        if probe[offset : offset + len(expected)] != expected:
            raise ValueError(
                f"natural probe magic path changed at 0x{offset:06X}"
            )


def verify_probe_rom(
    probe: bytes | bytearray,
    source: bytes | bytearray,
) -> None:
    checksum = int.from_bytes(probe[0x18E:0x190], "big")
    if checksum != PROBE_CHECKSUM:
        raise ValueError(
            f"expected natural probe checksum 0x{PROBE_CHECKSUM:04X}, "
            f"found 0x{checksum:04X}"
        )
    natural_probe.validate_stock_summon_path(probe, source)
    validate_stock_magic_path(probe, source)


def verify(before: SummonRuntime, after: SummonRuntime) -> None:
    expected_identity = (SUMMONER_CLASS, HEIN_COMMANDER_ID, 2, 0)
    for label, state in (("before", before), ("after", after)):
        identity = (
            state.class_id,
            state.commander_id,
            state.level,
            state.experience,
        )
        if identity != expected_identity:
            raise ValueError(
                f"{label} is not Hein Summoner LV2/EXP0: {identity!r}"
            )
        ability_ids = ability_ids_from_runtime_mask(state.command_flags)
        magic_ids = tuple(
            ability_id
            for ability_id in ability_ids
            if ability_id != SUMMON_ABILITY_ID
        )
        if magic_ids != NATURAL_MAGIC_IDS:
            raise ValueError(
                f"{label} natural magic IDs changed: {magic_ids!r}"
            )
        if SUMMON_ABILITY_ID not in ability_ids:
            raise ValueError(f"{label} lost the natural summon ability")
        if state.summoned_class != 0xFF:
            raise ValueError(
                f"{label} unexpectedly contains summoned class "
                f"0x{state.summoned_class:02X}"
            )

    if before.command_flags != after.command_flags:
        raise ValueError(
            "Attack application changed Hein's learned command flags"
        )
    if before.current_mp - after.current_mp != ATTACK_MP_COST:
        raise ValueError(
            f"expected Attack to consume {ATTACK_MP_COST} MP, found "
            f"{before.current_mp}->{after.current_mp}"
        )
    if after.summoned_class == BROTHER_CLASS:
        raise ValueError("natural magic evidence accidentally contains Brother")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify retained GST evidence for Hein's naturally accumulated "
            "magic list and stock 2-MP Attack application."
        )
    )
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    parser.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    parser.add_argument(
        "--probe-rom",
        type=Path,
        help=(
            "optional exact checksum-7256 diagnostic ROM; when supplied, "
            "also verify its checksum and source-locked magic/summon regions"
        ),
    )
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.probe_rom is not None:
        verify_probe_rom(
            args.probe_rom.read_bytes(),
            args.source_rom.read_bytes(),
        )
    before = read_runtime(args.before.read_bytes())
    after = read_runtime(args.after.read_bytes())
    verify(before, after)
    print(
        "verified 11 natural magic IDs, summon ability, Attack MP 16->14, "
        "and no summoned member"
        + (
            "; exact probe checksum and source-locked branches also verified"
            if args.probe_rom is not None
            else ""
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
