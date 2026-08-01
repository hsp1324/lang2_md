#!/usr/bin/env python3
"""Build B1.0.4 by rebasing the proven glyph-lifetime fix onto B1.0.3.

The B1.0.3 release remains the sole production base so character design,
hard-mode balance, scenarios, dialogue, and SRAM layout stay byte-identical.
Only the ownership-audited battle/preparation glyph patch, its ordinary enemy
mercenary cache helper, version records, and the Mega Drive checksum change.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


SOURCE_ROM = (
    ROOT / "roms/releases/Langrisser II (Korean Hard T1.0.1 B1.0.3).md"
)
PATCH_REFERENCE_ROM = ROOT / "tmp/current-glyph-lifetime-fix-hard.md"
OUTPUT_ROM = (
    ROOT / "roms/releases/Langrisser II (Korean Hard T1.0.1 B1.0.4).md"
)
SOURCE_SHA256 = "bc742e5c4c3964af9371feeb1203a9f2417fcea31d58a6dc0df0b1643101cb50"
PATCH_REFERENCE_SHA256 = (
    "f3d5e050eb84999571c9b575f9236ef01076bbba67542e8af183bf62223bf7ad"
)
SOURCE_HEADER = "LANGRISSER II KOREAN T1.0.1 B1.0.3 BY HSP1324"
TARGET_HEADER = "LANGRISSER II KOREAN T1.0.1 B1.0.4 BY HSP1324"
SOURCE_TRANSLATION_TITLE = "번역:1.0.1"
SOURCE_BALANCE_TITLE = "하드:1.0.3"
TARGET_BALANCE_TITLE = "하드:1.0.4"

# Half-open ranges containing the complete current glyph-lifetime correction.
# They were classified by comparing the exact B1.0.3 release with the exact
# normal/hard candidate that passed all 54 preparation runs, both animation
# frames, all ordinary acted-gray sprites, all 16 hire rows, and Pike/Monk
# focused runtime probes.
GLYPH_FIX_RANGES = (
    (0x0112DC, 0x0112E2),  # enemy ordinary-mercenary loader hook
    (0x01155C, 0x011562),  # enemy ordinary-mercenary lookup hook
    (0x2B7FCC, 0x2B7FCE),  # preparation renderer target
    (0x2B8E80, 0x2B8EDE),  # ordinary-mercenary cache helper routines
    (0x2BE800, 0x2BE880),  # battle VDP destination commands
    (0x2BE880, 0x2BE8C0),  # battle tile destinations
    (0x2BE9C0, 0x2BEAC0),  # preparation conflict-color slot map
    (0x2BEAC0, 0x2BEB40),  # preparation VDP destination commands
    (0x2BEB40, 0x2BEB80),  # preparation tile destinations
    (0x2BEBC0, 0x2BEC40),  # preparation-specific glyph renderer
    (0x2F1900, 0x2F1A00),  # first class-change dynamic-slot stream
    (0x2F7200, 0x2F7300),  # mirrored class-change dynamic-slot stream
)

# These are the only hard-balance bytes that differ between B1.0.3 and the
# diagnostic reference. They are explicitly excluded from B1.0.4.
PRESERVED_HARD_BALANCE_RANGES = (
    (0x181832, 0x181834),
    (0x1818E6, 0x1818E8),
    (0x181CEA, 0x181CEC),
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def offsets(ranges: tuple[tuple[int, int], ...]) -> set[int]:
    return {
        offset
        for start, end in ranges
        for offset in range(start, end)
    }


def md_checksum(data: bytes | bytearray) -> int:
    return sum(
        int.from_bytes(data[offset : offset + 2], "big")
        for offset in range(0x200, len(data), 2)
    ) & 0xFFFF


def validate_lineage(source: bytes, reference: bytes) -> None:
    if sha256(source) != SOURCE_SHA256:
        raise ValueError("B1.0.4 must use the exact B1.0.3 release ROM")
    if sha256(reference) != PATCH_REFERENCE_SHA256:
        raise ValueError("B1.0.4 glyph-fix reference changed")
    if len(source) != len(reference):
        raise ValueError("B1.0.3 and glyph-fix reference sizes differ")

    header = slice(
        builder.MD_HEADER_INTERNATIONAL_TITLE,
        builder.MD_HEADER_INTERNATIONAL_TITLE + builder.MD_HEADER_TITLE_SIZE,
    )
    if source[header].decode("ascii").rstrip() != SOURCE_HEADER:
        raise ValueError("B1.0.3 ROM header title changed")

    translation = builder.build_title_version_record(
        SOURCE_TRANSLATION_TITLE
    )
    translation_at = builder.TITLE_HARD_TRANSLATION_TEXT_RECORD
    if source[translation_at : translation_at + len(translation)] != translation:
        raise ValueError("B1.0.3 translation title record changed")
    balance = builder.build_title_version_record(SOURCE_BALANCE_TITLE)
    balance_at = builder.TITLE_HARD_BALANCE_TEXT_RECORD
    if source[balance_at : balance_at + len(balance)] != balance:
        raise ValueError("B1.0.3 hard-build title record changed")

    # Prove every source/reference difference was classified as glyph fix,
    # obsolete diagnostic version metadata, checksum, or excluded balance.
    changed = {
        index
        for index, (before, after) in enumerate(zip(source, reference))
        if before != after
    }
    reference_version_metadata = (
        set(range(header.start, header.stop))
        | set(range(0x18E, 0x190))
        | set(range(translation_at, translation_at + len(translation)))
        | set(range(balance_at, balance_at + len(balance)))
    )
    classified = (
        offsets(GLYPH_FIX_RANGES)
        | offsets(PRESERVED_HARD_BALANCE_RANGES)
        | reference_version_metadata
    )
    if not changed <= classified:
        unknown = sorted(changed - classified)
        raise ValueError(
            "unclassified B1.0.3/reference differences: "
            + ", ".join(f"0x{offset:06X}" for offset in unknown)
        )


def build(source: bytes, reference: bytes) -> bytes:
    validate_lineage(source, reference)
    data = bytearray(source)

    for start, end in GLYPH_FIX_RANGES:
        data[start:end] = reference[start:end]

    header = TARGET_HEADER.encode("ascii")
    header_at = builder.MD_HEADER_INTERNATIONAL_TITLE
    data[
        header_at : header_at + builder.MD_HEADER_TITLE_SIZE
    ] = header.ljust(builder.MD_HEADER_TITLE_SIZE, b" ")

    source_balance = builder.build_title_version_record(SOURCE_BALANCE_TITLE)
    target_balance = builder.build_title_version_record(TARGET_BALANCE_TITLE)
    if len(source_balance) != len(target_balance):
        raise ValueError("B1.0.4 title record unexpectedly changed size")
    balance_at = builder.TITLE_HARD_BALANCE_TEXT_RECORD
    data[balance_at : balance_at + len(target_balance)] = target_balance

    builder.update_md_checksum(data)
    return bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_ROM)
    parser.add_argument(
        "--patch-reference", type=Path, default=PATCH_REFERENCE_ROM
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_ROM)
    args = parser.parse_args()

    output = build(
        args.source.read_bytes(),
        args.patch_reference.read_bytes(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    print(args.output)
    print(f"sha256={sha256(output)}")
    print(f"md_checksum={md_checksum(output):04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
