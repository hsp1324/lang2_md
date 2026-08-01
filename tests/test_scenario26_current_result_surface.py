from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario26_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario26CurrentResultSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verifier.build_report()

    def test_report_passes_without_release_or_acceptance_promotion(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])
        self.assertFalse(self.report["acceptance_updated"])

    def test_checked_report_is_current(self):
        subprocess.check_call(
            [sys.executable, str(ROOT / "tools/verify_scenario26_current_result_surface.py"), "--check"],
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
            self.assertEqual(lineage["diagnostic_changed_byte_count"], 185)
            self.assertEqual(lineage["hard_bytes_replaced_inside_diagnostic_envelope"], 0)
            self.assertIn("groups 10..19", lineage["scope_limit"])

    def test_runtime_wrapper_preserves_all_players_and_defeats_only_hostiles(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertTrue(runtime["combat_state_valid"])
            state = runtime["runtime_clear_state"]
            self.assertTrue(state["player_groups_untouched_by_wrapper"])
            self.assertTrue(state["hostile_groups_defeated"])
            for group in range(10):
                self.assertEqual(state["groups"][str(group)], state["groups_before_start"][str(group)])
            for group in range(10, 20):
                self.assertEqual(state["groups"][str(group)]["hp"], 0)
                self.assertEqual(state["groups"][str(group)]["x"], 0xFF)

    def test_runtime_artifacts_and_all_aftermath_frames_are_locked(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["status"], "pass")
            self.assertTrue(runtime["evidence_json"]["hash_matches"])
            self.assertEqual(runtime["scenario_identity"]["identified_scenario"], 26)
            self.assertEqual(runtime["scenario_identity"]["best_match"]["matched_records"], 10)
            self.assertEqual(runtime["scenario_identity"]["best_match"]["total_records"], 10)
            self.assertEqual(runtime["battle_result_frame"], 42)
            self.assertEqual(runtime["aftermath"]["frame_count"], 42)
            self.assertEqual(runtime["aftermath"]["unique_frame_hashes"], 42)
            self.assertTrue(runtime["aftermath"]["sequence_hash_matches"])
            self.assertTrue(runtime["aftermath"]["total_bytes_match"])
            self.assertTrue(all(row["hash_matches"] for row in runtime["images"].values()))
            self.assertTrue(all(row["hash_matches"] for row in runtime["gsts"].values()))

    def test_corrected_particle_is_live_in_both_profiles(self):
        fix = self.report["dialogue_fix"]
        self.assertEqual(fix["status"], "pass")
        self.assertEqual(fix["old_tile_word"], "7089")
        self.assertEqual(fix["new_tile_word"], "7029")
        self.assertIn("보젤과 싸울", fix["expected_text"])
        self.assertIn("보젤와", fix["old_normal_run_rejected"])
        for profile in ("normal", "hard"):
            review = self.report["profiles"][profile]["runtime"]["manual_review"]
            self.assertIn("보젤과 싸울", review["corrected_dialogue"])
            self.assertFalse(review["broken_dynamic_glyphs_or_sprites"])

    def test_manual_review_locks_result_roster_and_point_value(self):
        for profile in ("normal", "hard"):
            review = self.report["profiles"][profile]["runtime"]["manual_review"]
            for expected in (
                "전과보고", "아군", "엘윈", "헤인", "쉐리", "아론",
                "키스", "레스터", "스코트", "리아나", "라나", "제시카",
                "POINT 4240P",
            ):
                self.assertIn(expected, review["battle_result_text"])

    def test_cross_profile_differences_are_reviewed_animation_only(self):
        cross = self.report["cross_profile"]
        self.assertTrue(cross["preparation_pixel_identical"])
        self.assertTrue(cross["turn1_command_pixel_identical"])
        self.assertTrue(cross["runtime_clear_start_pixel_identical"])
        self.assertEqual(cross["aftermath_pixel_identical_frames"], 39)
        self.assertEqual(cross["aftermath_differing_frames"], [32, 34, 42])
        self.assertTrue(cross["aftermath_differences_match_reviewed_set"])
        self.assertEqual(cross["differing_frame_bboxes"]["32"], [0, 49, 8, 65])
        self.assertEqual(cross["differing_frame_bboxes"]["34"], [280, 49, 296, 65])
        self.assertTrue(cross["save_menu_pixel_identical"])

    def test_selector_retry_is_recorded_without_gameplay_claim(self):
        notes = self.report["automation_notes"]
        self.assertIn("timed out", notes["normal_selector_attempt_1"])
        self.assertEqual(notes["normal_accepted_attempt"], 2)
        self.assertEqual(notes["hard_accepted_attempt"], 1)


if __name__ == "__main__":
    unittest.main()
