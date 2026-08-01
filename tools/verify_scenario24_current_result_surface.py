#!/usr/bin/env python3
"""Verify fresh current normal/hard Scenario 24 result-surface evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario24_clear_probe_rom as probe_builder
from tools import run_scenario24_result_surface as runner
from tools import verify_scenario23_current_result_surface as base


DEFAULT_OUTPUT = ROOT / "localization/scenario24_current_result_surface_regression.json"
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
        "path": ROOT / "tmp/current-result-probes/normal/s24-runtime-clear.md",
        "sha256": "2fddd78d8ecc366ca8909aa8ced6d495c4b0b649fc5a157d57dc9e1f5a089032",
        "checksum": "5812",
    },
    "hard": {
        "path": ROOT / "tmp/current-result-probes/hard/s24-runtime-clear.md",
        "sha256": "2c64319555ccff6b1d9b77ff0cfa18e73e54ad99406426f6cd2eed0e43cbbe50",
        "checksum": "6E1D",
    },
}
RUNS = {
    "normal": {
        "root": ROOT / "captures/run/current_s24_result/normal/runtime02",
        "evidence_sha256": "546f8d8221b2f5e52434ba0478cfade19126b650b4c40e7167d64c3ff07e9753",
        "aftermath_digest": "ce94752e05853ff906485e658dc5737de8614de1db23f8064b9e81dd698d553e",
        "aftermath_bytes": 754636,
        "save_menu_frame": 3,
        "images": {
            "preparation": ("preparation.png", "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437"),
            "turn1_command": ("battle/turn1_command.png", "d742ef1250acb8458e7ff03998f9ea547631074777348dd188b0cd0adb98c49e"),
            "runtime_clear_start": ("battle/runtime_clear_start_menu.png", "f3523ef193e87d6188e60c4f562738b972531586887d61505050a4becbe0f17d"),
            "battle_result": ("aftermath/battle_result.png", "63da3e603663afe4561dbba490267f957c5cf3d529ef7dfff229eac88156f360"),
            "save_menu": ("save/save_menu.png", "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c"),
        },
        "gsts": {
            "before_runtime_clear": ("states/before_runtime_clear.gst", "e8b8114ed1f0f2771f2a804a1f1bd715ab4d670b39da1af53ba25e11b1c3e86c"),
            "runtime_clear_start": ("states/runtime_clear_start_menu.gst", "69346667bff4143a637f01b372fa40c528a9cc530acdb092e9eee5a52407be58"),
            "battle_result": ("states/battle_result.gst", "cc13949473428f9358b4dabb19e7e694229444aa19cdf4e10ba0f4ab4792a363"),
            "save_menu": ("states/save_menu.gst", "d51c1e7054633b5600ea60dd5af2ca0e5ee633bdb31efcfbe2047834e668ab2f"),
        },
    },
    "hard": {
        "root": ROOT / "captures/run/current_s24_result/hard/runtime02",
        "evidence_sha256": "0ac0a602cb603e4aa7f6bf545975ff8914b439df8e6d660397da15417296297b",
        "aftermath_digest": "e72413042ace283f5a9122219a32d5765a70a647497228a5442df8c685799f4d",
        "aftermath_bytes": 754635,
        "save_menu_frame": 3,
        "images": {
            "preparation": ("preparation.png", "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437"),
            "turn1_command": ("battle/turn1_command.png", "d742ef1250acb8458e7ff03998f9ea547631074777348dd188b0cd0adb98c49e"),
            "runtime_clear_start": ("battle/runtime_clear_start_menu.png", "f3523ef193e87d6188e60c4f562738b972531586887d61505050a4becbe0f17d"),
            "battle_result": ("aftermath/battle_result.png", "a6ca94b9370aa789b4d80920570f7ec765b864295f8a2fcd58babd50beb9bed7"),
            "save_menu": ("save/save_menu.png", "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c"),
        },
        "gsts": {
            "before_runtime_clear": ("states/before_runtime_clear.gst", "ca3d16f11ce98e680798e18703983ba1c0dd8d8504a62790782e87a18a35942a"),
            "runtime_clear_start": ("states/runtime_clear_start_menu.gst", "b728f879684a1fa0a11f69b2226190fd7a9005e200381fbb721652309042d0a3"),
            "battle_result": ("states/battle_result.gst", "5e870a4121dbac6743dd72084f609529ee07b145eaadcb681631551ee48cb216"),
            "save_menu": ("states/save_menu.gst", "110a0d96cc833cbe66dd905566e39452317af774f373a72834ce821de21461e9"),
        },
    },
}
AFTERMATH_FRAMES = 42
EXPECTED_CROSS_PROFILE_DIFFERENCES = [42]


def build_report() -> dict[str, object]:
    replacements = {
        "probe_builder": probe_builder,
        "runner": runner,
        "CANDIDATES": CANDIDATES,
        "PROBES": PROBES,
        "RUNS": RUNS,
        "AFTERMATH_FRAMES": AFTERMATH_FRAMES,
        "EXPECTED_CROSS_PROFILE_DIFFERENCES": EXPECTED_CROSS_PROFILE_DIFFERENCES,
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
        "Fresh current normal/hard Scenario 24 preparation, source-preserving "
        "runtime completion, all 42 aftermath frames, result, and save menu"
    )
    manual_review = {
        "status": "pass",
        "reviewed_normal_aftermath_frames": AFTERMATH_FRAMES,
        "reviewed_hard_differing_frames": len(EXPECTED_CROSS_PROFILE_DIFFERENCES),
        "dialogue_and_level_names": [
            "데몬로드", "케르베로스", "리치", "뱀파이어로드",
            "키스", "헤인", "아론", "라나", "리아나", "엘윈",
            "쉐리", "레스터", "스코트",
        ],
        "battle_result_text": [
            "전과보고", "아군", "엘윈", "헤인", "쉐리", "아론",
            "키스", "레스터", "스코트", "리아나", "라나",
            "POINT 55900P",
        ],
        "save_text": ["저장", "다음 시나리오"],
        "broken_dynamic_glyphs_or_sprites": False,
    }
    for profile in ("normal", "hard"):
        report["profiles"][profile]["runtime"]["manual_review"] = manual_review
    report["cross_profile"]["differing_frames_manual_classification"] = (
        "frame 42 lower-unit result animation only: 13 pixels inside a 7x8 "
        "box; no text, name, class, mercenary, commander, portrait, map-sprite, "
        "or UI glyph difference"
    )
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
            raise ValueError(f"stale Scenario 24 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 24 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
