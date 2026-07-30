#!/usr/bin/env python3
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
from tools.analyze_preparation_vram_ownership import (
    HSCROLL_TABLE_BYTES,
    TILE_BYTES,
    load_gst,
)


DEFAULT_RUNS = {
    "normal": (
        ROOT
        / "captures/run/preparation_surface_matrix/normal/s01/yal02"
    ),
    "hard": (
        ROOT
        / "captures/run/preparation_surface_matrix/hard/s01/yal01"
    ),
}
DEFAULT_REVIEW = ROOT / "localization/preparation_surface_review.json"
DEFAULT_INVENTORY = ROOT / "localization/byte_ui_slot_inventory.json"
DEFAULT_OUTPUT = ROOT / "localization/preparation_surface_matrix.json"
CHECKPOINT_CHAR = "얄"
CHECKPOINT_TILE = 0x03DF
SHOP_CAPTURE_PATHS = (
    "shop/menu.png",
    "shop/item_list.png",
    "shop/returned_unfocused.png",
    "shop/returned_focused.png",
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def checkpoint_local_index(inventory_path: Path) -> int:
    inventory = read_json(inventory_path)
    matches = [
        row
        for row in inventory["local_indexes"]
        if row["char"] == CHECKPOINT_CHAR
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one local index for {CHECKPOINT_CHAR!r}, got {len(matches)}"
        )
    return int(matches[0]["local_index"], 16)


def plane_tile_hits(state: object, tile: int) -> list[dict[str, object]]:
    hits = []
    for plane, base in state.plane_bases.items():
        for y in range(state.plane_height):
            for x in range(state.plane_width):
                offset = base + (y * state.plane_width + x) * 2
                word = int.from_bytes(state.vram[offset : offset + 2], "big")
                if word & 0x07FF == tile:
                    hits.append(
                        {
                            "plane": plane,
                            "x": x,
                            "y": y,
                            "tile_word": f"0x{word:04X}",
                        }
                    )
    return hits


def checkpoint_report(
    run: Path,
    phase: str,
    rom: bytes,
    local_index: int,
) -> dict[str, object]:
    path = run / f"states/{phase}_fixed_record_09.gst"
    state = load_gst(path)
    tile_start = CHECKPOINT_TILE * TILE_BYTES
    payload = state.vram[tile_start : tile_start + TILE_BYTES]
    glyph_start = (
        builder.BYTE_UI_DYNAMIC_GLYPH_TABLE + local_index * TILE_BYTES
    )
    expected = rom[glyph_start : glyph_start + TILE_BYTES]
    hscroll = state.vram[
        state.hscroll_base : state.hscroll_base + HSCROLL_TABLE_BYTES
    ]
    return {
        "gst": relative(path),
        "gst_sha256": sha256_path(path),
        "vdp_register_11": f"0x{state.registers[11]:02X}",
        "vdp_register_13": f"0x{state.registers[13]:02X}",
        "hscroll_base": f"0x{state.hscroll_base:04X}",
        "hscroll_nonzero_bytes": sum(bool(value) for value in hscroll),
        "tile_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "matches_candidate_rom_glyph": payload == expected,
        "plane_references": plane_tile_hits(state, CHECKPOINT_TILE),
    }


def run_report(
    profile: str,
    run: Path,
    review: dict[str, object],
    local_index: int,
) -> dict[str, object]:
    plan_path = run / "plan.json"
    plan = read_json(plan_path)
    rom_path = ROOT / plan["rom"]["path"]
    rom = rom_path.read_bytes()

    pairs = matrix.capture_pairs(run)
    expected_pair_count = (
        sum(
            1 + int(commander["hire_page_count"])
            for commander in plan["allied_commanders"]["seed_records"]
        )
        + int(plan["allied_commanders"]["roster_page_count"])
        + len(plan["fixed_records"]["route"])
        + 3
    )
    checkpoint_records = [
        row
        for row in plan["fixed_records"]["route"]
        if CHECKPOINT_CHAR in row["runtime_checkpoint_chars"]
    ]
    shop_captures = [
        {
            "path": relative(run / capture),
            "sha256": sha256_path(run / capture),
        }
        for capture in SHOP_CAPTURE_PATHS
    ]
    result = {
        "run": relative(run),
        "status": review["status"],
        "plan": {
            "path": relative(plan_path),
            "sha256": sha256_path(plan_path),
        },
        "capture_status": "recomputed_exact_reviewed",
        "candidate": {
            "path": relative(rom_path),
            "md_checksum": matrix.md_checksum(rom_path),
            "sha256": sha256_path(rom_path),
        },
        "scenario": plan["scenario"],
        "allied_commander_count": plan["allied_commanders"]["count"],
        "visible_fixed_record_indexes": [
            row["index"] for row in plan["fixed_records"]["route"]
        ],
        "checkpoint_record_indexes": [
            row["index"] for row in checkpoint_records
        ],
        "expected_pair_count": expected_pair_count,
        "actual_pair_count": len(pairs),
        "capture_pairs": pairs,
        "shop_captures": shop_captures,
        "runtime_checkpoint": {
            "char": CHECKPOINT_CHAR,
            "local_index": f"0x{local_index:02X}",
            "dynamic_slot": builder.BYTE_UI_PREP_DYNAMIC_CHARS.index(
                CHECKPOINT_CHAR
            ),
            "vram_tile": f"0x{CHECKPOINT_TILE:04X}",
            "pre_shop": checkpoint_report(
                run, "pre", rom, local_index
            ),
            "post_shop": checkpoint_report(
                run, "post", rom, local_index
            ),
        },
        "human_review": review,
    }
    validate_run_report(profile, result, plan)
    return result


def validate_run_report(
    profile: str,
    report: dict[str, object],
    plan: dict[str, object],
) -> None:
    checkpoint = report["runtime_checkpoint"]
    checks = {
        "scenario is 1": report["scenario"] == 1,
        "capture profile matches run path": (
            f"/{profile}/s01/" in f"/{report['run']}/"
        ),
        "capture status is recomputed": (
            report["capture_status"] == "recomputed_exact_reviewed"
        ),
        "pair count is complete": (
            report["actual_pair_count"] == report["expected_pair_count"] == 14
        ),
        "all full-screen pairs are exact": all(
            row["byte_identical"] for row in report["capture_pairs"]
        ),
        "all six fixed records are routed": (
            report["visible_fixed_record_indexes"] == [0, 1, 8, 9, 10, 11]
        ),
        "royal-horse record is checkpointed": (
            report["checkpoint_record_indexes"] == [9]
        ),
        "candidate checksum matches plan": (
            report["candidate"]["md_checksum"] == plan["rom"]["md_checksum"]
        ),
        "candidate hash matches plan": (
            report["candidate"]["sha256"] == plan["rom"]["sha256"]
        ),
        "review records preparation-only pass": (
            report["status"] == "preparation_surface_pass_battle_pending"
        ),
        "gray/result review remains pending": (
            report["human_review"]["checks"][
                "gray_acted_sprites_and_battle_result"
            ]
            == "pending_separate_battle_run"
        ),
    }
    for phase in ("pre_shop", "post_shop"):
        phase_report = checkpoint[phase]
        checks[f"{phase} uses the audited glyph"] = phase_report[
            "matches_candidate_rom_glyph"
        ]
        checks[f"{phase} H-scroll is clean"] = (
            phase_report["hscroll_base"] == "0xF400"
            and phase_report["hscroll_nonzero_bytes"] == 0
        )
        checks[f"{phase} references tile in Plane A"] = (
            phase_report["plane_references"]
            == [
                {
                    "plane": "plane_a",
                    "x": 7,
                    "y": 8,
                    "tile_word": "0x83DF",
                }
            ]
        )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} preparation-surface evidence failed: "
            + ", ".join(failed)
        )


