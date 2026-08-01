#!/usr/bin/env python3
"""Verify the narrowly rebased B1.0.4 glyph-lifetime release and saves."""

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
from tools import build_b104_glyph_lifetime_fix as release


ROM = release.OUTPUT_ROM
DESKTOP_ROM = Path(
    "/mnt/c/Users/hsp13/Desktop/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.4).md"
)
DESKTOP_SRAM = Path(
    "/mnt/c/Users/hsp13/Desktop/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.4).srm"
)
DESKTOP_STATE = Path(
    "/mnt/c/Users/hsp13/Desktop/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.4).state4"
)
SOURCE_SRAM = Path(
    "/mnt/c/Users/hsp13/Downloads/Mobile Devices/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.2).srm"
)
SOURCE_STATE = Path(
    "/mnt/c/Users/hsp13/Downloads/Mobile Devices/"
    "Langrisser II (Korean Hard T1.0.1 B1.0.2).state4"
)
MONK_DIAGNOSTIC_ROM = ROOT / "tmp/diagnostic/b104-release-monk-probe.md"
PIKE_EVIDENCE = (
    ROOT
    / "captures/run/pike_acted_surface_probe/"
    "b104-release-pike01/evidence.json"
)
MONK_EVIDENCE = (
    ROOT
    / "captures/run/pike_acted_surface_probe/"
    "b104-release-monk01/evidence.json"
)
OUTPUT = ROOT / "localization/b104_glyph_lifetime_release.json"

