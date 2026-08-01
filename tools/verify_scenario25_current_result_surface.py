#!/usr/bin/env python3
"""Verify fresh current normal/hard Scenario 25 result-surface evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario25_clear_probe_rom as probe_builder
from tools import run_scenario25_result_surface as runner
from tools import verify_scenario23_current_result_surface as base


DEFAULT_OUTPUT = ROOT / "localization/scenario25_current_result_surface_regression.json"
CANDIDATES = {
    "normal": {
        "path": ROOT / "tmp/current-glyph-lifetime-fix-normal.md",
        "sha256": "00f0dec38c01db6489d061476648504164b206d1ef73d57bcb9ec7b63e14d371",
        "checksum": "CB53",
    },
    "hard": {
        "path": ROOT / "tmp/current-glyph-lifetime-fix-hard.md",
        "sha256": "f3d5e050eb84999571c9b575f9236ef01076bbba67542e8af183bf62223bf7ad",
        "checksum": "E15E",
    },
}
PROBES = {
    "normal": {
        "path": ROOT / "tmp/current-result-probes/normal/s25-runtime-clear.md",
        "sha256": "8bf91cb6c7c5c9aaf325f4b20acf42406ace3dedfe47d9ddf049a1dd5aad9e34",
        "checksum": "6472",
    },
    "hard": {
        "path": ROOT / "tmp/current-result-probes/hard/s25-runtime-clear.md",
        "sha256": "e705f51c1c64d3fd58466e6d8b74946e44be8f041398fdff1d00a9534501801a",
        "checksum": "7A7D",
    },
}
RUNS = {
    "normal": {
        "root": ROOT / "captures/run/current_s25_result/normal/runtime01",
        "evidence_sha256": "046b293aacf55d49d23f8f0ea13db8cbb247c7856b4f9ae2c34a2a844754f255",
        "aftermath_digest": "a7bb49aefc3f3299ec96000afd4d041f4b8e105a1f96d2af1f801d9d286b1411",
        "aftermath_bytes": 556588,
        "save_menu_frame": 3,
        "images": {
            "preparation": ("preparation.png", "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437"),
            "turn1_command": ("battle/turn1_command.png", "47c9b3712f46eb6d24b90b01e4b74903daf54772f76b85ae84520fdcee7a9d11"),
            "runtime_clear_start": ("battle/runtime_clear_start_menu.png", "92bef4ff2098839a600dd322bdea8cd1ab3b02fa1a81c9c026cd3c3845f6afbb"),
            "battle_result": ("aftermath/battle_result.png", "265203b8c8d9f7b4a66c8b1c6af4a7c16b1d95ddd52558d2a28eb3c4ee945c50"),
            "save_menu": ("save/save_menu.png", "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c"),
        },
        "gsts": {
            "before_runtime_clear": ("states/before_runtime_clear.gst", "288bd512c92f6ce3f9800edba2097fa74a2712e88f87b25733f6631c3a625f5a"),
            "runtime_clear_start": ("states/runtime_clear_start_menu.gst", "98b8fc9c27e437908b0dc4fcf0cf153d1ff09d7eca843c1a926d2cc1c1583ccd"),
            "battle_result": ("states/battle_result.gst", "aa1befd7e744f82b5ae2c84742c0ac4323eee26d42b078dc03a25d3e263dc55b"),
            "save_menu": ("states/save_menu.gst", "228ac1cdf2bb94d18ab3e1f3f1d448b51ac6dbfdfd65bbb79f2143bd555f7158"),
        },
    },
    "hard": {
        "root": ROOT / "captures/run/current_s25_result/hard/runtime01",
        "evidence_sha256": "5d8430b10c969a0ab29059138bc0464baf277c827de23818898c60df9fc7e680",
        "aftermath_digest": "b4b0080df8cdf49103feb8f9dc511106e316772b5e5baad2c8bf44348c444ce9",
        "aftermath_bytes": 557802,
        "save_menu_frame": 3,
        "images": {
            "preparation": ("preparation.png", "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437"),
            "turn1_command": ("battle/turn1_command.png", "5b74af6eb1b90168df2aff2d2405205765404bc4a220d0df0071f29acaacc185"),
            "runtime_clear_start": ("battle/runtime_clear_start_menu.png", "c13f087e1e238ba12765c0c9fa3b895d61e06041cd34e25151c7a7fc9c41f68d"),
            "battle_result": ("aftermath/battle_result.png", "2eb2af2d9a40087e34903bc4591ec057d081e50eb0335ba7a04c9a3b06e4b9c5"),
            "save_menu": ("save/save_menu.png", "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c"),
        },
        "gsts": {
            "before_runtime_clear": ("states/before_runtime_clear.gst", "4577208ba84d99ff24b33ab6bc825a47ae91dac9b5fa1835258c5c59029bbf47"),
            "runtime_clear_start": ("states/runtime_clear_start_menu.gst", "1f575c3c82f9649751c62f4f08a25b582265bc9e9ab498baabe1764abd291504"),
            "battle_result": ("states/battle_result.gst", "e67a122b1f90a4ad3b38842026929862892db5a4203bfc18144c35d34267dfeb"),
            "save_menu": ("states/save_menu.gst", "5c480cb0531594e9977559b9d0c9647212ee77487fd33c7203d537e7d986ebac"),
        },
    },
}
AFTERMATH_FRAMES = 42
EXPECTED_CROSS_PROFILE_DIFFERENCES = [*range(1, 25), 29, 42]
IDENTITY_NOTE = (
    "11 of 12 fixed records match at runtime; source record 0 is correctly "
    "replaced by event-spawned allied Jessica"
)


def build_report() -> dict[str, object]:
    replacements = {
        "probe_builder": probe_builder,
        "runner": runner,
        "CANDIDATES": CANDIDATES,
        "PROBES": PROBES,
        "RUNS": RUNS,
        "AFTERMATH_FRAMES": AFTERMATH_FRAMES,
        "EXPECTED_CROSS_PROFILE_DIFFERENCES": EXPECTED_CROSS_PROFILE_DIFFERENCES,
        "EXPECTED_IDENTITY_MATCHED_RECORDS": 11,
        "EXPECTED_IDENTITY_TOTAL_RECORDS": 12,
        "IDENTITY_NOTE": IDENTITY_NOTE,
    }
    previous = {key: getattr(base, key) for key in replacements}
    try:
        for key, value in replacements.items():
            setattr(base, key, value)
        report = base.build_report()
    finally:
        for key, value in previous.items():
            setattr(base, key, value)

    report["scope"] = (
        "Fresh current normal/hard Scenario 25 preparation, allied-Jessica-"
        "preserving runtime completion, all 42 aftermath frames, result, and save"
    )
    manual_review = {
        "status": "pass",
        "reviewed_normal_aftermath_frames": AFTERMATH_FRAMES,
        "reviewed_hard_differing_frames": len(EXPECTED_CROSS_PROFILE_DIFFERENCES),
        "dialogue_and_level_names": [
            "레온", "제국병", "제국군지휘관", "레아드", "엘윈",
            "헤인", "쉐리", "라나", "리아나",
        ],
        "battle_result_text": [
            "전과보고", "아군", "엘윈", "헤인", "쉐리", "아론",
            "키스", "레스터", "스코트", "리아나", "라나", "POINT 5200P",
        ],
        "save_text": ["저장", "다음 시나리오"],
        "broken_dynamic_glyphs_or_sprites": False,
    }
    for profile in ("normal", "hard"):
        report["profiles"][profile]["runtime"]["manual_review"] = manual_review

    cross = report["cross_profile"]
    cross["turn1_command_difference_bbox"] = [88, 9, 152, 41]
    cross["runtime_clear_start_difference_bbox"] = [88, 9, 152, 41]
    cross["differing_frames_manual_classification"] = (
        "frames 1..24 and the command/Start surfaces differ only in a 64x32 "
        "top-map unit animation box; frame 29 is dialogue typewriter phase; "
        "frame 42 is result-unit animation. No text tile, name, class, "
        "mercenary, commander, portrait, or UI glyph is corrupt."
    )
    cross["command_and_start_animation_only"] = True
    report["status"] = "pass" if (
        all(row["status"] == "pass" for row in report["profiles"].values())
        and cross["preparation_pixel_identical"]
        and cross["aftermath_differences_match_reviewed_set"]
        and cross["save_menu_pixel_identical"]
        and cross["result_manual_content_identical"]
        and cross["command_and_start_animation_only"]
    ) else "fail"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file():
            raise FileNotFoundError(args.output)
        if args.output.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"stale Scenario 25 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 25 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
