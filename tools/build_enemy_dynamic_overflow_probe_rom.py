#!/usr/bin/env python3
"""Build a diagnostic ROM with legacy Scenario 13 enemy mercenaries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools.v137_release_identity import RELEASE_ROM_PATHS, RELEASE_ROM_SHA256


SCENARIO_13_LEGACY_RECORDS = (0x181814, 0x1818C8)
MERCENARY_OFFSET = 0x1E
MERCENARY_COUNT = 6
VISIBLE_MERCENARY_OFFSET = 0x1818C2
VISIBLE_MERCENARY_EXPECTED_CLASS = 0x7D
DARK_GUARD_CLASS = 0x7C
CHECKSUM_OFFSETS = (0x18E, 0x18F)
SOURCE_LOCK_COMMIT = "b304f5d9"
SOURCE_LOCKED_ROWS = {
    0x181814: bytes.fromhex("7F 7F 7E 7E 7E 7E"),
    0x1818C8: bytes.fromhex("7C 7C 73 73 7A 7A"),
}
SOURCE_LOCKED_V137_INPUTS = {
    RELEASE_ROM_SHA256["pure"]: {
        "profile": "pure",
        "release_rom": RELEASE_ROM_PATHS["pure"].name,
    },
    RELEASE_ROM_SHA256["normal"]: {
        "profile": "normal",
        "release_rom": RELEASE_ROM_PATHS["normal"].name,
    },
    RELEASE_ROM_SHA256["hard"]: {
        "profile": "hard",
        "release_rom": RELEASE_ROM_PATHS["hard"].name,
    },
}
SOURCE_LOCKED_V137_OUTPUT_SHA256 = {
    "pure": "9600990a5be6f459ed2525417427c676de7a25d4e40bc3eed031f28a5cc55670",
    "normal": "0769ec812257dcca555a3799a28f60dce4d0c1b111360da052d7c5926048e11b",
    "hard": "9d46c40f5dd41a1c482db1782e3bcf192acb969e8f169df23e5b503479aa4cbb",
}
SOURCE_LOCKED_CHANGED_OFFSETS = (
    *CHECKSUM_OFFSETS,
    0x181814 + MERCENARY_OFFSET,
    0x181814 + MERCENARY_OFFSET + 1,
    VISIBLE_MERCENARY_OFFSET,
    0x1818C8 + MERCENARY_OFFSET,
    0x1818C8 + MERCENARY_OFFSET + 1,
)


def sha256_bytes(payload: bytes | bytearray) -> str:
    return hashlib.sha256(payload).hexdigest()


def md_checksum(payload: bytes | bytearray) -> int:
    return sum(
        builder.be16(payload, offset)
        for offset in range(0x200, len(payload), 2)
    ) & 0xFFFF


def exact_byte_changes(
    before: bytes,
    after: bytes | bytearray,
) -> list[dict[str, object]]:
    if len(before) != len(after):
        raise ValueError("before and after ROM sizes differ")
    return [
        {
            "offset": f"0x{offset:06X}",
            "before": f"{old:02X}",
            "after": f"{new:02X}",
            "kind": "checksum" if offset in CHECKSUM_OFFSETS else "diagnostic",
        }
        for offset, (old, new) in enumerate(zip(before, after))
        if old != new
    ]


def build_source_locked_v137_probe(
    base: bytes,
) -> tuple[bytearray, dict[str, object]]:
    """Build the 12-class S13 diagnostic from exact v1.3.7 bytes only."""
    input_hash = sha256_bytes(base)
    source = SOURCE_LOCKED_V137_INPUTS.get(input_hash)
    if source is None:
        raise ValueError(
            "source-locked mode requires an exact current v1.3.7 "
            f"Original/Normal/Hard ROM, got SHA-256 {input_hash}"
        )
    if len(base) != 0x400000:
        raise ValueError("source-locked v1.3.7 ROM must be exactly 4 MiB")
    if builder.be16(base, 0x18E) != md_checksum(base):
        raise ValueError("source-locked v1.3.7 input checksum is invalid")
    if base[VISIBLE_MERCENARY_OFFSET] != VISIBLE_MERCENARY_EXPECTED_CLASS:
        raise ValueError(
            "visible Scenario 13 diagnostic mercenary is not Dragonia"
        )

    probe = bytearray(base)
    row_manifest = []
    for record, literal in SOURCE_LOCKED_ROWS.items():
        start = record + MERCENARY_OFFSET
        end = start + MERCENARY_COUNT
        before = bytes(probe[start:end])
        probe[start:end] = literal
        row_manifest.append(
            {
                "record_offset": f"0x{record:06X}",
                "mercenary_offset": f"0x{start:06X}",
                "before": before.hex(" ").upper(),
                "after": literal.hex(" ").upper(),
            }
        )
    visible_before = probe[VISIBLE_MERCENARY_OFFSET]
    probe[VISIBLE_MERCENARY_OFFSET] = DARK_GUARD_CLASS
    checksum = builder.update_md_checksum(probe)

    changed = exact_byte_changes(base, probe)
    changed_offsets = tuple(int(row["offset"], 16) for row in changed)
    if changed_offsets != SOURCE_LOCKED_CHANGED_OFFSETS:
        raise ValueError(
            "source-locked diagnostic changed unexpected offsets: "
            f"{[row['offset'] for row in changed]}"
        )
    profile = str(source["profile"])
    output_hash = sha256_bytes(probe)
    expected_output_hash = SOURCE_LOCKED_V137_OUTPUT_SHA256[profile]
    if output_hash != expected_output_hash:
        raise ValueError(
            f"{profile} source-locked output hash drifted: "
            f"{output_hash} != {expected_output_hash}"
        )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "mode": "scenario13_dynamic_overflow_source_locked_v137",
        "status": "pass",
        "source_lock": {
            "commit": SOURCE_LOCK_COMMIT,
            "legacy_rom_required": False,
            "literal_rows": row_manifest,
            "visible_dark_guard": {
                "offset": f"0x{VISIBLE_MERCENARY_OFFSET:06X}",
                "before": f"{visible_before:02X}",
                "after": f"{DARK_GUARD_CLASS:02X}",
            },
        },
        "input": {
            **source,
            "sha256": input_hash,
            "md_checksum": f"{builder.be16(base, 0x18E):04X}",
            "bytes": len(base),
        },
        "output": {
            "sha256": output_hash,
            "expected_sha256": expected_output_hash,
            "md_checksum": f"{checksum:04X}",
            "bytes": len(probe),
        },
        "changed_offsets": [row["offset"] for row in changed],
        "changed_bytes": changed,
    }
    return probe, manifest


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
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--legacy", type=Path)
    mode.add_argument(
        "--source-locked-v137",
        action="store_true",
        help=(
            "build from the exact v1.3.7 Original/Normal/Hard input SHA "
            "using the b304f5d9 literal Scenario 13 rows"
        ),
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        help=(
            "source-locked evidence manifest path; defaults to the output "
            "ROM name with .manifest.json"
        ),
    )
    parser.add_argument(
        "--make-darkguard-visible",
        action="store_true",
        help=(
            "replace one immediately visible Dragonia subordinate with "
            "Dark Guard in the ignored diagnostic ROM"
        ),
    )
    args = parser.parse_args()
    if args.manifest is not None and not args.source_locked_v137:
        parser.error("--manifest is only valid with --source-locked-v137")

    base_bytes = args.base.read_bytes()
    manifest = None
    if args.source_locked_v137:
        base, manifest = build_source_locked_v137_probe(base_bytes)
        checksum = int(manifest["output"]["md_checksum"], 16)
    else:
        base = bytearray(base_bytes)
        legacy = args.legacy.read_bytes()
        checksum = patch_probe(
            base,
            legacy,
            make_darkguard_visible=args.make_darkguard_visible,
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(base)
    if manifest is not None:
        manifest["input"]["path"] = str(args.base.resolve())
        manifest["output"]["path"] = str(args.out.resolve())
        manifest_path = args.manifest or args.out.with_suffix(".manifest.json")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(manifest_path)
    print(args.out)
    print(f"checksum={checksum:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
