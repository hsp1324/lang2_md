import json
import tempfile
import unittest
from pathlib import Path

from tools import verify_hard_mode_first_turn as first_turn


class HardModeFirstTurnTests(unittest.TestCase):
    def test_entry_evidence_uses_loader_and_deep_manifests(self):
        self.assertEqual(first_turn.entry_evidence(2)["kind"], "loader_smoke")
        self.assertEqual(first_turn.entry_evidence(1)["kind"], "loader_smoke")
        self.assertTrue(first_turn.entry_evidence(1)["hash_locked"])

    def test_retained_entry_hashes_match_manifests(self):
        for number in (1, 2, 16, 25, 27):
            evidence = first_turn.entry_evidence(number)
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
        source = first_turn.entry_evidence(31)
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

    def test_turn_counter_reads_work_ram_byte(self):
        data = bytearray(first_turn.TURN_COUNTER_FILE_OFFSET + 1)
        data[first_turn.TURN_COUNTER_FILE_OFFSET] = 2
        self.assertEqual(first_turn.turn_counter(bytes(data)), 2)

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

    def test_endpoint_classification_requires_turn_two_command(self):
        self.assertEqual(
            first_turn.classify_endpoint("turn_command", 2),
            "turn_2_command",
        )
        with self.assertRaises(ValueError):
            first_turn.classify_endpoint("turn_command", 1)
        self.assertEqual(
            first_turn.classify_endpoint("game_over", 1),
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
        self.assertIsNone(first_turn.expected_endpoint(12))
        self.assertIsNone(first_turn.expected_endpoint(14))

    def test_save_result_replaces_scenario_and_updates_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            results = {
                "schema_version": 1,
                "status": "in_progress",
                "hard_rom": {},
                "scenarios": [
                    {
                        "number": 2,
                        "status": "first_turn_runtime_verified",
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


if __name__ == "__main__":
    unittest.main()
