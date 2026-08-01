from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario10_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario10CurrentResultSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verifier.build_report()

    def test_report_passes(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])

    def test_checked_report_is_current(self):
        subprocess.check_call(
            [
                sys.executable,
                str(ROOT / "tools/verify_scenario10_current_result_surface.py"),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_both_profiles_preserve_candidate_lineage(self):
        for profile in ("normal", "hard"):
            row = self.report["profiles"][profile]
            self.assertEqual(row["status"], "pass")
            lineage = row["diagnostic_lineage"]
            self.assertTrue(
                lineage["changes_limited_to_checksum_operand_and_wrapper"]
            )
            self.assertTrue(lineage["scenario_fixed_records_identical"])
            self.assertTrue(lineage["checksum_valid"])

    def test_both_result_headers_are_intact_and_identical(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["header_text"], "전과보고")
            self.assertTrue(runtime["all_header_plane_cells_match"])
            self.assertTrue(
                runtime["battle_result"]["result_frame_detected"]
            )
        self.assertTrue(
            self.report["cross_profile"]["result_header_vram_identical"]
        )

    def test_reward_and_class_choice_were_reviewed(self):
        surfaces = self.report["supporting_surfaces"]
        self.assertEqual(surfaces["necklace_acquisition"]["manual_review"], "pass")
        self.assertEqual(surfaces["class_change_choice"]["manual_review"], "pass")
        self.assertIn(
            "넥클리스를 얻었다!",
            surfaces["necklace_acquisition"]["observed_text"],
        )
        self.assertIn(
            "클래스체인지",
            surfaces["class_change_choice"]["observed_text"],
        )


if __name__ == "__main__":
    unittest.main()