def build_report(
    runs: dict[str, Path] = DEFAULT_RUNS,
    review_path: Path = DEFAULT_REVIEW,
    inventory_path: Path = DEFAULT_INVENTORY,
) -> dict[str, object]:
    review = read_json(review_path)
    local_index = checkpoint_local_index(inventory_path)
    profiles = {
        profile: run_report(
            profile,
            runs[profile],
            review["profiles"][profile],
            local_index,
        )
        for profile in ("normal", "hard")
    }
    return {
        "schema_version": 1,
        "status": "scenario_1_preparation_partial_pass_battle_pending",
        "review": {
            "path": relative(review_path),
            "sha256": sha256_path(review_path),
            "reviewed_on": review["reviewed_on"],
            "scope": review["scope"],
            "class_change": review["class_change"],
            "acceptance_effect": review["acceptance_effect"],
        },
        "profiles": profiles,
        "matrix_progress": {
            "required_profile_scenario_runs": 54,
            "preparation_surface_runs_reviewed": 2,
            "fully_accepted_scenarios": 0,
            "remaining_requirement": (
                "Scenario 1 gray acted sprites and battle result in both "
                "profiles, then complete Scenarios 2 through 27."
            ),
        },
        "rejected_normal_scenario_1_attempts": [
            {
                "run_id": "canonical01",
                "result": "13/14 pairs; equipment/focus state was captured as commander detail",
            },
            {
                "run_id": "canonical02",
                "result": "first fixed-record detail detector failure",
            },
            {
                "run_id": "canonical03",
                "result": "hire END/focus error; an unintended Soldier hire changed money",
            },
            {
                "run_id": "canonical04",
                "result": "preparation focus state was not restored",
            },
            {
                "run_id": "canonical05",
                "result": "commander scan passed but arrangement focus was wrong",
            },
            {
                "run_id": "canonical06",
                "result": "arrangement focus/navigation failure",
            },
            {
                "run_id": "canonical07",
                "result": "arrangement action-list focus detector failure",
            },
            {
                "run_id": "canonical08",
                "result": "arrangement focus failure; retained GST proved B transfers focus",
            },
            {
                "run_id": "canonical09",
                "result": "14 pairs but only four distinct fixed details; popup-close input was ignored",
            },
            {
                "run_id": "canonical10",
                "result": "13/14 exact; post-shop 로얄호스 exposed static 얄 tile corruption",
            },
        ],
        "rejected_checkpoint_attempt": {
            "result": (
                "Loading pre_shop.gst into the later runtime unexpectedly "
                "deployed instead of reopening Leon; no pre-checkpoint state "
                "from that attempt is accepted."
            ),
            "replacement": (
                "The clean yal02 and hard yal01 runs save both pre/post "
                "checkpoints automatically without loading a state."
            ),
        },
    }


def validate_report(report: dict[str, object]) -> None:
    if report["status"] != "scenario_1_preparation_partial_pass_battle_pending":
        raise ValueError("matrix status must remain partial until battle evidence passes")
    progress = report["matrix_progress"]
    if progress["preparation_surface_runs_reviewed"] != 2:
        raise ValueError("expected exactly two reviewed Scenario 1 preparation runs")
    if progress["fully_accepted_scenarios"] != 0:
        raise ValueError("Scenario 1 must not be fully accepted yet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the reviewed normal/hard Scenario 1 preparation matrix, "
            "including the post-shop 얄 VRAM checkpoint."
        )
    )
    parser.add_argument("--normal-run", type=Path, default=DEFAULT_RUNS["normal"])
    parser.add_argument("--hard-run", type=Path, default=DEFAULT_RUNS["hard"])
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        {"normal": args.normal_run, "hard": args.hard_run},
        args.review,
        args.inventory,
    )
    validate_report(report)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file():
            raise FileNotFoundError(f"checked report does not exist: {args.output}")
        if args.output.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"checked report is stale: {args.output}")
        print(f"verified {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
