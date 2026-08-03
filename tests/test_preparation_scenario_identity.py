import argparse
import json
from pathlib import Path
import unittest

from tools import verify_battle_mercenary_sprite_cache as battle
from tools import verify_preparation_scenario_identity as identity


ROOT = Path(__file__).resolve().parents[1]


class PreparationScenarioIdentityTests(unittest.TestCase):
    def test_run_id_override_parser_is_strict(self) -> None:
        self.assertEqual(
            battle.parse_run_id_overrides("3=corrected,12=targeted"),
            {3: "corrected", 12: "targeted"},
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            battle.parse_run_id_overrides("3")
        with self.assertRaises(argparse.ArgumentTypeError):
            battle.parse_run_id_overrides("32=bad")

    def test_corrected_scenario_three_identity_passes_both_profiles(self) -> None:
        class Args:
            normal_rom = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
            hard_rom = ROOT / "tmp/current-glyph-lifetime-fix-hard.md"
            normal_run_id = "glyph-lifetime-full01"
            hard_run_id = "glyph-lifetime-full01"
            normal_run_id_overrides = {3: "glyph-lifetime-s03-corrected01"}
            hard_run_id_overrides = {3: "glyph-lifetime-s03-corrected01"}
            scenarios = [3]
            capture_root = ROOT / "captures/run/preparation_surface_matrix"

        report = identity.build_report(Args())
        self.assertEqual(report["status"], "pass")
        for profile in ("normal", "hard"):
            row = report["profiles"][profile]["scenarios"][0]
            self.assertEqual(row["identity"]["identified_scenario"], 3)

    def test_old_scenario_three_evidence_is_rejected(self) -> None:
        class Args:
            normal_rom = ROOT / "tmp/current-glyph-lifetime-fix-normal.md"
            hard_rom = ROOT / "tmp/current-glyph-lifetime-fix-hard.md"
            normal_run_id = "glyph-lifetime-full01"
            hard_run_id = "glyph-lifetime-full01"
            normal_run_id_overrides = {}
            hard_run_id_overrides = {}
            scenarios = [3]
            capture_root = ROOT / "captures/run/preparation_surface_matrix"

        report = identity.build_report(Args())
        self.assertEqual(report["status"], "fail")
        for profile in ("normal", "hard"):
            error = report["profiles"][profile]["scenarios"][0]["error"]
            self.assertIn("identified 1", error)


if __name__ == "__main__":
    unittest.main()
