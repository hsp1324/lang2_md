from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import verify_preparation_glyph_conflicts as verifier


ROOT = Path(__file__).resolve().parents[1]


class PreparationGlyphConflictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contexts = verifier.build_contexts(
            (ROOT / builder.IN_ROM).read_bytes(),
            verifier.DEFAULT_REFERENCE.read_bytes(),
            verifier.DEFAULT_HARD_PLAN,
        )
        cls.report = verifier.verify_contexts(cls.contexts)

    def test_all_normal_hard_and_synthetic_surfaces_are_collision_free(self) -> None:
        self.assertEqual(self.report["surface_context_count"], 69449)
        self.assertEqual(self.report["conflict_count"], 0)
        self.assertEqual(self.report["status"], "pass")

    def test_cursor_redraw_regression_pairs_use_distinct_slots(self) -> None:
        rows = {
            (row["left"], row["right"]): row
            for row in self.report["regression_pairs"]
        }
        for pair in verifier.REGRESSION_PAIRS:
            with self.subTest(pair=pair):
                self.assertTrue(rows[pair]["separated"])

    def test_complete_scenario_roster_is_one_lifetime(self) -> None:
        scenario_12 = next(
            context
            for context in self.contexts
            if context.name == "scenario:12:complete_roster"
        )
        self.assertIn("쉐", scenario_12.chars)
        self.assertIn("제", scenario_12.chars)


if __name__ == "__main__":
    unittest.main()
