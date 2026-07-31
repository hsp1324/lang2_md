#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_scenario1_clear_probe_rom as clear_probe
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
DEFAULT_BATTLE_RUNS = {
    profile: (
        ROOT
        / f"captures/run/preparation_battle_surface/{profile}/s01"
    )
    for profile in ("normal", "hard")
}
DEFAULT_REVIEW = ROOT / "localization/preparation_surface_review.json"
DEFAULT_INVENTORY = ROOT / "localization/byte_ui_slot_inventory.json"
DEFAULT_OUTPUT = ROOT / "localization/preparation_surface_matrix.json"
CHECKPOINT_CHAR = "얄"
CHECKPOINT_TILE = 0x03DF
CHECKPOINT_DYNAMIC_SLOT = 24
SHOP_CAPTURE_PATHS = (
    "shop/menu.png",
    "shop/item_list.png",
    "shop/returned_unfocused.png",
    "shop/returned_focused.png",
)
GST_WORK_RAM_OFFSET = 0x2478
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
GRAY_VRAM_START = 0x9600
GRAY_VRAM_BYTES = 0x80
GRAY_TILE_START = GRAY_VRAM_START // TILE_BYTES
GRAY_SOURCE_MASK_BASE = 0x0510C0
RESULT_HEADER_VRAM_START = 0xA000
RESULT_HEADER_VRAM_BYTES = 0x200
RESULT_HEADER_TILE_START = RESULT_HEADER_VRAM_START // TILE_BYTES
EXPECTED_RESULT_CAPTURE_SHA256 = (
    "55ccde344035d7bf5696a9f0b83c2ae6ac696ec1fa1f60cc2246d42d3565c825"
)
EXPECTED_RESULT_HEADER_VRAM_SHA256 = (
    "6b11a3261d70c91d8bb4e6bd8a637ac88172c16ad39948925a769ba127fe28b6"
)
EXPECTED_BATTLE_HASHES = {
    "normal": {
        "active_capture": (
            "9b01d3b03c48916661628f0af93867b83b5b0cc7c70402dbbf0c16a7f92a7aa9"
        ),
        "acted_capture": (
            "1054f6c2738bf2e6a6e6c60120d2f3dfdaf294f6636e717860a31aa1409749ce"
        ),
        "acted_gst": (
            "a5985c9872271ca1988a0633c1ef2e179984e37582f2f92952fe3619c3ae77be"
        ),
        "result_gst": (
            "481c01f74a25521b01f0d1aae8272429fcf9bb1fdcfd0b4ae4df2a06d25963db"
        ),
        "result_probe_checksum": "4B7D",
        "result_probe_sha256": (
            "66b9a4cb7944a506ff10b333a533d3be8d9d9c5fdc542c9bac4ec092de60b9e3"
        ),
    },
    "hard": {
        "active_capture": (
            "9b01d3b03c48916661628f0af93867b83b5b0cc7c70402dbbf0c16a7f92a7aa9"
        ),
        "acted_capture": (
            "bc6fc30ccb8a9cfa140a1f8184ed539398e519d0fd5cb1aa7d4f7c50d26a54ed"
        ),
        "acted_gst": (
            "9c32bdb5c589f1ded4e6af8678325c0543666835f52aa3267a7a19f50514e025"
        ),
        "result_gst": (
            "e13c1e8e70149c8adf690231b55f11ed894cd14069a1560a959bd62d99aae3eb"
        ),
        "result_probe_checksum": "92BA",
        "result_probe_sha256": (
            "4702bacfb7dc3ed80a6bbf8016dfde2edf46f1e210c6d6149f8cc9d3bfa49dd5"
        ),
    },
}


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


def image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        dimensions = [image.width, image.height]
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "dimensions": dimensions,
    }


def expand_gray_source_mask(payload: bytes) -> bytes:
    if len(payload) != 0x40:
        raise ValueError(
            f"gray source mask must contain 0x40 bytes, got 0x{len(payload):X}"
        )
    expanded = bytearray()
    for offset in range(0, len(payload), 2):
        high_plane, low_plane = payload[offset : offset + 2]
        pixels = [
            2 * ((high_plane >> bit) & 1) + ((low_plane >> bit) & 1)
            for bit in range(7, -1, -1)
        ]
        expanded.extend(
            (pixels[index] << 4) | pixels[index + 1]
            for index in range(0, len(pixels), 2)
        )
    return bytes(expanded)


