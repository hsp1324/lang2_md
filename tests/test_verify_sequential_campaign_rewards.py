from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import verify_sequential_campaign_rewards as rewards


ROOT = Path(__file__).resolve().parents[1]


def state(scenario: int, record_sha256: str, inventory: list[dict[str, int]]):
    return {
        "scenario": scenario,
        "record_sha256": record_sha256,
        "inventory": deepcopy(inventory),
    }


def synthetic_summary(manifest: dict) -> dict:
    route = deepcopy(manifest["route_order"])
    profiles = deepcopy(manifest["expected_profiles"])
    run_id = "synthetic-reward-chain"
    profile_reports = []
    for profile in profiles:
        inventory: list[dict[str, int]] = []
        input_state = state(1, f"{profile}-seed", inventory)
        rows = []
        for route_index, scenario in enumerate(route):
            transition = manifest["transitions"][str(scenario)]
            expected_next = manifest["next_scenario"][str(scenario)]
            output_state = None
            if transition["kind"] != "terminal_unserialized":
                inventory = rewards.expected_inventory_after(
                    input_state["inventory"], transition, scenario=scenario
                )
                output_state = state(
                    expected_next,
                    f"{profile}-route-{route_index}-output",
                    inventory,
                )
            rows.append(
                {
                    "profile": profile,
                    "scenario": scenario,
                    "rom": (
                        f"tmp/probes/{profile}/"
                        f"{manifest['runner_contracts'][str(scenario)]['probe_filename']}"
                    ),
                    "command": [
                        f"tools/{manifest['runner_contracts'][str(scenario)]['runner']}"
                    ],
                    "route_index": route_index,
                    "run_id": run_id,
                    "returncode": 0,
                    "status": "pass",
                    "manual_intervention": False,
                    "input_state": deepcopy(input_state),
                    "output_state": deepcopy(output_state),
                    "expected_next_scenario": expected_next,
                }
            )
            if output_state is not None:
                input_state = output_state
        profile_reports.append(
            {
                "profile": profile,
                "status": "pass",
                "run_id": run_id,
                "manual_intervention": False,
                "passed_steps": 31,
                "total_steps": 31,
                "results": rows,
            }
        )
    release_roms = {
        profile: {"path": f"{profile}.md", "sha256": profile * 16}
        for profile in profiles
    }
    return {
        "schema_version": 1,
        "status": "pass",
        "run_id": run_id,
        "profiles": profiles,
        "route_order": route,
        "continuous_save_chain": True,
        "manual_intervention": False,
        "automation_only": True,
        "release_roms": release_roms,
        "release_roms_after": deepcopy(release_roms),
        "release_roms_unchanged": True,
        "passed_profiles": 3,
        "total_profiles": 3,
        "results": profile_reports,
    }


def scenario_row(summary: dict, scenario: int, profile: str = "pure") -> dict:
    profile_row = next(row for row in summary["results"] if row["profile"] == profile)
    return next(row for row in profile_row["results"] if row["scenario"] == scenario)


class SequentialCampaignRewardVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = rewards.load_json(rewards.DEFAULT_MANIFEST)

    def test_source_opcodes_records_hidden_items_and_branch_inventory_are_locked(
        self,
    ) -> None:
        report = rewards.verify_source_locks(self.manifest)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["byte_ranges_checked"], 33)
        self.assertEqual(report["fixed_records_checked"], 17)
        self.assertEqual(report["condition_screens_checked"], 31)
        self.assertEqual(report["focused_runtime_confirmations_checked"], 6)
        bounded = report["bounded_source_only_claims"]
        self.assertEqual(bounded["bypassed_fixed_equipment_records"], 11)
        self.assertEqual(bounded["runtime_clear_records"], 6)
        self.assertEqual(bounded["alternate_objective_records"], 5)
        self.assertEqual(bounded["hidden_item_handlers"], 22)
        self.assertEqual(bounded["hidden_tile_collections_performed"], 0)
        self.assertFalse(bounded["scenario31_alhazard_claimed_as_loot"])
        self.assertFalse(bounded["scenario27_serialized_inventory_available"])
        selected = report["selected_route_reward_claims"]
        self.assertEqual(selected["conditional_victory_grants"], 1)
        self.assertEqual(selected["scenarios"], [18])
        self.assertEqual(selected["item_ids"], [31])
        self.assertEqual(selected["event_flags"], [30])
        self.assertEqual(selected["hidden_tile_collections_claimed"], 0)

    def test_exact_synthetic_three_profile_chain_passes(self) -> None:
        report = rewards.verify_summary(synthetic_summary(self.manifest), self.manifest)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["inventory_transitions_checked"], 93)
        self.assertEqual(len(report["profiles"]), 3)
        bounded = report["bounded_reward_coverage"]
        self.assertEqual(bounded["runtime_exclusion_audits"], 39)
        self.assertEqual(bounded["bypassed_record_audits_per_profile"], 11)
        self.assertEqual(bounded["hidden_map_item_source_locks"], 22)
        self.assertEqual(bounded["hidden_tile_collections_performed"], 0)
        self.assertEqual(bounded["hidden_inventory_deltas_asserted"], 0)
        self.assertEqual(bounded["conditional_victory_grant_source_locks"], 1)
        self.assertEqual(bounded["conditional_victory_grant_runtime_assertions"], 3)
        self.assertFalse(bounded["scenario31_alhazard_claimed_as_loot"])
        self.assertFalse(bounded["scenario27_inventory_delta_asserted"])
        conditional = report["conditional_victory_grant_coverage"]
        self.assertEqual(conditional["source_locks"], 1)
        self.assertEqual(conditional["runtime_assertions"], 3)
        self.assertEqual(conditional["expected_runtime_assertions"], 3)
        self.assertEqual(conditional["scenarios"], [18])
        self.assertEqual(conditional["item_ids"], [31])
        self.assertEqual(conditional["event_flags"], [30])
        self.assertEqual(conditional["hidden_tile_collections_performed"], 0)
        for profile in report["profiles"]:
            audits = profile["bounded_reward_audits"]
            self.assertEqual(len(audits), 13)
            runtime_clear = {
                row["scenario"]
                for row in audits
                if row["category"] == "runtime_clear_combat_loot"
            }
            self.assertEqual(
                runtime_clear,
                set(rewards.RUNTIME_CLEAR_COMBAT_LOOT_SCENARIOS),
            )
            scenario18_bypass = next(
                row for row in audits if row["scenario"] == 18
            )
            self.assertEqual(scenario18_bypass["excluded_item_ids"], [30])
            self.assertEqual(scenario18_bypass["observed_gained_item_ids"], [31])
            conditional_audits = profile["conditional_victory_grant_audits"]
            self.assertEqual(len(conditional_audits), 1)
            scenario18_grant = conditional_audits[0]
            self.assertEqual(scenario18_grant["scenario"], 18)
            self.assertEqual(
                scenario18_grant["excluded_bypassed_fixed_equipment_ids"],
                [30],
            )
            self.assertEqual(scenario18_grant["asserted_item_ids"], [31])
            self.assertEqual(scenario18_grant["observed_gained_item_ids"], [31])
            self.assertFalse(scenario18_grant["hidden_tile_collection_performed"])
            terminal = next(row for row in audits if row["scenario"] == 27)
            self.assertEqual(terminal["status"], "bounded_no_inventory_assertion")

    def test_missing_script_reward_fails(self) -> None:
        summary = synthetic_summary(self.manifest)
        scenario_row(summary, 2)["output_state"]["inventory"] = []
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 2 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_missing_scenario18_conditional_crown_fails(self) -> None:
        summary = synthetic_summary(self.manifest)
        row = scenario_row(summary, 18)
        row["output_state"]["inventory"] = deepcopy(
            row["input_state"]["inventory"]
        )
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 18 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_wrong_scenario18_conditional_reward_fails(self) -> None:
        summary = synthetic_summary(self.manifest)
        scenario_row(summary, 18)["output_state"]["inventory"][-1][
            "item_id"
        ] = 30
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 18 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_wrong_reward_id_fails(self) -> None:
        summary = synthetic_summary(self.manifest)
        scenario_row(summary, 13)["output_state"]["inventory"][-1]["item_id"] = 7
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 13 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_unexpected_reward_on_no_delta_scenario_fails(self) -> None:
        summary = synthetic_summary(self.manifest)
        output = scenario_row(summary, 3)["output_state"]["inventory"]
        output.append({"slot": 1, "item_id": 1, "owner": 0xFF})
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 3 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_reward_owner_change_fails(self) -> None:
        summary = synthetic_summary(self.manifest)
        scenario_row(summary, 2)["output_state"]["inventory"][0]["owner"] = 1
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 2 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_existing_slot_mutation_fails(self) -> None:
        summary = synthetic_summary(self.manifest)
        scenario_row(summary, 3)["output_state"]["inventory"][0]["item_id"] = 4
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 3 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_scenario24_requires_same_slot_langrisser_replacement(self) -> None:
        summary = synthetic_summary(self.manifest)
        output = scenario_row(summary, 24)["output_state"]["inventory"]
        langrisser = next(row for row in output if row["item_id"] == 9)
        langrisser["item_id"] = 8
        output.append(
            {
                "slot": max(row["slot"] for row in output) + 1,
                "item_id": 9,
                "owner": 0xFF,
            }
        )
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 24 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_scenario26_rejects_contact_loot_on_runtime_clear_path(self) -> None:
        summary = synthetic_summary(self.manifest)
        output = scenario_row(summary, 26)["output_state"]["inventory"]
        output.append(
            {
                "slot": max(row["slot"] for row in output) + 1,
                "item_id": 13,
                "owner": 0xFF,
            }
        )
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 26 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_scenario31_excludes_special_alhazard_but_requires_other_equipment(
        self,
    ) -> None:
        summary = synthetic_summary(self.manifest)
        output = scenario_row(summary, 31)["output_state"]["inventory"]
        self.assertEqual([row["item_id"] for row in output[-2:]], [21, 36])
        output.insert(-2, {"slot": output[-2]["slot"], "item_id": 14, "owner": 0xFF})
        output[-2]["slot"] += 1
        output[-1]["slot"] += 1
        with self.assertRaisesRegex(
            rewards.VerificationError, "Scenario 31 inventory delta mismatch"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_bounded_claim_cannot_say_bypassed_combat_was_performed(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["bounded_reward_claims"]["runtime_clear_combat_loot"][
            "scripted_combat_or_contact_interaction_performed"
        ] = True
        with self.assertRaisesRegex(
            rewards.VerificationError,
            "must not claim an unperformed combat/contact interaction",
        ):
            rewards.validate_manifest(manifest)

    def test_bounded_claim_requires_exact_bypass_partition(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["bounded_reward_claims"]["runtime_clear_combat_loot"][
            "scenarios"
        ].remove(23)
        with self.assertRaisesRegex(
            rewards.VerificationError,
            "runtime_clear_combat_loot scenario scope changed",
        ):
            rewards.validate_manifest(manifest)

    def test_hidden_items_cannot_be_promoted_to_runtime_collection_claim(self) -> None:
        manifest = deepcopy(self.manifest)
        hidden = manifest["bounded_reward_claims"]["hidden_map_items"]
        hidden["scripted_tile_collection_performed"] = True
        hidden["continuous_inventory_delta_claimed"] = True
        with self.assertRaisesRegex(
            rewards.VerificationError,
            "hidden items must remain source-only",
        ):
            rewards.validate_manifest(manifest)

    def test_scenario18_conditional_grant_cannot_be_called_hidden_collection(
        self,
    ) -> None:
        manifest = deepcopy(self.manifest)
        conditional = manifest["bounded_reward_claims"][
            "conditional_victory_grants"
        ]
        conditional["hidden_tile_collection_performed"] = True
        with self.assertRaisesRegex(
            rewards.VerificationError,
            "Scenario 18 conditional-victory claim changed",
        ):
            rewards.validate_manifest(manifest)

    def test_scenario18_conditional_grant_requires_runtime_delta_claim(self) -> None:
        manifest = deepcopy(self.manifest)
        conditional = manifest["bounded_reward_claims"][
            "conditional_victory_grants"
        ]
        conditional["continuous_inventory_delta_claimed"] = False
        with self.assertRaisesRegex(
            rewards.VerificationError,
            "Scenario 18 conditional-victory claim changed",
        ):
            rewards.validate_manifest(manifest)

    def test_scenario18_transition_must_award_crown_not_speed_boots(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["transitions"]["18"]["item_ids"] = [30]
        with self.assertRaisesRegex(
            rewards.VerificationError,
            "both excludes and awards fixed-record equipment",
        ):
            rewards.validate_manifest(manifest)

    def test_scenario18_conditional_source_contract_is_exact(self) -> None:
        mutations = (
            ("address", "0x1A475F"),
            ("item_opcode_address", "0x1A477F"),
            ("item_id", 30),
            ("flag", 29),
            ("resident_name_ids", [32, 34]),
            ("skip_address", "0x1A4785"),
            ("expected_hex", "00"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                manifest = deepcopy(self.manifest)
                manifest["source_locks"]["conditional_victory_grants"][0][
                    field
                ] = value
                with self.assertRaisesRegex(
                    rewards.VerificationError,
                    "conditional-victory source contract changed",
                ):
                    rewards.validate_manifest(manifest)

    def test_scenario31_alhazard_must_remain_explicitly_excluded(self) -> None:
        manifest = deepcopy(self.manifest)
        record = next(
            row
            for row in manifest["source_locks"]["route_combat_loot"]
            if row["scenario"] == 31
        )
        record["excluded_equipment_ids"] = []
        record["route_loot_item_ids"].append(14)
        with self.assertRaisesRegex(
            rewards.VerificationError,
            "Alhazard is not explicitly excluded",
        ):
            rewards.validate_manifest(manifest)

    def test_scenario27_cannot_claim_a_serialized_inventory(self) -> None:
        manifest = deepcopy(self.manifest)
        terminal = manifest["bounded_reward_claims"][
            "scenario27_terminal_inventory"
        ]
        terminal["inventory_delta_asserted"] = True
        with self.assertRaisesRegex(
            rewards.VerificationError,
            "Scenario 27 terminal inventory claim changed",
        ):
            rewards.validate_manifest(manifest)

    def test_route_profile_and_status_are_fail_closed(self) -> None:
        for mutate, message in (
            (lambda summary: summary["route_order"].reverse(), "route order changed"),
            (lambda summary: summary["profiles"].pop(), "profiles are incomplete"),
            (lambda summary: summary.__setitem__("status", "fail"), "did not pass"),
        ):
            with self.subTest(message=message):
                summary = synthetic_summary(self.manifest)
                mutate(summary)
                with self.assertRaisesRegex(rewards.VerificationError, message):
                    rewards.verify_summary(summary, self.manifest)

    def test_probe_and_runner_contracts_are_fail_closed(self) -> None:
        summary = synthetic_summary(self.manifest)
        scenario_row(summary, 5)["rom"] = "tmp/probes/pure/wrong.md"
        with self.assertRaisesRegex(
            rewards.VerificationError, "probe ROM contract changed"
        ):
            rewards.verify_summary(summary, self.manifest)

        summary = synthetic_summary(self.manifest)
        scenario_row(summary, 5)["command"][0] = "tools/wrong.py"
        with self.assertRaisesRegex(
            rewards.VerificationError, "result runner contract changed"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_terminal_scenario_must_not_serialize_output(self) -> None:
        summary = synthetic_summary(self.manifest)
        row = scenario_row(summary, 27)
        row["output_state"] = deepcopy(row["input_state"])
        with self.assertRaisesRegex(
            rewards.VerificationError, "unexpectedly serialized terminal output"
        ):
            rewards.verify_summary(summary, self.manifest)

    def test_changed_hidden_item_source_byte_fails_even_with_updated_rom_hash(
        self,
    ) -> None:
        manifest = deepcopy(self.manifest)
        source = bytearray((ROOT / manifest["source_rom"]["path"]).read_bytes())
        hidden = manifest["source_locks"]["hidden_optional_grants"][0]
        source[rewards.parse_address(hidden["address"]) + 9] ^= 1
        manifest["source_rom"]["sha256"] = hashlib.sha256(source).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "changed-source.md"
            path.write_bytes(source)
            with self.assertRaisesRegex(
                rewards.VerificationError,
                r"hidden_optional_grants\[0\] source bytes changed",
            ):
                rewards.verify_source_locks(manifest, source_path=path)

    def test_changed_scenario18_conditional_chain_byte_fails_with_updated_rom_hash(
        self,
    ) -> None:
        manifest = deepcopy(self.manifest)
        source = bytearray((ROOT / manifest["source_rom"]["path"]).read_bytes())
        conditional = manifest["source_locks"]["conditional_victory_grants"][0]
        source[rewards.parse_address(conditional["address"]) + 3] ^= 1
        manifest["source_rom"]["sha256"] = hashlib.sha256(source).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "changed-source.md"
            path.write_bytes(source)
            with self.assertRaisesRegex(
                rewards.VerificationError,
                r"conditional_victory_grants\[0\] source bytes changed",
            ):
                rewards.verify_source_locks(manifest, source_path=path)

    def test_changed_scenario18_item_opcode_or_flag_fails(self) -> None:
        for offset in (0, 3):
            with self.subTest(offset=offset):
                manifest = deepcopy(self.manifest)
                source = bytearray(
                    (ROOT / manifest["source_rom"]["path"]).read_bytes()
                )
                conditional = manifest["source_locks"][
                    "conditional_victory_grants"
                ][0]
                opcode = rewards.parse_address(conditional["item_opcode_address"])
                source[opcode + offset] ^= 1
                manifest["source_rom"]["sha256"] = hashlib.sha256(source).hexdigest()
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "changed-source.md"
                    path.write_bytes(source)
                    with self.assertRaisesRegex(
                        rewards.VerificationError,
                        r"conditional_victory_grants\[0\] source bytes changed",
                    ):
                        rewards.verify_source_locks(manifest, source_path=path)

    def test_cli_accepts_explicit_summary_path_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            summary_path = root / "summary.json"
            output_path = root / "reward-report.json"
            summary_path.write_text(
                json.dumps(synthetic_summary(self.manifest), ensure_ascii=False),
                encoding="utf-8",
            )
            with (
                mock.patch.object(
                    rewards.sys,
                    "argv",
                    [
                        "verify_sequential_campaign_rewards.py",
                        "--summary",
                        str(summary_path),
                        "--output",
                        str(output_path),
                    ],
                ),
                mock.patch("builtins.print"),
            ):
                self.assertEqual(rewards.main(), 0)
            self.assertEqual(json.loads(output_path.read_text())["status"], "pass")


if __name__ == "__main__":
    unittest.main()
