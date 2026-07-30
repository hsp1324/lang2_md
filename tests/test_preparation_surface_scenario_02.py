import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_surface_scenario_02.json"


class PreparationSurfaceScenario02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_checked_report_is_current(self) -> None:
        subprocess.check_call(
            [
                sys.executable,
                str(
                    ROOT
                    / "tools/verify_preparation_surface_scenario_02.py"
                ),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_both_profiles_have_all_exact_preparation_pairs(self) -> None:
        self.assertEqual(self.model["status"], "scenario_2_complete_pass")
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                run = self.model["profiles"][profile]
                self.assertEqual(run["status"], "scenario_2_surface_pass")
                self.assertEqual(run["actual_pair_count"], 18)
                self.assertEqual(run["expected_pair_count"], 18)
                self.assertEqual(
                    run["visible_fixed_record_indexes"], list(range(8))
                )
                self.assertEqual(
                    [
                        row["index"]
                        for row in run["not_applicable_fixed_records"]
                    ],
                    [8, 9],
                )
                self.assertTrue(
                    all(
                        row["byte_identical"]
                        for row in run["capture_pairs"]
                    )
                )

    def test_gray_acted_sprite_is_stock_fighter_on_plane_a(self) -> None:
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                gray = self.model["profiles"][profile]["battle_evidence"][
                    "gray_acted_sprite"
                ]
                self.assertEqual(gray["source_silhouette_id"], "0x001E")
                self.assertEqual(
                    gray["runtime_group_zero"]["class_id"], 1
                )
                self.assertEqual(
                    gray["runtime_group_zero"]["commander_id"], 1
                )
                self.assertEqual(
                    gray["runtime_group_zero"]["acted_flag"], 1
                )
                self.assertTrue(
                    gray["matches_stock_fighter_silhouette_expansion"]
                )
                self.assertTrue(
                    all(
                        row["hits"]
                        and all(
                            hit["plane"] == "plane_a"
                            for hit in row["hits"]
                        )
                        for row in gray["plane_references"]
                    )
                )

    def test_result_header_and_diagnostic_lineage_are_intact(self) -> None:
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                result = self.model["profiles"][profile]["battle_evidence"][
                    "battle_result"
                ]
                self.assertEqual(result["header_text"], "전과보고")
                self.assertTrue(
                    all(
                        cell["matches"]
                        for cell in result["header_plane_cells"]
                    )
                )
                lineage = result["diagnostic_lineage"]
                self.assertTrue(
                    lineage[
                        "changed_only_checksum_start_operand_and_wrapper"
                    ]
                )
                self.assertTrue(lineage["scenario_deployments_unchanged"])
                self.assertTrue(lineage["scenario_fixed_records_unchanged"])
                self.assertTrue(lineage["scenario_result_events_unchanged"])
                self.assertTrue(
                    lineage["korean_battle_result_header_unchanged"]
                )


if __name__ == "__main__":
    unittest.main()
