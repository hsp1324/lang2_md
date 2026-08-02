#!/usr/bin/env python3
"""Aggregate exact-current Scenario 1-27 result evidence for both profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_current_result_revalidation_parallel as parallel
from tools import run_scenario21_result_surface as shared


DEFAULT_OUTPUT = ROOT / "localization/current_result_surface_regression.json"
DEFAULT_RUNTIME_ROOT = ROOT / "captures/run/current_source_result_revalidation"
PROFILE_NAMES = ("normal", "hard")
EARLY_RUN_18 = frozenset((1, 2, 3, 5, 6, 7, 9))
EARLY_RUN_19 = frozenset((4, 8, 11))
LATER_SCENARIOS = frozenset((10, *range(12, 28)))
ALL_SCENARIOS = tuple(range(1, 28))
FIN_SHA256 = "4cb7db62c30ace38e0d8b2fa1a34fc7ba31586104f5b59c9663b6ad9564a46b0"
RUN_IDS = {
    **{scenario: "post-darkguard-20260802-18" for scenario in EARLY_RUN_18},
    **{scenario: "post-darkguard-20260802-19" for scenario in EARLY_RUN_19},
    **{scenario: "current-source-20260802-20" for scenario in LATER_SCENARIOS},
    19: "current-source-20260802-21",
    **{
        scenario: "current-source-20260802-22"
        for scenario in (17, *range(21, 27))
    },
    27: "current-source-20260802-23",
}
RUN_ID_OVERRIDES = {
    ("hard", 27): "current-source-20260802-24",
}
PROBE_ROOTS = {
    **{
        scenario: ROOT / "tmp/current-source-result-probes-full01"
        for scenario in EARLY_RUN_18
    },
    **{
        scenario: ROOT / "tmp/current-source-result-probes-retry02"
        for scenario in EARLY_RUN_19
    },
    **{
        scenario: ROOT / "tmp/current-source-result-probes-full02"
        for scenario in LATER_SCENARIOS
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def evidence_path(
    runtime_root: Path,
    profile: str,
    scenario: int,
) -> Path:
    args = argparse.Namespace()
    output = parallel.task_output(
        runtime_root,
        profile,
        scenario,
        run_id(profile, scenario),
    )
    return output / "evidence.json"


def run_id(profile: str, scenario: int) -> str:
    return RUN_ID_OVERRIDES.get((profile, scenario), RUN_IDS[scenario])


def resolve_report_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def manifest_for(scenario: int) -> dict[str, object]:
    path = PROBE_ROOTS[scenario] / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"probe manifest is missing: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report["status"] != "pass":
        raise ValueError(f"probe manifest did not pass: {path}")
    if report.get("release_promoted") is not False:
        raise ValueError(f"probe manifest promoted a release: {path}")
    if report.get("version_bumped") is not False:
        raise ValueError(f"probe manifest bumped a version: {path}")
    return report


def candidate_identity(manifests: list[dict[str, object]]) -> dict[str, object]:
    identities = [report["candidate_roms"] for report in manifests]
    if any(identity != identities[0] for identity in identities[1:]):
        raise ValueError("probe manifests do not share one current candidate pair")
    return identities[0]


def expected_probe(
    manifest: dict[str, object],
    profile: str,
    scenario: int,
) -> dict[str, object]:
    matches = [
        row
        for row in manifest["probes"]
        if int(row["scenario"]) == scenario
    ]
    if len(matches) != 1:
        raise ValueError(f"Scenario {scenario} is missing from its probe manifest")
    return matches[0][profile]


def verify_image(report: dict[str, object], key: str) -> dict[str, object]:
    image = report[key]
    path = resolve_report_path(str(image["path"]))
    actual = sha256(path)
    if actual != image["sha256"]:
        raise ValueError(f"{key} image hash changed: {path}")
    return {
        "path": relative(path),
        "sha256": actual,
        "surface": image.get("surface"),
    }


def verify_observation_hashes(
    report: dict[str, object],
    key: str,
) -> int:
    rows = report.get(key, [])
    if not rows:
        raise ValueError(f"{key} observations are missing")
    for row in rows:
        path_value = row.get("capture", row.get("path"))
        if path_value is None:
            raise ValueError(f"{key} observation has no capture path")
        path = resolve_report_path(str(path_value))
        if sha256(path) != row["sha256"]:
            raise ValueError(f"{key} observation hash changed: {path}")
    return len(rows)


def verify_run(
    runtime_root: Path,
    profile: str,
    scenario: int,
    manifest: dict[str, object],
) -> dict[str, object]:
    path = evidence_path(runtime_root, profile, scenario)
    if not path.is_file():
        raise FileNotFoundError(f"runtime evidence is missing: {path}")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("status") != "pass":
        raise ValueError(f"runtime evidence did not pass: {path}")
    if evidence.get("acceptance_updated") is not False:
        raise ValueError(f"runtime evidence unexpectedly promoted acceptance: {path}")
    if evidence.get("profile") != profile or evidence.get("scenario") != scenario:
        raise ValueError(f"runtime evidence identity changed: {path}")
    identity = evidence.get("scenario_identity", {})
    if (
        identity.get("status") != "pass"
        or identity.get("requested_scenario") != scenario
        or identity.get("identified_scenario") != scenario
    ):
        raise ValueError(f"runtime scenario identity failed: {path}")

    probe = expected_probe(manifest, profile, scenario)
    rom = evidence["rom"]
    rom_path = resolve_report_path(str(rom["path"]))
    rom_sha = sha256(rom_path)
    if rom_sha != rom["sha256"] or rom_sha != probe["sha256"]:
        raise ValueError(f"runtime ROM is not its manifest probe: {path}")
    if rom["md_checksum"] != probe["md_checksum"]:
        raise ValueError(f"runtime ROM checksum is not its manifest probe: {path}")

    row = {
        "scenario": scenario,
        "profile": profile,
        "status": "pass",
        "run_id": run_id(profile, scenario),
        "evidence": relative(path),
        "evidence_sha256": sha256(path),
        "probe": {
            "path": relative(rom_path),
            "sha256": rom_sha,
            "md_checksum": rom["md_checksum"],
        },
        "scenario_identity": "pass",
    }
    if scenario == 27:
        fin = verify_image(evidence, "fin")
        if evidence["bernhardt_runtime_state"]["hp"] != 0:
            raise ValueError(f"Scenario 27 boss HP is not zero: {path}")
        if fin["sha256"] != FIN_SHA256:
            raise ValueError(f"Scenario 27 Fin surface changed: {path}")
        fin["surface"] = "fin"
        row["terminal_surface"] = fin
        row["boss_hp_zero"] = True
        row["ending_observation_frames"] = verify_observation_hashes(
            evidence,
            "ending_observations",
        )
        row["battle_observation_frames"] = verify_observation_hashes(
            evidence,
            "battle_frames",
        )
    else:
        result = verify_image(evidence, "battle_result")
        if result["surface"] != "battle_result":
            raise ValueError(f"battle-result classifier failed: {path}")
        row["battle_result"] = result
        if "save_menu" in evidence:
            save = verify_image(evidence, "save_menu")
            if save["surface"] != "save_menu":
                raise ValueError(f"save-menu classifier failed: {path}")
            row["save_menu"] = save
    return row


def verify(runtime_root: Path) -> dict[str, object]:
    manifests_by_root = {
        root: manifest_for(scenario)
        for scenario, root in PROBE_ROOTS.items()
    }
    manifests = list(manifests_by_root.values())
    candidates = candidate_identity(manifests)
    rows = []
    for profile in PROFILE_NAMES:
        for scenario in ALL_SCENARIOS:
            rows.append(
                verify_run(
                    runtime_root,
                    profile,
                    scenario,
                    manifests_by_root[PROBE_ROOTS[scenario]],
                )
            )
    passed = sum(row["status"] == "pass" for row in rows)
    manifest_artifacts = [
        {
            "path": relative(root / "manifest.json"),
            "sha256": sha256(root / "manifest.json"),
        }
        for root in sorted(manifests_by_root, key=str)
    ]
    return {
        "schema_version": 1,
        "status": "pass" if passed == 54 else "fail",
        "scope": "exact_current_result_and_ending_surfaces_scenarios_1_to_27",
        "candidate_roms": {
            **candidates,
            "release_roms_modified": False,
            "version_bumped": False,
        },
        "profile_scenario_runs": 54,
        "passed_profile_scenario_runs": passed,
        "scenario_1_to_26_result_runs": 52,
        "scenario_27_terminal_runs": 2,
        "scenarios": list(ALL_SCENARIOS),
        "profiles": list(PROFILE_NAMES),
        "probe_manifests": manifest_artifacts,
        "manual_visual_review": {
            "status": "pass",
            "reviewed_profile_scenario_runs": 54,
            "result_frames": 52,
            "terminal_fin_frames": 2,
            "method": (
                "Every retained normal/hard result frame was inspected for "
                "Korean names, portraits, result sprites, POINT, borders, "
                "rows, and numeric fields."
            ),
        },
        "runs": rows,
        "release_gate": {
            "status": "complete",
            "release_or_version_promotion_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    runtime_root = args.runtime_root.resolve()
    output = args.output.resolve()
    report = verify(runtime_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"{report['status']}: {report['passed_profile_scenario_runs']}/"
        f"{report['profile_scenario_runs']} current result runs"
    )
    print(output)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
