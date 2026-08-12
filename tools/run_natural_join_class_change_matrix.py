#!/usr/bin/env python3
# ruff: noqa: E402
"""Exercise natural join choices and legacy-save recovery on isolated Xvfb.

The result probes alter only the bounded scenario-completion setup.  Opening,
deployment, join/result callbacks, the production class-choice UI, class
application, runtime-to-roster synchronization, result pages, and save pages
remain owned by the candidate ROM.  Every case retains the candidate screen,
the immediate applied state, the battle result, and the next manual-save state.

BlastEm writes live SRAM to disk only when its process exits, while a GST made
at these result callbacks cannot safely resume the callback.  The runner
therefore proves the pending marker in a separate fresh run that stops at the
candidate screen, then performs another fresh, uninterrupted run through
candidate selection, application, battle result, and manual save.  The two
isolated runtime homes are hash-linked in the final evidence.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as builder
from tools import build_class_change_probe_rom as class_probe
from tools import build_current_result_probe_matrix as probe_matrix
from tools.class_change_data import transition_for_class
from tools import run_gray_acted_surface_matrix as gray
from tools import run_preparation_surface_matrix as preparation
from tools import run_preparation_surface_parallel as preparation_parallel
from tools import run_scenario01_09_result_surface as early_result
from tools import run_scenario10_result_surface as scenario10_result
from tools import run_scenario21_result_surface as shared_result
from tools.capture_class_change_application import (
    class_change_candidate_surface_visible,
)
from tools.run_sequential_campaign_revalidation import state_snapshot
from tools.verify_v134_release_regression import commander_runtime


PROFILES = ("pure", "normal", "hard")
EXECUTION_POLICY = (
    "independent_pending_exit_flush_then_fresh_continuous_full_flow"
)
DEFAULT_PROBE_ROOT = ROOT / "tmp/current-source-result-probes"
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/natural_join_class_change_matrix"
DEFAULT_RUNTIME_ROOT = ROOT / "tmp/natural_join_class_change_runtime"
# Restrict the fingerprint to the three text labels.  The former x=56 crop
# also included the animated class sprites, so the same Keith screen produced
# a different hash on another animation frame and was mistaken for a different
# commander's class choice.
CANDIDATE_LABEL_BOX = (84, 84, 138, 168)


@dataclass(frozen=True)
class CharacterSpec:
    slug: str
    name: str
    commander_id: int
    tier1_class: int
    initial_experience: int
    candidates: tuple[int, int, int]
    candidate_labels: tuple[str, str, str]
    label_fingerprint: str
    natural_scenario: int
    first_player_scenario: int


@dataclass(frozen=True)
class CaseSpec:
    slug: str
    group: str
    character: CharacterSpec
    scenario: int
    candidate_index: int
    selected_class: int
    legacy_level: int | None = None

    @property
    def next_scenario(self) -> int:
        return self.scenario + 1


KEITH = CharacterSpec(
    slug="keith",
    name="Keith",
    commander_id=7,
    tier1_class=0x06,
    initial_experience=5,
    candidates=(0x04, 0x2B, 0x08),
    candidate_labels=("로드", "호크로드", "힐러"),
    label_fingerprint=(
        "33823c42fbac2092b392b6e50932cadbde96a99e41f5dcf54421653060ed2b8e"
    ),
    natural_scenario=7,
    first_player_scenario=8,
)
LESTER = CharacterSpec(
    slug="lester",
    name="Lester",
    commander_id=9,
    tier1_class=0x07,
    initial_experience=15,
    candidates=(0x05, 0x2C, 0x0A),
    candidate_labels=("나이트", "크로코로드", "샤먼"),
    label_fingerprint=(
        "d36b1f8bbea07aad42e169027d3217044dbed7a599c42cbeffc0ee988fae46af"
    ),
    natural_scenario=10,
    first_player_scenario=11,
)
JESSICA = CharacterSpec(
    slug="jessica",
    name="Jessica",
    commander_id=10,
    tier1_class=0x03,
    initial_experience=0,
    candidates=(0x08, 0x09, 0x04),
    candidate_labels=("힐러", "소서러", "로드"),
    label_fingerprint=(
        "2116c10bfcfcde14f0be72565f46180f000e4c757644de42f95600198278e4d8"
    ),
    natural_scenario=11,
    first_player_scenario=12,
)
CHARACTERS = (KEITH, LESTER, JESSICA)

# Independent release acceptance values.  These deliberately do not import the
# production record values: the gate must catch a builder and test changing in
# lockstep.  Each amount is the cumulative raw EXP needed to reach the numeric
# level of the character's Japanese second-tier join row, excluding the
# partially filled residual bar (Keith LV1, Lester LV7, Jessica LV5).
EXPECTED_JOIN_RAW_EXPERIENCE = {
    KEITH.commander_id: 0x00,
    LESTER.commander_id: 0x90,
    JESSICA.commander_id: 0x60,
}
ORIGINAL_SECOND_TIER_JOIN = {
    KEITH.commander_id: {"class_id": 0x06, "level": 1, "residual_experience": 5},
    LESTER.commander_id: {"class_id": 0x07, "level": 7, "residual_experience": 15},
    JESSICA.commander_id: {"class_id": 0x09, "level": 5, "residual_experience": 0},
}
SRAM_START_ADDRESS = 0x00400001
SRAM_BYTES = 0x2000


NATURAL_CASES = (
    CaseSpec("natural-keith-default", "natural", KEITH, 7, 1, 0x04),
    CaseSpec("natural-keith-hawk-lord", "natural", KEITH, 7, 2, 0x2B),
    CaseSpec("natural-keith-healer", "natural", KEITH, 7, 3, 0x08),
    CaseSpec("natural-lester-default", "natural", LESTER, 10, 1, 0x05),
    CaseSpec("natural-lester-croco-lord", "natural", LESTER, 10, 2, 0x2C),
    CaseSpec("natural-lester-shaman", "natural", LESTER, 10, 3, 0x0A),
    CaseSpec("natural-jessica-default", "natural", JESSICA, 11, 1, 0x08),
    CaseSpec("natural-jessica-sorcerer", "natural", JESSICA, 11, 2, 0x09),
    CaseSpec("natural-jessica-lord", "natural", JESSICA, 11, 3, 0x04),
)
LEGACY_CASES = tuple(
    CaseSpec(
        f"legacy-{character.slug}-fighter-lv{level}",
        "legacy",
        character,
        character.natural_scenario,
        1,
        character.candidates[0],
        legacy_level=level,
    )
    for character in (KEITH, LESTER)
    for level in (10, 11, 12)
)
LEGACY_LATER_CASES = tuple(
    CaseSpec(
        f"legacy-later-{character.slug}-fighter-lv{level}",
        "legacy-later",
        character,
        character.first_player_scenario,
        1,
        character.candidates[0],
        legacy_level=level,
    )
    for character in (KEITH, LESTER)
    for level in (10, 11, 12)
)
ALL_CASES = (*NATURAL_CASES, *LEGACY_CASES, *LEGACY_LATER_CASES)
CASES_BY_SLUG = {case.slug: case for case in ALL_CASES}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_join_raw_experience(profile: str, commander_id: int) -> int:
    """Return the release contract, intentionally invariant by profile."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    try:
        return EXPECTED_JOIN_RAW_EXPERIENCE[commander_id]
    except KeyError as exc:
        raise ValueError(f"commander {commander_id} has no join EXP grant") from exc


