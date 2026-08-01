#!/usr/bin/env python3
"""Verify current normal/hard Scenario 18-20 result-surface evidence."""

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
from tools import build_scenario18_clear_probe_rom as builder18
from tools import build_scenario19_clear_probe_rom as builder19
from tools import build_scenario20_clear_probe_rom as builder20
from tools import run_scenario14_15_result_surface as surface_classifier


DEFAULT_OUTPUT = (
    ROOT / "localization/scenario18_20_current_result_surface_regression.json"
)
CAPTURE_ROOT = ROOT / "captures/run/current_s18_20_result"
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
SCENARIOS = {
    18: {
        "builder": builder18,
        "state": ROOT / (
            "captures/runtime/s18_completion_17f2/.local/share/blastem/"
            "Langrisser II (Scenario 18 Completion Probe)/quicksave.gst"
        ),
        "state_sha256": "7705afdf02ad178b589c74dbd59998279759f8eb68014b0fe74271a8741d01d3",
        "probes": {
            "normal": {
                "path": ROOT / "tmp/current-result-probes/normal/s18.md",
                "sha256": "c118c30250bceb0ed9f23ea7da20427b1513637b858fa284ad80d8123d3fc1ba",
                "checksum": "04CD",
            },
            "hard": {
                "path": ROOT / "tmp/current-result-probes/hard/s18.md",
                "sha256": "1fcc0e36ce7589bd27f1f29eef662e5719f43f3f7ad21dc35d423b9330253afe",
                "checksum": "EEBE",
            },
        },
    },
    19: {
        "builder": builder19,
        "state": ROOT / (
            "captures/runtime/s19_completion_2829_strong/.local/share/blastem/"
            "Langrisser II (Scenario 19 Completion Probe)/quicksave.gst"
        ),
        "state_sha256": "b7ea024e1332febd6dd00cd79224d99abc1543b830d9f2957189fd446956597d",
        "hard_state": ROOT / (
            "captures/runtime/current-s19-hard-result06/.local/share/blastem/"
            "s19/quicksave.gst"
        ),
        "hard_state_sha256": "da46cf9718c0c93d9d643eb41fb385e394847beaa287c72c994a3700813ba54b",
        "hard_state_hp_offset": 0x8877,
        "probes": {
            "normal": {
                "path": ROOT / "tmp/current-result-probes/normal/s19.md",
                "sha256": "28d3c110182fde302ad842d700241af64f81caf420fa08236c62b23912a02e8e",
                "checksum": "1504",
            },
            "hard": {
                "path": ROOT / "tmp/current-result-probes/hard/s19.md",
                "sha256": "27a6d3cea3f50f0c0bd0ef5a9df11a29e47028f79e051f7966b6a50608631b2f",
                "checksum": "C6BF",
            },
        },
    },
    20: {
        "builder": builder20,
        "state": ROOT / (
            "captures/runtime/s20_completion_d2f9_hidden/.local/share/blastem/"
            "Langrisser II (Scenario 20 Completion Probe)/quicksave.gst"
        ),
        "state_sha256": "595c32d434bb3d79d0dd8513256c77a38c2191bedea95730c3eca1e23d3b3bc2",
        "probes": {
            "normal": {
                "path": ROOT / "tmp/current-result-probes/normal/s20.md",
                "sha256": "4d6cd94dba1f0d23340543c8f787a4dc8de6e70e32173e9c3ea4598e6e0bdc1b",
                "checksum": "C6B0",
            },
            "hard": {
                "path": ROOT / "tmp/current-result-probes/hard/s20.md",
                "sha256": "212561e2af4411db771f0dcaf37b036861fdd3c5e2c71a71c8c89f5c74a73def",
                "checksum": "A89B",
            },
        },
    },
}


def evidence(
    sha256: str,
    observed: list[str],
    surface: str = "other",
) -> dict[str, object]:
    return {"sha256": sha256, "observed": observed, "surface": surface}


