#!/usr/bin/env python3
"""Build a non-release Scenario 12 probe for battle overlay VRAM audits."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_magic_application_probe_rom as magic_probe
from tools.scenario_data import DEFAULT_REFERENCE_ROM, FIELD_OFFSETS, read_scenario


DEFAULT_INPUT = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
DEFAULT_OUTPUT = ROOT / "tmp/current-battle-overlay-probe.md"
SCENARIO = 12
ENEMY_RECORD_INDEX = 0
SOURCE_COORDINATES = (15, 8)
PROBE_COORDINATES = (7, 25)


def patch_probe(data: bytearray, reference: bytes) -> int:
    model = read_scenario(data, reference, SCENARIO)
    record = model["records"][ENEMY_RECORD_INDEX]
    actual = (int(record["x"]), int(record["y"]))
    if actual != SOURCE_COORDINATES:
        raise ValueError(
            f"Scenario {SCENARIO} enemy coordinate changed: {actual!r}"
        )
    offset = int(record["offset"])
    data[offset + FIELD_OFFSETS["x"]] = PROBE_COORDINATES[0]
    data[offset + FIELD_OFFSETS["y"]] = PROBE_COORDINATES[1]

    for label, branch, expected, replacement in (
        (
            "all-magic list",
            magic_probe.ALL_MAGIC_BRANCH_OFFSET,
            magic_probe.ALL_MAGIC_BRANCH_SOURCE,
            magic_probe.ALL_MAGIC_BRANCH_PATCH,
        ),
        (
            "magic MP",
            magic_probe.MAGIC_MP_BRANCH_OFFSET,
            magic_probe.MAGIC_MP_BRANCH_SOURCE,
            magic_probe.MAGIC_MP_BRANCH_PATCH,
        ),
    ):
        if data[branch : branch + len(expected)] != expected:
            raise ValueError(f"input {label} branch changed")
        data[branch : branch + len(replacement)] = replacement
    return builder.update_md_checksum(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(data, DEFAULT_REFERENCE_ROM.read_bytes())
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(data)
    print(
        f"Scenario {SCENARIO} enemy {ENEMY_RECORD_INDEX}: "
        f"{SOURCE_COORDINATES} -> {PROBE_COORDINATES}"
    )
    print("all-magic and MP diagnostic branches enabled")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