def original_experience_basis(source: bytes) -> dict[str, object]:
    """Prove that the fixed grants exclude each original residual EXP bar."""
    rows = []
    for character in CHARACTERS:
        basis = ORIGINAL_SECOND_TIER_JOIN[character.commander_id]
        gauge = class_probe.class_change_experience(
            source, int(basis["class_id"])
        )
        calculated = (int(basis["level"]) - 1) * gauge
        expected = EXPECTED_JOIN_RAW_EXPERIENCE[character.commander_id]
        if calculated != expected:
            raise ValueError(
                f"{character.name} original numeric-level basis {calculated} "
                f"!= fixed raw grant {expected}"
            )
        rows.append(
            {
                "name": character.name,
                "commander_id": character.commander_id,
                "original_second_tier_class": f"0x{int(basis['class_id']):02X}",
                "original_second_tier_level": int(basis["level"]),
                "original_residual_experience_excluded": int(
                    basis["residual_experience"]
                ),
                "class_experience_gauge": gauge,
                "fixed_raw_experience": expected,
            }
        )
    return {
        "status": "pass",
        "policy": "numeric_level_cumulative_raw_excluding_residual_bar",
        "rows": rows,
    }


def progression_expectation(
    profile: str,
    case: CaseSpec,
    rom: bytes,
) -> dict[str, object]:
    """Model the finite grant through the selected class's real EXP gauge."""
    raw = expected_join_raw_experience(
        profile, case.character.commander_id
    )
    gauge = class_probe.class_change_experience(rom, case.selected_class)
    if gauge <= 0:
        raise ValueError(
            f"class 0x{case.selected_class:02X} has invalid EXP gauge {gauge}"
        )
    gained_levels, residual = divmod(raw, gauge)
    level = 1 + gained_levels
    reaches_another_choice = level >= 10
    next_candidates: list[int] = []
    if reaches_another_choice:
        next_candidates = list(
            transition_for_class(
                rom,
                case.character.commander_id,
                case.selected_class,
            ).candidates
        )
    return {
        "policy": "one_fixed_raw_grant_no_target_level_pump",
        "profile_invariant": True,
        "commander_id": case.character.commander_id,
        "selected_class": case.selected_class,
        "raw_experience": raw,
        "class_experience_gauge": gauge,
        "expected_result_class": case.selected_class,
        "expected_result_level": level,
        "expected_result_experience": residual,
        "reaches_another_class_choice": reaches_another_choice,
        "next_candidates": next_candidates,
    }


def validate_profile_invariant_wrappers(
    probe_manifest: dict[str, object],
    *,
    probe_root: Path,
    profiles: tuple[str, ...],
    scenarios: list[int],
) -> dict[str, object]:
    """Bind release and diagnostic ROMs to one profile-independent wrapper."""
    expected_wrapper = builder.build_join_class_choice_level_wrapper()
    wrapper_start = builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER
    wrapper_end = wrapper_start + len(expected_wrapper)
    expected_sha256 = hashlib.sha256(expected_wrapper).hexdigest()
    expected_grants = {
        str(commander_id): value
        for commander_id, value in EXPECTED_JOIN_RAW_EXPERIENCE.items()
    }
    builder_grants = {
        str(commander_id): builder.join_raw_experience(commander_id)
        for commander_id in EXPECTED_JOIN_RAW_EXPERIENCE
    }
    if builder_grants != expected_grants:
        raise ValueError(
            f"builder join raw grants {builder_grants} != release contract "
            f"{expected_grants}"
        )
    deprecated_fields = {
        "target_tier2_level",
        "join_level_bonus",
        "fixed_experience_by_class",
        "experience_policy",
    }
    stale = {
        commander_id: sorted(deprecated_fields & set(row))
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items()
        if deprecated_fields & set(row)
    }
    if stale:
        raise ValueError(f"target/class-specific EXP policy fields remain: {stale}")
    target_pump = bytes.fromhex("11 7C 00 FF 00 2F")
    if target_pump in expected_wrapper:
        raise ValueError("target-level EXP refill instruction remains in wrapper")

    profile_rows = []
    wrapper_hashes = set()
    candidates = probe_manifest["candidate_roms"]
    for profile in profiles:
        candidate = candidates[profile]
        candidate_path = resolve_manifest_path(candidate["path"])
        candidate_payload = candidate_path.read_bytes()
        release_wrapper = candidate_payload[wrapper_start:wrapper_end]
        if release_wrapper != expected_wrapper:
            raise ValueError(f"{profile} release join EXP wrapper differs")
        wrapper_hash = hashlib.sha256(release_wrapper).hexdigest()
        wrapper_hashes.add(wrapper_hash)
        probe_rows = []
        for scenario in scenarios:
            path = probe_path(probe_root, profile, scenario)
            payload = path.read_bytes()
            probe_wrapper = payload[wrapper_start:wrapper_end]
            if probe_wrapper != release_wrapper:
                raise ValueError(
                    f"{profile} Scenario {scenario} probe changed join EXP wrapper"
                )
            probe_rows.append(
                {
                    "scenario": scenario,
                    "path": relative(path),
                    "wrapper_sha256": hashlib.sha256(probe_wrapper).hexdigest(),
                    "byte_identical_to_release": True,
                }
            )
        profile_rows.append(
            {
                "profile": profile,
                "candidate_rom": {
                    "path": relative(candidate_path),
                    "sha256": sha256(candidate_path),
                },
                "wrapper_offset": f"0x{wrapper_start:06X}",
                "wrapper_size": len(expected_wrapper),
                "wrapper_sha256": wrapper_hash,
                "matches_current_builder": True,
                "raw_experience_by_commander": expected_grants,
                "probes": probe_rows,
            }
        )
    if len(wrapper_hashes) != 1:
        raise ValueError("join EXP wrapper is not byte-identical across profiles")
    return {
        "status": "pass",
        "policy": "profile_and_branch_invariant_one_time_raw_experience",
        "profile_invariant": True,
        "branch_invariant": True,
        "target_level_pump_absent": True,
        "class_specific_adjustment_absent": True,
        "raw_experience_by_commander": expected_grants,
        "expected_wrapper_sha256": expected_sha256,
        "profile_wrapper_sha256": next(iter(wrapper_hashes)),
        "profiles": profile_rows,
    }


