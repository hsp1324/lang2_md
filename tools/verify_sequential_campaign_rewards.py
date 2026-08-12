#!/usr/bin/env python3
"""Verify exact item deltas and branch coverage in a continuous campaign run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_korean_jp_probe as korean_builder  # noqa: E402
from tools import build_current_result_probe_matrix as current_probes  # noqa: E402
from tools import run_current_result_revalidation_parallel as current_runners  # noqa: E402
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout  # noqa: E402


DEFAULT_MANIFEST = ROOT / "localization/v137_campaign_reward_expectations.json"
DEFAULT_RUNTIME_INVENTORY = ROOT / "localization/runtime_verification.json"
VALID_PROFILES = ("pure", "normal", "hard")
VALID_ITEM_IDS = frozenset(range(1, 38))
VALID_OWNERS = frozenset((*range(11), 0xFF))
RUNTIME_CLEAR_COMBAT_LOOT_SCENARIOS = (7, 8, 9, 23, 24, 26)
ALTERNATE_OBJECTIVE_EQUIPMENT_SCENARIOS = (14, 15, 16, 18, 21)
CONDITIONAL_VICTORY_GRANT_CONTRACT = {
    "scenario": 18,
    "item_id": 31,
    "flag": 30,
    "resident_name_ids": [0x20, 0x21],
    "skip_address": "0x1A4784",
    "address": "0x1A475E",
    "item_opcode_address": "0x1A477E",
    "expected_hex": (
        "2701032021FF001A47840A1E001A4784"
        "02203101001A56900200FF00001A5704031F0B001EFF"
    ),
}
CONDITIONAL_VICTORY_CHAIN_START = 0x1A475E
CONDITIONAL_VICTORY_CHAIN_END = 0x1A4784
CONDITIONAL_VICTORY_ITEM_OPCODE = 0x1A477E
BOUNDED_REWARD_CLAIM_KEYS = frozenset(
    {
        "runtime_clear_combat_loot",
        "alternate_objective_optional_equipment",
        "hidden_map_items",
        "conditional_victory_grants",
        "scenario31_alhazard",
        "scenario27_terminal_inventory",
    }
)


class VerificationError(ValueError):
    """A campaign summary or its source provenance is not canonical."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def parse_address(value: int | str) -> int:
    if isinstance(value, int):
        return value
    return int(value, 0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(payload, dict), f"JSON root is not an object: {path}")
    return payload


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def transition_awarded_item_ids(transition: dict[str, Any]) -> list[int]:
    """Return only items newly introduced by the selected serialized path."""
    kind = transition.get("kind")
    if kind == "append":
        return [int(item_id) for item_id in transition.get("item_ids", [])]
    if kind == "replace":
        return [int(transition["new_item_id"])]
    if kind in {"none", "terminal_unserialized"}:
        return []
    raise VerificationError(f"unknown transition kind {kind!r}")


