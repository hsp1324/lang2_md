#!/usr/bin/env python3
"""Verify current normal/hard Scenario 14/15 completion surfaces."""

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
from tools import build_scenario14_clear_probe_rom as scenario14_builder
from tools import build_scenario15_clear_probe_rom as scenario15_builder
from tools import run_scenario14_15_result_surface as runner
from tools.verify_preparation_surface_evidence import (
    EXPECTED_RESULT_HEADER_VRAM_SHA256,
    RESULT_HEADER_VRAM_BYTES,
    RESULT_HEADER_VRAM_START,
    load_gst,
    result_header_plane_cells,
)


DEFAULT_OUTPUT = (
    ROOT / "localization/scenario14_15_current_result_surface_regression.json"
)
RUNTIME_ROOT = ROOT / "captures/run/current_s14_s15_result_retry"
REJECTED_ROOT = ROOT / "captures/run/current_s14_s15_result"
RUN_ID = "stable01"
SOURCE_ROM = scenario14_builder.DEFAULT_SOURCE_ROM
EXPECTED_CANDIDATES = {
    "normal": {
        "sha256": "00f0dec38c01db6489d061476648504164b206d1ef73d57bcb9ec7b63e14d371",
        "checksum": "CB53",
    },
    "hard": {
        "sha256": "f3d5e050eb84999571c9b575f9236ef01076bbba67542e8af183bf62223bf7ad",
        "checksum": "E15E",
    },
}
SCENARIOS = {
    14: {
        "builder": scenario14_builder,
        "move": "up",
        "result_frame": 32,
        "result_sha256": "fc8ebaba0a37631e5ffa6f9543ef83402c11bdd40cbbb08a93672e0d2ec218af",
        "mismatch_frames": [6, 8, 9, 10, 11, 13, 14, 20, 21, 22, 23],
        "result_roster": [
            "전과보고",
            "아론",
            "엘윈",
            "헤인",
            "쉐리",
            "키스",
            "레스터",
            "제시카",
            "POINT",
            "2200P",
        ],
    },
    15: {
        "builder": scenario15_builder,
        "move": "down",
        "result_frame": 71,
        "result_sha256": "679bb7ea0f8ae6d6050c1cf71e2b7cdde44e4f087faecd1a1964a6e3e0baa3dc",
        "mismatch_frames": [2, 7, 10, 12, 15, 30, 39, 49, 50, 65],
        "result_roster": [
            "전과보고",
            "아론",
            "엘윈",
            "헤인",
            "쉐리",
            "키스",
            "레스터",
            "제시카",
            "스코트",
            "POINT",
            "2300P",
        ],
    },
}
CRITICAL_SURFACES = {
    14: {
        "leon_withdrawal": {
            "frame": 6,
            "observed_text": ["레온", "퇴각한다!"],
            "sha256": {
                "normal": "788d1125f68aecad2ab3696e263cf7b957307acddf7043b33e28e95da8e260fe",
                "hard": "5a7c534f907ef9908df40d7935116b6713215b86e731f208845cb893d7e71e8d",
            },
        },
        "sherry_langrisser_dialogue": {
            "frame": 14,
            "observed_text": ["쉐리", "검이 암흑검에 맞설 유일한 무기인가?"],
            "sha256": {
                "normal": "51eeb997ba2a20838b2de1b34ecdc978ca89027a2cbd04c769d163c9905b390a",
                "hard": "cbe789bbe98fece88fb0bb00cabb9ab96c08effda4dde3400fe3a6e25d98e09e",
            },
        },
        "elwin_escape_dialogue": {
            "frame": 21,
            "observed_text": ["엘윈", "무슨 일이든 일어나도 우리는 물러설 수 없다!"],
            "sha256": {
                "normal": "42e610ab34ef4178a9fa029d732277f60bac2b25820157f7fa2e036754ec368f",
                "hard": "88251ec3c5ca2eceed33585b382c54072eb630f57842b6413865af3ac7be7f51",
            },
        },
        "escape_instruction": {
            "frame": 22,
            "observed_text": ["성문 오른쪽의 가호 아래 빠져!", "리아나를 구해 내자!"],
            "sha256": {
                "normal": "c58baba0388dbcdb360e8ec40c644533517bb29e6045d0204f0e8468f773dc82",
                "hard": "245fa581b91c304570c56dd77c39418af23d58d5ab96214f9fa30489fad65346",
            },
        },
    },
    15: {
        "scott_df_level_up": {
            "frame": 39,
            "observed_text": ["스코트의", "레벨이 올랐다!", "DF가 1 상승"],
            "sha256": {
                "normal": "5ce4f43ce219ac862956166c86c6e182a109dc6e306cb7d1369f1e1dcb25b661",
                "hard": "44f7a5af3de3785f5fac7d990c71dab7224217473ce82eccb0df4190803bafb7",
            },
        },
        "scott_at_level_up": {
            "frame": 49,
            "observed_text": ["스코트의", "레벨이 올랐다!", "AT가 1 상승"],
            "sha256": {
                "normal": "f6319baeab0dde0a9e3084c4624600ce5e5f03e0ecb6161a14effbbfa75a48a2",
                "hard": "07e1d315d6309f1edf042d2914dd5656abff0c1009f7c276e5bf252796d13697",
            },
        },
        "class_change_available": {
            "frame": 65,
            "observed_text": ["클래스체인지 가능"],
            "sha256": {
                "normal": "fa14f0fea2b53501f12fc32c0b3f622684ebac0f90dc12f158f7661e11c09f54",
                "hard": "6f83957a5f37b950fcd7dc9ef0c412c9649cbf1f66ca0173380174cc123ac6d3",
            },
        },
    },
}
REJECTED_ATTEMPTS = {
    "normal_s14": REJECTED_ROOT / "normal/s14/battle/clear_path_120.png",
    "hard_s14": REJECTED_ROOT / "hard/s14/battle/clear_path_120.png",
    "normal_s15": REJECTED_ROOT / "normal/s15/battle/clear_path_120.png",
    "hard_s15_retained_result": REJECTED_ROOT / "hard/s15/battle/battle_result.png",
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
        "surface": runner.classify_surface(path),
    }