EVIDENCE = {
    "normal": {
        18: {
            "s18_boss_defeat.png": evidence("fe8448ae76713f3c2a549d7d7cf406894faecddcc56005a82241e891a8619e60", ["그레이트드래곤", "격파"]),
            "s18_scott_dialogue.png": evidence("4f80f82e3ba3269de120f55733c541217ef7a7e1c365b575797aabd286bec0d5", ["스코트"]),
            "s18_resident_dialogue.png": evidence("4d6718e90bca3c76cdbde898223d84a5dc252c5c1756166b7d35eb231a6697d0", ["주민"]),
            "s18_elwin_dialogue.png": evidence("d730dd0dc60e59ff86c1be94bbecfebd1483057b551a345b03c7b6c7702e1396", ["엘윈"]),
            "s18_elwin_level.png": evidence("e32b86958e2b73d2ae7492e13c02a17189f07be947373cee773259a11c1efdf7", ["엘윈의", "레벨이 올랐다"]),
            "s18_class_change.png": evidence("298b4e8498c99185220477ebd05f8224463be6282e9fb45738c163aabbf06bda", ["클래스체인지", "스코트", "세인트"]),
            "s18_result.png": evidence("2bb0a355e3796dee86d3f93322e95ccbee1f5539d9d4b1cb63216a0e4127d343", ["전과보고", "POINT 12500P"], "battle_result"),
            "s18_save.png": evidence("cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a", ["저장", "다음 시나리오"], "save_menu"),
        },
        19: {
            "s19_imelda_dialogue.png": evidence("6fd5ca173a88c539f9c01735a1317aded1019678cab9b24d674d469804375a13", ["이멜다", "제너럴"]),
            "s19_elwin_dialogue.png": evidence("991b74c772f648cf2838bef5a21a8c7fa2ac1d8835df2f8b1692baa475bab870", ["엘윈"]),
            "s19_elwin_level.png": evidence("74385e7969d26ccaebe59b1eb81efe5e6a33d3c981416381b5f0431fe43b77fb", ["엘윈의", "레벨이 올랐다"]),
            "s19_aaron_level.png": evidence("69b47aba867403cf22fb13875efc109fed76a64124b11cf837723be19f22c33f", ["아론의", "레벨이 올랐다"]),
            "s19_result.png": evidence("bfb7feead8e5636e83cc9c7f590181269682877d06631b88bc4eb3d979ee57ce", ["전과보고", "POINT 14600P"], "battle_result"),
            "s19_save.png": evidence("cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a", ["저장", "다음 시나리오"], "save_menu"),
        },
        20: {
            "s20_fias_dialogue.png": evidence("1ea0e3e9c84d94b9d8a00f5a7b7b74df056e4bc7cfe5a47b47dcfa08a2589693", ["파이어스", "데몬로드"]),
            "s20_elwin_dialogue.png": evidence("fecab6fff196f93ef6e3a9e116975d3d23f0ade52e1c6ef9195bf8ed3a32bf93", ["엘윈"]),
            "s20_jessica_dialogue.png": evidence("accaa2e11e57a3f5fd7ddbb844d6252bc016e9a8123f5de680147d8c7cdfa0b4", ["제시카"]),
            "s20_keith_dialogue.png": evidence("8fe01239ed276083c6a171bbeaa8a7b31cb96468a764e9e42a40df0bcc95376f", ["키스"]),
            "s20_elwin_level.png": evidence("233cc711b169192ca0d9631b9a7a1d9b73766239f1bd843e6743377f3db34ef9", ["엘윈의", "레벨이 올랐다"]),
            "s20_class_change.png": evidence("118a31908656e9a247dda268d2bd096f09370265709cb15fdf8801adc0a4fcea", ["클래스체인지", "스코트"]),
            "s20_result.png": evidence("99d9906f9ac03e21a83e77787a15fd6e9bf3f17e86565fb1e7c8819b0d8b0e4c", ["전과보고", "POINT 0P"], "battle_result"),
            "s20_save.png": evidence("cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a", ["저장", "다음 시나리오"], "save_menu"),
        },
    },
    "hard": {
        18: {
            "s18_boss_defeat.png": evidence("4986ef9d2ee64c2442bf182e3f2965b82c8747c503c915a2b7c006d49cc0c4b2", ["그레이트드래곤", "격파"]),
            "s18_scott_dialogue.png": evidence("305cac7c8a059069d33414330c3c4f766012ce93010324ddeff7deb97162e76f", ["스코트"]),
            "s18_resident_dialogue.png": evidence("c3e09d6334551beb5211b5169050bf71d85149ae770117e89145d96b53239cc3", ["주민"]),
            "s18_elwin_dialogue.png": evidence("0aabbab3e83c6eb3241c7871d91614aa464b1e4cf326d855cedb85f9568690ac", ["엘윈"]),
            "s18_elwin_level.png": evidence("aee117a051318dcc061e737efc0b43665b4bde631ecbb602d2c07cefd615f436", ["엘윈의", "레벨이 올랐다"]),
            "s18_class_change.png": evidence("cd43294328dcab9f4d82ba7d7a554db330155008b93c48726e2ee2872060c614", ["클래스체인지", "스코트"]),
            "s18_result.png": evidence("2bb0a355e3796dee86d3f93322e95ccbee1f5539d9d4b1cb63216a0e4127d343", ["전과보고", "POINT 12500P"], "battle_result"),
            "s18_save.png": evidence("cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a", ["저장", "다음 시나리오"], "save_menu"),
        },
        19: {
            "s19_imelda_hp0.png": evidence("5d42dd3a940164588851579d1043c20122941e6d75bd81313021a57bc7c37486", ["이멜다", "HP0"]),
            "s19_elwin_level.png": evidence("477f6995727a485f1eaa2e4f4ae9164aafdc9601ed6b30c236101f8ca66f02e2", ["엘윈의", "레벨이 올랐다"]),
            "s19_aaron_level.png": evidence("69b47aba867403cf22fb13875efc109fed76a64124b11cf837723be19f22c33f", ["아론의", "레벨이 올랐다"]),
            "s19_result.png": evidence("bb8e04d61a44b60b2d765f8dd3be4d28c331ac1b34cff68dd5c99709a1636647", ["전과보고", "POINT 15500P"], "battle_result"),
            "s19_save.png": evidence("cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a", ["저장", "다음 시나리오"], "save_menu"),
        },
        20: {
            "s20_fias_dialogue.png": evidence("49fedb261935c700d7e0a67a5ae8cb48b5ae082b400f9eab0d75aa8dfe59a178", ["파이어스", "데몬로드"]),
            "s20_elwin_dialogue.png": evidence("5158dad3e1dd9d0db983820cf0147e3f525a02e1c4dbc45617d05be5b60fbbc5", ["엘윈"]),
            "s20_jessica_dialogue.png": evidence("90b3891a20473e3194e23f923586ab6447f325f229b49bbb9025330fdad3cd8b", ["제시카"]),
            "s20_keith_dialogue.png": evidence("0d700be9d37b2ba62b8a82c987303d78fe401219d8b60951c062793dd1d1ae7b", ["키스"]),
            "s20_elwin_level.png": evidence("9243680d9f5fe7dfef3d5bcbe620959170a19eaa929b730d09795136493afe17", ["엘윈의", "레벨이 올랐다"]),
            "s20_class_change.png": evidence("216e60b57af0b2286558cbabacab8643422020ff151337d6a7690cd6205b8948", ["클래스체인지", "스코트"]),
            "s20_result.png": evidence("8d27d664940a1653b4c93dfaa01d13448ad9bf3a2eb22e3262a07deeb1849e53", ["전과보고", "POINT 18050P"], "battle_result"),
            "s20_save.png": evidence("cd36d6691dcd0cae1c3458ad5a7c8869cb123245dec5ac982a9cd7a304288d9a", ["저장", "다음 시나리오"], "save_menu"),
        },
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


def lineage_report(scenario: int, profile: str) -> dict[str, object]:
    definition = SCENARIOS[scenario]
    builder = definition["builder"]
    candidate_path = CANDIDATES[profile]["path"]
    probe_definition = definition["probes"][profile]
    probe_path = probe_definition["path"]
    normal_candidate = NORMAL_CANDIDATE.read_bytes()
    normal_probe = definition["probes"]["normal"]["path"].read_bytes()
    candidate = candidate_path.read_bytes()
    probe = probe_path.read_bytes()
    rebuilt_normal = bytearray(normal_candidate)
    builder.patch_probe(
        rebuilt_normal,
        builder.DEFAULT_SOURCE_ROM.read_bytes(),
        completion_layout=True,
    )
    delta = {
        offset
        for offset, (before, after) in enumerate(
            zip(normal_candidate, rebuilt_normal)
        )
        if before != after
    }
    if profile == "normal":
        exact = bytes(rebuilt_normal) == probe
        conflicts = 0
        method = "exact current-normal completion-layout builder replay"
    else:
        expected = bytearray(candidate)
        for offset in delta - {0x18E, 0x18F}:
            expected[offset] = rebuilt_normal[offset]
        md_builder.update_md_checksum(expected)
        exact = bytes(expected) == probe
        conflicts = sum(
            normal_candidate[offset] != candidate[offset]
            for offset in delta - {0x18E, 0x18F}
        )
        method = (
            "exact current-normal diagnostic delta over the current hard "
            "candidate, followed only by checksum recalculation"
        )
    candidate_report = rom_report(candidate_path)
    probe_report = rom_report(probe_path)
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
            probe_report["sha256"] == probe_definition["sha256"]
            and probe_report["header_checksum"] == probe_definition["checksum"]
        ),
        "diagnostic_changed_byte_count": len(delta),
        "hard_bytes_replaced_inside_diagnostic_envelope": conflicts,
        "exact_rebuild": exact,
    }


