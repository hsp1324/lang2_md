#!/usr/bin/env python3
"""Verify fresh current normal/hard Scenario 27 ending evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as korean_builder
from tools import build_scenario27_ending_probe_rom as probe_builder
from tools import run_scenario27_ending_surface as runner
from tools.run_preparation_surface_matrix import md_checksum


DEFAULT_OUTPUT = ROOT / "localization/scenario27_current_ending_surface_regression.json"
CANDIDATES = {
    "normal": {
        "path": ROOT / "tmp/current-s26-particle-fix-normal.md",
        "sha256": "178e70487d4defc3e801abeb37cee43066db0ab5f8685c4c300ea0431336bb70",
        "checksum": "CAF3",
    },
    "hard": {
        "path": ROOT / "tmp/current-s26-particle-fix-hard.md",
        "sha256": "9c6282c7f31f8ad0569944a4fdab0929b53a28b1c5308777eb199c278ecc5f56",
        "checksum": "E0FE",
    },
}
PROBES = {
    "normal": {
        "path": ROOT / "tmp/current-result-probes/normal/s27-particle-ending.md",
        "sha256": "8806c387ad486f1b870045db80d411c01f3f5f05a57c43f0b30c6f47ccc6ef50",
        "checksum": "1661",
    },
    "hard": {
        "path": ROOT / "tmp/current-result-probes/hard/s27-particle-ending.md",
        "sha256": "1a7d3c65b36cd8ca68d6c08a482a49d5bc133596019d51921af4fc88f3e92707",
        "checksum": "1B5F",
    },
}
RUNS = {
    "normal": {
        "root": ROOT / "captures/run/current_s27_ending/normal/runtime08",
        "run_id": "runtime08",
        "evidence_sha256": "26c75b8dd9881b95390d98cc9488d6ed82b4dc3228ed23ca8af3564fdc3e642f",
        "evidence_bytes": 1645459,
        "post_battle_gst_sha256": "d3053b39a4fdc0afc8e3400cb6dd813c698b17e40b43a431a4f15a3f05ef3a01",
        "fin_gst_sha256": "dfcc268f3554c7b61fc728a1b12e65b0e3dc1f93b4d5616afb3fb054ee156f7b",
        "fin_frame": 2957,
        "battle_unique": 34,
        "battle_digest": "f4aba24a18d2a12b26c051c6cf387b2e9ff07754beddbb5ddd1e9b59bf5d6ed2",
        "battle_bytes": 597313,
        "ending_unique": 1124,
        "ending_digest": "ef02ac73e56125239408bc6304e426c0d9892b1c8a255e03850df368384e87e9",
        "ending_bytes": 35171068,
        "historical_matches": {
            "montage": 224,
            "scott": 767,
            "lana": 1222,
            "bozel": 1932,
            "leon": 2207,
            "liana": 2700,
            "elwin": 2805,
            "fin": 2957,
        },
    },
    "hard": {
        "root": ROOT / "captures/run/current_s27_ending/hard/runtime01",
        "run_id": "runtime01",
        "evidence_sha256": "df93b15dc2d4c32890d9bc47c65eae0071c3cdb78a3a73f0b46c2be64105b45e",
        "evidence_bytes": 1640823,
        "post_battle_gst_sha256": "ba4ca5db14efae12ea39c9852b6b3c05ababe279665d44b1339446d0608bf07e",
        "fin_gst_sha256": "699e8450ceea6ef00bb6b0e8515a447b35e3a0fe08e899b564c15ae9bff8e245",
        "fin_frame": 2960,
        "battle_unique": 34,
        "battle_digest": "904a6387da0a448908563daf7c5ffa3167f2387e132c522f226c5bf4a55d4c5a",
        "battle_bytes": 595785,
        "ending_unique": 1126,
        "ending_digest": "3bb8a32643fd83b39e1e04b2d459bd5820d7e747c5801429e0fba46c80343b9d",
        "ending_bytes": 35174483,
        "historical_matches": {
            "montage": 220,
            "scott": 761,
            "lana": 1217,
            "bozel": 1927,
            "leon": 2203,
            "liana": 2700,
            "elwin": 2804,
            "fin": 2960,
        },
    },
}
SURFACE_HASHES = {
    "preparation": "77de0c40fb053bdb261d0226128e9a450388fe40fc6099429e1edc29dd530437",
    "turn1_command": "a242a0ef129eed4026a2f0d00dc52e0bbef0a5f8f2b67c3219ad4c5e24a95010",
    "bernhardt_target": "14c090c2258e687b45a6e80603337c2ba94a6dc4c7d162ff2c5fb47af263d7c1",
    "fin": "4cb7db62c30ace38e0d8b2fa1a34fc7ba31586104f5b59c9663b6ad9564a46b0",
}
HISTORICAL_REFERENCES = {
    "montage": (100, "0e9e02c2636667098be11c3dd48cf7ea6f9b542081bff69fe6fc5b3eb3e50265"),
    "scott": (225, "2fcfb72fc90c5f4ec040362c95245de0c53fff70055eacbce98997d3fc13f1ce"),
    "lana": (400, "78d4c84d076cf6e4bba5e794c26ea59145af4df7342ec86c695615df4adc92ae"),
    "bozel": (575, "ad013a95bcd1d258e2dca78982d34ab7d7437be6a3ec1124faebb64efba5e307"),
    "leon": (650, "612a042329ce427419896bf736bd04a106824510f17bfe52d3ee47bdbb86ba90"),
    "liana": (800, "e14bc69eeb74e34be38aa740ccc6eafc34002706de84df395dac7165af79e8d2"),
    "elwin": (825, "ee69e166d2327f5f218325164cd8bc6ca116763bfe59a3396b48158bf21fc3b2"),
    "fin": (875, SURFACE_HASHES["fin"]),
}
MANUAL_HARD_REVIEW = {
    "keith": (1050, "998e576be73b224d1ce3571c425d8af4e365a6e9b3c27503d33e8ef6de0cdb4e"),
    "egbert": (2360, "0099abb3c0b115ed549aae7d737fd02f17c763b37838cc8eda6218453276548d"),
    "bernhardt": (2460, "08366b6db6bedf2d783408340607f8cd90fc78d1f0c162ab410099de2dd4d961"),
    "fin": (2960, SURFACE_HASHES["fin"]),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sequence_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    hashes = [str(row["sha256"]) for row in rows]
    paths = [ROOT / str(row.get("path", row.get("capture"))) for row in rows]
    actual_hashes = [sha256(path) for path in paths]
    return {
        "frame_count": len(rows),
        "unique_frame_hashes": len(set(hashes)),
        "sequence_digest": hashlib.sha256("".join(hashes).encode()).hexdigest(),
        "total_bytes": sum(path.stat().st_size for path in paths),
        "all_recorded_hashes_match_files": hashes == actual_hashes,
    }


def artifact(path: Path, expected_sha256: str) -> dict[str, object]:
    actual = sha256(path)
    return {
        "path": relative(path),
        "sha256": actual,
        "expected_sha256": expected_sha256,
        "hash_matches": actual == expected_sha256,
        "bytes": path.stat().st_size,
    }


def exact_probe_rebuild(profile: str) -> bool:
    source = (ROOT / korean_builder.IN_ROM).read_bytes()
    rebuilt = bytearray(CANDIDATES[profile]["path"].read_bytes())
    probe_builder.patch_probe(
        rebuilt,
        source,
        allow_balanced_input=profile == "hard",
    )
    return bytes(rebuilt) == PROBES[profile]["path"].read_bytes()


def build_profile(profile: str) -> dict[str, object]:
    expected = RUNS[profile]
    root = expected["root"]
    evidence_path = root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    battle = sequence_summary(evidence["battle_frames"])
    ending = sequence_summary(evidence["ending_observations"])
    images = {
        key: artifact(ROOT / evidence[key]["path"], value)
        for key, value in SURFACE_HASHES.items()
        if key in evidence
    }
    historical = {}
    for label, frame in expected["historical_matches"].items():
        old_frame, old_hash = HISTORICAL_REFERENCES[label]
        old_path = ROOT / f"captures/run/e93e_s27_ending_watch/{old_frame:03d}.png"
        current_path = root / f"ending/advance_{frame:04d}.png"
        historical[label] = {
            "historical_path": relative(old_path),
            "current_path": relative(current_path),
            "sha256": old_hash,
            "historical_hash_matches": sha256(old_path) == old_hash,
            "current_hash_matches": sha256(current_path) == old_hash,
        }
    run_checks = {
        "status": evidence["status"] == "pass",
        "profile": evidence["profile"] == profile,
        "scenario": evidence["scenario"] == 27,
        "run_id": evidence["run_id"] == expected["run_id"],
        "acceptance_not_updated": evidence["acceptance_updated"] is False,
        "rom_hash": evidence["rom"]["sha256"] == PROBES[profile]["sha256"],
        "rom_checksum": evidence["rom"]["md_checksum"] == PROBES[profile]["checksum"],
        "scenario_identity": (
            evidence["scenario_identity"]["status"] == "pass"
            and evidence["scenario_identity"]["identified_scenario"] == 27
            and evidence["scenario_identity"]["best_match"]["matched_records"] == 10
            and evidence["scenario_identity"]["best_match"]["total_records"] == 10
        ),
        "bernhardt_runtime_state": evidence["bernhardt_runtime_state"] == {
            "class_id": 78,
            "name_id": 14,
            "defeated_flag": 0,
            "defeated": False,
            "hp": 0,
            "x": 15,
            "y": 15,
        },
        "post_battle_gst": evidence["post_battle_gst_sha256"] == expected["post_battle_gst_sha256"],
        "fin_gst": evidence["fin_gst_sha256"] == expected["fin_gst_sha256"],
        "fin_frame": evidence["fin_frame"] == expected["fin_frame"],
        "fin_detector": runner.fin_visible(root / f"ending/advance_{expected['fin_frame']:04d}.png"),
    }
    sequence_checks = {
        "battle": {
            **battle,
            "expected_frame_count": 36,
            "expected_unique_frame_hashes": expected["battle_unique"],
            "expected_sequence_digest": expected["battle_digest"],
            "expected_total_bytes": expected["battle_bytes"],
        },
        "ending": {
            **ending,
            "expected_frame_count": expected["fin_frame"],
            "expected_unique_frame_hashes": expected["ending_unique"],
            "expected_sequence_digest": expected["ending_digest"],
            "expected_total_bytes": expected["ending_bytes"],
        },
    }
    candidate = artifact(CANDIDATES[profile]["path"], CANDIDATES[profile]["sha256"])
    candidate["checksum"] = md_checksum(CANDIDATES[profile]["path"])
    candidate["checksum_matches"] = candidate["checksum"] == CANDIDATES[profile]["checksum"]
    probe = artifact(PROBES[profile]["path"], PROBES[profile]["sha256"])
    probe["checksum"] = md_checksum(PROBES[profile]["path"])
    probe["checksum_matches"] = probe["checksum"] == PROBES[profile]["checksum"]
    probe["exact_rebuild"] = exact_probe_rebuild(profile)
    probe["changed_byte_count_including_checksum"] = sum(
        before != after
        for before, after in zip(
            CANDIDATES[profile]["path"].read_bytes(),
            PROBES[profile]["path"].read_bytes(),
        )
    )
    evidence_artifact = artifact(evidence_path, expected["evidence_sha256"])
    evidence_bytes_match = evidence_path.stat().st_size == expected["evidence_bytes"]
    checks = [
        *run_checks.values(),
        *[row["hash_matches"] for row in images.values()],
        *[
            value
            for row in historical.values()
            for key, value in row.items()
            if key.endswith("_matches")
        ],
        candidate["hash_matches"],
        candidate["checksum_matches"],
        probe["hash_matches"],
        probe["checksum_matches"],
        probe["exact_rebuild"],
        probe["changed_byte_count_including_checksum"] == 11,
        evidence_artifact["hash_matches"],
        evidence_bytes_match,
        battle["frame_count"] == 36,
        battle["unique_frame_hashes"] == expected["battle_unique"],
        battle["sequence_digest"] == expected["battle_digest"],
        battle["total_bytes"] == expected["battle_bytes"],
        battle["all_recorded_hashes_match_files"],
        ending["frame_count"] == expected["fin_frame"],
        ending["unique_frame_hashes"] == expected["ending_unique"],
        ending["sequence_digest"] == expected["ending_digest"],
        ending["total_bytes"] == expected["ending_bytes"],
        ending["all_recorded_hashes_match_files"],
    ]
    return {
        "status": "pass" if all(checks) else "fail",
        "candidate": candidate,
        "diagnostic_probe": probe,
        "evidence_json": evidence_artifact,
        "evidence_bytes_match": evidence_bytes_match,
        "run_checks": run_checks,
        "images": images,
        "sequences": sequence_checks,
        "historical_pixel_matches": historical,
    }


def build_report() -> dict[str, object]:
    profiles = {profile: build_profile(profile) for profile in ("normal", "hard")}
    hard_root = RUNS["hard"]["root"]
    manual_review = {}
    for label, (frame, expected_hash) in MANUAL_HARD_REVIEW.items():
        path = hard_root / f"ending/advance_{frame:04d}.png"
        manual_review[label] = {
            **artifact(path, expected_hash),
            "review": "clean Korean text, portrait, class/status graphics, and background",
        }
    cross_profile = {
        "preparation_pixel_identical": (
            profiles["normal"]["images"]["preparation"]["sha256"]
            == profiles["hard"]["images"]["preparation"]["sha256"]
        ),
        "turn1_command_pixel_identical": (
            profiles["normal"]["images"]["turn1_command"]["sha256"]
            == profiles["hard"]["images"]["turn1_command"]["sha256"]
        ),
        "bernhardt_target_pixel_identical": (
            profiles["normal"]["images"]["bernhardt_target"]["sha256"]
            == profiles["hard"]["images"]["bernhardt_target"]["sha256"]
        ),
        "fin_pixel_identical": (
            profiles["normal"]["images"]["fin"]["sha256"]
            == profiles["hard"]["images"]["fin"]["sha256"]
        ),
        "timing_note": (
            "Normal and hard frame indices differ slightly because autonomous "
            "animation timing differs; accepted historical surfaces and Fin "
            "are compared by content hash instead of index."
        ),
    }
    status = "pass" if (
        all(row["status"] == "pass" for row in profiles.values())
        and all(row["hash_matches"] for row in manual_review.values())
        and all(
            value for key, value in cross_profile.items()
            if key.endswith("_identical")
        )
    ) else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "scenario": 27,
        "scope": (
            "Fresh selector entry, preparation, automatic deployment, ordinary "
            "Elwin/Bernhardt battle, complete stock ending, epilogues, credits, and Fin"
        ),
        "profiles": profiles,
        "manual_hard_review": manual_review,
        "cross_profile": cross_profile,
        "automation": {
            "fresh_uninterrupted_runs_only": True,
            "savestate_resume_accepted": False,
            "savestate_resume_note": (
                "Same-run GST continuation was rejected after BlastEm returned "
                "to Sega/title; accepted evidence always starts from the selector."
            ),
            "fin_bound_frames": 3200,
        },
        "release_promoted": False,
        "acceptance_updated": False,
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
            raise ValueError(f"stale Scenario 27 ending report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if report["status"] != "pass":
        raise RuntimeError("Scenario 27 current ending verification failed")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
