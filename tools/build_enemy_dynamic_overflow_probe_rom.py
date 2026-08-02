#!/usr/bin/env python3
"""Build a diagnostic ROM with legacy Scenario 13 enemy mercenaries."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


SCENARIO_13_LEGACY_RECORDS = (0x181814, 0x1818C8)
MERCENARY_OFFSET = 0x1E
MERCENARY_COUNT = 6
VISIBLE_MERCENARY_OFFSET = 0x1818C2
VISIBLE_MERCENARY_EXPECTED_CLASS = 0x7D
DARK_GUARD_CLASS = 0x7C


def patch_probe(
    base: bytearray,
    legacy: bytes,
    *,
    make_darkguard_visible: bool = False,
) -> int:
    if len(base) != len(legacy):
        raise ValueError("base and legacy ROM sizes differ")
    for record in SCENARIO_13_LEGACY_RECORDS:
        start = record + MERCENARY_OFFSET
        end = start + MERCENARY_COUNT
        base[start:end] = legacy[start:end]
    if make_darkguard_visible:
        if base[VISIBLE_MERCENARY_OFFSET] != VISIBLE_MERCENARY_EXPECTED_CLASS:
            raise ValueError(
                "visible Scenario 13 diagnostic mercenary is not Dragonia"
            )
        base[VISIBLE_MERCENARY_OFFSET] = DARK_GUARD_CLASS
    return builder.update_md_checksum(base)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--legacy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--make-darkguard-visible",
        action="store_true",
        help=(
            "replace one immediately visible Dragonia subordinate with "
            "Dark Guard in the ignored diagnostic ROM"
        ),
    )
    args = parser.parse_args()

    base = bytearray(args.base.read_bytes())
    legacy = args.legacy.read_bytes()
    checksum = patch_probe(
        base,
        legacy,
        make_darkguard_visible=args.make_darkguard_visible,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(base)
    print(args.out)
    print(f"checksum={checksum:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