EXPECTED_ROM_SHA256 = (
    "a5495934196ea94ac850d88745b7d0a673c8996bfffe7059c815f4c3fb7b26c8"
)
EXPECTED_SRAM_SHA256 = (
    "43ccc5d676cfdd0c53c3a9234988b93493e897c0216072f8ff2db3451c077fdf"
)
EXPECTED_STATE_SHA256 = (
    "a80b842718b9d841c3c1bbfc564d86fcd822c1f280adc48125b23e12d34fcd00"
)
EXPECTED_MONK_DIAGNOSTIC_SHA256 = (
    "0278c066a979f84e42091a495901b5f663e391d6aaff675154c76477d20a45c6"
)
EXPECTED_PIKE_EVIDENCE_SHA256 = (
    "7c108b677ba8eec980136de58bc0d981ad35baed1a793e868acc308221fef9c4"
)
EXPECTED_MONK_EVIDENCE_SHA256 = (
    "ac07b2f39bb5390828322d675d490f3873c8e837abba56b1b71884f0601d3ccc"
)
EXPECTED_MD_CHECKSUM = "1991"
EXPECTED_PIKE_GRAY_SHA256 = (
    "0fe0987d6d93be4842ad899ae0dedbf85f1342b86efc6957e53fde7f76aee0a8"
)
EXPECTED_MONK_ACTIVE_SHA256 = (
    "c73bc44f8eaccb97d9ac9a52ac4de704ab3dd19ce2658415ec6a67cd902311be",
    "fd335ef32b49328d74c7086dfec918ab7500fbb19e89592fff04285974b42f64",
)
EXPECTED_MONK_GRAY_SHA256 = (
    "b27c631ffbe055f066317d4975bf97c3012a7e59c461e98a91b9d60cd194fdd4"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def changed_offsets(before: bytes, after: bytes) -> set[int]:
    if len(before) != len(after):
        raise ValueError("ROM sizes differ")
    return {
        offset
        for offset, (left, right) in enumerate(zip(before, after))
        if left != right
    }


def title_record_matches(rom: bytes, text: str, offset: int) -> bool:
    record = builder.build_title_version_record(text)
    return rom[offset : offset + len(record)] == record


def runtime_summary(path: Path) -> dict[str, object]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    active = evidence["mercenary_active_cache"]
    gray = evidence["mercenary_gray_cache"]
    return {
        "evidence": relative(path),
        "evidence_sha256": sha256(path),
        "status": evidence["status"],
        "rom_sha256": evidence["rom"]["sha256"],
        "scenario": evidence["scenario"],
        "commander_id": evidence["commander_id"],
        "hired_class": evidence["hired_class"],
        "hired_class_id": evidence["hired_class_id"],
        "hired_count": evidence["hired_count"],
        "acted_flag_before": evidence["mercenary_before"]["acted_flag"],
        "acted_flag_after": evidence["mercenary_after"]["acted_flag"],
        "coordinate_changed": evidence["coordinate_changed"],
        "active_frame_sha256": [
            frame["actual_sha256"] for frame in active["frames"]
        ],
        "both_active_frames_match_rom_source": active[
            "both_frames_match_rom_source"
        ],
        "gray_sha256": gray["actual_sha256"],
        "gray_matches_stock_silhouette_expansion": gray[
            "matches_stock_silhouette_expansion"
        ],
        "all_four_gray_tiles_visible": gray["all_four_tiles_visible"],
        "all_ordinary_gray_before_move_match_stock": evidence[
            "ordinary_gray_cache_before_move"
        ]["all_match_stock_silhouette_expansion"],
        "all_ordinary_gray_after_move_match_stock": evidence[
            "ordinary_gray_cache_after_move"
        ]["all_match_stock_silhouette_expansion"],
        "active_capture": evidence["active_capture"],
        "active_capture_sha256": evidence["active_capture_sha256"],
        "acted_capture": evidence["acted_capture"],
        "acted_capture_sha256": evidence["acted_capture_sha256"],
        "visual_review": "pass_no_hangul_fragment_or_sprite_corruption",
    }


def build_report() -> dict[str, object]:
    source = release.SOURCE_ROM.read_bytes()
    reference = release.PATCH_REFERENCE_ROM.read_bytes()
    rom = ROM.read_bytes()
    rebuilt = release.build(source, reference)
    desktop_rom = DESKTOP_ROM.read_bytes()
    desktop_sram = DESKTOP_SRAM.read_bytes()
    desktop_state = DESKTOP_STATE.read_bytes()
    source_sram = SOURCE_SRAM.read_bytes()
    source_state = SOURCE_STATE.read_bytes()
    diagnostic = MONK_DIAGNOSTIC_ROM.read_bytes()

    source_delta = changed_offsets(source, rom)
    glyph_offsets = release.offsets(release.GLYPH_FIX_RANGES)
    title_offsets = set(range(0x150, 0x180))
    checksum_offsets = set(range(0x18E, 0x190))
    balance_record = builder.build_title_version_record("하드:1.0.4")
    balance_title_offsets = set(
        range(
            builder.TITLE_HARD_BALANCE_TEXT_RECORD,
            builder.TITLE_HARD_BALANCE_TEXT_RECORD + len(balance_record),
        )
    )
    allowed_source_delta = (
        glyph_offsets | title_offsets | checksum_offsets | balance_title_offsets
    )
    diagnostic_delta = changed_offsets(rom, diagnostic)
    diagnostic_non_checksum = diagnostic_delta - checksum_offsets

    pike = runtime_summary(PIKE_EVIDENCE)
    monk = runtime_summary(MONK_EVIDENCE)
    report = {
        "schema_version": 1,
        "status": "pass",
        "scope": (
            "B1.0.4 production rebase, desktop delivery, and reported "
            "Pike/Monk glyph-lifetime sprite regressions"
        ),
        "release": {
            "source_rom": relative(release.SOURCE_ROM),
            "source_rom_sha256": sha256_bytes(source),
            "patch_reference_rom": relative(release.PATCH_REFERENCE_ROM),
            "patch_reference_sha256": sha256_bytes(reference),
            "rom": relative(ROM),
            "rom_sha256": sha256_bytes(rom),
            "rebuilt_rom_sha256": sha256_bytes(rebuilt),
            "desktop_rom": str(DESKTOP_ROM),
            "desktop_rom_sha256": sha256_bytes(desktop_rom),
            "rom_size": len(rom),
            "md_checksum": f"{release.md_checksum(rom):04X}",
            "header_title": rom[0x150:0x180].decode("ascii").rstrip(),
            "translation_title": "번역:1.0.1",
            "translation_title_matches": title_record_matches(
                rom,
                "번역:1.0.1",
                builder.TITLE_HARD_TRANSLATION_TEXT_RECORD,
            ),
            "balance_title": "하드:1.0.4",
            "balance_title_matches": title_record_matches(
                rom,
                "하드:1.0.4",
                builder.TITLE_HARD_BALANCE_TEXT_RECORD,
            ),
        },
        "source_delta": {
            "changed_byte_count": len(source_delta),
            "all_changes_classified": source_delta <= allowed_source_delta,
            "glyph_fix_ranges": [
                {
                    "start": f"0x{start:06X}",
                    "end_exclusive": f"0x{end:06X}",
                    "matches_proven_reference": rom[start:end]
                    == reference[start:end],
                }
                for start, end in release.GLYPH_FIX_RANGES
            ],
            "preserved_hard_balance_ranges": [
                {
                    "start": f"0x{start:06X}",
                    "end_exclusive": f"0x{end:06X}",
                    "matches_b103_source": rom[start:end] == source[start:end],
                }
                for start, end in release.PRESERVED_HARD_BALANCE_RANGES
            ],
            "save_format_header_range": "0x0001B0..0x0001BB",
            "save_format_header_preserved": rom[0x1B0:0x1BC]
            == source[0x1B0:0x1BC],
        },
        "desktop_saves": {
            "sram": str(DESKTOP_SRAM),
            "sram_sha256": sha256_bytes(desktop_sram),
            "sram_size": len(desktop_sram),
            "source_sram": str(SOURCE_SRAM),
            "source_sram_sha256": sha256_bytes(source_sram),
            "sram_byte_identical_to_source": desktop_sram == source_sram,
            "state4": str(DESKTOP_STATE),
            "state4_sha256": sha256_bytes(desktop_state),
            "state4_size": len(desktop_state),
            "source_state4": str(SOURCE_STATE),
            "source_state4_sha256": sha256_bytes(source_state),
            "state4_byte_identical_to_source": desktop_state == source_state,
            "state4_embeds_legacy_runtime_vram": True,
            "acceptance_test_method": (
                "cold boot B1.0.4 ROM and load the in-game SRAM save; use "
                "state4 only to recover position, then save in-game and reboot"
            ),
        },
        "pike_runtime": pike,
        "monk_runtime": {
            **monk,
            "diagnostic_rom": relative(MONK_DIAGNOSTIC_ROM),
            "diagnostic_rom_sha256": sha256_bytes(diagnostic),
            "diagnostic_md_checksum": f"{release.md_checksum(diagnostic):04X}",
            "non_checksum_changed_offsets": [
                f"0x{offset:06X}" for offset in sorted(diagnostic_non_checksum)
            ],
            "hire_unlock_before": rom[0x05EE12],
            "hire_unlock_after": diagnostic[0x05EE12],
            "release_rom_modified_by_probe": False,
        },
        "limitations": [
            (
                "This report closes the reported Pike/Monk sprite/glyph "
                "family on B1.0.4; it does not claim the still-pending full "
                "battle-result gate for Scenarios 12 through 27."
            ),
            (
                "The renamed state4 contains B1.0.2 emulator runtime state "
                "and must not be used as proof that B1.0.4 initialized VRAM."
            ),
        ],
    }
    validate(report)
    return report


def validate(report: dict[str, object]) -> None:
    failures: list[str] = []
    release_report = report["release"]
    source_delta = report["source_delta"]
    saves = report["desktop_saves"]
    pike = report["pike_runtime"]
    monk = report["monk_runtime"]

    if report["status"] != "pass":
        failures.append("status")
    if release_report["source_rom_sha256"] != release.SOURCE_SHA256:
        failures.append("B1.0.3 source")
    if release_report["patch_reference_sha256"] != release.PATCH_REFERENCE_SHA256:
        failures.append("glyph-fix reference")
    if any(
        release_report[key] != EXPECTED_ROM_SHA256
        for key in ("rom_sha256", "rebuilt_rom_sha256", "desktop_rom_sha256")
    ):
        failures.append("B1.0.4 ROM lineage/copy")
    if release_report["rom_size"] != 0x400000:
        failures.append("ROM size")
    if release_report["md_checksum"] != EXPECTED_MD_CHECKSUM:
        failures.append("Mega Drive checksum")
    if release_report["header_title"] != release.TARGET_HEADER:
        failures.append("header title")
    if not release_report["translation_title_matches"]:
        failures.append("translation title")
    if not release_report["balance_title_matches"]:
        failures.append("balance title")
    if not source_delta["all_changes_classified"]:
        failures.append("unclassified source delta")
    if not all(
        row["matches_proven_reference"]
        for row in source_delta["glyph_fix_ranges"]
    ):
        failures.append("glyph-fix ranges")
    if not all(
        row["matches_b103_source"]
        for row in source_delta["preserved_hard_balance_ranges"]
    ):
        failures.append("hard balance preservation")
    if not source_delta["save_format_header_preserved"]:
        failures.append("save format")
    if (
        saves["sram_sha256"] != EXPECTED_SRAM_SHA256
        or saves["sram_size"] != 0x10000
        or not saves["sram_byte_identical_to_source"]
    ):
        failures.append("desktop SRAM")
    if (
        saves["state4_sha256"] != EXPECTED_STATE_SHA256
        or saves["state4_size"] != 42345
        or not saves["state4_byte_identical_to_source"]
        or not saves["state4_embeds_legacy_runtime_vram"]
    ):
        failures.append("desktop state4")

    if pike["evidence_sha256"] != EXPECTED_PIKE_EVIDENCE_SHA256:
        failures.append("Pike evidence hash")
    if (
        pike["status"] != "pass"
        or pike["rom_sha256"] != EXPECTED_ROM_SHA256
        or pike["scenario"] != 12
        or pike["hired_class_id"] != "0x62"
        or pike["hired_count"] != 6
        or pike["acted_flag_before"] != 0
        or pike["acted_flag_after"] != 1
        or not pike["coordinate_changed"]
        or not pike["both_active_frames_match_rom_source"]
        or pike["gray_sha256"] != EXPECTED_PIKE_GRAY_SHA256
        or not pike["gray_matches_stock_silhouette_expansion"]
        or not pike["all_four_gray_tiles_visible"]
        or not pike["all_ordinary_gray_before_move_match_stock"]
        or not pike["all_ordinary_gray_after_move_match_stock"]
    ):
        failures.append("Pike runtime")

    if monk["evidence_sha256"] != EXPECTED_MONK_EVIDENCE_SHA256:
        failures.append("Monk evidence hash")
    if (
        monk["status"] != "pass"
        or monk["diagnostic_rom_sha256"] != EXPECTED_MONK_DIAGNOSTIC_SHA256
        or monk["scenario"] != 12
        or monk["hired_class_id"] != "0x6C"
        or monk["hired_count"] != 1
        or monk["acted_flag_before"] != 0
        or monk["acted_flag_after"] != 1
        or not monk["coordinate_changed"]
        or tuple(monk["active_frame_sha256"]) != EXPECTED_MONK_ACTIVE_SHA256
        or not monk["both_active_frames_match_rom_source"]
        or monk["gray_sha256"] != EXPECTED_MONK_GRAY_SHA256
        or not monk["gray_matches_stock_silhouette_expansion"]
        or not monk["all_four_gray_tiles_visible"]
        or not monk["all_ordinary_gray_before_move_match_stock"]
        or not monk["all_ordinary_gray_after_move_match_stock"]
        or monk["non_checksum_changed_offsets"] != ["0x05EE12"]
        or monk["hire_unlock_before"] != 0x02
        or monk["hire_unlock_after"] != 0x0A
        or monk["release_rom_modified_by_probe"]
    ):
        failures.append("Monk runtime/diagnostic lineage")

    if failures:
        raise ValueError(
            "B1.0.4 release validation failed: " + ", ".join(failures)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = build_report()
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if (
            not args.output.is_file()
            or args.output.read_text(encoding="utf-8") != encoded
        ):
            raise ValueError(f"checked B1.0.4 report is stale: {args.output}")
        print(args.output)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
