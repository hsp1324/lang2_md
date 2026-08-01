#!/usr/bin/env python3
"""Verify current normal/hard Scenario 17 result-surface evidence."""

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
from tools import build_scenario17_clear_probe_rom as probe_builder
from tools import run_scenario17_result_surface as runner
from tools import run_scenario14_15_result_surface as surface_classifier


DEFAULT_OUTPUT = ROOT / "localization/scenario17_current_result_surface_regression.json"
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
        "path": ROOT / "tmp/current-result-probes/normal/s17-two-hit.md",
        "sha256": "9f116adabba8ce064ae20392bdbb1c464d745849b0c75180bc1e7fa6f15bcdb7",
        "checksum": "6642",
    },
    "hard": {
        "path": ROOT / "tmp/current-result-probes/hard/s17-two-hit.md",
        "sha256": "0d5aa7d104127d70cbd6d6001c77c545f6fa24d14e914c38c25b8740210c9296",
        "checksum": "250C",
    },
}
RUNS = {
    "normal": {
        "root": ROOT / "captures/run/current_s17_result/normal/result10",
        "evidence_sha256": "7e324494fc27eb621032f31a3840d3a4b686652fa524f78fdd43290855d773fc",
        "post_start_image": "battle/post_action_start_menu.png",
        "post_start_gst": "states/post_action_start_menu.gst",
        "images": {
            "preparation": ("preparation.png", "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437"),
            "turn1_command": ("battle/turn1_command.png", "26856cb8c29a928267b0a30a4591dfda26eaebd4ac97ab8c9efe6cecbdd1d308"),
            "first_start": ("battle/first_start_menu.png", "809f5bc18eaac77c11b5b221d7d39054ac54643091c072a82c4c2f412ab95cb8"),
            "turn1_return": ("battle/turn1_return_017.png", "5529ccf96bdae746880ff205207238b433f50cb9834749ac0403fcacc6a039a5"),
            "post_start": ("battle/post_action_start_menu.png", "a7650a8cd8da6933b08b38f22a84693532206104433b3248c3a4785497776607"),
            "turn2_command": ("battle/turn2_command.png", "28ed5c9e31c093c62f2d2df92f534fa083342dd75fce1cf6d45972564142ebae"),
            "battle_result": ("battle/battle_result.png", "6d4f7edb41ff246b01e3a14857ffae9b258711b5b6b52ca5b8986399ab83ec3d"),
            "save_menu": ("save/save_menu.png", "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c"),
        },
        "gsts": {
            "first_start": ("states/first_start_menu.gst", "7ba78cd87a5afc01e29fc2e0d02da849dea9d22a328737c10e0c4365bc518735"),
            "turn1_return": ("states/turn1_return_017.gst", "a5dd71b9dc62167fe2ab532444dfb3706b979ab42c552ce4843964cf189af51c"),
            "post_start": ("states/post_action_start_menu.gst", "46016aadb953ec6d994c1d40d89d6ef68663e3320b781675f835d7b437428a91"),
            "turn2_command": ("states/turn2_command.gst", "7ae352bb49e21d60fee28e07e5a2b4d047332462daa4138ad3b21eee8d62c466"),
            "battle_result": ("states/battle_result.gst", "716998842cae1d0796aaf750ffcb4dd6c8cd9bb69d78051df107d1a98cb4eb78"),
            "save_menu": ("states/save_menu.gst", "bdae9731cd12626dec1b8b4f8a03643d8b4b24ed1e4c6683d60db6f186ff7cd0"),
        },
    },
    "hard": {
        "root": ROOT / "captures/run/current_s17_result/hard/result02",
        "evidence_sha256": "e1a0c986fc0bfd1a065bcc4e8e9ca1fc98c8eb77f2f5ac86124a633f08b74d3d",
        "post_start_image": "battle/turn1_post_action_start_menu.png",
        "post_start_gst": "states/turn1_post_action_start_menu.gst",
        "images": {
            "preparation": ("preparation.png", "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437"),
            "turn1_command": ("battle/turn1_command.png", "26856cb8c29a928267b0a30a4591dfda26eaebd4ac97ab8c9efe6cecbdd1d308"),
            "first_start": ("battle/first_start_menu.png", "809f5bc18eaac77c11b5b221d7d39054ac54643091c072a82c4c2f412ab95cb8"),
            "turn1_return": ("battle/turn1_return_017.png", "7bb0f18a0a37995f9b1d2c5295ab75f85cdf6dbc00b9b5dffe0f11a35d8366e3"),
            "post_start": ("battle/turn1_post_action_start_menu.png", "3d20195c04beb2eabe7d3547cf1c290de4af339af26b14b515b6c8e00062600d"),
            "turn2_command": ("battle/turn2_command.png", "0c74afa2ef23183817d3d48fdec15ed61360dcbc9880fde8d9504a9f93f945f7"),
            "battle_result": ("battle/battle_result.png", "2c3bd6c9e3246c554908f49c45beb3af3ec17fd76014695ca67b265b7ed8cd91"),
            "save_menu": ("save/save_menu.png", "5dbfa653b0ff475125c524957f3c5196b40c867523f011c9ae9ee86e72b5b20c"),
        },
        "gsts": {
            "first_start": ("states/first_start_menu.gst", "66643cfe37605fb125b7a08e2107c22c7a49c1676ae778a0929d7e84af1833a9"),
            "turn1_return": ("states/turn1_return_017.gst", "a54d249b560c99e10c97385018eb7c19c5c8e0182ef269a157bd570c4281f6ad"),
            "post_start": ("states/turn1_post_action_start_menu.gst", "74bbec5962b0fca24d8b03b178c8c81f281b8a4f39180de41f6fbff67240b999"),
            "turn2_command": ("states/turn2_command.gst", "ac336a3ca3dc4a8ba014e5eeff4a053aa2ace66b3496cf16ca5b505963cdd604"),
            "battle_result": ("states/battle_result.gst", "5047d1c19de285e5f51dbc93d304bbe4d8742905ee77b0f31523640b7e5a5355"),
            "save_menu": ("states/save_menu.gst", "d54d1d3169f2ed2028e8bca766af2cf5e64f5e310174603ecb075eeea2648d81"),
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
    probe_builder.patch_probe(
        rebuilt_normal,
        source,
        completion_layout=True,
        two_hit_attacker=True,
    )
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
        method = "exact current-normal two-hit-attacker builder replay"
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
    wrapper = probe_builder.two_hit_attacker_wrapper_code()
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
                probe_builder.RUNTIME_WRAPPER:
                probe_builder.RUNTIME_WRAPPER + len(wrapper)
            ]
            == wrapper
        ),
        "start_entry_targets_wrapper": (
            probe[
                probe_builder.START_MENU_ENTRY_OPERAND:
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ]
            == probe_builder.RUNTIME_WRAPPER.to_bytes(4, "big")
        ),
        "scope_limit": (
            "diagnostic only: enemy AT/DF and mercenaries, Elwin deployment, "
            "and the isolated Start wrapper; no production candidate mutation"
        ),
    }


