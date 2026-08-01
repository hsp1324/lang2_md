#!/usr/bin/env python3
"""Verify current normal/hard Scenario 16 completion surfaces."""

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
from tools import build_scenario16_clear_probe_rom as probe_builder
from tools.verify_preparation_surface_evidence import (
    RESULT_HEADER_VRAM_BYTES,
    RESULT_HEADER_VRAM_START,
    load_gst,
    result_header_plane_cells,
)


DEFAULT_OUTPUT = (
    ROOT / "localization/scenario16_current_result_surface_regression.json"
)
NORMAL_CANDIDATE = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
NORMAL_PROBE = ROOT / "tmp/current-result-probes/normal/s16.md"
HARD_CANDIDATE = ROOT / "tmp/current-glyph-lifetime-fix-hard.md"
HARD_PROBE = ROOT / "tmp/current-result-probes/hard/s16.md"
SOURCE_ROM = probe_builder.DEFAULT_SOURCE_ROM
RUNTIME_ROOT = ROOT / "captures/run/current_s16_result"
PROFILES = {
    "normal": {
        "candidate": NORMAL_CANDIDATE,
        "probe": NORMAL_PROBE,
        "runtime": RUNTIME_ROOT / "normal",
    },
    "hard": {
        "candidate": HARD_CANDIDATE,
        "probe": HARD_PROBE,
        "runtime": RUNTIME_ROOT / "hard",
    },
}
RESULT_POINTS = {
    (160, 10): (206, 174, 119),
    (160, 30): (0, 0, 119),
    (20, 30): (0, 0, 0),
    (300, 30): (0, 0, 119),
    (160, 200): (0, 0, 119),
    (20, 220): (255, 146, 0),
}
CRITICAL_SURFACES = {
    "scott_status_bar": {
        "frame": 8,
        "observed_text": ["스코트"],
    },
    "jessica_status_bar": {
        "frame": 10,
        "observed_text": ["제시카"],
    },
    "sherry_level_up": {
        "frame": 18,
        "observed_text": ["쉐리", "레벨이 올랐다."],
    },
    "class_change_choice": {
        "frame": 20,
        "observed_text": [
            "클래스체인지",
            "쉐리",
            "로드",
            "호크나이트",
            "세인트",
            "파이크",
            "천사",
            "힐",
            "프로텍션",
        ],
    },
    "aaron_level_up": {
        "frame": 21,
        "observed_text": ["아론", "레벨이 올랐다."],
    },
    "lester_level_up": {
        "frame": 22,
        "observed_text": ["레스터", "레벨"],
    },
    "scott_level_up": {
        "frame": 24,
        "observed_text": ["스코트", "레벨이 올랐다."],
    },
    "battle_result_roster": {
        "frame": 26,
        "observed_text": [
            "전과보고",
            "키스",
            "레스터",
            "제시카",
            "스코트",
            "POINT",
            "2500P",
        ],
    },
}


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as source:
        image = source.convert("RGB")
        dimensions = [image.width, image.height]
        result_frame_detected = (
            dimensions == [320, 240]
            and all(image.getpixel(point) == color for point, color in RESULT_POINTS.items())
        )
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "dimensions": dimensions,
        "result_frame_detected": result_frame_detected,
    }


def md_checksum(data: bytes) -> int:
    return sum(
        int.from_bytes(data[offset : offset + 2], "big")
        for offset in range(0x200, len(data), 2)
    ) & 0xFFFF


def event_triggers_preserved(candidate: bytes, probe: bytes) -> bool:
    return all(
        candidate[offset : offset + len(expected)]
        == probe[offset : offset + len(expected)]
        == expected
        for offset, expected in probe_builder.COMPLETION_TRIGGERS.items()
    )


def normal_lineage() -> dict[str, object]:
    candidate = NORMAL_CANDIDATE.read_bytes()
    probe = NORMAL_PROBE.read_bytes()
    source = SOURCE_ROM.read_bytes()
    expected = bytearray(candidate)
    probe_builder.patch_probe(
        expected,
        source,
        completion_layout=True,
        protagonist_death=False,
        turn_event=None,
    )
    changed = {
        index
        for index, (before, after) in enumerate(zip(candidate, probe))
        if before != after
    }
    return {
        "method": "exact Scenario 16 completion-layout builder replay",
        "candidate": rom_report(NORMAL_CANDIDATE),
        "probe": rom_report(NORMAL_PROBE),
        "actual_changed_byte_count": len(changed),
        "exact_builder_rebuild": bytes(expected) == probe,
        "event_triggers_preserved": event_triggers_preserved(candidate, probe),
    }