def state_report(scenario: int) -> dict[str, object]:
    definition = SCENARIOS[scenario]
    source_path = definition["state"]
    source = source_path.read_bytes()
    report: dict[str, object] = {
        "path": relative(source_path),
        "sha256": sha256_path(source_path),
        "bytes": len(source),
        "identity_matches": sha256_path(source_path)
        == definition["state_sha256"],
        "normal_method": "historical completion continuation loaded unchanged",
    }
    if scenario == 19:
        hard_path = definition["hard_state"]
        hard = hard_path.read_bytes()
        changed = [
            offset
            for offset, (before, after) in enumerate(zip(source, hard))
            if before != after
        ]
        hp_offset = definition["hard_state_hp_offset"]
        report["hard_diagnostic"] = {
            "path": relative(hard_path),
            "sha256": sha256_path(hard_path),
            "bytes": len(hard),
            "identity_matches": sha256_path(hard_path)
            == definition["hard_state_sha256"],
            "exact_changed_offsets": [f"0x{offset:X}" for offset in changed],
            "exact_one_byte_hp_edit": (
                changed == [hp_offset]
                and source[hp_offset] == 10
                and hard[hp_offset] == 1
            ),
            "edit": "runtime Imelda current HP 10 -> 1",
            "scope_limit": (
                "deterministically enters the stock Imelda-defeat result path; "
                "not battle-balance evidence and not a distributable savestate"
            ),
        }
    return report


