#!/usr/bin/env python3
"""Verify the post-release hard candidate changes only owned UI/sprite bytes."""

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


DEFAULT_BEFORE = (
    ROOT
    / "roms/releases/archive/"
    "Langrisser II (Korean Hard T1.0.0 B1.0.0 checksum-1011).md"
)
DEFAULT_AFTER = (
    ROOT
    / "roms/builds/Langrisser II (Korean Hard T1.0.0 B1.0.0).md"
)
DEFAULT_OUTPUT = ROOT / "localization/hard_mode_candidate_delta.json"
EXPECTED_BEFORE_SHA256 = (
    "c46249fdc50db4010115e5509c173de007761f5a42562345eca747506b43227b"
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "size": len(payload),
        "md_checksum": f"{rom_update.md_header_checksum(payload):04X}",
        "sha256": sha256(payload),
        "sram_descriptor": rom_update.md_sram_descriptor(payload).hex().upper(),
    }


def owned_ranges() -> dict[str, tuple[tuple[int, int], ...]]:
    loren_frames = tuple(
        (offset, offset + builder.MAP_SPRITE_BYTES)
        for offset in builder.LOREN_CUSTOM_FRAME_OFFSETS
    )
    return {
        "header_checksum": ((0x00018E, 0x000190),),
        "result_label_record": ((0x0A2E63, 0x0A2E68),),
        "inactive_sprite_hook": ((
            builder.MAP_SPRITE_GRAY_SOURCE_HOOK,
            builder.MAP_SPRITE_GRAY_SOURCE_HOOK
            + len(builder.MAP_SPRITE_GRAY_SOURCE_HOOK_ORIGINAL),
        ),),
        "result_ui_routines": ((
            builder.BYTE_UI_ENDING_RESULT_FINAL_BANK_ROUTINE,
            builder.TITLE_CREDIT_FONT_LOAD_ROUTINE,
        ),),
        "result_glyph_routine": ((
            builder.BYTE_UI_ENDING_RESULT_GLYPH_RENDER_ROUTINE,
            builder.BYTE_UI_ENDING_RESULT_GLYPH_RENDER_ROUTINE_LIMIT,
        ),),
        "inactive_sprite_routine": ((
            builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE,
            builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE_LIMIT,
        ),),
        "inactive_sprite_table": ((
            builder.MAP_SPRITE_GRAY_SOURCE_REMAP_TABLE,
            builder.MAP_SPRITE_GRAY_SOURCE_REMAP_TABLE_LIMIT,
        ),),
        "dynamic_legacy_lookup_routine": ((
            builder.BYTE_UI_DYNAMIC_LEGACY_LOOKUP_ROUTINE,
            builder.BYTE_UI_DYNAMIC_LEGACY_LOOKUP_ROUTINE
            + len(builder._build_byte_ui_dynamic_legacy_lookup()),
        ),),
        "dynamic_glyph_render_routine": ((
            builder.BYTE_UI_DYNAMIC_GLYPH_RENDER_ROUTINE,
            builder.BYTE_UI_DYNAMIC_GLYPH_RENDER_ROUTINE
            + len(builder._build_byte_ui_dynamic_glyph_renderer()),
        ),),
        "prep_dynamic_lookup_routine": ((
            builder.BYTE_UI_PREP_LOCAL_TILE_LOOKUP_ROUTINE,
            builder.BYTE_UI_PREP_LOCAL_TILE_LOOKUP_ROUTINE
            + len(builder._build_byte_ui_prep_local_tile_lookup()),
        ),),
        "dynamic_glyph_tables": ((
            builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE,
            builder.BYTE_UI_PREP_DYNAMIC_SLOT_TABLE_LIMIT,
        ),),
        "loren_map_frames": loren_frames,
    }


def offsets_for(ranges: tuple[tuple[int, int], ...]) -> set[int]:
    result: set[int] = set()
    for start, end in ranges:
        if end <= start:
            raise ValueError(f"invalid owned range: 0x{start:X}..0x{end:X}")
        result.update(range(start, end))
    return result


def build_model(before_path: Path, after_path: Path) -> dict[str, Any]:
    before = before_path.read_bytes()
    after = after_path.read_bytes()
    if len(before) != len(after):
        raise ValueError("hard ROM sizes differ")

    before_identity = identity(before_path, before)
    after_identity = identity(after_path, after)
    if before_identity["sha256"] != EXPECTED_BEFORE_SHA256:
        raise ValueError(
            "unexpected released predecessor SHA-256: "
            f"{before_identity['sha256']}"
        )
    for label, payload in (("predecessor", before), ("candidate", after)):
        if rom_update.md_checksum(payload) != rom_update.md_header_checksum(payload):
            raise ValueError(f"{label} MD checksum is invalid")
    if before_identity["sram_descriptor"] != after_identity["sram_descriptor"]:
        raise ValueError("SRAM descriptor changed")

    ownership = owned_ranges()
    category_offsets = {
        name: offsets_for(ranges)
        for name, ranges in ownership.items()
    }
    names = list(category_offsets)
    for index, name in enumerate(names):
        for other in names[index + 1:]:
            overlap = category_offsets[name] & category_offsets[other]
            if overlap:
                raise ValueError(
                    f"owned ranges overlap: {name} and {other} "
                    f"at 0x{min(overlap):06X}"
                )

    changed = {
        offset
        for offset, (left, right) in enumerate(zip(before, after))
        if left != right
    }
    allowed = set().union(*category_offsets.values())
    unexpected = changed - allowed
    if unexpected:
        raise ValueError(
            f"{len(unexpected)} changed bytes are outside owned ranges; "
            f"first=0x{min(unexpected):06X}"
        )

    categories = {
        name: len(changed & offsets)
        for name, offsets in category_offsets.items()
    }
    if sum(categories.values()) != len(changed):
        raise AssertionError("delta category count does not cover every byte")

    return {
        "schema_version": 1,
        "status": "verified_ui_sprite_only_delta",
        "before": before_identity,
        "after": after_identity,
        "ownership": {
            name: [
                {
                    "start": f"0x{start:06X}",
                    "end_exclusive": f"0x{end:06X}",
                }
                for start, end in ranges
            ]
            for name, ranges in ownership.items()
        },
        "delta": {
            "changed_byte_count": len(changed),
            "categories": categories,
            "outside_owned_ranges": len(unexpected),
            "unexpected_offsets": [
                f"0x{offset:06X}" for offset in sorted(unexpected)
            ],
            "balance_event_ai_changed_bytes": 0,
            "sram_descriptor_unchanged": True,
        },
        "evidence_inheritance": {
            "source_runtime_rom_sha256": (
                "18f1203c32e66f660b84897cebe372c89e3c7d7787690abc5b62a84f470554ac"
            ),
            "runtime_loader_scenarios": 31,
            "first_turn_scenarios": 31,
            "scope": (
                "Only loader/first-turn balance evidence is inherited. "
                "UI and sprite behavior must use current-candidate captures."
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    parser.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model = build_model(args.before.resolve(), args.after.resolve())
    rendered = json.dumps(model, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale hard candidate delta: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(
        f"verified {model['delta']['changed_byte_count']} changed bytes; "
        f"unexpected={model['delta']['outside_owned_ranges']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