def validate_bounded_reward_claims(manifest: dict[str, Any]) -> None:
    """Keep source-only exclusions separate from fresh runtime assertions."""
    claims = manifest.get("bounded_reward_claims")
    require(isinstance(claims, dict), "bounded reward claims are missing")
    require(
        set(claims) == BOUNDED_REWARD_CLAIM_KEYS,
        "bounded reward claim categories changed",
    )
    provenance = manifest.get("source_locks")
    require(isinstance(provenance, dict), "manifest source locks are missing")
    bypassed = provenance.get("runner_bypassed_combat_loot")
    require(isinstance(bypassed, list), "bypassed combat-loot locks are missing")
    bypassed_scenarios = [int(row["scenario"]) for row in bypassed]
    expected_partition = {
        *RUNTIME_CLEAR_COMBAT_LOOT_SCENARIOS,
        *ALTERNATE_OBJECTIVE_EQUIPMENT_SCENARIOS,
    }
    require(
        len(bypassed_scenarios) == len(set(bypassed_scenarios))
        and set(bypassed_scenarios) == expected_partition,
        "bypassed combat-loot source records changed scope",
    )

    for key, expected_scenarios in (
        ("runtime_clear_combat_loot", RUNTIME_CLEAR_COMBAT_LOOT_SCENARIOS),
        (
            "alternate_objective_optional_equipment",
            ALTERNATE_OBJECTIVE_EQUIPMENT_SCENARIOS,
        ),
    ):
        row = claims[key]
        require(isinstance(row, dict), f"{key} bounded claim is missing")
        require(
            row.get("scenarios") == list(expected_scenarios),
            f"{key} scenario scope changed",
        )
        require(row.get("source_records_locked") is True, f"{key} source lock claim changed")
        require(
            row.get("continuous_inventory_delta_excludes_record_equipment") is True,
            f"{key} inventory exclusion claim changed",
        )
        require(
            row.get("scripted_combat_or_contact_interaction_performed") is False,
            f"{key} must not claim an unperformed combat/contact interaction",
        )
        require(isinstance(row.get("claim"), str) and row["claim"], f"{key} claim text is missing")

    transitions = manifest.get("transitions")
    require(isinstance(transitions, dict), "manifest transitions are missing")
    for index, lock in enumerate(bypassed):
        scenario = int(lock["scenario"])
        equipment = [int(item_id) for item_id in lock["equipment_ids"] if item_id]
        require(equipment, f"bypassed combat-loot lock {index} has no equipment")
        awarded = transition_awarded_item_ids(transitions[str(scenario)])
        require(
            set(equipment).isdisjoint(awarded),
            f"Scenario {scenario} both excludes and awards fixed-record equipment",
        )

    hidden = claims["hidden_map_items"]
    hidden_locks = provenance.get("hidden_optional_grants")
    require(isinstance(hidden, dict), "hidden-map-item bounded claim is missing")
    require(isinstance(hidden_locks, list), "hidden item source locks are missing")
    require(
        hidden.get("source_lock_count") == len(hidden_locks) == 22,
        "hidden item source-lock count changed",
    )
    require(hidden.get("source_handlers_locked") is True, "hidden source-handler claim changed")
    require(
        hidden.get("scripted_tile_collection_performed") is False
        and hidden.get("continuous_inventory_delta_claimed") is False,
        "hidden items must remain source-only, not fresh collection claims",
    )

    conditional = claims["conditional_victory_grants"]
    conditional_locks = provenance.get("conditional_victory_grants")
    require(
        isinstance(conditional, dict),
        "conditional-victory-grant claim is missing",
    )
    require(
        conditional_locks == [CONDITIONAL_VICTORY_GRANT_CONTRACT],
        "Scenario 18 conditional-victory source contract changed",
    )
    require(
        set(conditional)
        == {
            "scenarios",
            "source_lock_count",
            "source_condition_chains_locked",
            "selected_victory_condition_performed",
            "continuous_inventory_delta_claimed",
            "item_ids",
            "hidden_tile_collection_performed",
            "claim",
        },
        "conditional-victory-grant claim fields changed",
    )
    require(
        conditional["scenarios"] == [18]
        and conditional["source_lock_count"] == 1
        and conditional["source_condition_chains_locked"] is True
        and conditional["selected_victory_condition_performed"] is True
        and conditional["continuous_inventory_delta_claimed"] is True
        and conditional["item_ids"] == [31]
        and conditional["hidden_tile_collection_performed"] is False
        and isinstance(conditional["claim"], str)
        and conditional["claim"],
        "Scenario 18 conditional-victory claim changed",
    )
    require(
        transitions["18"].get("kind") == "append"
        and transitions["18"].get("item_ids") == [31],
        "Scenario 18 Crown grant is not bound to its route transition",
    )
    scenario18_bypassed = [
        lock for lock in bypassed if int(lock["scenario"]) == 18
    ]
    require(
        len(scenario18_bypassed) == 1
        and scenario18_bypassed[0].get("equipment_ids") == [0, 0, 30],
        "Scenario 18 Lana Speed Boots exclusion changed",
    )
    require(
        set(transition_awarded_item_ids(transitions["18"])) == {31}
        and 30 not in transition_awarded_item_ids(transitions["18"]),
        "Scenario 18 must exclude Speed Boots 30 and award only Crown 31",
    )

    alhazard = claims["scenario31_alhazard"]
    require(isinstance(alhazard, dict), "Scenario 31 Alhazard claim is missing")
    require(
        {
            "scenario": alhazard.get("scenario"),
            "record_index": alhazard.get("record_index"),
            "item_id": alhazard.get("item_id"),
        }
        == {"scenario": 31, "record_index": 9, "item_id": 14},
        "Scenario 31 Alhazard source identity changed",
    )
    require(
        alhazard.get("source_record_locked") is True
        and alhazard.get("continuous_inventory_delta_excludes_item") is True
        and alhazard.get("special_item_claimed_as_loot") is False,
        "Scenario 31 Alhazard bounded claim changed",
    )
    route_loot = provenance.get("route_combat_loot")
    alhazard_records = [
        row
        for row in route_loot
        if int(row["scenario"]) == 31 and int(row["record_index"]) == 9
    ] if isinstance(route_loot, list) else []
    require(len(alhazard_records) == 1, "Scenario 31 reward source record is missing")
    require(
        14 in alhazard_records[0].get("excluded_equipment_ids", [])
        and 14 not in alhazard_records[0].get("route_loot_item_ids", []),
        "Scenario 31 Alhazard is not explicitly excluded from route loot",
    )

    terminal = claims["scenario27_terminal_inventory"]
    require(isinstance(terminal, dict), "Scenario 27 terminal claim is missing")
    require(
        terminal.get("scenario") == 27
        and terminal.get("transition_kind") == "terminal_unserialized"
        and terminal.get("serialized_output_expected") is False
        and terminal.get("inventory_delta_asserted") is False,
        "Scenario 27 terminal inventory claim changed",
    )
    require(
        transitions["27"].get("kind") == "terminal_unserialized",
        "Scenario 27 transition must remain terminal and unserialized",
    )