def image_report(root: Path, definition: tuple[str, str]) -> dict[str, object]:
    relative_path, expected_sha256 = definition
    path = root / relative_path
    with Image.open(path) as source:
        dimensions = [source.width, source.height]
    actual_sha256 = sha256_path(path)
    surface = surface_classifier.classify_surface(path)
    return {
        "path": relative(path),
        "sha256": actual_sha256,
        "expected_sha256": expected_sha256,
        "hash_matches": actual_sha256 == expected_sha256,
        "bytes": path.stat().st_size,
        "dimensions": dimensions,
        "surface": surface,
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
        "runtime": runner.runtime_combat_state(path),
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
    first = gsts["first_start"]["runtime"]
    turn1 = gsts["turn1_return"]["runtime"]
    restored = gsts["post_start"]["runtime"]
    turn2 = gsts["turn2_command"]["runtime"]
    identity = evidence["scenario_identity"]
    state_sequence_valid = (
        first == {
            "elwin_acted": 0,
            "elwin_hp": 10,
            "elwin_at": 5,
            "bernhardt_hp": 10,
        }
        and turn1["elwin_acted"] == 1
        and turn1["elwin_at"] == 5
        and 0 < turn1["bernhardt_hp"] < 10
        and restored["elwin_acted"] == 1
        and restored["elwin_at"] == 23
        and restored["bernhardt_hp"] == turn1["bernhardt_hp"]
        and turn2["elwin_acted"] == 0
        and turn2["elwin_at"] == 23
        and turn1["bernhardt_hp"] <= turn2["bernhardt_hp"] <= 10
    )
    passed = (
        evidence["status"] == "pass"
        and evidence["profile"] == profile
        and evidence["scenario"] == 17
        and evidence["rom"]["sha256"] == PROBES[profile]["sha256"]
        and evidence["rom"]["md_checksum"] == PROBES[profile]["checksum"]
        and sha256_path(evidence_path) == definition["evidence_sha256"]
        and identity["status"] == "pass"
        and identity["requested_scenario"] == identity["identified_scenario"] == 17
        and identity["best_match"]["matched_records"]
        == identity["best_match"]["total_records"]
        == 11
        and all(row["hash_matches"] for row in images.values())
        and all(row["dimensions"] == [320, 240] for row in images.values())
        and all(row["hash_matches"] for row in gsts.values())
        and state_sequence_valid
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
        "state_sequence_valid": state_sequence_valid,
        "manual_review": {
            "status": "pass",
            "battle_result_text": [
                "전과보고",
                "키스",
                "레스터",
                "제시카",
                "스코트",
                "POINT 4200P",
            ],
            "save_text": ["저장", "1 시나리오 27", "다음 시나리오"],
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
            and runtime["status"] == "pass"
        )
        profiles[profile] = {
            "status": "pass" if passed else "fail",
            "diagnostic_lineage": lineage,
            "runtime": runtime,
        }
    cross_profile = {
        "preparation_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["preparation"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["preparation"]["sha256"]
        ),
        "turn1_command_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["turn1_command"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["turn1_command"]["sha256"]
        ),
        "save_menu_pixel_identical": (
            profiles["normal"]["runtime"]["images"]["save_menu"]["sha256"]
            == profiles["hard"]["runtime"]["images"]["save_menu"]["sha256"]
        ),
        "result_manual_content_identical": True,
        "result_frames_have_different_animation_phase": (
            profiles["normal"]["runtime"]["images"]["battle_result"]["sha256"]
            != profiles["hard"]["runtime"]["images"]["battle_result"]["sha256"]
        ),
    }
    rejected_attempts = [
        {"attempt": "result01", "result": "HP1 edit entered Scenario 17's early-ending path", "classification": "rejected diagnostic"},
        {"attempt": "result02", "result": "input timing lost the Attack selection", "classification": "rejected input trace"},
        {"attempt": "input_probe03/input_probe04", "result": "unsafe offline GST reload reset or booted", "classification": "rejected state manipulation"},
        {"attempt": "result04", "result": "omitted Up and retained Elwin as target", "classification": "rejected input trace"},
        {"attempt": "result05", "result": "Start was sent during the pre-battle dialogue", "classification": "rejected input timing"},
        {"attempt": "result06", "result": "stock AT23 turn-1 attack took the early-ending branch", "classification": "rejected completion path"},
        {"attempt": "result07", "result": "invalid HP19 exceeded the stock HP10 range and froze battle animation", "classification": "rejected diagnostic; removed"},
        {"attempt": "result08", "result": "transient post-battle map was mistaken for command-ready return", "classification": "rejected detector timing"},
        {"attempt": "result09", "result": "stock turn-start regeneration was incorrectly rejected", "classification": "rejected over-strict assertion"},
        {"attempt": "hard/result01", "result": "fixed two-attack assumption waited on the live map", "classification": "rejected runner assumption"},
    ]
    passed = (
        all(row["status"] == "pass" for row in profiles.values())
        and cross_profile["preparation_pixel_identical"]
        and cross_profile["turn1_command_pixel_identical"]
        and cross_profile["save_menu_pixel_identical"]
        and cross_profile["result_manual_content_identical"]
        and cross_profile["result_frames_have_different_animation_phase"]
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": (
            "Fresh current normal/hard Scenario 17 preparation-to-result path, "
            "dynamic commander roster, and save menu"
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
            raise ValueError(f"stale Scenario 17 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 17 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
