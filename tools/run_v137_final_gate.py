#!/usr/bin/env python3
"""Plan and verify the immutable, fresh-start v1.3.7 final validation gate.

This is deliberately a top-level *gate*, not another emulator runner.  ``plan``
hash-locks the three release ROMs and writes every lower-level command in the
only accepted order.  ``verify`` reads the resulting summaries, checks their
exact coverage, follows seed/probe/save-chain lineage where the runners expose
it, and refuses to pass if a phase is absent or a release ROM changed.

Final evidence must be planned only after every required-scope adapter is
frozen, in a never-before-created run root.  Runs through
``v137-final-fresh-20260812-05`` are permanently retired development evidence;
the next final lineage is ``-06`` or later.  An incomplete-scope plan may still
be useful for harness development, but is explicitly ineligible for final
acceptance and can never verify as passing.

The commands are argv arrays as well as shell-rendered strings so a caller may
execute them without reconstructing any paths.  This module never deletes an
output, launches an emulator, commits, or publishes a release.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shlex
import sys
from typing import Any, Callable

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import v137_release_identity as release_identity  # noqa: E402
from tools import build_class_change_probe_rom as class_probe  # noqa: E402
from tools import build_scenario6_runestone_probe_rom as scenario6_probe  # noqa: E402
from tools import build_scenario27_ending_probe_rom as scenario27_probe  # noqa: E402
from tools import run_scenario14_15_result_surface as result_surface  # noqa: E402
from tools import (  # noqa: E402
    run_current_result_revalidation_parallel as result_parallel,
)
from tools.run_sequential_campaign_revalidation import (  # noqa: E402
    state_snapshot as serialized_state_snapshot,
)
from tools import run_scenario6_runestone_surface as scenario6_surface  # noqa: E402
from tools.verify_v134_release_regression import (  # noqa: E402
    commander_runtime as parsed_commander_runtime,
)


PROFILES = ("pure", "normal", "hard")
SCENARIOS = tuple(range(1, 32))
FULL_ROUTE_ORDER = (
    *range(1, 13),
    28,
    *range(13, 20),
    29,
    *range(20, 23),
    30,
    *range(23, 27),
    31,
    27,
)
NEXT_SCENARIO = {
    **{scenario: scenario + 1 for scenario in range(1, 27)},
    28: 13,
    29: 20,
    30: 23,
    31: 27,
    27: None,
}
DEFAULT_SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
DEFAULT_OUTPUT_ROOT = ROOT / "tmp/v137_final_gate"
RELEASE_ROM_BYTES = 0x400000

NATURAL_CASES = (
    "natural-keith-default",
    "natural-keith-hawk-lord",
    "natural-keith-healer",
    "natural-lester-default",
    "natural-lester-croco-lord",
    "natural-lester-shaman",
    "natural-jessica-default",
    "natural-jessica-sorcerer",
    "natural-jessica-lord",
)
LEGACY_CASES = tuple(
    f"legacy-{character}-fighter-lv{level}"
    for character in ("keith", "lester")
    for level in (10, 11, 12)
)
LEGACY_LATER_CASES = tuple(
    f"legacy-later-{character}-fighter-lv{level}"
    for character in ("keith", "lester")
    for level in (10, 11, 12)
)
EXPECTED_FRESH_ROSTER = {
    7: {"class_id": 0x06, "level": 10, "experience": 5},
    9: {"class_id": 0x07, "level": 10, "experience": 15},
    10: {"class_id": 0x03, "level": 10, "experience": 0},
}
JOIN_PENDING_MARKER = 0xA5
JOIN_EXECUTION_POLICY = (
    "independent_pending_exit_flush_then_fresh_continuous_full_flow"
)
JOIN_CANDIDATE_LABEL_BOX = (84, 84, 138, 168)
JOIN_RAW_EXPERIENCE = {
    "keith": 0x00,
    "lester": 0x90,
    "jessica": 0x60,
}
JOIN_CHARACTER = {
    "keith": {
        "commander_id": 7,
        "tier1_class": 0x06,
        "tier1_experience": 5,
        "marker_address": "0x00403FE7",
    },
    "lester": {
        "commander_id": 9,
        "tier1_class": 0x07,
        "tier1_experience": 15,
        "marker_address": "0x00403FE9",
    },
    "jessica": {
        "commander_id": 10,
        "tier1_class": 0x03,
        "tier1_experience": 0,
        "marker_address": "0x00403FEB",
    },
}
JOIN_CANDIDATE_LABEL_FINGERPRINT = {
    "keith": "33823c42fbac2092b392b6e50932cadbde96a99e41f5dcf54421653060ed2b8e",
    "lester": "d36b1f8bbea07aad42e169027d3217044dbed7a599c42cbeffc0ee988fae46af",
    "jessica": "2116c10bfcfcde14f0be72565f46180f000e4c757644de42f95600198278e4d8",
}
NATURAL_JOIN_EXPECTED_RESULT = {
    "natural-keith-default": (0x04, 1, 0),
    "natural-keith-hawk-lord": (0x2B, 1, 0),
    "natural-keith-healer": (0x08, 1, 0),
    "natural-lester-default": (0x05, 5, 16),
    "natural-lester-croco-lord": (0x2C, 7, 0),
    "natural-lester-shaman": (0x0A, 7, 0),
    "natural-jessica-default": (0x08, 7, 0),
    "natural-jessica-sorcerer": (0x09, 5, 0),
    "natural-jessica-lord": (0x04, 5, 0),
}
RUNESTONE_EXPECTED = {
    "keith": {
        "commander_id": 7,
        "marker_address": "0x00403FE7",
        "selected_class": "0x2B",
        "candidate_labels": ["로드", "호크로드", "힐러"],
        "label_fingerprint": (
            "e5cf981faeef5139733e62875b05cb637ff60758b7362c141e933d267b2a4587"
        ),
    },
    "lester": {
        "commander_id": 9,
        "marker_address": "0x00403FE9",
        "selected_class": "0x2C",
        "candidate_labels": ["나이트", "크로코로드", "샤먼"],
        "label_fingerprint": (
            "be5d7c3e0a6a69b8d9fdbc9f50abb943f4dd60273ea697be91c4be28ca8a1657"
        ),
    },
    "jessica": {
        "commander_id": 10,
        "marker_address": "0x00403FEB",
        "selected_class": "0x08",
        "candidate_labels": ["힐러", "소서러", "로드"],
        "label_fingerprint": (
            "3c436dfea9136f11b0be8f1cdccb97a9a5a3b20659772432f187d57fcdf89101"
        ),
    },
}
MOUNTED_EXPECTED = {
    "keith": {
        "commander_id": 7,
        "class_id": "0x2B",
        "class_name": "Hawk Lord",
        "class_stats": "08030206",
        "move": 8,
        "a_plus": 2,
        "d_plus": 6,
        "combat_resource": "0x80CE",
    },
    "lester": {
        "commander_id": 9,
        "class_id": "0x2C",
        "class_name": "Croco Lord",
        "class_stats": "06030505",
        "move": 6,
        "a_plus": 5,
        "d_plus": 5,
        "combat_resource": "0x80DC",
    },
}
PREPARATION_REVIEW_REQUIREMENT_IDS = (
    "korean_labels",
    "commander_mercenary_sprites",
    "fixed_map_records",
    "arrangement_shop_ui",
    "numeric_tiles_borders",
)


@dataclass(frozen=True)
class PhaseDefinition:
    phase_id: str
    expected_pass_count: int
    summary_count: int
    acceptance_units: dict[str, int]


@dataclass(frozen=True)
class ScopeRequirement:
    """One mandatory proof that is deliberately outside the 612 base count.

    The base count predates several user-requested release regressions.  Keeping
    those checks in a separate contract prevents their still-changing evidence
    schemas from silently changing the meaning of ``612``.  It also prevents a
    green base gate from being reported as a complete release gate.
    """

    requirement_id: str
    requirement: str
    base_phase_coverage: tuple[str, ...]
    missing_proof: str
    verifier_id: str
    expected_acceptance_units: int | None = None


PHASE_DEFINITIONS = (
    PhaseDefinition(
        "fresh_s1_seed",
        3,
        3,
        {"empty_runtime_new_game_seed": 3},
    ),
    PhaseDefinition(
        "current_result_probes",
        93,
        1,
        {"current_result_probe": 93},
    ),
    PhaseDefinition(
        "continuous_campaign_route",
        93,
        1,
        {"continuous_saved_route_step": 93},
    ),
    PhaseDefinition(
        "first_turn_s01_s31",
        93,
        3,
        {"no_action_first_turn_scenario": 93},
    ),
    PhaseDefinition(
        "preparation_s01_s31",
        93,
        4,
        {"preparation_scenario_with_manual_visual_approval": 93},
    ),
    PhaseDefinition(
        "gray_acted_s01_s31",
        93,
        3,
        {"gray_acted_scenario": 93},
    ),
    PhaseDefinition(
        "natural_and_legacy_join",
        45,
        1,
        {"natural_join": 27, "legacy_result_recovery": 18},
    ),
    PhaseDefinition(
        "legacy_later_join",
        18,
        1,
        {"legacy_later_load_recovery": 18},
    ),
    PhaseDefinition(
        "runestone_restart",
        36,
        1,
        {"character_tier_restart": 36},
    ),
    PhaseDefinition(
        "scenario6_actual_runestone",
        3,
        3,
        {"actual_move_dialogue_inventory": 3},
    ),
    PhaseDefinition(
        "mounted_lord_combat",
        6,
        1,
        {"mounted_map_status_sideview_case": 6},
    ),
    PhaseDefinition(
        "scenario27_final_and_ending",
        36,
        3,
        {
            "ending_to_fin": 3,
            "final_enemy_fixed_record": 30,
            "x4_to_s27_save_transition": 3,
        },
    ),
)
PHASE_IDS = tuple(definition.phase_id for definition in PHASE_DEFINITIONS)
PHASE_BY_ID = {
    definition.phase_id: definition for definition in PHASE_DEFINITIONS
}
EXPECTED_PHASE_DEPENDENCIES = {
    "fresh_s1_seed": (),
    "current_result_probes": ("fresh_s1_seed",),
    "continuous_campaign_route": ("fresh_s1_seed", "current_result_probes"),
    "first_turn_s01_s31": (
        "fresh_s1_seed",
        "current_result_probes",
        "continuous_campaign_route",
    ),
    "preparation_s01_s31": ("fresh_s1_seed", "first_turn_s01_s31"),
    "gray_acted_s01_s31": ("fresh_s1_seed", "preparation_s01_s31"),
    "natural_and_legacy_join": (
        "fresh_s1_seed",
        "current_result_probes",
        "gray_acted_s01_s31",
    ),
    "legacy_later_join": (
        "fresh_s1_seed",
        "current_result_probes",
        "natural_and_legacy_join",
    ),
    "runestone_restart": ("continuous_campaign_route",),
    "scenario6_actual_runestone": ("fresh_s1_seed", "runestone_restart"),
    "mounted_lord_combat": ("natural_and_legacy_join", "runestone_restart"),
    "scenario27_final_and_ending": (
        "current_result_probes",
        "continuous_campaign_route",
    ),
}
FIRST_TURN_LINEAGE_CHECKS = (
    "explicit_seed_path_match",
    "explicit_seed_sha256_match",
    "loader_rom_sha256_match",
    "first_turn_entry_kind",
    "first_turn_loader_manifest_match",
    "first_turn_entry_gst_path_match",
    "first_turn_entry_gst_sha256_match",
    "first_turn_manifest_rom_sha256_match",
    "loader_entry_gst_hash_match",
)
EXPECTED_GATE_PASS_COUNT = sum(
    definition.expected_pass_count for definition in PHASE_DEFINITIONS
)
RUN_ID_OPTIONAL_PHASES: set[str] = set()


# These requirements are mandatory even though their acceptance-unit counts
# are not folded into EXPECTED_GATE_PASS_COUNT.  Some runners/verifiers are
# still being hardened.  A new plan remains possible while that work is in
# progress, but verify is fail-closed when either the named verifier or its
# exact fresh-run evidence is absent.
REQUIRED_SCOPE_CONTRACT = (
    ScopeRequirement(
        "natural_campaign_battles_s01_s31",
        (
            "From each fresh profile seed, complete S1-S31 in chronological "
            "route order through ordinary tactical objectives and combat, "
            "carrying the exact save forward without runtime-clear shortcuts."
        ),
        (
            "continuous_campaign_route",
            "first_turn_s01_s31",
            "gray_acted_s01_s31",
        ),
        (
            "The base continuous route explicitly uses minimal runtime-clear "
            "probes; entry, first-turn, and save continuity are not proof of a "
            "natural full tactical clear."
        ),
        "natural_campaign_battle_route_v1",
        93,
    ),
    ScopeRequirement(
        "campaign_rewards_and_items",
        (
            "Verify every selected-route reward/item transition in the exact "
            "three-profile continuous save chain."
        ),
        ("continuous_campaign_route",),
        (
            "The base campaign proves record continuity but does not validate "
            "the inventory delta at each route step."
        ),
        "campaign_reward_inventory_v1",
        93,
    ),
    ScopeRequirement(
        "all_item_acquisition_paths",
        (
            "Exercise every scripted, combat-loot, replacement, hidden-tile, "
            "optional, and terminal item path, including all 22 hidden-tile "
            "handlers plus Scenario 18's conditional Crown victory grant, "
            "and reconcile the resulting inventory semantics."
        ),
        ("continuous_campaign_route", "scenario6_actual_runestone"),
        (
            "The current reward audit explicitly records zero hidden-tile "
            "collections and source-locks several combat/terminal exclusions; "
            "that bounded report is not an all-item runtime matrix."
        ),
        "all_item_acquisition_runtime_matrix_v1",
        None,
    ),
    ScopeRequirement(
        "scenario_event_and_condition_branches",
        (
            "Exercise each scenario's reviewed victory, alternate-victory, "
            "defeat, and material event-condition branches on all applicable "
            "release profiles."
        ),
        ("continuous_campaign_route", "current_result_probes"),
        (
            "The base route exercises one selected victory per scenario; the "
            "current reward/branch audit explicitly leaves alternate victories "
            "and defeat conditions as historical or static evidence."
        ),
        "scenario_event_branch_runtime_matrix_v1",
        None,
    ),
    ScopeRequirement(
        "late_hidden_spawns_s22_s25",
        (
            "Exercise and identify Scenario 22 hidden Bernhardt and Scenario "
            "25 hidden Dragon Lord on all exact release profiles."
        ),
        ("continuous_campaign_route", "preparation_s01_s31"),
        (
            "Preparation and result probes do not execute both stock hidden-"
            "commander appearance paths."
        ),
        "late_hidden_spawn_runtime_v1",
        6,
    ),
    ScopeRequirement(
        "late_enemy_s23_s26",
        (
            "On exact continuous-campaign inputs, verify named hostile "
            "commanders and mercenaries, class/name/map/status surfaces, and "
            "retain natural side-view combat in the late chapter matrix."
        ),
        (
            "continuous_campaign_route",
            "preparation_s01_s31",
            "first_turn_s01_s31",
        ),
        (
            "The base route uses bounded clear probes and cannot claim natural "
            "late-battle enemy/status/motion coverage."
        ),
        "late_enemy_runtime_matrix_v1",
        12,
    ),
    ScopeRequirement(
        "enemy_dynamic_cache_s13_s16",
        (
            "Verify the S13/S16 fixed and dynamic enemy-mercenary cache owner, "
            "row, class, tile, and exact runtime key for all release profiles."
        ),
        ("preparation_s01_s31", "gray_acted_s01_s31"),
        (
            "Generic preparation/acted captures do not prove cache ownership "
            "or reject a wrong dynamic-row lookup."
        ),
        "enemy_dynamic_cache_matrix_v1",
        9,
    ),
    ScopeRequirement(
        "historical_saves_v131_v136",
        (
            "Generate and flush real in-game SRAM with every hash-locked "
            "public patch target from v1.3.1 through v1.3.6 (17 version/profile "
            "targets), then load each save through v1.3.7's real title LOAD "
            "path for Keith, Lester, and Jessica (51 cases) and prove the "
            "version-appropriate recovery or preservation without a duplicate "
            "join EXP grant."
        ),
        ("natural_and_legacy_join", "legacy_later_join"),
        (
            "The base legacy rows are level/marker fixtures, not a versioned "
            "17-target historical-ROM-to-SRAM provenance corpus. v1.3.0 has no "
            "public patch artifact and is intentionally excluded."
        ),
        "historical_save_version_matrix_v1",
        51,
    ),
    ScopeRequirement(
        "legacy_5a_exact_release",
        (
            "Load the stale 0x5A old-save marker on exact release ROMs, equip "
            "and consume a Rune Stone through ordinary UI/combat, and verify "
            "all three markers, class, LV/EXP, and inventory after process exit."
        ),
        ("natural_and_legacy_join", "runestone_restart"),
        (
            "The base join and Rune Stone probes do not jointly prove the real "
            "old-SRAM LOAD/equip/attack/flush path on an unmodified release ROM."
        ),
        "legacy_5a_exact_release_matrix_v1",
        9,
    ),
    ScopeRequirement(
        "runestone_exact_release_tiers2_t5",
        (
            "For Keith, Lester, and Jessica at tiers 2, 3, 4, and 5, equip and "
            "consume a real Rune Stone and verify the tier-2 candidate screen "
            "and applied class on every exact release profile."
        ),
        ("runestone_restart",),
        (
            "The 36 base rows use a forced-context diagnostic derivative; they "
            "do not alone prove real equipment UI and consumption on exact ROMs."
        ),
        "runestone_exact_release_matrix_v1",
        36,
    ),
    ScopeRequirement(
        "mounted_lord_acted_surface",
        (
            "Verify Hawk Lord and Croco Lord names, stats, EXP bar, map frames, "
            "acted/gray frames, and commander-specific side-view motion."
        ),
        ("gray_acted_s01_s31", "mounted_lord_combat"),
        (
            "The mounted base probe covers map/status/side-view resources but "
            "does not separately prove the selected mounted classes' acted frame."
        ),
        "mounted_lord_acted_runtime_v1",
        6,
    ),
    ScopeRequirement(
        "s31_x4_s27_exact_ending_pages",
        (
            "Carry the exact X4/S31 save into S27, defeat Bernhardt by ordinary "
            "combat on an exact release ROM, account for every selected montage, "
            "visit, epilogue, and credit page, and reach stable Fin."
        ),
        ("continuous_campaign_route", "scenario27_final_and_ending"),
        (
            "The base S27 phase explicitly uses a harness-only HP fixture with "
            "natural_full_battle_clear=false and records Fin without a complete "
            "ordered ending-page ledger."
        ),
        "scenario27_exact_ending_page_ledger_v1",
        None,
    ),
)
REQUIRED_SCOPE_IDS = tuple(
    requirement.requirement_id for requirement in REQUIRED_SCOPE_CONTRACT
)
SCOPE_EXTENSION_COUNT_STATUS = (
    "pending_until_all_supplemental_verifiers_and_evidence_are_frozen"
)
RETIRED_FINAL_GATE_RUN_IDS = (
    "v137-final-fresh-20260812-01",
    "v137-final-fresh-20260812-02",
    "v137-final-fresh-20260812-03",
    "v137-final-fresh-20260812-04",
    "v137-final-fresh-20260812-05",
)
FINAL_GATE_RUN_ID_SEQUENCE_PREFIX = "v137-final-fresh-20260812-"
NEXT_FINAL_GATE_RUN_SEQUENCE = 6
NEXT_FINAL_GATE_RUN_ID_FLOOR = "v137-final-fresh-20260812-06"
FINAL_PLAN_POLICY = (
    "Adapters must be frozen before planning and the run root must not exist. "
    "Development plans created earlier are not final evidence even if adapters "
    "are registered later."
)


ScopeVerifier = Callable[
    [ScopeRequirement, dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]],
    tuple[bool, list[str], dict[str, object]],
]


# Intentionally empty until each domain adapter has been reviewed and frozen.
# Unit tests install the strict schema verifier below as a fixture adapter; a
# production verify invocation must never infer acceptance from a JSON status
# string when the named domain verifier has not been registered.
SUPPLEMENTAL_SCOPE_VERIFIERS: dict[str, ScopeVerifier] = {}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_sha256(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise argparse.ArgumentTypeError(
            "SHA-256 must be exactly 64 hexadecimal characters"
        )
    return normalized


def absolute(path: Path) -> str:
    return str(path.resolve())


def report_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def resolve_report_path(value: object) -> Path:
    path = Path(str(value))
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def snapshot_file(path: Path, *, release_rom: bool = False) -> dict[str, object]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    size = resolved.stat().st_size
    if release_rom and size != RELEASE_ROM_BYTES:
        raise ValueError(
            f"release ROM must be exactly {RELEASE_ROM_BYTES} bytes: {resolved}"
        )
    return {
        "path": str(resolved),
        "sha256": sha256_path(resolved),
        "bytes": size,
    }


def hash_locked_release_snapshot(path: Path, expected_sha256: str) -> dict[str, object]:
    snapshot = snapshot_file(path, release_rom=True)
    if snapshot["sha256"] != expected_sha256:
        raise ValueError(
            f"release ROM SHA-256 mismatch for {snapshot['path']}: "
            f"{snapshot['sha256']} != {expected_sha256}"
        )
    snapshot["expected_sha256"] = expected_sha256
    snapshot["hash_locked"] = True
    return snapshot


def require_canonical_source_snapshot(
    snapshot: dict[str, object],
) -> dict[str, object]:
    expected_sha256 = release_identity.JAPANESE_SOURCE_ROM_SHA256
    expected_bytes = release_identity.JAPANESE_SOURCE_ROM_BYTES
    if snapshot.get("bytes") != expected_bytes:
        raise ValueError(
            "Japanese source ROM length mismatch: "
            f"{snapshot.get('bytes')} != {expected_bytes}"
        )
    if snapshot.get("sha256") != expected_sha256:
        raise ValueError(
            "Japanese source ROM SHA-256 mismatch: "
            f"{snapshot.get('sha256')} != {expected_sha256}"
        )
    return snapshot


def command_record(
    argv: list[str],
    summary_path: Path,
    *,
    label: str,
) -> dict[str, object]:
    return {
        "label": label,
        "cwd": str(ROOT),
        "argv": argv,
        "shell": shlex.join(argv),
        "summary_path": absolute(summary_path),
    }


def phase_record(
    definition: PhaseDefinition,
    *,
    order: int,
    root: Path,
    exact_release_inputs: dict[str, dict[str, object]],
    commands: list[dict[str, object]],
    dependencies: tuple[str, ...],
) -> dict[str, object]:
    summaries = [
        {
            "label": str(command["label"]),
            "path": str(command["summary_path"]),
        }
        for command in commands
    ]
    if len(summaries) != definition.summary_count:
        raise AssertionError(
            f"{definition.phase_id} planned {len(summaries)} summaries, "
            f"expected {definition.summary_count}"
        )
    return {
        "order": order,
        "id": definition.phase_id,
        "root": str(root.resolve()),
        "status": "planned",
        "dependencies": list(dependencies),
        "exact_release_inputs": exact_release_inputs,
        "expected_pass_count": definition.expected_pass_count,
        "expected_total_count": definition.expected_pass_count,
        "acceptance_units": definition.acceptance_units,
        "command_count": len(commands),
        "commands": commands,
        "summary_count": len(summaries),
        "summaries": summaries,
    }


def scope_requirement_record(
    requirement: ScopeRequirement,
    *,
    order: int,
    root: Path,
    exact_release_inputs: dict[str, dict[str, object]],
) -> dict[str, object]:
    summary = root / requirement.requirement_id / "summary.json"
    return {
        "order": order,
        "id": requirement.requirement_id,
        "requirement": requirement.requirement,
        "base_phase_coverage": list(requirement.base_phase_coverage),
        "missing_proof": requirement.missing_proof,
        "verifier_id": requirement.verifier_id,
        "verifier_status_at_plan": (
            "implemented"
            if requirement.verifier_id in SUPPLEMENTAL_SCOPE_VERIFIERS
            else "missing_pending_implementation"
        ),
        "summary_path": str(summary.resolve()),
        "exact_release_inputs": exact_release_inputs,
        "expected_acceptance_units": requirement.expected_acceptance_units,
        "acceptance_unit_count_status": (
            "frozen"
            if requirement.expected_acceptance_units is not None
            else "pending_domain_ledger"
        ),
        "mandatory_for_final_pass": True,
    }


def python_command(script: str, *args: str) -> list[str]:
    return [sys.executable, str(ROOT / "tools" / script), *args]


def validate_new_run_layout(
    *,
    output_root: Path,
    validation_root: Path,
    phase_roots: dict[str, Path],
) -> None:
    """Require a completely unused, non-overlapping layout for a new plan.

    This check belongs only to plan creation.  Verification must continue to
    accept already-populated/frozen run roots so it can inspect their evidence.
    """
    if not output_root.is_relative_to(validation_root):
        raise ValueError(
            f"run output root is outside validation root "
            f"{validation_root}: {output_root}"
        )
    if output_root.exists():
        raise FileExistsError(
            f"new final-gate run root already exists: {output_root}"
        )
    if set(phase_roots) != set(PHASE_IDS):
        raise ValueError("every exact final-gate phase must have one root")

    items = list(phase_roots.items())
    for phase_id, path in items:
        if path == output_root or not path.is_relative_to(output_root):
            raise ValueError(
                f"{phase_id} root is outside the new run root "
                f"{output_root}: {path}"
            )
        if path.exists():
            raise FileExistsError(
                f"new final-gate phase root already exists: {phase_id} -> {path}"
            )

    for index, (left_id, left) in enumerate(items):
        for right_id, right in items[index + 1 :]:
            if left == right:
                raise ValueError(
                    "every final-gate phase must have a distinct root: "
                    f"{left_id}, {right_id} -> {left}"
                )
            if left.is_relative_to(right) or right.is_relative_to(left):
                raise ValueError(
                    "final-gate phase roots must not overlap: "
                    f"{left_id} -> {left}; {right_id} -> {right}"
                )


def build_plan(
    *,
    run_id: str,
    output_root: Path,
    release_roms: dict[str, dict[str, object]],
    source_rom: dict[str, object],
    workers: int,
    display_base: int,
    phase_roots: dict[str, Path] | None = None,
    validation_root: Path | None = None,
) -> dict[str, object]:
    validate_run_id(run_id)
    require_canonical_source_snapshot(source_rom)
    if not 100 <= display_base <= 990 - workers:
        raise ValueError(
            "display_base must reserve only high-numbered isolated Xvfb "
            "displays (:100 or higher)"
        )
    output_root = output_root.resolve()
    validation_root = (
        output_root if validation_root is None else validation_root.resolve()
    )
    default_phase_roots = {
        "fresh_s1_seed": output_root / "01_fresh_s1_seed",
        "current_result_probes": output_root / "02_current_result_probes",
        "continuous_campaign_route": output_root / "03_continuous_campaign_route",
        "first_turn_s01_s31": output_root / "04_first_turn_s01_s31",
        "preparation_s01_s31": output_root / "05_preparation_s01_s31",
        "gray_acted_s01_s31": output_root / "06_gray_acted_s01_s31",
        "natural_and_legacy_join": output_root / "07_natural_and_legacy_join",
        "legacy_later_join": output_root / "08_legacy_later_join",
        "runestone_restart": output_root / "09_runestone_restart",
        "scenario6_actual_runestone": output_root / "10_scenario6_actual_runestone",
        "mounted_lord_combat": output_root / "11_mounted_lord_combat",
        "scenario27_final_and_ending": output_root / "12_scenario27_final_and_ending",
    }
    resolved_phase_roots = {
        phase_id: path.resolve()
        for phase_id, path in default_phase_roots.items()
    }
    if phase_roots:
        unknown = sorted(set(phase_roots) - set(PHASE_IDS))
        if unknown:
            raise ValueError("unknown phase root override(s): " + ", ".join(unknown))
        resolved_phase_roots.update({
            phase_id: path.resolve() for phase_id, path in phase_roots.items()
        })
    validate_new_run_layout(
        output_root=output_root,
        validation_root=validation_root,
        phase_roots=resolved_phase_roots,
    )
    scope_extension_root = output_root / "13_required_scope_extensions"
    if scope_extension_root.exists():
        raise FileExistsError(
            "new required-scope extension root already exists: "
            f"{scope_extension_root}"
        )
    if not scope_extension_root.is_relative_to(output_root):
        raise ValueError("required-scope extension root is outside the run root")
    for phase_id, phase_root in resolved_phase_roots.items():
        if (
            phase_root == scope_extension_root
            or phase_root.is_relative_to(scope_extension_root)
            or scope_extension_root.is_relative_to(phase_root)
        ):
            raise ValueError(
                "required-scope extension root overlaps a base phase root: "
                f"{phase_id} -> {phase_root}"
            )
    releases = {
        profile: {
            "path": str(release_roms[profile]["path"]),
            "sha256": str(release_roms[profile]["sha256"]),
            "bytes": int(release_roms[profile]["bytes"]),
        }
        for profile in PROFILES
    }
    rom_paths = {profile: releases[profile]["path"] for profile in PROFILES}
    rom_hashes = {profile: releases[profile]["sha256"] for profile in PROFILES}
    release_identity.require_final_release_identity(rom_hashes)
    source_path = str(source_rom["path"])
    scenarios_csv = ",".join(str(value) for value in SCENARIOS)
    profiles_csv = ",".join(PROFILES)

    fresh_output = resolved_phase_roots["fresh_s1_seed"]
    fresh_runtime = output_root / "runtime/01_fresh_s1_seed"
    seeds = {
        profile: fresh_output / profile / run_id / "fresh_s1_preparation.gst"
        for profile in PROFILES
    }

    def seed_arguments() -> list[str]:
        values = []
        for profile in PROFILES:
            values.extend((f"--seed-{profile}", str(seeds[profile])))
        return values

    fresh_commands = []
    for index, profile in enumerate(PROFILES):
        summary = fresh_output / profile / run_id / "report.json"
        fresh_commands.append(
            command_record(
                python_command(
                    "build_fresh_s1_runtime_seed.py",
                    "run",
                    "--profile",
                    profile,
                    "--rom",
                    rom_paths[profile],
                    "--expected-rom-sha256",
                    rom_hashes[profile],
                    "--display",
                    f":{display_base + index}",
                    "--run-id",
                    run_id,
                    "--output-root",
                    str(fresh_output),
                    "--runtime-root",
                    str(fresh_runtime),
                ),
                summary,
                label=profile,
            )
        )

    probe_root = resolved_phase_roots["current_result_probes"]
    probe_summary = probe_root / "manifest.json"
    probe_commands = [
        command_record(
            python_command(
                "build_current_result_probe_matrix.py",
                "--pure-rom",
                rom_paths["pure"],
                "--normal-rom",
                rom_paths["normal"],
                "--hard-rom",
                rom_paths["hard"],
                "--expected-pure-sha256",
                rom_hashes["pure"],
                "--expected-normal-sha256",
                rom_hashes["normal"],
                "--expected-hard-sha256",
                rom_hashes["hard"],
                "--source-rom",
                source_path,
                "--output-root",
                str(probe_root),
                "--run-id",
                run_id,
                "--scenarios",
                scenarios_csv,
            ),
            probe_summary,
            label="pure-normal-hard-s01-s31",
        )
    ]

    campaign_root = resolved_phase_roots["continuous_campaign_route"]
    campaign_summary = campaign_root / "summary.json"
    campaign_commands = [
        command_record(
            python_command(
                "run_sequential_campaign_revalidation.py",
                "run",
                "--profiles",
                profiles_csv,
                *seed_arguments(),
                "--pure-rom",
                rom_paths["pure"],
                "--expected-pure-sha256",
                rom_hashes["pure"],
                "--normal-rom",
                rom_paths["normal"],
                "--expected-normal-sha256",
                rom_hashes["normal"],
                "--hard-rom",
                rom_paths["hard"],
                "--expected-hard-sha256",
                rom_hashes["hard"],
                "--probe-root",
                str(probe_root),
                "--output-root",
                str(campaign_root / "evidence"),
                "--runtime-root",
                str(output_root / "runtime/03_continuous_campaign_route"),
                "--attempts",
                "2",
                "--display-base",
                str(display_base),
                "--run-id",
                run_id,
                "--summary",
                str(campaign_summary),
            ),
            campaign_summary,
            label="continuous-pure-normal-hard",
        )
    ]

    first_turn_root = resolved_phase_roots["first_turn_s01_s31"]
    first_turn_commands = []
    for profile in PROFILES:
        profile_root = first_turn_root / profile
        first_turn_commands.append(
            command_record(
                python_command(
                    "run_first_turn_surface_parallel.py",
                    "--profile",
                    profile,
                    "--rom",
                    rom_paths[profile],
                    "--seed-gst",
                    str(seeds[profile]),
                    "--campaign-summary",
                    str(campaign_summary),
                    "--scenarios",
                    "1-31",
                    "--workers",
                    str(workers),
                    "--display-base",
                    str(display_base),
                    "--attempts",
                    "2",
                    "--output-root",
                    str(profile_root),
                    "--evidence-prefix",
                    f"{run_id}-{profile}-first-turn",
                    "--run-id",
                    run_id,
                ),
                profile_root / "summary.json",
                label=profile,
            )
        )

    preparation_root = resolved_phase_roots["preparation_s01_s31"]
    preparation_runtime = output_root / "runtime/05_preparation_s01_s31"
    preparation_commands = []
    for profile in PROFILES:
        summary = preparation_root / f"{profile}-summary.json"
        preparation_commands.append(
            command_record(
                python_command(
                    "run_preparation_surface_parallel.py",
                    "run",
                    "--profile",
                    profile,
                    "--rom",
                    rom_paths[profile],
                    "--reference-rom",
                    source_path,
                    "--seed-gst",
                    str(seeds[profile]),
                    "--scenarios",
                    "1-31",
                    "--workers",
                    str(workers),
                    "--attempts",
                    "2",
                    "--display-base",
                    str(display_base),
                    "--output-root",
                    str(preparation_root),
                    "--runtime-root",
                    str(preparation_runtime),
                    "--run-id",
                    run_id,
                    "--summary",
                    str(summary),
                ),
                summary,
                label=profile,
            )
        )
    preparation_review_root = preparation_root / "visual_review"
    preparation_review_summary = preparation_root / "visual-review-summary.json"
    preparation_commands.append(
        command_record(
            python_command(
                "verify_v137_preparation_visual_reviews.py",
                "--run-id",
                run_id,
                "--review-root",
                str(preparation_review_root),
                "--capture-root",
                str(preparation_root),
                "--pure-rom",
                rom_paths["pure"],
                "--expected-pure-sha256",
                rom_hashes["pure"],
                "--normal-rom",
                rom_paths["normal"],
                "--expected-normal-sha256",
                rom_hashes["normal"],
                "--hard-rom",
                rom_paths["hard"],
                "--expected-hard-sha256",
                rom_hashes["hard"],
                "--output",
                str(preparation_review_summary),
            ),
            preparation_review_summary,
            label="manual-visual-review",
        )
    )

    gray_root = resolved_phase_roots["gray_acted_s01_s31"]
    gray_runtime = output_root / "runtime/06_gray_acted_s01_s31"
    gray_commands = []
    for profile in PROFILES:
        summary = gray_root / f"{profile}-summary.json"
        gray_commands.append(
            command_record(
                python_command(
                    "run_gray_acted_surface_parallel.py",
                    "run",
                    "--profile",
                    profile,
                    "--rom",
                    rom_paths[profile],
                    "--seed-gst",
                    str(seeds[profile]),
                    "--campaign-summary",
                    str(campaign_summary),
                    "--scenarios",
                    "1-31",
                    "--workers",
                    str(workers),
                    "--attempts",
                    "2",
                    "--display-base",
                    str(display_base),
                    "--output-root",
                    str(gray_root),
                    "--runtime-root",
                    str(gray_runtime),
                    "--run-id",
                    run_id,
                    "--summary",
                    str(summary),
                ),
                summary,
                label=profile,
            )
        )

    natural_root = resolved_phase_roots["natural_and_legacy_join"]
    natural_summary = natural_root / "summary.json"
    natural_commands = [
        command_record(
            python_command(
                "run_natural_join_class_change_matrix.py",
                "run",
                "--profiles",
                profiles_csv,
                "--case-groups",
                "natural,legacy",
                *seed_arguments(),
                "--probe-root",
                str(probe_root),
                "--output-root",
                str(natural_root / "evidence"),
                "--runtime-root",
                str(output_root / "runtime/07_natural_and_legacy_join"),
                "--attempts",
                "2",
                "--display-base",
                str(display_base),
                "--run-id",
                run_id,
                "--summary",
                str(natural_summary),
            ),
            natural_summary,
            label="natural-and-legacy-all-profiles",
        )
    ]

    later_root = resolved_phase_roots["legacy_later_join"]
    later_summary = later_root / "summary.json"
    later_commands = [
        command_record(
            python_command(
                "run_natural_join_class_change_matrix.py",
                "run",
                "--profiles",
                profiles_csv,
                "--case-groups",
                "legacy-later",
                *seed_arguments(),
                "--probe-root",
                str(probe_root),
                "--output-root",
                str(later_root / "evidence"),
                "--runtime-root",
                str(output_root / "runtime/08_legacy_later_join"),
                "--attempts",
                "2",
                "--display-base",
                str(display_base),
                "--run-id",
                run_id,
                "--summary",
                str(later_summary),
            ),
            later_summary,
            label="legacy-later-all-profiles",
        )
    ]

    runestone_root = resolved_phase_roots["runestone_restart"]
    runestone_summary = runestone_root / run_id / "summary.json"
    runestone_commands = [
        command_record(
            python_command(
                "run_runestone_restart_matrix.py",
                "run",
                "--pure-rom",
                rom_paths["pure"],
                "--normal-rom",
                rom_paths["normal"],
                "--hard-rom",
                rom_paths["hard"],
                "--expected-pure-sha256",
                rom_hashes["pure"],
                "--expected-normal-sha256",
                rom_hashes["normal"],
                "--expected-hard-sha256",
                rom_hashes["hard"],
                "--profiles",
                profiles_csv,
                "--workers",
                str(workers),
                "--display-base",
                str(display_base),
                "--attempts",
                "2",
                "--output-root",
                str(runestone_root),
                "--run-id",
                run_id,
            ),
            runestone_summary,
            label="all-profiles-all-tiers",
        )
    ]

    scenario6_root = resolved_phase_roots["scenario6_actual_runestone"]
    scenario6_runtime = output_root / "runtime/10_scenario6_actual_runestone"
    scenario6_commands = []
    for index, profile in enumerate(PROFILES):
        summary = scenario6_root / profile / run_id / "evidence.json"
        scenario6_commands.append(
            command_record(
                python_command(
                    "run_scenario6_runestone_surface.py",
                    "--profile",
                    profile,
                    "--candidate-rom",
                    rom_paths[profile],
                    "--expected-candidate-sha256",
                    rom_hashes[profile],
                    "--source-rom",
                    source_path,
                    "--seed-gst",
                    str(seeds[profile]),
                    "--display",
                    f":{display_base + index}",
                    "--output-root",
                    str(scenario6_root),
                    "--runtime-root",
                    str(scenario6_runtime),
                    "--run-id",
                    run_id,
                ),
                summary,
                label=profile,
            )
        )

    mounted_root = resolved_phase_roots["mounted_lord_combat"]
    mounted_summary = mounted_root / run_id / "summary.json"
    mounted_commands = [
        command_record(
            python_command(
                "run_mounted_lord_combat_regression.py",
                "matrix",
                "--pure-rom",
                rom_paths["pure"],
                "--normal-rom",
                rom_paths["normal"],
                "--hard-rom",
                rom_paths["hard"],
                "--source-rom",
                source_path,
                "--display-base",
                str(display_base),
                "--output-root",
                str(mounted_root),
                "--run-id",
                run_id,
            ),
            mounted_summary,
            label="keith-and-lester-all-profiles",
        )
    ]

    ending_root = resolved_phase_roots["scenario27_final_and_ending"]
    ending_runtime = output_root / "runtime/12_scenario27_final_and_ending"
    ending_commands = []
    for index, profile in enumerate(PROFILES):
        summary = ending_root / profile / run_id / "evidence.json"
        ending_commands.append(
            command_record(
                python_command(
                    "run_scenario27_ending_surface.py",
                    "--profile",
                    profile,
                    "--rom",
                    str(probe_root / profile / "s27-ending.md"),
                    "--seed-gst",
                    str(seeds[profile]),
                    "--display",
                    f":{display_base + index}",
                    "--output-root",
                    str(ending_root),
                    "--runtime-root",
                    str(ending_runtime),
                    "--run-id",
                    run_id,
                ),
                summary,
                label=profile,
            )
        )

    command_groups = tuple(
        (commands, EXPECTED_PHASE_DEPENDENCIES[phase_id])
        for phase_id, commands in zip(
            PHASE_IDS,
            (
                fresh_commands,
                probe_commands,
                campaign_commands,
                first_turn_commands,
                preparation_commands,
                gray_commands,
                natural_commands,
                later_commands,
                runestone_commands,
                scenario6_commands,
                mounted_commands,
                ending_commands,
            ),
            strict=True,
        )
    )
    phases = [
        phase_record(
            definition,
            order=index,
            root=resolved_phase_roots[definition.phase_id],
            exact_release_inputs=releases,
            commands=commands,
            dependencies=dependencies,
        )
        for index, (definition, (commands, dependencies)) in enumerate(
            zip(PHASE_DEFINITIONS, command_groups, strict=True),
            1,
        )
    ]
    required_scope = [
        scope_requirement_record(
            requirement,
            order=index,
            root=scope_extension_root,
            exact_release_inputs=releases,
        )
        for index, requirement in enumerate(REQUIRED_SCOPE_CONTRACT, 1)
    ]
    registered_scope_verifiers = tuple(sorted(SUPPLEMENTAL_SCOPE_VERIFIERS))
    expected_scope_verifiers = tuple(sorted(
        requirement.verifier_id for requirement in REQUIRED_SCOPE_CONTRACT
    ))
    scope_registry_frozen = registered_scope_verifiers == expected_scope_verifiers
    return {
        "schema_version": 1,
        "kind": "langrisser_ii_korean_v137_final_gate_plan",
        "status": "planned",
        "release_version": "1.3.7",
        "run_id": run_id,
        "cwd": str(ROOT),
        "output_root": str(output_root),
        "validation_root": str(validation_root),
        "phase_roots": {
            phase_id: str(resolved_phase_roots[phase_id])
            for phase_id in PHASE_IDS
        },
        "required_scope_extension_root": str(scope_extension_root.resolve()),
        "execution_policy": {
            "phase_order_is_mandatory": True,
            "commands_within_each_phase_are_listed_in_stable_order": True,
            "empty_runtime_and_sram_seed_required": True,
            "exact_release_roms_must_not_change": True,
            "no_phase_may_be_skipped": True,
            "emulator_execution_owned_by_lower_level_runners": True,
            "minimum_isolated_xvfb_display_number": 100,
            "inherited_physical_display_forbidden": True,
        },
        "release_roms_before": release_roms,
        "release_identity": release_identity.identity_snapshot(),
        "support_inputs_before": {"japanese_source_rom": source_rom},
        "expected_phase_order": list(PHASE_IDS),
        "expected_gate_pass_count": EXPECTED_GATE_PASS_COUNT,
        "expected_total_acceptance_units": {
            "status": SCOPE_EXTENSION_COUNT_STATUS,
            "base_gate_units": EXPECTED_GATE_PASS_COUNT,
            "supplemental_units": None,
            "total_units": None,
            "reason": (
                "Ending-page and versioned-save ledgers are not frozen; 612 "
                "therefore names only the immutable base gate."
            ),
        },
        "phases": phases,
        "required_scope_contract": {
            "schema_version": 1,
            "status": "planned_fail_closed_extension",
            "base_gate_pass_count": EXPECTED_GATE_PASS_COUNT,
            "extension_count_status": SCOPE_EXTENSION_COUNT_STATUS,
            "required_ids": list(REQUIRED_SCOPE_IDS),
            "requirements": required_scope,
            "complete_only_when_all_requirements_pass": True,
            "verifier_registry_frozen_at_plan": scope_registry_frozen,
            "registered_verifier_ids_at_plan": list(
                registered_scope_verifiers
            ),
            "expected_verifier_ids": list(expected_scope_verifiers),
            "final_plan_eligible_at_creation": scope_registry_frozen,
            "final_plan_policy": FINAL_PLAN_POLICY,
            "retired_run_ids": list(RETIRED_FINAL_GATE_RUN_IDS),
            "next_final_run_id_floor": NEXT_FINAL_GATE_RUN_ID_FLOOR,
        },
        "final_gate": {
            "requires_release_rom_before_after_sha_match": True,
            "requires_all_phase_summaries": True,
            "requires_exact_phase_pass_counts": True,
            "requires_exact_phase_order": True,
            "requires_zero_skipped_phases": True,
            "requires_all_required_scope_verifiers": True,
            "requires_all_required_scope_evidence": True,
            "base_612_alone_is_never_final_acceptance": True,
        },
    }


def read_json(path: Path, errors: list[str], *, label: str) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"{label}: missing summary {path}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: cannot read JSON {path}: {type(exc).__name__}: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: summary root is not an object: {path}")
        return None
    return value


def check_equal(
    errors: list[str],
    actual: object,
    expected: object,
    label: str,
) -> bool:
    if actual == expected:
        return True
    errors.append(f"{label}: {actual!r} != {expected!r}")
    return False


def summary_entries(phase: dict[str, Any]) -> list[dict[str, str]]:
    values = phase.get("summaries")
    if not isinstance(values, list):
        return []
    entries = []
    for value in values:
        if isinstance(value, dict) and "label" in value and "path" in value:
            entries.append({"label": str(value["label"]), "path": str(value["path"])})
    return entries


def validate_summary_rom(
    value: object,
    *,
    profile: str,
    releases: dict[str, dict[str, Any]],
    errors: list[str],
    label: str,
) -> bool:
    expected = releases[profile]
    if isinstance(value, dict):
        raw_path = value.get("path")
        raw_sha = value.get("sha256")
    else:
        raw_path = value
        raw_sha = None
    passed = True
    if raw_path is None or resolve_report_path(raw_path) != Path(expected["path"]):
        errors.append(f"{label}: ROM path is not exact {profile} release")
        passed = False
    if raw_sha is not None and raw_sha != expected["sha256"]:
        errors.append(f"{label}: ROM SHA-256 is not exact {profile} release")
        passed = False
    return passed


def verify_scope_acceptance_summary(
    requirement: ScopeRequirement,
    entry: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[bool, list[str], dict[str, object]]:
    """Strict common envelope used by reviewed supplemental domain adapters.

    This does not interpret a domain's runtime semantics.  The named domain
    verifier must first emit a hash-linked acceptance report and exact unit
    ledger.  Registering this function for a verifier ID is therefore an
    explicit code-review decision, never an automatic fallback.
    """

    errors: list[str] = []
    path = Path(str(entry.get("summary_path", ""))).resolve()
    data = read_json(
        path,
        errors,
        label=f"required scope {requirement.requirement_id}",
    )
    if data is None:
        return False, errors, {"summary": str(path), "status": "missing"}

    check_equal(errors, data.get("schema_version"), 1, "scope schema_version")
    check_equal(
        errors,
        data.get("kind"),
        "langrisser_ii_korean_v137_scope_acceptance",
        "scope kind",
    )
    check_equal(errors, data.get("status"), "pass", "scope status")
    check_equal(
        errors,
        data.get("requirement_id"),
        requirement.requirement_id,
        "scope requirement_id",
    )
    check_equal(errors, data.get("run_id"), context.get("run_id"), "scope run_id")
    check_equal(
        errors,
        data.get("base_phase_coverage"),
        list(requirement.base_phase_coverage),
        "scope base_phase_coverage",
    )
    check_equal(
        errors,
        data.get("release_acceptance_eligible"),
        True,
        "scope release_acceptance_eligible",
    )
    check_equal(
        errors,
        data.get("diagnostic_only"),
        False,
        "scope diagnostic_only",
    )
    check_equal(
        errors,
        data.get("missing_requirements"),
        [],
        "scope missing_requirements",
    )

    snapshots = data.get("exact_release_inputs")
    if not isinstance(snapshots, dict) or set(snapshots) != set(PROFILES):
        errors.append("scope exact_release_inputs are incomplete")
    else:
        for profile in PROFILES:
            validate_summary_rom(
                snapshots.get(profile),
                profile=profile,
                releases=releases,
                errors=errors,
                label=f"scope exact release/{profile}",
            )

    observed_units = data.get("acceptance_units_observed")
    if type(observed_units) is not int or observed_units <= 0:
        errors.append("scope acceptance_units_observed is not positive")
    elif (
        requirement.expected_acceptance_units is not None
        and observed_units != requirement.expected_acceptance_units
    ):
        errors.append(
            "scope acceptance unit count differs: "
            f"{observed_units} != {requirement.expected_acceptance_units}"
        )

    def hashed_file(value: object, label: str) -> Path | None:
        if not isinstance(value, dict):
            errors.append(f"{label}: artifact is missing")
            return None
        raw_path = value.get("path")
        raw_sha = value.get("sha256")
        if not isinstance(raw_path, str) or not isinstance(raw_sha, str):
            errors.append(f"{label}: path/SHA-256 is missing")
            return None
        artifact = resolve_report_path(raw_path)
        if not artifact.is_file():
            errors.append(f"{label}: artifact file is missing: {artifact}")
            return None
        if len(raw_sha) != 64 or sha256_path(artifact) != raw_sha:
            errors.append(f"{label}: artifact SHA-256 differs")
            return None
        return artifact

    ledger = data.get("acceptance_unit_ledger")
    ledger_path = hashed_file(ledger, "scope acceptance-unit ledger")
    if not isinstance(ledger, dict) or ledger.get("unit_count") != observed_units:
        errors.append("scope acceptance-unit ledger count differs")

    domain = data.get("domain_verifier")
    domain_path = None
    if not isinstance(domain, dict):
        errors.append("scope domain_verifier is missing")
    else:
        check_equal(
            errors,
            domain.get("id"),
            requirement.verifier_id,
            "scope domain verifier id",
        )
        check_equal(
            errors,
            domain.get("status"),
            "pass",
            "scope domain verifier status",
        )
        domain_path = hashed_file(domain.get("report"), "scope domain report")

    artifacts = data.get("evidence_artifacts")
    artifact_paths: list[Path] = []
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("scope evidence_artifacts are empty")
    else:
        for index, artifact in enumerate(artifacts):
            resolved = hashed_file(artifact, f"scope evidence artifact {index}")
            if resolved is not None:
                artifact_paths.append(resolved)
    all_paths = [path for path in (ledger_path, domain_path) if path is not None]
    all_paths.extend(artifact_paths)
    if len(set(all_paths)) != len(all_paths):
        errors.append("scope primary ledger/report/evidence artifacts are reused")

    checks = data.get("checks")
    if not isinstance(checks, dict) or not checks or any(
        value is not True for value in checks.values()
    ):
        errors.append("scope checks are missing or contain a non-true value")

    return not errors, errors, {
        "summary": str(path),
        "status": data.get("status"),
        "observed_acceptance_units": (
            observed_units if type(observed_units) is int else 0
        ),
        "evidence_artifact_count": len(artifact_paths),
    }


def diagnostic_delta_report(
    candidate: bytes | bytearray,
    probe: bytes | bytearray,
) -> dict[str, object]:
    if len(candidate) != len(probe):
        raise ValueError("diagnostic candidate/probe lengths differ")
    changed = [
        offset
        for offset, (before, after) in enumerate(zip(candidate, probe, strict=True))
        if before != after
    ]
    return {
        "changed_byte_count": len(changed),
        "payload_changed_byte_count": len(
            set(changed) - {0x18E, 0x18F}
        ),
        "changed_offsets": [f"0x{offset:06X}" for offset in changed],
    }


def verify_scenario27_probe_contract(
    *,
    profile: str,
    release_path: Path,
    probe_path: Path,
    source_path: Path,
    declared_delta: object,
) -> list[str]:
    """Rebuild the S27 diagnostic and require one exact release derivative."""
    errors: list[str] = []
    try:
        release = release_path.read_bytes()
        source = source_path.read_bytes()
        actual = probe_path.read_bytes()
        expected = bytearray(release)
        scenario27_probe.patch_probe(
            expected,
            source,
            allow_balanced_input=profile == "hard",
        )
    except (OSError, ValueError) as exc:
        return [f"cannot rebuild exact S27 probe: {type(exc).__name__}: {exc}"]

    if actual != expected:
        errors.append("probe is not the exact canonical S27 builder derivative")
    actual_delta = diagnostic_delta_report(release, actual)
    expected_delta = diagnostic_delta_report(release, expected)
    if expected_delta["changed_byte_count"] != (
        scenario27_probe.EXPECTED_PROBE_CHANGED_BYTE_COUNT
    ):
        errors.append("canonical S27 builder changed-byte count is no longer 31")
    if expected_delta["payload_changed_byte_count"] != (
        scenario27_probe.EXPECTED_PROBE_PAYLOAD_CHANGED_BYTE_COUNT
    ):
        errors.append("canonical S27 builder payload changed-byte count is no longer 29")
    if actual_delta != expected_delta:
        errors.append("S27 probe exact changed-byte set differs from the builder")
    if declared_delta != expected_delta:
        errors.append("S27 manifest diagnostic_delta differs from exact bytes")
    return errors


def seed_lineage(
    seed: dict[str, Any],
    *,
    profile: str,
    context: dict[str, Any],
    errors: list[str],
    label: str,
) -> bool:
    expected = context.get("seeds", {}).get(profile)
    if not isinstance(expected, dict):
        errors.append(f"{label}: fresh seed lineage is unavailable for {profile}")
        return False
    passed = True
    if resolve_report_path(seed.get("path")) != Path(expected["path"]):
        errors.append(f"{label}: seed path differs from fresh {profile} seed")
        passed = False
    if seed.get("sha256") != expected["sha256"]:
        errors.append(f"{label}: seed SHA-256 differs from fresh {profile} seed")
        passed = False
    return passed


def campaign_input_lineage(
    value: dict[str, Any],
    *,
    profile: str,
    scenario: int,
    context: dict[str, Any],
    errors: list[str],
    label: str,
    require_origin: bool = True,
) -> bool:
    expected = context.get("campaign_inputs", {}).get((profile, scenario))
    if not isinstance(expected, dict):
        errors.append(
            f"{label}: continuous-campaign input is unavailable for "
            f"{profile} S{scenario}"
        )
        return False
    passed = True
    actual_path = resolve_report_path(value.get("path"))
    if actual_path != Path(expected["path"]):
        errors.append(f"{label}: GST path differs from continuous campaign input")
        passed = False
    fields = [("sha256", "GST SHA-256")]
    if require_origin:
        fields.extend((
            ("record_sha256", "save-record SHA-256"),
            ("route_index", "route index"),
            ("source", "source kind"),
        ))
    for key, description in fields:
        if value.get(key) != expected.get(key):
            errors.append(f"{label}: {description} differs")
            passed = False
    if not actual_path.is_file() or sha256_path(actual_path) != expected.get("sha256"):
        errors.append(f"{label}: continuous-campaign input GST/hash changed")
        passed = False
    return passed


def probe_lineage(
    probe: dict[str, Any],
    *,
    profile: str,
    scenario: int,
    context: dict[str, Any],
    errors: list[str],
    label: str,
) -> bool:
    expected = context.get("probes", {}).get((profile, scenario))
    if not isinstance(expected, dict):
        errors.append(f"{label}: probe lineage is unavailable for {profile} S{scenario}")
        return False
    passed = True
    if resolve_report_path(probe.get("path")) != Path(expected["path"]):
        errors.append(f"{label}: probe path differs from generated {profile} S{scenario}")
        passed = False
    if probe.get("sha256") != expected["sha256"]:
        errors.append(f"{label}: probe SHA-256 differs from generated {profile} S{scenario}")
        passed = False
    return passed


def verify_fresh_seed(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    details = []
    passed = 0
    seeds = {}
    record_hashes = {}
    entries = summary_entries(phase)
    by_label = {entry["label"]: entry for entry in entries}
    for profile in PROFILES:
        entry = by_label.get(profile)
        if entry is None:
            errors.append(f"fresh_s1_seed: missing {profile} summary declaration")
            continue
        path = Path(entry["path"])
        data = read_json(path, errors, label=f"fresh_s1_seed/{profile}")
        row_errors: list[str] = []
        if data is not None:
            check_equal(row_errors, data.get("status"), "pass", "status")
            check_equal(row_errors, data.get("command"), "run", "command")
            check_equal(row_errors, data.get("profile"), profile, "profile")
            check_equal(row_errors, data.get("run_id"), context["run_id"], "run_id")
            verify_isolated_display(
                data.get("virtual_display"), row_errors, "fresh seed virtual display"
            )
            validate_summary_rom(
                data.get("rom"),
                profile=profile,
                releases=releases,
                errors=row_errors,
                label="rom",
            )
            check_equal(
                row_errors,
                data.get("fresh_title_to_new_game"),
                True,
                "fresh_title_to_new_game",
            )
            isolation = data.get("isolation", {})
            check_equal(
                row_errors,
                isolation.get("empty_runtime_verified")
                if isinstance(isolation, dict)
                else None,
                True,
                "empty_runtime_verified",
            )
            snapshot = data.get("snapshot", {})
            check_equal(
                row_errors,
                snapshot.get("scenario") if isinstance(snapshot, dict) else None,
                1,
                "snapshot.scenario",
            )
            record_sha256 = (
                snapshot.get("record_sha256")
                if isinstance(snapshot, dict)
                else None
            )
            if not isinstance(record_sha256, str) or len(record_sha256) != 64:
                row_errors.append("snapshot.record_sha256 is missing or invalid")
            else:
                record_hashes[profile] = record_sha256
            roster = data.get("target_roster")
            if not isinstance(roster, dict):
                row_errors.append("target_roster is missing")
            else:
                for commander_id, expected in EXPECTED_FRESH_ROSTER.items():
                    row = roster.get(str(commander_id), roster.get(commander_id))
                    if not isinstance(row, dict):
                        row_errors.append(
                            f"target_roster commander {commander_id} is missing"
                        )
                        continue
                    for field, expected_value in expected.items():
                        if row.get(field) != expected_value:
                            row_errors.append(
                                f"target_roster commander {commander_id} "
                                f"{field}={row.get(field)!r} != {expected_value}"
                            )
            gst = data.get("scenario_1_gst", {})
            if isinstance(gst, dict) and gst.get("path") and gst.get("sha256"):
                gst_path = resolve_report_path(gst["path"])
                if not gst_path.is_file():
                    row_errors.append(f"fresh GST is missing: {gst_path}")
                elif sha256_path(gst_path) != gst["sha256"]:
                    row_errors.append(f"fresh GST hash changed: {gst_path}")
                else:
                    seeds[profile] = {
                        "path": str(gst_path),
                        "sha256": str(gst["sha256"]),
                    }
            else:
                row_errors.append("scenario_1_gst path/SHA-256 is missing")
        if data is not None and not row_errors:
            passed += 1
        errors.extend(f"fresh_s1_seed/{profile}: {error}" for error in row_errors)
        details.append({
            "profile": profile,
            "summary": str(path),
            "status": "pass" if data is not None and not row_errors else "fail",
        })
    context["seeds"] = seeds
    common_record_hash = None
    if len(record_hashes) == len(PROFILES) and len(set(record_hashes.values())) == 1:
        common_record_hash = next(iter(record_hashes.values()))
    else:
        errors.append(
            "fresh_s1_seed: pure/normal/hard serialized Scenario 1 records "
            "are not one identical hash"
        )
    context["fresh_record_sha256"] = common_record_hash
    return passed, errors, details


def verify_result_probes(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    entries = summary_entries(phase)
    if len(entries) != 1:
        errors.append("current_result_probes: expected exactly one manifest")
        return 0, errors, []
    path = Path(entries[0]["path"])
    data = read_json(path, errors, label="current_result_probes")
    if data is None:
        return 0, errors, [{"summary": str(path), "status": "missing"}]
    check_equal(errors, data.get("status"), "pass", "probe manifest status")
    check_equal(errors, data.get("run_id"), context["run_id"], "probe run_id")
    check_equal(errors, data.get("scenarios"), list(SCENARIOS), "probe scenarios")
    check_equal(errors, data.get("probe_count"), 93, "probe_count")
    source_snapshot = context.get("source_rom")
    source_report = data.get("source_rom")
    source_path: Path | None = None
    if not isinstance(source_snapshot, dict) or not isinstance(source_report, dict):
        errors.append("probe canonical Japanese source lineage is missing")
    else:
        expected_source_path = Path(str(source_snapshot.get("path"))).resolve()
        source_path = resolve_report_path(source_report.get("path"))
        check_equal(
            errors,
            source_path,
            expected_source_path,
            "probe Japanese source path",
        )
        check_equal(
            errors,
            source_report.get("sha256"),
            release_identity.JAPANESE_SOURCE_ROM_SHA256,
            "probe Japanese source SHA-256",
        )
        check_equal(
            errors,
            source_report.get("expected_sha256"),
            release_identity.JAPANESE_SOURCE_ROM_SHA256,
            "probe expected Japanese source SHA-256",
        )
        check_equal(
            errors,
            source_report.get("bytes"),
            release_identity.JAPANESE_SOURCE_ROM_BYTES,
            "probe Japanese source bytes",
        )
        check_equal(
            errors,
            source_report.get("expected_bytes"),
            release_identity.JAPANESE_SOURCE_ROM_BYTES,
            "probe expected Japanese source bytes",
        )
        check_equal(
            errors,
            source_report.get("hash_locked"),
            True,
            "probe Japanese source hash lock",
        )
    candidates = data.get("candidate_roms", {})
    for profile in PROFILES:
        value = candidates.get(profile) if isinstance(candidates, dict) else None
        validate_summary_rom(
            value,
            profile=profile,
            releases=releases,
            errors=errors,
            label=f"probe candidate {profile}",
        )
    rows = data.get("probes")
    if not isinstance(rows, list) or len(rows) != len(SCENARIOS):
        errors.append("probe manifest must contain exactly 31 scenario rows")
        rows = []
    passed = 0
    probe_map = {}
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            errors.append("probe manifest contains a non-object row")
            continue
        scenario = row.get("scenario")
        if scenario not in SCENARIOS or scenario in seen:
            errors.append(f"probe manifest has invalid/duplicate scenario {scenario!r}")
            continue
        seen.add(scenario)
        row_ok = row.get("status") == "pass"
        if scenario == 27:
            if row.get("builder_module") != scenario27_probe.__name__:
                errors.append("probe S27 builder module identity differs")
                row_ok = False
            if row.get("builder_kwargs") != {"allow_balanced_input": False}:
                errors.append("probe S27 builder kwargs differ")
                row_ok = False
            diagnostic_delta = row.get("diagnostic_delta")
            if not isinstance(diagnostic_delta, dict):
                errors.append("probe S27 diagnostic_delta is missing")
                diagnostic_delta = {}
                row_ok = False
        else:
            diagnostic_delta = {}
        for profile in PROFILES:
            report = row.get(profile)
            if not isinstance(report, dict):
                errors.append(f"probe {profile} S{scenario}: report missing")
                continue
            probe_path = resolve_report_path(report.get("path"))
            report_ok = (
                report.get("checksum_valid") is True
                and isinstance(report.get("sha256"), str)
                and probe_path.is_file()
            )
            if report_ok and probe_path.stat().st_size != report.get("bytes"):
                report_ok = False
            if report_ok and sha256_path(probe_path) != report.get("sha256"):
                report_ok = False
            if report_ok and scenario == 27:
                if source_path is None:
                    contract_errors = ["canonical Japanese source is unavailable"]
                else:
                    contract_errors = verify_scenario27_probe_contract(
                        profile=profile,
                        release_path=Path(str(releases[profile]["path"])),
                        probe_path=probe_path,
                        source_path=source_path,
                        declared_delta=diagnostic_delta.get(profile),
                    )
                if contract_errors:
                    errors.extend(
                        f"probe {profile} S27: {error}"
                        for error in contract_errors
                    )
                    report_ok = False
            if not report_ok:
                errors.append(f"probe {profile} S{scenario}: file/hash/checksum mismatch")
                continue
            if row_ok:
                passed += 1
                probe_map[(profile, int(scenario))] = {
                    "path": str(probe_path),
                    "sha256": str(report["sha256"]),
                }
    if seen != set(SCENARIOS):
        errors.append("probe manifest scenario set is incomplete")
    context["probes"] = probe_map
    context["probe_manifest"] = data
    return passed, errors, [{"summary": str(path), "status": data.get("status")}]


def profile_summaries(
    phase: dict[str, Any],
    errors: list[str],
) -> dict[str, tuple[Path, dict[str, Any]]]:
    entries = summary_entries(phase)
    by_label = {entry["label"]: entry for entry in entries}
    result = {}
    for profile in PROFILES:
        entry = by_label.get(profile)
        if entry is None:
            errors.append(f"{phase.get('id')}: missing {profile} summary declaration")
            continue
        path = Path(entry["path"])
        data = read_json(path, errors, label=f"{phase.get('id')}/{profile}")
        if data is not None:
            result[profile] = (path, data)
    return result


def exact_numbered_row(
    data: dict[str, Any],
    scenario: int,
) -> dict[str, Any] | None:
    rows = data.get("scenarios")
    if not isinstance(rows, list):
        return None
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("number") == scenario
    ]
    return matches[0] if len(matches) == 1 else None


def verify_first_turn_entry_source_lineage(
    row: dict[str, Any],
    *,
    profile: str,
    scenario: int,
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
    errors: list[str],
) -> bool:
    label = f"S{scenario} loader entry-source"
    lineage = row.get("entry_source_lineage")
    if not isinstance(lineage, dict):
        errors.append(f"{label}: lineage is missing")
        return False
    passed = True
    if not check_equal(errors, lineage.get("status"), "pass", f"{label} status"):
        passed = False
    seed = lineage.get("seed")
    if not isinstance(seed, dict):
        errors.append(f"{label}: seed path/SHA-256 is missing")
        passed = False
    elif not campaign_input_lineage(
        seed,
        profile=profile,
        scenario=scenario,
        context=context,
        errors=errors,
        label=label,
        require_origin=False,
    ):
        passed = False

    source = lineage.get("source")
    if not isinstance(source, dict):
        errors.append(f"{label}: campaign source metadata is missing")
        passed = False
    elif not campaign_input_lineage(
        source,
        profile=profile,
        scenario=scenario,
        context=context,
        errors=errors,
        label=f"{label} source",
    ):
        passed = False

    loader_manifest = lineage.get("loader_manifest")
    loader_manifest_path = resolve_report_path(loader_manifest)
    if (
        loader_manifest is None
        or loader_manifest_path
        != resolve_report_path(row.get("loader_results"))
    ):
        errors.append(f"{label}: loader manifest path does not match row")
        passed = False
    if lineage.get("loader_manifest_rom_sha256") != releases[profile]["sha256"]:
        errors.append(f"{label}: loader ROM SHA-256 is not the release ROM")
        passed = False

    loader_gst = lineage.get("loader_entry_gst")
    first_entry = lineage.get("first_turn_entry")
    if not isinstance(loader_gst, dict):
        errors.append(f"{label}: loader entry GST path/SHA-256 is missing")
        passed = False
    if not isinstance(first_entry, dict):
        errors.append(f"{label}: first-turn entry evidence is missing")
        passed = False
    if isinstance(first_entry, dict):
        if first_entry.get("kind") != "loader_smoke":
            errors.append(f"{label}: first-turn entry kind is not loader_smoke")
            passed = False
        if (
            first_entry.get("manifest") is None
            or resolve_report_path(first_entry.get("manifest"))
            != resolve_report_path(loader_manifest)
        ):
            errors.append(f"{label}: first-turn manifest differs from loader")
            passed = False
        if first_entry.get("manifest_rom_sha256") != releases[profile]["sha256"]:
            errors.append(f"{label}: first-turn manifest ROM SHA-256 differs")
            passed = False
    if isinstance(loader_gst, dict) and isinstance(first_entry, dict):
        if (
            resolve_report_path(loader_gst.get("path"))
            != resolve_report_path(first_entry.get("gst"))
        ):
            errors.append(f"{label}: first-turn GST path differs from loader")
            passed = False
        loader_gst_sha256 = loader_gst.get("sha256")
        if (
            first_entry.get("gst_sha256") != loader_gst_sha256
            or first_entry.get("manifest_gst_sha256") != loader_gst_sha256
        ):
            errors.append(f"{label}: first-turn GST SHA-256 differs from loader")
            passed = False
        loader_gst_path = resolve_report_path(loader_gst.get("path"))
        if not loader_gst_path.is_file():
            errors.append(f"{label}: loader entry GST is missing")
            passed = False
        elif sha256_path(loader_gst_path) != loader_gst_sha256:
            errors.append(f"{label}: loader entry GST hash changed")
            passed = False

    loader_data = None
    if not loader_manifest_path.is_file():
        errors.append(f"{label}: loader manifest is missing")
        passed = False
    elif (
        lineage.get("loader_results_sha256")
        != row.get("loader_results_sha256")
        or sha256_path(loader_manifest_path)
        != lineage.get("loader_results_sha256")
    ):
        errors.append(f"{label}: loader manifest hash changed")
        passed = False
    else:
        loader_data = read_json(
            loader_manifest_path,
            errors,
            label=f"{label} loader manifest",
        )
    if loader_data is not None:
        manifest_rom = loader_data.get("hard_rom")
        actual_loader_row = exact_numbered_row(loader_data, scenario)
        if (
            not isinstance(manifest_rom, dict)
            or manifest_rom.get("sha256") != releases[profile]["sha256"]
        ):
            errors.append(f"{label}: loader manifest release ROM differs")
            passed = False
        if actual_loader_row is None:
            errors.append(f"{label}: loader manifest exact scenario row is missing")
            passed = False
        else:
            if not isinstance(seed, dict) or (
                resolve_report_path(actual_loader_row.get("seed"))
                != resolve_report_path(seed.get("path"))
                or actual_loader_row.get("seed_sha256") != seed.get("sha256")
            ):
                errors.append(f"{label}: loader manifest seed lineage differs")
                passed = False
            if not isinstance(loader_gst, dict) or (
                resolve_report_path(actual_loader_row.get("gst"))
                != resolve_report_path(loader_gst.get("path"))
                or actual_loader_row.get("gst_sha256")
                != loader_gst.get("sha256")
            ):
                errors.append(f"{label}: loader manifest entry GST differs")
                passed = False

    first_manifest = lineage.get("first_turn_manifest")
    first_manifest_path = resolve_report_path(first_manifest)
    first_data = None
    if (
        first_manifest is None
        or first_manifest_path
        != resolve_report_path(row.get("first_turn_results"))
    ):
        errors.append(f"{label}: first-turn results path does not match row")
        passed = False
    elif not first_manifest_path.is_file():
        errors.append(f"{label}: first-turn results are missing")
        passed = False
    elif (
        lineage.get("first_turn_results_sha256")
        != row.get("first_turn_results_sha256")
        or sha256_path(first_manifest_path)
        != lineage.get("first_turn_results_sha256")
    ):
        errors.append(f"{label}: first-turn results hash changed")
        passed = False
    else:
        first_data = read_json(
            first_manifest_path,
            errors,
            label=f"{label} first-turn results",
        )
    if first_data is not None:
        actual_first_row = exact_numbered_row(first_data, scenario)
        actual_entry = (
            actual_first_row.get("entry_evidence")
            if isinstance(actual_first_row, dict)
            else None
        )
        if actual_first_row is None or not isinstance(actual_entry, dict):
            errors.append(f"{label}: first-turn exact entry row is missing")
            passed = False
        elif not isinstance(first_entry, dict) or any(
            actual_entry.get(name) != first_entry.get(name)
            for name in (
                "kind",
                "manifest_rom_sha256",
                "gst_sha256",
                "manifest_gst_sha256",
            )
        ) or (
            resolve_report_path(actual_entry.get("manifest"))
            != resolve_report_path(first_entry.get("manifest"))
            or resolve_report_path(actual_entry.get("gst"))
            != resolve_report_path(first_entry.get("gst"))
        ):
            errors.append(f"{label}: first-turn entry evidence differs")
            passed = False

    checks = lineage.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(FIRST_TURN_LINEAGE_CHECKS):
        errors.append(f"{label}: exact lineage check set is missing")
        passed = False
    elif any(checks[name] is not True for name in FIRST_TURN_LINEAGE_CHECKS):
        errors.append(f"{label}: one or more runtime lineage checks failed")
        passed = False
    if lineage.get("all_checks_pass") is not True:
        errors.append(f"{label}: all_checks_pass is not true")
        passed = False
    return passed


def verify_first_turn(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    passed = 0
    details = []
    for profile, (path, data) in profile_summaries(phase, errors).items():
        row_errors = []
        check_equal(row_errors, data.get("status"), "pass", "status")
        check_equal(row_errors, data.get("profile"), profile, "profile")
        check_equal(row_errors, data.get("run_id"), context["run_id"], "run_id")
        rom = data.get("rom")
        if not isinstance(rom, dict) or not rom.get("sha256"):
            row_errors.append("rom path/SHA-256 evidence is missing")
        validate_summary_rom(
            rom,
            profile=profile,
            releases=releases,
            errors=row_errors,
            label="rom",
        )
        seed = data.get("seed")
        seed_before = data.get("seed_before")
        seed_after = data.get("seed_after")
        for name, value in (
            ("seed", seed),
            ("seed_before", seed_before),
            ("seed_after", seed_after),
        ):
            if not isinstance(value, dict):
                row_errors.append(f"{name} path/SHA-256 lineage is missing")
            else:
                seed_lineage(
                    value,
                    profile=profile,
                    context=context,
                    errors=row_errors,
                    label=f"first_turn_s01_s31/{profile}/{name}",
                )
        check_equal(row_errors, seed_before, seed, "seed_before")
        check_equal(row_errors, seed_after, seed, "seed_after")
        check_equal(row_errors, data.get("seed_unchanged"), True, "seed_unchanged")
        expected_campaign = context.get("campaign_summary")
        for name in ("campaign", "campaign_before", "campaign_after"):
            value = data.get(name)
            if not isinstance(value, dict):
                row_errors.append(f"{name} path/SHA-256 lineage is missing")
                continue
            if not isinstance(expected_campaign, dict):
                row_errors.append("verified campaign summary lineage is unavailable")
                continue
            if (
                resolve_report_path(value.get("path"))
                != Path(expected_campaign["path"])
                or value.get("sha256") != expected_campaign.get("sha256")
            ):
                row_errors.append(f"{name} differs from verified campaign summary")
        check_equal(
            row_errors,
            data.get("campaign_before"),
            data.get("campaign"),
            "campaign_before",
        )
        check_equal(
            row_errors,
            data.get("campaign_after"),
            data.get("campaign"),
            "campaign_after",
        )
        check_equal(
            row_errors,
            data.get("campaign_unchanged"),
            True,
            "campaign_unchanged",
        )
        expected_seed_keys = {str(scenario) for scenario in SCENARIOS}
        for name in ("scenario_seeds", "scenario_seeds_after"):
            values = data.get(name)
            if not isinstance(values, dict) or set(values) != expected_seed_keys:
                row_errors.append(f"{name} must contain exact S1-S31 inputs")
                continue
            for scenario in SCENARIOS:
                value = values.get(str(scenario))
                if not isinstance(value, dict):
                    row_errors.append(f"{name}/S{scenario} lineage is missing")
                    continue
                campaign_input_lineage(
                    value,
                    profile=profile,
                    scenario=scenario,
                    context=context,
                    errors=row_errors,
                    label=f"first_turn_s01_s31/{profile}/{name}/S{scenario}",
                )
        check_equal(
            row_errors,
            data.get("scenario_seeds_after"),
            data.get("scenario_seeds"),
            "scenario_seeds_after",
        )
        check_equal(
            row_errors,
            data.get("scenario_seeds_unchanged"),
            True,
            "scenario_seeds_unchanged",
        )
        coverage = data.get("coverage", {})
        check_equal(
            row_errors,
            coverage.get("requested") if isinstance(coverage, dict) else None,
            list(SCENARIOS),
            "coverage.requested",
        )
        check_equal(
            row_errors,
            coverage.get("passed") if isinstance(coverage, dict) else None,
            list(SCENARIOS),
            "coverage.passed",
        )
        check_equal(
            row_errors,
            coverage.get("failed") if isinstance(coverage, dict) else None,
            [],
            "coverage.failed",
        )
        rows = data.get("scenarios")
        if not isinstance(rows, list) or len(rows) != len(SCENARIOS):
            row_errors.append("scenario results must contain exactly S1-S31")
            rows = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            scenario = row.get("scenario")
            verify_isolated_display(
                row.get("display"), row_errors, f"S{scenario} first-turn display"
            )
            lineage_ok = False
            if scenario in SCENARIOS:
                lineage_ok = verify_first_turn_entry_source_lineage(
                    row,
                    profile=profile,
                    scenario=int(scenario),
                    releases=releases,
                    context=context,
                    errors=row_errors,
                )
            if (
                scenario in SCENARIOS
                and scenario not in seen
                and row.get("status") == "pass"
                and lineage_ok
            ):
                seen.add(scenario)
        if seen != set(SCENARIOS):
            row_errors.append("not every first-turn scenario row passed exactly once")
        passed += len(seen)
        errors.extend(f"first_turn/{profile}: {error}" for error in row_errors)
        details.append({
            "profile": profile,
            "summary": str(path),
            "passed": len(seen),
            "status": "pass" if not row_errors else "fail",
        })
    return passed, errors, details


def verify_parallel_surface(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
    *,
    accepted_status: str,
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    passed = 0
    details = []
    for profile, (path, data) in profile_summaries(phase, errors).items():
        row_errors = []
        check_equal(row_errors, data.get("status"), "pass", "status")
        check_equal(row_errors, data.get("profile"), profile, "profile")
        check_equal(row_errors, data.get("run_id"), context["run_id"], "run_id")
        validate_summary_rom(
            data.get("rom"),
            profile=profile,
            releases=releases,
            errors=row_errors,
            label="rom",
        )
        seed = data.get("seed")
        if isinstance(seed, dict):
            seed_lineage(
                seed,
                profile=profile,
                context=context,
                errors=row_errors,
                label=f"{phase.get('id')}/{profile}",
            )
        else:
            row_errors.append("seed lineage is missing")
        check_equal(
            row_errors,
            data.get("seed_unchanged"),
            True,
            "seed_unchanged",
        )
        check_equal(row_errors, data.get("scenarios"), list(SCENARIOS), "scenarios")
        check_equal(row_errors, data.get("passed_scenarios"), 31, "passed_scenarios")
        check_equal(row_errors, data.get("total_scenarios"), 31, "total_scenarios")
        rows = data.get("results")
        if not isinstance(rows, list) or len(rows) != len(SCENARIOS):
            row_errors.append("results must contain exactly S1-S31")
            rows = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            scenario = row.get("scenario")
            verify_isolated_display(
                row.get("display"), row_errors, f"S{scenario} surface display"
            )
            if (
                scenario in SCENARIOS
                and scenario not in seen
                and row.get("returncode") == 0
                and row.get("status") == accepted_status
            ):
                seen.add(scenario)
        if seen != set(SCENARIOS):
            row_errors.append("not every surface scenario row passed exactly once")
        passed += len(seen)
        errors.extend(f"{phase.get('id')}/{profile}: {error}" for error in row_errors)
        details.append({
            "profile": profile,
            "summary": str(path),
            "passed": len(seen),
            "status": "pass" if not row_errors else "fail",
        })
    return passed, errors, details


JOIN_ORIGINAL_BASIS = {
    "keith": {"class_id": "0x06", "level": 1, "residual": 5},
    "lester": {"class_id": "0x07", "level": 7, "residual": 15},
    "jessica": {"class_id": "0x09", "level": 5, "residual": 0},
}


def join_character_slug(case: str) -> str:
    matches = [slug for slug in JOIN_CHARACTER if slug in case]
    if len(matches) != 1:
        raise ValueError(f"cannot identify join character from case {case!r}")
    return matches[0]


def expected_join_scenario(case: str) -> int:
    character = join_character_slug(case)
    if character == "keith":
        return 8 if case.startswith("legacy-later-") else 7
    if character == "lester":
        return 11 if case.startswith("legacy-later-") else 10
    return 11


def expected_join_group(case: str) -> str:
    if case.startswith("legacy-later-"):
        return "legacy-later"
    if case.startswith("legacy-"):
        return "legacy"
    if case.startswith("natural-"):
        return "natural"
    raise ValueError(f"unsupported join case group: {case!r}")


def expected_join_legacy_level(case: str) -> int | None:
    if not case.startswith("legacy-"):
        return None
    try:
        return int(case.rsplit("-lv", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"invalid legacy join case level: {case!r}") from exc


def expected_join_pending_probe_key(case: str) -> str:
    group = expected_join_group(case)
    character = join_character_slug(case)
    if group == "natural":
        return f"natural:{character}"
    return (
        f"{group}:{character}:s{expected_join_scenario(case)}:"
        f"lv{expected_join_legacy_level(case)}"
    )


def expected_join_pending_representatives(
    cases: tuple[str, ...],
) -> dict[str, str]:
    representatives: dict[str, str] = {}
    for case in cases:
        representatives.setdefault(expected_join_pending_probe_key(case), case)
    return representatives


def expected_join_candidate_index(case: str) -> int:
    if case in NATURAL_CASES:
        return NATURAL_CASES.index(case) % 3 + 1
    return 1


def expected_join_result(case: str) -> tuple[int, int, int]:
    if case in NATURAL_JOIN_EXPECTED_RESULT:
        return NATURAL_JOIN_EXPECTED_RESULT[case]
    character = join_character_slug(case)
    if character == "keith":
        return (0x04, 1, 0)
    if character == "lester":
        return (0x05, 5, 16)
    raise ValueError(f"unsupported legacy join case {case!r}")


def expected_pre_completion_runtime(
    case: str,
) -> dict[str, int]:
    """Return the exact state before stock scenario-result EXP is awarded."""
    character = JOIN_CHARACTER[join_character_slug(case)]
    if case.startswith("legacy-"):
        level = expected_join_legacy_level(case)
        if level is None:
            raise ValueError(f"legacy join case has no level: {case!r}")
        return {
            "class_id": 0x01,
            "level": level,
            "experience": int(character["tier1_experience"]),
        }
    return {
        "class_id": int(character["tier1_class"]),
        "level": 10,
        "experience": int(character["tier1_experience"]),
    }


def verify_hashed_artifact(
    value: object,
    *,
    path_key: str,
    sha_key: str,
    errors: list[str],
    label: str,
) -> Path | None:
    if not isinstance(value, dict):
        errors.append(f"{label}: artifact report is missing")
        return None
    raw_path = value.get(path_key)
    digest = value.get(sha_key)
    if raw_path is None or not isinstance(digest, str) or len(digest) != 64:
        errors.append(f"{label}: path/SHA-256 is missing")
        return None
    path = resolve_report_path(raw_path)
    if not path.is_file() or sha256_path(path) != digest:
        errors.append(f"{label}: file is missing or hash changed: {path}")
        return None
    return path


def join_candidate_label_fingerprint(path: Path) -> str:
    """Recompute the three-label mask from a hash-bound 320x240 capture."""
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    if image.size != (320, 240):
        raise ValueError(f"join capture must be 320x240: {path}")
    crop = image.crop(JOIN_CANDIDATE_LABEL_BOX)
    mask = bytes(
        1 if red > 150 and green > 150 and blue > 150 else 0
        for red, green, blue in crop.getdata()
    )
    return hashlib.sha256(mask).hexdigest()


def verify_join_capture_artifact(
    value: object,
    *,
    errors: list[str],
    label: str,
    expected_label_fingerprint: str | None = None,
    expected_surface: str | None = None,
) -> Path | None:
    """Require a decodable 320x240 PNG and optionally its live label mask."""
    path = verify_hashed_artifact(
        value,
        path_key="path",
        sha_key="sha256",
        errors=errors,
        label=label,
    )
    if path is None:
        return None
    try:
        with Image.open(path) as opened:
            opened.load()
            size = opened.size
            image_format = opened.format
        if size != (320, 240) or image_format != "PNG":
            raise ValueError(
                f"expected a 320x240 PNG, got {size!r} {image_format!r}"
            )
        if expected_label_fingerprint is not None:
            observed = join_candidate_label_fingerprint(path)
            if observed != expected_label_fingerprint:
                errors.append(
                    f"{label}: live label fingerprint {observed} differs"
                )
        if (
            expected_surface is not None
            and result_surface.classify_surface(path) != expected_surface
        ):
            errors.append(f"{label}: live surface is not {expected_surface}")
    except (OSError, ValueError) as exc:
        errors.append(f"{label}: image content is invalid: {exc}")
    return path


def verify_join_gst_runtime(
    value: object,
    *,
    commander_id: int,
    runtime_key: str = "runtime",
    errors: list[str],
    label: str,
) -> tuple[Path | None, dict[str, int] | None]:
    """Parse commander runtime from GST instead of trusting JSON fields."""
    path = verify_hashed_artifact(
        value,
        path_key="gst",
        sha_key="gst_sha256",
        errors=errors,
        label=label,
    )
    if path is None:
        return None, None
    try:
        observed = parsed_commander_runtime(path, commander_id)
    except (OSError, ValueError) as exc:
        errors.append(f"{label}: GST runtime cannot be parsed: {exc}")
        return path, None
    reported = value.get(runtime_key) if isinstance(value, dict) else None
    if reported != observed:
        errors.append(f"{label}: reported runtime differs from GST work RAM")
    return path, observed


def join_primary_artifact_paths(row: dict[str, Any]) -> list[tuple[str, Path]]:
    """Return independently generated primary files that may never be reused."""
    paths: list[tuple[str, Path]] = []

    def add(label: str, value: object) -> None:
        if value is not None:
            paths.append((label, resolve_report_path(value)))

    add("evidence", row.get("evidence_path"))
    for section_name, section in (
        ("pre-completion", row.get("pre_completion")),
        ("candidate", row.get("candidate")),
        ("applied", row.get("applied_immediate")),
        ("result", row.get("battle_result")),
        ("save", row.get("save_menu")),
    ):
        if not isinstance(section, dict):
            continue
        add(f"{section_name} GST", section.get("gst"))
        capture = section.get("capture")
        if isinstance(capture, dict):
            add(f"{section_name} capture", capture.get("path"))
        if section_name == "candidate":
            selected = section.get("selected_capture")
            if isinstance(selected, dict):
                add("candidate selected capture", selected.get("path"))
            marker = section.get("pending_join_marker")
            if isinstance(marker, dict):
                add("candidate marker", marker.get("path"))
        if section_name == "save":
            marker = section.get("consumed_join_marker")
            if isinstance(marker, dict):
                add("save marker", marker.get("path"))
    return paths


def register_unique_join_artifacts(
    row: dict[str, Any],
    *,
    owner: str,
    seen: dict[Path, str],
    errors: list[str],
) -> None:
    """Reject path reuse within one execution or across independent cases."""
    local: dict[Path, str] = {}
    for label, path in join_primary_artifact_paths(row):
        previous_local = local.get(path)
        if previous_local is not None:
            errors.append(
                f"{owner}: {label} reuses this row's {previous_local} path"
            )
            continue
        local[path] = label
        previous_owner = seen.get(path)
        if previous_owner is not None:
            errors.append(
                f"{owner}: {label} reuses primary evidence from {previous_owner}"
            )
            continue
        seen[path] = f"{owner} {label}"


def verify_join_execution_evidence(
    row: dict[str, Any],
    *,
    expected_phase: str,
    expected_evidence_root: Path,
    expected_run_id: str,
    errors: list[str],
    label: str,
) -> tuple[Path | None, dict[str, Any] | None]:
    """Bind a summary row to its phase-specific fresh emulator execution."""
    check_equal(errors, row.get("phase"), expected_phase, f"{label} phase")
    check_equal(
        errors,
        row.get("execution_policy"),
        JOIN_EXECUTION_POLICY,
        f"{label} execution policy",
    )
    phase_component = (
        "pending-probe" if expected_phase == "pending_marker_probe" else "full-flow"
    )
    runtime_prefix = (
        "join-pending-" if expected_phase == "pending_marker_probe" else "join-full-"
    )
    check_equal(errors, row.get("run_id"), expected_run_id, f"{label} run_id")
    attempt = row.get("attempt")
    profile = row.get("profile")
    case = row.get("case")
    phase_name = "pending" if expected_phase == "pending_marker_probe" else "full"
    expected_runtime_name = (
        f"join-{phase_name}-{profile}-{case}-{expected_run_id}-a{attempt}"
    )
    runtime_name = row.get("runtime_name")
    if runtime_name != expected_runtime_name or not str(runtime_name).startswith(
        runtime_prefix
    ):
        errors.append(f"{label}: runtime name is not bound to this run/case/attempt")
    isolation = row.get("runtime_isolation")
    if not isinstance(isolation, dict):
        errors.append(f"{label}: runtime isolation report is missing")
    else:
        check_equal(
            errors,
            isolation.get("policy"),
            "replace_existing_named_home_before_launch",
            f"{label} runtime isolation policy",
        )
        check_equal(
            errors,
            isolation.get("phase_unique"),
            True,
            f"{label} phase-unique runtime",
        )
        runtime_home = isolation.get("runtime_home")
        if (
            not isinstance(runtime_home, str)
            or not runtime_home
            or Path(runtime_home).name != runtime_name
        ):
            errors.append(f"{label}: runtime home does not match runtime name")

    evidence_path = verify_hashed_artifact(
        row,
        path_key="evidence_path",
        sha_key="evidence_sha256",
        errors=errors,
        label=f"{label} evidence JSON",
    )
    evidence: dict[str, Any] | None = None
    if evidence_path is not None:
        expected_path = (
            expected_evidence_root
            / str(profile)
            / str(case)
            / expected_run_id
            / phase_component
            / f"attempt-{attempt}"
            / "evidence.json"
        ).resolve()
        if evidence_path != expected_path:
            errors.append(
                f"{label}: evidence path is not the canonical current-run path"
            )
        evidence = read_json(evidence_path, errors, label=f"{label} evidence JSON")
        if evidence is not None:
            # The on-disk evidence is written before the summary-only retry and
            # self-hash fields are attached.  Every field it does contain must
            # remain byte-for-byte represented by the selected summary row.
            for field, value in evidence.items():
                if row.get(field) != value:
                    errors.append(
                        f"{label}: summary differs from evidence JSON field {field}"
                    )
    return evidence_path, evidence


def verify_join_attempt_history(
    row: dict[str, Any],
    *,
    errors: list[str],
    label: str,
) -> None:
    attempt = row.get("attempt")
    history = row.get("attempt_history")
    if type(attempt) is not int or not 1 <= attempt <= 4:
        errors.append(f"{label}: successful attempt number is invalid")
        return
    if not isinstance(history, list) or len(history) != attempt:
        errors.append(f"{label}: retry history does not terminate at selected attempt")
        return
    for index, attempt_row in enumerate(history, 1):
        if not isinstance(attempt_row, dict) or attempt_row.get("attempt") != index:
            errors.append(f"{label}: retry history is not contiguous")
            continue
        expected_status = "pass" if index == attempt else "failed_attempt"
        if attempt_row.get("status") != expected_status:
            errors.append(f"{label}: retry status sequence differs")
    if isinstance(history[-1], dict) and history[-1].get("error") is not None:
        errors.append(f"{label}: successful retry retains an error")


def verify_command_display_policy(argv: list[str], errors: list[str]) -> None:
    """Reject any final-gate command that could target a desktop X server."""
    if "--desktop-display" in argv:
        errors.append("command explicitly opts into the inherited desktop display")
    for option in ("--display", "--virtual-display", "--display-base"):
        positions = [index for index, value in enumerate(argv) if value == option]
        if len(positions) > 1:
            errors.append(f"command contains duplicate {option} options")
        for position in positions:
            value = argv[position + 1] if position + 1 < len(argv) else None
            try:
                if option == "--display-base":
                    number = int(value) if isinstance(value, str) else -1
                    canonical = value == str(number)
                else:
                    number = (
                        int(value[1:])
                        if isinstance(value, str) and value.startswith(":")
                        else -1
                    )
                    canonical = value == f":{number}"
            except ValueError:
                number = -1
                canonical = False
            if not canonical or number < 100:
                errors.append(
                    f"command {option} must use a high-numbered isolated "
                    f"Xvfb display, got {value!r}"
                )


def verify_isolated_display(value: object, errors: list[str], label: str) -> None:
    try:
        number = int(value[1:]) if isinstance(value, str) else -1
    except ValueError:
        number = -1
    if value != f":{number}" or number < 100:
        errors.append(f"{label} is not a high-numbered isolated X display")


def verify_marker_snapshot(
    value: object,
    *,
    expected_value: int,
    expected_address: str,
    errors: list[str],
    label: str,
) -> Path | None:
    path = verify_hashed_artifact(
        value,
        path_key="path",
        sha_key="sha256",
        errors=errors,
        label=label,
    )
    if not isinstance(value, dict):
        return path
    expected_offset = (int(expected_address, 16) - 0x00400001) // 2
    if value.get("bytes") != 0x2000:
        errors.append(f"{label}: SRAM snapshot size is not 8192")
    if value.get("address") != expected_address:
        errors.append(f"{label}: marker address differs")
    if value.get("sram_offset") != f"0x{expected_offset:04X}":
        errors.append(f"{label}: marker SRAM offset differs")
    if value.get("value") != expected_value:
        errors.append(
            f"{label}: marker value {value.get('value')!r} != {expected_value}"
        )
    if path is not None:
        payload = path.read_bytes()
        if len(payload) != 0x2000 or payload[expected_offset] != expected_value:
            errors.append(f"{label}: hash-bound SRAM byte differs from report")
    return path


def verify_join_flush_checkpoint(
    value: object,
    *,
    marker: object,
    expected_marker: int,
    errors: list[str],
    label: str,
) -> None:
    """Require an explicit emulator-exit SRAM flush at one checkpoint."""
    if not isinstance(value, dict):
        errors.append(f"{label}: process-exit flush report is missing")
        return
    for field, expected in (
        ("status", "pass"),
        ("policy", "process_exit_flush"),
        ("expected_marker", expected_marker),
    ):
        check_equal(errors, value.get(field), expected, f"{label} {field}")
    if value.get("flushed_marker") != marker:
        errors.append(f"{label}: flushed marker differs from stage evidence")


def verify_join_character_identity(
    row: dict[str, Any],
    *,
    slug: str,
    errors: list[str],
    label: str,
) -> None:
    character = JOIN_CHARACTER[slug]
    reported = row.get("character")
    if not isinstance(reported, dict):
        errors.append(f"{label}: character identity is missing")
        return
    for field, expected in (
        ("commander_id", character["commander_id"]),
        ("tier1_class", character["tier1_class"]),
        ("candidate_labels", RUNESTONE_EXPECTED[slug]["candidate_labels"]),
        (
            "candidate_label_fingerprint",
            JOIN_CANDIDATE_LABEL_FINGERPRINT[slug],
        ),
    ):
        check_equal(errors, reported.get(field), expected, f"{label} {field}")


def verify_join_pre_completion(
    value: object,
    *,
    case: str,
    errors: list[str],
    label: str,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: pre-completion evidence is missing")
        return
    expected = expected_pre_completion_runtime(case)
    runtime = value.get("runtime")
    if not isinstance(runtime, dict) or any(
        runtime.get(field) != expected_value
        for field, expected_value in expected.items()
    ):
        errors.append(f"{label}: pre-completion class/LV/EXP differs")
    verify_join_gst_runtime(
        value,
        commander_id=int(JOIN_CHARACTER[join_character_slug(case)]["commander_id"]),
        errors=errors,
        label=f"{label} pre-completion GST",
    )


def verify_join_candidate_boundary(
    value: object,
    *,
    slug: str,
    errors: list[str],
    label: str,
    selected_capture_required: bool,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label}: candidate evidence is missing")
        return None
    character = JOIN_CHARACTER[slug]
    runtime = value.get("runtime")
    if not isinstance(runtime, dict):
        errors.append(f"{label}: candidate runtime is missing")
    else:
        if runtime.get("class_id") != character["tier1_class"] or (
            runtime.get("level") != 10
        ):
            errors.append(f"{label}: candidate is not the tier-one LV10 boundary")
        experience = runtime.get("experience")
        if type(experience) is not int or not 0 <= experience <= 0xFF:
            errors.append(f"{label}: stock result EXP byte was not recorded")
        x = runtime.get("x")
        y = runtime.get("y")
        if (
            type(x) is not int
            or type(y) is not int
            or not 0 <= x <= 0xFF
            or not 0 <= y <= 0xFF
            or x == 0xFF
            or y == 0xFF
            or (x == 0 and y == 0)
        ):
            errors.append(f"{label}: commander is not visibly on the player map")
    check_equal(
        errors,
        value.get("labels"),
        RUNESTONE_EXPECTED[slug]["candidate_labels"],
        f"{label} labels",
    )
    check_equal(
        errors,
        value.get("label_fingerprint"),
        JOIN_CANDIDATE_LABEL_FINGERPRINT[slug],
        f"{label} label fingerprint",
    )
    verify_join_capture_artifact(
        value.get("capture"),
        errors=errors,
        label=f"{label} capture",
        expected_label_fingerprint=JOIN_CANDIDATE_LABEL_FINGERPRINT[slug],
    )
    _gst_path, parsed_runtime = verify_join_gst_runtime(
        value,
        commander_id=int(character["commander_id"]),
        errors=errors,
        label=f"{label} GST",
    )
    if selected_capture_required:
        check_equal(
            errors,
            value.get("continuous_to_applied_state"),
            True,
            f"{label} continuous application",
        )
        verify_join_capture_artifact(
            value.get("selected_capture"),
            errors=errors,
            label=f"{label} selected capture",
            expected_label_fingerprint=JOIN_CANDIDATE_LABEL_FINGERPRINT[slug],
        )
    if parsed_runtime is not None:
        return parsed_runtime
    return runtime if isinstance(runtime, dict) else None


def join_candidate_runtime_identity(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    fields = ("class_id", "level", "experience", "x", "y")
    return {field: value.get(field) for field in fields}


def verify_join_experience_contract(
    data: dict[str, Any],
    *,
    releases: dict[str, dict[str, Any]],
    expected_cases: tuple[str, ...],
    errors: list[str],
    label: str,
) -> None:
    expected_raw = {
        str(JOIN_CHARACTER[slug]["commander_id"]): raw
        for slug, raw in JOIN_RAW_EXPERIENCE.items()
    }
    basis = data.get("original_experience_basis")
    if not isinstance(basis, dict):
        errors.append(f"{label}: original EXP basis is missing")
    else:
        check_equal(errors, basis.get("status"), "pass", f"{label} basis status")
        check_equal(
            errors,
            basis.get("policy"),
            "numeric_level_cumulative_raw_excluding_residual_bar",
            f"{label} basis policy",
        )
        rows = basis.get("rows")
        by_id = (
            {
                row.get("commander_id"): row
                for row in rows
                if isinstance(row, dict)
            }
            if isinstance(rows, list)
            else {}
        )
        for slug, character in JOIN_CHARACTER.items():
            commander_id = int(character["commander_id"])
            row = by_id.get(commander_id)
            original = JOIN_ORIGINAL_BASIS[slug]
            if not isinstance(row, dict):
                errors.append(f"{label}: {slug} original EXP row is missing")
                continue
            gauge = row.get("class_experience_gauge")
            raw = JOIN_RAW_EXPERIENCE[slug]
            if (
                row.get("original_second_tier_class") != original["class_id"]
                or row.get("original_second_tier_level") != original["level"]
                or row.get("original_residual_experience_excluded")
                != original["residual"]
                or not isinstance(gauge, int)
                or (int(original["level"]) - 1) * gauge != raw
                or row.get("fixed_raw_experience") != raw
            ):
                errors.append(f"{label}: {slug} original numeric-level basis differs")

    policy = data.get("production_experience_policy")
    if not isinstance(policy, dict):
        errors.append(f"{label}: production EXP policy proof is missing")
        return
    for field, expected in (
        ("status", "pass"),
        ("policy", "profile_and_branch_invariant_one_time_raw_experience"),
        ("profile_invariant", True),
        ("branch_invariant", True),
        ("target_level_pump_absent", True),
        ("class_specific_adjustment_absent", True),
        ("raw_experience_by_commander", expected_raw),
    ):
        check_equal(errors, policy.get(field), expected, f"{label} policy {field}")
    expected_wrapper_sha = policy.get("expected_wrapper_sha256")
    common_wrapper_sha = policy.get("profile_wrapper_sha256")
    if (
        not isinstance(expected_wrapper_sha, str)
        or len(expected_wrapper_sha) != 64
        or common_wrapper_sha != expected_wrapper_sha
    ):
        errors.append(f"{label}: common expected wrapper SHA-256 differs")
    profiles = policy.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != len(PROFILES):
        errors.append(f"{label}: wrapper profile proof count is not three")
        return
    by_profile = {
        row.get("profile"): row for row in profiles if isinstance(row, dict)
    }
    expected_scenarios = {
        expected_join_scenario(case) for case in expected_cases
    }
    for profile in PROFILES:
        row = by_profile.get(profile)
        if not isinstance(row, dict):
            errors.append(f"{label}: {profile} wrapper proof is missing")
            continue
        validate_summary_rom(
            row.get("candidate_rom"),
            profile=profile,
            releases=releases,
            errors=errors,
            label=f"{label} wrapper {profile}",
        )
        if (
            row.get("matches_current_builder") is not True
            or row.get("wrapper_sha256") != common_wrapper_sha
            or row.get("raw_experience_by_commander") != expected_raw
        ):
            errors.append(f"{label}: {profile} wrapper identity/grants differ")
        probes = row.get("probes")
        if not isinstance(probes, list):
            errors.append(f"{label}: {profile} wrapper probe proof is missing")
            continue
        seen_scenarios = {
            probe.get("scenario")
            for probe in probes
            if isinstance(probe, dict)
            and probe.get("byte_identical_to_release") is True
            and probe.get("wrapper_sha256") == common_wrapper_sha
        }
        if seen_scenarios != expected_scenarios:
            errors.append(f"{label}: {profile} wrapper probe coverage differs")


def verify_join_pending_probe(
    row: dict[str, Any],
    *,
    profile: str,
    case: str,
    evidence_root: Path,
    context: dict[str, Any],
    errors: list[str],
) -> None:
    label = f"pending {profile}/{expected_join_pending_probe_key(case)}"
    slug = join_character_slug(case)
    character = JOIN_CHARACTER[slug]
    scenario = expected_join_scenario(case)
    check_equal(errors, row.get("status"), "pass", f"{label} status")
    check_equal(errors, row.get("profile"), profile, f"{label} profile")
    check_equal(errors, row.get("case"), case, f"{label} representative case")
    check_equal(errors, row.get("group"), expected_join_group(case), f"{label} group")
    check_equal(errors, row.get("scenario"), scenario, f"{label} scenario")
    check_equal(errors, row.get("next_scenario"), scenario + 1, f"{label} next scenario")
    check_equal(
        errors,
        row.get("legacy_level"),
        expected_join_legacy_level(case),
        f"{label} legacy level",
    )
    check_equal(
        errors,
        row.get("pending_probe_key"),
        expected_join_pending_probe_key(case),
        f"{label} key",
    )
    check_equal(errors, row.get("virtual_display"), True, f"{label} virtual display")
    verify_isolated_display(row.get("display"), errors, f"{label} display")
    verify_join_attempt_history(row, errors=errors, label=label)
    verify_join_execution_evidence(
        row,
        expected_phase="pending_marker_probe",
        expected_evidence_root=evidence_root,
        expected_run_id=str(context["run_id"]),
        errors=errors,
        label=label,
    )
    verify_join_character_identity(row, slug=slug, errors=errors, label=label)
    seed = row.get("seed")
    if isinstance(seed, dict):
        seed_lineage(
            seed,
            profile=profile,
            context=context,
            errors=errors,
            label=label,
        )
    else:
        errors.append(f"{label}: seed lineage is missing")
    probe = row.get("probe")
    if isinstance(probe, dict):
        probe_lineage(
            probe,
            profile=profile,
            scenario=scenario,
            context=context,
            errors=errors,
            label=label,
        )
    else:
        errors.append(f"{label}: probe lineage is missing")
    join_exp = row.get("join_experience")
    if not isinstance(join_exp, dict) or (
        join_exp.get("policy") != "one_fixed_raw_grant_no_target_level_pump"
        or join_exp.get("profile_invariant") is not True
        or join_exp.get("branch_invariant") is not True
        or join_exp.get("raw_experience") != JOIN_RAW_EXPERIENCE[slug]
    ):
        errors.append(f"{label}: fixed raw EXP contract differs")
    selection = row.get("selection")
    if not isinstance(selection, dict) or (
        selection.get("candidate_index") != 1
        or selection.get("selected_class") != expected_join_result(case)[0]
    ):
        errors.append(f"{label}: representative selection identity differs")
    verify_join_pre_completion(
        row.get("pre_completion"), case=case, errors=errors, label=label
    )
    candidate = row.get("candidate")
    verify_join_candidate_boundary(
        candidate,
        slug=slug,
        errors=errors,
        label=f"{label} candidate",
        selected_capture_required=False,
    )
    if not isinstance(candidate, dict):
        return
    marker = candidate.get("pending_join_marker")
    verify_marker_snapshot(
        marker,
        expected_value=JOIN_PENDING_MARKER,
        expected_address=str(character["marker_address"]),
        errors=errors,
        label=f"{label} pending marker",
    )
    verify_join_flush_checkpoint(
        candidate.get("pending_flush"),
        marker=marker,
        expected_marker=JOIN_PENDING_MARKER,
        errors=errors,
        label=f"{label} process-exit flush",
    )
    for forbidden in (
        "pending_flush_resume",
        "resume_method",
        "resumed_gst",
        "resumed_runtime",
    ):
        if forbidden in candidate:
            errors.append(f"{label}: invalid GST-resume field {forbidden} is present")
    for forbidden in ("applied_immediate", "battle_result", "save_menu"):
        if forbidden in row:
            errors.append(f"{label}: pending-only run contains {forbidden}")


def verify_join_pending_reference(
    row: dict[str, Any],
    *,
    pending: dict[str, Any],
    errors: list[str],
    label: str,
) -> None:
    reference = row.get("pending_marker_probe")
    pending_candidate = pending.get("candidate")
    if not isinstance(reference, dict) or not isinstance(pending_candidate, dict):
        errors.append(f"{label}: pending-marker reference is missing")
        return
    expected_reference = {
        "status": "pass",
        "run_id": pending.get("run_id"),
        "pending_probe_key": pending.get("pending_probe_key"),
        "profile": pending.get("profile"),
        "case": pending.get("case"),
        "scenario": pending.get("scenario"),
        "legacy_level": pending.get("legacy_level"),
        "runtime_name": pending.get("runtime_name"),
        "evidence_path": pending.get("evidence_path"),
        "evidence_sha256": pending.get("evidence_sha256"),
        "probe": pending.get("probe"),
        "seed": pending.get("seed"),
        "candidate_gst": pending_candidate.get("gst"),
        "candidate_gst_sha256": pending_candidate.get("gst_sha256"),
        "pending_marker": pending_candidate.get("pending_join_marker"),
    }
    if reference != expected_reference:
        errors.append(f"{label}: pending-marker reference differs from selected proof")
    if row.get("pending_probe_key") != pending.get("pending_probe_key"):
        errors.append(f"{label}: full flow points to the wrong pending-probe key")
    if row.get("profile") != pending.get("profile"):
        errors.append(f"{label}: full flow and pending probe profiles differ")
    if row.get("seed") != pending.get("seed") or row.get("probe") != pending.get(
        "probe"
    ):
        errors.append(f"{label}: full flow seed/probe differs from pending probe")
    if row.get("runtime_name") == pending.get("runtime_name"):
        errors.append(f"{label}: pending and full flow reused one runtime name")
    if row.get("evidence_path") == pending.get("evidence_path"):
        errors.append(f"{label}: pending and full flow reused one evidence path")
    row_isolation = row.get("runtime_isolation")
    pending_isolation = pending.get("runtime_isolation")
    if isinstance(row_isolation, dict) and isinstance(pending_isolation, dict) and (
        row_isolation.get("runtime_home") == pending_isolation.get("runtime_home")
    ):
        errors.append(f"{label}: pending and full flow reused one runtime home")
    full_candidate = row.get("candidate")
    if not isinstance(full_candidate, dict):
        errors.append(f"{label}: full-flow candidate evidence is missing")
        return
    if join_candidate_runtime_identity(full_candidate.get("runtime")) != (
        join_candidate_runtime_identity(pending_candidate.get("runtime"))
    ):
        errors.append(f"{label}: fresh executions reached different candidate runtime")
    for field in ("labels", "label_fingerprint"):
        if full_candidate.get(field) != pending_candidate.get(field):
            errors.append(f"{label}: fresh executions differ at candidate {field}")


def join_progression_settlement(
    runtime: dict[str, Any],
    expectation: dict[str, Any],
) -> dict[str, object]:
    """Model a valid intermediate scan of the finite join EXP grant."""
    selected_class = expectation.get("selected_class")
    raw_experience = expectation.get("raw_experience")
    gauge = expectation.get("class_experience_gauge")
    final_class = expectation.get("expected_result_class")
    final_level = expectation.get("expected_result_level")
    final_experience = expectation.get("expected_result_experience")
    values = (
        selected_class,
        raw_experience,
        gauge,
        final_class,
        final_level,
        final_experience,
        runtime.get("class_id"),
        runtime.get("level"),
        runtime.get("experience"),
    )
    if any(type(value) is not int for value in values):
        raise ValueError("join progression values must all be integers")
    assert isinstance(selected_class, int)
    assert isinstance(raw_experience, int)
    assert isinstance(gauge, int)
    assert isinstance(final_class, int)
    assert isinstance(final_level, int)
    assert isinstance(final_experience, int)
    class_id = int(runtime["class_id"])
    level = int(runtime["level"])
    experience = int(runtime["experience"])
    if gauge <= 0 or selected_class != final_class:
        raise ValueError("join progression expectation is invalid")
    minimum_observable_level = 2 if raw_experience >= gauge else 1
    if (
        class_id != selected_class
        or not minimum_observable_level <= level <= final_level
    ):
        raise ValueError("immediate join class/level is outside the settlement range")
    consumed = (level - 1) * gauge
    remaining = raw_experience - consumed
    if remaining < 0 or experience != remaining:
        raise ValueError("immediate join EXP is not a finite-grant settlement step")
    settled = (class_id, level, experience) == (
        final_class,
        final_level,
        final_experience,
    )
    if level == final_level and not settled:
        raise ValueError("final join settlement tuple differs")
    return {
        "status": "settled" if settled else "settling",
        "stock_scan_consumption": True,
        "selected_class": selected_class,
        "raw_experience": raw_experience,
        "class_experience_gauge": gauge,
        "consumed_raw_experience": consumed,
        "remaining_raw_experience": remaining,
        "expected_final": {
            "class_id": final_class,
            "level": final_level,
            "experience": final_experience,
        },
    }


def verify_join_runtime_row(
    row: dict[str, Any],
    *,
    profile: str,
    case: str,
    pending: dict[str, Any],
    evidence_root: Path,
    run_id: str,
    expected_gauge: int,
    errors: list[str],
) -> None:
    label = f"full {profile}/{case}"
    slug = join_character_slug(case)
    character = JOIN_CHARACTER[slug]
    expected_result = expected_join_result(case)
    scenario = expected_join_scenario(case)
    expected_raw = JOIN_RAW_EXPERIENCE[slug]
    check_equal(errors, row.get("status"), "pass", f"{label} status")
    check_equal(errors, row.get("profile"), profile, f"{label} profile")
    check_equal(errors, row.get("case"), case, f"{label} case")
    check_equal(errors, row.get("group"), expected_join_group(case), f"{label} group")
    check_equal(errors, row.get("scenario"), scenario, f"{label} scenario")
    check_equal(errors, row.get("next_scenario"), scenario + 1, f"{label} next scenario")
    check_equal(
        errors,
        row.get("legacy_level"),
        expected_join_legacy_level(case),
        f"{label} legacy level",
    )
    check_equal(
        errors,
        row.get("pending_probe_key"),
        expected_join_pending_probe_key(case),
        f"{label} pending-probe key",
    )
    check_equal(errors, row.get("virtual_display"), True, f"{label} virtual display")
    verify_isolated_display(row.get("display"), errors, f"{label} display")
    verify_join_attempt_history(row, errors=errors, label=label)
    verify_join_execution_evidence(
        row,
        expected_phase="full_flow",
        expected_evidence_root=evidence_root,
        expected_run_id=run_id,
        errors=errors,
        label=label,
    )
    verify_join_character_identity(row, slug=slug, errors=errors, label=label)
    verify_join_pending_reference(row, pending=pending, errors=errors, label=label)
    join_exp = row.get("join_experience")
    if not isinstance(join_exp, dict) or (
        join_exp.get("policy") != "one_fixed_raw_grant_no_target_level_pump"
        or join_exp.get("profile_invariant") is not True
        or join_exp.get("branch_invariant") is not True
        or join_exp.get("raw_experience") != expected_raw
    ):
        errors.append("row fixed raw EXP contract differs")
    expectation = row.get("progression_expectation")
    if not isinstance(expectation, dict):
        errors.append("row progression expectation is missing")
    else:
        expected_fields = {
            "policy": "one_fixed_raw_grant_no_target_level_pump",
            "profile_invariant": True,
            "commander_id": character["commander_id"],
            "selected_class": expected_result[0],
            "raw_experience": expected_raw,
            "expected_result_class": expected_result[0],
            "expected_result_level": expected_result[1],
            "expected_result_experience": expected_result[2],
            "reaches_another_class_choice": False,
            "next_candidates": [],
        }
        for field, expected in expected_fields.items():
            check_equal(errors, expectation.get(field), expected, f"progression {field}")
        gauge = expectation.get("class_experience_gauge")
        if not isinstance(gauge, int) or gauge <= 0:
            errors.append("progression class EXP gauge is invalid")
        elif gauge != expected_gauge:
            errors.append("progression class EXP gauge differs from release ROM")
        elif divmod(expected_raw, gauge) != (
            expected_result[1] - 1,
            expected_result[2],
        ):
            errors.append("progression result is not derived from fixed raw EXP")

    expected_runtime = {
        "class_id": expected_result[0],
        "level": expected_result[1],
        "experience": expected_result[2],
    }
    selection = row.get("selection")
    if not isinstance(selection, dict) or (
        selection.get("candidate_index") != expected_join_candidate_index(case)
        or selection.get("selected_class") != expected_result[0]
    ):
        errors.append("selected class differs from the requested branch")
    pre_completion = row.get("pre_completion")
    candidate = row.get("candidate")
    applied = row.get("applied_immediate")
    result = row.get("battle_result")
    save = row.get("save_menu")
    if not all(
        isinstance(value, dict)
        for value in (pre_completion, candidate, applied, result, save)
    ):
        errors.append(
            "pre-completion/candidate/application/result/save evidence is incomplete"
        )
        return
    verify_join_pre_completion(
        pre_completion, case=case, errors=errors, label=label
    )
    verify_join_candidate_boundary(
        candidate,
        slug=slug,
        errors=errors,
        label=f"{label} candidate",
        selected_capture_required=True,
    )
    applied_runtime = applied.get("runtime")
    if not isinstance(applied_runtime, dict) or not isinstance(expectation, dict):
        errors.append("applied progression runtime/expectation is missing")
    else:
        try:
            settlement = join_progression_settlement(
                applied_runtime,
                expectation,
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"applied progression differs: {exc}")
        else:
            check_equal(
                errors,
                applied.get("progression_settlement"),
                settlement,
                "applied progression settlement",
            )

    for section_name, section in (("result", result), ("save", save)):
        runtime = section.get("runtime")
        if not isinstance(runtime, dict) or any(
            runtime.get(field) != expected
            for field, expected in expected_runtime.items()
        ):
            errors.append(f"{section_name} class/LV/EXP differs")

    stage_gst_paths: dict[str, Path] = {}
    for section_name, section in (
        ("applied", applied),
        ("result", result),
        ("save", save),
    ):
        gst_path, _parsed_runtime = verify_join_gst_runtime(
            section,
            commander_id=int(character["commander_id"]),
            errors=errors,
            label=f"{section_name} GST",
        )
        if gst_path is not None:
            stage_gst_paths[section_name] = gst_path
        verify_join_capture_artifact(
            section.get("capture"),
            errors=errors,
            label=f"{section_name} capture",
            expected_surface={
                "result": "battle_result",
                "save": "save_menu",
            }.get(section_name),
        )
    serialized = save.get("serialized_commander")
    if not isinstance(serialized, dict) or any(
        serialized.get(field) != expected
        for field, expected in expected_runtime.items()
    ):
        errors.append("serialized save class/LV/EXP differs")
    elif serialized.get("commander_id") != character["commander_id"]:
        errors.append("serialized save commander identity differs")
    check_equal(errors, save.get("scenario"), scenario + 1, "save scenario")
    save_gst = stage_gst_paths.get("save")
    if save_gst is not None:
        try:
            snapshot = serialized_state_snapshot(save_gst)
        except (OSError, ValueError) as exc:
            errors.append(f"save GST: serialized record cannot be parsed: {exc}")
        else:
            parsed_serialized = next(
                (
                    commander
                    for commander in snapshot["commanders"]
                    if commander.get("commander_id") == character["commander_id"]
                ),
                None,
            )
            if snapshot.get("scenario") != scenario + 1:
                errors.append("save GST: serialized scenario differs")
            if save.get("record_sha256") != snapshot.get("record_sha256"):
                errors.append("save GST: serialized record SHA-256 differs")
            if serialized != parsed_serialized:
                errors.append("save GST: serialized commander differs from file")
    check_equal(
        errors,
        candidate.get("continuous_to_applied_state"),
        True,
        "candidate-to-application continuity",
    )
    check_equal(
        errors,
        applied.get("continuous_to_battle_result"),
        True,
        "application-to-result continuity",
    )
    check_equal(
        errors,
        result.get("continuous_from_applied_state"),
        True,
        "result continuity",
    )
    check_equal(
        errors,
        save.get("continuous_from_battle_result"),
        True,
        "result-to-save continuity",
    )
    save_marker = save.get("consumed_join_marker")
    verify_marker_snapshot(
        save_marker,
        expected_value=0,
        expected_address=str(character["marker_address"]),
        errors=errors,
        label="save marker",
    )
    verify_join_flush_checkpoint(
        save.get("consumed_flush"),
        marker=save_marker,
        expected_marker=0,
        errors=errors,
        label="save-menu consumed-marker final flush",
    )
    for section_name, section in (
        ("candidate", candidate),
        ("applied", applied),
        ("result", result),
    ):
        for forbidden in (
            "pending_flush_resume",
            "consumed_flush_resume",
            "resume_method",
            "resumed_gst",
            "resumed_runtime",
            "pending_join_marker",
            "consumed_join_marker",
        ):
            if forbidden in section:
                errors.append(
                    f"{section_name}: invalid intermediate flush/resume field "
                    f"{forbidden} is present"
                )
    skipped = row.get("skipped_other_candidate_screens")
    if not isinstance(skipped, list):
        errors.append("skipped candidate-screen audit is missing")
    else:
        for skipped_row in skipped:
            if not isinstance(skipped_row, dict):
                errors.append("skipped candidate-screen row is invalid")
                continue
            verify_join_gst_runtime(
                skipped_row,
                commander_id=int(character["commander_id"]),
                runtime_key="target_runtime",
                errors=errors,
                label="skipped candidate GST",
            )
            if skipped_row.get("confirmed_not_target_followup") is True:
                runtime = skipped_row.get("target_runtime")
                if not isinstance(runtime, dict) or any(
                    runtime.get(field) != expected
                    for field, expected in expected_runtime.items()
                ):
                    errors.append("skipped screen may be a target follow-up choice")


def verify_join_phase(
    phase: dict[str, Any],
    _releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
    *,
    expected_groups: tuple[str, ...],
    expected_cases: tuple[str, ...],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    entries = summary_entries(phase)
    if len(entries) != 1:
        errors.append(f"{phase.get('id')}: expected exactly one summary")
        return 0, errors, []
    path = Path(entries[0]["path"])
    data = read_json(path, errors, label=str(phase.get("id")))
    if data is None:
        return 0, errors, [{"summary": str(path), "status": "missing"}]
    evidence_root = (path.parent / "evidence").resolve()
    seen_primary_artifacts: dict[Path, str] = {}
    check_equal(errors, data.get("status"), "pass", "join status")
    check_equal(errors, data.get("run_id"), context["run_id"], "join run_id")
    check_equal(errors, data.get("profiles"), list(PROFILES), "join profiles")
    check_equal(errors, data.get("case_groups"), list(expected_groups), "join groups")
    check_equal(errors, data.get("cases"), list(expected_cases), "join cases")
    check_equal(errors, data.get("passed_profiles"), len(PROFILES), "passed_profiles")
    check_equal(errors, data.get("total_profiles"), len(PROFILES), "total_profiles")
    check_equal(
        errors,
        data.get("execution_policy"),
        JOIN_EXECUTION_POLICY,
        "join execution policy",
    )
    check_equal(
        errors,
        data.get("maximum_simultaneous_emulators"),
        len(PROFILES),
        "join maximum simultaneous emulators",
    )
    virtual_displays = data.get("virtual_displays")
    if not isinstance(virtual_displays, dict) or set(virtual_displays) != set(PROFILES):
        errors.append("join virtual-display allocation is incomplete")
        virtual_displays = {}
    else:
        for profile, display in virtual_displays.items():
            verify_isolated_display(display, errors, f"join {profile} allocated display")
    verify_join_experience_contract(
        data,
        releases=_releases,
        expected_cases=expected_cases,
        errors=errors,
        label=str(phase.get("id")),
    )
    reports = data.get("results")
    if not isinstance(reports, list) or len(reports) != len(PROFILES):
        errors.append("join summary must contain exactly three profile reports")
        reports = []
    passed = 0
    seen_profiles = set()
    release_payloads: dict[str, bytes] = {}
    for profile in PROFILES:
        try:
            release_payloads[profile] = resolve_report_path(
                _releases[profile]["path"]
            ).read_bytes()
        except (KeyError, OSError, TypeError, ValueError) as exc:
            errors.append(
                f"join {profile}: exact release ROM cannot be read: "
                f"{type(exc).__name__}: {exc}"
            )
    pending_representatives = expected_join_pending_representatives(expected_cases)
    expected_pending_keys = set(pending_representatives)
    for report in reports:
        if not isinstance(report, dict):
            continue
        profile = report.get("profile")
        if profile not in PROFILES or profile in seen_profiles:
            errors.append(f"join summary has invalid/duplicate profile {profile!r}")
            continue
        seen_profiles.add(profile)
        check_equal(errors, report.get("status"), "pass", f"join {profile} status")
        report_display = report.get("display")
        verify_isolated_display(report_display, errors, f"join {profile} report display")
        check_equal(
            errors,
            report_display,
            virtual_displays.get(profile),
            f"join {profile} allocated/report display",
        )
        check_equal(
            errors,
            report.get("passed_pending_probes"),
            len(pending_representatives),
            f"join {profile} passed_pending_probes",
        )
        check_equal(
            errors,
            report.get("total_pending_probes"),
            len(pending_representatives),
            f"join {profile} total_pending_probes",
        )
        check_equal(
            errors,
            report.get("passed_cases"),
            len(expected_cases),
            f"join {profile} passed_cases",
        )
        check_equal(
            errors,
            report.get("total_cases"),
            len(expected_cases),
            f"join {profile} total_cases",
        )
        pending_rows = report.get("pending_marker_probes")
        if not isinstance(pending_rows, list) or len(pending_rows) != len(
            pending_representatives
        ):
            errors.append(
                f"join {profile}: pending-probe count is not "
                f"{len(pending_representatives)}"
            )
            pending_rows = []
        pending_by_key: dict[str, dict[str, Any]] = {}
        valid_pending_keys = set()
        for pending_row in pending_rows:
            if not isinstance(pending_row, dict):
                errors.append(f"join {profile}: invalid pending-probe row")
                continue
            key = pending_row.get("pending_probe_key")
            if key not in expected_pending_keys or key in pending_by_key:
                errors.append(
                    f"join {profile}: invalid/duplicate pending-probe key {key!r}"
                )
                continue
            pending_by_key[str(key)] = pending_row
            pending_errors: list[str] = []
            expected_case = pending_representatives[str(key)]
            verify_join_pending_probe(
                pending_row,
                profile=str(profile),
                case=expected_case,
                evidence_root=evidence_root,
                context=context,
                errors=pending_errors,
            )
            register_unique_join_artifacts(
                pending_row,
                owner=f"pending {profile}/{key}",
                seen=seen_primary_artifacts,
                errors=pending_errors,
            )
            check_equal(
                pending_errors,
                pending_row.get("display"),
                report_display,
                "pending/report display",
            )
            if pending_errors:
                errors.extend(
                    f"join {profile}/{key}: {error}" for error in pending_errors
                )
            else:
                valid_pending_keys.add(str(key))
        if set(pending_by_key) != expected_pending_keys:
            errors.append(f"join {profile}: pending-probe key set is incomplete")
        rows = report.get("results")
        if not isinstance(rows, list) or len(rows) != len(expected_cases):
            errors.append(f"join {profile}: result count is not {len(expected_cases)}")
            continue
        seen_cases = set()
        reference_counts = {key: 0 for key in expected_pending_keys}
        for row in rows:
            if not isinstance(row, dict):
                continue
            case = row.get("case")
            if case not in expected_cases or case in seen_cases:
                errors.append(f"join {profile}: invalid/duplicate case {case!r}")
                continue
            seen_cases.add(case)
            row_errors = []
            check_equal(row_errors, row.get("status"), "pass", "status")
            check_equal(row_errors, row.get("profile"), profile, "profile")
            check_equal(
                row_errors,
                row.get("display"),
                report_display,
                "full-flow/report display",
            )
            pending_key = expected_join_pending_probe_key(str(case))
            pending = pending_by_key.get(pending_key)
            if pending is None:
                row_errors.append("matching pending-marker proof is missing")
            elif str(profile) not in release_payloads:
                row_errors.append("exact release ROM payload is unavailable")
            else:
                reference_counts[pending_key] += 1
                if pending_key not in valid_pending_keys:
                    row_errors.append("matching pending-marker proof did not validate")
                verify_join_runtime_row(
                    row,
                    profile=str(profile),
                    case=str(case),
                    pending=pending,
                    evidence_root=evidence_root,
                    run_id=str(context["run_id"]),
                    expected_gauge=class_probe.class_change_experience(
                        release_payloads[str(profile)],
                        expected_join_result(str(case))[0],
                    ),
                    errors=row_errors,
                )
                register_unique_join_artifacts(
                    row,
                    owner=f"full {profile}/{case}",
                    seen=seen_primary_artifacts,
                    errors=row_errors,
                )
            seed = row.get("seed")
            if isinstance(seed, dict):
                seed_lineage(
                    seed,
                    profile=str(profile),
                    context=context,
                    errors=row_errors,
                    label=f"join {profile}/{case}",
                )
            else:
                row_errors.append("seed lineage is missing")
            probe = row.get("probe")
            scenario = row.get("scenario")
            if isinstance(probe, dict) and isinstance(scenario, int):
                probe_lineage(
                    probe,
                    profile=str(profile),
                    scenario=scenario,
                    context=context,
                    errors=row_errors,
                    label=f"join {profile}/{case}",
                )
            else:
                row_errors.append("probe lineage is missing")
            if not row_errors:
                passed += 1
            else:
                errors.extend(
                    f"join {profile}/{case}: {error}" for error in row_errors
                )
        if seen_cases != set(expected_cases):
            errors.append(f"join {profile}: case set is incomplete")
        expected_reference_counts = {
            key: sum(
                expected_join_pending_probe_key(case) == key for case in expected_cases
            )
            for key in expected_pending_keys
        }
        if reference_counts != expected_reference_counts:
            errors.append(f"join {profile}: pending-probe reference counts differ")
    if seen_profiles != set(PROFILES):
        errors.append("join summary profile set is incomplete")
    return passed, errors, [{"summary": str(path), "status": data.get("status")}]


def verify_campaign_process_retry(
    row: dict[str, Any],
    *,
    scenario: int,
    errors: list[str],
) -> None:
    """Require whole-process retries and reject the removed GST-load path."""
    label = f"S{scenario}"
    attempt = row.get("attempt")
    history = row.get("attempt_history")
    if type(attempt) is not int or not 1 <= attempt <= 4:
        errors.append(f"{label} selected outer-process attempt is invalid")
        return
    if not isinstance(history, list) or len(history) != attempt:
        errors.append(f"{label} outer-process retry history is incomplete")
        return
    for index, item in enumerate(history, 1):
        if not isinstance(item, dict) or item.get("attempt") != index:
            errors.append(f"{label} outer-process retries are not contiguous")
            continue
        if index < attempt and (
            item.get("status") == "pass" and item.get("returncode") == 0
        ):
            errors.append(f"{label} retried after an already passing process")
        if index == attempt and (
            item.get("status") != "pass" or item.get("returncode") != 0
        ):
            errors.append(f"{label} selected outer-process retry did not pass")

    affected = scenario in result_parallel.FRESH_PROCESS_SINGLE_ATTEMPT_SCENARIOS
    if affected:
        sessions = []
        runtime_homes = []
        input_seed = row.get("input_state")
        for index, item in enumerate(history, 1):
            if not isinstance(item, dict):
                continue
            if item.get("fresh_process_attempt") != index:
                errors.append(
                    f"{label} retry {index} fresh-process number differs"
                )
            seed = item.get("input_seed_gst")
            if not isinstance(seed, dict) or not isinstance(input_seed, dict):
                errors.append(f"{label} retry {index} input-seed proof is missing")
            elif (
                resolve_report_path(seed.get("path"))
                != resolve_report_path(input_seed.get("path"))
                or seed.get("sha256") != input_seed.get("gst_sha256")
            ):
                errors.append(f"{label} retry {index} did not reuse exact input GST")
            session = item.get("runtime_session")
            if not isinstance(session, dict):
                errors.append(f"{label} retry {index} live process proof is missing")
                continue
            process_key = (
                session.get("pid"),
                session.get("proc_start_time_ticks"),
            )
            if (
                type(process_key[0]) is not int
                or type(process_key[1]) is not int
                or session.get("display") != row.get("display")
                or session.get("observed_display") != row.get("display")
                or session.get("isolated_virtual_display") is not True
                or session.get("observed_home") != session.get("runtime_home")
            ):
                errors.append(f"{label} retry {index} live process proof differs")
            sessions.append(process_key)
            runtime_homes.append(session.get("runtime_home"))
        if len(set(sessions)) != len(sessions):
            errors.append(f"{label} retries reused one BlastEm process identity")
        if len(set(runtime_homes)) != len(runtime_homes):
            errors.append(f"{label} retries reused one runtime HOME")
        if row.get("retry_policy") != "external_fresh_process_only":
            errors.append(f"{label} retry policy is not whole-process-only")
        if row.get("runtime_session") != history[-1].get("runtime_session"):
            errors.append(f"{label} selected runtime session differs from history")

    command = row.get("command")
    if not isinstance(command, list) or not all(
        isinstance(value, str) for value in command
    ):
        errors.append(f"{label} runner command is missing")
        return
    for forbidden in ("--attack-attempts", "--retry-rng-delay"):
        if forbidden in command:
            errors.append(f"{label} uses removed in-process retry option {forbidden}")
    if affected:
        if command.count("--fresh-process-attempt") != 1:
            errors.append(f"{label} fresh-process attempt proof is missing")
        else:
            index = command.index("--fresh-process-attempt")
            value = command[index + 1] if index + 1 < len(command) else None
            if value != str(attempt):
                errors.append(f"{label} fresh-process attempt number differs")


def verify_campaign(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    entries = summary_entries(phase)
    if len(entries) != 1:
        errors.append("continuous campaign: expected exactly one summary")
        return 0, errors, []
    path = Path(entries[0]["path"])
    data = read_json(path, errors, label="continuous_campaign_route")
    if data is None:
        return 0, errors, [{"summary": str(path), "status": "missing"}]
    context["campaign_summary"] = {
        "path": str(path.resolve()),
        "sha256": sha256_path(path),
    }
    check_equal(errors, data.get("status"), "pass", "campaign status")
    check_equal(errors, data.get("run_id"), context["run_id"], "campaign run_id")
    check_equal(errors, data.get("profiles"), list(PROFILES), "campaign profiles")
    check_equal(errors, data.get("manual_intervention"), False, "manual_intervention")
    check_equal(errors, data.get("automation_only"), True, "automation_only")
    check_equal(errors, data.get("attempts_per_step"), 2, "attempts_per_step")
    check_equal(
        errors,
        data.get("release_roms_unchanged"),
        True,
        "release_roms_unchanged",
    )
    for key in ("release_roms", "release_roms_after"):
        snapshots = data.get(key)
        for profile in PROFILES:
            validate_summary_rom(
                snapshots.get(profile) if isinstance(snapshots, dict) else None,
                profile=profile,
                releases=releases,
                errors=errors,
                label=f"campaign {key}/{profile}",
            )
    check_equal(errors, data.get("route_order"), list(FULL_ROUTE_ORDER), "route_order")
    check_equal(errors, data.get("continuous_save_chain"), True, "continuous_save_chain")
    reports = data.get("results")
    if not isinstance(reports, list) or len(reports) != len(PROFILES):
        errors.append("campaign summary must contain exactly three profiles")
        reports = []
    passed = 0
    seen_profiles = set()
    x4_transitions = {}
    campaign_inputs: dict[tuple[str, int], dict[str, Any]] = {}
    for report in reports:
        if not isinstance(report, dict):
            continue
        profile = report.get("profile")
        if profile not in PROFILES or profile in seen_profiles:
            errors.append(f"campaign has invalid/duplicate profile {profile!r}")
            continue
        seen_profiles.add(profile)
        report_errors = []
        check_equal(report_errors, report.get("status"), "pass", "status")
        check_equal(report_errors, report.get("run_id"), context["run_id"], "run_id")
        report_display = report.get("display")
        verify_isolated_display(report_display, report_errors, "campaign display")
        check_equal(
            report_errors,
            report.get("manual_intervention"),
            False,
            "manual_intervention",
        )
        validate_summary_rom(
            report.get("release_rom"),
            profile=str(profile),
            releases=releases,
            errors=report_errors,
            label=f"campaign {profile} release",
        )
        check_equal(report_errors, report.get("passed_steps"), 31, "passed_steps")
        check_equal(report_errors, report.get("total_steps"), 31, "total_steps")
        initial = report.get("initial_seed")
        if isinstance(initial, dict):
            seed_lineage(
                {
                    "path": initial.get("path"),
                    "sha256": initial.get("gst_sha256"),
                },
                profile=str(profile),
                context=context,
                errors=report_errors,
                label=f"campaign {profile}",
            )
        else:
            report_errors.append("initial seed snapshot is missing")
        rows = report.get("results")
        if not isinstance(rows, list) or len(rows) != len(FULL_ROUTE_ORDER):
            report_errors.append("route result count is not 31")
            rows = []
        seen_steps = []
        previous_output_hash = None
        previous_output_gst_hash = None
        previous_output_path: Path | None = None
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            scenario = row.get("scenario")
            if index >= len(FULL_ROUTE_ORDER) or scenario != FULL_ROUTE_ORDER[index]:
                report_errors.append(f"route index {index} has scenario {scenario!r}")
                continue
            seen_steps.append(scenario)
            row_ok = row.get("status") == "pass" and row.get("returncode") == 0
            if row.get("route_index") != index:
                row_ok = False
                report_errors.append(f"S{scenario} route index differs")
            if row.get("display") != report_display:
                row_ok = False
                report_errors.append(f"S{scenario} display differs from profile Xvfb")
            if row.get("run_id") != context["run_id"]:
                row_ok = False
                report_errors.append(f"S{scenario} run_id differs")
            if row.get("manual_intervention") is not False:
                row_ok = False
                report_errors.append(f"S{scenario} manual-intervention proof differs")
            retry_errors: list[str] = []
            verify_campaign_process_retry(
                row,
                scenario=int(scenario),
                errors=retry_errors,
            )
            if retry_errors:
                row_ok = False
                report_errors.extend(retry_errors)
            probe = context.get("probes", {}).get((profile, scenario))
            if not isinstance(probe, dict) or resolve_report_path(row.get("rom")) != Path(probe["path"]):
                row_ok = False
                report_errors.append(f"S{scenario} did not use the planned probe")
            input_state = row.get("input_state")
            if not isinstance(input_state, dict):
                row_ok = False
                report_errors.append(f"S{scenario} input snapshot is missing")
            else:
                input_path = resolve_report_path(input_state.get("path"))
                input_gst_hash = input_state.get("gst_sha256")
                input_record_hash = input_state.get("record_sha256")
                input_valid = True
                if (
                    not input_path.is_file()
                    or not isinstance(input_gst_hash, str)
                    or len(input_gst_hash) != 64
                    or sha256_path(input_path) != input_gst_hash
                    or not isinstance(input_record_hash, str)
                    or len(input_record_hash) != 64
                ):
                    input_valid = False
                    row_ok = False
                    report_errors.append(f"S{scenario} input GST/hash proof broke")
                if index == 0:
                    expected_seed = context.get("seeds", {}).get(profile)
                    if (
                        not isinstance(expected_seed, dict)
                        or input_path != Path(expected_seed["path"])
                        or input_gst_hash != expected_seed["sha256"]
                        or input_record_hash != context.get("fresh_record_sha256")
                    ):
                        row_ok = False
                        report_errors.append(
                            f"S{scenario} did not begin from the exact fresh S1 seed"
                        )
                        input_valid = False
                elif (
                    input_path != previous_output_path
                    or input_gst_hash != previous_output_gst_hash
                    or input_record_hash != previous_output_hash
                ):
                    input_valid = False
                    row_ok = False
                    report_errors.append(f"S{scenario} exact save-chain input broke")
                if input_valid:
                    campaign_inputs[(str(profile), int(scenario))] = {
                        "path": str(input_path),
                        "sha256": input_gst_hash,
                        "record_sha256": input_record_hash,
                        "route_index": index,
                        "source": (
                            "fresh_s1_seed"
                            if scenario == 1
                            else "continuous_campaign_input"
                        ),
                    }
            expected_next = NEXT_SCENARIO[int(scenario)]
            output_state = row.get("output_state")
            if expected_next is None:
                if output_state is not None:
                    row_ok = False
                    report_errors.append("terminal S27 unexpectedly produced a next save")
            elif not isinstance(output_state, dict) or output_state.get("scenario") != expected_next:
                row_ok = False
                report_errors.append(
                    f"S{scenario} output scenario is not {expected_next}"
                )
            else:
                output_path = resolve_report_path(output_state.get("path"))
                output_gst_hash = output_state.get("gst_sha256")
                output_record_hash = output_state.get("record_sha256")
                if (
                    not output_path.is_file()
                    or not isinstance(output_gst_hash, str)
                    or len(output_gst_hash) != 64
                    or sha256_path(output_path) != output_gst_hash
                    or not isinstance(output_record_hash, str)
                    or len(output_record_hash) != 64
                ):
                    row_ok = False
                    report_errors.append(f"S{scenario} output GST/hash proof broke")
                previous_output_path = output_path
                previous_output_gst_hash = output_gst_hash
                previous_output_hash = output_record_hash
            if scenario == 31 and isinstance(output_state, dict):
                x4_transitions[profile] = {
                    "output_scenario": output_state.get("scenario"),
                    "record_sha256": output_state.get("record_sha256"),
                }
            if row_ok:
                passed += 1
        if seen_steps != list(FULL_ROUTE_ORDER):
            report_errors.append("route order/coverage is incomplete")
        errors.extend(
            f"campaign {profile}: {error}" for error in report_errors
        )
    if seen_profiles != set(PROFILES):
        errors.append("campaign profile set is incomplete")
    expected_campaign_inputs = {
        (profile, scenario) for profile in PROFILES for scenario in SCENARIOS
    }
    if set(campaign_inputs) != expected_campaign_inputs:
        errors.append("campaign exact per-profile S1-S31 input set is incomplete")
    context["campaign"] = data
    context["campaign_inputs"] = campaign_inputs
    context["x4_transitions"] = x4_transitions
    return passed, errors, [{"summary": str(path), "status": data.get("status")}]


def verify_runestone(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    entries = summary_entries(phase)
    if len(entries) != 1:
        errors.append("runestone: expected exactly one summary")
        return 0, errors, []
    path = Path(entries[0]["path"])
    data = read_json(path, errors, label="runestone_restart")
    if data is None:
        return 0, errors, [{"summary": str(path), "status": "missing"}]
    check_equal(errors, data.get("status"), "pass", "runestone status")
    check_equal(errors, data.get("run_id"), context["run_id"], "runestone run_id")
    check_equal(errors, data.get("profiles"), list(PROFILES), "runestone profiles")
    check_equal(errors, data.get("tiers"), [2, 3, 4, 5], "runestone tiers")
    check_equal(
        errors,
        data.get("characters"),
        ["keith", "lester", "jessica"],
        "runestone characters",
    )
    check_equal(errors, data.get("release_roms_unchanged"), True, "release_roms_unchanged")
    for key in ("release_roms_before", "release_roms_after"):
        snapshots = data.get(key, {})
        for profile in PROFILES:
            value = snapshots.get(profile) if isinstance(snapshots, dict) else None
            validate_summary_rom(
                value,
                profile=profile,
                releases=releases,
                errors=errors,
                label=f"runestone {key}/{profile}",
            )
    rows = data.get("results")
    if not isinstance(rows, list) or len(rows) != 36:
        errors.append("runestone result count is not 36")
        rows = []
    expected = {
        (profile, character, tier)
        for profile in PROFILES
        for character in ("keith", "lester", "jessica")
        for tier in (2, 3, 4, 5)
    }
    passed_rows = set()
    for row in rows:
        if not isinstance(row, dict):
            errors.append("runestone result contains a non-object row")
            continue
        key = (row.get("profile"), row.get("character"), row.get("current_tier"))
        if key not in expected:
            errors.append(f"runestone result has invalid case {key!r}")
            continue
        profile, character, tier = key
        expected_character = RUNESTONE_EXPECTED[str(character)]
        surface = row.get("candidate_label_surface")
        state = row.get("state")
        production = row.get("production_resume")
        marker = row.get("marker_setup")
        runtime_marker = row.get("runtime_join_marker")
        expected_fingerprint = expected_character["label_fingerprint"]
        runtime_marker_errors: list[str] = []
        verify_isolated_display(
            row.get("display"), runtime_marker_errors, "runestone job display"
        )
        runtime_marker_path = verify_marker_snapshot(
            runtime_marker,
            expected_value=0,
            expected_address=str(expected_character["marker_address"]),
            errors=runtime_marker_errors,
            label="runtime join marker",
        )
        if not isinstance(runtime_marker, dict) or (
            runtime_marker.get("status") != "pass"
        ):
            runtime_marker_errors.append("runtime join marker status differs")
        row_ok = (
            row.get("status") == "pass"
            and row.get("returncode") == 0
            and row.get("candidate_labels")
            == expected_character["candidate_labels"]
            and row.get("selected_class")
            == expected_character["selected_class"]
            and isinstance(surface, dict)
            and surface.get("status") == "pass"
            and surface.get("expected_fingerprint") == expected_fingerprint
            and surface.get("observed_fingerprints")
            == [expected_fingerprint] * 3
            and isinstance(state, dict)
            and state.get("class_id") == expected_character["selected_class"]
            and state.get("commander_id_after_apply")
            == expected_character["commander_id"]
            and state.get("level") == 1
            and state.get("experience") == 0
            and state.get("equipped_item_after_use") == "0x00"
            and isinstance(production, dict)
            and production.get("status") == "pass"
            and production.get("resume_operand") == "0x014D0C"
            and production.get("expected_production_target") == "0x31E000"
            and production.get("release_target") == "0x31E000"
            and production.get("probe_target") == "0x31E000"
            and production.get("operand_byte_identical") is True
            and isinstance(production.get("wrapper_size"), int)
            and production.get("wrapper_size") > 0
            and production.get("wrapper_byte_identical") is True
            and production.get("release_wrapper_matches_current_builder") is True
            and isinstance(production.get("release_wrapper_sha256"), str)
            and production.get("release_wrapper_sha256")
            == production.get("probe_wrapper_sha256")
            and production.get("release_wrapper_sha256")
            == production.get("expected_wrapper_sha256")
            and isinstance(marker, dict)
            and marker.get("status") == "pass"
            and marker.get("entry_target") == marker.get("probe_wrapper")
            and marker.get("marker_address")
            == expected_character["marker_address"]
            and marker.get("clear_instruction")
            == "4239" + expected_character["marker_address"][2:].lower()
            and marker.get("clear_instruction_offset")
            == marker.get("probe_wrapper")
            and marker.get("stock_handler_target") == "0x01480C"
            and marker.get("clear_precedes_stock_handler") is True
            and marker.get("release_probe_region_empty") is True
            and marker.get("setup_sha256")
            == marker.get("expected_setup_sha256")
            and runtime_marker_path is not None
            and not runtime_marker_errors
        )
        if not row_ok:
            errors.append(
                f"runestone {profile}/{character}/tier{tier}: "
                "production-resume, explicit marker-clear, LV1/EXP0 "
                "application, consumed runtime join marker, or three-label "
                "fingerprint proof is incomplete"
            )
            errors.extend(
                f"runestone {profile}/{character}/tier{tier}: {error}"
                for error in runtime_marker_errors
            )
            continue
        if key in passed_rows:
            errors.append(f"runestone result duplicates case {key!r}")
            continue
        passed_rows.add(key)
    if passed_rows != expected:
        errors.append("runestone passing Cartesian case set is incomplete")
    check_equal(errors, data.get("passed_tasks"), 36, "passed_tasks")
    check_equal(errors, data.get("total_tasks"), 36, "total_tasks")
    return len(passed_rows & expected), errors, [
        {"summary": str(path), "status": data.get("status")}
    ]


def verify_scenario6(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    passed = 0
    details = []
    for profile, (path, data) in profile_summaries(phase, errors).items():
        row_errors = []
        check_equal(row_errors, data.get("schema_version"), 1, "schema_version")
        check_equal(row_errors, data.get("status"), "pass", "status")
        check_equal(row_errors, data.get("run_id"), context["run_id"], "run_id")
        check_equal(row_errors, data.get("profile"), profile, "profile")
        check_equal(row_errors, data.get("scenario"), 6, "scenario")
        verify_isolated_display(
            data.get("virtual_display"), row_errors, "scenario6 virtual display"
        )
        candidate = data.get("candidate")
        validate_summary_rom(
            candidate,
            profile=profile,
            releases=releases,
            errors=row_errors,
            label="candidate",
        )
        seed = data.get("seed")
        if isinstance(seed, dict):
            seed_lineage(
                seed,
                profile=profile,
                context=context,
                errors=row_errors,
                label=f"scenario6/{profile}",
            )
        else:
            row_errors.append("seed lineage is missing")
        source = context.get("source_rom")
        probe = data.get("probe")
        expected_probe: bytes | None = None
        if not isinstance(source, dict) or not isinstance(probe, dict):
            row_errors.append("source-locked Scenario 6 probe proof is missing")
        else:
            source_path = Path(str(source.get("path", ""))).resolve()
            release_path = Path(str(releases[profile]["path"])).resolve()
            probe_path = resolve_report_path(probe.get("path"))
            try:
                expected_probe = bytes(
                    scenario6_probe.build_probe(
                        release_path.read_bytes(),
                        source_path.read_bytes(),
                    )
                )
                actual_probe = probe_path.read_bytes()
            except (OSError, ValueError) as exc:
                row_errors.append(
                    "cannot rebuild/read exact Scenario 6 probe: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                if actual_probe != expected_probe:
                    row_errors.append(
                        "Scenario 6 probe is not the exact source-locked derivative"
                    )
                if probe.get("sha256") != hashlib.sha256(actual_probe).hexdigest():
                    row_errors.append("Scenario 6 probe SHA-256 differs")
                delta = probe.get("delta_from_candidate")
                expected_delta = scenario6_surface.probe_delta_report(
                    release_path.read_bytes(),
                    expected_probe,
                )
                if delta != expected_delta or expected_delta.get("status") != "pass":
                    row_errors.append(
                        "Scenario 6 two-coordinate-byte diagnostic delta differs"
                    )
        identity = data.get("scenario_identity")
        if not isinstance(identity, dict) or identity.get("status") != "pass":
            row_errors.append("Scenario 6 runtime scenario identity is missing")
        movement = data.get("movement", {})
        check_equal(
            row_errors,
            movement.get("expected_start") if isinstance(movement, dict) else None,
            [6, 4],
            "movement.expected_start",
        )
        check_equal(
            row_errors,
            movement.get("expected_destination") if isinstance(movement, dict) else None,
            [7, 4],
            "movement.expected_destination",
        )
        evidence = data.get("evidence")
        evidence_paths: dict[str, Path] = {}
        expected_evidence = (
            "preparation",
            "active_command",
            "move_target",
            "after_move_before_standby",
            "runestone_dialogue",
            "after_item_acquisition",
            "before_move_gst",
            "runestone_dialogue_gst",
            "after_item_acquisition_gst",
        )
        if not isinstance(evidence, dict) or set(evidence) != set(expected_evidence):
            row_errors.append("Scenario 6 evidence artifact set is incomplete")
        else:
            for label in expected_evidence:
                value = evidence.get(label)
                if not isinstance(value, dict):
                    row_errors.append(f"Scenario 6 {label} artifact is missing")
                    continue
                artifact = resolve_report_path(value.get("path"))
                digest = value.get("sha256")
                if (
                    not artifact.is_file()
                    or not isinstance(digest, str)
                    or len(digest) != 64
                    or sha256_path(artifact) != digest
                ):
                    row_errors.append(f"Scenario 6 {label} artifact/hash differs")
                    continue
                evidence_paths[label] = artifact
        if len(set(evidence_paths.values())) != len(evidence_paths):
            row_errors.append("Scenario 6 evidence artifacts are reused")

        expected_states = (
            ("before", "before_move_gst", [6, 4], 0),
            ("dialogue", "runestone_dialogue_gst", [7, 4], 1),
            ("after_acquisition", "after_item_acquisition_gst", [7, 4], 1),
        )
        for state_name, gst_name, coordinate, acted in expected_states:
            gst_path = evidence_paths.get(gst_name)
            declared = movement.get(state_name) if isinstance(movement, dict) else None
            if gst_path is None or not isinstance(declared, dict):
                row_errors.append(f"Scenario 6 {state_name} runtime state is missing")
                continue
            try:
                parsed = scenario6_surface.commander_state(gst_path)
            except (OSError, ValueError) as exc:
                row_errors.append(
                    f"Scenario 6 {state_name} GST cannot be parsed: "
                    f"{type(exc).__name__}: {exc}"
                )
                continue
            if parsed != declared:
                row_errors.append(
                    f"Scenario 6 {state_name} reported state differs from GST"
                )
            if (
                [parsed.get("x"), parsed.get("y")] != coordinate
                or parsed.get("acted_flag") != acted
                or parsed.get("commander_id") != 1
                or type(parsed.get("hp")) is not int
                or parsed["hp"] <= 0
            ):
                row_errors.append(
                    f"Scenario 6 {state_name} movement/acted identity differs"
                )

        dialogue_path = evidence_paths.get("runestone_dialogue")
        if dialogue_path is None:
            row_errors.append("Scenario 6 Rune Stone dialogue capture is missing")
        else:
            try:
                dialogue_visible = scenario6_surface.blastem.battle_dialogue_visible(
                    dialogue_path
                )
            except (OSError, ValueError) as exc:
                row_errors.append(
                    "Scenario 6 dialogue capture cannot be classified: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                if not dialogue_visible:
                    row_errors.append("Scenario 6 Rune Stone dialogue is not visible")
        acquisition = data.get("inventory_acquisition", {})
        check_equal(
            row_errors,
            acquisition.get("status") if isinstance(acquisition, dict) else None,
            "pass",
            "inventory_acquisition.status",
        )
        before_gst = evidence_paths.get("before_move_gst")
        after_gst = evidence_paths.get("after_item_acquisition_gst")
        if before_gst is not None and after_gst is not None:
            try:
                recomputed_acquisition = (
                    scenario6_surface.runestone_acquisition_report(
                        scenario6_surface.inventory_records(before_gst),
                        scenario6_surface.inventory_records(after_gst),
                    )
                )
            except (OSError, ValueError) as exc:
                row_errors.append(
                    "Scenario 6 inventory GST cannot be parsed: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                if acquisition != recomputed_acquisition:
                    row_errors.append(
                        "Scenario 6 reported inventory delta differs from GST"
                    )
        if not row_errors:
            passed += 1
        errors.extend(f"scenario6/{profile}: {error}" for error in row_errors)
        details.append({
            "profile": profile,
            "summary": str(path),
            "status": "pass" if not row_errors else "fail",
        })
    return passed, errors, details


def verify_all_true_checks(
    value: object,
    *,
    required: tuple[str, ...],
    errors: list[str],
    label: str,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: checks are missing")
        return
    for name in required:
        if value.get(name) is not True:
            errors.append(f"{label}: {name} did not pass")
    false_checks = sorted(name for name, passed in value.items() if passed is not True)
    if false_checks:
        errors.append(f"{label}: non-passing checks {false_checks!r}")


def verify_mounted_image(value: object, errors: list[str], label: str) -> None:
    verify_hashed_artifact(
        value,
        path_key="path",
        sha_key="sha256",
        errors=errors,
        label=label,
    )
    if not isinstance(value, dict) or value.get("dimensions") != [320, 240]:
        errors.append(f"{label}: dimensions are not 320x240")


def verify_mounted_runtime(
    value: object,
    *,
    expected: dict[str, object],
    errors: list[str],
    label: str,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: runtime report is missing")
        return
    check_equal(errors, value.get("status"), "pass", f"{label} status")
    verify_hashed_artifact(
        value,
        path_key="path",
        sha_key="sha256",
        errors=errors,
        label=f"{label} GST",
    )
    verify_all_true_checks(
        value.get("checks"),
        required=(
            "class_is_selected_mounted_lord",
            "commander_identity_preserved",
            "alive_and_visible",
            "level_reset_to_one",
            "experience_reset_to_zero",
            "class_stats_match_mounted_source",
            "display_at_matches",
            "display_df_matches",
        ),
        errors=errors,
        label=f"{label} runtime",
    )
    values = value.get("values")
    expected_values = {
        "class_id": expected["class_id"],
        "commander_id": expected["commander_id"],
        "level": 1,
        "experience": 0,
        "at": 23,
        "df": 18,
        "class_stats": expected["class_stats"],
        "move": expected["move"],
        "a_plus": expected["a_plus"],
        "d_plus": expected["d_plus"],
    }
    if not isinstance(values, dict) or any(
        values.get(field) != wanted for field, wanted in expected_values.items()
    ):
        errors.append(f"{label}: exact mounted runtime values differ")
    elif (
        type(values.get("hp")) is not int
        or values["hp"] <= 0
        or values.get("x") in (0, 0xFF)
        or values.get("y") in (0, 0xFF)
    ):
        errors.append(f"{label}: mounted commander is not alive and visible")


def verify_mounted_evidence(
    data: dict[str, Any],
    *,
    profile: str,
    case: str,
    releases: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    expected = MOUNTED_EXPECTED[case]
    check_equal(errors, data.get("status"), "pass", "mounted evidence status")
    check_equal(errors, data.get("case"), case, "mounted evidence case")
    validate_summary_rom(
        data.get("profile_input"),
        profile=profile,
        releases=releases,
        errors=errors,
        label="mounted evidence profile_input",
    )
    isolation = data.get("runtime_isolation")
    if not isinstance(isolation, dict) or (
        isolation.get("required_absent_before_launch") is not True
        or isolation.get("existing_blastem_pids_before_launch") != []
        or isolation.get("reuse_runtime_state") is not False
        or not isolation.get("runtime_home")
    ):
        errors.append("mounted runtime isolation proof differs")
    diagnostic = data.get("diagnostic")
    if not isinstance(diagnostic, dict):
        errors.append("mounted diagnostic proof is missing")
    else:
        for path_key, sha_key, artifact_label in (
            ("rom", "rom_sha256", "mounted diagnostic ROM"),
            ("manifest", "manifest_sha256", "mounted diagnostic manifest"),
        ):
            verify_hashed_artifact(
                diagnostic,
                path_key=path_key,
                sha_key=sha_key,
                errors=errors,
                label=artifact_label,
            )
        if (
            diagnostic.get("changed_byte_count") != 65
            or diagnostic.get("exact_derivative_verified_before_launch") is not True
        ):
            errors.append("mounted exact diagnostic delta proof differs")

    class_change = data.get("class_change")
    if not isinstance(class_change, dict):
        errors.append("mounted class-change evidence is missing")
    else:
        for key in ("trigger", "candidate_first", "candidate_mounted_lord"):
            verify_mounted_image(
                class_change.get(key), errors, f"mounted class-change {key}"
            )
        if (
            class_change.get("selected_candidate_index") != 2
            or class_change.get("selected_class_id") != expected["class_id"]
        ):
            errors.append("mounted class-change selection differs")

    map_report = data.get("map")
    if not isinstance(map_report, dict):
        errors.append("mounted map evidence is missing")
    else:
        verify_mounted_image(map_report.get("capture"), errors, "mounted map capture")
        verify_mounted_runtime(
            map_report.get("runtime"),
            expected=expected,
            errors=errors,
            label="mounted map",
        )
        sprite = map_report.get("sprite")
        if not isinstance(sprite, dict):
            errors.append("mounted map sprite proof is missing")
        else:
            check_equal(errors, sprite.get("status"), "pass", "mounted sprite status")
            verify_all_true_checks(
                sprite.get("checks"),
                required=(
                    "mapped_to_reviewed_mounted_sprite",
                    "frames_differ_from_wrong_class",
                    "rom_payload_loaded_into_vram",
                    "actual_plane_a_unit_uses_verified_payload",
                ),
                errors=errors,
                label="mounted map sprite",
            )
            if sprite.get("sprite_id") == sprite.get("wrong_sprite_id"):
                errors.append("mounted map sprite still aliases the wrong class")

    status = data.get("status_detail_and_exp")
    if not isinstance(status, dict):
        errors.append("mounted status/EXP evidence is missing")
    else:
        verify_mounted_runtime(
            status.get("runtime"),
            expected=expected,
            errors=errors,
            label="mounted status",
        )
        surface = status.get("surface")
        if not isinstance(surface, dict):
            errors.append("mounted status surface proof is missing")
        else:
            check_equal(errors, surface.get("status"), "pass", "status surface")
            verify_mounted_image(surface, errors, "mounted status capture")
            verify_all_true_checks(
                surface.get("checks"),
                required=(
                    "command_panel_visible",
                    "status_detail_panel_visible",
                    "bottom_status_and_exp_bar_visible",
                    "runtime_status_is_exact",
                    "class_name_source_is_selected_class",
                    "exp_bar_source_is_zero",
                ),
                errors=errors,
                label="mounted status surface",
            )
            expected_visible = surface.get("expected_visible_values")
            if not isinstance(expected_visible, dict) or any(
                expected_visible.get(field) != wanted
                for field, wanted in {
                    "class": expected["class_name"],
                    "level": 1,
                    "experience": 0,
                    "at": 23,
                    "df": 18,
                    "move": expected["move"],
                    "a_plus": expected["a_plus"],
                    "d_plus": expected["d_plus"],
                }.items()
            ):
                errors.append("mounted visible status values differ")

    attack = data.get("side_view_attack")
    if not isinstance(attack, dict):
        errors.append("mounted side-view attack evidence is missing")
        return
    animation = attack.get("animation")
    if not isinstance(animation, dict):
        errors.append("mounted side-view animation proof is missing")
    else:
        check_equal(errors, animation.get("status"), "pass", "attack animation")
        verify_all_true_checks(
            animation.get("checks"),
            required=(
                "multiple_live_battle_frames_captured",
                "side_view_attacker_region_animated",
                "commander_specific_combat_payload_observed",
            ),
            errors=errors,
            label="mounted attack animation",
        )
        if (
            type(animation.get("battle_frame_count")) is not int
            or animation["battle_frame_count"] < 2
            or type(animation.get("unique_attacker_crop_count")) is not int
            or animation["unique_attacker_crop_count"] < 2
            or type(animation.get("passing_combat_state_count")) is not int
            or animation["passing_combat_state_count"] < 1
        ):
            errors.append("mounted live animated combat counts are insufficient")
    samples = attack.get("samples")
    if not isinstance(samples, list) or len(samples) < 4:
        errors.append("mounted attack sample set is too small")
    else:
        for index, sample in enumerate(samples):
            verify_mounted_image(sample, errors, f"mounted attack sample {index}")
    states = attack.get("combat_states")
    if not isinstance(states, list) or not states:
        errors.append("mounted combat GST evidence is missing")
    else:
        for index, state in enumerate(states):
            if not isinstance(state, dict):
                errors.append(f"mounted combat state {index} is invalid")
                continue
            check_equal(errors, state.get("status"), "pass", "combat state status")
            verify_hashed_artifact(
                state,
                path_key="path",
                sha_key="sha256",
                errors=errors,
                label=f"mounted combat state {index} GST",
            )
            resource = state.get("resource")
            if not isinstance(resource, dict):
                errors.append(f"mounted combat state {index} resource is missing")
                continue
            check_equal(errors, resource.get("status"), "pass", "combat resource")
            check_equal(
                errors,
                resource.get("raw_resource_id"),
                expected["combat_resource"],
                "commander combat resource",
            )
            verify_all_true_checks(
                resource.get("checks"),
                required=(
                    "commander_override_resource_selected",
                    "expected_payload_at_battle_destination",
                    "expected_payload_present_in_vram",
                    "sister_vampire_or_generic_fallback_absent",
                ),
                errors=errors,
                label="mounted combat resource",
            )
            forbidden = resource.get("forbidden_fallbacks")
            if not isinstance(forbidden, list) or any(
                not isinstance(row, dict)
                or row.get("loaded_at_combat_destination") is not False
                for row in forbidden
            ):
                errors.append("forbidden Sister/Vampire fallback reached combat VRAM")


def verify_mounted(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    _context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    entries = summary_entries(phase)
    if len(entries) != 1:
        errors.append("mounted combat: expected exactly one summary")
        return 0, errors, []
    path = Path(entries[0]["path"])
    data = read_json(path, errors, label="mounted_lord_combat")
    if data is None:
        return 0, errors, [{"summary": str(path), "status": "missing"}]
    check_equal(errors, data.get("status"), "pass", "mounted status")
    profiles = data.get("profiles", {})
    for profile in PROFILES:
        validate_summary_rom(
            profiles.get(profile) if isinstance(profiles, dict) else None,
            profile=profile,
            releases=releases,
            errors=errors,
            label=f"mounted profile {profile}",
        )
    rows = data.get("jobs")
    if not isinstance(rows, list) or len(rows) != 6:
        errors.append("mounted combat result count is not 6")
        rows = []
    expected = {
        (profile, case)
        for profile in PROFILES
        for case in ("keith", "lester")
    }
    actual = set()
    runtime_homes = set()
    for row in rows:
        if not isinstance(row, dict):
            errors.append("mounted result contains a non-object row")
            continue
        key = (row.get("profile"), row.get("case"))
        if key not in expected or key in actual:
            errors.append(f"mounted result has invalid/duplicate case {key!r}")
            continue
        profile, case = str(key[0]), str(key[1])
        row_errors: list[str] = []
        check_equal(row_errors, row.get("status"), "pass", "job status")
        verify_isolated_display(row.get("display"), row_errors, "job display")
        evidence_path = verify_hashed_artifact(
            row,
            path_key="evidence",
            sha_key="evidence_sha256",
            errors=row_errors,
            label="mounted evidence JSON",
        )
        evidence = (
            read_json(evidence_path, row_errors, label="mounted evidence")
            if evidence_path is not None
            else None
        )
        if evidence is not None:
            verify_mounted_evidence(
                evidence,
                profile=profile,
                case=case,
                releases=releases,
                errors=row_errors,
            )
            isolation = evidence.get("runtime_isolation")
            runtime_home = (
                isolation.get("runtime_home")
                if isinstance(isolation, dict)
                else None
            )
            if runtime_home in runtime_homes or not runtime_home:
                row_errors.append("mounted runtime home is missing or reused")
            else:
                runtime_homes.add(runtime_home)
        if row_errors:
            errors.extend(
                f"mounted {profile}/{case}: {error}" for error in row_errors
            )
            continue
        actual.add(key)
    if actual != expected:
        errors.append("mounted passing profile/case set is incomplete")
    check_equal(errors, data.get("pass_count"), 6, "mounted pass_count")
    check_equal(errors, data.get("job_count"), 6, "mounted job_count")
    return len(actual & expected), errors, [
        {"summary": str(path), "status": data.get("status")}
    ]


def verify_final_ending(
    phase: dict[str, Any],
    _releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    errors: list[str] = []
    passed = 0
    details = []
    ending_profiles = set()
    for profile, (path, data) in profile_summaries(phase, errors).items():
        row_errors = []
        check_equal(row_errors, data.get("status"), "pass", "status")
        check_equal(row_errors, data.get("profile"), profile, "profile")
        check_equal(row_errors, data.get("scenario"), 27, "scenario")
        check_equal(row_errors, data.get("run_id"), context["run_id"], "run_id")
        rom = data.get("rom")
        if isinstance(rom, dict):
            probe_lineage(
                rom,
                profile=profile,
                scenario=27,
                context=context,
                errors=row_errors,
                label=f"ending {profile}",
            )
        else:
            row_errors.append("ending probe ROM lineage is missing")
        seed = data.get("seed")
        if isinstance(seed, dict):
            seed_lineage(
                seed,
                profile=profile,
                context=context,
                errors=row_errors,
                label=f"ending {profile}",
            )
        else:
            row_errors.append("ending seed lineage is missing")
        check_equal(
            row_errors,
            data.get("seed_unchanged"),
            True,
            "seed_unchanged",
        )
        stage = data.get("diagnostic_runtime_stage")
        if not isinstance(stage, dict):
            row_errors.append("S27 diagnostic_runtime_stage proof is missing")
        else:
            expected_stage = {
                "harness_only": True,
                "natural_full_battle_clear": False,
                "product_release_rom_changed": False,
                "start_callback_operand_address": (
                    f"0x{scenario27_probe.START_MENU_ENTRY_OPERAND:06X}"
                ),
                "start_wrapper_address": (
                    f"0x{scenario27_probe.RUNTIME_WRAPPER:06X}"
                ),
                "stock_start_entry_address": (
                    f"0x{scenario27_probe.START_MENU_ENTRY:06X}"
                ),
                "wrapper_sha256": hashlib.sha256(
                    scenario27_probe.completion_hp_wrapper_code()
                ).hexdigest(),
                "runtime_hp_address": (
                    f"0x{scenario27_probe.BERNHARDT_RUNTIME_HP_ADDRESS:08X}"
                ),
                "ordinary_stock_attack_death_and_ending_handlers": True,
            }
            for key, expected in expected_stage.items():
                check_equal(
                    row_errors,
                    stage.get(key),
                    expected,
                    f"diagnostic_runtime_stage.{key}",
                )
            staged_bernhardt = stage.get("bernhardt")
            if not isinstance(staged_bernhardt, dict):
                row_errors.append("S27 staged Bernhardt HP1 proof is missing")
            else:
                for key, expected in {
                    "class_id": 0x4E,
                    "name_id": 0x0E,
                    "defeated": False,
                    "hp": scenario27_probe.PROBE_BERNHARDT_HP,
                    "x": scenario27_probe.PROBE_BERNHARDT_X,
                    "y": scenario27_probe.PROBE_BERNHARDT_Y,
                }.items():
                    check_equal(
                        row_errors,
                        staged_bernhardt.get(key),
                        expected,
                        f"diagnostic_runtime_stage.bernhardt.{key}",
                    )
        fin = data.get("fin")
        if not isinstance(fin, dict) or not fin.get("sha256"):
            row_errors.append("terminal Fin evidence is missing")
        bernhardt = data.get("bernhardt_runtime_state")
        if not isinstance(bernhardt, dict) or bernhardt.get("hp") != 0:
            row_errors.append("Bernhardt HP-zero runtime proof is missing")
        elif (
            bernhardt.get("class_id") != 0x4E
            or bernhardt.get("name_id") != 0x0E
        ):
            row_errors.append("defeated Bernhardt runtime identity is missing")
        identity = data.get("scenario_identity", {})
        fixed = identity.get("fixed_record_layout") if isinstance(identity, dict) else None
        fixed_count = 0
        if not isinstance(fixed, dict):
            row_errors.append("final fixed-record layout proof is missing")
        else:
            check_equal(row_errors, fixed.get("status"), "pass", "fixed status")
            check_equal(row_errors, fixed.get("fixed_record_count"), 10, "fixed count")
            check_equal(row_errors, fixed.get("mismatch_count"), 0, "fixed mismatches")
            check_equal(
                row_errors,
                fixed.get("checked_fields"),
                ["class_id", "name_id", "side_id", "level", "x", "y", "mercenaries"],
                "fixed checked fields",
            )
            records = fixed.get("records")
            if isinstance(records, list) and len(records) == 10 and all(
                isinstance(record, dict) and not record.get("protected_mismatches")
                for record in records
            ):
                fixed_count = 10
            else:
                row_errors.append("not all ten final fixed records are clean")
        if not row_errors:
            passed += 1 + fixed_count
            ending_profiles.add(profile)
        errors.extend(f"ending/{profile}: {error}" for error in row_errors)
        details.append({
            "profile": profile,
            "summary": str(path),
            "ending_pass": not row_errors,
            "final_enemy_records_passed": fixed_count if not row_errors else 0,
        })

    campaign = context.get("campaign")
    x4 = context.get("x4_transitions", {})
    campaign_reports = {
        report.get("profile"): report
        for report in campaign.get("results", [])
        if isinstance(campaign, dict) and isinstance(report, dict)
    } if isinstance(campaign, dict) else {}
    for profile in PROFILES:
        transition = x4.get(profile) if isinstance(x4, dict) else None
        report = campaign_reports.get(profile)
        rows = report.get("results", []) if isinstance(report, dict) else []
        s31_index = list(FULL_ROUTE_ORDER).index(31)
        s27_index = s31_index + 1
        transition_ok = (
            isinstance(transition, dict)
            and transition.get("output_scenario") == 27
            and isinstance(transition.get("record_sha256"), str)
            and len(rows) > s27_index
            and isinstance(rows[s27_index], dict)
            and rows[s27_index].get("scenario") == 27
            and isinstance(rows[s27_index].get("input_state"), dict)
            and rows[s27_index]["input_state"].get("record_sha256")
            == transition.get("record_sha256")
        )
        if transition_ok:
            passed += 1
        else:
            errors.append(f"ending/{profile}: X4 -> S27 exact save transition missing")
    if ending_profiles != set(PROFILES):
        errors.append("ending profile set is incomplete")
    return passed, errors, details


PhaseVerifier = Callable[
    [dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]],
    tuple[int, list[str], list[dict[str, object]]],
]


def verify_preparation_visual_review(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    entries = [
        entry
        for entry in summary_entries(phase)
        if entry.get("label") == "manual-visual-review"
    ]
    if len(entries) != 1:
        return ["manual visual review summary declaration is missing"], {
            "status": "missing"
        }
    summary_path = Path(entries[0]["path"])
    data = read_json(summary_path, errors, label="preparation visual review")
    if data is None:
        return errors, {"summary": str(summary_path), "status": "missing"}
    check_equal(errors, data.get("status"), "pass", "visual review status")
    check_equal(errors, data.get("run_id"), context["run_id"], "visual review run_id")
    check_equal(errors, data.get("profiles"), list(PROFILES), "visual review profiles")
    check_equal(errors, data.get("scenarios"), list(SCENARIOS), "visual review scenarios")
    check_equal(errors, data.get("reviewed_cases"), 93, "visual reviewed_cases")
    check_equal(errors, data.get("required_cases"), 93, "visual required_cases")
    candidates = data.get("candidate_roms")
    for profile in PROFILES:
        validate_summary_rom(
            candidates.get(profile) if isinstance(candidates, dict) else None,
            profile=profile,
            releases=releases,
            errors=errors,
            label=f"visual review candidate {profile}",
        )

    rows = data.get("results")
    if not isinstance(rows, list) or len(rows) != 93:
        errors.append("visual review results must contain exactly 93 cases")
        rows = []
    expected = {
        (profile, scenario) for profile in PROFILES for scenario in SCENARIOS
    }
    seen: set[tuple[object, object]] = set()
    phase_root = Path(str(phase["root"])).resolve()
    for row in rows:
        if not isinstance(row, dict):
            errors.append("visual review result contains a non-object row")
            continue
        key = (row.get("profile"), row.get("scenario"))
        if key not in expected or key in seen:
            errors.append(f"visual review has invalid/duplicate case {key!r}")
            continue
        seen.add(key)
        profile, scenario = key
        label = f"visual review {profile}/S{int(scenario):02d}"
        row_errors: list[str] = []
        check_equal(row_errors, row.get("status"), "pass", "status")
        check_equal(row_errors, row.get("run_id"), context["run_id"], "run_id")
        check_equal(
            row_errors,
            row.get("approved_requirement_ids"),
            list(PREPARATION_REVIEW_REQUIREMENT_IDS),
            "approved requirements",
        )
        if not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip():
            row_errors.append("reviewer is missing")
        if not isinstance(row.get("reviewed_at"), str) or not row["reviewed_at"]:
            row_errors.append("review timestamp is missing")
        seed = row.get("seed")
        if isinstance(seed, dict):
            seed_lineage(
                seed,
                profile=str(profile),
                context=context,
                errors=row_errors,
                label=label,
            )
        else:
            row_errors.append("fresh seed lineage is missing")

        expected_manifest = (
            phase_root
            / "visual_review"
            / str(profile)
            / f"s{int(scenario):02d}"
            / context["run_id"]
            / "manifest.json"
        )
        expected_evidence = (
            phase_root
            / str(profile)
            / f"s{int(scenario):02d}"
            / context["run_id"]
            / "evidence.json"
        )
        snapshots = (
            ("manifest", row.get("manifest"), expected_manifest),
            (
                "preparation evidence",
                row.get("preparation_evidence"),
                expected_evidence,
            ),
        )
        for snapshot_label, snapshot, expected_path in snapshots:
            if not isinstance(snapshot, dict):
                row_errors.append(f"{snapshot_label} snapshot is missing")
                continue
            actual_path = resolve_report_path(snapshot.get("path"))
            if actual_path != expected_path:
                row_errors.append(f"{snapshot_label} path differs")
            if (
                not actual_path.is_file()
                or snapshot.get("sha256") != sha256_path(actual_path)
            ):
                row_errors.append(f"{snapshot_label} file/hash differs")

        manifest = read_json(expected_manifest, row_errors, label=f"{label} manifest")
        if manifest is not None:
            check_equal(row_errors, manifest.get("status"), "manual_review_pass", "manifest status")
            check_equal(row_errors, manifest.get("profile"), profile, "manifest profile")
            check_equal(row_errors, manifest.get("scenario"), scenario, "manifest scenario")
            check_equal(row_errors, manifest.get("run_id"), context["run_id"], "manifest run_id")
            requirements = manifest.get("review_requirements")
            requirement_ids = [
                item.get("id") for item in requirements if isinstance(item, dict)
            ] if isinstance(requirements, list) else []
            check_equal(
                row_errors,
                requirement_ids,
                list(PREPARATION_REVIEW_REQUIREMENT_IDS),
                "manifest requirements",
            )
            decision = manifest.get("review_decision")
            if not isinstance(decision, dict):
                row_errors.append("manifest review decision is missing")
            else:
                check_equal(row_errors, decision.get("decision"), "pass", "decision")
                check_equal(
                    row_errors,
                    decision.get("approved_requirement_ids"),
                    list(PREPARATION_REVIEW_REQUIREMENT_IDS),
                    "decision requirements",
                )
                check_equal(row_errors, decision.get("reviewer"), row.get("reviewer"), "reviewer")
                check_equal(row_errors, decision.get("reviewed_at"), row.get("reviewed_at"), "reviewed_at")
            listed_sources: list[Path] = []
            groups = manifest.get("groups")
            if not isinstance(groups, list) or len(groups) != 5:
                row_errors.append("five visual review groups are required")
                groups = []
            for group in groups:
                sheets = group.get("sheets") if isinstance(group, dict) else None
                if not isinstance(sheets, list):
                    row_errors.append("visual review sheet list is missing")
                    continue
                for sheet in sheets:
                    if not isinstance(sheet, dict):
                        row_errors.append("visual review sheet entry is invalid")
                        continue
                    sheet_path = resolve_report_path(sheet.get("path"))
                    if (
                        not sheet_path.is_file()
                        or sheet.get("sha256") != sha256_path(sheet_path)
                    ):
                        row_errors.append("contact sheet file/hash differs")
                    sources = sheet.get("sources")
                    if not isinstance(sources, list):
                        row_errors.append("contact sheet source list is missing")
                        continue
                    for source in sources:
                        if not isinstance(source, dict):
                            row_errors.append("contact sheet source entry is invalid")
                            continue
                        source_path = resolve_report_path(source.get("path"))
                        if (
                            not source_path.is_file()
                            or source.get("sha256") != sha256_path(source_path)
                            or not (
                                source_path.is_relative_to(
                                    expected_evidence.parent / "pre"
                                )
                                or source_path.is_relative_to(
                                    expected_evidence.parent / "shop"
                                )
                            )
                        ):
                            row_errors.append("review source file/hash/path differs")
                        listed_sources.append(source_path)
            pre_root = expected_evidence.parent / "pre"
            expected_sources = [pre_root / "root.png"]
            expected_sources.extend(sorted((pre_root / "allied").glob("*.png")))
            expected_sources.extend(sorted((pre_root / "arrangement").glob("*.png")))
            expected_sources.extend(
                sorted((expected_evidence.parent / "shop").glob("*.png"))
            )
            expected_sources.extend(sorted((pre_root / "fixed").glob("*.png")))
            if sorted(listed_sources) != sorted(expected_sources) or len(
                listed_sources
            ) != len(set(listed_sources)):
                row_errors.append("review source coverage is incomplete or duplicated")

        evidence = read_json(expected_evidence, row_errors, label=f"{label} evidence")
        if evidence is not None:
            check_equal(
                row_errors,
                evidence.get("status"),
                "captured_exact_unreviewed",
                "evidence status",
            )
            check_equal(row_errors, evidence.get("profile"), profile, "evidence profile")
            check_equal(row_errors, evidence.get("scenario"), scenario, "evidence scenario")
            check_equal(row_errors, evidence.get("run_id"), context["run_id"], "evidence run_id")
            identity = evidence.get("scenario_identity")
            if (
                not isinstance(identity, dict)
                or identity.get("status") != "pass"
                or identity.get("identified_scenario") != scenario
            ):
                row_errors.append("runtime scenario identity is missing")
        errors.extend(f"{label}: {error}" for error in row_errors)
    if seen != expected:
        errors.append("visual review profile/scenario coverage is incomplete")
    return errors, {
        "summary": str(summary_path),
        "status": "pass" if not errors else "fail",
        "reviewed_cases": len(seen),
    }


def verify_preparation(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    passed, errors, details = verify_parallel_surface(
        phase,
        releases,
        context,
        accepted_status="captured_exact_unreviewed",
    )
    review_errors, review_detail = verify_preparation_visual_review(
        phase,
        releases,
        context,
    )
    errors.extend(review_errors)
    details.append(review_detail)
    return passed, errors, details


def verify_gray(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    return verify_parallel_surface(
        phase,
        releases,
        context,
        accepted_status="pass",
    )


def verify_natural_and_legacy(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    return verify_join_phase(
        phase,
        releases,
        context,
        expected_groups=("natural", "legacy"),
        expected_cases=(*NATURAL_CASES, *LEGACY_CASES),
    )


def verify_legacy_later(
    phase: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
) -> tuple[int, list[str], list[dict[str, object]]]:
    return verify_join_phase(
        phase,
        releases,
        context,
        expected_groups=("legacy-later",),
        expected_cases=LEGACY_LATER_CASES,
    )


PHASE_VERIFIERS: dict[str, PhaseVerifier] = {
    "fresh_s1_seed": verify_fresh_seed,
    "current_result_probes": verify_result_probes,
    "first_turn_s01_s31": verify_first_turn,
    "preparation_s01_s31": verify_preparation,
    "gray_acted_s01_s31": verify_gray,
    "natural_and_legacy_join": verify_natural_and_legacy,
    "legacy_later_join": verify_legacy_later,
    "continuous_campaign_route": verify_campaign,
    "runestone_restart": verify_runestone,
    "scenario6_actual_runestone": verify_scenario6,
    "mounted_lord_combat": verify_mounted,
    "scenario27_final_and_ending": verify_final_ending,
}


def verify_required_scope_contract(
    plan: dict[str, Any],
    releases: dict[str, dict[str, Any]],
    context: dict[str, Any],
    *,
    validation_root: Path,
    phase_roots: dict[str, Path],
) -> dict[str, object]:
    """Verify every mandatory extension without changing the base 612 count."""

    errors: list[str] = []
    contract = plan.get("required_scope_contract")
    if not isinstance(contract, dict):
        return {
            "status": "fail",
            "all_verifiers_present": False,
            "all_evidence_present": False,
            "all_requirements_pass": False,
            "requirements": [],
            "errors": ["required_scope_contract is missing"],
        }
    for key, expected in (
        ("schema_version", 1),
        ("status", "planned_fail_closed_extension"),
        ("base_gate_pass_count", EXPECTED_GATE_PASS_COUNT),
        ("extension_count_status", SCOPE_EXTENSION_COUNT_STATUS),
        ("required_ids", list(REQUIRED_SCOPE_IDS)),
        ("complete_only_when_all_requirements_pass", True),
        ("verifier_registry_frozen_at_plan", True),
        (
            "registered_verifier_ids_at_plan",
            sorted(
                requirement.verifier_id
                for requirement in REQUIRED_SCOPE_CONTRACT
            ),
        ),
        (
            "expected_verifier_ids",
            sorted(
                requirement.verifier_id
                for requirement in REQUIRED_SCOPE_CONTRACT
            ),
        ),
        ("final_plan_eligible_at_creation", True),
        ("final_plan_policy", FINAL_PLAN_POLICY),
        ("retired_run_ids", list(RETIRED_FINAL_GATE_RUN_IDS)),
        ("next_final_run_id_floor", NEXT_FINAL_GATE_RUN_ID_FLOOR),
    ):
        check_equal(errors, contract.get(key), expected, f"scope contract {key}")

    raw_root = plan.get("required_scope_extension_root")
    if not isinstance(raw_root, str):
        errors.append("required_scope_extension_root is missing")
        extension_root = validation_root / "missing-required-scope-root"
    else:
        extension_root = Path(raw_root).resolve()
        if not extension_root.is_relative_to(validation_root):
            errors.append("required_scope_extension_root is outside validation_root")
        for phase_id, phase_root in phase_roots.items():
            if (
                phase_root == extension_root
                or phase_root.is_relative_to(extension_root)
                or extension_root.is_relative_to(phase_root)
            ):
                errors.append(
                    "required_scope_extension_root overlaps base phase "
                    f"{phase_id}"
                )

    rows = contract.get("requirements")
    if not isinstance(rows, list):
        errors.append("required scope requirement list is missing")
        rows = []
    row_ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if row_ids != list(REQUIRED_SCOPE_IDS):
        errors.append(f"required scope order/IDs changed: {row_ids!r}")

    expected_inputs = {
        profile: {
            "path": releases[profile]["path"],
            "sha256": releases[profile]["sha256"],
            "bytes": releases[profile]["bytes"],
        }
        for profile in PROFILES
        if profile in releases
    }
    results: list[dict[str, object]] = []
    all_verifiers_present = True
    all_evidence_present = True
    all_requirements_pass = True
    summary_paths: list[Path] = []
    observed_frozen_units = 0
    for index, requirement in enumerate(REQUIRED_SCOPE_CONTRACT, 1):
        row_errors: list[str] = []
        row = rows[index - 1] if index <= len(rows) else None
        if not isinstance(row, dict) or row.get("id") != requirement.requirement_id:
            row_errors.append("required scope declaration is missing or out of order")
            row = {}
        expected_status = (
            "implemented"
            if requirement.verifier_id in SUPPLEMENTAL_SCOPE_VERIFIERS
            else "missing_pending_implementation"
        )
        for key, expected in (
            ("order", index),
            ("requirement", requirement.requirement),
            ("base_phase_coverage", list(requirement.base_phase_coverage)),
            ("missing_proof", requirement.missing_proof),
            ("verifier_id", requirement.verifier_id),
            ("verifier_status_at_plan", expected_status),
            ("exact_release_inputs", expected_inputs),
            ("expected_acceptance_units", requirement.expected_acceptance_units),
            (
                "acceptance_unit_count_status",
                (
                    "frozen"
                    if requirement.expected_acceptance_units is not None
                    else "pending_domain_ledger"
                ),
            ),
            ("mandatory_for_final_pass", True),
        ):
            check_equal(
                row_errors,
                row.get(key),
                expected,
                f"scope {requirement.requirement_id} {key}",
            )
        raw_summary = row.get("summary_path")
        summary_path = (
            Path(raw_summary).resolve()
            if isinstance(raw_summary, str)
            else extension_root / requirement.requirement_id / "missing.json"
        )
        expected_summary = (
            extension_root / requirement.requirement_id / "summary.json"
        ).resolve()
        if summary_path != expected_summary:
            row_errors.append(
                f"scope summary path differs: {summary_path} != {expected_summary}"
            )
        if not summary_path.is_relative_to(extension_root):
            row_errors.append("scope summary path is outside extension root")
        summary_paths.append(summary_path)

        verifier = SUPPLEMENTAL_SCOPE_VERIFIERS.get(requirement.verifier_id)
        verifier_present = verifier is not None
        evidence_present = summary_path.is_file()
        all_verifiers_present &= verifier_present
        all_evidence_present &= evidence_present
        details: dict[str, object] = {
            "summary": str(summary_path),
            "status": "missing",
        }
        accepted = False
        if not verifier_present or not evidence_present:
            row_errors.append(
                "missing supplemental verifier/evidence: "
                f"{requirement.requirement_id} "
                f"(verifier={requirement.verifier_id}, "
                f"verifier_present={verifier_present}, "
                f"evidence_present={evidence_present})"
            )
        else:
            assert verifier is not None
            accepted, verifier_errors, details = verifier(
                requirement,
                row,
                releases,
                context,
            )
            row_errors.extend(verifier_errors)
        if row_errors:
            accepted = False
        if accepted and requirement.expected_acceptance_units is not None:
            observed_frozen_units += requirement.expected_acceptance_units
        all_requirements_pass &= accepted
        results.append(
            {
                "order": index,
                "id": requirement.requirement_id,
                "status": "pass" if accepted else "fail",
                "verifier_id": requirement.verifier_id,
                "verifier_present": verifier_present,
                "evidence_present": evidence_present,
                "expected_acceptance_units": (
                    requirement.expected_acceptance_units
                ),
                "details": details,
                "errors": row_errors,
            }
        )

    if len(set(summary_paths)) != len(summary_paths):
        errors.append("required scope summary paths are duplicated")
        all_requirements_pass = False
    if len(rows) != len(REQUIRED_SCOPE_CONTRACT):
        errors.append("required scope requirement count differs")
        all_requirements_pass = False
    status = "pass" if (
        not errors
        and all_verifiers_present
        and all_evidence_present
        and all_requirements_pass
    ) else "fail"
    return {
        "status": status,
        "base_gate_pass_count": EXPECTED_GATE_PASS_COUNT,
        "extension_count_status": SCOPE_EXTENSION_COUNT_STATUS,
        "expected_supplemental_units": None,
        "observed_frozen_supplemental_units": observed_frozen_units,
        "all_verifiers_present": all_verifiers_present,
        "all_evidence_present": all_evidence_present,
        "all_requirements_pass": all_requirements_pass,
        "requirements": results,
        "errors": errors,
    }


def verify_plan_manifest(manifest_path: Path) -> dict[str, object]:
    manifest_path = manifest_path.resolve()
    top_errors: list[str] = []
    plan = read_json(manifest_path, top_errors, label="final gate plan")
    if plan is None:
        return {
            "schema_version": 1,
            "kind": "langrisser_ii_korean_v137_final_gate_verification",
            "status": "fail",
            "plan_manifest": str(manifest_path),
            "errors": top_errors,
        }
    check_equal(top_errors, plan.get("schema_version"), 1, "plan schema_version")
    check_equal(
        top_errors,
        plan.get("kind"),
        "langrisser_ii_korean_v137_final_gate_plan",
        "plan kind",
    )
    check_equal(top_errors, plan.get("release_version"), "1.3.7", "release_version")
    check_equal(top_errors, plan.get("expected_phase_order"), list(PHASE_IDS), "phase order")
    check_equal(
        top_errors,
        plan.get("expected_gate_pass_count"),
        EXPECTED_GATE_PASS_COUNT,
        "expected gate pass count",
    )
    expected_total = plan.get("expected_total_acceptance_units")
    if not isinstance(expected_total, dict):
        top_errors.append("expected_total_acceptance_units is missing")
    else:
        for key, expected in (
            ("status", SCOPE_EXTENSION_COUNT_STATUS),
            ("base_gate_units", EXPECTED_GATE_PASS_COUNT),
            ("supplemental_units", None),
            ("total_units", None),
        ):
            check_equal(
                top_errors,
                expected_total.get(key),
                expected,
                f"expected total acceptance units {key}",
            )
    run_id = plan.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        top_errors.append("plan run_id is missing")
    else:
        try:
            validate_run_id(run_id)
        except ValueError as exc:
            top_errors.append(f"plan run_id: {exc}")

    releases = plan.get("release_roms_before")
    if not isinstance(releases, dict) or set(releases) != set(PROFILES):
        top_errors.append("release_roms_before must contain pure, normal, and hard")
        releases = {}
    observed_release_hashes = {
        profile: str(releases.get(profile, {}).get("sha256"))
        for profile in PROFILES
        if isinstance(releases.get(profile), dict)
    }
    try:
        release_identity.require_final_release_identity(observed_release_hashes)
    except ValueError as exc:
        top_errors.append(f"central v1.3.7 release identity: {exc}")
    if plan.get("release_identity") != release_identity.identity_snapshot():
        top_errors.append("plan release identity attestation is stale or missing")
    release_after = {}
    release_unchanged = True
    for profile in PROFILES:
        before = releases.get(profile)
        if not isinstance(before, dict):
            release_unchanged = False
            continue
        path = Path(str(before.get("path"))).resolve()
        try:
            after = snapshot_file(path, release_rom=True)
        except (OSError, ValueError) as exc:
            top_errors.append(f"release {profile}: {type(exc).__name__}: {exc}")
            release_unchanged = False
            continue
        release_after[profile] = after
        if (
            before.get("sha256") != after["sha256"]
            or before.get("bytes") != after["bytes"]
            or before.get("expected_sha256") != after["sha256"]
            or before.get("hash_locked") is not True
        ):
            top_errors.append(f"release {profile}: before/after exact SHA lock failed")
            release_unchanged = False
    if len({value.get("sha256") for value in releases.values() if isinstance(value, dict)}) != 3:
        top_errors.append("the three exact release ROM SHA-256 values must be distinct")

    support = plan.get("support_inputs_before", {})
    source_before = support.get("japanese_source_rom") if isinstance(support, dict) else None
    source_after = None
    support_unchanged = True
    if not isinstance(source_before, dict):
        top_errors.append("Japanese source ROM snapshot is missing")
        support_unchanged = False
    else:
        try:
            require_canonical_source_snapshot(source_before)
        except ValueError as exc:
            top_errors.append(f"canonical Japanese source ROM: {exc}")
            support_unchanged = False
        try:
            source_after = snapshot_file(Path(str(source_before["path"])))
        except (KeyError, OSError, ValueError) as exc:
            top_errors.append(f"Japanese source ROM: {type(exc).__name__}: {exc}")
            support_unchanged = False
        else:
            try:
                require_canonical_source_snapshot(source_after)
            except ValueError as exc:
                top_errors.append(f"canonical Japanese source ROM: {exc}")
                support_unchanged = False
            if (
                source_before.get("sha256") != source_after["sha256"]
                or source_before.get("bytes") != source_after["bytes"]
            ):
                top_errors.append("Japanese source ROM changed after plan")
                support_unchanged = False

    raw_phases = plan.get("phases")
    if not isinstance(raw_phases, list):
        top_errors.append("plan phases are missing")
        raw_phases = []
    phase_ids = [phase.get("id") for phase in raw_phases if isinstance(phase, dict)]
    exact_phase_order = phase_ids == list(PHASE_IDS)
    if not exact_phase_order:
        top_errors.append(f"phase list/order changed: {phase_ids!r}")

    validation_root_valid = True
    raw_validation_root = plan.get("validation_root")
    if not isinstance(raw_validation_root, str):
        top_errors.append("plan validation_root is missing")
        validation_root = manifest_path.parent
        validation_root_valid = False
    else:
        validation_root = Path(raw_validation_root).resolve()
    if not manifest_path.is_relative_to(validation_root):
        top_errors.append("plan manifest is outside its validation_root")
        validation_root_valid = False
    declared_roots = plan.get("phase_roots")
    if not isinstance(declared_roots, dict) or set(declared_roots) != set(PHASE_IDS):
        top_errors.append("phase_roots must contain every exact final-gate phase")
        declared_roots = {}
        validation_root_valid = False
    resolved_roots = {}
    for phase_id in PHASE_IDS:
        value = declared_roots.get(phase_id)
        if value is None:
            continue
        path = Path(str(value)).resolve()
        resolved_roots[phase_id] = path
        if not path.is_relative_to(validation_root):
            top_errors.append(
                f"phase root outside validation_root: {phase_id} -> {path}"
            )
            validation_root_valid = False
    if len(set(resolved_roots.values())) != len(PHASE_IDS):
        top_errors.append("phase roots are missing or duplicated")
        validation_root_valid = False
    all_declared_summary_paths = [
        Path(entry["path"]).resolve()
        for phase in raw_phases
        if isinstance(phase, dict)
        for entry in summary_entries(phase)
    ]
    if len(set(all_declared_summary_paths)) != len(all_declared_summary_paths):
        top_errors.append("summary paths are duplicated across final-gate phases")
        validation_root_valid = False

    context: dict[str, Any] = {
        "run_id": run_id,
        "source_rom": source_after if source_after is not None else source_before,
    }
    phase_results = []
    total_passed = 0
    summaries_present = True
    structural_phase_match = exact_phase_order and len(raw_phases) == len(PHASE_DEFINITIONS)
    for index, definition in enumerate(PHASE_DEFINITIONS, 1):
        phase = raw_phases[index - 1] if index <= len(raw_phases) else None
        phase_errors = []
        if not isinstance(phase, dict) or phase.get("id") != definition.phase_id:
            summaries_present = False
            structural_phase_match = False
            phase_results.append({
                "order": index,
                "id": definition.phase_id,
                "status": "skipped",
                "expected_pass_count": definition.expected_pass_count,
                "observed_pass_count": 0,
                "all_summaries_present": False,
                "errors": ["phase declaration is missing or out of order"],
            })
            continue
        check_equal(phase_errors, phase.get("order"), index, "phase order number")
        phase_root = Path(str(phase.get("root"))).resolve()
        check_equal(
            phase_errors,
            phase_root,
            resolved_roots.get(definition.phase_id),
            "phase root",
        )
        if not phase_root.is_relative_to(validation_root):
            phase_errors.append("phase root is outside validation_root")
        check_equal(
            phase_errors,
            phase.get("expected_pass_count"),
            definition.expected_pass_count,
            "phase expected_pass_count",
        )
        check_equal(
            phase_errors,
            phase.get("expected_total_count"),
            definition.expected_pass_count,
            "phase expected_total_count",
        )
        check_equal(
            phase_errors,
            phase.get("acceptance_units"),
            definition.acceptance_units,
            "phase acceptance_units",
        )
        check_equal(
            phase_errors,
            phase.get("dependencies"),
            list(EXPECTED_PHASE_DEPENDENCIES[definition.phase_id]),
            "phase dependencies",
        )
        check_equal(
            phase_errors,
            phase.get("summary_count"),
            definition.summary_count,
            "phase summary_count",
        )
        phase_inputs = phase.get("exact_release_inputs")
        expected_inputs = {
            profile: {
                "path": releases[profile]["path"],
                "sha256": releases[profile]["sha256"],
                "bytes": releases[profile]["bytes"],
            }
            for profile in PROFILES
            if profile in releases
        }
        check_equal(
            phase_errors,
            phase_inputs,
            expected_inputs,
            "phase exact_release_inputs",
        )
        entries = summary_entries(phase)
        if len({entry["label"] for entry in entries}) != len(entries):
            phase_errors.append("summary labels are duplicated within phase")
        for entry in entries:
            if not Path(entry["path"]).resolve().is_relative_to(phase_root):
                phase_errors.append(
                    f"summary path is outside phase root: {entry['path']}"
                )
        commands = phase.get("commands")
        if not isinstance(commands, list):
            phase_errors.append("phase commands are missing")
            commands = []
        check_equal(
            phase_errors,
            phase.get("command_count"),
            len(commands),
            "phase command_count",
        )
        command_summaries = []
        for command in commands:
            if not isinstance(command, dict):
                phase_errors.append("phase contains a non-object command")
                continue
            argv = command.get("argv")
            if not isinstance(argv, list) or not all(
                isinstance(value, str) for value in argv
            ):
                phase_errors.append("command argv is not a string list")
                continue
            verify_command_display_policy(argv, phase_errors)
            if definition.phase_id == "first_turn_s01_s31":
                profile = command.get("label")
                positions = [
                    position
                    for position, value in enumerate(argv)
                    if value == "--seed-gst"
                ]
                if len(positions) != 1:
                    phase_errors.append(
                        "first-turn command must contain exactly one "
                        "--seed-gst option"
                    )
                elif profile not in PROFILES:
                    phase_errors.append(
                        f"first-turn command has invalid profile label {profile!r}"
                    )
                else:
                    position = positions[0]
                    actual_seed = (
                        argv[position + 1]
                        if position + 1 < len(argv)
                        else None
                    )
                    expected_seed = context.get("seeds", {}).get(profile)
                    if not isinstance(expected_seed, dict):
                        phase_errors.append(
                            f"first-turn command fresh {profile} seed lineage "
                            "is unavailable"
                        )
                    elif (
                        resolve_report_path(actual_seed)
                        != Path(str(expected_seed["path"])).resolve()
                    ):
                        phase_errors.append(
                            f"first-turn command --seed-gst differs from "
                            f"fresh {profile} seed"
                        )
                campaign_positions = [
                    position
                    for position, value in enumerate(argv)
                    if value == "--campaign-summary"
                ]
                if len(campaign_positions) != 1:
                    phase_errors.append(
                        "first-turn command must contain exactly one "
                        "--campaign-summary option"
                    )
                else:
                    position = campaign_positions[0]
                    actual_campaign = (
                        argv[position + 1]
                        if position + 1 < len(argv)
                        else None
                    )
                    expected_campaign = context.get("campaign_summary")
                    if not isinstance(expected_campaign, dict):
                        phase_errors.append(
                            "first-turn command campaign lineage is unavailable"
                        )
                    elif (
                        resolve_report_path(actual_campaign)
                        != Path(str(expected_campaign["path"])).resolve()
                    ):
                        phase_errors.append(
                            "first-turn command --campaign-summary differs from "
                            "verified continuous campaign summary"
                        )
            run_id_options = [
                position for position, value in enumerate(argv) if value == "--run-id"
            ]
            if len(run_id_options) > 1:
                phase_errors.append("command contains duplicate --run-id options")
            elif len(run_id_options) == 1:
                position = run_id_options[0]
                actual_run_id = argv[position + 1] if position + 1 < len(argv) else None
                if actual_run_id != run_id:
                    phase_errors.append(
                        f"command --run-id {actual_run_id!r} != plan {run_id!r}"
                    )
            elif definition.phase_id not in RUN_ID_OPTIONAL_PHASES:
                phase_errors.append("command is missing its mandatory --run-id")
            command_summary = Path(str(command.get("summary_path"))).resolve()
            command_summaries.append(command_summary)
            if not command_summary.is_relative_to(phase_root):
                phase_errors.append("command summary_path is outside phase root")
            if Path(str(command.get("cwd"))).resolve() != ROOT:
                phase_errors.append("command cwd differs from repository root")
        if command_summaries != [Path(entry["path"]).resolve() for entry in entries]:
            phase_errors.append("command and declared summary paths differ")
        phase_summaries_present = (
            len(entries) == definition.summary_count
            and all(Path(entry["path"]).is_file() for entry in entries)
        )
        summaries_present &= phase_summaries_present
        verifier = PHASE_VERIFIERS[definition.phase_id]
        observed, verifier_errors, details = verifier(phase, releases, context)
        phase_errors.extend(verifier_errors)
        total_passed += observed
        exact_count = observed == definition.expected_pass_count
        phase_status = (
            "pass"
            if phase_summaries_present and exact_count and not phase_errors
            else "fail"
        )
        phase_results.append({
            "order": index,
            "id": definition.phase_id,
            "status": phase_status,
            "expected_pass_count": definition.expected_pass_count,
            "observed_pass_count": observed,
            "exact_pass_count": exact_count,
            "all_summaries_present": phase_summaries_present,
            "summaries": details,
            "errors": phase_errors,
        })

    all_phase_counts_exact = all(
        row.get("exact_pass_count") is True for row in phase_results
    )
    all_phases_pass = all(row.get("status") == "pass" for row in phase_results)
    no_phase_skipped = (
        structural_phase_match
        and summaries_present
        and len(phase_results) == len(PHASE_DEFINITIONS)
        and all(row.get("status") != "skipped" for row in phase_results)
    )
    required_scope = verify_required_scope_contract(
        plan,
        releases,
        context,
        validation_root=validation_root,
        phase_roots=resolved_roots,
    )
    required_scope_pass = required_scope.get("status") == "pass"
    status = "pass" if all((
        not top_errors,
        release_unchanged,
        support_unchanged,
        validation_root_valid,
        exact_phase_order,
        summaries_present,
        no_phase_skipped,
        all_phase_counts_exact,
        all_phases_pass,
        total_passed == EXPECTED_GATE_PASS_COUNT,
        required_scope_pass,
    )) else "fail"
    return {
        "schema_version": 1,
        "kind": "langrisser_ii_korean_v137_final_gate_verification",
        "status": status,
        "release_version": "1.3.7",
        "run_id": run_id,
        "plan_manifest": {
            "path": str(manifest_path),
            "sha256": sha256_path(manifest_path),
        },
        "release_roms_before": releases,
        "release_roms_after": release_after,
        "release_roms_unchanged": release_unchanged,
        "support_inputs_before": support,
        "support_inputs_after": {"japanese_source_rom": source_after},
        "support_inputs_unchanged": support_unchanged,
        "validation_root": str(validation_root),
        "validation_root_valid": validation_root_valid,
        "phase_roots": {
            phase_id: str(path) for phase_id, path in resolved_roots.items()
        },
        "expected_phase_order": list(PHASE_IDS),
        "observed_phase_order": phase_ids,
        "exact_phase_order": exact_phase_order,
        "all_phase_summaries_present": summaries_present,
        "no_phase_skipped": no_phase_skipped,
        "all_phase_counts_exact": all_phase_counts_exact,
        "expected_gate_pass_count": EXPECTED_GATE_PASS_COUNT,
        "observed_gate_pass_count": total_passed,
        "expected_total_acceptance_units": {
            "status": SCOPE_EXTENSION_COUNT_STATUS,
            "base_gate_units": EXPECTED_GATE_PASS_COUNT,
            "supplemental_units": None,
            "total_units": None,
        },
        "phases": phase_results,
        "required_scope_contract": required_scope,
        "errors": top_errors,
        "final_gate": {
            "release_rom_before_after_sha_match": release_unchanged,
            "support_inputs_before_after_sha_match": support_unchanged,
            "validation_root_and_phase_roots_valid": validation_root_valid,
            "exact_phase_order": exact_phase_order,
            "all_phase_summaries_present": summaries_present,
            "no_phase_skipped": no_phase_skipped,
            "all_phase_counts_exact": all_phase_counts_exact,
            "all_phases_pass": all_phases_pass,
            "all_required_scope_verifiers_present": required_scope.get(
                "all_verifiers_present"
            ),
            "all_required_scope_evidence_present": required_scope.get(
                "all_evidence_present"
            ),
            "all_required_scope_requirements_pass": required_scope.get(
                "all_requirements_pass"
            ),
            "base_612_alone_is_never_final_acceptance": True,
        },
    }


def add_release_arguments(parser: argparse.ArgumentParser) -> None:
    for profile in PROFILES:
        parser.add_argument(f"--{profile}-rom", type=Path, required=True)
        parser.add_argument(
            f"--{profile}-sha256",
            type=valid_sha256,
            required=True,
        )


PHASE_ROOT_ARGUMENTS = {
    "fresh_seed_root": "fresh_s1_seed",
    "probe_root": "current_result_probes",
    "first_turn_root": "first_turn_s01_s31",
    "preparation_root": "preparation_s01_s31",
    "gray_root": "gray_acted_s01_s31",
    "natural_join_root": "natural_and_legacy_join",
    "natural_join_later_root": "legacy_later_join",
    "sequential_root": "continuous_campaign_route",
    "runestone_root": "runestone_restart",
    "s6_root": "scenario6_actual_runestone",
    "mounted_root": "mounted_lord_combat",
    "ending_root": "scenario27_final_and_ending",
}


def add_phase_root_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--fresh-seed-root", type=Path)
    parser.add_argument("--probe-root", type=Path)
    parser.add_argument("--first-turn-root", type=Path)
    parser.add_argument("--preparation-root", type=Path)
    parser.add_argument("--gray-root", type=Path)
    parser.add_argument("--natural-join-root", type=Path)
    parser.add_argument("--natural-join-later-root", type=Path)
    parser.add_argument("--sequential-root", type=Path)
    parser.add_argument("--runestone-root", type=Path)
    parser.add_argument("--s6-root", type=Path)
    parser.add_argument("--mounted-root", type=Path)
    parser.add_argument("--ending-root", type=Path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="write the hash-locked phase plan")
    add_release_arguments(plan)
    plan.add_argument("--source-rom", type=Path, default=DEFAULT_SOURCE_ROM)
    plan.add_argument("--run-id", required=True)
    plan.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    plan.add_argument("--manifest", type=Path)
    plan.add_argument("--workers", type=int, default=3)
    plan.add_argument("--display-base", type=int, default=820)
    add_phase_root_arguments(plan)

    verify = subparsers.add_parser(
        "verify",
        help="read every planned summary and enforce the immutable final gate",
    )
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--output", type=Path)
    return parser.parse_args()


def validate_run_id(value: str) -> str:
    if not value or Path(value).name != value or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in value
    ):
        raise ValueError(
            "--run-id must contain only ASCII letters, digits, '-' and '_'"
        )
    suffix = (
        value.removeprefix(FINAL_GATE_RUN_ID_SEQUENCE_PREFIX)
        if value.startswith(FINAL_GATE_RUN_ID_SEQUENCE_PREFIX)
        else ""
    )
    below_final_floor = suffix.isdigit() and int(suffix) < (
        NEXT_FINAL_GATE_RUN_SEQUENCE
    )
    if value in RETIRED_FINAL_GATE_RUN_IDS or below_final_floor:
        raise ValueError(
            f"--run-id {value!r} is permanently retired development evidence; "
            f"create a nonexistent fresh root at "
            f"{NEXT_FINAL_GATE_RUN_ID_FLOOR!r} or later after all required-"
            "scope verifier adapters are frozen"
        )
    return value


def main() -> int:
    args = parse_args()
    if args.command == "verify":
        report = verify_plan_manifest(args.manifest)
        output = (
            args.output.resolve()
            if args.output is not None
            else args.manifest.resolve().with_name("verification.json")
        )
        if output == args.manifest.resolve():
            raise ValueError("verification output must not overwrite the plan manifest")
        if output.exists():
            raise FileExistsError(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(output)
        print(
            f"{report['status']}: {report.get('observed_gate_pass_count', 0)}/"
            f"{report.get('expected_gate_pass_count', EXPECTED_GATE_PASS_COUNT)} "
            "base-gate checks; required-scope extension is separately mandatory"
        )
        return 0 if report["status"] == "pass" else 1

    run_id = validate_run_id(args.run_id)
    if not 1 <= args.workers <= 6:
        raise ValueError("--workers must be 1..6 for the final low-concurrency pass")
    if not 100 <= args.display_base <= 990 - args.workers:
        raise ValueError(
            "--display-base must be at least 100 and leave enough virtual displays"
        )
    source = snapshot_file(args.source_rom)
    releases = {}
    for profile in PROFILES:
        path = getattr(args, f"{profile}_rom")
        expected = getattr(args, f"{profile}_sha256")
        releases[profile] = hash_locked_release_snapshot(path, expected)
    if len({releases[profile]["sha256"] for profile in PROFILES}) != 3:
        raise ValueError("pure, normal, and hard release ROMs must be distinct")
    validation_root = args.output_root.resolve()
    output_root = (validation_root / run_id).resolve()
    if output_root.exists():
        raise FileExistsError(
            f"new final-gate run root already exists: {output_root}"
        )
    phase_roots = {
        phase_id: value
        for argument, phase_id in PHASE_ROOT_ARGUMENTS.items()
        if (value := getattr(args, argument)) is not None
    }
    for phase_id, path in phase_roots.items():
        resolved = path.resolve()
        if resolved == output_root or not resolved.is_relative_to(output_root):
            raise ValueError(
                f"{phase_id} root is outside the new run root "
                f"{output_root}: {resolved}"
            )
        phase_roots[phase_id] = resolved
    manifest = (
        args.manifest.resolve()
        if args.manifest is not None
        else output_root / "plan.json"
    )
    if not manifest.is_relative_to(output_root):
        raise ValueError(
            f"plan manifest is outside new run root {output_root}: {manifest}"
        )
    if manifest.exists():
        raise FileExistsError(manifest)
    plan = build_plan(
        run_id=run_id,
        output_root=output_root,
        release_roms=releases,
        source_rom=source,
        workers=args.workers,
        display_base=args.display_base,
        phase_roots=phase_roots,
        validation_root=validation_root,
    )
    planned_phase_roots = [
        Path(path).resolve() for path in plan["phase_roots"].values()
    ]
    if any(
        manifest == phase_root or manifest.is_relative_to(phase_root)
        for phase_root in planned_phase_roots
    ):
        raise ValueError(
            "plan manifest must not create or occupy a planned phase root: "
            f"{manifest}"
        )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(manifest)
    print(
        f"planned: {len(PHASE_DEFINITIONS)} phases, "
        f"{EXPECTED_GATE_PASS_COUNT} immutable base checks plus "
        f"{len(REQUIRED_SCOPE_CONTRACT)} mandatory scope extensions "
        "(combined unit total pending)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