def validate_manifest(manifest: dict[str, Any]) -> None:
    require(manifest.get("schema_version") == 1, "unsupported reward manifest")
    route = manifest.get("route_order")
    require(isinstance(route, list), "manifest route_order is missing")
    require(len(route) == 31, "manifest route must contain 31 steps")
    require(set(route) == set(range(1, 32)), "manifest route is not 1..31")
    require(
        manifest.get("expected_profiles") == list(VALID_PROFILES),
        "manifest profiles are not pure/normal/hard",
    )
    transitions = manifest.get("transitions")
    require(isinstance(transitions, dict), "manifest transitions are missing")
    require(
        set(transitions) == {str(scenario) for scenario in route},
        "manifest transitions do not cover the exact route",
    )
    runner_contracts = manifest.get("runner_contracts")
    require(isinstance(runner_contracts, dict), "manifest runner contracts are missing")
    require(
        set(runner_contracts) == {str(scenario) for scenario in route},
        "manifest runner contracts do not cover the exact route",
    )
    for scenario in route:
        contract = runner_contracts[str(scenario)]
        definition = current_probes.PROBE_DEFINITIONS[scenario]
        require(
            contract["probe_filename"] == definition["filename"]
            and contract["probe_kwargs"] == definition["kwargs"]
            and contract["runner"] == current_runners.RUNNERS[scenario],
            f"Scenario {scenario} current-result runner contract changed",
        )
    item_names = manifest.get("item_names")
    require(isinstance(item_names, dict), "manifest item catalog is missing")
    require(
        set(item_names) == {str(item_id) for item_id in VALID_ITEM_IDS},
        "manifest item catalog is not the exact 1..37 ID set",
    )
    branches = manifest.get("branch_coverage")
    require(isinstance(branches, list), "manifest branch coverage is missing")
    require(
        {row.get("scenario") for row in branches} == set(range(1, 32)),
        "manifest branch coverage does not cover scenarios 1..31",
    )
    confirmations = manifest.get("focused_runtime_confirmations")
    require(
        isinstance(confirmations, list), "focused runtime confirmations are missing"
    )
    require(
        {row.get("scenario") for row in confirmations} == {19, 23, 24, 26, 30, 31},
        "focused runtime confirmations changed scope",
    )
    validate_bounded_reward_claims(manifest)
    for row in confirmations:
        scenario = int(row["scenario"])
        for field in ("input_record_sha256", "output_record_sha256"):
            digest = row[field]
            require(
                isinstance(digest, str)
                and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest),
                f"Scenario {scenario} focused confirmation has invalid {field}",
            )
        before = [
            {"slot": slot, "item_id": item_id, "owner": 0xFF}
            for slot, item_id in enumerate(row["before_item_ids"])
        ]
        expected = expected_inventory_after(
            before, transitions[str(scenario)], scenario=scenario
        )
        require(
            [item["item_id"] for item in expected] == row["after_item_ids"],
            f"Scenario {scenario} focused runtime confirmation contradicts its transition",
        )


def verify_byte_range(source: bytes, lock: dict[str, Any], label: str) -> None:
    address = parse_address(lock["address"])
    expected = bytes.fromhex(lock["expected_hex"])
    actual = source[address : address + len(expected)]
    require(
        actual == expected,
        f"{label} source bytes changed at 0x{address:06X}: "
        f"{actual.hex().upper()} != {expected.hex().upper()}",
    )
    expected_sha256 = lock.get("sha256")
    if expected_sha256 is not None:
        require(
            sha256_bytes(actual) == expected_sha256,
            f"{label} source range SHA-256 changed at 0x{address:06X}",
        )


