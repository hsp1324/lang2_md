from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario14_15_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario1415CurrentResultSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verifier.build_report()

    def test_report_passes_without_promoting_release_or_acceptance(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])
        self.assertFalse(self.report["acceptance_updated"])

    def test_checked_report_is_current(self):
        subprocess.check_call(
            [
                sys.executable,
                str(
                    ROOT
                    / "tools/verify_scenario14_15_current_result_surface.py"
                ),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_both_profiles_have_exact_probe_lineage(self):
        for profile in ("normal", "hard"):
            for scenario in ("14", "15"):
                row = self.report["profiles"][profile]["scenarios"][scenario]
                lineage = row["diagnostic_lineage"]
                self.assertEqual(row["status"], "pass")
                self.assertTrue(lineage["candidate_identity_matches"])
                self.assertTrue(lineage["candidate"]["checksum_valid"])
                self.assertTrue(lineage["probe"]["checksum_valid"])
                self.assertTrue(lineage["event_triggers_preserved"])
                if profile == "normal":
                    self.assertTrue(lineage["exact_builder_rebuild"])
                else:
                    self.assertTrue(lineage["exact_three_way_overlay"])

    def test_real_scenarios_and_completion_moves_are_bound(self):
        expected_moves = {"14": "up", "15": "down"}
        for profile in ("normal", "hard"):
            for scenario, move in expected_moves.items():
                runtime = self.report["profiles"][profile]["scenarios"][
                    scenario
                ]["runtime"]
                identity = runtime["scenario_identity"]
                self.assertEqual(identity["status"], "pass")
                self.assertEqual(identity["requested_scenario"], int(scenario))
                self.assertEqual(identity["identified_scenario"], int(scenario))
                self.assertEqual(runtime["completion_move"], move)
                self.assertTrue(all(runtime["evidence"]["integrity"].values()))

    def test_reviewed_dynamic_text_and_rosters_are_present(self):
        expected = {
            "레온",
            "쉐리",
            "엘윈",
            "스코트의",
            "클래스체인지 가능",
        }
        observed = set()
        for profile in ("normal", "hard"):
            for scenario in ("14", "15"):
                runtime = self.report["profiles"][profile]["scenarios"][
                    scenario
                ]["runtime"]
                for row in runtime["critical_surfaces"].values():
                    self.assertEqual(row["manual_review"], "pass")
                    self.assertTrue(row["reviewed_hash_matches"])
                    self.assertEqual(row["observed_sprite_state"], "clean")
                    observed.update(row["observed_text"])
                self.assertEqual(runtime["observed_result_sprites"], "clean")
        self.assertTrue(expected <= observed)
        scenario15_roster = self.report["profiles"]["normal"]["scenarios"][
            "15"
        ]["runtime"]["observed_result_roster"]
        self.assertIn("스코트", scenario15_roster)
        self.assertIn("2300P", scenario15_roster)

    def test_sequences_and_result_headers_are_intact(self):
        expected_frames = {"14": 32, "15": 71}
        for profile in ("normal", "hard"):
            for scenario, frame_count in expected_frames.items():
                runtime = self.report["profiles"][profile]["scenarios"][
                    scenario
                ]["runtime"]
                self.assertEqual(runtime["sequence"]["frame_count"], frame_count)
                self.assertTrue(runtime["sequence"]["all_evidence_hashes_match"])
                self.assertEqual(
                    runtime["battle_result"]["surface"], "battle_result"
                )
                self.assertTrue(runtime["result_hash_matches"])
                self.assertTrue(runtime["result_alias_matches"])
                self.assertTrue(runtime["header_vram_matches_expected"])
                self.assertTrue(runtime["all_header_plane_cells_match"])

    def test_normal_and_hard_results_match_after_reviewed_timing_differences(self):
        for row in self.report["cross_profile"].values():
            self.assertTrue(row["battle_result_frame_identical"])
            self.assertTrue(row["result_header_vram_identical"])
            self.assertTrue(row["sequence_mismatches_match_review"])
            self.assertEqual(row["manual_mismatch_review"], "pass")

    def test_failed_first_capture_method_stays_rejected(self):
        rejected = self.report["rejected_first_attempt"]
        self.assertEqual(rejected["status"], "rejected")
        self.assertTrue(rejected["three_runs_ended_at_save_menu"])
        self.assertTrue(rejected["one_result_was_retained"])
        self.assertFalse(rejected["acceptance_updated"])


if __name__ == "__main__":
    unittest.main()
