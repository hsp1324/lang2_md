import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_surface_scenario_06.json"


class PreparationSurfaceScenario06Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_checked_report_is_current(self) -> None:
        subprocess.check_call(
            [
                sys.executable,
                str(
                    ROOT
                    / "tools/verify_preparation_surface_scenario_06.py"
                ),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_every_allied_npc_and_enemy_record_is_accounted_for(self) -> None:
        self.assertEqual(self.model["status"], "scenario_6_complete_pass")
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                run = self.model["profiles"][profile]
                self.assertEqual(run["status"], "scenario_6_surface_pass")
                self.assertEqual(run["allied_commander_count"], 5)
                self.assertEqual(run["fixed_record_count"], 13)
                self.assertEqual(
                    run["visible_fixed_record_indexes"],
                    list(range(12)),
                )
                self.assertEqual(
                    [
                        row["index"]
                        for row in run["not_applicable_fixed_records"]
                    ],
                    [12],
                )
                self.assertEqual(run["actual_pair_count"], 26)
                self.assertTrue(
                    all(row["byte_identical"] for row in run["capture_pairs"])
                )

    def test_requested_names_classes_and_mercenaries_are_reviewed(self) -> None:
        joined = " ".join(self.model["review"]["allied_scope"])
        joined += " " + " ".join(self.model["review"]["fixed_record_scope"])
        for text in (
            "엘윈",
            "헤인",
            "스코트",
            "리아나",
            "쉐리",
            "글래디에이터",
            "시민",
            "바바리안",
            "다크엘프",
            "호스맨",
            "샤먼",
        ):
            self.assertIn(text, joined)
        for profile in ("normal", "hard"):
            checks = self.model["profiles"][profile]["human_review"]["checks"]
            self.assertTrue(all(value == "pass" for value in checks.values()))

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
                [5, 26],
            )
            self.assertTrue(
                gray["matches_stock_fighter_silhouette_expansion"]
            )
            self.assertTrue(
                all(
                    row["hits"]
                    and all(
                        hit["plane"] == "plane_a" for hit in row["hits"]
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
        self.assertEqual(choices["normal"], choices["hard"])
        self.assertTrue(
            self.model["cross_profile_identity"][
                "all_three_class_change_frames_identical"
            ]
        )

    def test_result_diagnostic_is_runtime_only_and_header_is_intact(self) -> None:
        for profile in ("normal", "hard"):
            result = self.model["profiles"][profile]["battle_evidence"][
                "battle_result"
            ]
            self.assertEqual(result["header_text"], "전과보고")
            self.assertTrue(
                all(cell["matches"] for cell in result["header_plane_cells"])
            )
            lineage = result["diagnostic_lineage"]
            self.assertEqual(
                lineage["runtime_groups_marked_defeated"],
                list(range(9, 18)),
            )
            self.assertTrue(lineage["all_player_deployments_unchanged"])
            self.assertTrue(lineage["all_thirteen_fixed_records_unchanged"])
            self.assertTrue(lineage["scheduled_turn_table_unchanged"])
            self.assertTrue(lineage["scheduled_turn_handlers_unchanged"])
            self.assertTrue(
                lineage["korean_battle_result_header_unchanged"]
            )


if __name__ == "__main__":
    unittest.main()
