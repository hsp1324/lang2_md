import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tools import verify_hard_mode_scenario_runtime as scenario_runtime
from tools import verify_hard_mode_runtime_evidence as runtime_evidence


class HardModeScenarioRuntimeTests(unittest.TestCase):
    def test_retain_entry_gst_replaces_snapshot_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            original_root = scenario_runtime.RETAINED_ENTRY_ROOT
            try:
                scenario_runtime.RETAINED_ENTRY_ROOT = Path(directory)
                destination = scenario_runtime.retain_entry_gst(
                    4,
                    b"entry",
                )
                self.assertEqual(destination.read_bytes(), b"entry")
                self.assertFalse(destination.with_suffix(".gst.tmp").exists())
            finally:
                scenario_runtime.RETAINED_ENTRY_ROOT = original_root

    def test_evidence_prefix_separates_candidate_artifacts(self):
        calls = []
        original_argv = sys.argv
        try:
            sys.argv = [
                "verify_hard_mode_scenario_runtime.py",
                "--scenario",
                "3",
                "--scenario",
                "6",
                "--evidence-prefix",
                "hard_fbe2",
            ]
            with (
                mock.patch.object(
                    scenario_runtime,
                    "load_results",
                    return_value={
                        "schema_version": 1,
                        "status": "in_progress",
                        "hard_rom": {},
                        "scenarios": [],
                    },
                ),
                mock.patch.object(
                    scenario_runtime,
                    "verify_scenario",
                    side_effect=lambda number, **kwargs: calls.append(
                        (number, kwargs["runtime_name"], kwargs["evidence_tag"])
                    )
                    or {
                        "number": number,
                        "target_record_count": 1,
                        "runtime_group_range": [1, 1],
                    },
                ),
                mock.patch.object(scenario_runtime, "save_result"),
            ):
                self.assertEqual(scenario_runtime.main(), 0)
        finally:
            sys.argv = original_argv
        self.assertEqual(
            calls,
            [
                (3, "hard-fbe2-s03", "hard_fbe2_s03_entry"),
                (6, "hard-fbe2-s06", "hard_fbe2_s06_entry"),
            ],
        )

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
            self.assertEqual(results["status"], "in_progress")
            self.assertIn(1, results["coverage"]["verified_scenarios"])
            self.assertIn(3, results["coverage"]["missing_scenarios"])

    def test_seed_selection_avoids_future_roster_data_in_early_scenarios(self):
        with mock.patch.object(Path, "is_file", return_value=True):
            self.assertEqual(
                scenario_runtime.seed_for_scenario(10),
                scenario_runtime.EARLYGAME_SEED,
            )
            self.assertEqual(
                scenario_runtime.seed_for_scenario(11),
                scenario_runtime.MIDGAME_SEED,
            )
            self.assertEqual(
                scenario_runtime.seed_for_scenario(24),
                scenario_runtime.MIDGAME_SEED,
            )
            self.assertEqual(
                scenario_runtime.seed_for_scenario(25),
                scenario_runtime.LATEGAME_SEED,
            )

    def test_seed_selection_falls_back_when_historical_band_seed_was_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "removed-midgame.gst"
            with mock.patch.object(scenario_runtime, "MIDGAME_SEED", missing):
                self.assertEqual(
                    scenario_runtime.seed_for_scenario(11),
                    scenario_runtime.EARLYGAME_SEED,
                )
                self.assertEqual(
                    scenario_runtime.seed_for_scenario(24),
                    scenario_runtime.EARLYGAME_SEED,
                )

    def test_scenario_ten_lester_stock_roster_rewrite_is_explicit(self):
        gst = runtime_evidence.SCENARIO_TEN_GST.read_bytes()
        self.assertEqual(
            scenario_runtime.matching_player_group_count(gst, 10),
            5,
        )
        self.assertEqual(
            scenario_runtime.scenario_runtime_exception_indexes(10),
            [1],
        )

    def test_scenario_ten_exception_still_checks_identity(self):
        gst = bytearray(runtime_evidence.SCENARIO_TEN_GST.read_bytes())
        start = (
            runtime_evidence.GST_WORK_RAM_FILE_OFFSET
            + runtime_evidence.RUNTIME_GROUP_BASE
            + 6 * runtime_evidence.RUNTIME_GROUP_SIZE
        )
        gst[start] ^= 1
        with self.assertRaises(ValueError):
            runtime_evidence.verify_planned_scenario(bytes(gst), 10, 5)


if __name__ == "__main__":
    unittest.main()
