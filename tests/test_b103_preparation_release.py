import json
import unittest

from tools import verify_b103_preparation_release as release


class B103PreparationReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = release.build_report()

    def test_release_report_passes_all_runtime_contracts(self) -> None:
        release.validate(self.report)
        matrix = self.report["full_preparation_matrix"]
        self.assertEqual(matrix["passed_scenarios"], 27)
        self.assertEqual(matrix["total_scenarios"], 27)
        self.assertGreater(matrix["total_pre_post_pairs"], 500)

    def test_checked_report_is_current(self) -> None:
        checked = json.loads(release.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(checked, self.report)


if __name__ == "__main__":
    unittest.main()