def resolve_manifest_path(value: object) -> Path:
    path = Path(str(value))
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def runtime_sram_marker(
    runtime_home: Path,
    character: CharacterSpec,
    snapshot: Path | None = None,
) -> dict[str, object]:
    paths = sorted(runtime_home.rglob("save.sram"))
    if len(paths) != 1:
        raise ValueError(
            f"expected one isolated save.sram, found {len(paths)} under "
            f"{runtime_home}"
        )
    path = paths[0]
    payload = path.read_bytes()
    if len(payload) != SRAM_BYTES:
        raise ValueError(f"BlastEm SRAM size {len(payload)} != {SRAM_BYTES}")
    address = int(
        builder.JOIN_CLASS_CHOICE_RECORDS[character.commander_id][
            "active_marker_address"
        ]
    )
    if address < SRAM_START_ADDRESS or (address - SRAM_START_ADDRESS) % 2:
        raise ValueError(f"join marker is not an odd-addressed SRAM byte: {address:#x}")
    offset = (address - SRAM_START_ADDRESS) // 2
    evidence_path = path
    if snapshot is not None:
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(payload)
        evidence_path = snapshot
    return {
        "path": relative(evidence_path),
        "sha256": sha256(evidence_path),
        "bytes": len(payload),
        "source_path": relative(path),
        "address": f"0x{address:08X}",
        "sram_offset": f"0x{offset:04X}",
        "value": payload[offset],
    }


def flush_sram_checkpoint(
    recorder: preparation.RuntimeRecorder,
    character: CharacterSpec,
    snapshot: Path,
    expected_marker: int,
) -> dict[str, object]:
    """Terminate the isolated emulator and verify its newly flushed SRAM."""
    preparation.terminate_blastem_processes(display=recorder.display)
    marker = runtime_sram_marker(
        recorder.runtime_home,
        character,
        snapshot,
    )
    if marker["value"] != expected_marker:
        raise ValueError(
            f"{character.name} flushed join marker {marker['value']:#04x} "
            f"!= {expected_marker:#04x}: {marker}"
        )
    return {
        "status": "pass",
        "policy": "process_exit_flush",
        "flushed_marker": marker,
        "expected_marker": expected_marker,
    }


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def candidate_label_fingerprint(path: Path) -> str:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    if image.size != (320, 240):
        raise ValueError(f"candidate capture must be 320x240: {path}")
    crop = image.crop(CANDIDATE_LABEL_BOX)
    mask = bytes(
        1 if red > 150 and green > 150 and blue > 150 else 0
        for red, green, blue in crop.getdata()
    )
    return hashlib.sha256(mask).hexdigest()


def legacy_recovery_eligible(
    character: CharacterSpec,
    *,
    scenario: int,
    result_next_scenario: int | None = None,
    x: int,
    y: int,
    class_id: int,
    level: int,
) -> bool:
    """Mirror the bounded production recovery truth table for tests/plans."""
    effective_scenario = (
        scenario if result_next_scenario is None else result_next_scenario
    )
    return (
        character in (KEITH, LESTER)
        and class_id == 0x01
        and level >= 10
        and effective_scenario >= character.first_player_scenario
        and x != 0xFF
        and y != 0xFF
        and (x != 0 or y != 0)
    )


def effective_recovery_scenario(case: CaseSpec) -> int:
    """Return the scenario marker visible to the result-time recovery hook."""
    if case.group == "legacy":
        return case.next_scenario
    return case.scenario


def selected_cases(
    groups: tuple[str, ...],
    case_ids: tuple[str, ...] | None = None,
) -> tuple[CaseSpec, ...]:
    cases = tuple(case for case in ALL_CASES if case.group in groups)
    if case_ids is None:
        return cases
    unknown = sorted(set(case_ids) - set(CASES_BY_SLUG))
    if unknown:
        raise ValueError("unknown case IDs: " + ", ".join(unknown))
    selected = tuple(case for case in cases if case.slug in case_ids)
    missing_group = sorted(set(case_ids) - {case.slug for case in selected})
    if missing_group:
        raise ValueError(
            "case IDs excluded by --case-groups: " + ", ".join(missing_group)
        )
    return selected


def legacy_manual_slot_args(case: CaseSpec) -> list[str] | None:
    if case.legacy_level is None:
        return None
    character = case.character
    return [
        "--manual-slot-commander-id",
        str(character.commander_id),
        "--manual-slot-level",
        str(case.legacy_level),
        "--manual-slot-experience",
        str(character.initial_experience),
        "--manual-slot-expected-class",
        f"0x{character.tier1_class:02X}",
        "--manual-slot-class",
        "0x01",
    ]


def legacy_diagnostic_exact_overrides(
    case: CaseSpec,
) -> dict[tuple[int, int], dict[str, int]] | None:
    """Declare the exact impossible fixed-record state injected by a probe."""
    if case.group != "legacy" or case.legacy_level is None:
        return None
    fixed_record = {KEITH.commander_id: 3, LESTER.commander_id: 1}.get(
        case.character.commander_id
    )
    if fixed_record is None:
        raise ValueError(f"unsupported legacy diagnostic case: {case.slug}")
    return {
        (case.scenario, fixed_record): {
            "name_id": case.character.commander_id,
            "class_id": 0x01,
            "level": case.legacy_level,
        }
    }


def diagnostic_override_report(case: CaseSpec) -> list[dict[str, int]]:
    overrides = legacy_diagnostic_exact_overrides(case) or {}
    return [
        {
            "scenario": scenario,
            "fixed_record_index": record,
            **values,
        }
        for (scenario, record), values in overrides.items()
    ]


def commander_row(snapshot: dict[str, object], commander_id: int) -> dict[str, int]:
    rows = [
        row
        for row in snapshot["commanders"]
        if int(row["commander_id"]) == commander_id
    ]
    if len(rows) != 1:
        raise ValueError(
            f"serialized state has {len(rows)} commander {commander_id} rows"
        )
    return rows[0]


def validate_fresh_seed(snapshot: dict[str, object]) -> None:
    if snapshot["scenario"] != 1:
        raise ValueError(f"fresh seed is Scenario {snapshot['scenario']}, not 1")
    for character in CHARACTERS:
        row = commander_row(snapshot, character.commander_id)
        actual = (row["class_id"], row["level"], row["experience"])
        expected = (character.tier1_class, 10, character.initial_experience)
        if actual != expected:
            raise ValueError(
                f"fresh seed {character.name} is class/LV/EXP {actual}, "
                f"expected {expected}"
            )