def expected_gray_payload() -> tuple[int, int, bytes]:
    original = (ROOT / builder.IN_ROM).read_bytes()
    record_offset = builder.commander_sprite_record_offset(original, 1, 1)
    sprite_id = builder.be16(original, record_offset + 1)
    source_start = GRAY_SOURCE_MASK_BASE + sprite_id * 0x40
    return (
        record_offset,
        sprite_id,
        expand_gray_source_mask(original[source_start : source_start + 0x40]),
    )


def runtime_group_zero(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    start = GST_WORK_RAM_OFFSET + RUNTIME_GROUP_BASE
    record = data[start : start + RUNTIME_GROUP_SIZE]
    if len(record) != RUNTIME_GROUP_SIZE:
        raise ValueError(f"{path} has a truncated runtime group 0")
    return {
        "class_id": record[0],
        "commander_id": record[1],
        "acted_flag": record[2],
        "hp": record[3],
        "x": record[6],
        "y": record[7],
        "record_prefix": record[:16].hex(),
    }


def result_header_plane_cells(state: object) -> list[dict[str, object]]:
    base = state.plane_bases["plane_a"]
    cells = []
    for glyph_index in range(4):
        tile = RESULT_HEADER_TILE_START + glyph_index * 4
        x = 17 + glyph_index * 2
        for y_offset, tile_offsets in enumerate(((0, 1), (2, 3))):
            for x_offset, tile_offset in enumerate(tile_offsets):
                offset = (
                    base
                    + ((1 + y_offset) * state.plane_width + x + x_offset) * 2
                )
                word = int.from_bytes(
                    state.vram[offset : offset + 2], "big"
                )
                cells.append(
                    {
                        "x": x + x_offset,
                        "y": 1 + y_offset,
                        "tile_word": f"0x{word:04X}",
                        "expected_tile": f"0x{tile + tile_offset:04X}",
                        "matches": (word & 0x07FF) == tile + tile_offset,
                    }
                )
    return cells


def result_probe_report(
    candidate: bytes,
    expected: dict[str, str],
) -> dict[str, object]:
    diagnostic = bytearray(candidate)
    checksum = clear_probe.patch_probe(diagnostic, candidate)
    changed_offsets = [
        offset
        for offset, (before, after) in enumerate(zip(candidate, diagnostic))
        if before != after
    ]
    bald = clear_probe.BALD_RECORD_OFFSET
    allowed_offsets = {
        0x18E,
        0x18F,
        bald + clear_probe.FIELD_OFFSETS["at"],
        bald + clear_probe.FIELD_OFFSETS["df"],
        bald + clear_probe.FIELD_OFFSETS["x"],
        bald + clear_probe.FIELD_OFFSETS["y"],
        *(
            bald + clear_probe.FIELD_OFFSETS["mercenaries"] + index
            for index in range(6)
        ),
    }
    return {
        "md_checksum": f"{checksum:04X}",
        "sha256": hashlib.sha256(diagnostic).hexdigest(),
        "changed_offsets": [
            f"0x{offset:06X}" for offset in changed_offsets
        ],
        "changed_only_bald_setup_and_checksum": (
            bool(changed_offsets) and set(changed_offsets) <= allowed_offsets
        ),
        "battle_result_header_and_event_code_unchanged": not any(
            builder.BATTLE_RESULT_HEADER_GLYPH_LIST
            <= offset
            < (
                builder.BATTLE_RESULT_HEADER_GLYPH_LIST
                + len(builder.BATTLE_RESULT_HEADER_EXPECTED_GLYPHS) * 2
                + 2
            )
            for offset in changed_offsets
        ),
        "matches_expected_checksum": (
            f"{checksum:04X}" == expected["result_probe_checksum"]
        ),
        "matches_expected_sha256": (
            hashlib.sha256(diagnostic).hexdigest()
            == expected["result_probe_sha256"]
        ),
    }


def battle_evidence_report(
    profile: str,
    root: Path,
    candidate: bytes,
) -> dict[str, object]:
    expected = EXPECTED_BATTLE_HASHES[profile]
    active_capture = root / "gray01/active_command.png"
    acted_capture = root / "gray01/acted_gray.png"
    acted_gst = root / "gray01/states/acted_gray.gst"
    result_capture = root / "result01/battle_result.png"
    result_gst = root / "result01/states/battle_result.gst"

    acted_state = load_gst(acted_gst)
    result_state = load_gst(result_gst)
    source_record, source_sprite_id, expected_gray = expected_gray_payload()
    gray_payload = acted_state.vram[
        GRAY_VRAM_START : GRAY_VRAM_START + GRAY_VRAM_BYTES
    ]
    result_header_payload = result_state.vram[
        RESULT_HEADER_VRAM_START :
        RESULT_HEADER_VRAM_START + RESULT_HEADER_VRAM_BYTES
    ]
    return {
        "status": "pass",
        "run_root": relative(root),
        "gray_acted_sprite": {
            "active_capture": image_report(active_capture),
            "acted_capture": image_report(acted_capture),
            "gst": relative(acted_gst),
            "gst_sha256": sha256_path(acted_gst),
            "runtime_group_zero": runtime_group_zero(acted_gst),
            "source_commander_id": 1,
            "source_class_id": 1,
            "source_record_offset": f"0x{source_record:06X}",
            "source_silhouette_id": f"0x{source_sprite_id:04X}",
            "vram_range": "0x9600..0x967F",
            "vram_sha256": hashlib.sha256(gray_payload).hexdigest(),
            "matches_stock_fighter_silhouette_expansion": (
                gray_payload == expected_gray
            ),
            "plane_references": [
                {
                    "tile": f"0x{tile:04X}",
                    "hits": plane_tile_hits(acted_state, tile),
                }
                for tile in range(GRAY_TILE_START, GRAY_TILE_START + 4)
            ],
        },
        "battle_result": {
            "capture": image_report(result_capture),
            "gst": relative(result_gst),
            "gst_sha256": sha256_path(result_gst),
            "header_text": builder.DIRECT_WORD_SEQUENCE_PATCHES[
                builder.BATTLE_RESULT_HEADER_GLYPH_LIST
            ][1],
            "header_vram_range": "0xA000..0xA1FF",
            "header_vram_sha256": hashlib.sha256(
                result_header_payload
            ).hexdigest(),
            "header_plane_cells": result_header_plane_cells(result_state),
            "diagnostic_lineage": result_probe_report(candidate, expected),
        },
    }


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
    battle_run: Path,
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
            # This report hash-locks the accepted Scenario 1 yal01/yal02
            # candidate, where 얄 occupied slot 24. Later conflict coloring
            # may assign the character to another slot; it must not rewrite
            # historical runtime evidence.
            "dynamic_slot": CHECKPOINT_DYNAMIC_SLOT,
            "vram_tile": f"0x{CHECKPOINT_TILE:04X}",
            "pre_shop": checkpoint_report(
                run, "pre", rom, local_index
            ),
            "post_shop": checkpoint_report(
                run, "post", rom, local_index
            ),
        },
        "battle_evidence": battle_evidence_report(
            profile, battle_run, rom
        ),
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
        "review records complete Scenario 1 pass": (
            report["status"] == "scenario_1_surface_pass"
        ),
        "gray/result review passes": (
            report["human_review"]["checks"][
                "gray_acted_sprites_and_battle_result"
            ]
            == "pass"
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
    battle = report["battle_evidence"]
    gray = battle["gray_acted_sprite"]
    result = battle["battle_result"]
    expected_hashes = EXPECTED_BATTLE_HASHES[profile]
    checks.update(
        {
            "battle evidence passes": battle["status"] == "pass",
            "active capture hash is locked": (
                gray["active_capture"]["sha256"]
                == expected_hashes["active_capture"]
            ),
            "acted capture hash is locked": (
                gray["acted_capture"]["sha256"]
                == expected_hashes["acted_capture"]
            ),
            "acted GST hash is locked": (
                gray["gst_sha256"] == expected_hashes["acted_gst"]
            ),
            "battle captures are full screen": (
                gray["active_capture"]["dimensions"] == [320, 240]
                and gray["acted_capture"]["dimensions"] == [320, 240]
                and result["capture"]["dimensions"] == [320, 240]
            ),
            "runtime group records acted Elwin Fighter": (
                gray["runtime_group_zero"]["class_id"] == 1
                and gray["runtime_group_zero"]["commander_id"] == 1
                and gray["runtime_group_zero"]["acted_flag"] == 1
                and [
                    gray["runtime_group_zero"]["x"],
                    gray["runtime_group_zero"]["y"],
                ]
                == [12, 17]
            ),
            "gray source is stock Fighter silhouette": (
                gray["source_record_offset"] == "0x05DBA8"
                and gray["source_silhouette_id"] == "0x001E"
                and gray["matches_stock_fighter_silhouette_expansion"]
                and gray["vram_sha256"]
                == (
                    "74e404c1c9dad9a31578fcdf25c61158a"
                    "de1fdb43221941c7b2c3f6e19313b22"
                )
            ),
            "gray tiles are the visible Plane A unit": (
                gray["plane_references"]
                == [
                    {
                        "tile": "0x04B0",
                        "hits": [
                            {
                                "plane": "plane_a",
                                "x": 20,
                                "y": 11,
                                "tile_word": "0xA4B0",
                            }
                        ],
                    },
                    {
                        "tile": "0x04B1",
                        "hits": [
                            {
                                "plane": "plane_a",
                                "x": 20,
                                "y": 12,
                                "tile_word": "0xA4B1",
                            }
                        ],
                    },
                    {
                        "tile": "0x04B2",
                        "hits": [
                            {
                                "plane": "plane_a",
                                "x": 21,
                                "y": 11,
                                "tile_word": "0xA4B2",
                            }
                        ],
                    },
                    {
                        "tile": "0x04B3",
                        "hits": [
                            {
                                "plane": "plane_a",
                                "x": 21,
                                "y": 12,
                                "tile_word": "0xA4B3",
                            }
                        ],
                    },
                ]
            ),
            "result capture hash is locked": (
                result["capture"]["sha256"]
                == EXPECTED_RESULT_CAPTURE_SHA256
            ),
            "result GST hash is locked": (
                result["gst_sha256"] == expected_hashes["result_gst"]
            ),
            "result header is Korean and present in VRAM": (
                result["header_text"] == "전과보고"
                and result["header_vram_sha256"]
                == EXPECTED_RESULT_HEADER_VRAM_SHA256
                and all(
                    cell["matches"] for cell in result["header_plane_cells"]
                )
            ),
            "result diagnostic changes only setup": (
                result["diagnostic_lineage"][
                    "changed_only_bald_setup_and_checksum"
                ]
                and result["diagnostic_lineage"][
                    "battle_result_header_and_event_code_unchanged"
                ]
                and result["diagnostic_lineage"][
                    "matches_expected_checksum"
                ]
                and result["diagnostic_lineage"][
                    "matches_expected_sha256"
                ]
            ),
        }
    )
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{profile} preparation-surface evidence failed: "
            + ", ".join(failed)
        )


