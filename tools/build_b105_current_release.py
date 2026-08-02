#!/usr/bin/env python3
"""Stamp the runtime-verified current hard candidate as T1.0.1/B1.0.5."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder


SOURCE_ROM = ROOT / "tmp/s13-custom-gray-fix-20260802-01/candidate-hard.md"
OUTPUT_ROM = (
    ROOT / "roms/releases/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.5).md"
)
DESKTOP_ROM = Path(
    "/mnt/c/Users/hsp13/Desktop/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.5).md"
)
SOURCE_SRAM = Path(
    "/mnt/c/Users/hsp13/Desktop/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.4).srm"
)
DESKTOP_SRAM = Path(
    "/mnt/c/Users/hsp13/Desktop/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.5).srm"
)
MANIFEST = ROOT / "localization/b105_current_release.json"
SOURCE_SHA256 = (
    "fff955d9c2549a8ac06ae2182e1aee93aed6296861aa309109d8074ae77417e2"
)
SOURCE_MD_CHECKSUM = "EC96"
SOURCE_HEADER = "LANGRISSER II KOREAN T1.0.0 B1.0.0 BY HSP1324"
TARGET_HEADER = "LANGRISSER II KOREAN T1.0.1 B1.0.5 BY HSP1324"
SOURCE_TRANSLATION_TITLE = "번역:1.0.0"
TARGET_TRANSLATION_TITLE = "번역:1.0.1"
SOURCE_BALANCE_TITLE = "하드:1.0.0"
TARGET_BALANCE_TITLE = "하드:1.0.5"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def md_checksum(data: bytes | bytearray) -> int:
    return sum(
        int.from_bytes(data[offset : offset + 2], "big")
        for offset in range(0x200, len(data), 2)
    ) & 0xFFFF


def _replace_title_record(
    data: bytearray,
    offset: int,
    source_text: str,
    target_text: str,
) -> None:
    source = builder.build_title_version_record(source_text)
    target = builder.build_title_version_record(target_text)
    if len(source) != len(target):
        raise ValueError("version title record size changed")
    if data[offset : offset + len(source)] != source:
        raise ValueError(f"source title record changed at 0x{offset:06X}")
    data[offset : offset + len(target)] = target


def stamp_release(source: bytes) -> bytes:
    if len(source) != 0x400000:
        raise ValueError("B1.0.5 source must be a 4 MiB ROM")
    if sha256_bytes(source) != SOURCE_SHA256:
        raise ValueError("B1.0.5 source candidate hash changed")
    if f"{md_checksum(source):04X}" != SOURCE_MD_CHECKSUM:
        raise ValueError("B1.0.5 source candidate checksum changed")

    data = bytearray(source)
    header_at = builder.MD_HEADER_INTERNATIONAL_TITLE
    header_end = header_at + builder.MD_HEADER_TITLE_SIZE
    if data[header_at:header_end].decode("ascii").rstrip() != SOURCE_HEADER:
        raise ValueError("B1.0.5 source header changed")

    target_header = TARGET_HEADER.encode("ascii")
    if len(target_header) > builder.MD_HEADER_TITLE_SIZE:
        raise ValueError("B1.0.5 target header is too long")
    data[header_at:header_end] = target_header.ljust(
        builder.MD_HEADER_TITLE_SIZE, b" "
    )
    _replace_title_record(
        data,
        builder.TITLE_HARD_TRANSLATION_TEXT_RECORD,
        SOURCE_TRANSLATION_TITLE,
        TARGET_TRANSLATION_TITLE,
    )
    _replace_title_record(
        data,
        builder.TITLE_HARD_BALANCE_TEXT_RECORD,
        SOURCE_BALANCE_TITLE,
        TARGET_BALANCE_TITLE,
    )
    builder.update_md_checksum(data)
    return bytes(data)


def build_manifest(source: bytes, release: bytes) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "built",
        "release": {
            "translation_version": "1.0.1",
            "build_version": "1.0.5",
            "filename": OUTPUT_ROM.name,
            "rom": str(OUTPUT_ROM.relative_to(ROOT)),
            "desktop_rom": str(DESKTOP_ROM),
            "rom_size": len(release),
            "md_checksum": f"{md_checksum(release):04X}",
            "sha256": sha256_bytes(release),
            "header_title": release[
                builder.MD_HEADER_INTERNATIONAL_TITLE :
                builder.MD_HEADER_INTERNATIONAL_TITLE
                + builder.MD_HEADER_TITLE_SIZE
            ].decode("ascii").rstrip(),
        },
        "source_candidate": {
            "rom": str(SOURCE_ROM.relative_to(ROOT)),
            "md_checksum": f"{md_checksum(source):04X}",
            "sha256": sha256_bytes(source),
            "runtime_evidence": (
                "localization/scenario13_royalhorse_gray_regression.json"
            ),
        },
        "included_fix": {
            "scenario_13_royal_horse_cache_isolated": True,
            "redesigned_custom_acted_gray_masks": True,
            "custom_sprite_count": 53,
            "ordinary_mercenary_cache_fix_retained": True,
        },
        "save_compatibility": {
            "save_format": "lang2-ko-sram-v1",
            "sram_compatible": True,
            "save_state_compatibility_guaranteed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROM)
    parser.add_argument("--desktop-output", type=Path, default=DESKTOP_ROM)
    parser.add_argument("--source-sram", type=Path, default=SOURCE_SRAM)
    parser.add_argument("--desktop-sram", type=Path, default=DESKTOP_SRAM)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--no-desktop-copy", action="store_true")
    parser.add_argument("--no-sram-copy", action="store_true")
    args = parser.parse_args()

    source = args.source.read_bytes()
    release = stamp_release(source)
    manifest = build_manifest(source, release)
    manifest["release"]["rom"] = str(args.output)
    manifest["release"]["desktop_rom"] = (
        None if args.no_desktop_copy else str(args.desktop_output)
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(release)
    if not args.no_desktop_copy:
        args.desktop_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.output, args.desktop_output)
    if not args.no_sram_copy:
        source_sram = args.source_sram.read_bytes()
        if len(source_sram) not in (0x2000, 0x10000):
            raise ValueError("B1.0.5 SRAM must be 8 KiB or 64 KiB")
        args.desktop_sram.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.source_sram, args.desktop_sram)
        copied_sram = args.desktop_sram.read_bytes()
        if copied_sram != source_sram:
            raise ValueError("B1.0.5 desktop SRAM copy differs from source")
        manifest["save_compatibility"].update({
            "source_sram": str(args.source_sram),
            "desktop_sram": str(args.desktop_sram),
            "sram_size": len(copied_sram),
            "sram_sha256": sha256_bytes(copied_sram),
            "sram_byte_identical_to_b104_source": True,
        })
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(args.output)
    if not args.no_desktop_copy:
        print(args.desktop_output)
    if not args.no_sram_copy:
        print(args.desktop_sram)
    print(args.manifest)
    print(f"sha256={sha256_bytes(release)}")
    print(f"md_checksum={md_checksum(release):04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
