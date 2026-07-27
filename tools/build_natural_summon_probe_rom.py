#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_class_change_probe_rom as class_probe
from tools import build_item_shop_probe_rom as shop_probe
from tools import build_summon_application_probe_rom as summon_probe


DEFAULT_INPUT_ROM = ROOT / builder.OUT_ROM
DEFAULT_SOURCE_ROM = ROOT / builder.IN_ROM
DEFAULT_OUTPUT_ROM = (
    ROOT / "roms/builds/Langrisser II (Hein Natural Brother Summon Probe).md"
)

HEIN_RUNTIME_RECORD = 1
SUMMONER_CLASS = 0x28
SUMMONER_PROBE_LEVEL = 1


def source_locked_summon_regions() -> tuple[tuple[int, int], ...]:
    regions = [
        (
            summon_probe.SUMMON_COMMAND_BRANCH_OFFSET,
            len(summon_probe.SUMMON_COMMAND_BRANCH_SOURCE),
        ),
        (
            summon_probe.ALL_SUMMON_BRANCH_OFFSET,
            len(summon_probe.ALL_SUMMON_BRANCH_SOURCE),
        ),
        (
            summon_probe.SUMMON_MP_BRANCH_OFFSET,
            len(summon_probe.SUMMON_MP_BRANCH_SOURCE),
        ),
    ]
    regions.extend(
        (
            summon_probe.SUMMON_DATA_TABLE
            + summon_id * summon_probe.SUMMON_DATA_RECORD_SIZE,
            summon_probe.SUMMON_DATA_RECORD_SIZE,
        )
        for summon_id in range(len(summon_probe.SUMMON_SOURCE_COSTS))
    )
    return tuple(regions)


def validate_stock_summon_path(
    probe: bytes | bytearray,
    source: bytes,
) -> None:
    for offset, size in source_locked_summon_regions():
        if probe[offset : offset + size] != source[offset : offset + size]:
            raise ValueError(
                f"input stock summon path changed at 0x{offset:06X}"
            )


def patch_probe(probe: bytearray, source: bytes) -> int:
    validate_stock_summon_path(probe, source)
    class_probe.patch_level_up_only_probe(
        probe,
        source,
        current_class=SUMMONER_CLASS,
        runtime_record_index=HEIN_RUNTIME_RECORD,
        probe_level=SUMMONER_PROBE_LEVEL,
    )
    shop_probe.patch_probe(probe, source, free_prices=False)
    validate_stock_summon_path(probe, source)
    return builder.update_md_checksum(probe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ignored diagnostic ROM that levels a real Hein Summoner "
            "from LV1 to LV2 and exposes the Japanese all-item shop list. "
            "Summon ownership, list construction, MP acceptance, and costs "
            "remain source-identical."
        )
    )
    parser.add_argument("--input-rom", type=Path, default=DEFAULT_INPUT_ROM)
    parser.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    parser.add_argument("--output-rom", type=Path, default=DEFAULT_OUTPUT_ROM)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_rom.read_bytes()
    probe = bytearray(args.input_rom.read_bytes())
    checksum = patch_probe(probe, source)
    args.output_rom.parent.mkdir(parents=True, exist_ok=True)
    args.output_rom.write_bytes(probe)
    print("Hein Summoner LV1 -> LV2 stock ability-learning trigger enabled")
    print("Japanese source shop list 33 enabled with original prices")
    print("summon ownership, list, MP branches, and costs remain source-identical")
    print(f"checksum: {checksum:04X}")
    print(args.output_rom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
