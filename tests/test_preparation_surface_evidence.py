import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools import verify_preparation_surface_evidence as evidence


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_surface_matrix.json"
ACCEPTANCE = ROOT / "localization/preparation_surface_acceptance.json"


class PreparationSurfaceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))
        cls.acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))

    def test_checked_report_is_current(self) -> None:
        subprocess.check_call(
            [
                sys.executable,
                str(ROOT / "tools/verify_preparation_surface_evidence.py"),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_scenario_one_report_and_cumulative_acceptance_are_current(self) -> None:
        self.assertEqual(
            self.model["status"],
            "scenario_1_complete_pass_scenarios_2_to_27_pending",
        )
        progress = self.model["matrix_progress"]
        self.assertEqual(progress["required_profile_scenario_runs"], 54)
        self.assertEqual(progress["preparation_surface_runs_reviewed"], 2)
        self.assertEqual(progress["battle_surface_runs_reviewed"], 2)
        self.assertEqual(progress["fully_accepted_profile_scenario_runs"], 2)
        self.assertEqual(progress["fully_accepted_scenarios"], 1)
        self.assertEqual(self.acceptance["status"], "pending")
        self.assertEqual(
            self.acceptance["matrix_summary"],
            {
                "required_profile_scenario_runs": 54,
                "preparation_surface_runs_reviewed": 14,
                "battle_surface_runs_reviewed": 14,
                "fully_accepted_profile_scenario_runs": 14,
                "fully_accepted_scenarios": 7,
                "release_gate_status": "pending",
            },
        )
        self.assertEqual(
            {
                (row["scenario"], row["profile"], row["status"])
                for row in self.acceptance["scenario_progress"]
            },
            {
                (1, "normal_korean", "pass"),
                (1, "hard_korean", "pass"),
                (2, "normal_korean", "pass"),
                (2, "hard_korean", "pass"),
                (3, "normal_korean", "pass"),
                (3, "hard_korean", "pass"),
                (4, "normal_korean", "pass"),
                (4, "hard_korean", "pass"),
                (5, "normal_korean", "pass"),
                (5, "hard_korean", "pass"),
                (9, "normal_korean", "pass"),
                (9, "hard_korean", "pass"),
                (11, "normal_korean", "pass"),
                (11, "hard_korean", "pass"),
            },
        )

    def test_both_profiles_have_exact_full_screen_pairs(self) -> None:
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                run = self.model["profiles"][profile]
                self.assertEqual(
                    run["status"],
                    "scenario_1_surface_pass",
                )
                self.assertEqual(run["actual_pair_count"], 14)
                self.assertEqual(run["expected_pair_count"], 14)
                self.assertTrue(
                    all(row["byte_identical"] for row in run["capture_pairs"])
                )
                self.assertEqual(
                    run["human_review"]["checks"][
                        "gray_acted_sprites_and_battle_result"
                    ],
                    "pass",
                )

    def test_gray_acted_sprite_matches_stock_fighter_silhouette(self) -> None:
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                gray = self.model["profiles"][profile]["battle_evidence"][
                    "gray_acted_sprite"
                ]
                self.assertEqual(
                    gray["runtime_group_zero"]["class_id"], 1
                )
                self.assertEqual(
                    gray["runtime_group_zero"]["commander_id"], 1
                )
                self.assertEqual(
                    gray["runtime_group_zero"]["acted_flag"], 1
                )
                self.assertEqual(
                    [
                        gray["runtime_group_zero"]["x"],
                        gray["runtime_group_zero"]["y"],
                    ],
                    [12, 17],
                )
                self.assertEqual(gray["source_silhouette_id"], "0x001E")
                self.assertTrue(
                    gray["matches_stock_fighter_silhouette_expansion"]
                )
                self.assertEqual(
                    gray["vram_sha256"],
                    (
                        "74e404c1c9dad9a31578fcdf25c61158a"
                        "de1fdb43221941c7b2c3f6e19313b22"
                    ),
                )

    def test_battle_result_is_identical_and_keeps_korean_header(self) -> None:
        results = [
            self.model["profiles"][profile]["battle_evidence"][
                "battle_result"
            ]
            for profile in ("normal", "hard")
        ]
        self.assertEqual(
            results[0]["capture"]["sha256"],
            results[1]["capture"]["sha256"],
        )
        for result in results:
            self.assertEqual(result["header_text"], "전과보고")
            self.assertTrue(
                all(cell["matches"] for cell in result["header_plane_cells"])
            )
            self.assertTrue(
                result["diagnostic_lineage"][
                    "changed_only_bald_setup_and_checksum"
                ]
            )
            self.assertTrue(
                result["diagnostic_lineage"][
                    "battle_result_header_and_event_code_unchanged"
                ]
            )

    def test_yal_uses_clean_ordinary_pattern_tile_before_and_after_shop(self) -> None:
        for profile in ("normal", "hard"):
            checkpoint = self.model["profiles"][profile]["runtime_checkpoint"]
            self.assertEqual(checkpoint["char"], "얄")
            self.assertEqual(checkpoint["local_index"], "0x3F")
            self.assertEqual(checkpoint["dynamic_slot"], 24)
            self.assertEqual(checkpoint["vram_tile"], "0x03DF")
            for phase in ("pre_shop", "post_shop"):
                state = checkpoint[phase]
                self.assertTrue(state["matches_candidate_rom_glyph"])
                self.assertEqual(state["hscroll_base"], "0xF400")
                self.assertEqual(state["hscroll_nonzero_bytes"], 0)
                self.assertEqual(
                    state["plane_references"],
                    [
                        {
                            "plane": "plane_a",
                            "x": 7,
                            "y": 8,
                            "tile_word": "0x83DF",
                        }
                    ],
                )


if __name__ == "__main__":
    unittest.main()
