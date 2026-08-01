from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario21_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario21CurrentResultSurfaceTests(unittest.TestCase):
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
                str(ROOT / "tools/verify_scenario21_current_result_surface.py"),
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
            self.assertEqual(lineage["diagnostic_changed_byte_count"], 185)
            self.assertEqual(
                lineage["hard_bytes_replaced_inside_diagnostic_envelope"], 0
            )

    def test_runtime_wrapper_defeats_only_hostiles_and_preserves_lana(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertTrue(runtime["hostile_state_valid"])
            state = runtime["runtime_clear_state"]
            self.assertTrue(state["hostiles_defeated"])
            self.assertTrue(state["lana_untouched_by_wrapper"])
            lana = state["groups"][str(verifier.probe_builder.LANA_RUNTIME_GROUP)]
            self.assertEqual(lana["class_id"], 0x60)
            self.assertEqual(lana["name_id"], 0x0C)
            self.assertEqual(lana["hp"], 10)
            self.assertEqual(lana["defeated_flag"], 0)

    def test_result_and_save_surfaces_are_hash_locked(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["status"], "pass")
            self.assertTrue(runtime["evidence_json"]["hash_matches"])
            self.assertEqual(runtime["battle_result_frame"], 36)
            self.assertEqual(runtime["save_menu_frame"], 3)
            self.assertTrue(
                all(row["hash_matches"] for row in runtime["images"].values())
            )
            self.assertTrue(
                all(row["dimensions"] == [320, 240]
                    for row in runtime["images"].values())
            )
            self.assertTrue(
                all(row["hash_matches"] for row in runtime["gsts"].values())
            )
            self.assertEqual(
                runtime["images"]["battle_result"]["surface"],
                "battle_result",
            )
            self.assertEqual(
                runtime["images"]["save_menu"]["surface"], "save_menu"
            )

    def test_aftermath_and_result_text_are_manually_reviewed(self):
        expected_names = {
            "리빙아머",
            "서큐버스",
            "리치",
            "크라켄",
            "제국군지휘관",
            "헤인",
            "엘윈",
            "제시카",
            "쉐리",
            "아론",
            "키스",
            "레스터",
            "스코트",
        }
        for profile in ("normal", "hard"):
            review = self.report["profiles"][profile]["runtime"]["manual_review"]
            self.assertEqual(review["status"], "pass")
            self.assertEqual(review["reviewed_aftermath_frames"], 36)
            self.assertFalse(review["broken_dynamic_glyphs_or_sprites"])
            self.assertEqual(set(review["dialogue_names"]), expected_names)
            for expected in (
                "전과보고",
                "아군",
                "엘윈",
                "헤인",
                "쉐리",
                "아론",
                "키스",
                "레스터",
                "제시카",
                "스코트",
                "POINT 31100P",
            ):
                self.assertIn(expected, review["battle_result_text"])
            self.assertIn("not a duplicate 아론", review["clarification"])

    def test_cross_profile_relationships_are_explicit(self):
        cross = self.report["cross_profile"]
        self.assertTrue(cross["preparation_pixel_identical"])
        self.assertTrue(cross["turn1_command_pixel_identical"])
        self.assertTrue(cross["runtime_clear_start_pixel_identical"])
        self.assertTrue(cross["aftermath_frames_1_through_35_pixel_identical"])
        self.assertTrue(cross["save_menu_pixel_identical"])
        self.assertTrue(cross["result_manual_content_identical"])
        self.assertTrue(cross["result_frames_have_different_animation_phase"])

    def test_rejected_attempts_and_srm_policy_remain_documented(self):
        attempts = self.report["rejected_attempts"]
        self.assertEqual(len(attempts), 3)
        rendered = " ".join(
            f"{row['attempt']} {row['result']} {row['classification']}"
            for row in attempts
        )
        for expected in (
            "cross-build savestate",
            "Japanese-specific",
            "아군",
        ):
            if expected == "Japanese-specific":
                self.assertIn("Korean-specific", rendered)
            else:
                self.assertIn(expected, rendered)
        policy = self.report["savestate_policy"]
        self.assertIn("in-game SRM load", policy)
        self.assertIn("fresh savestate", policy)


if __name__ == "__main__":
    unittest.main()
