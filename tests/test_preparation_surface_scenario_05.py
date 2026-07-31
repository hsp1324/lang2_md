import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_surface_scenario_05.json"


class PreparationSurfaceScenario05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_checked_report_is_current(self) -> None:
        subprocess.check_call(
            [
                sys.executable,
                str(
                    ROOT
                    / "tools/verify_preparation_surface_scenario_05.py"
                ),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_all_commanders_and_fixed_records_are_accounted_for(self) -> None:
        self.assertEqual(self.model["status"], "scenario_5_complete_pass")
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                run = self.model["profiles"][profile]
                self.assertEqual(run["status"], "scenario_5_surface_pass")
                self.assertEqual(run["allied_commander_count"], 5)
                self.assertEqual(run["fixed_record_count"], 9)
                self.assertEqual(
                    run["visible_fixed_record_indexes"],
                    [0, 1, 2, 3, 4],
                )
                self.assertEqual(
                    [
                        row["index"]
                        for row in run["not_applicable_fixed_records"]
                    ],
                    [5, 6, 7, 8],
                )
                self.assertEqual(run["actual_pair_count"], 19)
                self.assertEqual(run["expected_pair_count"], 19)
                self.assertTrue(
                    all(
                        row["byte_identical"]
                        for row in run["capture_pairs"]
                    )
                )

    def test_sherry_and_reported_werewolf_rows_are_reviewed(self) -> None:
        for profile in ("normal", "hard"):
            checks = self.model["profiles"][profile]["human_review"]["checks"]
            self.assertEqual(checks["sherry_name_after_shop"], "pass")
            self.assertEqual(checks["werewolf_and_ulffman_rows"], "pass")
            self.assertEqual(
                checks["all_korean_commander_class_and_mercenary_labels"],
                "pass",
            )
            self.assertEqual(
                checks["commander_and_mercenary_sprites"],
                "pass",
            )

    def test_gray_acted_sprite_is_stock_fighter_on_plane_a(self) -> None:
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                gray = self.model["profiles"][profile]["battle_evidence"][
                    "gray_acted_sprite"
                ]
                self.assertEqual(gray["source_silhouette_id"], "0x001E")
                self.assertEqual(gray["runtime_group_zero"]["class_id"], 1)
                self.assertEqual(
                    gray["runtime_group_zero"]["commander_id"], 1
                )
                self.assertEqual(gray["runtime_group_zero"]["acted_flag"], 1)
                self.assertEqual(
                    [
                        gray["runtime_group_zero"]["x"],
                        gray["runtime_group_zero"]["y"],
                    ],
                    [14, 51],
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

    def test_all_three_natural_class_choices_match_between_profiles(self) -> None:
        choices = {}
        for profile in ("normal", "hard"):
            rows = self.model["profiles"][profile]["battle_evidence"][
                "class_change"
            ]["choices"]
            choices[profile] = [
                (
                    row["class_name"],
                    row["mercenary_names"],
                    row["magic_names"],
                    row["capture"]["sha256"],
                )
                for row in rows
            ]
            self.assertEqual(
                [row["class_name"] for row in rows],
                ["로드", "호크나이트", "세인트"],
            )
            self.assertTrue(
                all(row["capture"]["dimensions"] == [320, 240] for row in rows)
            )
        self.assertEqual(choices["normal"], choices["hard"])
        self.assertTrue(
            self.model["cross_profile_identity"][
                "all_three_class_change_frames_identical"
            ]
        )

    def test_result_uses_stock_escape_and_keeps_korean_header(self) -> None:
        captures = []
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                result = self.model["profiles"][profile]["battle_evidence"][
                    "battle_result"
                ]
                captures.append(result["capture"]["sha256"])
                self.assertEqual(result["header_text"], "전과보고")
                self.assertTrue(
                    all(
                        cell["matches"]
                        for cell in result["header_plane_cells"]
                    )
                )
                lineage = result["diagnostic_lineage"]
                self.assertTrue(
                    lineage["changed_only_checksum_and_elwin_y"]
                )
                self.assertTrue(lineage["all_fixed_records_unchanged"])
                self.assertTrue(
                    lineage["all_other_player_deployments_unchanged"]
                )
                self.assertTrue(lineage["scenario_event_block_unchanged"])
                self.assertTrue(
                    lineage["korean_battle_result_header_unchanged"]
                )
        self.assertEqual(len(set(captures)), 1)


if __name__ == "__main__":
    unittest.main()
