#!/usr/bin/env python3
"""Verify both animation frames in every scenario's battle mercenary cache."""

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
from tools import hard_mode_plan
from tools import run_preparation_surface_matrix as preparation
from tools.run_preparation_surface_parallel import parse_scenarios
from tools.verify_preparation_surface_evidence import load_gst


GST_WORK_RAM_OFFSET = 0x2478
WORK_RAM_BYTES = 0x10000
FIXED_CACHE_TABLE = 0xA84E
FIXED_CACHE_COUNT = 16
DYNAMIC_CACHE_TABLE = 0xA88E
DYNAMIC_CACHE_COUNT = 10
CACHE_ROW_BYTES = 4
TILE_BYTES = 32
FRAME_TILE_COUNT = builder.MAP_SPRITE_BYTES // TILE_BYTES
SECOND_FRAME_TILE_DELTA = 0x100
GRAY_VRAM_START = 0x9600
DEFAULT_CAPTURE_ROOT = ROOT / "captures/run/gray_acted_surface_matrix"
DEFAULT_OUTPUT = ROOT / "localization/battle_mercenary_sprite_cache.json"
TRACKED_BASELINE = ROOT / "localization/hard_mode_baseline.json"
TRACKED_PLAN = ROOT / "localization/hard_mode_plan.json"


def parse_run_id_overrides(value: str) -> dict[int, str]:
    result = {}
    for part in value.split(","):
        scenario_text, separator, run_id = part.strip().partition("=")
        if not separator:
            raise argparse.ArgumentTypeError(
                "run-ID override must use SCENARIO=RUN_ID"
            )
        scenario = int(scenario_text)
        if not 1 <= scenario <= 31:
            raise argparse.ArgumentTypeError("override scenario must be 1..31")
        if scenario in result:
            raise argparse.ArgumentTypeError(
                f"duplicate run-ID override for Scenario {scenario}"
            )
        result[scenario] = preparation.validate_run_id(run_id)
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def work_ram(path: Path) -> bytes:
    payload = path.read_bytes()
    result = payload[
        GST_WORK_RAM_OFFSET:GST_WORK_RAM_OFFSET + WORK_RAM_BYTES
    ]
    if len(result) != WORK_RAM_BYTES:
        raise ValueError(f"GST is missing work RAM: {path}")
    return result


def cache_rows(
    ram: bytes,
    table: int,
    count: int,
    *,
    stop_at_blank: bool,
) -> list[dict[str, int]]:
    rows = []
    for index in range(count):
        offset = table + index * CACHE_ROW_BYTES
        class_id = int.from_bytes(ram[offset:offset + 2], "big")
        tile = int.from_bytes(ram[offset + 2:offset + 4], "big")
        if stop_at_blank and class_id == 0 and tile == 0:
            break
        rows.append({"index": index, "class_id": class_id, "tile": tile})
    return rows


def expected_dynamic_ids(
    baseline_scenario: dict[str, object],
    planned_scenario: dict[str, object] | None,
) -> list[int]:
    planned_records = (
        [] if planned_scenario is None else planned_scenario["records"]
    )
    return hard_mode_plan.dynamic_enemy_mercenary_class_ids(
        baseline_scenario,
        planned_records,
    )


def frame_source(rom: bytes, class_id: int, frame: int) -> tuple[int, bytes]:
    sprite_id = builder.be16(
        rom,
        builder.GENERIC_CLASS_SPRITE_TABLE + class_id * 2,
    )
    source = builder.MAP_SPRITE_FRAME_BASES[frame] + (
        sprite_id * builder.MAP_SPRITE_BYTES
    )
    payload = rom[source:source + builder.MAP_SPRITE_BYTES]
    if len(payload) != builder.MAP_SPRITE_BYTES:
        raise ValueError(
            f"class 0x{class_id:02X} frame {frame} source is truncated"
        )
    return sprite_id, payload