def validate_candidate_runtime(case: CaseSpec, runtime: dict[str, int]) -> None:
    """Require the live join boundary without constraining result-awarded EXP.

    The fresh roster and pre-completion state retain each character's source
    residual EXP.  The stock scenario-result handler can add EXP before it
    opens the LV10 class-choice screen (Scenario 7 adds ten to Keith), so that
    pre-choice byte is not the join grant being tested here.  The pending A5
    marker below proves ownership of the one-time post-selection grant.  The
    immediate state is checked as one valid stock settlement step, and the
    exact final class/LV/EXP tuple is required at result and save.
    """
    character = case.character
    if (
        runtime["class_id"] != character.tier1_class
        or runtime["level"] != 10
        or runtime["x"] == 0xFF
        or runtime["y"] == 0xFF
        or (runtime["x"] == 0 and runtime["y"] == 0)
    ):
        raise ValueError(
            f"{character.name} candidate runtime is not visible tier1 "
            f"LV10: {runtime}"
        )


def expected_result_tuple(expectation: dict[str, object]) -> tuple[int, int, int]:
    return (
        int(expectation["expected_result_class"]),
        int(expectation["expected_result_level"]),
        int(expectation["expected_result_experience"]),
    )


def validate_applied_runtime(
    case: CaseSpec,
    runtime: dict[str, int],
    expectation: dict[str, object],
) -> dict[str, object]:
    """Validate one stock EXP-settlement step after the class selection.

    The continuation writes the complete finite raw grant once, but the stock
    result state machine consumes at most one class-gauge chunk per scan.  A
    capture taken immediately after pressing C can therefore observe a valid
    intermediate state such as Knight LV2/EXP112 on the way to LV5/EXP16.
    The later battle-result and serialized-save checks still require the exact
    final tuple.
    """
    actual = (runtime["class_id"], runtime["level"], runtime["experience"])
    expected = expected_result_tuple(expectation)
    selected_class = int(expectation["selected_class"])
    raw_experience = int(expectation["raw_experience"])
    gauge = int(expectation["class_experience_gauge"])
    level = runtime["level"]
    experience = runtime["experience"]
    minimum_observable_level = 2 if raw_experience >= gauge else 1
    if (
        runtime["class_id"] != selected_class
        or not minimum_observable_level <= level <= expected[1]
    ):
        raise ValueError(
            f"{case.slug} immediate application mismatch: {runtime}, "
            f"expected a settling state for class/LV/EXP {expected} "
            "after the mandatory stock scan of one raw grant"
        )
    consumed = (level - 1) * gauge
    remaining = raw_experience - consumed
    if remaining < 0 or experience != remaining:
        raise ValueError(
            f"{case.slug} immediate application mismatch: {runtime}, "
            f"raw EXP {raw_experience} with gauge {gauge} requires "
            f"LV{level}/EXP{remaining}"
        )
    settled = actual == expected
    if level == expected[1] and not settled:
        raise ValueError(
            f"{case.slug} immediate application mismatch: {runtime}, "
            f"final class/LV/EXP must be {expected}"
        )
    return {
        "status": "settled" if settled else "settling",
        "stock_scan_consumption": True,
        "selected_class": selected_class,
        "raw_experience": raw_experience,
        "class_experience_gauge": gauge,
        "consumed_raw_experience": consumed,
        "remaining_raw_experience": remaining,
        "expected_final": {
            "class_id": expected[0],
            "level": expected[1],
            "experience": expected[2],
        },
    }


def validate_result_runtime(
    case: CaseSpec,
    runtime: dict[str, int],
    expectation: dict[str, object],
) -> None:
    expected = expected_result_tuple(expectation)
    actual = (
        runtime["class_id"],
        runtime["level"],
        runtime["experience"],
    )
    if actual != expected:
        raise ValueError(f"{case.slug} result {actual} != expected {expected}")


def validate_save_persistence(
    case: CaseSpec,
    snapshot: dict[str, object],
    expectation: dict[str, object],
) -> None:
    if snapshot["scenario"] != case.next_scenario:
        raise ValueError(
            f"{case.slug} save scenario {snapshot['scenario']} != {case.next_scenario}"
        )
    row = commander_row(snapshot, case.character.commander_id)
    expected = expected_result_tuple(expectation)
    actual = (row["class_id"], row["level"], row["experience"])
    if actual != expected:
        raise ValueError(f"{case.slug} serialized {actual} != expected {expected}")


def probe_path(probe_root: Path, profile: str, scenario: int) -> Path:
    definition = probe_matrix.PROBE_DEFINITIONS[scenario]
    return probe_root / profile / str(definition["filename"])


def verify_probe_manifest(
    probe_root: Path,
    profiles: tuple[str, ...],
    cases: tuple[CaseSpec, ...],
) -> dict[str, object]:
    path = probe_root / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("status") != "pass":
        raise ValueError("probe manifest is not passing")
    rows = {int(row["scenario"]): row for row in manifest["probes"]}
    scenarios = sorted({case.scenario for case in cases})
    conflicts = []
    for profile in profiles:
        candidate = manifest["candidate_roms"][profile]
        candidate_path = resolve_manifest_path(candidate["path"])
        if (
            not candidate_path.is_file()
            or sha256(candidate_path) != candidate["sha256"]
        ):
            raise ValueError(f"{profile} candidate ROM does not match probe manifest")
        for scenario in scenarios:
            if scenario not in rows:
                raise ValueError(f"probe manifest is missing Scenario {scenario}")
            expected_path = probe_path(probe_root, profile, scenario)
            record = rows[scenario][profile]
            if not expected_path.is_file() or sha256(expected_path) != record["sha256"]:
                raise ValueError(
                    f"{profile} Scenario {scenario} probe does not match manifest"
                )
            if profile == "hard" and rows[scenario].get(
                "hard_candidate_conflicts_inside_diagnostic_delta", 0
            ):
                conflicts.append(
                    {
                        "scenario": scenario,
                        "bytes": rows[scenario][
                            "hard_candidate_conflicts_inside_diagnostic_delta"
                        ],
                    }
                )
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "candidate_roms": manifest["candidate_roms"],
        "scenarios": scenarios,
        "hard_diagnostic_conflicts": conflicts,
    }


def trigger_scenario10(
    recorder: preparation.RuntimeRecorder,
) -> tuple[dict[str, object], Path]:
    recorder.send(["b"], delay=0.8)
    recorder.send(["start"], delay=1.0)
    start_menu = recorder.capture("battle/runtime_clear_start_menu.png")
    clear_gst = recorder.save_gst("states/runtime_clear_start_menu.gst")
    clear_state = scenario10_result.runtime_clear_state(clear_gst)
    if not clear_state["all_monsters_defeated"]:
        raise RuntimeError("Scenario 10 Start wrapper did not clear every monster")
    recorder.send(["b"], delay=0.8)
    recorder.send(["start"], delay=1.0)
    recorder.send(["down", "down", "down", "down"], delay=0.55)
    recorder.send(["c"], delay=1.4)
    return (
        {
            "mode": "runtime_end_turn",
            "start_menu": shared_result.image_report(start_menu),
            "clear_state": clear_state,
        },
        clear_gst,
    )


