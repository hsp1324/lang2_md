from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_scenario16_current_result_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario16CurrentResultSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verifier.build_report()

    def test_report_passes_without_promoting_release(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])

    def test_checked_report_is_current(self):
        subprocess.check_call(
            [
                sys.executable,
                str(ROOT / "tools/verify_scenario16_current_result_surface.py"),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_both_diagnostic_lineages_are_exact(self):
        normal = self.report["profiles"]["normal"]["diagnostic_lineage"]
        hard = self.report["profiles"]["hard"]["diagnostic_lineage"]
        self.assertTrue(normal["exact_builder_rebuild"])
        self.assertTrue(hard["exact_three_way_overlay"])
        self.assertTrue(normal["event_triggers_preserved"])
        self.assertTrue(hard["event_triggers_preserved"])
        self.assertTrue(normal["probe"]["checksum_valid"])
        self.assertTrue(hard["probe"]["checksum_valid"])

    def test_dynamic_names_and_class_choice_were_reviewed(self):
        expected = {
            "키스",
            "레스터",
            "제시카",
            "스코트",
            "쉐리",
            "클래스체인지",
            "파이크",
        }
        for profile in ("normal", "hard"):
            surfaces = self.report["profiles"][profile]["runtime"][
                "critical_surfaces"
            ]
            observed = {
                text
                for row in surfaces.values()
                for text in row["observed_text"]
            }
            self.assertEqual(
                {row["manual_review"] for row in surfaces.values()},
                {"pass"},
            )
            self.assertTrue(expected <= observed)

    def test_both_result_headers_are_intact_and_identical(self):
        for profile in ("normal", "hard"):
            runtime = self.report["profiles"][profile]["runtime"]
            self.assertEqual(runtime["sequence"]["frame_count"], 27)
            self.assertTrue(runtime["battle_result"]["result_frame_detected"])
            self.assertTrue(runtime["all_header_plane_cells_match"])
        self.assertTrue(
            self.report["cross_profile"]["battle_result_frame_identical"]
        )
        self.assertTrue(
            self.report["cross_profile"]["result_header_vram_identical"]
        )


if __name__ == "__main__":
    unittest.main()
