#!/usr/bin/env python3
"""Classify the hard-ROM delta introduced by promoted AI class sprites."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import rom_update


DEFAULT_AFTER = (
    ROOT
    / "roms/releases/archive/"
    "Langrisser II (Korean Hard T1.0.0 B1.0.0 checksum-1011).md"
)
DEFAULT_OUTPUT = ROOT / "localization/ai_class_release_delta.json"
BEFORE_COMMIT = "1360b69"
EXPECTED_BEFORE_SHA256 = (
    "18f1203c32e66f660b84897cebe372c89e3c7d7787690abc5b62a84f470554ac"
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": str(path),
        "size": len(payload),
        "md_checksum": f"{rom_update.md_header_checksum(payload):04X}",
        "sha256": sha256(payload),
        "sram_descriptor": rom_update.md_sram_descriptor(payload).hex().upper(),
    }


def build_model(before_path: Path, after_path: Path) -> dict[str, Any]:
    before = before_path.read_bytes()
    after = after_path.read_bytes()
    if len(before) != len(after):
        raise ValueError("hard ROM sizes differ")
    before_identity = identity(before_path, before)
    after_identity = identity(after_path, after)
    if before_identity["sha256"] != EXPECTED_BEFORE_SHA256:
        raise ValueError(
            "unexpected predecessor SHA-256: "
            f"{before_identity['sha256']}"
        )
    if rom_update.md_checksum(before) != rom_update.md_header_checksum(before):
        raise ValueError("predecessor MD checksum is invalid")
    if rom_update.md_checksum(after) != rom_update.md_header_checksum(after):
        raise ValueError("current MD checksum is invalid")
    if (
        before_identity["sram_descriptor"]
        != after_identity["sram_descriptor"]
    ):
        raise ValueError("SRAM descriptor changed")

    header_offsets = {0x18E, 0x18F}
    mapping_offsets: set[int] = set()
    frame_offsets: set[int] = set()
    allowed = set(header_offsets)
    mappings = []
    frames = []
    for commander_id, class_id, sprite_id in (
        builder.AI_CLASS_MAP_SPRITE_SPECS
    ):
        record = builder.commander_sprite_record_offset(
            before, commander_id, class_id
        )
        mapping_offsets.update((record + 1, record + 2))
        allowed.update((record + 1, record + 2))
        before_sprite = builder.be16(before, record + 1)
        after_sprite = builder.be16(after, record + 1)
        if after_sprite != sprite_id:
            raise ValueError(
                f"unexpected promoted sprite at 0x{record:06X}: "
                f"0x{after_sprite:04X}"
            )
        mappings.append({
            "commander_id": commander_id,
            "class_id": f"0x{class_id:02X}",
            "record_offset": f"0x{record:06X}",
            "before_sprite_id": f"0x{before_sprite:04X}",
            "after_sprite_id": f"0x{after_sprite:04X}",
        })
        for frame_index, frame_base in enumerate(
            builder.MAP_SPRITE_FRAME_BASES
        ):
            offset = frame_base + sprite_id * builder.MAP_SPRITE_BYTES
            end = offset + builder.MAP_SPRITE_BYTES
            frame_offsets.update(range(offset, end))
            allowed.update(range(offset, end))
            before_payload = before[offset:end]
            after_payload = after[offset:end]
            if before_payload != bytes([0xFF]) * builder.MAP_SPRITE_BYTES:
                raise ValueError(
                    f"predecessor frame is not blank at 0x{offset:06X}"
                )
            frames.append({
                "commander_id": commander_id,
                "class_id": f"0x{class_id:02X}",
                "frame_index": frame_index,
                "offset": f"0x{offset:06X}",
                "size": builder.MAP_SPRITE_BYTES,
                "before_sha256": sha256(before_payload),
                "after_sha256": sha256(after_payload),
                "changed_bytes": sum(
                    left != right
                    for left, right in zip(before_payload, after_payload)
                ),
            })

    changed = {
        offset
        for offset, (left, right) in enumerate(zip(before, after))
        if left != right
    }
    unexpected = changed - allowed
    categories = {
        "header_checksum": len(changed & header_offsets),
        "commander_class_mapping": len(changed & mapping_offsets),
        "map_sprite_frames": len(changed & frame_offsets),
        "outside_owned_ranges": len(unexpected),
    }
    if unexpected:
        raise ValueError(
            f"{len(unexpected)} changed bytes are outside owned ranges"
        )
    if sum(categories.values()) != len(changed):
        raise AssertionError("delta category count does not cover every byte")

    return {
        "schema_version": 1,
        "status": "verified_cosmetic_only_delta",
        "reproduction": {
            "predecessor_commit": BEFORE_COMMIT,
            "command": "python3 tools/build_hard_mode_rom.py",
            "expected_predecessor_sha256": EXPECTED_BEFORE_SHA256,
        },
        "before": before_identity,
        "after": after_identity,
        "ownership": {
            "promoted_mapping_records": len(mappings),
            "promoted_animation_frames": len(frames),
            "sprite_id_range": [
                f"0x{builder.AI_CLASS_MAP_SPRITE_SPECS[0][2]:04X}",
                f"0x{builder.AI_CLASS_MAP_SPRITE_SPECS[-1][2]:04X}",
            ],
            "allowed_byte_count": len(allowed),
        },
        "delta": {
            "changed_byte_count": len(changed),
            "categories": categories,
            "unexpected_offsets": [
                f"0x{offset:06X}" for offset in sorted(unexpected)
            ],
            "balance_event_ai_changed_bytes": 0,
            "sram_descriptor_unchanged": True,
        },
        "mappings": mappings,
        "frames": frames,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the promoted class-sprite hard-ROM delta"
    )
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model = build_model(args.before, args.after)
    rendered = json.dumps(model, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale class-sprite delta: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(
        f"verified {model['delta']['changed_byte_count']} changed bytes; "
        f"unexpected={model['delta']['categories']['outside_owned_ranges']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
