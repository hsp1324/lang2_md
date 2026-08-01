from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario17_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario17CurrentResultSurfaceTests(unittest.TestCase):
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
                str(ROOT / "tools/verify_scenario17_current_result_surface.py"),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_both_profiles_use_exact_current_candidate_lineage(self):
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
            self.assertEqual(lineage["diagnostic_changed_byte_count"], 129)
        self.assertEqual(
            self.report["profiles"]["normal"]["diagnostic_lineage"]
            ["hard_bytes_replaced_inside_diagnostic_envelope"],
            0,
        )
        self.assertEqual(
            self.report["profiles"]["hard"]["diagnostic_lineage"]
            ["hard_bytes_replaced_inside_diagnostic_envelope"],
            44,
        )

    def test_runtime_sequence_stays_in_stock_hp_range(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["status"], "pass")
            self.assertTrue(runtime["state_sequence_valid"])
            gsts = runtime["gsts"]
            first = gsts["first_start"]["runtime"]
            turn1 = gsts["turn1_return"]["runtime"]
            restored = gsts["post_start"]["runtime"]
            turn2 = gsts["turn2_command"]["runtime"]
            self.assertEqual(first["elwin_at"], 5)
            self.assertEqual(first["bernhardt_hp"], 10)
            self.assertEqual(turn1["elwin_acted"], 1)
            self.assertLess(turn1["bernhardt_hp"], 10)
            self.assertGreater(turn1["bernhardt_hp"], 0)
            self.assertEqual(restored["elwin_at"], 23)
            self.assertEqual(turn2["elwin_acted"], 0)
            self.assertEqual(turn2["elwin_at"], 23)
            self.assertLessEqual(turn2["bernhardt_hp"], 10)
            self.assertTrue(all(row["hash_matches"] for row in gsts.values()))

    def test_result_and_save_surfaces_are_hash_locked(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertTrue(runtime["evidence_json"]["hash_matches"])
            images = runtime["images"]
            self.assertTrue(all(row["hash_matches"] for row in images.values()))
            self.assertTrue(
                all(row["dimensions"] == [320, 240] for row in images.values())
            )
            self.assertEqual(images["battle_result"]["surface"], "battle_result")
            self.assertEqual(images["save_menu"]["surface"], "save_menu")

    def test_dynamic_result_names_are_manually_reviewed(self):
        for profile in ("normal", "hard"):
            review = self.report["profiles"][profile]["runtime"]["manual_review"]
            self.assertEqual(review["status"], "pass")
            self.assertFalse(review["broken_dynamic_glyphs_or_sprites"])
            for expected in (
                "전과보고",
                "키스",
                "레스터",
                "제시카",
                "스코트",
                "POINT 4200P",
            ):
                self.assertIn(expected, review["battle_result_text"])

    def test_cross_profile_differences_are_explicit(self):
        cross = self.report["cross_profile"]
        self.assertTrue(cross["preparation_pixel_identical"])
        self.assertTrue(cross["turn1_command_pixel_identical"])
        self.assertTrue(cross["save_menu_pixel_identical"])
        self.assertTrue(cross["result_manual_content_identical"])
        self.assertTrue(cross["result_frames_have_different_animation_phase"])

    def test_rejected_attempts_remain_documented(self):
        attempts = self.report["rejected_attempts"]
        self.assertEqual(len(attempts), 10)
        rendered = " ".join(
            f"{row['attempt']} {row['result']} {row['classification']}"
            for row in attempts
        )
        for expected in (
            "HP19",
            "froze",
            "transient post-battle map",
            "regeneration",
            "fixed two-attack assumption",
        ):
            self.assertIn(expected, rendered)

    def test_player_migration_policy_uses_srm(self):
        policy = self.report["savestate_policy"]
        self.assertIn("in-game SRM load", policy)
        self.assertIn("fresh savestate", policy)


if __name__ == "__main__":
    unittest.main()
