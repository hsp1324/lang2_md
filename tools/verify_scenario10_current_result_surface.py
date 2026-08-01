#!/usr/bin/env python3
"""Verify current normal/hard Scenario 10 reward and result evidence."""

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

from tools import build_scenario10_result_surface_probe_rom as probe_builder
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout
from tools.verify_preparation_surface_evidence import (
    RESULT_HEADER_VRAM_BYTES,
    RESULT_HEADER_VRAM_START,
    load_gst,
    result_header_plane_cells,
)


DEFAULT_OUTPUT = (
    ROOT / "localization/scenario10_current_result_surface_regression.json"
)
PROFILES = {
    "normal": {
        "candidate": ROOT / "tmp/current-glyph-lifetime-fix-normal.md",
        "probe": ROOT / "tmp/rebuilt-current-s10-result-normal.md",
        "result_root": ROOT / "captures/run/current_s10_result_retry/normal",
    },
    "hard": {
        "candidate": ROOT / "tmp/current-glyph-lifetime-fix-hard.md",
        "probe": ROOT / "tmp/rebuilt-current-s10-result-hard.md",
        "result_root": ROOT / "captures/run/current_s10_result_retry/hard",
        "reward": "battle/clear_path_43.png",
        "class_choice": "battle/clear_path_50.png",
    },
}


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def md_checksum(data: bytes) -> int:
    return sum(
        int.from_bytes(data[offset : offset + 2], "big")
        for offset in range(0x200, len(data), 2)
    ) & 0xFFFF


def image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as source:
        image = source.convert("RGB")
        dimensions = [image.width, image.height]
        result_frame_detected = (
            dimensions == [320, 240]
            and image.getpixel((160, 10)) == (206, 174, 119)
            and image.getpixel((160, 30)) == (0, 0, 119)
        )
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "dimensions": dimensions,
        "result_frame_detected": result_frame_detected,
    }


def supporting_image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as source:
        dimensions = [source.width, source.height]
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "dimensions": dimensions,
    }


def diagnostic_lineage(candidate_path: Path, probe_path: Path) -> dict[str, object]:
    candidate = candidate_path.read_bytes()
    probe = probe_path.read_bytes()
    wrapper = probe_builder.result_surface_wrapper_code()
    allowed = {
        0x18E,
        0x18F,
        *range(
            probe_builder.START_MENU_ENTRY_OPERAND,
            probe_builder.START_MENU_ENTRY_OPERAND + 4,
        ),
        *range(
            probe_builder.RUNTIME_WRAPPER,
            probe_builder.RUNTIME_WRAPPER + len(wrapper),
        ),
    }
    changed = {
        index
        for index, (before, after) in enumerate(zip(candidate, probe))
        if before != after
    }
    layout = scenario_layout(candidate, probe_builder.SCENARIO_NUMBER)
    scenario_records_identical = all(
        probe[
            layout.records_offset + index * FIXED_RECORD_SIZE :
            layout.records_offset + (index + 1) * FIXED_RECORD_SIZE
        ]
        == candidate[
            layout.records_offset + index * FIXED_RECORD_SIZE :
            layout.records_offset + (index + 1) * FIXED_RECORD_SIZE
        ]
        for index in range(layout.record_count)
    )
    checksum = md_checksum(probe)
    return {
        "candidate": {
            "path": relative(candidate_path),
            "sha256": sha256_path(candidate_path),
            "header_checksum": f"0x{int.from_bytes(candidate[0x18E:0x190], 'big'):04X}",
        },
        "probe": {
            "path": relative(probe_path),
            "sha256": sha256_path(probe_path),
            "header_checksum": f"0x{int.from_bytes(probe[0x18E:0x190], 'big'):04X}",
            "computed_checksum": f"0x{checksum:04X}",
        },
        "same_size": len(candidate) == len(probe),
        "actual_changed_byte_count": len(changed),
        "changes_limited_to_checksum_operand_and_wrapper": changed <= allowed,
        "scenario_fixed_records_identical": scenario_records_identical,
        "start_operand_points_to_wrapper": (
            int.from_bytes(
                probe[
                    probe_builder.START_MENU_ENTRY_OPERAND :
                    probe_builder.START_MENU_ENTRY_OPERAND + 4
                ],
                "big",
            )
            == probe_builder.RUNTIME_WRAPPER
        ),
        "wrapper_matches_builder": (
            probe[
                probe_builder.RUNTIME_WRAPPER :
                probe_builder.RUNTIME_WRAPPER + len(wrapper)
            ]
            == wrapper
        ),
        "checksum_valid": (
            int.from_bytes(probe[0x18E:0x190], "big") == checksum
        ),
    }


