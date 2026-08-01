#!/usr/bin/env python3
"""Verify fresh current normal/hard Scenario 26 result-surface evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_scenario26_clear_probe_rom as probe_builder
from tools import run_scenario26_result_surface as runner
from tools import verify_scenario23_current_result_surface as base


DEFAULT_OUTPUT = ROOT / "localization/scenario26_current_result_surface_regression.json"
NORMAL_CANDIDATE = ROOT / "tmp/current-s26-particle-fix-normal.md"
HARD_CANDIDATE = ROOT / "tmp/current-s26-particle-fix-hard.md"
CANDIDATES = {
    "normal": {
        "path": NORMAL_CANDIDATE,
        "sha256": "178e70487d4defc3e801abeb37cee43066db0ab5f8685c4c300ea0431336bb70",
        "checksum": "CAF3",
    },
    "hard": {
        "path": HARD_CANDIDATE,
        "sha256": "9c6282c7f31f8ad0569944a4fdab0929b53a28b1c5308777eb199c278ecc5f56",
        "checksum": "E0FE",
    },
}
PROBES = {
    "normal": {
        "path": ROOT / "tmp/current-result-probes/normal/s26-particle-runtime-clear.md",
        "sha256": "c038e7688301f5bab55808cd9fd39367093df05f441ffa0cb26f93721cfabb4b",
        "checksum": "031A",
    },
    "hard": {
        "path": ROOT / "tmp/current-result-probes/hard/s26-particle-runtime-clear.md",
        "sha256": "2d0cae9212fd32f469c1d1932d42e7161d81ec9d2df2a4b753c6b237e9fc00aa",
        "checksum": "1925",
    },
}
RUNS = {
    "normal": {
        "root": ROOT / "captures/run/current_s26_result/normal/runtime02",
        "evidence_sha256": "0bee3549db59b4ae63183944f957bf6f4f9da0b7a7a3a25c13b436c570f3138e",
        "aftermath_digest": "7fd1538620df76d77c41c1ca218d20a9361299629a5dcd5a1871be2a27c81d7c",
        "aftermath_bytes": 627326,
        "save_menu_frame": 3,
        "images": {
            "preparation": ("preparation.png", "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437"),
            "turn1_command": ("battle/turn1_command.png", "7e3bb76c730f9ff1a72f6f83d2f215987a40d0b5aff1fa471c751ff4158802b3"),
            "runtime_clear_start": ("battle/runtime_clear_start_menu.png", "a61629bff6b24b51ebbff75597733cbb888e29670f0aaba229bba9a29b8fea4f"),
            "battle_result": ("aftermath/battle_result.png", "515d706586cf18ff506884daf9045f38252f696073338fbd82c76d189a097759"),
            "save_menu": ("save/save_menu.png", "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c"),
        },
        "gsts": {
            "before_runtime_clear": ("states/before_runtime_clear.gst", "9e6d2b5a9ec645c627c8c5848036ccf5af628d0382ba8526a06b0586067faa04"),
            "runtime_clear_start": ("states/runtime_clear_start_menu.gst", "c55adfe62995533af993a5dc8326fe9381c58aa82adb9487549c5257e7fe23b7"),
            "battle_result": ("states/battle_result.gst", "f7b2f214d748d3de7d5607acacf31e3fa5c000ed99f62d4e6fb517346d5ef511"),
            "save_menu": ("states/save_menu.gst", "b44e8a5aae7c33934163429a6c5990c187020954e2f8571b8d9795e84ab435e5"),
        },
    },
    "hard": {
        "root": ROOT / "captures/run/current_s26_result/hard/runtime02",
        "evidence_sha256": "3ce1bef817082f46200a46a4577322c59d8934e9cbb9d1893a6486977b8faae2",
        "aftermath_digest": "75749c6f7da2d211ac1da6f414ace6484fde422ec9e397f14f493df93e79a8b1",
        "aftermath_bytes": 627237,
        "save_menu_frame": 3,
        "images": {
            "preparation": ("preparation.png", "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437"),
            "turn1_command": ("battle/turn1_command.png", "7e3bb76c730f9ff1a72f6f83d2f215987a40d0b5aff1fa471c751ff4158802b3"),
            "runtime_clear_start": ("battle/runtime_clear_start_menu.png", "a61629bff6b24b51ebbff75597733cbb888e29670f0aaba229bba9a29b8fea4f"),
            "battle_result": ("aftermath/battle_result.png", "8fc7186e3d9c2ef0caf019c565b9be517f63a19b127b0d7dbdc6d0a8de923cbb"),
            "save_menu": ("save/save_menu.png", "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c"),
        },
        "gsts": {
            "before_runtime_clear": ("states/before_runtime_clear.gst", "41ae598d32540b54245ae64dc5fdcb8b5a8dd58d163a98a3b550aae2aaadabf6"),
            "runtime_clear_start": ("states/runtime_clear_start_menu.gst", "8212f09b78516785e240b177728f8cdd627a1dd95c44aa2ed1f635628bef10ad"),
            "battle_result": ("states/battle_result.gst", "bbeae582c03baccaecb22c3f44c20ed44df408cbaa0c00b541335bf163a409ab"),
            "save_menu": ("states/save_menu.gst", "8da931e4a3b7877e24df60d618dd34d85b718e62f1763a8be363dd612cb61e8c"),
        },
    },
}
AFTERMATH_FRAMES = 42
EXPECTED_CROSS_PROFILE_DIFFERENCES = [32, 34, 42]
IDENTITY_NOTE = "all 10 fixed enemy records match at runtime"


def build_report() -> dict[str, object]:
    replacements = {
        "probe_builder": probe_builder,
        "runner": runner,
        "NORMAL_CANDIDATE": NORMAL_CANDIDATE,
        "HARD_CANDIDATE": HARD_CANDIDATE,
        "CANDIDATES": CANDIDATES,
        "PROBES": PROBES,
        "RUNS": RUNS,
        "AFTERMATH_FRAMES": AFTERMATH_FRAMES,
        "EXPECTED_CROSS_PROFILE_DIFFERENCES": EXPECTED_CROSS_PROFILE_DIFFERENCES,
        "EXPECTED_IDENTITY_MATCHED_RECORDS": 10,
        "EXPECTED_IDENTITY_TOTAL_RECORDS": 10,
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
        "Fresh current normal/hard Scenario 26 preparation, source-preserving "
        "runtime completion, corrected Bozel particle, all 42 aftermath "
        "frames, result, and save menu"
    )
    report["dialogue_fix"] = {
        "status": "pass",
        "source_record_address": "0x1B35B4",
        "tile_word_offset": "0x1B35C0",
        "old_tile_word": "7089",
        "new_tile_word": "7029",
        "expected_text": "제시카: 에그베르트는 보젤과 싸울 강대한 힘이 급히 필요했죠…",
        "normal_live_frame": "captures/run/current_s26_result/normal/runtime02/aftermath/advance_021.png",
        "hard_live_frame": "captures/run/current_s26_result/hard/runtime02/aftermath/advance_021.png",
        "old_normal_run_rejected": (
            "normal/runtime01 used the pre-fix text 보젤와 and carries no "
            "acceptance claim"
        ),
    }
    report["automation_notes"] = {
        "normal_selector_attempt_1": (
            "timed out after 80 selector confirmations; the automatic clean "
            "retry entered Scenario 26 on attempt 2"
        ),
        "normal_accepted_attempt": 2,
        "hard_accepted_attempt": 1,
    }
    manual_review = {
        "status": "pass",
        "reviewed_normal_aftermath_frames": AFTERMATH_FRAMES,
        "reviewed_hard_differing_frames": len(EXPECTED_CROSS_PROFILE_DIFFERENCES),
        "dialogue_and_level_names": [
            "에그베르트", "제국군지휘관", "제시카", "레스터", "라나",
            "리아나", "엘윈", "헤인", "쉐리",
        ],
        "corrected_dialogue": ["보젤과 싸울"],
        "level_text": ["클래스체인지 가능"],
        "battle_result_text": [
            "전과보고", "아군", "엘윈", "헤인", "쉐리", "아론",
            "키스", "레스터", "스코트", "리아나", "라나", "제시카",
            "POINT 4240P",
        ],
        "save_text": ["저장", "다음 시나리오"],
        "broken_dynamic_glyphs_or_sprites": False,
    }
    for profile in ("normal", "hard"):
        lineage = report["profiles"][profile]["diagnostic_lineage"]
        lineage["scope_limit"] = (
            "diagnostic only: Start preserves runtime groups 0..9 and marks "
            "only hostile runtime groups 10..19 defeated; all fixed records, "
            "deployments, events, identities, and combat values remain "
            "byte-identical to the input candidate"
        )
        report["profiles"][profile]["runtime"]["manual_review"] = manual_review

    cross = report["cross_profile"]
    cross["differing_frame_bboxes"] = {
        "32": [0, 49, 8, 65],
        "34": [280, 49, 296, 65],
        "42": [56, 121, 295, 169],
    }
    cross["differing_frames_manual_classification"] = (
        "frames 32 and 34 differ only in small opposite-edge map animation "
        "boxes; frame 42 differs only in result-unit animation. No text tile, "
        "name, class, mercenary, commander, portrait, map sprite, or UI glyph "
        "is corrupt."
    )
    report["status"] = "pass" if (
        all(row["status"] == "pass" for row in report["profiles"].values())
        and report["dialogue_fix"]["status"] == "pass"
        and cross["preparation_pixel_identical"]
        and cross["turn1_command_pixel_identical"]
        and cross["runtime_clear_start_pixel_identical"]
        and cross["aftermath_differences_match_reviewed_set"]
        and cross["save_menu_pixel_identical"]
        and cross["result_manual_content_identical"]
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
            raise ValueError(f"stale Scenario 26 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 26 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
