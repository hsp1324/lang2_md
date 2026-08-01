#!/usr/bin/env python3
"""Verify current normal/hard Scenario 12 completion-result evidence."""

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
from tools import build_scenario12_clear_probe_rom as probe_builder
from tools import run_scenario14_15_result_surface as surface_classifier


DEFAULT_OUTPUT = (
    ROOT / "localization/scenario12_current_result_surface_regression.json"
)
SOURCE_ROM = probe_builder.DEFAULT_SOURCE_ROM
SOURCE_STATE = (
    ROOT
    / "captures/runtime/s12-load-old-40bc/.local/share/blastem/"
    "Langrisser II (Scenario 12 Compact Clear Probe)/quicksave.gst"
)
EXPECTED_SOURCE_STATE_SHA256 = (
    "ac2958e056561b4c8345805b351f5b45ac55453c8e89db94ba787317d7588878"
)
EVENT_BLOCK = (0x198DE0, 0x19A964)
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
        "probe": ROOT / "tmp/current-result-probes/normal/s12.md",
        "probe_sha256": (
            "f8748183072e750d3827e7531477cc2fd1eca55e8a7cc2fb1847d5e6e25ba239"
        ),
        "probe_checksum": "15CA",
        "root": ROOT / "captures/run/current_s12_result/normal",
        "frame_prefix": "s12_current_",
        "target_evidence": {
            "hp10_target": {
                "file": "target_hp10.png",
                "sha256": (
                    "d36b4da487239fc19ce10864f5b518be6ec291eb28bd424f5ab292211d9e6aba"
                ),
                "observed": ["리빙아머", "HP10"],
            },
            "ordinary_attack_hp9": {
                "file": "target_hp9.png",
                "sha256": (
                    "53101d527a8a457c3b743d4efef5265b30126755cf20bda3a19f7c7ae6dc886b"
                ),
                "observed": ["쉐리", "리빙아머", "HP9"],
            },
            "defeat_dialogue_hp0": {
                "file": "target_hp0_dialogue.png",
                "sha256": (
                    "dd9214f470106ab3f90614982fb088563c5fb51d50751b504e15b94f59944405"
                ),
                "observed": ["리빙아머", "HP0", "……"],
            },
        },
        "title_sha256": (
            "66c740defa9e7235c00ba75ac982bd180b77b26c74be7356a2c60c395f16d9de"
        ),
    },
    "hard": {
        "probe": ROOT / "tmp/current-result-probes/hard/s12.md",
        "probe_sha256": (
            "7d51d06a78f438531db880c7f0e8b3a13b48dbe0a632e01250cd447c46bd571d"
        ),
        "probe_checksum": "02C2",
        "root": ROOT / "captures/run/current_s12_result/hard",
        "frame_prefix": "s12_after_second_",
        "target_evidence": {
            "first_attack_hp1": {
                "file": "first_attack_hp1_dialogue.png",
                "sha256": (
                    "2a6643947fbc72ef998454e97c4e609697b7cc1dd353f0ad03ce59f492a23cad"
                ),
                "observed": ["리빙아머", "HP1", "first ordinary attack"],
            },
            "second_attack_hp0": {
                "file": "second_attack_hp0_dialogue.png",
                "sha256": (
                    "c3059f51680a1869ae60c4138c8b4418906bd121ab8f45926b519e692f81a341"
                ),
                "observed": ["리빙아머", "HP0", "second ordinary attack"],
            },
        },
        "title_sha256": (
            "08f9b05ee774f858eaeeee7ed0704eb9d27759986cf199128b4e2ca7ef822f69"
        ),
    },
}
CRITICAL_SURFACES = {
    "elwin_clear": {
        "frame": 2,
        "sha256": "5d96f3a143d2cd50cc6b03a335c6153f093bd5179f3a5e13c284dd7770b70f5f",
        "observed": ["엘윈", "모두 쓰러뜨린 것 같군…"],
    },
    "jessica_apology": {
        "frame": 8,
        "sha256": "84f1568057a4b4486f99fd6d519a11a2f0b130bb4f0ead33bb5268f3c197381a",
        "observed": ["제시카", "미안해…"],
    },
    "aaron_reply": {
        "frame": 10,
        "sha256": "3be9dfc469e4af68a5c175fb0e53a38f949b37e369aba136580ef8a8a13c9167",
        "observed": ["아론", "그도 자기 생각으로 행동한 한 사람입니다."],
    },
    "jessica_to_hein": {
        "frame": 16,
        "sha256": "f99791e8f93cfc0cf5eb95638fe26b4fb5469d2469670862377ace3b68a3fcf2",
        "observed": ["제시카", "헤인… 내 제자가 되고 싶다고 했지?"],
    },
    "hein_liana": {
        "frame": 20,
        "sha256": "a56e6da234db90ea7f6c78a9e07d78c0c01dae2437ff3b41f3f9e54b0df2c7da",
        "observed": ["헤인", "리아나가 납치됐다면"],
    },
    "hein_level": {
        "frame": 22,
        "sha256": "5554ef78b54d9aac9911c0c1634e1831a7dd445489e79de9e55a8708f8e9f512",
        "observed": ["헤인의", "레벨이 올랐다!", "MP가 1 상승"],
    },
}
RESULT_SHA256 = (
    "da64f42f01cf3360813a24e7ed55dff6c166d7f8fdf6af44843921127972cb1b"
)
SAVE_SHA256 = (
    "cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a"
)
NEXT_SHA256 = (
    "342ced51ec1d1d8b915cc5a55b5235173303dc4fa48b23280c86918e42aa3742"
)
ROUTE_SHA256 = (
    "ee4e666dc175da14d6eb9f0a6eb3bfdd042af3372a42f8377c237935f3be7287"
)


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
        probe_builder.patch_probe(expected, source, compact_layout=True)
        exact_key = "exact_builder_rebuild"
        conflicts = 0
        method = "exact Scenario 12 compact clear-probe builder replay"
    else:
        delta = diagnostic_delta()
        normal_probe = PROFILES["normal"]["probe"].read_bytes()
        normal_candidate = EXPECTED_CANDIDATES["normal"]["path"].read_bytes()
        expected = bytearray(candidate)
        for index in delta - {0x18E, 0x18F}:
            expected[index] = normal_probe[index]
        md_builder.update_md_checksum(expected)
        exact_key = "exact_three_way_overlay"
        conflicts = sum(
            normal_candidate[index] != candidate[index]
            for index in delta - {0x18E, 0x18F}
        )
        method = (
            "apply the exact normal compact diagnostic delta to the hard "
            "candidate, then recalculate only the Mega Drive checksum"
        )
    candidate_report = rom_report(candidate_path)
    probe_report = rom_report(probe_path)
    event_start, event_end = EVENT_BLOCK
    return {
        "method": method,
        "candidate": candidate_report,
        "candidate_identity_matches": (
            candidate_report["sha256"]
            == EXPECTED_CANDIDATES[profile]["sha256"]
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
    }


def reviewed_image(
    path: Path,
    *,
    expected_sha256: str,
    observed: list[str],
) -> dict[str, object]:
    report = image_report(path)
    return {
        **report,
        "expected_reviewed_sha256": expected_sha256,
        "reviewed_hash_matches": report["sha256"] == expected_sha256,
        "manual_review": "pass",
        "observed_text": observed,
        "observed_sprite_state": "clean",
    }


def runtime_report(profile: str) -> dict[str, object]:
    definition = PROFILES[profile]
    root = definition["root"]
    prefix = definition["frame_prefix"]
    sequence = [image_report(root / f"{prefix}{frame:02d}.png") for frame in range(1, 28)]
    critical = {
        key: reviewed_image(
            root / f"{prefix}{row['frame']:02d}.png",
            expected_sha256=row["sha256"],
            observed=row["observed"],
        )
        for key, row in CRITICAL_SURFACES.items()
    }
    targets = {
        key: reviewed_image(
            root / row["file"],
            expected_sha256=row["sha256"],
            observed=row["observed"],
        )
        for key, row in definition["target_evidence"].items()
    }
    result = reviewed_image(
        root / f"{prefix}26.png",
        expected_sha256=RESULT_SHA256,
        observed=[
            "전과보고",
            "아론",
            "엘윈",
            "헤인",
            "쉐리",
            "키스",
            "레스터",
            "제시카",
            "POINT 4920P",
        ],
    )
    save = reviewed_image(
        root / f"{prefix}27.png",
        expected_sha256=SAVE_SHA256,
        observed=["저장", "데이터 없음", "다음 시나리오"],
    )
    next_selected = reviewed_image(
        root / "next_selected.png",
        expected_sha256=NEXT_SHA256,
        observed=["시나리오 13", "다음 시나리오"],
    )
    route = reviewed_image(
        root / "route.png",
        expected_sha256=ROUTE_SHA256,
        observed=["진군루트"],
    )
    title = reviewed_image(
        root / "scenario13_title.png",
        expected_sha256=definition["title_sha256"],
        observed=["시나리오 13", "염룡병단과의 결전"],
    )
    return {
        "sequence": {
            "frame_count": len(sequence),
            "all_dimensions_320x240": all(
                row["dimensions"] == [320, 240] for row in sequence
            ),
            "captures": sequence,
        },
        "last_living_armor": targets,
        "critical_surfaces": critical,
        "battle_result": result,
        "save_menu": save,
        "next_scenario_selected": next_selected,
        "scenario13_route": route,
        "scenario13_title": title,
        "scope_limit": (
            "the untouched historical work RAM is used only to continue the "
            "final ordinary battle into the current ROM's aftermath, result, "
            "save, route, and next-title renderers; it is not a fresh current "
            "deployment-to-clear replay and is not hard-mode balance evidence"
        ),
    }


def build_report() -> dict[str, object]:
    source_state_sha256 = sha256_path(SOURCE_STATE)
    source_state = {
        "path": relative(SOURCE_STATE),
        "sha256": source_state_sha256,
        "bytes": SOURCE_STATE.stat().st_size,
        "identity_matches": source_state_sha256 == EXPECTED_SOURCE_STATE_SHA256,
        "method": (
            "historical Scenario 12 battle continuation loaded without file "
            "or RAM edits; only post-final-attack current-renderer surfaces "
            "are accepted"
        ),
    }
    profiles = {}
    for profile in ("normal", "hard"):
        lineage = lineage_report(profile)
        runtime = runtime_report(profile)
        exact = (
            lineage.get("exact_builder_rebuild", False)
            if profile == "normal"
            else lineage.get("exact_three_way_overlay", False)
        )
        reviewed = [
            *runtime["last_living_armor"].values(),
            *runtime["critical_surfaces"].values(),
            runtime["battle_result"],
            runtime["save_menu"],
            runtime["next_scenario_selected"],
            runtime["scenario13_route"],
            runtime["scenario13_title"],
        ]
        profile_pass = (
            lineage["candidate_identity_matches"]
            and lineage["probe_identity_matches"]
            and lineage["candidate"]["checksum_valid"]
            and lineage["probe"]["checksum_valid"]
            and lineage["complete_event_block_preserved"]
            and exact
            and runtime["sequence"]["frame_count"] == 27
            and runtime["sequence"]["all_dimensions_320x240"]
            and runtime["battle_result"]["surface"] == "battle_result"
            and runtime["save_menu"]["surface"] == "save_menu"
            and all(row["reviewed_hash_matches"] for row in reviewed)
        )
        profiles[profile] = {
            "status": "pass" if profile_pass else "fail",
            "diagnostic_lineage": lineage,
            "runtime": runtime,
        }
    normal_result = profiles["normal"]["runtime"]["battle_result"]
    hard_result = profiles["hard"]["runtime"]["battle_result"]
    cross_profile = {
        "battle_result_frame_identical": (
            normal_result["sha256"] == hard_result["sha256"]
        ),
        "result_header_roster_and_points_identical": True,
        "manual_difference_review": "pass",
    }
    status = (
        "pass"
        if source_state["identity_matches"]
        and all(row["status"] == "pass" for row in profiles.values())
        and cross_profile["battle_result_frame_identical"]
        else "fail"
    )
    return {
        "schema_version": 1,
        "status": status,
        "scope": (
            "Current normal/hard Scenario 12 final Living Armor battle, stock "
            "aftermath, dynamic dialogue names, result roster, Scenario 13 "
            "save, route, and title"
        ),
        "release_promoted": False,
        "acceptance_updated": False,
        "source_state": source_state,
        "profiles": profiles,
        "cross_profile": cross_profile,
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
            raise ValueError(f"stale Scenario 12 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 12 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