def verify_source_locks(
    manifest: dict[str, Any],
    *,
    source_path: Path | None = None,
    runtime_inventory_path: Path = DEFAULT_RUNTIME_INVENTORY,
) -> dict[str, Any]:
    """Lock reward IDs to Japanese bytes and branch labels to reviewed data."""
    validate_manifest(manifest)
    source_spec = manifest["source_rom"]
    source_path = source_path or ROOT / source_spec["path"]
    source = source_path.read_bytes()
    actual_source_sha256 = sha256_bytes(source)
    require(
        actual_source_sha256 == source_spec["sha256"],
        "Japanese source ROM SHA-256 changed: "
        f"{actual_source_sha256} != {source_spec['sha256']}",
    )

    provenance = manifest["source_locks"]
    checked_ranges = 0
    for category in (
        "explicit_script_grants",
        "conditional_victory_grants",
        "hidden_optional_grants",
        "event_handlers",
    ):
        for index, lock in enumerate(provenance[category]):
            verify_byte_range(source, lock, f"{category}[{index}]")
            checked_ranges += 1

    for index, lock in enumerate(provenance["explicit_script_grants"]):
        opcode = parse_address(lock["item_opcode_address"])
        expected_opcode = bytes((0x03, int(lock["item_id"])))
        require(
            source[opcode : opcode + 2] == expected_opcode,
            f"explicit_script_grants[{index}] item opcode/ID changed",
        )
        transition = manifest["transitions"][str(lock["scenario"])]
        require(
            transition.get("kind") == "append"
            and transition.get("item_ids") == [lock["item_id"]],
            f"explicit_script_grants[{index}] is not bound to its route transition",
        )

    for index, lock in enumerate(provenance["hidden_optional_grants"]):
        opcode = parse_address(lock["address"]) + 8
        expected_opcode = bytes((0x03, int(lock["item_id"]), 0x0B)) + int(
            lock["flag"]
        ).to_bytes(2, "big")
        require(
            source[opcode : opcode + 5] == expected_opcode,
            f"hidden_optional_grants[{index}] item ID/flag changed",
        )

    for index, lock in enumerate(provenance["conditional_victory_grants"]):
        start = parse_address(lock["address"])
        end = start + len(bytes.fromhex(lock["expected_hex"]))
        opcode = parse_address(lock["item_opcode_address"])
        require(
            start == CONDITIONAL_VICTORY_CHAIN_START
            and end == CONDITIONAL_VICTORY_CHAIN_END
            and opcode == CONDITIONAL_VICTORY_ITEM_OPCODE,
            f"conditional_victory_grants[{index}] source range changed",
        )
        expected_opcode = bytes((0x03, int(lock["item_id"]), 0x0B)) + int(
            lock["flag"]
        ).to_bytes(2, "big")
        require(
            source[opcode : opcode + 5] == expected_opcode,
            f"conditional_victory_grants[{index}] item ID/flag changed",
        )
        require(
            source[start : start + 16]
            == bytes.fromhex("2701032021FF001A47840A1E001A4784"),
            f"conditional_victory_grants[{index}] resident/flag guard changed",
        )
        transition = manifest["transitions"][str(lock["scenario"])]
        require(
            transition.get("kind") == "append"
            and transition.get("item_ids") == [lock["item_id"]],
            f"conditional_victory_grants[{index}] is not bound to its route transition",
        )

    checked_records = 0
    route_loot_by_scenario: dict[int, list[int]] = {}
    for category in ("route_combat_loot", "runner_bypassed_combat_loot"):
        for index, lock in enumerate(provenance[category]):
            scenario = int(lock["scenario"])
            record_index = int(lock["record_index"])
            layout = scenario_layout(source, scenario)
            require(
                0 <= record_index < layout.record_count,
                f"{category}[{index}] record index is outside Scenario {scenario}",
            )
            address = layout.records_offset + record_index * FIXED_RECORD_SIZE
            require(
                address == parse_address(lock["address"]),
                f"{category}[{index}] record address changed: 0x{address:06X}",
            )
            record = source[address : address + FIXED_RECORD_SIZE]
            require(
                record.hex().upper() == lock["expected_hex"],
                f"{category}[{index}] Scenario {scenario} record {record_index} changed",
            )
            require(
                list(record[1:4]) == lock["equipment_ids"],
                f"{category}[{index}] Scenario {scenario} equipment IDs changed",
            )
            if category == "route_combat_loot":
                nonzero_equipment = [
                    item_id for item_id in lock["equipment_ids"] if item_id
                ]
                awarded = lock.get("route_loot_item_ids", nonzero_equipment)
                excluded = lock.get("excluded_equipment_ids", [])
                require(
                    sorted((*awarded, *excluded)) == sorted(nonzero_equipment),
                    f"{category}[{index}] loot/exclusion policy does not cover its equipment",
                )
                route_loot_by_scenario.setdefault(scenario, []).extend(awarded)
            checked_records += 1

    for scenario, item_ids in route_loot_by_scenario.items():
        transition = manifest["transitions"][str(scenario)]
        require(
            transition.get("kind") == "append"
            and transition.get("item_ids") == item_ids,
            f"Scenario {scenario} combat records are not bound to the route delta",
        )

    expected_screens = [
        row["condition_screen"]
        for row in sorted(manifest["branch_coverage"], key=lambda row: row["scenario"])
    ]
    require(
        korean_builder.CONDITION_SCREENS[:31] == expected_screens,
        "reviewed condition-screen branch inventory changed",
    )

    runtime_inventory = load_json(runtime_inventory_path)
    historical = {
        int(row["scenario"]): row.get("branches_endings")
        for row in runtime_inventory.get("scenarios", [])
    }
    for row in manifest["branch_coverage"]:
        scenario = int(row["scenario"])
        require(
            historical.get(scenario) == row["historical_branches_endings_status"],
            f"Scenario {scenario} historical branches/endings status changed",
        )

    return {
        "status": "pass",
        "source_rom": relative(source_path),
        "source_sha256": actual_source_sha256,
        "byte_ranges_checked": checked_ranges,
        "fixed_records_checked": checked_records,
        "condition_screens_checked": 31,
        "historical_branch_rows_checked": 31,
        "current_result_runner_contracts_checked": 31,
        "focused_runtime_confirmations_checked": len(
            manifest["focused_runtime_confirmations"]
        ),
        "bounded_source_only_claims": {
            "bypassed_fixed_equipment_records": len(
                provenance["runner_bypassed_combat_loot"]
            ),
            "runtime_clear_records": len(RUNTIME_CLEAR_COMBAT_LOOT_SCENARIOS),
            "alternate_objective_records": len(
                ALTERNATE_OBJECTIVE_EQUIPMENT_SCENARIOS
            ),
            "hidden_item_handlers": len(provenance["hidden_optional_grants"]),
            "hidden_tile_collections_performed": 0,
            "scenario31_alhazard_claimed_as_loot": False,
            "scenario27_serialized_inventory_available": False,
        },
        "selected_route_reward_claims": {
            "conditional_victory_grants": len(
                provenance["conditional_victory_grants"]
            ),
            "scenarios": [
                int(lock["scenario"])
                for lock in provenance["conditional_victory_grants"]
            ],
            "item_ids": [
                int(lock["item_id"])
                for lock in provenance["conditional_victory_grants"]
            ],
            "event_flags": [
                int(lock["flag"])
                for lock in provenance["conditional_victory_grants"]
            ],
            "hidden_tile_collections_claimed": 0,
        },
    }


