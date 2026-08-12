import hashlib
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tools import verify_hard_mode_first_turn as first_turn


class HardModeFirstTurnTests(unittest.TestCase):
    def require_legacy_file(self, path):
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = first_turn.ROOT / resolved
        if not resolved.is_file():
            self.skipTest("ignored legacy emulator evidence is absent")
        return resolved

    @staticmethod
    def current_entry_evidence(number):
        return first_turn.entry_evidence(
            number,
            loader_results_path=(
                first_turn.CURRENT_CANDIDATE_LOADER_RESULTS
            ),
        )

    def test_entry_evidence_uses_loader_and_deep_manifests(self):
        self.assertEqual(first_turn.entry_evidence(2)["kind"], "loader_smoke")
        self.assertEqual(first_turn.entry_evidence(1)["kind"], "loader_smoke")
        self.assertTrue(first_turn.entry_evidence(1)["hash_locked"])

    def test_retained_entry_hashes_match_manifests(self):
        for number in (1, 2, 16, 25, 27):
            evidence = self.current_entry_evidence(number)
            self.require_legacy_file(evidence["path"])
            path, digest, _ = first_turn.validate_entry_evidence(
                number,
                evidence,
            )
            self.assertEqual(
                first_turn.sha256(path),
                digest,
            )
            if evidence["hash_locked"]:
                self.assertEqual(
                    digest,
                    evidence["sha256"],
                )

    def test_mutable_loader_entry_is_validated_by_runtime_data(self):
        source = self.current_entry_evidence(31)
        self.require_legacy_file(source["path"])
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "loader.json"
            manifest.write_text(
                json.dumps(
                    {
                        "scenarios": [
                            {
                                "number": 31,
                                "gst": str(
                                    Path(source["path"]).relative_to(
                                        first_turn.ROOT
                                    )
                                ),
                                "gst_sha256": source["sha256"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            evidence = first_turn.entry_evidence(
                31,
                loader_results_path=manifest,
            )
            self.assertFalse(evidence["hash_locked"])
            path, digest, player_group_count = (
                first_turn.validate_entry_evidence(31, evidence)
            )
            self.assertEqual(first_turn.sha256(path), digest)
            self.assertEqual(player_group_count, 10)

    def test_custom_loader_manifest_retains_rom_lineage(self):
        source = self.current_entry_evidence(3)
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "loader.json"
            manifest.write_text(
                json.dumps(
                    {
                        "hard_rom": {"sha256": "candidate-sha256"},
                        "scenarios": [
                            {
                                "number": 3,
                                "gst": str(
                                    Path(source["path"]).relative_to(
                                        first_turn.ROOT
                                    )
                                ),
                                "gst_sha256": source["sha256"],
                                "runtime_gst": "runtime/quicksave.gst",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            evidence = first_turn.entry_evidence(
                3,
                loader_results_path=manifest,
            )
            self.assertEqual(
                evidence["manifest_path"],
                manifest.resolve(),
            )
            self.assertEqual(
                evidence["manifest_rom_sha256"],
                "candidate-sha256",
            )
            self.assertTrue(evidence["hash_locked"])
            self.assertIsNone(evidence["runtime_name"])

            first_turn.validate_entry_rom_lineage(
                evidence,
                "candidate-sha256",
                required=True,
            )
            with self.assertRaisesRegex(
                ValueError,
                "does not match selected ROM",
            ):
                first_turn.validate_entry_rom_lineage(
                    evidence,
                    "different-sha256",
                    required=True,
                )

            no_rom_hash = dict(evidence)
            no_rom_hash["manifest_rom_sha256"] = None
            with self.assertRaisesRegex(
                ValueError,
                "has no hard-ROM SHA-256",
            ):
                first_turn.validate_entry_rom_lineage(
                    no_rom_hash,
                    "candidate-sha256",
                    required=True,
                )

    def test_direct_entry_is_hash_locked_to_selected_rom(self):
        source = self.current_entry_evidence(3)["path"]
        self.require_legacy_file(source)
        evidence = first_turn.direct_entry_evidence(
            Path(source),
            rom_digest="fresh-rom-sha256",
        )
        self.assertEqual(evidence["kind"], "direct_current_rom")
        self.assertTrue(evidence["hash_locked"])
        self.assertIsNone(evidence["manifest_path"])
        self.assertEqual(
            evidence["manifest_rom_sha256"],
            "fresh-rom-sha256",
        )
        path, digest, player_group_count = (
            first_turn.validate_entry_evidence(3, evidence)
        )
        self.assertEqual(path, Path(source).resolve())
        self.assertEqual(digest, evidence["sha256"])
        self.assertIsNone(player_group_count)

    def test_current_candidate_entry_retains_versioned_runtime_name(self):
        evidence = self.current_entry_evidence(6)
        self.assertEqual(evidence["runtime_name"], "hard-fbe2-s06")

    def test_turn_counter_reads_work_ram_byte(self):
        data = bytearray(first_turn.TURN_COUNTER_FILE_OFFSET + 1)
        data[first_turn.TURN_COUNTER_FILE_OFFSET] = 2
        self.assertEqual(first_turn.turn_counter(bytes(data)), 2)

    @mock.patch.object(
        first_turn,
        "wait_for_title_screen",
        return_value=7,
    )
    @mock.patch.object(first_turn, "run_command")
    def test_game_over_dismissal_confirms_before_title_wait(
        self,
        run_command,
        wait_for_title_screen,
    ):
        env = {"DISPLAY": ":104"}
        self.assertEqual(
            first_turn.dismiss_game_over_and_wait_for_title(
                display=":104",
                env=env,
                max_checks=20,
                delay=0.3,
            ),
            7,
        )
        self.assertEqual(run_command.call_args.kwargs["env"], env)
        self.assertEqual(run_command.call_args.args[0][-1], "c:1.0")
        wait_for_title_screen.assert_called_once_with(
            display=":104",
            env=env,
            max_checks=20,
            delay=0.3,
        )

    def test_start_menu_detector_separates_unit_command_panel(self):
        start_menu = (
            first_turn.ROOT
            / "captures/run/1ab2_s22_current_start_menu_turn2.png"
        )
        command_menu = (
            first_turn.ROOT
            / "captures/run/1ab2_s22_current_jessica_command.png"
        )
        self.assertTrue(first_turn.start_menu_visible(start_menu))
        self.assertFalse(first_turn.start_menu_visible(command_menu))

    def test_start_menu_detector_accepts_blue_scenario_10_map(self):
        start_menu = (
            first_turn.ROOT
            / "captures/run/hard_8674_s10_start_menu_detector.png"
        )
        self.assertTrue(first_turn.start_menu_visible(start_menu))

    def test_start_menu_cursor_detector_reads_first_and_last_rows(self):
        first_row = (
            first_turn.ROOT
            / "captures/run/1ab2_s22_current_start_menu_turn2.png"
        )
        last_row = (
            first_turn.ROOT
            / "captures/run/hard_8674_s03_turn_end_cursor.png"
        )
        self.assertEqual(
            first_turn.start_menu_cursor_row(self.require_legacy_file(first_row)),
            0,
        )
        self.assertEqual(
            first_turn.start_menu_cursor_row(self.require_legacy_file(last_row)),
            4,
        )

    def test_retain_endpoint_gst_replaces_snapshot_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            original_root = first_turn.ROOT
            try:
                first_turn.ROOT = Path(directory)
                destination = first_turn.retain_endpoint_gst(7, b"endpoint")
                self.assertEqual(destination.read_bytes(), b"endpoint")
                self.assertFalse(destination.with_suffix(".gst.tmp").exists())
            finally:
                first_turn.ROOT = original_root

    def test_retain_endpoint_gst_separates_candidate_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            original_root = first_turn.ROOT
            try:
                first_turn.ROOT = Path(directory)
                destination = first_turn.retain_endpoint_gst(
                    20,
                    b"candidate",
                    evidence_prefix="hard_candidate_first_turn",
                )
                self.assertEqual(
                    destination.name,
                    "hard_candidate_first_turn_s20_endpoint.gst",
                )
                self.assertEqual(destination.read_bytes(), b"candidate")
            finally:
                first_turn.ROOT = original_root

    def test_endpoint_classification_requires_turn_two_command(self):
        self.assertEqual(
            first_turn.classify_endpoint("turn_command", 2),
            "turn_2_command",
        )
        with self.assertRaises(ValueError):
            first_turn.classify_endpoint("turn_command", 1)
        with self.assertRaisesRegex(
            ValueError,
            "not an approved first-turn endpoint",
        ):
            first_turn.classify_endpoint("game_over", 1)
        self.assertEqual(
            first_turn.classify_endpoint(
                "game_over",
                1,
                expected={"endpoint": "game_over_turn_1"},
            ),
            "game_over_turn_1",
        )
        with self.assertRaises(ValueError):
            first_turn.classify_endpoint("title_screen", 1)
        expected = first_turn.expected_endpoint(6)
        self.assertEqual(
            first_turn.classify_endpoint(
                "title_screen",
                1,
                expected=expected,
            ),
            "defeat_return_title_turn_1",
        )
        with self.assertRaises(ValueError):
            first_turn.classify_endpoint(
                "title_screen",
                2,
                expected=expected,
            )

    def test_title_defeat_exceptions_require_normal_comparison_evidence(self):
        self.assertEqual(
            first_turn.expected_endpoint(6)["endpoint"],
            "defeat_return_title_turn_1",
        )
        self.assertEqual(
            first_turn.expected_endpoint(13)["endpoint"],
            "defeat_return_title_turn_1",
        )
        self.assertIsNone(first_turn.expected_endpoint(5))
        self.assertIsNone(first_turn.expected_endpoint(7))
        self.assertEqual(
            first_turn.expected_endpoint(12)["endpoint"],
            "defeat_return_title_turn_1",
        )
        self.assertIsNone(first_turn.expected_endpoint(14))

    def test_scenario_12_rng_boundary_accepts_defeat_or_turn_two(self):
        expected_release_roms = {
            "pure_rom": (
                "roms/builds/Langrisser II (Korean Original v1.3.7).md",
                "66b4bc9b04e06b7e18f7d7f341d59ad5cfab02e480b3ff0949d277ba04a6f5a9",
            ),
            "normal_rom": (
                "roms/builds/Langrisser II (Korean Normal v1.3.7).md",
                "3f7de8fd1b4695c62e764fef5ed06bf4c96d1974f1296863c46f903ac21d69f5",
            ),
            "hard_rom": (
                "roms/builds/Langrisser II (Korean Hard v1.3.7).md",
                "6646c1ce86e960ea33228f6ef41e7b1b3cd1b39f9fa8779a3172d6c75c65a878",
            ),
        }
        for profile in ("pure", "normal", "hard"):
            expected = first_turn.expected_endpoint(12, profile=profile)
            self.assertTrue(expected["rng_sensitive"])
            self.assertTrue(expected["turn_2_also_valid"])
            self.assertEqual(
                first_turn.classify_endpoint(
                    "title_screen",
                    1,
                    expected=expected,
                ),
                "defeat_return_title_turn_1",
            )
            self.assertEqual(
                first_turn.classify_endpoint(
                    "turn_command",
                    2,
                    expected=expected,
                ),
                "turn_2_command",
            )

        expected = first_turn.expected_endpoint(12)
        for key, (path, digest) in expected_release_roms.items():
            self.assertEqual(expected[key]["path"], path)
            self.assertEqual(expected[key]["sha256"], digest)

        comparisons = expected["comparison_evidence"]
        self.assertTrue(
            any(
                row.get("observed_endpoint") == "turn_2_command"
                for row in comparisons
            )
        )

    def test_scenario_11_defeat_policy_is_profile_specific(self):
        self.assertEqual(
            first_turn.expected_endpoint(11, profile="pure")["endpoint"],
            "defeat_return_title_turn_1",
        )
        self.assertEqual(
            first_turn.expected_endpoint(11, profile="normal")["endpoint"],
            "defeat_return_title_turn_1",
        )
        self.assertIsNone(first_turn.expected_endpoint(11, profile="hard"))

    def test_missing_ignored_legacy_evidence_does_not_block_fresh_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "endpoints.json"
            path.write_text(
                json.dumps(
                    {
                        "scenarios": [
                            {
                                "number": 31,
                                "profiles": ["normal"],
                                "endpoint": "defeat_return_title_turn_1",
                                "normal_evidence": [
                                    {
                                        "path": "captures/missing.png",
                                        "sha256": "0" * 64,
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            approved, hint = first_turn.expected_endpoint_context(
                31,
                profile="normal",
                allow_unapproved_defeat=False,
                path=path,
            )
            self.assertEqual(
                approved["endpoint"], "defeat_return_title_turn_1"
            )
            self.assertIs(hint, approved)
            self.assertFalse(approved["archival_evidence_complete"])
            self.assertFalse(approved["archival_evidence"][0]["available"])

            approved, hint = first_turn.expected_endpoint_context(
                31,
                profile="hard",
                allow_unapproved_defeat=True,
                path=path,
            )
            self.assertIsNone(approved)
            self.assertEqual(hint["endpoint"], "defeat_return_title_turn_1")

    def test_save_result_replaces_scenario_and_updates_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            rom_digest = "current-candidate"
            results = {
                "schema_version": 1,
                "status": "in_progress",
                "hard_rom": {"sha256": rom_digest},
                "scenarios": [
                    {
                        "number": 2,
                        "status": "first_turn_runtime_verified",
                        "entry_evidence": {
                            "manifest_rom_sha256": rom_digest,
                        },
                    },
                    {"number": 3, "status": "old"},
                ],
            }
            first_turn.save_result(
                path,
                results,
                {
                    "number": 3,
                    "status": "first_turn_runtime_verified",
                    "entry_evidence": {
                        "manifest_rom_sha256": rom_digest,
                    },
                },
            )
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                [row["number"] for row in written["scenarios"]],
                [2, 3],
            )
            self.assertEqual(
                written["coverage"]["verified_scenarios"],
                [2, 3],
            )
            self.assertIn(1, written["coverage"]["missing_scenarios"])

    def test_load_results_drops_rows_from_other_rom_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            rom = directory_path / "candidate.md"
            rom.write_bytes(b"current hard candidate")
            rom_digest = hashlib.sha256(rom.read_bytes()).hexdigest()
            results_path = directory_path / "results.json"
            results_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "all_scenarios_first_turn_verified",
                        "hard_rom": {"sha256": "stale-candidate"},
                        "scenarios": [
                            {
                                "number": 1,
                                "status": "first_turn_runtime_verified",
                                "entry_evidence": {
                                    "manifest_rom_sha256": rom_digest,
                                },
                            },
                            {
                                "number": 12,
                                "status": "first_turn_runtime_verified",
                                "entry_evidence": {
                                    "manifest_rom_sha256": "stale-candidate",
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(
                first_turn,
                "relative",
                return_value="candidate.md",
            ):
                results = first_turn.load_results(results_path, rom)

            self.assertEqual(
                [row["number"] for row in results["scenarios"]],
                [1],
            )
            self.assertEqual(
                results["coverage"]["verified_scenarios"],
                [1],
            )
            self.assertIn(12, results["coverage"]["missing_scenarios"])
            self.assertEqual(results["status"], "in_progress")

    def test_update_coverage_ignores_mixed_candidate_lineage(self):
        results = {
            "hard_rom": {"sha256": "current-candidate"},
            "scenarios": [
                {
                    "number": 1,
                    "status": "first_turn_runtime_verified",
                    "entry_evidence": {
                        "manifest_rom_sha256": "current-candidate",
                    },
                },
                {
                    "number": 2,
                    "status": "first_turn_runtime_verified",
                    "entry_evidence": {
                        "manifest_rom_sha256": "older-candidate",
                    },
                },
            ],
        }

        first_turn.update_coverage(results)

        self.assertEqual(results["coverage"]["verified_scenarios"], [1])
        self.assertIn(2, results["coverage"]["missing_scenarios"])

    def test_document_reports_verified_and_missing_scenarios(self):
        results = {
            "schema_version": 1,
            "status": "in_progress",
            "scenarios": [
                {
                    "number": 28,
                    "endpoint": "turn_2_command",
                    "opening_confirmations": 13,
                    "phase_dialogue_confirmations": 3,
                    "emulator_speed_percent": 100,
                    "elapsed_seconds": 194.6,
                }
            ],
            "coverage": {
                "verified_scenarios": [28],
                "missing_scenarios": [1, 2],
            },
        }
        document = first_turn.render_document(results)
        self.assertIn("Verified: 1/31", document)
        self.assertIn(
            "| 28 | `turn_2_command` | 13 | 3 | 100% | 194.6s |",
            document,
        )
        self.assertIn("Missing scenarios: 1, 2", document)

    def test_document_names_custom_results_manifest(self):
        source = (
            first_turn.ROOT
            / "localization/hard_mode_current_candidate_first_turn.json"
        )
        document = first_turn.render_document(
            {"coverage": {}},
            source=source,
        )
        self.assertIn(
            "`localization/hard_mode_current_candidate_first_turn.json`",
            document,
        )

    def test_current_candidate_scenarios_use_checksum_isolated_evidence(self):
        manifest = (
            first_turn.ROOT
            / "localization/hard_mode_current_candidate_first_turn.json"
        )
        data = json.loads(manifest.read_text(encoding="utf-8"))
        by_number = {
            int(row["number"]): row for row in data["scenarios"]
        }
        prefix = "hard_fbe2_first_turn_"
        self.assertEqual(
            sorted(by_number),
            data["coverage"]["verified_scenarios"],
        )
        retained_paths = [
            first_turn.ROOT / row[path_key]
            for row in by_number.values()
            for path_key in (
                "opening_capture",
                "endpoint_capture",
                "endpoint_gst",
            )
        ]
        if not all(path.is_file() for path in retained_paths):
            self.skipTest("ignored legacy first-turn captures are absent")
        for number, row in sorted(by_number.items()):
            for path_key, digest_key in (
                ("opening_capture", "opening_capture_sha256"),
                ("endpoint_capture", "endpoint_capture_sha256"),
                ("endpoint_gst", "endpoint_gst_sha256"),
            ):
                with self.subTest(number=number, path_key=path_key):
                    path = first_turn.ROOT / row[path_key]
                    self.assertTrue(path.name.startswith(prefix))
                    self.assertEqual(
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                        row[digest_key],
                    )


if __name__ == "__main__":
    unittest.main()
