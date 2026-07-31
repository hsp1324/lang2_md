import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_surface_scenario_08.json"


class PreparationSurfaceScenario08Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_checked_report_is_current(self) -> None:
        subprocess.check_call(
            [
                sys.executable,
                str(
                    ROOT
                    / "tools/verify_preparation_surface_scenario_08.py"
                ),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_every_allied_npc_and_enemy_record_is_accounted_for(self) -> None:
        self.assertEqual(self.model["status"], "scenario_8_complete_pass")
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                run = self.model["profiles"][profile]
                self.assertEqual(run["status"], "scenario_8_surface_pass")
                self.assertEqual(run["allied_commander_count"], 7)
                self.assertEqual(run["fixed_record_count"], 11)
                self.assertEqual(
                    run["visible_fixed_record_indexes"],
                    list(range(9)),
                )
                self.assertEqual(
                    [
                        row["index"]
                        for row in run["not_applicable_fixed_records"]
                    ],
                    [9, 10],
                )
                self.assertEqual(run["actual_pair_count"], 28)
                self.assertTrue(
                    all(row["byte_identical"] for row in run["capture_pairs"])
                )

    def test_names_classes_mercenaries_and_shop_rows_are_reviewed(self) -> None:
        joined = " ".join(self.model["review"]["allied_scope"])
        joined += " " + " ".join(self.model["review"]["fixed_record_scope"])
        joined += " " + " ".join(self.model["review"]["shop_scope"])
        for text in (
            "엘윈",
            "헤인",
            "스코트",
            "리아나",
            "쉐리",
            "아론",
            "키스",
            "크레이머",
            "발가스",
            "조름",
            "제너럴",
            "하이로드",
            "메이지",
            "매직나이트",
            "다크엘프",
            "호스맨",
            "호크나이트",
            "그리폰",
            "대거",
            "로브",
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
                [3, 7],
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

    def test_hidden_vargas_and_zolm_are_stock_runtime_reinforcements(
        self,
    ) -> None:
        records = {}
        for profile in ("normal", "hard"):
            hidden = self.model["profiles"][profile]["battle_evidence"][
                "hidden_reinforcements"
            ]
            self.assertEqual(hidden["status"], "pass")
            self.assertEqual(
                (
                    hidden["vargas"]["name"],
                    hidden["vargas"]["class_name"],
                ),
                ("발가스", "제너럴"),
            )
            self.assertEqual(
                (
                    hidden["zolm"]["name"],
                    hidden["zolm"]["class_name"],
                ),
                ("조름", "로드"),
            )
            self.assertEqual(
                hidden["vargas"]["runtime_group"],
                {
                    "group": 16,
                    "class_id": 73,
                    "commander_id": 15,
                    "acted_flag": 0,
                    "hp": 10,
                    "x": 2,
                    "y": 11,
                    "at": 40,
                    "df": 30,
                    "record_prefix": "490f000a1000020b000000007e0f000a",
                },
            )
            self.assertEqual(
                hidden["zolm"]["runtime_group"],
                {
                    "group": 17,
                    "class_id": 50,
                    "commander_id": 19,
                    "acted_flag": 0,
                    "hp": 10,
                    "x": 3,
                    "y": 8,
                    "at": 24,
                    "df": 23,
                    "record_prefix": "3213000a11000308000000007213000a",
                },
            )
            records[profile] = (
                hidden["vargas"]["runtime_group"],
                hidden["zolm"]["runtime_group"],
            )
            survival = hidden["diagnostic_lineage"]
            self.assertEqual(survival["kramer_probe_at_df"], [0, 14])
            self.assertTrue(survival["hidden_vargas_record_unchanged"])
            self.assertTrue(survival["hidden_zolm_record_unchanged"])
            self.assertTrue(survival["matches_expected_sha256"])
        self.assertEqual(records["normal"], records["hard"])

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

    def test_result_diagnostic_is_record_isolated_and_header_is_intact(
        self,
    ) -> None:
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
                lineage["kramer_source_coordinates"],
                [38, 8],
            )
            self.assertEqual(
                lineage["kramer_probe_coordinates"],
                [2, 6],
            )
            self.assertEqual(lineage["kramer_probe_at_df"], [0, 0])
            self.assertTrue(lineage["kramer_probe_mercenaries_removed"])
            self.assertTrue(lineage["all_player_deployments_unchanged"])
            self.assertTrue(lineage["all_non_kramer_fixed_records_unchanged"])
            self.assertTrue(lineage["hidden_vargas_record_unchanged"])
            self.assertTrue(lineage["hidden_zolm_record_unchanged"])
            self.assertTrue(lineage["scheduled_turn_table_unchanged"])
            self.assertTrue(lineage["scheduled_turn_handlers_unchanged"])
            self.assertTrue(
                lineage["korean_battle_result_header_unchanged"]
            )


if __name__ == "__main__":
    unittest.main()