def validate_inventory(snapshot: Any, label: str) -> list[dict[str, int]]:
    require(isinstance(snapshot, dict), f"{label} is not a state object")
    inventory = snapshot.get("inventory")
    require(isinstance(inventory, list), f"{label}.inventory is missing")
    normalized: list[dict[str, int]] = []
    previous_slot = -1
    for index, row in enumerate(inventory):
        require(isinstance(row, dict), f"{label}.inventory[{index}] is not an object")
        require(
            set(row) == {"slot", "item_id", "owner"},
            f"{label}.inventory[{index}] has unexpected fields",
        )
        slot = row["slot"]
        item_id = row["item_id"]
        owner = row["owner"]
        require(isinstance(slot, int) and 0 <= slot < 40, f"{label} has invalid slot")
        require(
            slot > previous_slot, f"{label} inventory slots are not unique and ordered"
        )
        require(item_id in VALID_ITEM_IDS, f"{label} has invalid item ID {item_id}")
        require(owner in VALID_OWNERS, f"{label} has invalid owner {owner}")
        normalized.append({"slot": slot, "item_id": item_id, "owner": owner})
        previous_slot = slot
    return normalized


def expected_inventory_after(
    before: list[dict[str, int]],
    transition: dict[str, Any],
    *,
    scenario: int,
) -> list[dict[str, int]]:
    expected = [dict(row) for row in before]
    kind = transition["kind"]
    if kind == "none":
        return expected
    if kind == "append":
        occupied = {row["slot"] for row in expected}
        for item_id in transition["item_ids"]:
            require(
                item_id in VALID_ITEM_IDS,
                f"Scenario {scenario} manifest item ID is invalid",
            )
            slot = next(
                (candidate for candidate in range(40) if candidate not in occupied),
                None,
            )
            require(
                slot is not None,
                f"Scenario {scenario} inventory has no free reward slot",
            )
            expected.append({"slot": slot, "item_id": item_id, "owner": 0xFF})
            occupied.add(slot)
        expected.sort(key=lambda row: row["slot"])
        return expected
    if kind == "replace":
        old_item_id = transition["old_item_id"]
        new_item_id = transition["new_item_id"]
        matches = [row for row in expected if row["item_id"] == old_item_id]
        require(
            len(matches) == 1,
            f"Scenario {scenario} needs exactly one item {old_item_id} to replace",
        )
        matches[0]["item_id"] = new_item_id
        return expected
    if kind == "terminal_unserialized":
        return expected
    raise VerificationError(f"Scenario {scenario} has unknown transition kind {kind!r}")


def item_delta(
    before: list[dict[str, int]], after: list[dict[str, int]]
) -> list[dict[str, Any]]:
    before_by_slot = {row["slot"]: row for row in before}
    after_by_slot = {row["slot"]: row for row in after}
    delta = []
    for slot in sorted(before_by_slot.keys() | after_by_slot.keys()):
        old = before_by_slot.get(slot)
        new = after_by_slot.get(slot)
        if old != new:
            delta.append({"slot": slot, "before": old, "after": new})
    return delta


