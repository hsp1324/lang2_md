#!/usr/bin/env python3
"""Verify the hash-bound v1.3.4 all-scenario isolated-play evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "localization/v134_all_scenario_replay.json"
ALL_SCENARIOS = list(range(1, 32))
FIRST_TURN_PROFILES = {"pure", "normal", "hard"}
RESULT_PROFILES = {"normal", "hard"}
RESULT_SCENARIOS = {28, 29, 30, 31}
FRESH_PRE27_RESULT_SCENARIOS = {
    *range(1, 11),
    *range(14, 18),
    *range(21, 28),
}
CARRIED_RESULT_SCENARIOS = {11, 12, 13, 18, 19, 20}
RESULT_ONLY_SCENARIOS = {14, 15, 16}
FIN_SHA256 = (
    "4cb7db62c30ace38e0d8b2fa1a34fc7b"
    "a31586104f5b59c9663b6ad9564a46b0"
)
RELEASE_ROM_SHA256 = {
    "normal": "65d7458a3e4aa993c107ff15cda9152b206cf96c0a7ac3e32dfcf6365f4d99a4",
    "hard": "5dc9b5502210b2eb86ea16eff3bd8d047fa4b952f817a3366c4cbd6dd3b49dcf",
}
FULL_SURFACE_COMPONENTS = {
    ("preparation", "normal"),
    ("preparation", "hard"),
    ("gray_acted", "normal"),
    ("gray_acted", "hard"),
    ("preparation_glyph_conflicts", "both"),
    ("preparation_scenario_identity", "both"),
    ("battle_cache", "both"),
    ("all_mercenary_hire", "normal"),
    ("all_mercenary_hire", "hard"),
    ("pike_acted", "normal"),
    ("pike_acted", "hard"),
    ("monk_acted", "normal"),
    ("monk_acted", "hard"),
    ("shop_necklace", "normal"),
    ("shop_necklace", "hard"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_file(row: dict[str, object]) -> Path:
    path = ROOT / str(row["path"])
    if not path.is_file():
        raise ValueError(f"missing all-scenario evidence: {path}")
    actual = sha256(path)
    expected = str(row["sha256"])
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual} != {expected}")
    return path


def pair_set(rows: list[list[object]]) -> set[tuple[str, int]]:
    return {(str(profile), int(scenario)) for profile, scenario in rows}


def source_pair_set(source: dict[str, object]) -> set[tuple[str, int]]:
    return {
        (str(profile), int(scenario))
        for profile in source.get("profiles", [])
        for scenario in source.get("scenarios", [])
    }


def verify_recorded_image(image: object, surface: str) -> None:
    if not isinstance(image, dict):
        raise ValueError(f"fresh {surface} image is missing")
    path = ROOT / str(image["path"])
    if (
        (surface != "fin" and image.get("surface") != surface)
        or not path.is_file()
        or sha256(path) != image.get("sha256")
    ):
        raise ValueError(f"fresh {surface} image changed: {path}")


def verify_fresh_result_evidence(
    row: dict[str, object],
    probes: dict[tuple[str, int], dict[str, object]],
) -> str:
    profile = str(row["profile"])
    scenario = int(row["scenario"])
    evidence_path = ROOT / str(row["evidence"])
    if not evidence_path.is_file():
        raise ValueError(f"missing fresh result evidence: {evidence_path}")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    identity = evidence.get("scenario_identity", {})
    if (
        evidence.get("status") != "pass"
        or evidence.get("profile") != profile
        or evidence.get("scenario") != scenario
        or identity.get("status") != "pass"
        or identity.get("requested_scenario") != scenario
        or identity.get("identified_scenario") != scenario
        or evidence.get("rom", {}).get("sha256")
        != probes[(profile, scenario)]["sha256"]
    ):
        raise ValueError(f"fresh result evidence changed: {evidence_path}")

    if scenario == 27:
        verify_recorded_image(evidence["fin"], "fin")
        if (
            evidence["fin"]["sha256"] != FIN_SHA256
            or evidence.get("bernhardt_runtime_state", {}).get("hp") != 0
        ):
            raise ValueError(f"Scenario 27 ending changed: {evidence_path}")
    else:
        verify_recorded_image(evidence["battle_result"], "battle_result")
        save_menu = evidence.get("save_menu")
        if scenario in RESULT_ONLY_SCENARIOS:
            if save_menu is not None:
                raise ValueError(f"unexpected result-only SAVE: {evidence_path}")
        else:
            verify_recorded_image(save_menu, "save_menu")
    return sha256(evidence_path)


def validate_contract(manifest: dict[str, object]) -> None:
    if (
        manifest.get("schema_version") != 1
        or manifest.get("release") != "v1.3.4"
        or manifest.get("status") != "reviewed_pass"
    ):
        raise ValueError("all-scenario manifest is not a passing v1.3.4 review")
    method = manifest.get("method", {})
    if method.get("display") != "isolated Xvfb" or method.get(
        "physical_desktop_used"
    ):
        raise ValueError("all-scenario replay was not isolated from the desktop")
    if manifest.get("scenarios") != ALL_SCENARIOS:
        raise ValueError("all-scenario manifest must cover Scenarios 1..31")

    first_turn = manifest.get("first_turn_replay", {})
    profiles = first_turn.get("profiles", [])
    if {row.get("profile") for row in profiles} != FIRST_TURN_PROFILES:
        raise ValueError("first-turn replay must cover pure, normal, and hard")
    for row in profiles:
        if row.get("passed_scenarios") != ALL_SCENARIOS:
            raise ValueError(f"{row.get('profile')} first-turn coverage is incomplete")
        counts = row.get("endpoint_counts", {})
        if sum(int(value) for value in counts.values()) != len(ALL_SCENARIOS):
            raise ValueError(f"{row.get('profile')} endpoint counts are incomplete")

    full = manifest.get("full_surface_replay", {})
    if full.get("profiles") != ["normal", "hard"]:
        raise ValueError("full surface replay must cover normal and hard")
    if full.get("scenarios") != ALL_SCENARIOS:
        raise ValueError("full surface replay must cover Scenarios 1..31")
    components = full.get("component_reports", [])
    component_pairs = {
        (str(row.get("kind")), str(row.get("profile")))
        for row in components
    }
    if component_pairs != FULL_SURFACE_COMPONENTS or len(components) != len(
        FULL_SURFACE_COMPONENTS
    ):
        raise ValueError("full surface component coverage changed")

    result_rows = manifest.get("late_result_and_save_replay", [])
    pairs = {
        (str(row.get("profile")), int(row.get("scenario", 0)))
        for row in result_rows
    }
    expected_pairs = {
        (profile, scenario)
        for profile in RESULT_PROFILES
        for scenario in RESULT_SCENARIOS
    }
    if pairs != expected_pairs or len(result_rows) != len(expected_pairs):
        raise ValueError("late result/save replay must cover normal/hard 28..31")

    fresh = manifest.get("fresh_result_and_ending_replay", {})
    if (
        fresh.get("profiles") != ["normal", "hard"]
        or set(fresh.get("scenarios", [])) != FRESH_PRE27_RESULT_SCENARIOS
        or fresh.get("profile_scenario_pairs") != 42
        or not fresh.get("source_summaries")
    ):
        raise ValueError("fresh result replay coverage changed")
    declared_pairs = set()
    for source in fresh["source_summaries"]:
        source_pairs = source_pair_set(source)
        allowed_failed = pair_set(source.get("allowed_failed_pairs", []))
        if not source_pairs or not allowed_failed <= source_pairs:
            raise ValueError("fresh result source contract changed")
        declared_pairs |= source_pairs
    expected_fresh_pairs = {
        (profile, scenario)
        for profile in RESULT_PROFILES
        for scenario in FRESH_PRE27_RESULT_SCENARIOS
    }
    if declared_pairs != expected_fresh_pairs:
        raise ValueError("fresh result source pairs are incomplete")

    carried = manifest.get("carried_result_and_save_regression", {})
    if (
        carried.get("profiles") != ["normal", "hard"]
        or set(carried.get("scenarios", [])) != CARRIED_RESULT_SCENARIOS
        or carried.get("profile_scenario_pairs") != 12
        or not carried.get("source_report")
    ):
        raise ValueError("carried result replay coverage changed")

    assertions = manifest.get("coverage_assertions", {})
    expected_assertions = {
        "first_turn_profile_scenario_pairs": 93,
        "preparation_profile_scenario_pairs": 62,
        "gray_acted_profile_scenario_pairs": 62,
        "late_result_profile_scenario_pairs": 8,
        "fresh_result_and_ending_profile_scenario_pairs": 50,
        "carried_result_profile_scenario_pairs": 12,
        "all_result_profile_scenario_pairs": 62,
    }
    if assertions != expected_assertions:
        raise ValueError("all-scenario coverage assertions changed")


def verify_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(manifest)

    verified_files = 0
    for row in manifest["first_turn_replay"]["profiles"]:
        combined: dict[int, str] = {}
        for source in row["source_summaries"]:
            source_path = verify_file(source)
            verified_files += 1
            report = json.loads(source_path.read_text(encoding="utf-8"))
            if report.get("profile") != row["profile"]:
                raise ValueError(f"first-turn profile mismatch in {source_path}")
            for result in report.get("scenarios", []):
                if result.get("status") == "pass":
                    combined[int(result["scenario"])] = str(result["endpoint"])
        if sorted(combined) != ALL_SCENARIOS:
            raise ValueError(f"{row['profile']} local first-turn evidence is incomplete")
        counts = dict(Counter(combined.values()))
        if counts != row["endpoint_counts"]:
            raise ValueError(f"{row['profile']} endpoint counts differ: {counts}")
        defeats = sorted(
            scenario
            for scenario, endpoint in combined.items()
            if endpoint == "defeat_return_title_turn_1"
        )
        if defeats != row["natural_defeat_scenarios"]:
            raise ValueError(f"{row['profile']} natural-defeat set differs")

    for row in manifest["full_surface_replay"]["component_reports"]:
        evidence_path = verify_file(row)
        verified_files += 1
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        kind = str(row["kind"])
        profile = str(row["profile"])
        if evidence.get("status") != "pass":
            raise ValueError(f"full-surface component failed: {evidence_path}")

        if kind in {"preparation", "gray_acted"}:
            if (
                evidence.get("profile") != profile
                or evidence.get("scenarios") != ALL_SCENARIOS
                or len(evidence.get("results", [])) != len(ALL_SCENARIOS)
                or any(
                    result.get("returncode") != 0
                    for result in evidence["results"]
                )
            ):
                raise ValueError(f"incomplete {kind} matrix: {evidence_path}")
        elif kind in {"preparation_scenario_identity", "battle_cache"}:
            if set(evidence.get("profiles", {})) != RESULT_PROFILES:
                raise ValueError(f"profile coverage changed: {evidence_path}")
            for profile_report in evidence["profiles"].values():
                if (
                    profile_report.get("passed_scenarios") != 31
                    or profile_report.get("total_scenarios") != 31
                ):
                    raise ValueError(f"scenario coverage changed: {evidence_path}")
        elif kind == "all_mercenary_hire":
            if (
                evidence.get("page_count") != 6
                or evidence.get("mercenary_count") != 16
                or len(evidence.get("pages", [])) != 6
            ):
                raise ValueError(f"mercenary coverage changed: {evidence_path}")
        elif kind in {"pike_acted", "monk_acted"}:
            expected_class = "파이크" if kind == "pike_acted" else "몽크"
            if (
                evidence.get("hired_class") != expected_class
                or evidence.get("coordinate_changed") is not True
                or evidence.get("ordinary_gray_cache_after_move", {}).get(
                    "all_match_stock_silhouette_expansion"
                )
                is not True
            ):
                raise ValueError(f"acted-sprite probe changed: {evidence_path}")
        elif kind == "shop_necklace":
            items = evidence.get("items", [])
            if (
                [(item.get("item_id"), item.get("label")) for item in items]
                != [(27, "크로스"), (28, "넥클리스")]
                or any(item.get("pixel_exact") is not True for item in items)
            ):
                raise ValueError(f"shop glyph evidence changed: {evidence_path}")

        if profile in RESULT_PROFILES and kind != "monk_acted":
            if evidence.get("rom", {}).get("sha256") != RELEASE_ROM_SHA256[profile]:
                raise ValueError(f"release ROM identity changed: {evidence_path}")

    for row in manifest["late_result_and_save_replay"]:
        evidence_path = verify_file(row)
        verified_files += 1
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if (
            evidence.get("status") != "pass"
            or evidence.get("profile") != row["profile"]
            or evidence.get("scenario") != row["scenario"]
            or evidence.get("battle_result_frame") != row["battle_result_frame"]
            or evidence.get("save_menu_frame") != row["save_menu_frame"]
            or evidence.get("rom", {}).get("sha256") != row["probe_rom_sha256"]
        ):
            raise ValueError(f"late result evidence differs in {evidence_path}")
        for key in ("battle_result", "save_menu"):
            verify_file(evidence[key])
            verified_files += 1

    fresh = manifest["fresh_result_and_ending_replay"]
    probe_path = verify_file(fresh["probe_manifest"])
    verified_files += 1
    probe_report = json.loads(probe_path.read_text(encoding="utf-8"))
    if (
        probe_report.get("status") != "pass"
        or probe_report.get("release_promoted") is not False
        or probe_report.get("version_bumped") is not False
        or {
            profile: probe_report.get("candidate_roms", {})
            .get(profile, {})
            .get("sha256")
            for profile in RESULT_PROFILES
        }
        != RELEASE_ROM_SHA256
    ):
        raise ValueError(f"fresh probe manifest changed: {probe_path}")
    probes = {
        (profile, int(probe["scenario"])): probe[profile]
        for probe in probe_report["probes"]
        for profile in RESULT_PROFILES
    }

    passed: dict[tuple[str, int], str] = {}
    for source in fresh["source_summaries"]:
        summary_path = verify_file(source)
        verified_files += 1
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        expected_source_pairs = source_pair_set(source)
        allowed_failed = pair_set(source.get("allowed_failed_pairs", []))
        actual_source_pairs = {
            (str(row["profile"]), int(row["scenario"]))
            for row in summary.get("results", [])
        }
        failed = {
            (str(row["profile"]), int(row["scenario"]))
            for row in summary.get("results", [])
            if row.get("returncode") != 0 or row.get("status") != "pass"
        }
        if (
            actual_source_pairs != expected_source_pairs
            or failed != allowed_failed
        ):
            raise ValueError(f"fresh result summary changed: {summary_path}")
        for result in summary["results"]:
            pair = (str(result["profile"]), int(result["scenario"]))
            if pair in failed:
                continue
            passed[pair] = verify_fresh_result_evidence(result, probes)
            verified_files += 1

    expected_fresh_pairs = {
        (profile, scenario)
        for profile in RESULT_PROFILES
        for scenario in FRESH_PRE27_RESULT_SCENARIOS
    }
    if set(passed) != expected_fresh_pairs:
        raise ValueError("fresh result evidence is incomplete")
    digest_payload = "\n".join(
        f"{profile}:{scenario}:{passed[(profile, scenario)]}"
        for profile, scenario in sorted(passed)
    ).encode()
    if hashlib.sha256(digest_payload).hexdigest() != fresh[
        "evidence_set_sha256"
    ]:
        raise ValueError("fresh result evidence-set digest changed")

    for discarded in fresh.get("discarded_attempts", []):
        discarded_path = verify_file(discarded)
        verified_files += 1
        discarded_report = json.loads(
            discarded_path.read_text(encoding="utf-8")
        )
        if discarded_report.get("status") != "fail":
            raise ValueError(f"discarded attempt unexpectedly passed: {discarded_path}")

    carried = manifest["carried_result_and_save_regression"]
    carried_path = verify_file(carried["source_report"])
    verified_files += 1
    carried_report = json.loads(carried_path.read_text(encoding="utf-8"))
    carried_pairs = {
        (str(row["profile"]), int(row["scenario"]))
        for row in carried_report.get("runs", [])
        if int(row["scenario"]) in CARRIED_RESULT_SCENARIOS
        and row.get("status") == "pass"
    }
    expected_carried_pairs = {
        (profile, scenario)
        for profile in RESULT_PROFILES
        for scenario in CARRIED_RESULT_SCENARIOS
    }
    if carried_report.get("status") != "pass" or carried_pairs != (
        expected_carried_pairs
    ):
        raise ValueError("carried result report changed")

    return {
        "status": "pass",
        "release": manifest["release"],
        "scenarios": len(ALL_SCENARIOS),
        "first_turn_profile_scenario_pairs": 93,
        "full_surface_profile_scenario_pairs": 62,
        "full_surface_component_reports": len(FULL_SURFACE_COMPONENTS),
        "late_result_profile_scenario_pairs": 8,
        "fresh_result_and_ending_profile_scenario_pairs": 50,
        "carried_result_profile_scenario_pairs": 12,
        "all_result_profile_scenario_pairs": 62,
        "verified_files": verified_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    print(json.dumps(verify_manifest(args.manifest), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
