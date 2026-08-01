import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "localization/current_candidate_surface_regression.json"


class CurrentCandidateSurfaceRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_all_current_surface_gates_pass(self) -> None:
        self.assertEqual(self.report["status"], "pass")
        for key in (
            "preparation_surfaces",
            "scenario_identity",
            "glyph_lifetime_conflicts",
            "hscroll",
            "first_dynamic_draw",
            "acted_gray_matrix",
            "battle_mercenary_cache",
            "all_mercenary_hire_pages",
            "pike_active_and_acted",
            "monk_active_and_acted",
            "shop_items",
        ):
            self.assertEqual(self.report[key]["status"], "pass", key)

    def test_all_scenario_counts_are_complete(self) -> None:
        self.assertEqual(
            self.report["preparation_surfaces"]["passed_profile_scenario_runs"],
            54,
        )
        self.assertEqual(self.report["hscroll"]["states"], 162)
        self.assertEqual(self.report["acted_gray_matrix"]["normal"]["scenarios"], "27/27")
        self.assertEqual(self.report["acted_gray_matrix"]["hard"]["scenarios"], "27/27")
        self.assertEqual(self.report["all_mercenary_hire_pages"]["mercenary_classes"], 16)

    def test_exact_reported_pike_and_monk_caches_pass(self) -> None:
        self.assertEqual(self.report["pike_active_and_acted"]["hired_per_profile"], 6)
        monk = self.report["monk_active_and_acted"]
        self.assertEqual(monk["active_frame_0"], "0x0370..0x0373")
        self.assertEqual(monk["active_frame_1"], "0x0470..0x0473")
        self.assertEqual(monk["acted_gray"], "0x03D8..0x03DB")
        self.assertTrue(monk["both_profiles_match_original_sprite_sources"])

    def test_report_does_not_promote_a_release(self) -> None:
        self.assertFalse(self.report["candidate_roms"]["release_roms_modified"])
        self.assertFalse(self.report["candidate_roms"]["version_bumped"])
        self.assertEqual(self.report["remaining_release_gate"]["status"], "pending")
        self.assertFalse(
            self.report["remaining_release_gate"]["release_or_version_promotion_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
