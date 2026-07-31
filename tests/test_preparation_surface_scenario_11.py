import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_surface_scenario_11.json"


class PreparationSurfaceScenario11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_checked_report_is_current(self) -> None:
        subprocess.check_call(
            [
                sys.executable,
                str(
                    ROOT
                    / "tools/verify_preparation_surface_scenario_11.py"
                ),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_every_allied_npc_and_enemy_record_is_accounted_for(self) -> None:
        self.assertEqual(self.model["status"], "scenario_11_complete_pass")
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                run = self.model["profiles"][profile]
                self.assertEqual(run["status"], "scenario_11_surface_pass")
                self.assertEqual(run["allied_commander_count"], 6)
                self.assertEqual(run["fixed_record_count"], 11)
                self.assertEqual(
                    run["visible_fixed_record_indexes"],
                    list(range(10)),
                )
                self.assertEqual(
                    [
                        row["index"]
                        for row in run["not_applicable_fixed_records"]
                    ],
                    [10],
                )
                self.assertEqual(run["actual_pair_count"], 27)
                self.assertEqual(run["expected_pair_count"], 27)
                self.assertTrue(
                    all(
                        row["byte_identical"]
                        for row in run["capture_pairs"]
                    )
                )

    def test_reported_mercenary_rows_and_all_sides_are_reviewed(self) -> None:
        for profile in ("normal", "hard"):
            run = self.model["profiles"][profile]
            checks = run["human_review"]["checks"]
            self.assertEqual(
                checks["all_six_allied_names_classes_hiring_rows"],
                "pass",
            )
            self.assertEqual(
                checks["all_ten_visible_fixed_names_classes_mercenary_rows"],
                "pass",
            )
            records = run["visible_fixed_records"]
            self.assertEqual(records[0]["name_korean"], "제시카")
            self.assertEqual(records[0]["side_id"], "0x03")
            self.assertTrue(
                all(row["side_id"] == "0x04" for row in records[1:])
            )
            self.assertIn(
                ["다크엘프", "파이크"],
                [row["mercenary_classes_korean"] for row in records],
            )
            self.assertIn(
                ["아머솔저"],
                [row["mercenary_classes_korean"] for row in records],
            )

    def test_gray_acted_sprite_is_stock_fighter_on_plane_a(self) -> None:
        for profile in ("normal", "hard"):
            gray = self.model["profiles"][profile]["battle_evidence"][
                "gray_acted_sprite"
            ]
            self.assertEqual(gray["source_silhouette_id"], "0x001E")
            self.assertEqual(gray["runtime_group_zero"]["class_id"], 1)
            self.assertEqual(gray["runtime_group_zero"]["commander_id"], 1)
            self.assertEqual(gray["runtime_group_zero"]["acted_flag"], 1)
            self.assertEqual(
                [
                    gray["runtime_group_zero"]["x"],
                    gray["runtime_group_zero"]["y"],
                ],
                [14, 11],
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

    def test_real_final_attack_reaches_all_dialogue_and_result(self) -> None:
        results = []
        for profile in ("normal", "hard"):
            result = self.model["profiles"][profile]["battle_evidence"][
                "battle_result"
            ]
            results.append(result)
            self.assertEqual(result["victory_dialogue_count"], 18)
            self.assertEqual(result["header_text"], "전과보고")
            self.assertEqual(result["point_text"], "3770P")
            self.assertTrue(
                all(cell["matches"] for cell in result["header_plane_cells"])
            )
            self.assertEqual(
                result["class_change"]["status"],
                "not_applicable",
            )
            lineage = result["diagnostic_lineage"]
            self.assertTrue(
                lineage["changed_offsets_within_declared_diagnostic_fields"]
            )
            self.assertTrue(
                lineage["input_all_fixed_records_match_japanese_source"]
            )
            self.assertTrue(lineage["all_fixed_side_and_name_ids_preserved"])
            self.assertFalse(
                lineage["source_result_state"][
                    "state_modified_before_current_replay"
                ]
            )
        self.assertEqual(
            results[0]["capture"]["sha256"],
            results[1]["capture"]["sha256"],
        )

    def test_user_reported_failures_are_closed_on_current_candidates(self) -> None:
        rows = self.model["review"]["reported_failures_closed"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(
            all(row["current_candidate_result"] == "pass" for row in rows)
        )


if __name__ == "__main__":
    unittest.main()