def build_report(
    runs: dict[str, Path] = DEFAULT_RUNS,
    battle_runs: dict[str, Path] = DEFAULT_BATTLE_RUNS,
    review_path: Path = DEFAULT_REVIEW,
    inventory_path: Path = DEFAULT_INVENTORY,
) -> dict[str, object]:
    review = read_json(review_path)
    local_index = checkpoint_local_index(inventory_path)
    profiles = {
        profile: run_report(
            profile,
            runs[profile],
            battle_runs[profile],
            review["profiles"][profile],
            local_index,
        )
        for profile in ("normal", "hard")
    }
    return {
        "schema_version": 2,
        "status": "scenario_1_complete_pass_scenarios_2_to_27_pending",
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
            "battle_surface_runs_reviewed": 2,
            "fully_accepted_profile_scenario_runs": 2,
            "fully_accepted_scenarios": 1,
            "remaining_requirement": (
                "Complete every required surface in Scenarios 2 through 27 "
                "for both profiles."
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
    if report["status"] != "scenario_1_complete_pass_scenarios_2_to_27_pending":
        raise ValueError("Scenario 1 matrix status must record its complete pass")
    progress = report["matrix_progress"]
    if progress["preparation_surface_runs_reviewed"] != 2:
        raise ValueError("expected exactly two reviewed Scenario 1 preparation runs")
    if progress["battle_surface_runs_reviewed"] != 2:
        raise ValueError("expected exactly two reviewed Scenario 1 battle runs")
    if progress["fully_accepted_scenarios"] != 1:
        raise ValueError("Scenario 1 must be the sole fully accepted scenario")
    normal_result = report["profiles"]["normal"]["battle_evidence"][
        "battle_result"
    ]["capture"]["sha256"]
    hard_result = report["profiles"]["hard"]["battle_evidence"][
        "battle_result"
    ]["capture"]["sha256"]
    if normal_result != hard_result:
        raise ValueError("normal/hard Scenario 1 result captures differ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the reviewed normal/hard Scenario 1 preparation and "
            "battle matrix, including the post-shop 얄 VRAM checkpoint, gray "
            "acted sprite, and battle-result header."
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
        DEFAULT_BATTLE_RUNS,
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
