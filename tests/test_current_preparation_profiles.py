import json
import unittest

from tools import verify_current_preparation_profiles as profiles


class CurrentPreparationProfilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = profiles.build_report()

    def test_both_profiles_cover_all_scenarios_exactly(self) -> None:
        profiles.validate(self.report)
        for profile in ("normal", "hard"):
            row = self.report["profiles"][profile]
            self.assertEqual(row["passed_scenarios"], 27)
            self.assertEqual(row["total_scenarios"], 27)
            self.assertEqual(row["total_pre_post_pairs"], 733)

    def test_both_profiles_cover_all_mercenaries(self) -> None:
        self.assertEqual(
            [row["mercenary_count"] for row in self.report["all_mercenary_probes"]],
            [16, 16],
        )
        self.assertTrue(
            all(
                row["ballista_icon_cell_restored"]
                for row in self.report["all_mercenary_probes"]
            )
        )

    def test_checked_report_is_current(self) -> None:
        checked = json.loads(profiles.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(checked, self.report)


if __name__ == "__main__":
    unittest.main()
