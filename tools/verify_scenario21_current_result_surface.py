#!/usr/bin/env python3
"""Verify fresh current normal/hard Scenario 21 result-surface evidence."""

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

from scripts import build_korean_jp_probe as md_builder
from tools import build_scenario21_clear_probe_rom as probe_builder
from tools import run_scenario14_15_result_surface as surface_classifier
from tools import run_scenario21_result_surface as runner


DEFAULT_OUTPUT = ROOT / "localization/scenario21_current_result_surface_regression.json"
NORMAL_CANDIDATE = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
HARD_CANDIDATE = ROOT / "tmp/current-glyph-lifetime-fix-hard.md"
CANDIDATES = {
    "normal": {
        "path": NORMAL_CANDIDATE,
        "sha256": "00f0dec38c01db6489d061476648504164b206d1ef73d57bcb9ec7b63e14d371",
        "checksum": "CB53",
    },
    "hard": {
        "path": HARD_CANDIDATE,
        "sha256": "f3d5e050eb84999571c9b575f9236ef01076bbba67542e8af183bf62223bf7ad",
        "checksum": "E15E",
    },
}
PROBES = {
    "normal": {
        "path": ROOT / "tmp/current-result-probes/normal/s21-runtime-clear.md",
        "sha256": "7b16954a5cf601f36867eaffaf815cde532da524070f84c3a5c23076f218e672",
        "checksum": "F4DA",
    },
    "hard": {
        "path": ROOT / "tmp/current-result-probes/hard/s21-runtime-clear.md",
        "sha256": "eb41d394502e55ebcd86ea4cc2d5b603faa69a194df2773f49b0ff1a3c61d46e",
        "checksum": "0AE5",
    },
}
RUNS = {
    "normal": {
        "root": ROOT / "captures/run/current_s21_result/normal/runtime01",
        "evidence_sha256": "64f2a69882a38ec4a8624c4378b72631eb0010c9869e9460f8c46230cffc38e3",
        "images": {
            "preparation": (
                "preparation.png",
                "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437",
            ),
            "turn1_command": (
                "battle/turn1_command.png",
                "e1a68e4595077f5c06ffd806034c03ba125172e0f4b14693aa609c305319ab51",
            ),
            "runtime_clear_start": (
                "battle/runtime_clear_start_menu.png",
                "6bdb17d1624a42d57934deb92d31e55219ece16144e0c7c07ec34f27f8278710",
            ),
            "battle_result": (
                "aftermath/battle_result.png",
                "c29063158456ce72f39bb0de6cd7477f23cd9c2a0a00877234ae6fdbf74d6dba",
            ),
            "save_menu": (
                "save/save_menu.png",
                "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c",
            ),
        },
        "gsts": {
            "runtime_clear_start": (
                "states/runtime_clear_start_menu.gst",
                "659af65cd58d1c66548653bbeb940f8031d93ab55abd2381e83b227e753d1181",
            ),
            "battle_result": (
                "states/battle_result.gst",
                "399156d7620f94137ce4e78ae2650bfd2a7d8b14c47d1a144f67dc1d4573906d",
            ),
            "save_menu": (
                "states/save_menu.gst",
                "50fb0bb5388fc66a6095f9d402df1bab6dfe244275f9d64b036db97c1f3f951a",
            ),
        },
    },
    "hard": {
        "root": ROOT / "captures/run/current_s21_result/hard/runtime01",
        "evidence_sha256": "af9a996da1ae9a09c22e43e39d6f1de51c53eadcf0d60fbeb3b3cd12c4234eea",
        "images": {
            "preparation": (
                "preparation.png",
                "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437",
            ),
            "turn1_command": (
                "battle/turn1_command.png",
                "e1a68e4595077f5c06ffd806034c03ba125172e0f4b14693aa609c305319ab51",
            ),
            "runtime_clear_start": (
                "battle/runtime_clear_start_menu.png",
                "6bdb17d1624a42d57934deb92d31e55219ece16144e0c7c07ec34f27f8278710",
            ),
            "battle_result": (
                "aftermath/battle_result.png",
                "9c62d41a22ae2a6584b161285570bfd424d6c5f2b2961b4e77bc573020d830c1",
            ),
            "save_menu": (
                "save/save_menu.png",
                "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c",
            ),
        },
        "gsts": {
            "runtime_clear_start": (
                "states/runtime_clear_start_menu.gst",
                "949276d1379b1222e6f2f26f5bce0d8dad4c7607f6fc69274aed415fab9eb21c",
            ),
            "battle_result": (
                "states/battle_result.gst",
                "ee08bdf362a3c0aab56f3ae24e39e5f733cc5eb8bab21c69b954d428f5688230",
            ),
            "save_menu": (
                "states/save_menu.gst",
                "a74bff19e28aecfa78f27b7760c51aa0d47de11c92eb18766714b44812d3eb50",
            ),
        },
    },
}


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def md_checksum(data: bytes) -> int:
    return sum(
        int.from_bytes(data[offset:offset + 2], "big")
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


def lineage_report(profile: str) -> dict[str, object]:
    source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
    normal_candidate = NORMAL_CANDIDATE.read_bytes()
    rebuilt_normal = bytearray(normal_candidate)
    probe_builder.patch_probe(rebuilt_normal, source, runtime_clear=True)
    delta = {
        offset
        for offset, (before, after) in enumerate(
            zip(normal_candidate, rebuilt_normal)
        )
        if before != after
    }
    candidate = CANDIDATES[profile]["path"].read_bytes()
    probe = PROBES[profile]["path"].read_bytes()
    if profile == "normal":
        expected = rebuilt_normal
        conflicts = 0
        method = "exact current-normal runtime-clear builder replay"
    else:
        expected = bytearray(candidate)
        for offset in delta - {0x18E, 0x18F}:
            expected[offset] = rebuilt_normal[offset]
        md_builder.update_md_checksum(expected)
        conflicts = sum(
            normal_candidate[offset] != candidate[offset]
            for offset in delta - {0x18E, 0x18F}
        )
        method = (
            "exact current-normal diagnostic delta over the current hard "
            "candidate, followed only by checksum recalculation"
        )
    candidate_report = rom_report(CANDIDATES[profile]["path"])
    probe_report = rom_report(PROBES[profile]["path"])
    wrapper = probe_builder.runtime_clear_wrapper_code()
    source_layout = probe_builder.scenario_layout(
        source, probe_builder.SCENARIO_NUMBER
    )
    fixed_start = source_layout.records_offset
    fixed_end = fixed_start + source_layout.record_count * probe_builder.FIXED_RECORD_SIZE
    deployment_start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
    deployment_end = deployment_start + len(
        probe_builder.deployment_bytes(probe_builder.SOURCE_PLAYER_DEPLOYMENTS)
    )
    return {
        "method": method,
        "candidate": candidate_report,
        "candidate_identity_matches": (
            candidate_report["sha256"] == CANDIDATES[profile]["sha256"]
            and candidate_report["header_checksum"]
            == CANDIDATES[profile]["checksum"]
        ),
        "probe": probe_report,
        "probe_identity_matches": (
            probe_report["sha256"] == PROBES[profile]["sha256"]
            and probe_report["header_checksum"] == PROBES[profile]["checksum"]
        ),
        "diagnostic_changed_byte_count": len(delta),
        "hard_bytes_replaced_inside_diagnostic_envelope": conflicts,
        "exact_rebuild": bytes(expected) == probe,
        "wrapper_exact": (
            probe[
                probe_builder.COMPLETION_HP_WRAPPER:
                probe_builder.COMPLETION_HP_WRAPPER + len(wrapper)
            ]
            == wrapper
        ),
        "start_entry_targets_wrapper": (
            probe[
                probe_builder.START_MENU_ENTRY_OPERAND:
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ]
            == probe_builder.COMPLETION_HP_WRAPPER.to_bytes(4, "big")
        ),
        "fixed_records_input_exact": probe[fixed_start:fixed_end]
        == candidate[fixed_start:fixed_end],
        "normal_fixed_records_source_exact": (
            profile != "normal"
            or probe[fixed_start:fixed_end] == source[fixed_start:fixed_end]
        ),
        "player_deployments_input_exact": probe[
            deployment_start:deployment_end
        ] == candidate[deployment_start:deployment_end],
        "normal_player_deployments_source_exact": (
            profile != "normal"
            or probe[deployment_start:deployment_end]
            == source[deployment_start:deployment_end]
        ),
        "scope_limit": (
            "diagnostic only: Start marks hostile runtime groups defeated; "
            "all fixed records, deployments, events, identities, and combat "
            "values remain byte-identical to the input candidate"
        ),
    }


def image_report(root: Path, definition: tuple[str, str]) -> dict[str, object]:
    relative_path, expected_sha256 = definition
    path = root / relative_path
    with Image.open(path) as source:
        dimensions = [source.width, source.height]
    actual_sha256 = sha256_path(path)
    return {
        "path": relative(path),
        "sha256": actual_sha256,
        "expected_sha256": expected_sha256,
        "hash_matches": actual_sha256 == expected_sha256,
        "bytes": path.stat().st_size,
        "dimensions": dimensions,
        "surface": surface_classifier.classify_surface(path),
    }


def gst_report(root: Path, definition: tuple[str, str]) -> dict[str, object]:
    relative_path, expected_sha256 = definition
    path = root / relative_path
    actual_sha256 = sha256_path(path)
    return {
        "path": relative(path),
        "sha256": actual_sha256,
        "expected_sha256": expected_sha256,
        "hash_matches": actual_sha256 == expected_sha256,
        "bytes": path.stat().st_size,
    }


def runtime_report(profile: str) -> dict[str, object]:
    definition = RUNS[profile]
    root = definition["root"]
    evidence_path = root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    images = {
        key: image_report(root, value)
        for key, value in definition["images"].items()
    }
    gsts = {
        key: gst_report(root, value)
        for key, value in definition["gsts"].items()
    }
    clear_state = runner.runtime_clear_state(
        root / definition["gsts"]["runtime_clear_start"][0]
    )
    identity = evidence["scenario_identity"]
    groups = clear_state["groups"]
    hostile_ids = set(probe_builder.RUNTIME_CLEAR_GROUPS)
    hostile_state_valid = (
        clear_state["hostiles_defeated"]
        and clear_state["lana_untouched_by_wrapper"]
        and all(
            groups[str(group)]["defeated_flag"] & 0x80
            and groups[str(group)]["hp"] == 0
            and groups[str(group)]["x"] == 0xFF
            for group in hostile_ids
        )
        and groups[str(probe_builder.LANA_RUNTIME_GROUP)] == {
            "class_id": 0x60,
            "name_id": 0x0C,
            "defeated_flag": 0,
            "hp": 10,
            "x": 37,
            "y": 11,
        }
    )
    passed = (
        evidence["status"] == "pass"
        and evidence["profile"] == profile
        and evidence["scenario"] == probe_builder.SCENARIO_NUMBER
        and evidence["rom"]["sha256"] == PROBES[profile]["sha256"]
        and evidence["rom"]["md_checksum"] == PROBES[profile]["checksum"]
        and sha256_path(evidence_path) == definition["evidence_sha256"]
        and identity["status"] == "pass"
        and identity["requested_scenario"]
        == identity["identified_scenario"]
        == probe_builder.SCENARIO_NUMBER
        and identity["best_match"]["matched_records"]
        == identity["best_match"]["total_records"]
        == 11
        and all(row["hash_matches"] for row in images.values())
        and all(row["dimensions"] == [320, 240] for row in images.values())
        and all(row["hash_matches"] for row in gsts.values())
        and hostile_state_valid
        and evidence["battle_result_frame"] == 36
        and evidence["save_menu_frame"] == 3
        and images["battle_result"]["surface"] == "battle_result"
        and images["save_menu"]["surface"] == "save_menu"
    )
    return {
        "status": "pass" if passed else "fail",
        "run_root": relative(root),
        "evidence_json": {
            "path": relative(evidence_path),
            "sha256": sha256_path(evidence_path),
            "expected_sha256": definition["evidence_sha256"],
            "hash_matches": sha256_path(evidence_path)
            == definition["evidence_sha256"],
        },
        "scenario_identity": identity,
        "images": images,
        "gsts": gsts,
        "runtime_clear_state": clear_state,
        "hostile_state_valid": hostile_state_valid,
        "battle_result_frame": evidence["battle_result_frame"],
        "save_menu_frame": evidence["save_menu_frame"],
        "manual_review": {
            "status": "pass",
            "reviewed_aftermath_frames": 36,
            "dialogue_names": [
                "리빙아머",
                "서큐버스",
                "리치",
                "크라켄",
                "제국군지휘관",
                "헤인",
                "엘윈",
                "제시카",
                "쉐리",
                "아론",
                "키스",
                "레스터",
                "스코트",
            ],
            "battle_result_text": [
                "전과보고",
                "아군",
                "엘윈",
                "헤인",
                "쉐리",
                "아론",
                "키스",
                "레스터",
                "제시카",
                "스코트",
                "POINT 31100P",
            ],
            "clarification": (
                "the first left-column label is the faction heading 아군, "
                "not a duplicate 아론 commander row"
            ),
            "class_change_text": ["클래스체인지 가능", "로드", "호크나이트"],
            "save_text": ["저장", "다음 시나리오"],
            "broken_dynamic_glyphs_or_sprites": False,
        },
    }


def aftermath_hashes(profile: str) -> list[str]:
    root = RUNS[profile]["root"] / "aftermath"
    return [
        sha256_path(root / f"advance_{frame:03d}.png")
        for frame in range(1, 37)
    ]


def build_report() -> dict[str, object]:
    profiles = {}
    for profile in ("normal", "hard"):
        lineage = lineage_report(profile)
        runtime = runtime_report(profile)
        passed = (
            lineage["candidate_identity_matches"]
            and lineage["probe_identity_matches"]
            and lineage["candidate"]["checksum_valid"]
            and lineage["probe"]["checksum_valid"]
            and lineage["exact_rebuild"]
            and lineage["wrapper_exact"]
            and lineage["start_entry_targets_wrapper"]
            and lineage["fixed_records_input_exact"]
            and lineage["normal_fixed_records_source_exact"]
            and lineage["player_deployments_input_exact"]
            and lineage["normal_player_deployments_source_exact"]
            and runtime["status"] == "pass"
        )
        profiles[profile] = {
            "status": "pass" if passed else "fail",
            "diagnostic_lineage": lineage,
            "runtime": runtime,
        }

    normal_aftermath = aftermath_hashes("normal")
    hard_aftermath = aftermath_hashes("hard")
    cross_profile = {
        "preparation_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["preparation"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["preparation"]["sha256"]
        ),
        "turn1_command_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["turn1_command"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["turn1_command"]["sha256"]
        ),
        "runtime_clear_start_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["runtime_clear_start"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["runtime_clear_start"]["sha256"]
        ),
        "aftermath_frames_1_through_35_pixel_identical": (
            normal_aftermath[:35] == hard_aftermath[:35]
        ),
        "save_menu_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["save_menu"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["save_menu"]["sha256"]
        ),
        "result_manual_content_identical": True,
        "result_frames_have_different_animation_phase": (
            normal_aftermath[35] != hard_aftermath[35]
        ),
    }
    rejected_attempts = [
        {
            "attempt": "historical s21_completion_8a18_fresh GST",
            "result": "current-ROM load black-wiped and crashed",
            "classification": "rejected cross-build savestate continuation",
        },
        {
            "attempt": "Japanese runtime-clear preparation automation",
            "result": "Korean-specific preparation cursor detector did not identify the Japanese surface",
            "classification": "rejected detector mismatch; no Japanese result claim",
        },
        {
            "attempt": "result roster first-row duplicate suspicion",
            "result": "manual zoom and comparison identify the row as the faction heading 아군, followed by the real 아론 row",
            "classification": "resolved as correct UI, not a defect",
        },
    ]
    passed = (
        all(row["status"] == "pass" for row in profiles.values())
        and all(cross_profile.values())
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": (
            "Fresh current normal/hard Scenario 21 preparation, source-preserving "
            "runtime completion, all aftermath frames, battle result, and save menu"
        ),
        "release_promoted": False,
        "acceptance_updated": False,
        "profiles": profiles,
        "cross_profile": cross_profile,
        "rejected_attempts": rejected_attempts,
        "savestate_policy": (
            "These GSTs are isolated verification fixtures. Player migration "
            "continues through in-game SRM load and then a fresh savestate."
        ),
    }


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
            raise ValueError(f"stale Scenario 21 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 21 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