def verify_cache_row(
    state,
    rom: bytes,
    row: dict[str, int],
) -> dict[str, object]:
    class_id = row["class_id"]
    base_tile = row["tile"]
    frames = []
    passed = True
    sprite_ids = []
    for frame, tile in (
        (0, base_tile),
        (1, base_tile + SECOND_FRAME_TILE_DELTA),
    ):
        sprite_id, expected = frame_source(rom, class_id, frame)
        sprite_ids.append(sprite_id)
        start = tile * TILE_BYTES
        actual = state.vram[start:start + builder.MAP_SPRITE_BYTES]
        matches = actual == expected
        passed &= matches
        frames.append({
            "frame": frame,
            "tile_start": f"0x{tile:04X}",
            "vram_range": (
                f"0x{start:04X}.."
                f"0x{start + builder.MAP_SPRITE_BYTES - 1:04X}"
            ),
            "sha256": hashlib.sha256(actual).hexdigest(),
            "expected_sha256": hashlib.sha256(expected).hexdigest(),
            "matches_rom_source": matches,
        })
    if len(set(sprite_ids)) != 1:
        raise AssertionError("map sprite ID changed between animation frames")
    return {
        "index": row["index"],
        "class_id": f"0x{class_id:02X}",
        "class_korean": builder.KOREAN_CLASS_LABELS[class_id],
        "sprite_id": f"0x{sprite_ids[0]:04X}",
        "base_tile": f"0x{base_tile:04X}",
        "frames": frames,
        "status": "pass" if passed else "fail",
    }


def accepted_gray_attempt_is_valid(accepted: dict[str, object]) -> bool:
    """Accept both the legacy and current gray-evidence schemas."""
    legacy = accepted.get("matches_stock_fighter_silhouette_expansion")
    if legacy is not None:
        return bool(legacy)
    return bool(
        accepted.get("status") == "pass"
        and accepted.get("coordinate_changed")
        and accepted.get("matching_gray_ranges")
        and accepted.get("linked_gray_ranges")
    )


