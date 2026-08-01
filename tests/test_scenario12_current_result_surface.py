from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario12_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario12CurrentResultSurfaceTests(unittest.TestCase):
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
                str(ROOT / "tools/verify_scenario12_current_result_surface.py"),
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

    def test_both_profiles_reach_result_save_route_and_title(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["sequence"]["frame_count"], 27)
            self.assertTrue(runtime["sequence"]["all_dimensions_320x240"])
            self.assertEqual(runtime["battle_result"]["surface"], "battle_result")
            self.assertEqual(runtime["save_menu"]["surface"], "save_menu")
            self.assertEqual(runtime["battle_result"]["manual_review"], "pass")
            self.assertEqual(runtime["scenario13_route"]["manual_review"], "pass")
            self.assertEqual(runtime["scenario13_title"]["manual_review"], "pass")

    def test_dynamic_names_and_result_roster_are_hash_locked(self):
        expected = {"엘윈", "제시카", "아론", "헤인"}
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            observed = {
                text
                for row in runtime["critical_surfaces"].values()
                for text in row["observed_text"]
            }
            roster = set(runtime["battle_result"]["observed_text"])
            self.assertTrue(expected <= observed | roster)
            self.assertIn("쉐리", roster)
            self.assertIn("레스터", roster)
            self.assertTrue(
                all(
                    row["reviewed_hash_matches"]
                    for row in runtime["critical_surfaces"].values()
                )
            )

    def test_hard_profile_requires_the_observed_second_attack(self):
        hard = self.report["profiles"]["hard"]["runtime"]["last_living_armor"]
        self.assertIn("HP1", hard["first_attack_hp1"]["observed_text"])
        self.assertIn("HP0", hard["second_attack_hp0"]["observed_text"])
        self.assertTrue(hard["first_attack_hp1"]["reviewed_hash_matches"])
        self.assertTrue(hard["second_attack_hp0"]["reviewed_hash_matches"])

    def test_final_result_is_identical_across_profiles(self):
        cross = self.report["cross_profile"]
        self.assertTrue(cross["battle_result_frame_identical"])
        self.assertTrue(cross["result_header_roster_and_points_identical"])
        self.assertEqual(cross["manual_difference_review"], "pass")


if __name__ == "__main__":
    unittest.main()
