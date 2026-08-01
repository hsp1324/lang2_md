#!/usr/bin/env python3
"""Verify fresh current normal/hard Scenario 22 result-surface evidence."""

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
from tools import build_scenario22_clear_probe_rom as probe_builder
from tools import run_scenario14_15_result_surface as surface_classifier
from tools import run_scenario22_result_surface as runner


DEFAULT_OUTPUT = ROOT / "localization/scenario22_current_result_surface_regression.json"
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
        "path": ROOT / "tmp/current-result-probes/normal/s22-runtime-clear.md",
        "sha256": "2fddd78d8ecc366ca8909aa8ced6d495c4b0b649fc5a157d57dc9e1f5a089032",
        "checksum": "5812",
    },
    "hard": {
        "path": ROOT / "tmp/current-result-probes/hard/s22-runtime-clear.md",
        "sha256": "2c64319555ccff6b1d9b77ff0cfa18e73e54ad99406426f6cd2eed0e43cbbe50",
        "checksum": "6E1D",
    },
}
RUNS = {
    "normal": {
        "root": ROOT / "captures/run/current_s22_result/normal/runtime02",
        "evidence_sha256": "39b882cb67f02d003c4a91acaf0ae9ea03d6037da04ddc05ad409f1d278b9788",
        "aftermath_digest": "2a751baa67402cab662468cdffe60e8c38c5e4578ce8d2a12d1c4fdc7d5ed15b",
        "aftermath_bytes": 2883406,
        "save_menu_frame": 3,
        "images": {
            "preparation": (
                "preparation.png",
                "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437",
            ),
            "turn1_command": (
                "battle/turn1_command.png",
                "b6babd6c9066308fe27d917cc4c3162a2fb956094169160763631e07a29bee0f",
            ),
            "runtime_clear_start": (
                "battle/runtime_clear_start_menu.png",
                "1709e88fcfe3734849936927e053da65619abfffb051757b8c5ccec2225bd3d8",
            ),
            "battle_result": (
                "aftermath/battle_result.png",
                "a52a25ff38028df9d272ad1eff0b2f45d2f3f11a7ba2384c29174e5a9300620e",
            ),
            "save_menu": (
                "save/save_menu.png",
                "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c",
            ),
        },
        "gsts": {
            "before_runtime_clear": (
                "states/before_runtime_clear.gst",
                "2f29c6e425a0c50e4e867789ffd7d9c66e5f010a79d33c9114dcb44abd2a38a3",
            ),
            "runtime_clear_start": (
                "states/runtime_clear_start_menu.gst",
                "8f2af91d59ab0eb73347cd888e79613b36f83a492c07349127a217a9a61a347d",
            ),
            "battle_result": (
                "states/battle_result.gst",
                "12aeb0ff985e29ae24806fe7501164431b7b96c78b33f2730acd019c183d92ff",
            ),
            "save_menu": (
                "states/save_menu.gst",
                "63a5cc1c4a7aa41523af6f4abfaa6c5dec0c6783b5a32cdc6c3f7b8bed6ac686",
            ),
        },
    },
    "hard": {
        "root": ROOT / "captures/run/current_s22_result/hard/runtime01",
        "evidence_sha256": "6e41e0bccec9708999dc1e70f7bce25dee12ada6f68f526b26f57f6e0a37e3e7",
        "aftermath_digest": "c947621ff726a09cf0c0ee804d63d1d5b3efc08a0edd367ea3cbd154388c0b50",
        "aftermath_bytes": 2884895,
        "save_menu_frame": 2,
        "images": {
            "preparation": (
                "preparation.png",
                "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437",
            ),
            "turn1_command": (
                "battle/turn1_command.png",
                "b6babd6c9066308fe27d917cc4c3162a2fb956094169160763631e07a29bee0f",
            ),
            "runtime_clear_start": (
                "battle/runtime_clear_start_menu.png",
                "1709e88fcfe3734849936927e053da65619abfffb051757b8c5ccec2225bd3d8",
            ),
            "battle_result": (
                "aftermath/battle_result.png",
                "1f5a01060b15ad4e6f3d7e27658dfaef7e01c5581fd883d413ec432a40f7f604",
            ),
            "save_menu": (
                "save/save_menu.png",
                "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c",
            ),
        },
        "gsts": {
            "before_runtime_clear": (
                "states/before_runtime_clear.gst",
                "fa5566733d57ab3a805cefa93d2f7a9ec291e70b0c3457192add0452386f6f0f",
            ),
            "runtime_clear_start": (
                "states/runtime_clear_start_menu.gst",
                "10e50acb43d72e70432c4a2197414bd14099beee21e632828189a1f3356b9b79",
            ),
            "battle_result": (
                "states/battle_result.gst",
                "d8cea085b274a912ac6b178ddf9ab0d5bec1170409c4af52159595fea20a959a",
            ),
            "save_menu": (
                "states/save_menu.gst",
                "ad9de6b08416781bbe6106765d31f14e6dd2d9f3e10d2ab6c1547459f2de8b63",
            ),
        },
    },
}
AFTERMATH_FRAMES = 167
EXPECTED_CROSS_PROFILE_DIFFERENCES = [
    7, 14, 33, 42, 43, 44, 47, 75, 77, 79, 81, 91, 92, 99, 123,
    124, 127, 137, 140, 147, 148, 152, 167,
]


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
        for offset, (before, after) in enumerate(zip(normal_candidate, rebuilt_normal))
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
    layout = probe_builder.scenario_layout(source, probe_builder.SCENARIO_NUMBER)
    fixed_start = layout.records_offset
    fixed_end = fixed_start + layout.record_count * probe_builder.FIXED_RECORD_SIZE
    deployment_start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
    deployment_end = deployment_start + len(
        probe_builder.deployment_bytes(probe_builder.SOURCE_PLAYER_DEPLOYMENTS)
    )
    return {
        "method": method,
        "candidate": candidate_report,
        "candidate_identity_matches": (
            candidate_report["sha256"] == CANDIDATES[profile]["sha256"]
            and candidate_report["header_checksum"] == CANDIDATES[profile]["checksum"]
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
            ] == wrapper
        ),
        "start_entry_targets_wrapper": (
            probe[
                probe_builder.START_MENU_ENTRY_OPERAND:
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ] == probe_builder.COMPLETION_HP_WRAPPER.to_bytes(4, "big")
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
            "diagnostic only: Start marks combat runtime groups 9..19 "
            "defeated; all fixed records, deployments, events, identities, "
            "and combat values remain byte-identical to the input candidate"
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


def aftermath_report(profile: str) -> dict[str, object]:
    definition = RUNS[profile]
    root = definition["root"] / "aftermath"
    paths = [root / f"advance_{frame:03d}.png" for frame in range(1, AFTERMATH_FRAMES + 1)]
    hashes = [sha256_path(path) for path in paths]
    digest = hashlib.sha256(("\n".join(hashes) + "\n").encode()).hexdigest()
    dimensions = []
    for path in paths:
        with Image.open(path) as source:
            dimensions.append([source.width, source.height])
    total_bytes = sum(path.stat().st_size for path in paths)
    return {
        "frame_count": len(paths),
        "sequence_sha256": digest,
        "expected_sequence_sha256": definition["aftermath_digest"],
        "sequence_hash_matches": digest == definition["aftermath_digest"],
        "total_bytes": total_bytes,
        "expected_total_bytes": definition["aftermath_bytes"],
        "total_bytes_match": total_bytes == definition["aftermath_bytes"],
        "unique_frame_hashes": len(set(hashes)),
        "all_dimensions_320x240": all(row == [320, 240] for row in dimensions),
        "hashes": hashes,
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
        root / definition["gsts"]["runtime_clear_start"][0],
        root / definition["gsts"]["before_runtime_clear"][0],
    )
    aftermath = aftermath_report(profile)
    identity = evidence["scenario_identity"]
    groups = clear_state["groups"]
    combat_state_valid = (
        clear_state["combat_groups_defeated"]
        and clear_state["liana_untouched_by_wrapper"]
        and clear_state["liana_runtime_identity_valid"]
        and all(
            groups[str(group)]["defeated_flag"] & 0x80
            and groups[str(group)]["hp"] == 0
            and groups[str(group)]["x"] == 0xFF
            for group in probe_builder.RUNTIME_CLEAR_GROUPS
        )
        and groups[str(runner.LIANA_RUNTIME_GROUP)] == {
            "class_id": 0x02,
            "name_id": 0x02,
            "defeated_flag": 0,
            "hp": 10,
            "x": 14,
            "y": 4,
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
        and identity["best_match"]["matched_records"] == 11
        and identity["best_match"]["total_records"] == 12
        and all(row["hash_matches"] for row in images.values())
        and all(row["dimensions"] == [320, 240] for row in images.values())
        and all(row["hash_matches"] for row in gsts.values())
        and combat_state_valid
        and aftermath["sequence_hash_matches"]
        and aftermath["total_bytes_match"]
        and aftermath["all_dimensions_320x240"]
        and evidence["battle_result_frame"] == AFTERMATH_FRAMES
        and evidence["save_menu_frame"] == definition["save_menu_frame"]
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
        "identity_note": (
            "11/12 runtime records match because source class 97 for allied "
            "Liana is normalized to playable runtime Cleric class 02"
        ),
        "images": images,
        "gsts": gsts,
        "aftermath": aftermath,
        "runtime_clear_state": clear_state,
        "combat_state_valid": combat_state_valid,
        "battle_result_frame": evidence["battle_result_frame"],
        "save_menu_frame": evidence["save_menu_frame"],
        "manual_review": {
            "status": "pass",
            "reviewed_normal_aftermath_frames": 167,
            "reviewed_hard_differing_frames": 23,
            "dialogue_names": [
                "보젤", "라나", "베른하르트", "제국군지휘관", "리치",
                "아이언골렘", "제시카", "쉐리", "레스터", "헤인",
                "엘윈", "리아나", "아론", "스코트",
            ],
            "battle_result_text": [
                "전과보고", "아군", "엘윈", "헤인", "쉐리", "아론",
                "키스", "레스터", "제시카", "스코트", "POINT 4480P",
            ],
            "class_change_text": [
                "클래스체인지 가능", "서먼", "힐러", "로드", "메이지",
                "매직나이트", "프리스트", "아크메이지", "엘프나이트",
                "팔라딘", "호크나이트", "샤먼",
            ],
            "save_text": ["저장", "다음 시나리오"],
            "broken_dynamic_glyphs_or_sprites": False,
        },
    }


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

    normal_hashes = profiles["normal"]["runtime"]["aftermath"]["hashes"]
    hard_hashes = profiles["hard"]["runtime"]["aftermath"]["hashes"]
    differing = [
        frame
        for frame, (normal, hard) in enumerate(zip(normal_hashes, hard_hashes), 1)
        if normal != hard
    ]
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
        "aftermath_pixel_identical_frames": AFTERMATH_FRAMES - len(differing),
        "aftermath_differing_frames": differing,
        "aftermath_differences_match_reviewed_set": (
            differing == EXPECTED_CROSS_PROFILE_DIFFERENCES
        ),
        "differing_frames_manual_classification": (
            "animation/capture phase and hard-profile numeric differences; "
            "no name, class, mercenary, commander, or UI glyph corruption"
        ),
        "save_menu_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["save_menu"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["save_menu"]["sha256"]
        ),
        "result_manual_content_identical": True,
    }
    rejected_attempts = [
        {
            "attempt": "normal/runtime01 Liana assertion",
            "result": (
                "wrapper correctly preserved Liana, but the verifier expected "
                "source class 97 instead of normalized runtime Cleric class 02"
            ),
            "classification": (
                "rejected over-strict verifier; runtime02 compares the complete "
                "allied record before and after Start"
            ),
        },
    ]
    passed = (
        all(row["status"] == "pass" for row in profiles.values())
        and cross_profile["preparation_pixel_identical"]
        and cross_profile["turn1_command_pixel_identical"]
        and cross_profile["runtime_clear_start_pixel_identical"]
        and cross_profile["aftermath_differences_match_reviewed_set"]
        and cross_profile["save_menu_pixel_identical"]
        and cross_profile["result_manual_content_identical"]
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": (
            "Fresh current normal/hard Scenario 22 preparation, source-preserving "
            "runtime completion, all 167 aftermath frames, result, and save menu"
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
            raise ValueError(f"stale Scenario 22 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 22 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
