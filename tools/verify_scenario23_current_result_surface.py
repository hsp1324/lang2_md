#!/usr/bin/env python3
"""Verify fresh current normal/hard Scenario 23 result-surface evidence."""

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
from tools import build_scenario23_clear_probe_rom as probe_builder
from tools import run_scenario23_result_surface as runner
from tools import verify_scenario22_current_result_surface as shared


DEFAULT_OUTPUT = ROOT / "localization/scenario23_current_result_surface_regression.json"
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
        "path": ROOT / "tmp/current-result-probes/normal/s23-runtime-clear.md",
        "sha256": "2fddd78d8ecc366ca8909aa8ced6d495c4b0b649fc5a157d57dc9e1f5a089032",
        "checksum": "5812",
    },
    "hard": {
        "path": ROOT / "tmp/current-result-probes/hard/s23-runtime-clear.md",
        "sha256": "2c64319555ccff6b1d9b77ff0cfa18e73e54ad99406426f6cd2eed0e43cbbe50",
        "checksum": "6E1D",
    },
}
RUNS = {
    "normal": {
        "root": ROOT / "captures/run/current_s23_result/normal/runtime01",
        "evidence_sha256": "6f18ffa7751dfd29c7bdca8ae4fb6bb81f8d031cff50d34ccc6e2b7197b33a01",
        "aftermath_digest": "c27115a509bb91c12ad58e7547ea9bbd6989fbc58f69deeccac9dbd176ebab5f",
        "aftermath_bytes": 510070,
        "save_menu_frame": 3,
        "images": {
            "preparation": (
                "preparation.png",
                "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437",
            ),
            "turn1_command": (
                "battle/turn1_command.png",
                "a08a834e6c070dfec1edb9b803486d597a3a23b28a90f3b68a8fbd339c2334af",
            ),
            "runtime_clear_start": (
                "battle/runtime_clear_start_menu.png",
                "4157554bb8976f1aaa956d61e0c2147843d9cf4b1db424ca5113866e09014ca4",
            ),
            "battle_result": (
                "aftermath/battle_result.png",
                "752e417983a9bbe33d8d103f9c66f80a3471858087c98731ae5c96d04ebb8768",
            ),
            "save_menu": (
                "save/save_menu.png",
                "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c",
            ),
        },
        "gsts": {
            "before_runtime_clear": (
                "states/before_runtime_clear.gst",
                "3b3c7944f796c66826cc8f4408919024e14189a6b3d7ab6975535eda41fbd2c9",
            ),
            "runtime_clear_start": (
                "states/runtime_clear_start_menu.gst",
                "f5ebdca08848f63b43f488e6d3f85ff0ddaf71d0e989d01978c069674504649c",
            ),
            "battle_result": (
                "states/battle_result.gst",
                "a44dccc972486f763ad8f64e5ed015d9f8ea4c1e8ac7056ac7f522ab8ae29889",
            ),
            "save_menu": (
                "states/save_menu.gst",
                "e4fae47ee5e7d481ba7a341201ff083d7b8eb6b3540b41726ac35f81834949c5",
            ),
        },
    },
    "hard": {
        "root": ROOT / "captures/run/current_s23_result/hard/runtime01",
        "evidence_sha256": "69de309412f0780e9c6267bb07a2dfd3b4bfee96ea1e45b00dd32ad32888a1a4",
        "aftermath_digest": "b5b62b4afa1c434be096c3164c1360eb0d789ca1356363ed3b0ded9fce52825b",
        "aftermath_bytes": 510188,
        "save_menu_frame": 3,
        "images": {
            "preparation": (
                "preparation.png",
                "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437",
            ),
            "turn1_command": (
                "battle/turn1_command.png",
                "a08a834e6c070dfec1edb9b803486d597a3a23b28a90f3b68a8fbd339c2334af",
            ),
            "runtime_clear_start": (
                "battle/runtime_clear_start_menu.png",
                "4157554bb8976f1aaa956d61e0c2147843d9cf4b1db424ca5113866e09014ca4",
            ),
            "battle_result": (
                "aftermath/battle_result.png",
                "ebc2a179c7be44dc1c43db1560b160e5b9881ddf08cb06ad546a74a982a076b0",
            ),
            "save_menu": (
                "save/save_menu.png",
                "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c",
            ),
        },
        "gsts": {
            "before_runtime_clear": (
                "states/before_runtime_clear.gst",
                "3536ad3c957fbfac8eaa1d593e53a2b78dd8c33f9cb4b35fe6f6e3286aabe2d2",
            ),
            "runtime_clear_start": (
                "states/runtime_clear_start_menu.gst",
                "a298198ce72e286b74919acb04a64f33bdccdf454661218e26387d3ae518288d",
            ),
            "battle_result": (
                "states/battle_result.gst",
                "3e50da19687d5a60c7ec8bc6a2de87e3d551566e6ad3799c746b38d215507534",
            ),
            "save_menu": (
                "states/save_menu.gst",
                "8370e99bd5abf43a1ddc18c8bdcfd863572429a22567ef006e44665886d2550a",
            ),
        },
    },
}
AFTERMATH_FRAMES = 47
EXPECTED_CROSS_PROFILE_DIFFERENCES = [31, 38, 40, 43, 47]


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
    candidate_report = shared.rom_report(CANDIDATES[profile]["path"])
    probe_report = shared.rom_report(PROBES[profile]["path"])
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
        "wrapper_exact": probe[
            probe_builder.COMPLETION_HP_WRAPPER:
            probe_builder.COMPLETION_HP_WRAPPER + len(wrapper)
        ] == wrapper,
        "start_entry_targets_wrapper": probe[
            probe_builder.START_MENU_ENTRY_OPERAND:
            probe_builder.START_MENU_ENTRY_OPERAND + 4
        ] == probe_builder.COMPLETION_HP_WRAPPER.to_bytes(4, "big"),
        "fixed_records_input_exact": (
            probe[fixed_start:fixed_end] == candidate[fixed_start:fixed_end]
        ),
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
            "diagnostic only: Start marks hostile runtime groups 9..19 "
            "defeated; all fixed records, deployments, events, identities, "
            "and combat values remain byte-identical to the input candidate"
        ),
    }


