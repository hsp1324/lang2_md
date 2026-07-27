#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Korean Summon Apply Probe).md"
)

SUMMON_COMMAND_BRANCH_OFFSET = 0x020DFA
SUMMON_COMMAND_BRANCH_SOURCE = bytes.fromhex("67 1C")
SUMMON_COMMAND_BRANCH_PATCH = bytes.fromhex("4E 71")
ALL_SUMMON_BRANCH_OFFSET = 0x021724
ALL_SUMMON_BRANCH_SOURCE = bytes.fromhex("67 00 00 1A")
ALL_SUMMON_BRANCH_PATCH = bytes.fromhex("4E 71 4E 71")
SUMMON_MP_BRANCH_OFFSET = 0x021938
SUMMON_MP_BRANCH_SOURCE = bytes.fromhex("66 00 00 CE")
SUMMON_MP_BRANCH_PATCH = bytes.fromhex("60 00 00 CE")
SUMMON_DATA_TABLE = 0x0820F4
SUMMON_DATA_RECORD_SIZE = 4
SUMMON_COST_OFFSET = 2
SUMMON_SOURCE_COSTS = (5, 10, 12, 10, 8, 10, 10, 15)


def patch_summon_cost(
    probe: bytearray,
    source: bytes,
    summon_id: int,
    value: int,
) -> None:
    if not 0 <= summon_id < len(SUMMON_SOURCE_COSTS):
        raise ValueError("diagnostic summon ID must be 0..7")
    if not 0 <= value <= 99:
        raise ValueError("diagnostic summon cost must be 0..99")
    offset = (
        SUMMON_DATA_TABLE
        + summon_id * SUMMON_DATA_RECORD_SIZE
        + SUMMON_COST_OFFSET
    )
    expected = SUMMON_SOURCE_COSTS[summon_id].to_bytes(2, "big")
    for label, data in (("Japanese", source), ("input", probe)):
        actual = data[offset : offset + 2]
        if actual != expected:
            raise ValueError(
                f"{label} summon {summon_id} cost changed: "
                f"{actual.hex()} != {expected.hex()}"
            )
    probe[offset : offset + 2] = value.to_bytes(2, "big")


def patch_probe(
    probe: bytearray,
    source: bytes,
    diagnostic_summon_id: int | None = None,
    diagnostic_summon_cost: int | None = None,
) -> int:
    if (diagnostic_summon_id is None) != (diagnostic_summon_cost is None):
        raise ValueError("diagnostic summon ID and cost must be supplied together")
    patches = (
        (
            "summon command branch",
            SUMMON_COMMAND_BRANCH_OFFSET,
            SUMMON_COMMAND_BRANCH_SOURCE,
            SUMMON_COMMAND_BRANCH_PATCH,
        ),
        (
            "all-summon list branch",
            ALL_SUMMON_BRANCH_OFFSET,
            ALL_SUMMON_BRANCH_SOURCE,
            ALL_SUMMON_BRANCH_PATCH,
        ),
        (
            "summon MP branch",
            SUMMON_MP_BRANCH_OFFSET,
            SUMMON_MP_BRANCH_SOURCE,
            SUMMON_MP_BRANCH_PATCH,
        ),
    )
    for label, offset, expected, replacement in patches:
        if source[offset : offset + len(expected)] != expected:
            raise ValueError(f"Japanese {label} changed")
        if probe[offset : offset + len(expected)] != expected:
            raise ValueError(f"input {label} changed")
        probe[offset : offset + len(replacement)] = replacement
    if diagnostic_summon_id is not None and diagnostic_summon_cost is not None:
        patch_summon_cost(
            probe,
            source,
            diagnostic_summon_id,
            diagnostic_summon_cost,
        )
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored diagnostic ROM that offers Summon on Hein, "
            "exposes all eight summon IDs, and accepts a selected summon"
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    parser.add_argument("--diagnostic-summon-id", type=int)
    parser.add_argument("--diagnostic-summon-cost", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(
        probe,
        source,
        diagnostic_summon_id=args.diagnostic_summon_id,
        diagnostic_summon_cost=args.diagnostic_summon_cost,
    )
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print("summon command and all eight summon IDs enabled for diagnostics")
    if args.diagnostic_summon_id is not None:
        print(
            f"summon {args.diagnostic_summon_id} cost changed only for "
            f"diagnostics: {args.diagnostic_summon_cost}"
        )
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
