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

    def test_scenario_one_is_only_preparation_partial_pass(self) -> None:
        self.assertEqual(
            self.model["status"],
            "scenario_1_preparation_partial_pass_battle_pending",
        )
        progress = self.model["matrix_progress"]
        self.assertEqual(progress["required_profile_scenario_runs"], 54)
        self.assertEqual(progress["preparation_surface_runs_reviewed"], 2)
        self.assertEqual(progress["fully_accepted_scenarios"], 0)
        self.assertEqual(self.acceptance["status"], "pending")
        self.assertEqual(
            self.acceptance["matrix_summary"],
            {
                "required_profile_scenario_runs": 54,
                "preparation_surface_runs_reviewed": 2,
                "fully_accepted_scenarios": 0,
                "release_gate_status": "pending",
            },
        )
        self.assertEqual(
            {
                (row["scenario"], row["profile"], row["status"])
                for row in self.acceptance["scenario_progress"]
            },
            {
                (1, "normal_korean", "preparation_partial_pass_battle_pending"),
                (1, "hard_korean", "preparation_partial_pass_battle_pending"),
            },
        )

    def test_both_profiles_have_exact_full_screen_pairs(self) -> None:
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                run = self.model["profiles"][profile]
                self.assertEqual(
                    run["status"],
                    "preparation_surface_pass_battle_pending",
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
                    "pending_separate_battle_run",
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
