from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario22_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario22CurrentResultSurfaceTests(unittest.TestCase):
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
                str(ROOT / "tools/verify_scenario22_current_result_surface.py"),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_both_profiles_use_exact_source_preserving_lineage(self):
        for profile in ("normal", "hard"):
            row = self.report["profiles"][profile]
            lineage = row["diagnostic_lineage"]
            self.assertEqual(row["status"], "pass")
            self.assertTrue(lineage["candidate_identity_matches"])
            self.assertTrue(lineage["probe_identity_matches"])
            self.assertTrue(lineage["candidate"]["checksum_valid"])
            self.assertTrue(lineage["probe"]["checksum_valid"])
            self.assertTrue(lineage["exact_rebuild"])
            self.assertTrue(lineage["wrapper_exact"])
            self.assertTrue(lineage["start_entry_targets_wrapper"])
            self.assertTrue(lineage["fixed_records_input_exact"])
            self.assertTrue(lineage["normal_fixed_records_source_exact"])
            self.assertTrue(lineage["player_deployments_input_exact"])
            self.assertTrue(lineage["normal_player_deployments_source_exact"])
            self.assertEqual(lineage["diagnostic_changed_byte_count"], 202)
            self.assertEqual(
                lineage["hard_bytes_replaced_inside_diagnostic_envelope"], 0
            )

    def test_runtime_wrapper_defeats_only_combat_groups_and_preserves_liana(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertTrue(runtime["combat_state_valid"])
            state = runtime["runtime_clear_state"]
            self.assertTrue(state["combat_groups_defeated"])
            self.assertTrue(state["liana_untouched_by_wrapper"])
            self.assertTrue(state["liana_runtime_identity_valid"])
            liana = state["groups"][str(verifier.runner.LIANA_RUNTIME_GROUP)]
            self.assertEqual(liana, state["groups_before_start"]["8"])
            self.assertEqual(liana["class_id"], 0x02)
            self.assertEqual(liana["name_id"], 0x02)
            self.assertEqual(liana["hp"], 10)
            self.assertEqual(liana["defeated_flag"], 0)

    def test_every_aftermath_frame_and_key_surface_is_hash_locked(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["status"], "pass")
            self.assertTrue(runtime["evidence_json"]["hash_matches"])
            self.assertEqual(runtime["battle_result_frame"], 167)
            self.assertEqual(runtime["aftermath"]["frame_count"], 167)
            self.assertEqual(runtime["aftermath"]["unique_frame_hashes"], 158)
            self.assertTrue(runtime["aftermath"]["sequence_hash_matches"])
            self.assertTrue(runtime["aftermath"]["total_bytes_match"])
            self.assertTrue(runtime["aftermath"]["all_dimensions_320x240"])
            self.assertTrue(
                all(row["hash_matches"] for row in runtime["images"].values())
            )
            self.assertTrue(
                all(row["hash_matches"] for row in runtime["gsts"].values())
            )
            self.assertEqual(
                runtime["images"]["battle_result"]["surface"],
                "battle_result",
            )
            self.assertEqual(runtime["images"]["save_menu"]["surface"], "save_menu")

    def test_result_and_all_aftermath_text_are_manually_reviewed(self):
        expected_names = {
            "보젤", "라나", "베른하르트", "제국군지휘관", "리치",
            "아이언골렘", "제시카", "쉐리", "레스터", "헤인",
            "엘윈", "리아나", "아론", "스코트",
        }
        for profile in ("normal", "hard"):
            review = self.report["profiles"][profile]["runtime"]["manual_review"]
            self.assertEqual(review["status"], "pass")
            self.assertEqual(review["reviewed_normal_aftermath_frames"], 167)
            self.assertEqual(review["reviewed_hard_differing_frames"], 23)
            self.assertFalse(review["broken_dynamic_glyphs_or_sprites"])
            self.assertEqual(set(review["dialogue_names"]), expected_names)
            for expected in (
                "전과보고", "아군", "엘윈", "헤인", "쉐리", "아론",
                "키스", "레스터", "제시카", "스코트", "POINT 4480P",
            ):
                self.assertIn(expected, review["battle_result_text"])

    def test_cross_profile_differences_are_bounded_and_reviewed(self):
        cross = self.report["cross_profile"]
        self.assertTrue(cross["preparation_pixel_identical"])
        self.assertTrue(cross["turn1_command_pixel_identical"])
        self.assertTrue(cross["runtime_clear_start_pixel_identical"])
        self.assertEqual(cross["aftermath_pixel_identical_frames"], 144)
        self.assertEqual(
            cross["aftermath_differing_frames"],
            verifier.EXPECTED_CROSS_PROFILE_DIFFERENCES,
        )
        self.assertTrue(cross["aftermath_differences_match_reviewed_set"])
        self.assertIn("no name", cross["differing_frames_manual_classification"])
        self.assertTrue(cross["save_menu_pixel_identical"])
        self.assertTrue(cross["result_manual_content_identical"])

    def test_failed_assertion_and_savestate_policy_remain_documented(self):
        attempts = self.report["rejected_attempts"]
        self.assertEqual(len(attempts), 1)
        rendered = " ".join(
            f"{row['attempt']} {row['result']} {row['classification']}"
            for row in attempts
        )
        self.assertIn("class 97", rendered)
        self.assertIn("runtime Cleric class 02", rendered)
        self.assertIn("before and after Start", rendered)
        policy = self.report["savestate_policy"]
        self.assertIn("in-game SRM load", policy)
        self.assertIn("fresh savestate", policy)


if __name__ == "__main__":
    unittest.main()
