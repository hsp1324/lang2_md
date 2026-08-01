from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario18_20_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario18To20CurrentResultSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verifier.build_report()

    def test_report_passes_without_release_or_acceptance_promotion(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])
        self.assertFalse(self.report["acceptance_updated"])

    def test_checked_report_is_current(self):
        subprocess.check_call(
            [
                sys.executable,
                str(
                    ROOT
                    / "tools/verify_scenario18_20_current_result_surface.py"
                ),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_all_scenarios_and_profiles_use_exact_current_lineage(self):
        for scenario in ("18", "19", "20"):
            row = self.report["scenarios"][scenario]
            self.assertEqual(row["status"], "pass")
            for profile in ("normal", "hard"):
                result = row["profiles"][profile]
                lineage = result["diagnostic_lineage"]
                self.assertEqual(result["status"], "pass")
                self.assertTrue(lineage["candidate_identity_matches"])
                self.assertTrue(lineage["probe_identity_matches"])
                self.assertTrue(lineage["candidate"]["checksum_valid"])
                self.assertTrue(lineage["probe"]["checksum_valid"])
                self.assertTrue(lineage["exact_rebuild"])

    def test_scenario19_hard_state_changes_only_imelda_current_hp(self):
        state = self.report["scenarios"]["19"]["source_state"]
        self.assertTrue(state["identity_matches"])
        hard = state["hard_diagnostic"]
        self.assertTrue(hard["identity_matches"])
        self.assertTrue(hard["exact_one_byte_hp_edit"])
        self.assertEqual(hard["exact_changed_offsets"], ["0x8877"])
        self.assertIn("10 -> 1", hard["edit"])

    def test_every_profile_reaches_result_and_save_surfaces(self):
        for scenario in ("18", "19", "20"):
            for profile in ("normal", "hard"):
                runtime = self.report["scenarios"][scenario]["profiles"][
                    profile
                ]["runtime"]
                self.assertEqual(runtime["status"], "pass")
                self.assertEqual(
                    runtime["battle_result"]["surface"], "battle_result"
                )
                self.assertEqual(runtime["save_menu"]["surface"], "save_menu")
                for row in runtime["evidence"].values():
                    self.assertEqual(row["dimensions"], [320, 240])
                    self.assertTrue(row["reviewed_hash_matches"])
                    self.assertTrue(row["surface_matches"])
                    self.assertEqual(row["manual_review"], "pass")
                    self.assertEqual(row["observed_sprite_state"], "clean")

    def test_key_dynamic_names_are_hash_locked(self):
        observed = set()
        for scenario in ("18", "19", "20"):
            for profile in ("normal", "hard"):
                evidence = self.report["scenarios"][scenario]["profiles"][
                    profile
                ]["runtime"]["evidence"]
                for row in evidence.values():
                    observed.update(row["observed_text"])
        for expected in (
            "그레이트드래곤",
            "스코트",
            "엘윈",
            "이멜다",
            "아론의",
            "파이어스",
            "제시카",
            "키스",
            "클래스체인지",
            "전과보고",
        ):
            self.assertIn(expected, observed)

    def test_cross_profile_differences_are_not_hidden(self):
        cross = self.report["cross_profile"]
        self.assertTrue(cross["scenario18_result_pixel_identical"])
        self.assertTrue(cross["all_save_menu_frames_pixel_identical"])
        self.assertTrue(
            cross["scenario19_and_20_point_totals_intentionally_differ"]
        )
        self.assertEqual(cross["manual_roster_and_sprite_review"], "pass")

    def test_rejected_scenario19_attempts_remain_documented(self):
        attempts = self.report["rejected_attempts"]
        self.assertEqual(len(attempts), 4)
        rendered = " ".join(
            f"{row['attempt']} {row['result']} {row['classification']}"
            for row in attempts
        )
        self.assertIn("HP1", rendered)
        self.assertIn("GAME OVER", rendered)
        self.assertIn("A2BC", rendered)
        self.assertIn("removed", rendered)

    def test_player_migration_policy_uses_srm_not_old_savestates(self):
        policy = self.report["savestate_policy"]
        self.assertIn("in-game SRM load", policy)
        self.assertIn("fresh savestate", policy)


if __name__ == "__main__":
    unittest.main()