def event_blocks(builder: object) -> dict[int, bytes]:
    if builder is scenario14_builder:
        return {
            **scenario14_builder.LANGRISSER_SUCCESS_TRIGGERS,
            **scenario14_builder.LEON_LANGRISSER_TRIGGER,
        }
    return scenario15_builder.COMPLETION_TRIGGERS


def event_triggers_preserved(
    builder: object,
    candidate: bytes,
    probe: bytes,
) -> bool:
    return all(
        candidate[offset : offset + len(expected)]
        == probe[offset : offset + len(expected)]
        == expected
        for offset, expected in event_blocks(builder).items()
    )


def lineage_report(scenario: int, profile: str) -> dict[str, object]:
    builder = SCENARIOS[scenario]["builder"]
    candidate_path = ROOT / f"tmp/current-glyph-lifetime-fix-{profile}.md"
    probe_path = ROOT / f"tmp/current-result-probes/{profile}/s{scenario}.md"
    normal_candidate_path = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
    normal_probe_path = ROOT / f"tmp/current-result-probes/normal/s{scenario}.md"
    source = SOURCE_ROM.read_bytes()
    candidate = candidate_path.read_bytes()
    probe = probe_path.read_bytes()

    if profile == "normal":
        expected = bytearray(candidate)
        builder.patch_probe(expected, source, completion_layout=True)
        exact = bytes(expected) == probe
        method = f"exact Scenario {scenario} completion-layout builder replay"
        exact_key = "exact_builder_rebuild"
        conflicts = 0
        diagnostic_count = sum(
            before != after for before, after in zip(candidate, probe)
        )
    else:
        normal_candidate = normal_candidate_path.read_bytes()
        normal_probe = normal_probe_path.read_bytes()
        diagnostic_delta = {
            index
            for index, (before, after) in enumerate(
                zip(normal_candidate, normal_probe)
            )
            if before != after
        }
        expected = bytearray(candidate)
        for index in diagnostic_delta - {0x18E, 0x18F}:
            expected[index] = normal_probe[index]
        md_builder.update_md_checksum(expected)
        exact = bytes(expected) == probe
        method = (
            f"apply exact Scenario {scenario} normal diagnostic delta to the "
            "hard candidate, then recalculate only the Mega Drive checksum"
        )
        exact_key = "exact_three_way_overlay"
        conflicts = sum(
            normal_candidate[index] != candidate[index]
            for index in diagnostic_delta - {0x18E, 0x18F}
        )
        diagnostic_count = len(diagnostic_delta)

    changed = sum(before != after for before, after in zip(candidate, probe))
    candidate_report = rom_report(candidate_path)
    expected_candidate = EXPECTED_CANDIDATES[profile]
    return {
        "method": method,
        "candidate": candidate_report,
        "candidate_expected_sha256": expected_candidate["sha256"],
        "candidate_expected_checksum": expected_candidate["checksum"],
        "candidate_identity_matches": (
            candidate_report["sha256"] == expected_candidate["sha256"]
            and candidate_report["header_checksum"]
            == expected_candidate["checksum"]
        ),
        "probe": rom_report(probe_path),
        "diagnostic_changed_byte_count": diagnostic_count,
        "hard_conflicts_inside_diagnostic_envelope": conflicts,
        "actual_changed_byte_count": changed,
        exact_key: exact,
        "event_triggers_preserved": event_triggers_preserved(
            builder, candidate, probe
        ),
    }