def aftermath_report(profile: str) -> dict[str, object]:
    definition = RUNS[profile]
    root = definition["root"] / "aftermath"
    paths = [
        root / f"advance_{frame:03d}.png"
        for frame in range(1, AFTERMATH_FRAMES + 1)
    ]
    hashes = [shared.sha256_path(path) for path in paths]
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
        key: shared.image_report(root, value)
        for key, value in definition["images"].items()
    }
    gsts = {
        key: shared.gst_report(root, value)
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
        clear_state["player_groups_untouched_by_wrapper"]
        and clear_state["hostile_groups_defeated"]
        and all(
            groups[str(group)]["defeated_flag"] & 0x80
            and groups[str(group)]["hp"] == 0
            and groups[str(group)]["x"] == 0xFF
            for group in probe_builder.RUNTIME_CLEAR_GROUPS
        )
    )
    passed = (
        evidence["status"] == "pass"
        and evidence["profile"] == profile
        and evidence["scenario"] == probe_builder.SCENARIO_NUMBER
        and evidence["rom"]["sha256"] == PROBES[profile]["sha256"]
        and evidence["rom"]["md_checksum"] == PROBES[profile]["checksum"]
        and shared.sha256_path(evidence_path) == definition["evidence_sha256"]
        and identity["status"] == "pass"
        and identity["requested_scenario"]
        == identity["identified_scenario"]
        == probe_builder.SCENARIO_NUMBER
        and identity["best_match"]["matched_records"] == 11
        and identity["best_match"]["total_records"] == 11
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
        "run_root": shared.relative(root),
        "evidence_json": {
            "path": shared.relative(evidence_path),
            "sha256": shared.sha256_path(evidence_path),
            "expected_sha256": definition["evidence_sha256"],
            "hash_matches": shared.sha256_path(evidence_path)
            == definition["evidence_sha256"],
        },
        "scenario_identity": identity,
        "identity_note": "all 11 fixed enemy records match at runtime",
        "images": images,
        "gsts": gsts,
        "aftermath": aftermath,
        "runtime_clear_state": clear_state,
        "combat_state_valid": combat_state_valid,
        "battle_result_frame": evidence["battle_result_frame"],
        "save_menu_frame": evidence["save_menu_frame"],
        "manual_review": {
            "status": "pass",
            "reviewed_normal_aftermath_frames": AFTERMATH_FRAMES,
            "reviewed_hard_differing_frames": len(EXPECTED_CROSS_PROFILE_DIFFERENCES),
            "dialogue_and_level_names": [
                "레아드", "제국군지휘관", "엘윈", "일반병", "헤인",
                "리아나", "쉐리", "아론", "레스터", "스코트",
            ],
            "acquisition_text": ["성스러운 지팡이 획득!"],
            "battle_result_text": [
                "전과보고", "아군", "엘윈", "헤인", "쉐리", "아론",
                "키스", "레스터", "스코트", "리아나", "라나",
                "POINT 3400P",
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
            "map/result animation and capture phase only; no name, class, "
            "mercenary, commander, portrait, map-sprite, or UI glyph corruption"
        ),
        "save_menu_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["save_menu"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["save_menu"]["sha256"]
        ),
        "result_manual_content_identical": True,
    }
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
            "Fresh current normal/hard Scenario 23 preparation, source-preserving "
            "runtime completion, all 47 aftermath frames, result, and save menu"
        ),
        "release_promoted": False,
        "acceptance_updated": False,
        "profiles": profiles,
        "cross_profile": cross_profile,
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
            raise ValueError(f"stale Scenario 23 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 23 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