def reviewed_image(
    profile: str,
    scenario: int,
    filename: str,
    definition: dict[str, object],
) -> dict[str, object]:
    path = CAPTURE_ROOT / profile / filename
    with Image.open(path) as source:
        dimensions = [source.width, source.height]
    actual_sha256 = sha256_path(path)
    actual_surface = surface_classifier.classify_surface(path)
    return {
        "path": relative(path),
        "sha256": actual_sha256,
        "bytes": path.stat().st_size,
        "dimensions": dimensions,
        "surface": actual_surface,
        "expected_surface": definition["surface"],
        "expected_reviewed_sha256": definition["sha256"],
        "reviewed_hash_matches": actual_sha256 == definition["sha256"],
        "surface_matches": actual_surface == definition["surface"],
        "manual_review": "pass",
        "observed_text": definition["observed"],
        "observed_sprite_state": "clean",
    }


def runtime_report(profile: str, scenario: int) -> dict[str, object]:
    rows = {
        filename: reviewed_image(profile, scenario, filename, definition)
        for filename, definition in EVIDENCE[profile][scenario].items()
    }
    result = rows[f"s{scenario}_result.png"]
    save = rows[f"s{scenario}_save.png"]
    passed = (
        all(row["dimensions"] == [320, 240] for row in rows.values())
        and all(row["reviewed_hash_matches"] for row in rows.values())
        and all(row["surface_matches"] for row in rows.values())
        and result["surface"] == "battle_result"
        and save["surface"] == "save_menu"
    )
    return {
        "status": "pass" if passed else "fail",
        "evidence_count": len(rows),
        "evidence": rows,
        "battle_result": result,
        "save_menu": save,
        "scope_limit": (
            "historical work RAM continues directly into current ROM result "
            "renderers; this is not a fresh deployment-to-clear replay or "
            "hard-mode balance evidence"
        ),
    }


