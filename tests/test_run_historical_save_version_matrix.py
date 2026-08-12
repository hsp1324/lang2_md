from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools import run_historical_save_version_matrix as matrix
from tools import v137_release_identity as identity


class HistoricalSaveVersionMatrixTests(unittest.TestCase):
    """Unit-level schema samples only; none are runtime acceptance artifacts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.plan = matrix.build_plan("historical-matrix-test", cls.root / "artifacts")
        cls.visual = cls.root / "controller-capture.png"
        cls.visual.write_bytes(b"controller-visible-runtime-capture")
        cls.visual_sha256 = hashlib.sha256(cls.visual.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_exact_public_target_and_case_cardinality(self) -> None:
        self.assertEqual(self.plan["historical_target_count"], 17)
        self.assertEqual(self.plan["case_count"], 51)
        self.assertEqual(len(self.plan["historical_targets"]), 17)
        self.assertEqual(len(self.plan["cases"]), 51)
        self.assertEqual(
            [(row["release"], row["profile"]) for row in self.plan["historical_targets"]],
            [
                ("v1.3.1", "normal"),
                ("v1.3.1", "hard"),
                ("v1.3.2", "pure"),
                ("v1.3.2", "normal"),
                ("v1.3.2", "hard"),
                ("v1.3.3", "pure"),
                ("v1.3.3", "normal"),
                ("v1.3.3", "hard"),
                ("v1.3.4", "pure"),
                ("v1.3.4", "normal"),
                ("v1.3.4", "hard"),
                ("v1.3.5", "pure"),
                ("v1.3.5", "normal"),
                ("v1.3.5", "hard"),
                ("v1.3.6", "pure"),
                ("v1.3.6", "normal"),
                ("v1.3.6", "hard"),
            ],
        )
        self.assertFalse(
            any(row["release"] == "v1.3.0" for row in self.plan["historical_targets"])
        )

    def test_all_manifest_patch_and_reconstructed_rom_hashes_are_verified(self) -> None:
        expected = {
            (target.release, target.profile): target for target in matrix.HISTORICAL_TARGETS
        }
        for row in self.plan["historical_targets"]:
            target = expected[(row["release"], row["profile"])]
            self.assertEqual(row["manifest"]["sha256"], matrix.EXPECTED_MANIFEST_SHA256[target.release])
            self.assertEqual(row["patch"]["filename"], target.patch_filename)
            self.assertEqual(row["patch"]["bytes"], target.patch_size)
            self.assertEqual(row["patch"]["sha256"], target.patch_sha256)
            self.assertEqual(row["reconstructed_rom"]["bytes"], 0x400000)
            self.assertEqual(row["reconstructed_rom"]["sha256"], target.output_sha256)
            self.assertRegex(row["provenance_sha256"], r"^[0-9a-f]{64}$")

    def test_final_release_identity_is_the_frozen_three_profile_set(self) -> None:
        self.assertEqual(
            {profile: row["rom"]["sha256"] for profile, row in self.plan["final_targets"].items()},
            {
                "pure": identity.RELEASE_ROM_SHA256["pure"],
                "normal": identity.RELEASE_ROM_SHA256["normal"],
                "hard": identity.RELEASE_ROM_SHA256["hard"],
            },
        )

    def test_each_target_has_exactly_three_character_rows(self) -> None:
        grouped: dict[tuple[str, str], list[str]] = {}
        for case in self.plan["cases"]:
            grouped.setdefault((case["release"], case["profile"]), []).append(
                case["character"]["key"]
            )
        self.assertEqual(len(grouped), 17)
        for characters in grouped.values():
            self.assertEqual(characters, ["keith", "lester", "jessica"])

    def test_v132_v133_keith_and_lester_use_v131_damaged_lineage(self) -> None:
        lineage = [case for case in self.plan["cases"] if case["predecessor"]]
        self.assertEqual(
            [case["case_id"] for case in lineage],
            [
                "v1.3.2-pure-keith",
                "v1.3.2-pure-lester",
                "v1.3.2-normal-keith",
                "v1.3.2-normal-lester",
                "v1.3.2-hard-keith",
                "v1.3.2-hard-lester",
                "v1.3.3-pure-keith",
                "v1.3.3-pure-lester",
                "v1.3.3-normal-keith",
                "v1.3.3-normal-lester",
                "v1.3.3-hard-keith",
                "v1.3.3-hard-lester",
            ],
        )
        for case in lineage:
            expected_parent = "hard" if case["profile"] == "hard" else "normal"
            self.assertEqual(case["predecessor"]["release"], "v1.3.1")
            self.assertEqual(case["predecessor"]["profile"], expected_parent)
            self.assertEqual(case["expected_behavior"]["kind"], "recover_legacy_fighter_once")
            self.assertEqual(
                case["expected_behavior"]["historical_predicate"]["level"],
                {"operator": "at_least", "value": 11},
            )
            expected_raw = 0 if case["character"]["key"] == "keith" else 0x90
            self.assertEqual(
                case["expected_behavior"]["expected_current_join_raw_experience"],
                expected_raw,
            )
            stages = case["route_contract"]["stages"]
            self.assertIn(
                "predecessor_controller_only_natural_play_to_released_fighter_save",
                stages,
            )
            self.assertIn("historical_target_fresh_process_title_load", stages)
            self.assertIn(
                "historical_target_controller_only_natural_play_to_fighter_lv11_plus",
                stages,
            )
            self.assertIn("historical_target_stock_in_game_resave", stages)

    def test_v134_v136_lester_recovers_missed_tier1_join_once(self) -> None:
        cases = {
            case["case_id"]: case
            for case in self.plan["cases"]
        }
        for release in ("v1.3.4", "v1.3.5", "v1.3.6"):
            for profile in ("pure", "normal", "hard"):
                case = cases[f"{release}-{profile}-lester"]
                behavior = case["expected_behavior"]
                self.assertEqual(behavior["kind"], "recover_unselected_tier1_once")
                self.assertEqual(behavior["historical_predicate"]["class_id"], 7)
                self.assertEqual(
                    behavior["historical_predicate"]["level"],
                    {"operator": "equal", "value": 10},
                )
                self.assertEqual(behavior["expected_selected_class_id"], 5)
                self.assertEqual(behavior["expected_selected_level"], 5)
                self.assertEqual(behavior["expected_selected_experience"], 16)
                self.assertEqual(behavior["expected_current_join_exp_grant_count"], 1)
                self.assertEqual(behavior["expected_current_join_raw_experience"], 0x90)

    def test_v131_lester_covers_real_fighter_lv10_save(self) -> None:
        cases = {
            case["case_id"]: case
            for case in self.plan["cases"]
        }
        for profile in ("normal", "hard"):
            case = cases[f"v1.3.1-{profile}-lester"]
            predicate = case["expected_behavior"]["historical_predicate"]
            self.assertEqual(predicate["class_id"], 1)
            self.assertEqual(predicate["level"], {"operator": "equal", "value": 10})
            self.assertEqual(predicate["origin"], "fresh_v1.3.1_scenario10_result")

    def test_every_route_requires_real_save_exit_and_two_fresh_title_loads(self) -> None:
        for case in self.plan["cases"]:
            route = case["route_contract"]
            stages = route["stages"]
            self.assertIn(
                "historical_target_process_exit_and_8kib_sram_flush", stages
            )
            self.assertIn("current_first_fresh_process_cold_title_load", stages)
            self.assertIn("current_first_controller_only_progress_and_stock_resave", stages)
            self.assertIn("current_first_process_exit_and_8kib_sram_flush", stages)
            self.assertIn("current_second_fresh_process_title_load", stages)
            self.assertIn("current_second_controller_visible_status_confirmation", stages)
            self.assertEqual(route["required_input_surface"], "controller_only")
            self.assertEqual(route["historical_save_surface"], "stock_in_game_save")
            self.assertEqual(route["state_artifact_inputs"], 0)
            self.assertEqual(route["external_save_inputs"], 0)
            self.assertEqual(route["direct_memory_mutations"], 0)
            self.assertEqual(route["scenario_selector_entries"], 0)

    def test_plan_is_explicitly_pending_and_cannot_claim_runtime_acceptance(self) -> None:
        self.assertEqual(self.plan["runtime_status"], "pending_controller_execution")
        self.assertFalse(self.plan["acceptance_claimed"])
        self.assertFalse(self.plan["policy"]["emulator_state_input_allowed"])
        self.assertFalse(self.plan["policy"]["external_save_input_allowed"])
        self.assertFalse(self.plan["policy"]["direct_memory_or_save_mutation_allowed"])

    def test_plan_digest_is_deterministic_and_covers_artifact_root(self) -> None:
        duplicate = matrix.build_plan("historical-matrix-test", self.root / "artifacts")
        self.assertEqual(duplicate["plan_sha256"], self.plan["plan_sha256"])
        moved = matrix.build_plan("historical-matrix-test", self.root / "moved")
        self.assertNotEqual(moved["plan_sha256"], self.plan["plan_sha256"])

    def test_acceptance_source_has_no_state_or_save_mutation_call_path(self) -> None:
        source_path = Path(matrix.__file__)
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        banned_calls = {
            "save_gst",
            "recover_manual_slot_from_gst",
            "import_manual_slot_srm",
            "copy_manual_slot",
            "patch_manual_slot_commander_progress",
            "patch_manual_slot_scenario",
            "write_bytes",
        }
        observed_calls: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                observed_calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                observed_calls.add(node.func.attr)
        self.assertTrue(banned_calls.isdisjoint(observed_calls))
        self.assertNotIn("tools.run_blastem_sequence", source)
        self.assertNotIn("tools.run_natural_join_class_change_matrix", source)
        self.assertNotIn("tools.run_legacy_5a_runestone_release_matrix", source)

    def test_cli_surface_has_no_emulator_state_or_external_save_input(self) -> None:
        parser = matrix.parse_args(
            [
                "plan",
                "--run-id",
                "cli-test",
                "--artifact-root",
                str(self.root),
            ]
        )
        self.assertEqual(parser.command, "plan")
        source = Path(matrix.__file__).read_text(encoding="utf-8")
        banned_literals = (
            "manual-slot-gst",
            "manual-slot-srm",
            "manual-slot-copy-from",
            "seed-gst",
            "scenario-select",
        )
        for literal in banned_literals:
            self.assertNotIn(literal, source)

    def test_sram_snapshot_accepts_real_layout_and_rejects_corruption(self) -> None:
        commander = matrix.COMMANDERS[1]
        payload = self.valid_sram(commander.commander_id, 1, 11, 7)
        snapshot = matrix.sram_snapshot(payload, commander)
        self.assertEqual(snapshot["bytes"], 8192)
        self.assertEqual(snapshot["format_marker"], 0x07CA)
        self.assertEqual(snapshot["scenario"], 11)
        self.assertEqual(
            snapshot["selected_commander"],
            {
                "commander_id": 9,
                "class_id": 1,
                "level": 11,
                "experience": 7,
                "record_sha256": snapshot["selected_commander"]["record_sha256"],
            },
        )
        corrupted = bytearray(payload)
        corrupted[matrix.MANUAL_SLOT_BASE + 3] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            matrix.sram_snapshot(bytes(corrupted), commander)

    def test_complete_strict_evidence_verifies_51_rows(self) -> None:
        evidence = self.complete_evidence()
        report = matrix.verify_evidence(self.plan, evidence)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["release_acceptance_eligible"])
        self.assertEqual(report["historical_target_count"], 17)
        self.assertEqual(report["case_count"], 51)
        self.assertEqual(len(report["cases"]), 51)
        self.assertTrue(all(report["checks"].values()))

    def test_verifier_rejects_duplicate_exp_claim(self) -> None:
        evidence = self.complete_evidence()
        evidence["cases"][0]["progression_proof"]["duplicate_exp_grant_count"] = 1
        with self.assertRaisesRegex(ValueError, "duplicate EXP"):
            matrix.verify_evidence(self.plan, evidence)

    def test_verifier_rejects_missing_target_character_row(self) -> None:
        evidence = self.complete_evidence()
        evidence["cases"].pop()
        with self.assertRaisesRegex(ValueError, "case count"):
            matrix.verify_evidence(self.plan, evidence)

    def test_verifier_rejects_external_save_or_state_input(self) -> None:
        evidence = self.complete_evidence()
        evidence["cases"][0]["mechanism_counts"]["external_save_inputs"] = 1
        with self.assertRaisesRegex(ValueError, "external_save_inputs"):
            matrix.verify_evidence(self.plan, evidence)
        evidence = self.complete_evidence()
        evidence["cases"][0]["mechanism_counts"]["emulator_state_inputs"] = 1
        with self.assertRaisesRegex(ValueError, "emulator_state_inputs"):
            matrix.verify_evidence(self.plan, evidence)

    def test_verifier_rejects_reused_process_identity(self) -> None:
        evidence = self.complete_evidence()
        row = evidence["cases"][0]
        row["processes"]["current_second"]["pid"] = row["processes"]["current_first"]["pid"]
        with self.assertRaisesRegex(ValueError, "distinct emulator processes"):
            matrix.verify_evidence(self.plan, evidence)

    def test_verifier_rejects_non_natural_damaged_fighter_level(self) -> None:
        evidence = self.complete_evidence()
        row = next(
            item for item in evidence["cases"] if item["case_id"] == "v1.3.2-pure-lester"
        )
        payload = self.valid_sram(9, 1, 10, 25)
        row["sram_checkpoints"]["historical_after_exit"] = self.checkpoint(payload, matrix.COMMANDERS[1])
        row["current_first_load_input_sha256"] = hashlib.sha256(payload).hexdigest()
        with self.assertRaisesRegex(ValueError, "LV11"):
            matrix.verify_evidence(self.plan, evidence)

    def test_verifier_rejects_changed_preservation_case(self) -> None:
        evidence = self.complete_evidence()
        row = next(
            item for item in evidence["cases"] if item["case_id"] == "v1.3.6-normal-keith"
        )
        payload = self.valid_sram(7, 4, 3, 1)
        row["sram_checkpoints"]["current_after_resave_exit"] = self.checkpoint(
            payload, matrix.COMMANDERS[0]
        )
        row["current_second_load_input_sha256"] = hashlib.sha256(payload).hexdigest()
        row["progression_proof"]["second_load_visible_progress"] = {
            "class_id": 4,
            "level": 3,
            "experience": 1,
        }
        with self.assertRaisesRegex(ValueError, "preserved commander progress"):
            matrix.verify_evidence(self.plan, evidence)

    @staticmethod
    def valid_sram(
        commander_id: int,
        class_id: int,
        level: int,
        experience: int,
        scenario: int = 11,
    ) -> bytes:
        payload = bytearray(matrix.SRAM_BYTES)
        payload[matrix.MANUAL_SLOT_BASE : matrix.MANUAL_SLOT_BASE + 2] = scenario.to_bytes(2, "big")
        row = (
            matrix.MANUAL_SLOT_BASE
            + matrix.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
            + (commander_id - 1) * matrix.MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        payload[row] = class_id
        payload[row + 2] = level
        payload[row + 3] = experience
        payload[
            matrix.SRAM_FORMAT_MARKER_OFFSET : matrix.SRAM_FORMAT_MARKER_OFFSET + 2
        ] = matrix.SRAM_FORMAT_MARKER.to_bytes(2, "big")
        payload[
            matrix.SRAM_VALID_FLAGS_OFFSET : matrix.SRAM_VALID_FLAGS_OFFSET + 2
        ] = matrix.MANUAL_SLOT_VALID_BIT.to_bytes(2, "big")
        checksum = matrix.manual_slot_checksum(bytes(payload))
        checksum_at = matrix.MANUAL_SLOT_BASE + matrix.MANUAL_SLOT_CHECKSUM_OFFSET
        payload[checksum_at : checksum_at + 2] = checksum.to_bytes(2, "big")
        return bytes(payload)

    @staticmethod
    def checkpoint(payload: bytes, commander: matrix.Commander) -> dict[str, object]:
        return {
            "captured_after_process_exit": True,
            "payload_hex": payload.hex(),
            "snapshot": matrix.sram_snapshot(payload, commander),
        }

    def complete_evidence(self) -> dict[str, object]:
        # Synthetic bytes exercise rejection/acceptance branches in the
        # read-only verifier.  They are confined to TemporaryDirectory and
        # are never emitted as campaign or release evidence.
        rows: list[dict[str, object]] = []
        for index, case in enumerate(self.plan["cases"]):
            commander = matrix.Commander(**case["character"])
            behavior = case["expected_behavior"]
            if behavior["kind"] != "preserve_existing_progress":
                predicate = behavior["historical_predicate"]
                historical_level = predicate["level"]["value"]
                historical_payload = self.valid_sram(
                    commander.commander_id,
                    predicate["class_id"],
                    historical_level,
                    25,
                )
                current_payload = self.valid_sram(
                    commander.commander_id,
                    behavior["expected_selected_class_id"],
                    behavior["expected_selected_level"],
                    behavior["expected_selected_experience"],
                )
                transition_count = 1
            else:
                natural_progress = {
                    "keith": (4, 2, 0),
                    "lester": (7, 10, 25),
                    "jessica": (8, 3, 0),
                }[commander.key]
                historical_payload = self.valid_sram(
                    commander.commander_id, *natural_progress
                )
                current_payload = historical_payload
                transition_count = 0
            historical_snapshot = matrix.sram_snapshot(historical_payload, commander)
            current_snapshot = matrix.sram_snapshot(current_payload, commander)
            pid = 1000 + index * 10
            historical_processes: list[dict[str, object]] = []
            if case["predecessor"] is not None:
                historical_processes.append(
                    {
                        "role": "predecessor",
                        "pid": pid,
                        "rom_sha256": case["predecessor"]["reconstructed_rom"]["sha256"],
                        "fresh_process": True,
                        "exited_before_next": True,
                    }
                )
                pid += 1
            historical_processes.append(
                {
                    "role": "historical_target",
                    "pid": pid,
                    "rom_sha256": case["historical_target"]["reconstructed_rom"]["sha256"],
                    "fresh_process": True,
                    "exited_before_next": True,
                }
            )
            first_pid = pid + 1
            second_pid = pid + 2
            rows.append(
                {
                    "case_id": case["case_id"],
                    "release": case["release"],
                    "profile": case["profile"],
                    "character": commander.key,
                    "status": "pass",
                    "route_contract_sha256": case["route_contract"]["contract_sha256"],
                    "historical_provenance_sha256": case["historical_target"]["provenance_sha256"],
                    "final_provenance_sha256": case["final_target"]["provenance_sha256"],
                    "mechanism_counts": {
                        "emulator_state_inputs": 0,
                        "external_save_inputs": 0,
                        "manual_slot_mutations": 0,
                        "direct_ram_writes": 0,
                        "direct_sram_writes": 0,
                        "marker_injections": 0,
                        "scenario_selector_entries": 0,
                        "historical_stock_in_game_saves": 2 if case["predecessor"] else 1,
                        "current_stock_in_game_saves": 1,
                        "current_title_loads": 2,
                    },
                    "processes": {
                        "historical": historical_processes,
                        "current_first": {
                            "pid": first_pid,
                            "rom_sha256": case["final_target"]["rom"]["sha256"],
                            "fresh_process": True,
                            "cold_runtime_start": True,
                            "title_load_ui": True,
                            "exited_before_next": True,
                        },
                        "current_second": {
                            "pid": second_pid,
                            "rom_sha256": case["final_target"]["rom"]["sha256"],
                            "fresh_process": True,
                            "cold_runtime_start": True,
                            "title_load_ui": True,
                            "exited_before_next": True,
                        },
                    },
                    "sram_checkpoints": {
                        "historical_after_exit": self.checkpoint(
                            historical_payload, commander
                        ),
                        "current_after_resave_exit": self.checkpoint(
                            current_payload, commander
                        ),
                    },
                    "current_first_load_input_sha256": historical_snapshot["sha256"],
                    "current_second_load_input_sha256": current_snapshot["sha256"],
                    "progression_proof": {
                        "current_transition_count": transition_count,
                        "current_join_exp_grant_count": behavior[
                            "expected_current_join_exp_grant_count"
                        ],
                        "current_join_raw_experience": behavior[
                            "expected_current_join_raw_experience"
                        ],
                        "duplicate_exp_grant_count": 0,
                        "observation_method": "controller_opened_status_window_visual_decoder",
                        "second_load_visible_progress": {
                            "class_id": current_snapshot["selected_commander"]["class_id"],
                            "level": current_snapshot["selected_commander"]["level"],
                            "experience": current_snapshot["selected_commander"]["experience"],
                        },
                    },
                    "visual_artifacts": [
                        {
                            "phase": phase,
                            "path": str(self.visual),
                            "sha256": self.visual_sha256,
                        }
                        for phase in case["required_visual_artifact_phases"]
                    ],
                }
            )
        return {
            "schema_version": matrix.SCHEMA_VERSION,
            "kind": matrix.EVIDENCE_KIND,
            "run_id": self.plan["run_id"],
            "plan_sha256": self.plan["plan_sha256"],
            "status": "pass",
            "cases": rows,
        }


if __name__ == "__main__":
    unittest.main()