def trigger_scenario11(
    recorder: preparation.RuntimeRecorder,
) -> tuple[dict[str, object], Path]:
    recorder.send(["b"], delay=0.7)
    recorder.send(["start"], delay=1.0)
    start_capture = recorder.capture("battle/completion_start_menu.png")
    start_gst = recorder.save_gst("states/pre_final_attack.gst")
    recorder.send(["b"], delay=0.7)
    recorder.send(["c"], delay=0.7)

    # The stock opening settles on Lester. Close that menu and cycle to Sherry.
    recorder.send(["b:0.5", "a:0.5", "a:0.5", "a:0.5", "c:0.5"])
    recorder.send(["down:0.5", "c:0.6", "right:0.5"])
    target = recorder.capture("battle/final_reinforcement_target.png")
    recorder.send(["c"], delay=1.4)
    combat = recorder.capture("battle/final_reinforcement_combat.png")
    return (
        {
            "mode": "actual_final_reinforcement_attack",
            "start_menu": shared_result.image_report(start_capture),
            "target": shared_result.image_report(target),
            "combat": shared_result.image_report(combat),
        },
        start_gst,
    )


def trigger_completion(
    recorder: preparation.RuntimeRecorder,
    scenario: int,
) -> tuple[dict[str, object], Path]:
    if scenario in (7, 8):
        report = early_result.trigger_completion(
            recorder, early_result.SCENARIOS[scenario]
        )
        return report, recorder.output / "states/runtime_clear_start_menu.gst"
    if scenario == 10:
        return trigger_scenario10(recorder)
    if scenario == 11:
        return trigger_scenario11(recorder)
    raise ValueError(f"unsupported join matrix scenario {scenario}")


def case_output(
    output_root: Path,
    profile: str,
    case: CaseSpec,
    run_id: str,
    attempt: int,
    *,
    pending_only: bool,
) -> Path:
    phase = "pending-probe" if pending_only else "full-flow"
    return output_root / profile / case.slug / run_id / phase / f"attempt-{attempt}"


def pending_probe_key(case: CaseSpec) -> str:
    """Identify one genuinely identical pre-choice setup.

    Natural branches differ only after the shared candidate screen, so their
    pending-marker proof may be shared per character.  Legacy diagnostics
    retain their scenario and serialized Fighter level in the key.
    """
    if case.group == "natural":
        return f"natural:{case.character.slug}"
    return (
        f"{case.group}:{case.character.slug}:s{case.scenario}:"
        f"lv{case.legacy_level}"
    )


def pending_probe_representatives(
    cases: tuple[CaseSpec, ...],
) -> tuple[tuple[str, CaseSpec], ...]:
    representatives: dict[str, CaseSpec] = {}
    for case in cases:
        representatives.setdefault(pending_probe_key(case), case)
    return tuple(representatives.items())


