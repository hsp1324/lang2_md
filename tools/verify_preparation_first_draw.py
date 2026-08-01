#!/usr/bin/env python3
"""Verify the exact VRAM delta around a preparation dynamic-glyph draw."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import analyze_preparation_vram_ownership as ownership
from tools import run_preparation_surface_matrix as matrix


DEFAULT_CAPTURE_ROOT = ROOT / "captures/analysis/preparation_first_draw_current"
DEFAULT_NORMAL_ROM = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
DEFAULT_HARD_ROM = ROOT / "tmp/current-glyph-lifetime-fix-hard.md"
DEFAULT_OUTPUT = ROOT / "localization/preparation_first_draw_current_candidate.json"
PROFILES = ("normal", "hard")
GST_68K_PC_OFFSET = 0xC8
RENDERER_START = builder.BYTE_UI_PREP_DYNAMIC_GLYPH_RENDER_ROUTINE
RENDERER_END = RENDERER_START + len(
    builder._build_byte_ui_dynamic_glyph_renderer(
        builder.BYTE_UI_PREP_DYNAMIC_VDP_COMMAND_TABLE,
        builder.BYTE_UI_PREP_DYNAMIC_TILE_ID_TABLE,
    )
)
HSCROLL_START = 0xF400
HSCROLL_END = 0xF800
MERCENARY_ICON_CACHE_START = 0x0348 * ownership.TILE_BYTES
MERCENARY_ICON_CACHE_END = 0x0388 * ownership.TILE_BYTES


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def gst_pc(path: Path) -> int:
    data = path.read_bytes()
    require(data[:4] == b"GST@", f"{path} is not a BlastEm GST state")
    return int.from_bytes(data[GST_68K_PC_OFFSET:GST_68K_PC_OFFSET + 4], "little")


def changed_indexes(before: bytes, after: bytes) -> list[int]:
    require(len(before) == len(after), "VRAM sizes differ")
    return [index for index, pair in enumerate(zip(before, after)) if pair[0] != pair[1]]


def matching_chars(payload: bytes, font: ImageFont.FreeTypeFont) -> list[str]:
    return [
        char
        for char in builder.BYTE_UI_PREP_DYNAMIC_CHARS
        if builder.render_byte_ui_tile(char, font) == payload
    ]


def verify_profile(profile: str, rom_path: Path, capture_root: Path) -> dict[str, object]:
    directory = capture_root / profile
    before_path = directory / "before.gst"
    after_path = directory / "after.gst"
    require(before_path.is_file(), f"missing {before_path}")
    require(after_path.is_file(), f"missing {after_path}")

    before = ownership.load_gst(before_path)
    after = ownership.load_gst(after_path)
    require(before.registers == after.registers, f"{profile} VDP registers changed")
    require(before.hscroll_mode == 0, f"{profile} H-scroll mode changed")
    require(before.hscroll_base == HSCROLL_START, f"{profile} H-scroll base changed")

    before_hscroll = before.vram[HSCROLL_START:HSCROLL_END]
    after_hscroll = after.vram[HSCROLL_START:HSCROLL_END]
    require(not any(before_hscroll), f"{profile} before H-scroll is not clean")
    require(not any(after_hscroll), f"{profile} after H-scroll is not clean")
    require(before_hscroll == after_hscroll, f"{profile} H-scroll changed")
    require(
        before.vram[MERCENARY_ICON_CACHE_START:MERCENARY_ICON_CACHE_END]
        == after.vram[MERCENARY_ICON_CACHE_START:MERCENARY_ICON_CACHE_END],
        f"{profile} mercenary icon cache changed",
    )

    changed = changed_indexes(before.vram, after.vram)
    require(changed, f"{profile} did not change VRAM")
    changed_tiles = {index // ownership.TILE_BYTES for index in changed}
    require(
        len(changed_tiles) == 1,
        f"{profile} changed {len(changed_tiles)} VRAM tiles",
    )
    tile = next(iter(changed_tiles))
    start = tile * ownership.TILE_BYTES
    end = start + ownership.TILE_BYTES
    require(
        len(changed) <= ownership.TILE_BYTES,
        f"{profile} changed more than one tile payload",
    )
    require(tile in builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS, f"{profile} changed unowned tile 0x{tile:04X}")
    require(not HSCROLL_START <= start < HSCROLL_END, f"{profile} changed H-scroll tile")
    require(
        not MERCENARY_ICON_CACHE_START <= start < MERCENARY_ICON_CACHE_END,
        f"{profile} changed mercenary icon tile",
    )

    font = ImageFont.truetype(str(ROOT / "tools/fonts/Galmuri7.ttf"), 8)
    payload = after.vram[start:end]
    chars = matching_chars(payload, font)
    require(len(chars) == 1, f"{profile} after payload matched {chars!r}")
    char = chars[0]
    slot = builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS.index(tile)
    require(
        char in builder.BYTE_UI_PREP_DYNAMIC_SLOT_GROUPS[slot],
        f"{profile} {char!r} does not own tile slot {slot}",
    )
    require(before.vram[start:end] != payload, f"{profile} tile did not change")

    before_pc = gst_pc(before_path)
    after_pc = gst_pc(after_path)
    require(
        RENDERER_START <= before_pc < RENDERER_END,
        f"{profile} before PC 0x{before_pc:06X} is outside renderer",
    )
    require(
        not RENDERER_START <= after_pc < RENDERER_END,
        f"{profile} after PC 0x{after_pc:06X} remains inside renderer",
    )

    return {
        "status": "pass",
        "rom": {
            "path": relative(rom_path),
            "sha256": sha256(rom_path),
            "md_checksum": matrix.md_checksum(rom_path),
        },
        "before": {
            "path": relative(before_path),
            "sha256": sha256(before_path),
            "m68k_pc": f"0x{before_pc:06X}",
            "hscroll_nonzero_bytes": sum(bool(value) for value in before_hscroll),
        },
        "after": {
            "path": relative(after_path),
            "sha256": sha256(after_path),
            "m68k_pc": f"0x{after_pc:06X}",
            "hscroll_nonzero_bytes": sum(bool(value) for value in after_hscroll),
        },
        "vdp_registers_unchanged": True,
        "full_vram_changed_bytes": len(changed),
        "changed_range": f"0x{start:04X}..0x{end - 1:04X}",
        "changed_offsets_within_tile": [index - start for index in changed],
        "verified_tile_payload_bytes": ownership.TILE_BYTES,
        "changed_tile": f"0x{tile:04X}",
        "dynamic_slot": slot,
        "rendered_character": char,
        "after_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "hscroll_unchanged_and_zero": True,
        "mercenary_icon_cache_unchanged": True,
        "all_other_vram_bytes_unchanged": True,
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    roms = {"normal": args.normal_rom, "hard": args.hard_rom}
    profiles = {
        profile: verify_profile(profile, roms[profile], args.capture_root)
        for profile in PROFILES
    }
    return {
        "schema_version": 1,
        "status": "pass",
        "scope": "preparation_dynamic_glyph_first_draw_vram_delta",
        "debugger_breakpoints": {
            "renderer_entry": f"0x{RENDERER_START:06X}",
            "renderer_final_rts": f"0x{RENDERER_END - 2:06X}",
        },
        "gst_serialization_note": (
            "The save request was issued at the entry/final-RTS breakpoints. "
            "BlastEm serializes a queued GST at the next 68K synchronization boundary; "
            "the recorded before PC is therefore inside the renderer while its full VRAM "
            "still contains the complete pre-draw tile payload."
        ),
        "profiles": profiles,
        "summary": {
            "profiles_checked": len(profiles),
            "gst_states_checked": len(profiles) * 2,
            "changed_vram_bytes_by_profile": {
                profile: row["full_vram_changed_bytes"]
                for profile, row in profiles.items()
            },
            "maximum_changed_vram_bytes_per_profile": ownership.TILE_BYTES,
            "changed_tiles_per_profile": 1,
            "hscroll_nonzero_states": 0,
            "mercenary_icon_cache_changes": 0,
            "status": "pass",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--normal-rom", type=Path, default=DEFAULT_NORMAL_ROM)
    parser.add_argument("--hard-rom", type=Path, default=DEFAULT_HARD_ROM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="fail if the existing report is stale")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file(), f"missing report {args.output}")
        require(
            args.output.read_text(encoding="utf-8") == serialized,
            f"checked first-draw report is stale: {args.output}",
        )
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(
        "pass: 2 profiles, 4 GST states, one dynamic tile per profile, "
        "0 H-scroll or mercenary-cache changes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
