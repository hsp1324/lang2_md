import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import run_pike_acted_surface_probe as probe


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "localization/pike_acted_surface_regression.json"


class PikeActedSurfaceRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_report_identifies_the_exact_reported_class_and_collision(self) -> None:
        self.assertEqual(self.report["status"], "pass")
        self.assertEqual(self.report["reported_defect"]["exact_class"], "파이크")
        self.assertEqual(self.report["reported_defect"]["class_id"], "0x62")
        self.assertEqual(self.report["root_cause"]["former_dynamic_tile"], "0x03B0")
        self.assertEqual(self.report["root_cause"]["pike_gray_tile_range"], "0x03B0..0x03B3")

    def test_reported_battle_pool_matches_the_builder(self) -> None:
        self.assertEqual(
            self.report["fix"]["battle_dynamic_tiles"],
            [f"0x{tile:04X}" for tile in builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS],
        )

    def test_runtime_covers_real_pike_action_and_all_gray_classes(self) -> None:
        runtime = self.report["runtime"]
        self.assertEqual(runtime["hired_class"], "파이크")
        self.assertEqual(runtime["hired_count"], 6)
        self.assertEqual(runtime["movement"]["before"]["acted_flag"], 0)
        self.assertEqual(runtime["movement"]["after"]["acted_flag"], 1)
        self.assertEqual(runtime["all_ordinary_gray_class_count"], 16)
        self.assertTrue(runtime["all_ordinary_gray_match_before_move"])
        self.assertTrue(runtime["all_ordinary_gray_match_after_move"])

    def test_report_is_non_release(self) -> None:
        self.assertFalse(self.report["release_promoted"])
        self.assertFalse(self.report["version_bumped"])
        self.assertEqual(probe.PIKE_CLASS_ID, 0x62)


if __name__ == "__main__":
    unittest.main()