def runtime_report(root: Path) -> dict[str, object]:
    result_image = root / "battle/battle_result.png"
    result_gst = root / "states/battle_result.gst"
    state = load_gst(result_gst)
    header = state.vram[
        RESULT_HEADER_VRAM_START :
        RESULT_HEADER_VRAM_START + RESULT_HEADER_VRAM_BYTES
    ]
    cells = result_header_plane_cells(state)
    return {
        "battle_result": image_report(result_image),
        "gst": {
            "path": relative(result_gst),
            "sha256": sha256_path(result_gst),
            "bytes": result_gst.stat().st_size,
        },
        "header_text": "전과보고",
        "header_vram_range": "0xA000..0xA1FF",
        "header_vram_sha256": hashlib.sha256(header).hexdigest(),
        "header_plane_cells": cells,
        "all_header_plane_cells_match": all(row["matches"] for row in cells),
    }


def build_report() -> dict[str, object]:
    profiles: dict[str, object] = {}
    for profile, paths in PROFILES.items():
        lineage = diagnostic_lineage(paths["candidate"], paths["probe"])
        runtime = runtime_report(paths["result_root"])
        passed = (
            lineage["same_size"]
            and lineage["changes_limited_to_checksum_operand_and_wrapper"]
            and lineage["scenario_fixed_records_identical"]
            and lineage["start_operand_points_to_wrapper"]
            and lineage["wrapper_matches_builder"]
            and lineage["checksum_valid"]
            and runtime["battle_result"]["result_frame_detected"]
            and runtime["all_header_plane_cells_match"]
        )
        profiles[profile] = {
            "status": "pass" if passed else "fail",
            "diagnostic_lineage": lineage,
            "runtime": runtime,
        }

    hard_paths = PROFILES["hard"]
    supporting = {
        "necklace_acquisition": {
            **supporting_image_report(
                hard_paths["result_root"] / hard_paths["reward"]
            ),
            "manual_review": "pass",
            "observed_text": "넥클리스를 얻었다!",
        },
        "class_change_choice": {
            **supporting_image_report(
                hard_paths["result_root"] / hard_paths["class_choice"]
            ),
            "manual_review": "pass",
            "observed_text": [
                "클래스체인지",
                "쉐리",
                "로드",
                "호크나이트",
                "세인트",
                "용병",
                "파이크",
                "천사",
                "마법 힐",
                "프로텍션",
            ],
        },
    }
    normal_runtime = profiles["normal"]["runtime"]
    hard_runtime = profiles["hard"]["runtime"]
    cross_profile = {
        "battle_result_frame_identical": (
            normal_runtime["battle_result"]["sha256"]
            == hard_runtime["battle_result"]["sha256"]
        ),
        "result_header_vram_identical": (
            normal_runtime["header_vram_sha256"]
            == hard_runtime["header_vram_sha256"]
        ),
    }
    passed = (
        all(row["status"] == "pass" for row in profiles.values())
        and all(row["manual_review"] == "pass" for row in supporting.values())
        and all(cross_profile.values())
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": (
            "Current normal/hard Scenario 10 stock reward, class-choice, and "
            "battle-result surfaces reached through an input-preserving "
            "runtime-only diagnostic"
        ),
        "release_promoted": False,
        "profiles": profiles,
        "supporting_surfaces": supporting,
        "cross_profile": cross_profile,
        "limitations": [
            "The probe is diagnostic-only and is never a release candidate.",
            "Scenario 10 TURN 3 event timing is covered by separate current-candidate event evidence; this probe intentionally isolates only the completion surfaces.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the checked report differs from fresh evidence",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report()
    if args.check:
        checked = json.loads(args.output.read_text(encoding="utf-8"))
        if checked != report:
            raise SystemExit(
                f"checked Scenario 10 result report is stale: {args.output}"
            )
        print(f"checked Scenario 10 result report is current: {args.output}")
        return 0 if report["status"] == "pass" else 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