def run_case(
    args: argparse.Namespace,
    profile: str,
    case: CaseSpec,
    display: str,
    attempt: int,
    *,
    pending_only: bool,
    pending_probe_reference: dict[str, object] | None = None,
) -> dict[str, object]:
    if not pending_only and pending_probe_reference is None:
        raise ValueError(f"{case.slug} full flow has no pending-marker proof")
    output = case_output(
        args.output_root,
        profile,
        case,
        args.run_id,
        attempt,
        pending_only=pending_only,
    )
    output.mkdir(parents=True)
    phase = "pending" if pending_only else "full"
    runtime_name = (
        f"join-{phase}-{profile}-{case.slug}-{args.run_id}-a{attempt}"
    )
    recorder = preparation.RuntimeRecorder(
        output, display, args.runtime_root / runtime_name
    )
    rom = probe_path(args.probe_root, profile, case.scenario)
    seed = args.seed_gsts[profile]
    expectation = args.progression_expectations[(profile, case.slug)]
    started = time.monotonic()
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "running",
        "phase": "pending_marker_probe" if pending_only else "full_flow",
        "run_id": args.run_id,
        "execution_policy": EXECUTION_POLICY,
        "pending_probe_key": pending_probe_key(case),
        "profile": profile,
        "case": case.slug,
        "group": case.group,
        "scenario": case.scenario,
        "next_scenario": case.next_scenario,
        "effective_recovery_scenario": effective_recovery_scenario(case),
        "attempt": attempt,
        "display": display,
        "virtual_display": True,
        "runtime_name": runtime_name,
        "runtime_isolation": {
            "policy": "replace_existing_named_home_before_launch",
            "runtime_home": relative(recorder.runtime_home),
            "phase_unique": True,
        },
        "evidence_path": relative(output / "evidence.json"),
        "probe": {"path": relative(rom), "sha256": sha256(rom)},
        "seed": {"path": relative(seed), "sha256": sha256(seed)},
        "character": {
            "name": case.character.name,
            "commander_id": case.character.commander_id,
            "tier1_class": case.character.tier1_class,
            "candidate_classes": list(case.character.candidates),
            "candidate_labels": list(case.character.candidate_labels),
            "candidate_label_fingerprint": case.character.label_fingerprint,
        },
        "selection": {
            "candidate_index": case.candidate_index,
            "selected_class": case.selected_class,
        },
        "join_experience": {
            "policy": "one_fixed_raw_grant_no_target_level_pump",
            "profile_invariant": True,
            "branch_invariant": True,
            "raw_experience": expected_join_raw_experience(
                profile, case.character.commander_id
            ),
        },
        "progression_expectation": expectation,
        "legacy_level": case.legacy_level,
        "diagnostic_exact_overrides_requested": diagnostic_override_report(case),
    }
    if not pending_only:
        report["pending_marker_probe"] = pending_probe_reference
    try:
        identity = preparation.launch_to_preparation(
            recorder,
            rom,
            seed,
            case.scenario,
            runtime_name,
            output,
            manual_slot_args=legacy_manual_slot_args(case),
            diagnostic_exact_overrides=legacy_diagnostic_exact_overrides(case),
        )
        report["scenario_identity"] = identity
        prep_capture = recorder.capture("preparation.png")
        prep_gst = recorder.save_gst("states/preparation.gst")
        prep_snapshot = state_snapshot(prep_gst)
        prep_row = commander_row(prep_snapshot, case.character.commander_id)
        if case.legacy_level is not None:
            if prep_row["class_id"] != 0x01 or prep_row["level"] != case.legacy_level:
                raise ValueError(
                    f"legacy seed override did not reach preparation: {prep_row}"
                )
        report["preparation"] = {
            "capture": shared_result.image_report(prep_capture),
            "gst": relative(prep_gst),
            "gst_sha256": sha256(prep_gst),
            "serialized_commander": prep_row,
        }

        gray.enter_battle_command(recorder, rom, output)
        completion, pre_completion_gst = trigger_completion(recorder, case.scenario)
        report["completion"] = completion
        initial_runtime = commander_runtime(
            pre_completion_gst, case.character.commander_id
        )
        if case.legacy_level is None:
            expected_initial = (
                case.character.tier1_class,
                10,
                case.character.initial_experience,
            )
        else:
            expected_initial = (
                0x01,
                case.legacy_level,
                case.character.initial_experience,
            )
        if (
            initial_runtime["class_id"],
            initial_runtime["level"],
            initial_runtime["experience"],
        ) != expected_initial:
            raise ValueError(
                f"{case.slug} pre-completion runtime {initial_runtime} "
                f"!= class/LV/EXP {expected_initial}"
            )
        report["pre_completion"] = {
            "gst": relative(pre_completion_gst),
            "gst_sha256": sha256(pre_completion_gst),
            "runtime": initial_runtime,
        }

        observations = []
        skipped_candidates = []
        candidate_seen = False
        for frame in range(1, args.max_result_frames + 1):
            time.sleep(args.settle_delay)
            capture = recorder.capture(f"aftermath/advance_{frame:03d}.png")
            surface = shared_result.result_surface.classify_surface(capture)
            observation = {
                "frame": frame,
                "surface": surface,
                "capture": relative(capture),
                "sha256": sha256(capture),
            }
            observations.append(observation)

            if surface == "battle_result":
                if not candidate_seen:
                    raise RuntimeError(
                        f"{case.character.name} candidate screen was not observed"
                    )
                result_capture = output / "aftermath/battle_result.png"
                shutil.copy2(capture, result_capture)
                result_gst = recorder.save_gst("states/battle_result.gst")
                result_runtime = commander_runtime(
                    result_gst, case.character.commander_id
                )
                validate_result_runtime(case, result_runtime, expectation)
                report["battle_result"] = {
                    "frame": frame,
                    "capture": shared_result.image_report(result_capture),
                    "gst": relative(result_gst),
                    "gst_sha256": sha256(result_gst),
                    "runtime": result_runtime,
                    "continuous_from_applied_state": True,
                }
                break
            if surface == "save_menu":
                raise RuntimeError("save menu appeared before battle-result retention")

            if class_change_candidate_surface_visible(capture):
                fingerprint = candidate_label_fingerprint(capture)
                if fingerprint == case.character.label_fingerprint:
                    if candidate_seen:
                        raise RuntimeError(
                            f"duplicate {case.character.name} candidate screen"
                        )
                    candidate_gst = recorder.save_gst(
                        f"states/candidate_seen_{frame:03d}.gst"
                    )
                    candidate_runtime = commander_runtime(
                        candidate_gst, case.character.commander_id
                    )
                    validate_candidate_runtime(case, candidate_runtime)
                    candidate_report = {
                        "frame": frame,
                        "capture": shared_result.image_report(capture),
                        "label_fingerprint": fingerprint,
                        "labels": list(case.character.candidate_labels),
                        "gst": relative(candidate_gst),
                        "gst_sha256": sha256(candidate_gst),
                        "runtime": candidate_runtime,
                    }
                    if pending_only:
                        pending_flush = flush_sram_checkpoint(
                            recorder,
                            case.character,
                            output / f"states/pending_marker_{frame:03d}.sram",
                            builder.JOIN_CLASS_CHOICE_PENDING_MARKER,
                        )
                        candidate_report["pending_join_marker"] = pending_flush[
                            "flushed_marker"
                        ]
                        candidate_report["pending_flush"] = pending_flush
                        report["candidate"] = candidate_report
                        report["observations"] = observations
                        report["elapsed_seconds"] = round(
                            time.monotonic() - started,
                            3,
                        )
                        report["status"] = "pass"
                        (output / "evidence.json").write_text(
                            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )
                        return report

                    candidate_report["continuous_to_applied_state"] = True
                    for _ in range(case.candidate_index - 1):
                        recorder.send(["down"], delay=0.75)
                    selected_capture = recorder.capture(
                        "aftermath/selected_candidate.png"
                    )
                    if (
                        candidate_label_fingerprint(selected_capture)
                        != case.character.label_fingerprint
                    ):
                        raise RuntimeError("candidate labels changed during navigation")
                    candidate_report["selected_capture"] = shared_result.image_report(
                        selected_capture
                    )
                    report["candidate"] = candidate_report

                    recorder.send(["c"], delay=1.0)
                    applied_capture = recorder.capture(
                        "aftermath/applied_immediate.png"
                    )
                    applied_gst = recorder.save_gst("states/applied_immediate.gst")
                    applied_runtime = commander_runtime(
                        applied_gst, case.character.commander_id
                    )
                    applied_progression = validate_applied_runtime(
                        case, applied_runtime, expectation
                    )
                    report["applied_immediate"] = {
                        "capture": shared_result.image_report(applied_capture),
                        "gst": relative(applied_gst),
                        "gst_sha256": sha256(applied_gst),
                        "runtime": applied_runtime,
                        "progression_settlement": applied_progression,
                        "continuous_to_battle_result": True,
                    }
                    candidate_seen = True
                    continue

                skipped_gst = recorder.save_gst(
                    f"states/skipped_candidate_{frame:03d}.gst"
                )
                target_runtime = commander_runtime(
                    skipped_gst, case.character.commander_id
                )
                if candidate_seen:
                    validate_result_runtime(case, target_runtime, expectation)
                skipped_candidates.append(
                    {
                        **observation,
                        "label_fingerprint": fingerprint,
                        "gst": relative(skipped_gst),
                        "gst_sha256": sha256(skipped_gst),
                        "target_runtime": target_runtime,
                        "confirmed_not_target_followup": candidate_seen,
                    }
                )
                recorder.send(["c"], delay=0.45)
                continue

            recorder.send(["c"], delay=0.45)
        else:
            raise RuntimeError("battle result was not reached")

        recorder.send(["c"], delay=0.8)
        save_source, save_frame = shared_result.wait_for_save_menu(
            recorder,
            max_frames=args.max_save_frames,
            settle_delay=args.save_settle_delay,
        )
        save_capture = output / "save/save_menu.png"
        shutil.copy2(save_source, save_capture)
        save_gst = recorder.save_gst("states/save_menu.gst")
        save_snapshot = state_snapshot(save_gst)
        validate_save_persistence(case, save_snapshot, expectation)
        save_runtime = commander_runtime(save_gst, case.character.commander_id)
        validate_result_runtime(case, save_runtime, expectation)
        save_flush = flush_sram_checkpoint(
            recorder,
            case.character,
            output / "states/save_marker.sram",
            0,
        )
        save_marker = save_flush["flushed_marker"]
        report["save_menu"] = {
            "frame": save_frame,
            "capture": shared_result.image_report(save_capture),
            "gst": relative(save_gst),
            "gst_sha256": sha256(save_gst),
            "record_sha256": save_snapshot["record_sha256"],
            "scenario": save_snapshot["scenario"],
            "runtime": save_runtime,
            "serialized_commander": commander_row(
                save_snapshot, case.character.commander_id
            ),
            "consumed_join_marker": save_marker,
            "consumed_flush": save_flush,
            "continuous_from_battle_result": True,
        }
        report["skipped_other_candidate_screens"] = skipped_candidates
        report["observations"] = observations
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["status"] = "pass"
        (output / "evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    except Exception as exc:
        failure_gst = None
        try:
            path = recorder.save_gst("states/failure.gst")
            failure_gst = {"path": relative(path), "sha256": sha256(path)}
        except Exception:
            pass
        report.update(
            {
                "status": "failed_attempt",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "failure_gst": failure_gst,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )
        (output / "failure.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    finally:
        preparation.terminate_blastem_processes(display=display)


def run_profile(
    args: argparse.Namespace,
    profile: str,
    display: str,
) -> dict[str, object]:
    def run_attempts(
        case: CaseSpec,
        *,
        pending_only: bool,
        pending_reference: dict[str, object] | None = None,
    ) -> dict[str, object]:
        attempts = []
        passed = None
        for attempt in range(1, args.attempts + 1):
            row = run_case(
                args,
                profile,
                case,
                display,
                attempt,
                pending_only=pending_only,
                pending_probe_reference=pending_reference,
            )
            attempts.append(
                {
                    "attempt": attempt,
                    "status": row["status"],
                    "error": row.get("error"),
                }
            )
            if row["status"] == "pass":
                passed = row
                break
        selected = passed if passed is not None else row
        selected["attempt_history"] = attempts
        evidence_path = resolve_manifest_path(selected["evidence_path"])
        if evidence_path.is_file():
            selected["evidence_sha256"] = sha256(evidence_path)
        return selected

    pending_rows = []
    pending_references: dict[str, dict[str, object]] = {}
    for key, case in pending_probe_representatives(args.cases):
        selected = run_attempts(case, pending_only=True)
        pending_rows.append(selected)
        print(
            f"{profile} pending {key}: {selected['status']}",
            flush=True,
        )
        if selected["status"] != "pass":
            continue
        evidence_path = resolve_manifest_path(selected["evidence_path"])
        candidate = selected["candidate"]
        pending_references[key] = {
            "status": "pass",
            "run_id": selected["run_id"],
            "pending_probe_key": key,
            "profile": profile,
            "case": selected["case"],
            "scenario": selected["scenario"],
            "legacy_level": selected["legacy_level"],
            "runtime_name": selected["runtime_name"],
            "evidence_path": selected["evidence_path"],
            "evidence_sha256": sha256(evidence_path),
            "probe": selected["probe"],
            "seed": selected["seed"],
            "candidate_gst": candidate["gst"],
            "candidate_gst_sha256": candidate["gst_sha256"],
            "pending_marker": candidate["pending_join_marker"],
        }

    if len(pending_references) != len(pending_rows):
        return {
            "profile": profile,
            "display": display,
            "status": "fail",
            "passed_pending_probes": len(pending_references),
            "total_pending_probes": len(pending_rows),
            "pending_marker_probes": pending_rows,
            "passed_cases": 0,
            "total_cases": len(args.cases),
            "results": [],
        }

    rows = []
    for case in args.cases:
        key = pending_probe_key(case)
        selected = run_attempts(
            case,
            pending_only=False,
            pending_reference=pending_references[key],
        )
        rows.append(selected)
        print(f"{profile} full {case.slug}: {selected['status']}", flush=True)

    return {
        "profile": profile,
        "display": display,
        "status": "pass" if all(row["status"] == "pass" for row in rows) else "fail",
        "passed_pending_probes": len(pending_references),
        "total_pending_probes": len(pending_rows),
        "pending_marker_probes": pending_rows,
        "passed_cases": sum(row["status"] == "pass" for row in rows),
        "total_cases": len(rows),
        "results": rows,
    }


def run_all(args: argparse.Namespace) -> dict[str, object]:
    displays = {
        profile: f":{args.display_base + index}"
        for index, profile in enumerate(args.profiles)
    }
    xvfb_processes = {}
    reports = []
    started = time.monotonic()
    try:
        for profile, display in displays.items():
            xvfb_processes[profile] = preparation_parallel.start_xvfb(
                args.xvfb, args.xvfb_library_path, display
            )
        with ThreadPoolExecutor(max_workers=len(args.profiles)) as executor:
            futures = {
                executor.submit(run_profile, args, profile, displays[profile]): profile
                for profile in args.profiles
            }
            for future in as_completed(futures):
                profile = futures[future]
                try:
                    reports.append(future.result())
                except Exception as exc:
                    reports.append(
                        {
                            "profile": profile,
                            "status": "orchestrator_error",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
    finally:
        for process in xvfb_processes.values():
            preparation_parallel.stop_process(process)
    reports.sort(key=lambda row: args.profiles.index(str(row["profile"])))
    passed = sum(row.get("status") == "pass" for row in reports)
    return {
        "schema_version": 1,
        "status": "pass" if passed == len(args.profiles) else "fail",
        "run_id": args.run_id,
        "profiles": list(args.profiles),
        "case_groups": list(args.case_groups),
        "cases": [case.slug for case in args.cases],
        "virtual_displays": displays,
        "maximum_simultaneous_emulators": len(args.profiles),
        "execution_policy": EXECUTION_POLICY,
        "probe_manifest": args.probe_manifest,
        "original_experience_basis": args.original_experience_basis,
        "production_experience_policy": args.production_experience_policy,
        "passed_profiles": passed,
        "total_profiles": len(args.profiles),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "results": reports,
    }


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    tasks = []
    pending_tasks = []
    for profile in args.profiles:
        for key, case in pending_probe_representatives(args.cases):
            pending_tasks.append(
                {
                    "phase": "pending_marker_probe",
                    "pending_probe_key": key,
                    "profile": profile,
                    "representative_case": case.slug,
                    "group": case.group,
                    "scenario": case.scenario,
                    "legacy_level": case.legacy_level,
                    "probe": relative(
                        probe_path(args.probe_root, profile, case.scenario)
                    ),
                    "seed": relative(args.seed_gsts[profile]),
                    "candidate_labels": list(case.character.candidate_labels),
                    "expected_flushed_marker": (
                        builder.JOIN_CLASS_CHOICE_PENDING_MARKER
                    ),
                }
            )
        for case in args.cases:
            tasks.append(
                {
                    "phase": "full_flow",
                    "pending_probe_key": pending_probe_key(case),
                    "profile": profile,
                    "case": case.slug,
                    "group": case.group,
                    "scenario": case.scenario,
                    "probe": relative(
                        probe_path(args.probe_root, profile, case.scenario)
                    ),
                    "seed": relative(args.seed_gsts[profile]),
                    "candidate_labels": list(case.character.candidate_labels),
                    "candidate_index": case.candidate_index,
                    "selected_class": case.selected_class,
                    "join_raw_experience": expected_join_raw_experience(
                        profile, case.character.commander_id
                    ),
                    "progression_expectation": args.progression_expectations[
                        (profile, case.slug)
                    ],
                    "pending_marker_value": builder.JOIN_CLASS_CHOICE_PENDING_MARKER,
                    "consumed_marker_value": 0,
                    "legacy_level": case.legacy_level,
                    "diagnostic_exact_overrides_requested": (
                        diagnostic_override_report(case)
                    ),
                    "effective_recovery_scenario": effective_recovery_scenario(case),
                    "expected_save_scenario": case.next_scenario,
                }
            )
    return {
        "schema_version": 1,
        "status": "pass",
        "command": "plan",
        "run_id": args.run_id,
        "profiles": list(args.profiles),
        "case_groups": list(args.case_groups),
        "probe_manifest": args.probe_manifest,
        "original_experience_basis": args.original_experience_basis,
        "production_experience_policy": args.production_experience_policy,
        "execution_policy": EXECUTION_POLICY,
        "pending_marker_tasks": pending_tasks,
        "pending_marker_task_count": len(pending_tasks),
        "tasks": tasks,
        "full_flow_task_count": len(tasks),
    }


def comma_tuple(value: str) -> tuple[str, ...]:
    rows = tuple(part.strip() for part in value.split(",") if part.strip())
    if not rows:
        raise argparse.ArgumentTypeError("list must not be empty")
    if len(set(rows)) != len(rows):
        raise argparse.ArgumentTypeError("list must not contain duplicates")
    return rows


def parse_profiles(value: str) -> tuple[str, ...]:
    rows = comma_tuple(value)
    unknown = sorted(set(rows) - set(PROFILES))
    if unknown:
        raise argparse.ArgumentTypeError("unknown profiles: " + ", ".join(unknown))
    return rows


def parse_groups(value: str) -> tuple[str, ...]:
    rows = comma_tuple(value)
    unknown = sorted(set(rows) - {"natural", "legacy", "legacy-later"})
    if unknown:
        raise argparse.ArgumentTypeError("unknown groups: " + ", ".join(unknown))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--profiles", type=parse_profiles, default=PROFILES)
    parser.add_argument(
        "--case-groups", type=parse_groups, default=("natural", "legacy")
    )
    parser.add_argument("--case-ids", type=comma_tuple)
    parser.add_argument("--seed-pure", type=Path)
    parser.add_argument("--seed-normal", type=Path)
    parser.add_argument("--seed-hard", type=Path)
    parser.add_argument("--probe-root", type=Path, default=DEFAULT_PROBE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--max-result-frames", type=int, default=360)
    parser.add_argument("--max-save-frames", type=int, default=160)
    parser.add_argument("--settle-delay", type=float, default=0.18)
    parser.add_argument("--save-settle-delay", type=float, default=0.7)
    parser.add_argument("--display-base", type=int, default=780)
    parser.add_argument("--xvfb", type=Path, default=preparation_parallel.DEFAULT_XVFB)
    parser.add_argument(
        "--xvfb-library-path",
        type=Path,
        default=preparation_parallel.DEFAULT_XVFB_LIBRARY_PATH,
    )
    parser.add_argument("--run-id", type=preparation.validate_run_id, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    args.profiles = tuple(args.profiles)
    args.case_groups = tuple(args.case_groups)
    args.cases = selected_cases(args.case_groups, args.case_ids)
    if not args.cases:
        parser.error("no cases selected")
    for name in (
        "probe_root",
        "output_root",
        "runtime_root",
        "xvfb",
        "xvfb_library_path",
    ):
        setattr(args, name, getattr(args, name).resolve())
    if not 1 <= args.attempts <= 4:
        parser.error("--attempts must be 1..4")
    if args.max_result_frames < 1 or args.max_save_frames < 1:
        parser.error("frame limits must be positive")
    if args.settle_delay < 0 or args.save_settle_delay < 0:
        parser.error("settle delays must be nonnegative")
    if not (
        preparation_parallel.MIN_ISOLATED_DISPLAY_NUMBER
        <= args.display_base
        <= 999 - len(args.profiles)
    ):
        parser.error(
            "--display-base must reserve only high-numbered isolated Xvfb "
            "displays and leave room for every profile"
        )

    args.seed_gsts = {}
    for profile in args.profiles:
        seed = getattr(args, f"seed_{profile}")
        if seed is None:
            parser.error(f"--seed-{profile} is required")
        seed = seed.resolve()
        if not seed.is_file():
            raise FileNotFoundError(seed)
        snapshot = state_snapshot(seed)
        validate_fresh_seed(snapshot)
        args.seed_gsts[profile] = seed

    args.probe_manifest = verify_probe_manifest(
        args.probe_root, args.profiles, args.cases
    )
    source_path = resolve_manifest_path(builder.IN_ROM)
    source_payload = source_path.read_bytes()
    args.original_experience_basis = original_experience_basis(source_payload)
    args.production_experience_policy = validate_profile_invariant_wrappers(
        args.probe_manifest,
        probe_root=args.probe_root,
        profiles=args.profiles,
        scenarios=list(args.probe_manifest["scenarios"]),
    )
    args.progression_expectations = {}
    candidate_rows = args.probe_manifest["candidate_roms"]
    for profile in args.profiles:
        candidate_path = resolve_manifest_path(candidate_rows[profile]["path"])
        candidate_payload = candidate_path.read_bytes()
        for case in args.cases:
            expectation = progression_expectation(
                profile, case, candidate_payload
            )
            if expectation["reaches_another_class_choice"]:
                raise ValueError(
                    f"{profile} {case.slug} fixed grant unexpectedly reaches "
                    "another class-choice boundary"
                )
            args.progression_expectations[(profile, case.slug)] = expectation
    for profile in args.profiles:
        phases = (
            (
                True,
                tuple(
                    case
                    for _key, case in pending_probe_representatives(args.cases)
                ),
            ),
            (False, args.cases),
        )
        for pending_only, cases in phases:
            for case in cases:
                for attempt in range(1, args.attempts + 1):
                    output = case_output(
                        args.output_root,
                        profile,
                        case,
                        args.run_id,
                        attempt,
                        pending_only=pending_only,
                    )
                    if output.exists():
                        raise FileExistsError(output)
    if args.command == "run":
        for label, path in (
            ("Xvfb", args.xvfb),
            ("Xvfb library path", args.xvfb_library_path),
        ):
            if not path.exists():
                raise FileNotFoundError(f"{label} does not exist: {path}")

    report = build_plan(args) if args.command == "plan" else run_all(args)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.summary is None:
        print(encoded, end="")
    else:
        args.summary = args.summary.resolve()
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(encoded, encoding="utf-8")
        print(args.summary)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
