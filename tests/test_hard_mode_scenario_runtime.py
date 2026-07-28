import json
import tempfile
import unittest
from pathlib import Path

from tools import verify_hard_mode_scenario_runtime as scenario_runtime


class HardModeScenarioRuntimeTests(unittest.TestCase):
    def test_matching_player_group_count_finds_retained_scenario_sixteen(self):
        gst = scenario_runtime.runtime_evidence.SCENARIO_SIXTEEN_GST.read_bytes()
        self.assertEqual(
            scenario_runtime.matching_player_group_count(gst, 16),
            8,
        )

    def test_matching_player_group_count_rejects_unrelated_scenario(self):
        gst = scenario_runtime.runtime_evidence.SCENARIO_SIXTEEN_GST.read_bytes()
        with self.assertRaises(RuntimeError):
            scenario_runtime.matching_player_group_count(gst, 25)

    def test_save_result_replaces_one_scenario_and_sorts_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            results = {
                "schema_version": 1,
                "status": "in_progress",
                "hard_rom": {},
                "scenarios": [
                    {"number": 16, "status": "old"},
                    {"number": 2, "status": "kept"},
                ],
            }
            scenario_runtime.save_result(
                path,
                results,
                {"number": 16, "status": "new"},
            )
            self.assertEqual(
                [(row["number"], row["status"]) for row in results["scenarios"]],
                [(2, "kept"), (16, "new")],
            )
            self.assertEqual(
                [(row["number"], row["status"]) for row in json.loads(
                    path.read_text(encoding="utf-8")
                )["scenarios"]],
                [(2, "kept"), (16, "new")],
            )

    def test_seed_selection_uses_late_progress_only_from_scenario_twenty_five(self):
        self.assertEqual(
            scenario_runtime.seed_for_scenario(24),
            scenario_runtime.MIDGAME_SEED,
        )
        self.assertEqual(
            scenario_runtime.seed_for_scenario(25),
            scenario_runtime.LATEGAME_SEED,
        )


if __name__ == "__main__":
    unittest.main()