def build_report() -> dict[str, object]:
    scenarios: dict[str, object] = {}
    for scenario in (18, 19, 20):
        profiles = {}
        for profile in ("normal", "hard"):
            lineage = lineage_report(scenario, profile)
            runtime = runtime_report(profile, scenario)
            passed = (
                lineage["candidate_identity_matches"]
                and lineage["probe_identity_matches"]
                and lineage["candidate"]["checksum_valid"]
                and lineage["probe"]["checksum_valid"]
                and lineage["exact_rebuild"]
                and runtime["status"] == "pass"
            )
            profiles[profile] = {
                "status": "pass" if passed else "fail",
                "diagnostic_lineage": lineage,
                "runtime": runtime,
            }
        state = state_report(scenario)
        state_pass = state["identity_matches"]
        if scenario == 19:
            state_pass = state_pass and state["hard_diagnostic"][
                "identity_matches"
            ] and state["hard_diagnostic"]["exact_one_byte_hp_edit"]
        scenario_pass = state_pass and all(
            row["status"] == "pass" for row in profiles.values()
        )
        scenarios[str(scenario)] = {
            "status": "pass" if scenario_pass else "fail",
            "source_state": state,
            "profiles": profiles,
        }
    cross_profile = {
        "scenario18_result_pixel_identical": (
            scenarios["18"]["profiles"]["normal"]["runtime"][
                "battle_result"
            ]["sha256"]
            == scenarios["18"]["profiles"]["hard"]["runtime"][
                "battle_result"
            ]["sha256"]
        ),
        "all_save_menu_frames_pixel_identical": len(
            {
                scenarios[str(scenario)]["profiles"][profile]["runtime"][
                    "save_menu"
                ]["sha256"]
                for scenario in (18, 19, 20)
                for profile in ("normal", "hard")
            }
        )
        == 1,
        "scenario19_and_20_point_totals_intentionally_differ": True,
        "manual_roster_and_sprite_review": "pass",
    }
    rejected_attempts = [
        {
            "scenario": 19,
            "profile": "hard",
            "attempt": "HP10 continuation with short repeated confirms",
            "result": (
                "ordinary damage left Imelda at HP1; later confirms selected "
                "Laird's status panel instead of proving completion"
            ),
            "classification": "input/timing and incomplete battle, not a renderer failure",
        },
        {
            "scenario": 19,
            "profile": "hard",
            "attempt": "end turn after the incomplete HP1 branch",
            "result": "reached GAME OVER rather than battle result",
            "classification": "rejected completion evidence",
        },
        {
            "scenario": 19,
            "profile": "hard",
            "attempt": "runtime Imelda HP9",
            "result": "ordinary damage was 8 and again left HP1",
            "classification": "rejected nondeterministic completion evidence",
        },
        {
            "scenario": 19,
            "profile": "hard",
            "attempt": "temporary Start-menu MP guard checksum A2BC",
            "result": "not needed for the accepted run and removed from source",
            "classification": "rejected diagnostic ROM",
        },
    ]
    passed = (
        all(row["status"] == "pass" for row in scenarios.values())
        and cross_profile["scenario18_result_pixel_identical"]
        and cross_profile["all_save_menu_frames_pixel_identical"]
    )
    return {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": (
            "Current normal/hard Scenario 18, 19, and 20 boss defeat, stock "
            "aftermath names/classes, class-change pages, result rosters, "
            "sprites, and save menus"
        ),
        "release_promoted": False,
        "acceptance_updated": False,
        "savestate_policy": (
            "player migration uses in-game SRM load under the current ROM and "
            "then creates a fresh savestate; historical GSTs here are isolated "
            "renderer-continuation fixtures only"
        ),
        "scenarios": scenarios,
        "cross_profile": cross_profile,
        "rejected_attempts": rejected_attempts,
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
            raise ValueError(f"stale Scenario 18-20 result report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 18-20 current result verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