def critical_surface_report(
    profile: str,
    scenario: int,
    root: Path,
) -> dict[str, object]:
    report = {}
    for key, row in CRITICAL_SURFACES[scenario].items():
        frame = int(row["frame"])
        capture = image_report(root / f"battle/clear_path_{frame:03d}.png")
        expected_sha = row["sha256"][profile]
        report[key] = {
            **capture,
            "frame": frame,
            "expected_reviewed_sha256": expected_sha,
            "reviewed_hash_matches": capture["sha256"] == expected_sha,
            "manual_review": "pass",
            "observed_text": row["observed_text"],
            "observed_sprite_state": "clean",
        }
    return report


def runtime_report(profile: str, scenario: int) -> dict[str, object]:
    root = RUNTIME_ROOT / profile / f"s{scenario:02d}" / RUN_ID
    evidence_path = root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    observations = []
    all_evidence_hashes_match = True
    for observation in evidence["observations"]:
        capture = image_report(ROOT / observation["capture"])
        matches = capture["sha256"] == observation["sha256"]
        all_evidence_hashes_match &= matches
        observations.append(
            {
                **capture,
                "frame": observation["frame"],
                "evidence_surface": observation["surface"],
                "evidence_hash_matches": matches,
            }
        )

    expected = SCENARIOS[scenario]
    result_path = root / "battle/battle_result.png"
    result_gst = root / "states/battle_result.gst"
    result = image_report(result_path)
    result_alias = image_report(
        root / f"battle/clear_path_{expected['result_frame']:03d}.png"
    )
    state = load_gst(result_gst)
    header = state.vram[
        RESULT_HEADER_VRAM_START :
        RESULT_HEADER_VRAM_START + RESULT_HEADER_VRAM_BYTES
    ]
    header_sha = hashlib.sha256(header).hexdigest()
    header_cells = result_header_plane_cells(state)
    critical = critical_surface_report(profile, scenario, root)
    identity = evidence["scenario_identity"]
    evidence_probe = lineage_report(scenario, profile)["probe"]
    evidence_integrity = {
        "status_pass": evidence["status"] == "pass",
        "profile_matches": evidence["profile"] == profile,
        "scenario_matches": evidence["scenario"] == scenario,
        "probe_sha256_matches": (
            evidence["rom"]["sha256"] == evidence_probe["sha256"]
        ),
        "scenario_identity_pass": (
            identity["status"] == "pass"
            and identity["requested_scenario"] == scenario
            and identity["identified_scenario"] == scenario
        ),
        "completion_move_matches": evidence["completion_move"] == expected["move"],
        "result_frame_matches": evidence["result_frame"] == expected["result_frame"],
        "all_observation_hashes_match": all_evidence_hashes_match,
    }
    return {
        "root": relative(root),
        "evidence": {
            "path": relative(evidence_path),
            "sha256": sha256_path(evidence_path),
            "integrity": evidence_integrity,
        },
        "scenario_identity": identity,
        "completion_move": evidence["completion_move"],
        "sequence": {
            "frame_count": len(observations),
            "expected_frame_count": expected["result_frame"],
            "all_dimensions_320x240": all(
                row["dimensions"] == [320, 240] for row in observations
            ),
            "all_evidence_hashes_match": all_evidence_hashes_match,
            "captures": observations,
        },
        "critical_surfaces": critical,
        "battle_result": result,
        "expected_result_sha256": expected["result_sha256"],
        "result_hash_matches": result["sha256"] == expected["result_sha256"],
        "result_alias_matches": result["sha256"] == result_alias["sha256"],
        "observed_result_roster": expected["result_roster"],
        "observed_result_sprites": "clean",
        "gst": {
            "path": relative(result_gst),
            "sha256": sha256_path(result_gst),
            "bytes": result_gst.stat().st_size,
        },
        "header_text": "전과보고",
        "header_vram_range": "0xA000..0xA1FF",
        "header_vram_sha256": header_sha,
        "header_vram_matches_expected": (
            header_sha == EXPECTED_RESULT_HEADER_VRAM_SHA256
        ),
        "header_plane_cells": header_cells,
        "all_header_plane_cells_match": all(
            row["matches"] for row in header_cells
        ),
    }


def rejected_attempt_report() -> dict[str, object]:
    captures = {
        key: image_report(path) for key, path in REJECTED_ATTEMPTS.items()
    }
    return {
        "status": "rejected",
        "reason": (
            "The first loop sent C before taking each stable capture. Three "
            "runs crossed the result screen and ended at the save menu; only "
            "hard Scenario 15 happened to retain a result frame."
        ),
        "captures": captures,
        "three_runs_ended_at_save_menu": sum(
            row["surface"] == "save_menu" for row in captures.values()
        ) == 3,
        "one_result_was_retained": sum(
            row["surface"] == "battle_result" for row in captures.values()
        ) == 1,
        "acceptance_updated": False,
    }


