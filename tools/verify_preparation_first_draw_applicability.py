#!/usr/bin/env python3
"""Prove that retained preparation first-draw evidence applies to new ROMs."""

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
from tools import run_preparation_surface_matrix as matrix


DEFAULT_SOURCE_REPORT = (
    ROOT / "localization/preparation_first_draw_current_candidate.json"
)
DEFAULT_SOURCE_NORMAL_ROM = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
DEFAULT_SOURCE_HARD_ROM = ROOT / "tmp/current-glyph-lifetime-fix-hard.md"
DEFAULT_OUTPUT = (
    ROOT / "localization/preparation_first_draw_current_applicability.json"
)
PROFILES = ("normal", "hard")

# A retained before/after GST pair is reusable only if every ROM byte that can
# affect one preparation-glyph draw is unchanged.  The battle-only VDP command
# and tile-ID tables are deliberately excluded: preparation has an independent
# slot table, VDP table, tile table, and renderer.
PREPARATION_OWNED_RANGES = (
    (
        "dynamic_glyph_payloads",
        builder.BYTE_UI_DYNAMIC_GLYPH_TABLE,
        builder.BYTE_UI_DYNAMIC_GLYPH_TABLE_LIMIT,
    ),
    (
        "preparation_slot_table",
        builder.BYTE_UI_PREP_DYNAMIC_SLOT_TABLE,
        builder.BYTE_UI_PREP_DYNAMIC_SLOT_TABLE_LIMIT,
    ),
    (
        "preparation_vdp_commands",
        builder.BYTE_UI_PREP_DYNAMIC_VDP_COMMAND_TABLE,
        builder.BYTE_UI_PREP_DYNAMIC_VDP_COMMAND_TABLE_LIMIT,
    ),
    (
        "preparation_tile_ids",
        builder.BYTE_UI_PREP_DYNAMIC_TILE_ID_TABLE,
        builder.BYTE_UI_PREP_DYNAMIC_TILE_ID_TABLE_LIMIT,
    ),
    (
        "preparation_renderer",
        builder.BYTE_UI_PREP_DYNAMIC_GLYPH_RENDER_ROUTINE,
        builder.BYTE_UI_PREP_DYNAMIC_GLYPH_RENDER_ROUTINE_LIMIT,
    ),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_source_evidence(
    source_report: dict[str, object],
    profile: str,
    source_rom: Path,
) -> dict[str, object]:
    row = source_report["profiles"][profile]
    require(row["status"] == "pass", f"{profile} source first-draw did not pass")
    recorded_rom = row["rom"]
    require(
        recorded_rom["sha256"] == sha256(source_rom),
        f"{profile} source ROM does not match the retained first-draw report",
    )
    for phase in ("before", "after"):
        recorded = row[phase]
        path = ROOT / recorded["path"]
        require(path.is_file(), f"missing retained {profile} {phase} GST: {path}")
        require(
            sha256(path) == recorded["sha256"],
            f"retained {profile} {phase} GST changed",
        )
    return row


def verify_profile(
    profile: str,
    source_report: dict[str, object],
    source_rom_path: Path,
    target_rom_path: Path,
) -> dict[str, object]:
    source_row = verify_source_evidence(source_report, profile, source_rom_path)
    source = source_rom_path.read_bytes()
    target = target_rom_path.read_bytes()
    require(len(source) == len(target), f"{profile} ROM sizes differ")

    ranges = []
    for name, start, end in PREPARATION_OWNED_RANGES:
        require(end <= len(source), f"{profile} {name} is outside the ROM")
        source_payload = source[start:end]
        target_payload = target[start:end]
        require(
            source_payload == target_payload,
            f"{profile} preparation-owned range changed: {name} "
            f"0x{start:06X}..0x{end - 1:06X}",
        )
        ranges.append(
            {
                "name": name,
                "start": f"0x{start:06X}",
                "end_exclusive": f"0x{end:06X}",
                "bytes": end - start,
                "sha256": hashlib.sha256(source_payload).hexdigest(),
                "byte_identical": True,
            }
        )

    return {
        "status": "pass",
        "source_rom": {
            "path": relative(source_rom_path),
            "sha256": sha256(source_rom_path),
            "md_checksum": matrix.md_checksum(source_rom_path),
        },
        "target_rom": {
            "path": relative(target_rom_path),
            "sha256": sha256(target_rom_path),
            "md_checksum": matrix.md_checksum(target_rom_path),
        },
        "retained_capture": {
            "before": source_row["before"],
            "after": source_row["after"],
            "rendered_character": source_row["rendered_character"],
            "changed_tile": source_row["changed_tile"],
            "full_vram_changed_bytes": source_row["full_vram_changed_bytes"],
            "hscroll_unchanged_and_zero": source_row[
                "hscroll_unchanged_and_zero"
            ],
            "mercenary_icon_cache_unchanged": source_row[
                "mercenary_icon_cache_unchanged"
            ],
            "all_other_vram_bytes_unchanged": source_row[
                "all_other_vram_bytes_unchanged"
            ],
        },
        "preparation_owned_ranges": ranges,
        "all_preparation_owned_ranges_byte_identical": True,
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    source_report = json.loads(args.source_report.read_text(encoding="utf-8"))
    require(source_report.get("status") == "pass", "source report did not pass")
    source_roms = {
        "normal": args.source_normal_rom,
        "hard": args.source_hard_rom,
    }
    target_roms = {
        "normal": args.target_normal_rom,
        "hard": args.target_hard_rom,
    }
    profiles = {
        profile: verify_profile(
            profile,
            source_report,
            source_roms[profile],
            target_roms[profile],
        )
        for profile in PROFILES
    }
    return {
        "schema_version": 1,
        "status": "pass",
        "scope": "preparation_first_draw_hash_exact_rom_applicability",
        "source_report": {
            "path": relative(args.source_report),
            "sha256": sha256(args.source_report),
        },
        "policy": (
            "Retained debugger GST evidence applies to a target ROM only when "
            "the recorded source ROM and GST hashes still match and every "
            "preparation-owned glyph payload, slot table, VDP command table, "
            "tile-ID table, and renderer byte is identical. Battle-only tables "
            "are outside this lifetime contract."
        ),
        "profiles": profiles,
        "summary": {
            "profiles_checked": len(profiles),
            "owned_ranges_per_profile": len(PREPARATION_OWNED_RANGES),
            "changed_preparation_owned_ranges": 0,
            "retained_gst_states": len(profiles) * 2,
            "hscroll_nonzero_states": 0,
            "mercenary_icon_cache_changes": 0,
            "status": "pass",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument(
        "--source-normal-rom", type=Path, default=DEFAULT_SOURCE_NORMAL_ROM
    )
    parser.add_argument(
        "--source-hard-rom", type=Path, default=DEFAULT_SOURCE_HARD_ROM
    )
    parser.add_argument("--target-normal-rom", type=Path, required=True)
    parser.add_argument("--target-hard-rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check", action="store_true", help="fail if the existing report is stale"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file(), f"missing report {args.output}")
        require(
            args.output.read_text(encoding="utf-8") == serialized,
            f"checked applicability report is stale: {args.output}",
        )
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(
        "pass: 2 profiles, 5 preparation-owned ranges per profile, "
        "0 changed ranges"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
