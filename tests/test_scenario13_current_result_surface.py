from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario13_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario13CurrentResultSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verifier.build_report()

    def test_report_passes_without_promoting_release_or_full_acceptance(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])
        self.assertFalse(self.report["acceptance_updated"])

    def test_checked_report_is_current(self):
        subprocess.check_call(
            [
                sys.executable,
                str(ROOT / "tools/verify_scenario13_current_result_surface.py"),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_both_probe_lineages_are_exact_and_event_safe(self):
        for profile in ("normal", "hard"):
            lineage = self.report["profiles"][profile]["diagnostic_lineage"]
            self.assertTrue(lineage["candidate_identity_matches"])
            self.assertTrue(lineage["probe_identity_matches"])
            self.assertTrue(lineage["candidate"]["checksum_valid"])
            self.assertTrue(lineage["probe"]["checksum_valid"])
            self.assertTrue(lineage["complete_event_block_preserved"])
            self.assertTrue(lineage["inline_start_trampoline_installed"])
        self.assertTrue(
            self.report["profiles"]["normal"]["diagnostic_lineage"][
                "exact_builder_rebuild"
            ]
        )
        self.assertTrue(
            self.report["profiles"]["hard"]["diagnostic_lineage"][
                "exact_three_way_overlay"
            ]
        )

    def test_both_profiles_reach_clean_result_save_route_and_title(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["sequence"]["frame_count"], 48)
            self.assertTrue(runtime["sequence"]["all_dimensions_320x240"])
            self.assertEqual(runtime["battle_result"]["surface"], "battle_result")
            self.assertEqual(runtime["save_menu_before_write"]["surface"], "save_menu")
            self.assertEqual(runtime["scenario14_save_written"]["surface"], "save_menu")
            self.assertEqual(runtime["battle_result"]["manual_review"], "pass")
            self.assertEqual(runtime["scenario14_route"]["manual_review"], "pass")
            self.assertEqual(runtime["scenario14_title"]["manual_review"], "pass")
            self.assertTrue(
                all(
                    row["reviewed_hash_matches"]
                    for row in runtime["critical_surfaces"].values()
                )
            )

    def test_dynamic_dialogue_names_and_result_rosters_were_reviewed(self):
        expected_names = {"발가스", "레온", "아론", "엘윈", "키스", "제시카"}
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            observed = {
                text
                for row in runtime["critical_surfaces"].values()
                for text in row["observed_text"]
            }
            roster = set(runtime["battle_result"]["observed_roster"])
            self.assertTrue(expected_names <= observed | roster)
            self.assertIn("전과보고", roster)
            self.assertIn("쉐리", roster)
            self.assertIn("레스터", roster)
            self.assertIn("제시카", roster)

    def test_cross_profile_difference_is_only_the_points_digit(self):
        cross = self.report["cross_profile"]
        self.assertFalse(cross["battle_result_frame_identical"])
        self.assertTrue(cross["difference_is_points_digit_only"])
        self.assertTrue(cross["result_header_and_roster_top_identical"])
        self.assertEqual(cross["manual_difference_review"], "pass")

    def test_failed_paths_remain_explicitly_rejected(self):
        rejected = self.report["rejected_attempts"]
        self.assertEqual(rejected["status"], "rejected")
        self.assertFalse(rejected["acceptance_updated"])
        for row in rejected["attempts"].values():
            self.assertTrue(row["hash_matches"])
            self.assertFalse(row["accepted"])


if __name__ == "__main__":
    unittest.main()
