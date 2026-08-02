import argparse
import unittest

from tools import verify_preparation_manual_reviews as verify


class VerifyPreparationManualReviewsTests(unittest.TestCase):
    def test_scenario_three_uses_corrected_run(self) -> None:
        self.assertEqual(
            verify.run_id_for(3),
            "glyph-lifetime-s03-corrected01",
        )
        self.assertEqual(verify.run_id_for(2), "glyph-lifetime-full01")
        self.assertEqual(verify.run_id_for(4), "glyph-lifetime-full01")

    def test_require_equal_rejects_stale_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            verify.require_equal("old", "current", "hash")

    def test_required_scenarios_are_complete(self) -> None:
        self.assertEqual(verify.SCENARIOS, tuple(range(1, 28)))

    def test_checked_report_is_current(self) -> None:
        args = argparse.Namespace(
            scenario=None,
            review_root=verify.DEFAULT_REVIEW_ROOT,
            preparation_root=verify.DEFAULT_PREPARATION_ROOT,
            gray_root=verify.DEFAULT_GRAY_ROOT,
            identity_report=verify.DEFAULT_IDENTITY_REPORT,
            normal_rom=verify.DEFAULT_NORMAL_ROM,
            hard_rom=verify.DEFAULT_HARD_ROM,
        )
        checked = verify.review.load_json(verify.DEFAULT_OUTPUT)
        self.assertEqual(checked, verify.build_report(args))


if __name__ == "__main__":
    unittest.main()