def verify_summary(summary: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify exact route, save continuity, and reward transitions."""
    validate_manifest(manifest)
    route = manifest["route_order"]
    profiles = manifest["expected_profiles"]
    require(summary.get("schema_version") == 1, "unsupported campaign summary")
    require(summary.get("status") == "pass", "campaign summary did not pass")
    require(
        summary.get("profiles") == profiles,
        "campaign profiles are incomplete or reordered",
    )
    require(summary.get("route_order") == route, "campaign route order changed")
    require(
        summary.get("continuous_save_chain") is True,
        "campaign is not a continuous save chain",
    )
    require(
        summary.get("manual_intervention") is False, "campaign used manual intervention"
    )
    require(summary.get("automation_only") is True, "campaign is not automation-only")
    require(
        summary.get("release_roms_unchanged") is True,
        "release ROMs changed during campaign",
    )
    require(
        summary.get("release_roms") == summary.get("release_roms_after"),
        "release ROM identity differs before and after campaign",
    )
    require(summary.get("passed_profiles") == 3, "not every profile passed")
    require(summary.get("total_profiles") == 3, "campaign profile total is not three")
    run_id = summary.get("run_id")
    require(isinstance(run_id, str) and run_id, "campaign run_id is missing")
    profile_rows = summary.get("results")
    require(isinstance(profile_rows, list), "campaign profile results are missing")
    require(
        [row.get("profile") for row in profile_rows] == profiles,
        "campaign profile result order changed",
    )

    bypassed_by_scenario: dict[int, dict[str, Any]] = {
        int(row["scenario"]): row
        for row in manifest["source_locks"]["runner_bypassed_combat_loot"]
    }
    conditional_by_scenario: dict[int, dict[str, Any]] = {
        int(row["scenario"]): row
        for row in manifest["source_locks"]["conditional_victory_grants"]
    }
    profile_reports = []
    for profile_row in profile_rows:
        profile = profile_row["profile"]
        require(profile_row.get("status") == "pass", f"{profile} profile did not pass")
        require(profile_row.get("run_id") == run_id, f"{profile} run_id changed")
        require(
            profile_row.get("manual_intervention") is False,
            f"{profile} used manual intervention",
        )
        require(
            profile_row.get("passed_steps") == 31, f"{profile} did not pass 31 steps"
        )
        require(
            profile_row.get("total_steps") == 31, f"{profile} total step count changed"
        )
        rows = profile_row.get("results")
        require(
            isinstance(rows, list) and len(rows) == 31,
            f"{profile} lacks 31 scenario rows",
        )
        require(
            [row.get("scenario") for row in rows] == route,
            f"{profile} route rows changed",
        )

        previous_output: dict[str, Any] | None = None
        transitions_report = []
        bounded_reward_audits = []
        conditional_victory_grant_audits = []
        for route_index, (scenario, row) in enumerate(zip(route, rows, strict=True)):
            label = f"{profile} Scenario {scenario}"
            require(row.get("profile") == profile, f"{label} profile field changed")
            require(row.get("scenario") == scenario, f"{label} scenario field changed")
            require(
                row.get("route_index") == route_index, f"{label} route index changed"
            )
            require(row.get("run_id") == run_id, f"{label} run_id changed")
            require(row.get("status") == "pass", f"{label} did not pass")
            require(
                row.get("returncode") == 0, f"{label} runner return code is not zero"
            )
            require(
                row.get("manual_intervention") is False,
                f"{label} used manual intervention",
            )
            contract = manifest["runner_contracts"][str(scenario)]
            rom = row.get("rom")
            require(
                isinstance(rom, str) and Path(rom).name == contract["probe_filename"],
                f"{label} probe ROM contract changed",
            )
            command = row.get("command")
            require(
                isinstance(command, list)
                and command
                and Path(command[0]).name == contract["runner"],
                f"{label} result runner contract changed",
            )

            input_state = row.get("input_state")
            before = validate_inventory(input_state, f"{label}.input_state")
            expected_input_scenario = (
                1
                if route_index == 0
                else manifest["next_scenario"][str(route[route_index - 1])]
            )
            require(
                input_state.get("scenario") == expected_input_scenario,
                f"{label} input scenario changed",
            )
            if previous_output is not None:
                require(
                    input_state.get("record_sha256")
                    == previous_output.get("record_sha256"),
                    f"{label} input record is not the preceding output",
                )
                require(
                    before
                    == validate_inventory(previous_output, f"{label}.previous_output"),
                    f"{label} inventory is not continuous with the preceding save",
                )

            transition = manifest["transitions"][str(scenario)]
            expected_next = manifest["next_scenario"][str(scenario)]
            require(
                row.get("expected_next_scenario") == expected_next,
                f"{label} next scenario changed",
            )
            output_state = row.get("output_state")
            if transition["kind"] == "terminal_unserialized":
                require(
                    expected_next is None, f"{label} terminal next scenario is not null"
                )
                require(
                    output_state is None,
                    f"{label} unexpectedly serialized terminal output",
                )
                transitions_report.append(
                    {
                        "scenario": scenario,
                        "kind": transition["kind"],
                        "status": "pass",
                        "observed_delta": "not_serialized_terminal",
                    }
                )
                bounded_reward_audits.append(
                    {
                        "scenario": scenario,
                        "category": "terminal_unserialized",
                        "status": "bounded_no_inventory_assertion",
                        "serialized_output_present": False,
                        "inventory_delta_asserted": False,
                    }
                )
                previous_output = None
                continue

            after = validate_inventory(output_state, f"{label}.output_state")
            require(
                output_state.get("scenario") == expected_next,
                f"{label} output scenario changed",
            )
            expected_after = expected_inventory_after(
                before, transition, scenario=scenario
            )
            require(
                after == expected_after,
                f"{label} inventory delta mismatch: observed {item_delta(before, after)!r}, "
                f"expected {item_delta(before, expected_after)!r}",
            )
            observed_delta = item_delta(before, after)
            gained_item_ids = [
                int(change["after"]["item_id"])
                for change in observed_delta
                if change["after"] is not None
                and (
                    change["before"] is None
                    or change["before"]["item_id"]
                    != change["after"]["item_id"]
                )
            ]
            bypassed = bypassed_by_scenario.get(scenario)
            if bypassed is not None:
                excluded_item_ids = [
                    int(item_id)
                    for item_id in bypassed["equipment_ids"]
                    if item_id
                ]
                require(
                    set(excluded_item_ids).isdisjoint(gained_item_ids),
                    f"{label} unexpectedly serialized bypassed fixed-record equipment",
                )
                bounded_reward_audits.append(
                    {
                        "scenario": scenario,
                        "category": (
                            "runtime_clear_combat_loot"
                            if scenario in RUNTIME_CLEAR_COMBAT_LOOT_SCENARIOS
                            else "alternate_objective_optional_equipment"
                        ),
                        "status": "source_locked_runtime_delta_excludes_equipment",
                        "fixed_record_index": int(bypassed["record_index"]),
                        "excluded_item_ids": excluded_item_ids,
                        "observed_gained_item_ids": gained_item_ids,
                        "scripted_combat_or_contact_interaction_performed": False,
                    }
                )
            conditional_grant = conditional_by_scenario.get(scenario)
            if conditional_grant is not None:
                asserted_item_ids = [int(conditional_grant["item_id"])]
                require(
                    gained_item_ids == asserted_item_ids,
                    f"{label} conditional-victory grant changed: "
                    f"{gained_item_ids} != {asserted_item_ids}",
                )
                require(
                    bypassed is not None
                    and [
                        int(item_id)
                        for item_id in bypassed["equipment_ids"]
                        if item_id
                    ]
                    == [30],
                    f"{label} Lana Speed Boots exclusion changed",
                )
                conditional_victory_grant_audits.append(
                    {
                        "scenario": scenario,
                        "category": "resident_survival_conditional_victory_grant",
                        "status": "source_locked_runtime_delta_asserts_reward",
                        "source_chain": {
                            "start": conditional_grant["address"],
                            "end_exclusive": conditional_grant["skip_address"],
                            "resident_name_ids": conditional_grant[
                                "resident_name_ids"
                            ],
                            "event_flag": int(conditional_grant["flag"]),
                        },
                        "excluded_bypassed_fixed_equipment_ids": [30],
                        "asserted_item_ids": asserted_item_ids,
                        "observed_gained_item_ids": gained_item_ids,
                        "selected_victory_condition_performed": True,
                        "hidden_tile_collection_performed": False,
                    }
                )
            if scenario == 31:
                require(14 not in gained_item_ids, f"{label} unexpectedly serialized Alhazard")
                require(
                    all(item_id in gained_item_ids for item_id in (21, 36)),
                    f"{label} did not serialize the asserted non-special equipment",
                )
                bounded_reward_audits.append(
                    {
                        "scenario": 31,
                        "category": "special_nonloot_equipment",
                        "status": "source_locked_runtime_delta_excludes_alhazard",
                        "excluded_item_id": 14,
                        "asserted_item_ids": [21, 36],
                        "observed_gained_item_ids": gained_item_ids,
                        "special_item_claimed_as_loot": False,
                    }
                )
            transitions_report.append(
                {
                    "scenario": scenario,
                    "kind": transition["kind"],
                    "status": "pass",
                    "observed_delta": observed_delta,
                }
            )
            previous_output = output_state

        profile_reports.append(
            {
                "profile": profile,
                "status": "pass",
                "scenarios_checked": len(transitions_report),
                "transitions": transitions_report,
                "bounded_reward_audits": bounded_reward_audits,
                "conditional_victory_grant_audits": (
                    conditional_victory_grant_audits
                ),
            }
        )

    alternate_victories = sum(
        len(row["fresh_dynamic"]["alternate_victories_not_exercised"])
        for row in manifest["branch_coverage"]
    )
    defeat_conditions = sum(
        len(row["fresh_dynamic"]["defeats_not_exercised"])
        for row in manifest["branch_coverage"]
    )
    return {
        "status": "pass",
        "run_id": run_id,
        "profiles_checked": profiles,
        "route_steps_per_profile": 31,
        "inventory_transitions_checked": 93,
        "canonical_transitions": [
            {
                "scenario": scenario,
                **manifest["transitions"][str(scenario)],
            }
            for scenario in route
        ],
        "profiles": profile_reports,
        "bounded_reward_coverage": {
            "runtime_exclusion_audits": sum(
                len(row["bounded_reward_audits"]) for row in profile_reports
            ),
            "bypassed_record_audits_per_profile": len(bypassed_by_scenario),
            "hidden_map_item_source_locks": len(
                manifest["source_locks"]["hidden_optional_grants"]
            ),
            "hidden_tile_collections_performed": 0,
            "hidden_inventory_deltas_asserted": 0,
            "conditional_victory_grant_source_locks": len(
                manifest["source_locks"]["conditional_victory_grants"]
            ),
            "conditional_victory_grant_runtime_assertions": sum(
                len(row["conditional_victory_grant_audits"])
                for row in profile_reports
            ),
            "scenario31_alhazard_claimed_as_loot": False,
            "scenario27_serialized_output_present": False,
            "scenario27_inventory_delta_asserted": False,
            "claims": manifest["bounded_reward_claims"],
        },
        "conditional_victory_grant_coverage": {
            "source_locks": len(
                manifest["source_locks"]["conditional_victory_grants"]
            ),
            "runtime_assertions": sum(
                len(row["conditional_victory_grant_audits"])
                for row in profile_reports
            ),
            "expected_runtime_assertions": len(profiles)
            * len(manifest["source_locks"]["conditional_victory_grants"]),
            "scenarios": sorted(conditional_by_scenario),
            "item_ids": sorted(
                int(lock["item_id"])
                for lock in manifest["source_locks"][
                    "conditional_victory_grants"
                ]
            ),
            "event_flags": sorted(
                int(lock["flag"])
                for lock in manifest["source_locks"][
                    "conditional_victory_grants"
                ]
            ),
            "hidden_tile_collections_performed": 0,
        },
        "branch_coverage": {
            "fresh_selected_victory_paths": 31,
            "fresh_alternate_victories_not_exercised": alternate_victories,
            "fresh_defeat_conditions_not_exercised": defeat_conditions,
            "historical_status_source": relative(DEFAULT_RUNTIME_INVENTORY),
            "scenarios": [
                {
                    "scenario": row["scenario"],
                    "fresh_selected_victory": row["fresh_dynamic"]["selected_victory"],
                    "fresh_alternate_victories_not_exercised": row["fresh_dynamic"][
                        "alternate_victories_not_exercised"
                    ],
                    "fresh_defeats_not_exercised": row["fresh_dynamic"][
                        "defeats_not_exercised"
                    ],
                    "historical_branches_endings_status": row[
                        "historical_branches_endings_status"
                    ],
                }
                for row in manifest["branch_coverage"]
            ],
            "scope_note": (
                "The continuous run exercises one selected victory path per scenario. "
                "Alternate victories and defeats remain historical/static coverage, not "
                "fresh dynamic claims."
            ),
        },
        "known_dynamic_gaps": manifest["known_dynamic_gaps"],
    }


def build_report(
    summary_path: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
    source_path: Path | None = None,
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    source_report = verify_source_locks(manifest, source_path=source_path)
    summary = load_json(summary_path)
    campaign_report = verify_summary(summary, manifest)
    return {
        "schema_version": 1,
        "status": "pass",
        "scope": "v1.3.7 continuous campaign reward and branch audit",
        "summary": relative(summary_path),
        "manifest": relative(manifest_path),
        "source_provenance": source_report,
        "campaign": campaign_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", nargs="?", type=Path)
    parser.add_argument("--summary", dest="summary_option", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-rom", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary_path = args.summary_option or args.summary
    if summary_path is None:
        parser.error("a summary path is required (positional or --summary)")
    try:
        report = build_report(summary_path, args.manifest, args.source_rom)
    except (
        OSError,
        json.JSONDecodeError,
        VerificationError,
        KeyError,
        TypeError,
        IndexError,
    ) as exc:
        failure = {
            "schema_version": 1,
            "status": "fail",
            "summary": relative(summary_path),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        rendered = json.dumps(failure, ensure_ascii=False, indent=2) + "\n"
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 1

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
