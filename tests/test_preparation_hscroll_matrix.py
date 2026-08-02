import argparse
import json
import unittest

from tools import verify_preparation_hscroll_matrix as hscroll


class PreparationHscrollMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.args = argparse.Namespace(
            capture_root=hscroll.DEFAULT_CAPTURE_ROOT,
            identity_report=hscroll.DEFAULT_IDENTITY_REPORT,
            manual_report=hscroll.DEFAULT_MANUAL_REPORT,
            ownership_report=hscroll.DEFAULT_OWNERSHIP_REPORT,
            normal_rom=hscroll.DEFAULT_NORMAL_ROM,
            hard_rom=hscroll.DEFAULT_HARD_ROM,
        )
        cls.report = hscroll.build_report(cls.args)

    def test_checked_report_is_current(self) -> None:
        checked = json.loads(hscroll.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(checked, self.report)

    def test_both_profiles_cover_every_required_state(self) -> None:
        self.assertEqual(self.report["status"], "pass")
        self.assertEqual(self.report["total_profile_scenario_runs"], 54)
        self.assertEqual(self.report["total_states_checked"], 162)
        self.assertEqual(self.report["total_nonzero_hscroll_states"], 0)
        for profile in hscroll.PROFILES:
            row = self.report["profiles"][profile]
            self.assertEqual(row["passed_scenarios"], 27)
            self.assertEqual(row["total_scenarios"], 27)
            self.assertEqual(row["states_checked"], 81)
            self.assertEqual(row["nonzero_hscroll_states"], 0)

    def test_every_state_decodes_the_stock_hscroll_allocation(self) -> None:
        for profile in hscroll.PROFILES:
            for scenario in self.report["profiles"][profile]["scenarios"]:
                for phase in hscroll.PHASES:
                    state = scenario["states"][phase]
                    self.assertEqual(state["vdp_register_11"], "0x00")
                    self.assertEqual(state["vdp_register_13"], "0x3D")
                    self.assertEqual(state["hscroll_base"], "0xF400")
                    self.assertEqual(state["hscroll_end"], "0xF7FF")
                    self.assertEqual(state["nonzero_hscroll_bytes"], 0)
                    self.assertEqual(state["dynamic_tiles_inside_hscroll"], [])

    def test_current_pool_is_outside_the_historical_collision(self) -> None:
        pool = self.report["dynamic_tile_pool"]
        self.assertEqual(pool["tile_count"], 26)
        self.assertTrue(pool["all_outside_hscroll"])
        self.assertTrue(all(row["outside_hscroll"] for row in pool["tiles"]))
        historical = self.report["historical_collision_reference"]
        self.assertTrue(historical["historical_tiles_inside_hscroll"])
        self.assertGreater(historical["nonzero_hscroll_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
