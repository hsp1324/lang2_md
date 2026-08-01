#!/usr/bin/env python3
"""Verify current normal/hard Scenario 13 completion-result evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as md_builder
from tools import build_scenario13_clear_probe_rom as probe_builder
from tools import run_scenario14_15_result_surface as surface_classifier


DEFAULT_OUTPUT = (
    ROOT / "localization/scenario13_current_result_surface_regression.json"
)
SOURCE_ROM = probe_builder.DEFAULT_SOURCE_ROM
SOURCE_STATE = (
    ROOT
    / "captures/runtime/s13-completion-0ce6/.local/share/blastem/"
    "Langrisser II (Scenario 13 Completion Probe)/quicksave.gst"
)
EXPECTED_SOURCE_STATE_SHA256 = (
    "11af030d8cf45a61502a60c1fde7811a3c256e92fcfd751944da739feacad658"
)
EVENT_BLOCK = (0x19A964, 0x19C736)
EXPECTED_CANDIDATES = {
    "normal": {
        "path": ROOT / "tmp/current-glyph-lifetime-fix-normal.md",
        "sha256": (
            "00f0dec38c01db6489d061476648504164b206d1ef73d57bcb9ec7b63e14d371"
        ),
        "checksum": "CB53",
    },
    "hard": {
        "path": ROOT / "tmp/current-glyph-lifetime-fix-hard.md",
        "sha256": (
            "f3d5e050eb84999571c9b575f9236ef01076bbba67542e8af183bf62223bf7ad"
        ),
        "checksum": "E15E",
    },
}
PROFILES = {
    "normal": {
        "probe": ROOT / "tmp/current-result-probes/normal/s13-continuation.md",
        "root": (
            ROOT
            / "captures/run/current_s13_result_debug/normal/continuation-hook02"
        ),
        "target": (
            ROOT
            / "captures/run/current_s13_result_debug/normal/"
            "continuation-hook02_target_vargas.png"
        ),
        "after_attack": (
            ROOT
            / "captures/run/current_s13_result_debug/normal/"
            "continuation-hook02_after_attack.png"
        ),
        "probe_sha256": (
            "e181b1a3b3519b0a54ae80484ac7ef3da9158c4c2f5b48e7f4d69241e6f4435d"
        ),
        "probe_checksum": "A46A",
        "result_points": "6450P",
    },
    "hard": {
        "probe": ROOT / "tmp/current-result-probes/hard/s13-continuation.md",
        "root": (
            ROOT
            / "captures/run/current_s13_result_debug/hard/continuation-hook01"
        ),
        "target": (
            ROOT
            / "captures/run/current_s13_result_debug/hard/"
            "continuation-hook01_target_vargas.png"
        ),
        "after_attack": (
            ROOT
            / "captures/run/current_s13_result_debug/hard/"
            "continuation-hook01_after_attack.png"
        ),
        "probe_sha256": (
            "ed95b5eda14a92c605dc76351cdf91aee3dde85385be6036037244c54bff06fa"
        ),
        "probe_checksum": "9065",
        "result_points": "6420P",
    },
}
CRITICAL_SURFACES = {
    "vargas_departure": {
        "frame": 1,
        "observed_text": ["발가스", "드디어 내 차례인가…"],
        "sha256": {
            "normal": "ea812d0b5a8c22ae9689e3b31120efef827f615b704a0f7192025dfa4f7732c0",
            "hard": "ea812d0b5a8c22ae9689e3b31120efef827f615b704a0f7192025dfa4f7732c0",
        },
    },
    "leon_reveal": {
        "frame": 15,
        "observed_text": ["레온", "내 이름은 레온이다!"],
        "sha256": {
            "normal": "a8e3f2fb76e7ae7e68b4ed966e5790161b3c7687737855065fb3fb571b33410b",
            "hard": "c6ac23d2bff101e05100eee81594fb323977c7f34952f9f3d8cc33a07e5ecf6e",
        },
    },
    "aaron_report": {
        "frame": 20,
        "observed_text": ["아론", "칼자스 성으로 돌아가라"],
        "sha256": {
            "normal": "538e439ca29c528ee98f98b0269856a969f70a5ae139ed7f4501ada65844b743",
            "hard": "538e439ca29c528ee98f98b0269856a969f70a5ae139ed7f4501ada65844b743",
        },
    },
    "elwin_order": {
        "frame": 21,
        "observed_text": ["엘윈", "바로 칼자스로 돌아가자!"],
        "sha256": {
            "normal": "3a1662438e87baddc53c071ffa750b49065ebc9da2104bd7624baa9e4f5b15fe",
            "hard": "3a1662438e87baddc53c071ffa750b49065ebc9da2104bd7624baa9e4f5b15fe",
        },
    },
    "commander_reply": {
        "frame": 25,
        "observed_text": ["제국지휘관", "면목 없습니다."],
        "sha256": {
            "normal": "40d6d9074282f6a94e31fd3b587e062a9399e4f929f560424cc1eb95793eac88",
            "hard": "40d6d9074282f6a94e31fd3b587e062a9399e4f929f560424cc1eb95793eac88",
        },
    },
    "keith_reaction": {
        "frame": 30,
        "observed_text": ["키스", "공주님…"],
        "sha256": {
            "normal": "0d360209e37382d6592f8e8c53bc3c72d980635235cf54c403fd5625e68b9828",
            "hard": "f94fc457605296ba7953115ed0ad0cc3d2b5d17a30b79dbca6d59212e56164d8",
        },
    },
    "jessica_reaction": {
        "frame": 35,
        "observed_text": ["제시카", "설마…"],
        "sha256": {
            "normal": "406d7812fed525232026a09f19a2d42b69fa82d999b87eccd06ff7ea1f2b98bd",
            "hard": "406d7812fed525232026a09f19a2d42b69fa82d999b87eccd06ff7ea1f2b98bd",
        },
    },
    "elwin_resolve": {
        "frame": 40,
        "observed_text": ["엘윈", "리아나를 구할 수 있어?"],
        "sha256": {
            "normal": "dc1d3cf8faf3242de6775bc0abc9df2ed382dc6c5a0d1c77d56e23ddaac87d25",
            "hard": "dc1d3cf8faf3242de6775bc0abc9df2ed382dc6c5a0d1c77d56e23ddaac87d25",
        },
    },
    "keith_skill": {
        "frame": 44,
        "observed_text": ["키스", "스킬 습득!"],
        "sha256": {
            "normal": "ebe58833ec38c7e765f3cc3aae3c737a7b0b4c069e446762759ff657e69e279b",
            "hard": "dccb7cf24dc8d396cf590a29949eadaadd960f2e69e523de67bb913a5b855109",
        },
    },
    "jessica_level": {
        "frame": 45,
        "observed_text": ["제시카의", "레벨이 올랐다!", "MP가 1 상승"],
        "sha256": {
            "normal": "466100cf7a0f4fd56759262ea727e22c20fae89493e93cb3c479c40c4169542e",
            "hard": "466100cf7a0f4fd56759262ea727e22c20fae89493e93cb3c479c40c4169542e",
        },
    },
}
REJECTED_ATTEMPTS = {
    "fresh_southern_layout_before_zorum": {
        "capture": (
            ROOT
            / "captures/run/current_s13_result_debug/normal/attack-zorum02/"
            "advance_20.png"
        ),
        "sha256": "5a3c802520f96d737b7a16bc74f7eaa75e35807063fcb08b8e77b9f3aedc7aaa",
        "reason": (
            "players already occupied the southern arrival lane before the "
            "Zorum event completed; the attempted attack reset to the title"
        ),
    },
    "cached_callback_initializer_only": {
        "capture": (
            ROOT
            / "captures/run/current_s13_result_debug/normal/"
            "legacy-0ce6-current-c_start.png"
        ),
        "sha256": "31981832d52bb19920326e00db7a7e99b215fd75f244af04375cbbca2e6b109f",
        "reason": (
            "the loaded battle had already cached the stock Start callback, "
            "so changing only its initializer did not invoke the HP wrapper"
        ),
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


def rom_report(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    header = int.from_bytes(data[0x18E:0x190], "big")
    computed = md_checksum(data)
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "bytes": len(data),
        "header_checksum": f"{header:04X}",
        "computed_checksum": f"{computed:04X}",
        "checksum_valid": header == computed,
    }


def image_report(path: Path) -> dict[str, object]:
    with Image.open(path) as source:
        dimensions = [source.width, source.height]
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "bytes": path.stat().st_size,
        "dimensions": dimensions,
        "surface": surface_classifier.classify_surface(path),
    }


def diagnostic_delta() -> set[int]:
    candidate = EXPECTED_CANDIDATES["normal"]["path"].read_bytes()
    probe = PROFILES["normal"]["probe"].read_bytes()
    return {
        index
        for index, (before, after) in enumerate(zip(candidate, probe))
        if before != after
    }


def lineage_report(profile: str) -> dict[str, object]:
    candidate_path = EXPECTED_CANDIDATES[profile]["path"]
    probe_path = PROFILES[profile]["probe"]
    candidate = candidate_path.read_bytes()
    probe = probe_path.read_bytes()
    source = SOURCE_ROM.read_bytes()
    if profile == "normal":
        expected = bytearray(candidate)
        probe_builder.patch_probe(
            expected,
            source,
            completion_layout=True,
            completion_continuation=True,
        )
        exact_key = "exact_builder_rebuild"
        method = "exact Scenario 13 continuation-layout builder replay"
        conflicts = 0
    else:
        delta = diagnostic_delta()
        normal_probe = PROFILES["normal"]["probe"].read_bytes()
        normal_candidate = EXPECTED_CANDIDATES["normal"]["path"].read_bytes()
        expected = bytearray(candidate)
        for index in delta - {0x18E, 0x18F}:
            expected[index] = normal_probe[index]
        md_builder.update_md_checksum(expected)
        exact_key = "exact_three_way_overlay"
        method = (
            "apply the exact normal continuation diagnostic delta to the "
            "hard candidate, then recalculate only the Mega Drive checksum"
        )
        conflicts = sum(
            normal_candidate[index] != candidate[index]
            for index in delta - {0x18E, 0x18F}
        )
    candidate_report = rom_report(candidate_path)
    probe_report = rom_report(probe_path)
    event_start, event_end = EVENT_BLOCK
    return {
        "method": method,
        "candidate": candidate_report,
        "candidate_identity_matches": (
            candidate_report["sha256"] == EXPECTED_CANDIDATES[profile]["sha256"]
            and candidate_report["header_checksum"]
            == EXPECTED_CANDIDATES[profile]["checksum"]
        ),
        "probe": probe_report,
        "probe_identity_matches": (
            probe_report["sha256"] == PROFILES[profile]["probe_sha256"]
            and probe_report["header_checksum"]
            == PROFILES[profile]["probe_checksum"]
        ),
        "diagnostic_changed_byte_count": len(diagnostic_delta()),
        "hard_bytes_replaced_inside_diagnostic_envelope": conflicts,
        exact_key: bytes(expected) == probe,
        "complete_event_block_preserved": (
            candidate[event_start:event_end] == probe[event_start:event_end]
        ),
        "event_block": [f"0x{event_start:06X}", f"0x{event_end:06X}"],
        "inline_start_trampoline_installed": (
            probe[
                probe_builder.START_MENU_ENTRY :
                probe_builder.START_MENU_ENTRY
                + probe_builder.START_MENU_ENTRY_PATCH_SIZE
            ]
            == bytes.fromhex("4E F9")
            + probe_builder.COMPLETION_HP_WRAPPER.to_bytes(4, "big")
        ),
    }


def critical_surface_report(profile: str, root: Path) -> dict[str, object]:
    rows = {}
    for key, definition in CRITICAL_SURFACES.items():
        path = root / f"advance_{definition['frame']:02d}.png"
        report = image_report(path)
        expected = definition["sha256"][profile]
        rows[key] = {
            **report,
            "expected_reviewed_sha256": expected,
            "reviewed_hash_matches": report["sha256"] == expected,
            "manual_review": "pass",
            "observed_text": definition["observed_text"],
            "observed_sprite_state": "clean",
        }
    return rows


def runtime_report(profile: str) -> dict[str, object]:
    definition = PROFILES[profile]
    root = definition["root"]
    sequence = [image_report(root / f"advance_{frame:02d}.png") for frame in range(1, 49)]
    target = image_report(definition["target"])
    after_attack = image_report(definition["after_attack"])
    result = image_report(root / "advance_46.png")
    save_empty = image_report(root / "advance_47.png")
    save_written = image_report(root / "advance_48.png")
    route = image_report(root / "next_selected.png")
    title = image_report(root / "scenario14_title.png")
    return {
        "sequence": {
            "frame_count": len(sequence),
            "all_dimensions_320x240": all(
                row["dimensions"] == [320, 240] for row in sequence
            ),
            "captures": sequence,
        },
        "vargas_hp_one_target": {
            **target,
            "manual_review": "pass",
            "observed_text": ["발가스", "파이터", "HP1"],
        },
        "devil_axe_and_vargas_hp_zero": {
            **after_attack,
            "manual_review": "pass",
            "observed_text": ["데빌액스 획득!", "발가스 HP0"],
        },
        "critical_surfaces": critical_surface_report(profile, root),
        "battle_result": {
            **result,
            "manual_review": "pass",
            "observed_roster": [
                "전과보고",
                "아론",
                "엘윈",
                "헤인",
                "쉐리",
                "키스",
                "레스터",
                "제시카",
                "POINT",
                definition["result_points"],
            ],
            "observed_sprite_state": "clean",
        },
        "save_menu_before_write": save_empty,
        "scenario14_save_written": {
            **save_written,
            "manual_review": "pass",
            "observed_text": ["저장", "시나리오 14", "다음 시나리오"],
        },
        "scenario14_route": {
            **route,
            "manual_review": "pass",
            "observed_text": ["진군루트"],
        },
        "scenario14_title": {
            **title,
            "manual_review": "pass",
            "observed_text": ["시나리오 14", "성검 랑그릿사"],
        },
        "scope_limit": (
            "the cross-checksum continuation proves the current ROM's stock "
            "Vargas aftermath, result, save, route, and next-title surfaces; "
            "pre-result map sprites are covered by the independent current "
            "preparation/gray-sprite matrices and are not claimed here"
        ),
    }


def result_difference(normal: Path, hard: Path) -> dict[str, object]:
    with Image.open(normal) as normal_source, Image.open(hard) as hard_source:
        normal_image = normal_source.convert("RGB")
        hard_image = hard_source.convert("RGB")
        difference = ImageChops.difference(normal_image, hard_image)
        difference_bbox = difference.getbbox()
        header_identical = (
            normal_image.crop((0, 0, 320, 72)).tobytes()
            == hard_image.crop((0, 0, 320, 72)).tobytes()
        )
    return {
        "battle_result_frame_identical": sha256_path(normal) == sha256_path(hard),
        "difference_bbox": list(difference_bbox) if difference_bbox else None,
        "difference_is_points_digit_only": difference_bbox == (272, 97, 279, 105),
        "result_header_and_roster_top_identical": header_identical,
        "manual_difference_review": "pass",
    }


def rejected_report() -> dict[str, object]:
    attempts = {}
    for key, definition in REJECTED_ATTEMPTS.items():
        report = image_report(definition["capture"])
        attempts[key] = {
            **report,
            "expected_sha256": definition["sha256"],
            "hash_matches": report["sha256"] == definition["sha256"],
            "reason": definition["reason"],
            "accepted": False,
        }
    return {
        "status": "rejected",
        "attempts": attempts,
        "acceptance_updated": False,
    }


def build_report() -> dict[str, object]:
    source_state = {
        "path": relative(SOURCE_STATE),
        "sha256": sha256_path(SOURCE_STATE),
        "bytes": SOURCE_STATE.stat().st_size,
        "identity_matches": sha256_path(SOURCE_STATE)
        == EXPECTED_SOURCE_STATE_SHA256,
        "method": (
            "historical 0CE6 battle continuation loaded without RAM edits; "
            "the current diagnostic ROM changed only the declared completion "
            "layout and the identity-guarded Start-entry trampoline"
        ),
    }
    profiles = {}
    for profile in ("normal", "hard"):
        lineage = lineage_report(profile)
        runtime = runtime_report(profile)
        profile_pass = (
            lineage["candidate_identity_matches"]
            and lineage["probe_identity_matches"]
            and lineage["candidate"]["checksum_valid"]
            and lineage["probe"]["checksum_valid"]
            and lineage["complete_event_block_preserved"]
            and lineage["inline_start_trampoline_installed"]
            and (
                lineage.get("exact_builder_rebuild", False)
                if profile == "normal"
                else lineage.get("exact_three_way_overlay", False)
            )
            and runtime["sequence"]["frame_count"] == 48
            and runtime["sequence"]["all_dimensions_320x240"]
            and runtime["battle_result"]["surface"] == "battle_result"
            and runtime["save_menu_before_write"]["surface"] == "save_menu"
            and runtime["scenario14_save_written"]["surface"] == "save_menu"
            and all(
                row["reviewed_hash_matches"]
                for row in runtime["critical_surfaces"].values()
            )
        )
        profiles[profile] = {
            "status": "pass" if profile_pass else "fail",
            "diagnostic_lineage": lineage,
            "runtime": runtime,
        }
    normal_result = PROFILES["normal"]["root"] / "advance_46.png"
    hard_result = PROFILES["hard"]["root"] / "advance_46.png"
    cross_profile = result_difference(normal_result, hard_result)
    rejected = rejected_report()
    status = (
        "pass"
        if all(row["status"] == "pass" for row in profiles.values())
        and source_state["identity_matches"]
        and cross_profile["difference_is_points_digit_only"]
        and cross_profile["result_header_and_roster_top_identical"]
        and all(
            row["hash_matches"] and not row["accepted"]
            for row in rejected["attempts"].values()
        )
        else "fail"
    )
    return {
        "schema_version": 1,
        "status": status,
        "scope": (
            "Current normal/hard Scenario 13 stock Vargas aftermath, dynamic "
            "dialogue names, result roster, Scenario 14 save, route, and title"
        ),
        "release_promoted": False,
        "acceptance_updated": False,
        "source_state": source_state,
        "profiles": profiles,
        "cross_profile": cross_profile,
        "rejected_attempts": rejected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file():
            raise FileNotFoundError(args.output)
        if args.output.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"stale Scenario 13 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 13 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