def build_report() -> dict[str, object]:
    profiles: dict[str, object] = {}
    for profile in ("normal", "hard"):
        scenarios = {}
        for scenario in SCENARIOS:
            lineage = lineage_report(scenario, profile)
            runtime = runtime_report(profile, scenario)
            exact_lineage = (
                lineage.get("exact_builder_rebuild", False)
                or lineage.get("exact_three_way_overlay", False)
            )
            integrity = runtime["evidence"]["integrity"]
            passed = (
                exact_lineage
                and lineage["candidate_identity_matches"]
                and lineage["candidate"]["checksum_valid"]
                and lineage["probe"]["checksum_valid"]
                and lineage["event_triggers_preserved"]
                and all(integrity.values())
                and runtime["sequence"]["frame_count"]
                == runtime["sequence"]["expected_frame_count"]
                and runtime["sequence"]["all_dimensions_320x240"]
                and runtime["sequence"]["all_evidence_hashes_match"]
                and all(
                    row["reviewed_hash_matches"]
                    and row["manual_review"] == "pass"
                    and row["observed_sprite_state"] == "clean"
                    for row in runtime["critical_surfaces"].values()
                )
                and runtime["battle_result"]["surface"] == "battle_result"
                and runtime["result_hash_matches"]
                and runtime["result_alias_matches"]
                and runtime["observed_result_sprites"] == "clean"
                and runtime["header_vram_matches_expected"]
                and runtime["all_header_plane_cells_match"]
            )
            scenarios[str(scenario)] = {
                "status": "pass" if passed else "fail",
                "diagnostic_lineage": lineage,
                "runtime": runtime,
            }
        profiles[profile] = {"scenarios": scenarios}

    cross_profile = {}
    for scenario, expected in SCENARIOS.items():
        normal = profiles["normal"]["scenarios"][str(scenario)]["runtime"]
        hard = profiles["hard"]["scenarios"][str(scenario)]["runtime"]
        mismatches = [
            frame
            for frame, (normal_row, hard_row) in enumerate(
                zip(
                    normal["sequence"]["captures"],
                    hard["sequence"]["captures"],
                ),
                start=1,
            )
            if normal_row["sha256"] != hard_row["sha256"]
        ]
        cross_profile[str(scenario)] = {
            "battle_result_frame_identical": (
                normal["battle_result"]["sha256"]
                == hard["battle_result"]["sha256"]
            ),
            "result_header_vram_identical": (
                normal["header_vram_sha256"] == hard["header_vram_sha256"]
            ),
            "observed_sequence_mismatch_frames": mismatches,
            "expected_sequence_mismatch_frames": expected["mismatch_frames"],
            "sequence_mismatches_match_review": (
                mismatches == expected["mismatch_frames"]
            ),
            "manual_mismatch_review": "pass",
            "mismatch_observation": (
                "Only selection blink, movement animation, map scroll, and "
                "normal/hard status timing differ; reviewed text, names, "
                "classes, and sprites are clean."
            ),
        }

    rejected = rejected_attempt_report()
    passed = (
        all(
            row["status"] == "pass"
            for profile in profiles.values()
            for row in profile["scenarios"].values()
        )
        and all(
            row["battle_result_frame_identical"]
            and row["result_header_vram_identical"]
            and row["sequence_mismatches_match_review"]
            and row["manual_mismatch_review"] == "pass"
            for row in cross_profile.values()
        )
        and rejected["three_runs_ended_at_save_menu"]
        and rejected["one_result_was_retained"]
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": (
            "Current normal/hard Scenario 14 and 15 stock completion paths, "
            "dynamic dialogue/status names, level-up/class-change messages, "
            "battle-result rosters, and sprites"
        ),
        "release_promoted": False,
        "acceptance_updated": False,
        "profiles": profiles,
        "cross_profile": cross_profile,
        "rejected_first_attempt": rejected,
        "limitations": [
            "The weakened-enemy completion ROMs are diagnostic-only and are never release candidates.",
            "Manual review is bound to the recorded critical and sequence capture hashes; later changes make --check fail.",
            "This result gate does not replace the already separate preparation, shop-return, minimap, and acted-sprite gates.",
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
            raise SystemExit(
                f"checked Scenario 14/15 result report is stale: {args.output}"
            )
        print(f"checked Scenario 14/15 result report is current: {args.output}")
        return 0 if report["status"] == "pass" else 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
