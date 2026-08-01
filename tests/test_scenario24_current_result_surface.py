from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario24_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario24CurrentResultSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verifier.build_report()

    def test_report_passes_without_release_or_acceptance_promotion(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])
        self.assertFalse(self.report["acceptance_updated"])

    def test_checked_report_is_current(self):
        subprocess.check_call(
            [sys.executable, str(ROOT / "tools/verify_scenario24_current_result_surface.py"), "--check"],
            cwd=ROOT,
        )

    def test_both_profiles_have_exact_source_preserving_lineage(self):
        for profile in ("normal", "hard"):
            lineage = self.report["profiles"][profile]["diagnostic_lineage"]
            for key in (
                "candidate_identity_matches", "probe_identity_matches",
                "exact_rebuild", "wrapper_exact", "start_entry_targets_wrapper",
                "fixed_records_input_exact", "normal_fixed_records_source_exact",
                "player_deployments_input_exact", "normal_player_deployments_source_exact",
            ):
                self.assertTrue(lineage[key], (profile, key))
            self.assertEqual(lineage["diagnostic_changed_byte_count"], 202)
            self.assertEqual(lineage["hard_bytes_replaced_inside_diagnostic_envelope"], 0)

    def test_runtime_wrapper_preserves_players_and_defeats_only_hostiles(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertTrue(runtime["combat_state_valid"])
            state = runtime["runtime_clear_state"]
            self.assertTrue(state["player_groups_untouched_by_wrapper"])
            self.assertTrue(state["hostile_groups_defeated"])
            for group in range(9):
                self.assertEqual(state["groups"][str(group)], state["groups_before_start"][str(group)])

    def test_all_runtime_artifacts_and_aftermath_frames_are_locked(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["status"], "pass")
            self.assertTrue(runtime["evidence_json"]["hash_matches"])
            self.assertEqual(runtime["scenario_identity"]["identified_scenario"], 24)
            self.assertEqual(runtime["scenario_identity"]["best_match"]["matched_records"], 11)
            self.assertEqual(runtime["battle_result_frame"], 42)
            self.assertEqual(runtime["aftermath"]["frame_count"], 42)
            self.assertEqual(runtime["aftermath"]["unique_frame_hashes"], 39)
            self.assertTrue(runtime["aftermath"]["sequence_hash_matches"])
            self.assertTrue(runtime["aftermath"]["total_bytes_match"])
            self.assertTrue(all(row["hash_matches"] for row in runtime["images"].values()))
            self.assertTrue(all(row["hash_matches"] for row in runtime["gsts"].values()))

    def test_manual_review_locks_names_result_roster_and_point_value(self):
        for profile in ("normal", "hard"):
            review = self.report["profiles"][profile]["runtime"]["manual_review"]
            self.assertEqual(review["status"], "pass")
            self.assertFalse(review["broken_dynamic_glyphs_or_sprites"])
            for expected in ("데몬로드", "케르베로스", "리치", "뱀파이어로드"):
                self.assertIn(expected, review["dialogue_and_level_names"])
            for expected in (
                "전과보고", "아군", "엘윈", "헤인", "쉐리", "아론",
                "키스", "레스터", "스코트", "리아나", "라나", "POINT 55900P",
            ):
                self.assertIn(expected, review["battle_result_text"])

    def test_cross_profile_difference_is_only_reviewed_animation(self):
        cross = self.report["cross_profile"]
        self.assertTrue(cross["preparation_pixel_identical"])
        self.assertTrue(cross["turn1_command_pixel_identical"])
        self.assertTrue(cross["runtime_clear_start_pixel_identical"])
        self.assertEqual(cross["aftermath_pixel_identical_frames"], 41)
        self.assertEqual(cross["aftermath_differing_frames"], [42])
        self.assertTrue(cross["aftermath_differences_match_reviewed_set"])
        self.assertIn("13 pixels", cross["differing_frames_manual_classification"])
        self.assertTrue(cross["save_menu_pixel_identical"])


if __name__ == "__main__":
    unittest.main()