def profile_report(
    *,
    profile: str,
    rom_path: Path,
    run_id: str,
    run_id_overrides: dict[int, str],
    scenarios: list[int],
    capture_root: Path,
    baseline_by_number: dict[int, dict[str, object]],
    plan_by_number: dict[int, dict[str, object]],
) -> dict[str, object]:
    rom = rom_path.read_bytes()
    results = []
    for scenario in scenarios:
        scenario_run_id = run_id_overrides.get(scenario, run_id)
        evidence_path = (
            capture_root
            / profile
            / f"s{scenario:02d}"
            / scenario_run_id
            / "evidence.json"
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        accepted = evidence["accepted_attempt"]
        gst_path = ROOT / accepted["active_gst"]
        state = load_gst(gst_path)
        ram = work_ram(gst_path)
        fixed = cache_rows(
            ram,
            FIXED_CACHE_TABLE,
            FIXED_CACHE_COUNT,
            stop_at_blank=False,
        )
        dynamic = cache_rows(
            ram,
            DYNAMIC_CACHE_TABLE,
            DYNAMIC_CACHE_COUNT,
            stop_at_blank=True,
        )
        expected_fixed_ids = list(
            range(
                builder.ENEMY_ORDINARY_MERCENARY_FIRST_CLASS,
                builder.ENEMY_ORDINARY_MERCENARY_LAST_CLASS + 1,
            )
        )
        expected_dynamic = expected_dynamic_ids(
            baseline_by_number[scenario],
            plan_by_number.get(scenario) if profile == "hard" else None,
        )
        fixed_reports = [
            verify_cache_row(state, rom, row) for row in fixed
        ]
        dynamic_reports = [
            verify_cache_row(state, rom, row) for row in dynamic
        ]
        highest_dynamic_frame_end = max(
            (
                (row["tile"] + SECOND_FRAME_TILE_DELTA) * TILE_BYTES
                + builder.MAP_SPRITE_BYTES
                for row in dynamic
            ),
            default=0,
        )
        passed = (
            evidence["status"] == "pass"
            and accepted_gray_attempt_is_valid(accepted)
            and [row["class_id"] for row in fixed] == expected_fixed_ids
            and {row["class_id"] for row in dynamic}
            == set(expected_dynamic)
            and len(dynamic) == len(expected_dynamic)
            and len(dynamic) <= DYNAMIC_CACHE_COUNT
            and highest_dynamic_frame_end <= GRAY_VRAM_START
            and all(row["status"] == "pass" for row in fixed_reports)
            and all(row["status"] == "pass" for row in dynamic_reports)
        )
        results.append({
            "scenario": scenario,
            "run_id": scenario_run_id,
            "status": "pass" if passed else "fail",
            "evidence": relative(evidence_path),
            "evidence_sha256": sha256(evidence_path),
            "active_gst": relative(gst_path),
            "active_gst_sha256": sha256(gst_path),
            "fixed_cache": {
                "capacity": FIXED_CACHE_COUNT,
                "class_ids": [
                    f"0x{row['class_id']:02X}" for row in fixed
                ],
                "rows": fixed_reports,
            },
            "dynamic_cache": {
                "capacity": DYNAMIC_CACHE_COUNT,
                "class_ids": [
                    f"0x{row['class_id']:02X}" for row in dynamic
                ],
                "expected_class_ids": [
                    f"0x{class_id:02X}" for class_id in expected_dynamic
                ],
                "highest_second_frame_end": (
                    f"0x{highest_dynamic_frame_end:04X}"
                ),
                "gray_vram_start": f"0x{GRAY_VRAM_START:04X}",
                "rows": dynamic_reports,
            },
        })
    return {
        "profile": profile,
        "rom": {
            "path": relative(rom_path),
            "sha256": sha256(rom_path),
            "md_checksum": preparation.md_checksum(rom_path),
        },
        "run_id": run_id,
        "run_id_overrides": {
            str(scenario): override
            for scenario, override in sorted(run_id_overrides.items())
        },
        "passed_scenarios": sum(
            row["status"] == "pass" for row in results
        ),
        "total_scenarios": len(results),
        "scenarios": results,
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    # Runtime cache checks consume the reviewed tracked inventories. Rebuilding
    # them here made playback require an old private v1.0.0 comparison ROM.
    baseline = json.loads(TRACKED_BASELINE.read_text(encoding="utf-8"))
    plan = json.loads(TRACKED_PLAN.read_text(encoding="utf-8"))
    baseline_by_number = {
        int(row["number"]): row for row in baseline["scenarios"]
    }
    plan_by_number = {
        int(row["number"]): row for row in plan["scenarios"]
    }
    profiles = {
        "normal": profile_report(
            profile="normal",
            rom_path=args.normal_rom,
            run_id=args.normal_run_id,
            run_id_overrides=args.normal_run_id_overrides,
            scenarios=args.scenarios,
            capture_root=args.capture_root,
            baseline_by_number=baseline_by_number,
            plan_by_number=plan_by_number,
        ),
        "hard": profile_report(
            profile="hard",
            rom_path=args.hard_rom,
            run_id=args.hard_run_id,
            run_id_overrides=args.hard_run_id_overrides,
            scenarios=args.scenarios,
            capture_root=args.capture_root,
            baseline_by_number=baseline_by_number,
            plan_by_number=plan_by_number,
        ),
    }
    status = "pass" if all(
        row["passed_scenarios"] == row["total_scenarios"]
        for row in profiles.values()
    ) else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "scope": "all_cached_mercenary_animation_frames_and_gray_slot",
        "profiles": profiles,
        "invariants": {
            "ordinary_fixed_cache_entries": FIXED_CACHE_COUNT,
            "dynamic_cache_capacity": DYNAMIC_CACHE_COUNT,
            "dynamic_second_frames_end_before_gray_vram": True,
            "animation_frames_checked_per_cached_class": 2,
        },
        "limitations": [
            "This verifies cached map graphics and the first allied gray slot; battle combat animations are separate resources.",
            "Scenario-specific reinforcement event timing is not advanced, but hidden records loaded into the battle cache are included.",
            "No release ROM or version is changed by this verifier.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal-rom", type=Path, required=True)
    parser.add_argument("--hard-rom", type=Path, required=True)
    parser.add_argument("--normal-run-id", required=True)
    parser.add_argument("--hard-run-id", required=True)
    parser.add_argument(
        "--normal-run-id-overrides",
        type=parse_run_id_overrides,
        default={},
    )
    parser.add_argument(
        "--hard-run-id-overrides",
        type=parse_run_id_overrides,
        default={},
    )
    parser.add_argument(
        "--scenarios",
        type=parse_scenarios,
        default=parse_scenarios("1-27"),
    )
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.normal_rom = args.normal_rom.resolve()
    args.hard_rom = args.hard_rom.resolve()
    args.capture_root = args.capture_root.resolve()
    args.output = args.output.resolve()
    report = build_report(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