def hard_lineage(normal: dict[str, object]) -> dict[str, object]:
    normal_candidate = NORMAL_CANDIDATE.read_bytes()
    normal_probe = NORMAL_PROBE.read_bytes()
    candidate = HARD_CANDIDATE.read_bytes()
    probe = HARD_PROBE.read_bytes()
    diagnostic_delta = {
        index
        for index, (before, after) in enumerate(zip(normal_candidate, normal_probe))
        if before != after
    }
    expected = bytearray(candidate)
    for index in diagnostic_delta - {0x18E, 0x18F}:
        expected[index] = normal_probe[index]
    builder.update_md_checksum(expected)
    changed = {
        index
        for index, (before, after) in enumerate(zip(candidate, probe))
        if before != after
    }
    conflicts = sum(
        normal_candidate[index] != candidate[index]
        for index in diagnostic_delta - {0x18E, 0x18F}
    )
    return {
        "method": (
            "apply the exact normal diagnostic delta to the hard candidate, "
            "then recalculate only the Mega Drive checksum"
        ),
        "candidate": rom_report(HARD_CANDIDATE),
        "probe": rom_report(HARD_PROBE),
        "normal_diagnostic_changed_byte_count": normal[
            "actual_changed_byte_count"
        ],
        "hard_bytes_replaced_inside_diagnostic_envelope": conflicts,
        "actual_changed_byte_count": len(changed),
        "exact_three_way_overlay": bytes(expected) == probe,
        "event_triggers_preserved": event_triggers_preserved(candidate, probe),
    }


def rom_report(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "header_checksum": f"0x{int.from_bytes(data[0x18E:0x190], 'big'):04X}",
        "computed_checksum": f"0x{md_checksum(data):04X}",
        "checksum_valid": int.from_bytes(data[0x18E:0x190], "big") == md_checksum(data),
    }


def runtime_report(root: Path) -> dict[str, object]:
    sequence_paths = [root / "battle/gate_event_00.png"] + [
        root / f"battle/clear_path_{frame:03d}.png"
        for frame in range(1, 27)
    ]
    sequence = [image_report(path) for path in sequence_paths]
    critical = {}
    for key, row in CRITICAL_SURFACES.items():
        frame = int(row["frame"])
        capture = image_report(root / f"battle/clear_path_{frame:03d}.png")
        critical[key] = {
            **capture,
            "manual_review": "pass",
            "observed_text": row["observed_text"],
        }

    result_image = root / "battle/battle_result.png"
    result_gst = root / "states/battle_result.gst"
    state = load_gst(result_gst)
    header = state.vram[
        RESULT_HEADER_VRAM_START :
        RESULT_HEADER_VRAM_START + RESULT_HEADER_VRAM_BYTES
    ]
    header_cells = result_header_plane_cells(state)
    result = image_report(result_image)
    result_alias = image_report(root / "battle/clear_path_026.png")
    return {
        "sequence": {
            "frame_count": len(sequence),
            "all_dimensions_320x240": all(
                row["dimensions"] == [320, 240] for row in sequence
            ),
            "captures": sequence,
        },
        "critical_surfaces": critical,
        "battle_result": result,
        "result_alias_matches": result["sha256"] == result_alias["sha256"],
        "gst": {
            "path": relative(result_gst),
            "sha256": sha256_path(result_gst),
            "bytes": result_gst.stat().st_size,
        },
        "header_text": "전과보고",
        "header_vram_range": "0xA000..0xA1FF",
        "header_vram_sha256": hashlib.sha256(header).hexdigest(),
        "header_plane_cells": header_cells,
        "all_header_plane_cells_match": all(
            row["matches"] for row in header_cells
        ),
    }


def build_report() -> dict[str, object]:
    normal_diagnostic = normal_lineage()
    lineages = {
        "normal": normal_diagnostic,
        "hard": hard_lineage(normal_diagnostic),
    }
    profiles = {}
    for profile, paths in PROFILES.items():
        runtime = runtime_report(paths["runtime"])
        lineage = lineages[profile]
        exact_lineage = (
            lineage.get("exact_builder_rebuild", False)
            or lineage.get("exact_three_way_overlay", False)
        )
        passed = (
            exact_lineage
            and lineage["event_triggers_preserved"]
            and lineage["probe"]["checksum_valid"]
            and runtime["sequence"]["all_dimensions_320x240"]
            and all(
                row["manual_review"] == "pass"
                for row in runtime["critical_surfaces"].values()
            )
            and runtime["battle_result"]["result_frame_detected"]
            and runtime["result_alias_matches"]
            and runtime["all_header_plane_cells_match"]
        )
        profiles[profile] = {
            "status": "pass" if passed else "fail",
            "diagnostic_lineage": lineage,
            "runtime": runtime,
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
        and all(cross_profile.values())
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": (
            "Current normal/hard Scenario 16 stock castle-gate completion, "
            "dynamic status names, class choice, and battle result"
        ),
        "release_promoted": False,
        "profiles": profiles,
        "cross_profile": cross_profile,
        "limitations": [
            "The weakened-enemy completion ROMs are diagnostic-only and are never release candidates.",
            "Manual text review is hash-bound to the checked captures; later byte changes make --check fail.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report()
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            raise SystemExit(f"checked Scenario 16 result report is stale: {args.output}")
        print(f"checked Scenario 16 result report is current: {args.output}")
        return 0 if report["status"] == "pass" else 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
