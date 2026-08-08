from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

from tools.rework_king_hero_and_archmage_magic_samples import (
    HERO_HEAD_ORNAMENT_DARK_POINTS,
    HERO_HEAD_ORNAMENT_LIGHT_POINTS,
    HERO_HEAD_ORNAMENT_POINTS,
    HERO_PURPLE_HEAD_ORNAMENT_DARK,
    HERO_PURPLE_HEAD_ORNAMENT_LIGHT,
)


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    "sample-class-variants-v4-free-five/01-elwin-22-hero"
)
LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"


class ElwinHeroSelectedSampleTests(unittest.TestCase):
    def test_live_hero_is_exactly_selected_sample_four(self) -> None:
        live = Image.open(LIVE_ROOT / "1/22.png").convert("RGBA")
        sample = Image.open(SAMPLE_ROOT / "logical16/04.png").convert("RGBA")
        self.assertEqual(
            list(live.get_flattened_data()),
            list(sample.get_flattened_data()),
        )
        for point in HERO_HEAD_ORNAMENT_LIGHT_POINTS:
            self.assertEqual(live.getpixel(point), HERO_PURPLE_HEAD_ORNAMENT_LIGHT)
        for point in HERO_HEAD_ORNAMENT_DARK_POINTS:
            self.assertEqual(live.getpixel(point), HERO_PURPLE_HEAD_ORNAMENT_DARK)

    def test_face_and_red_hair_match_the_archived_preselection_identity(self) -> None:
        live = Image.open(LIVE_ROOT / "1/22.png").convert("RGBA")
        archive = Image.open(
            SAMPLE_ROOT / "archive/01-22-before-purple-sample-04.png"
        ).convert("RGBA")
        masks = json.loads(
            (ROOT / "editor/ai_identity_masks.json").read_text(encoding="utf-8")
        )
        locked = {
            tuple(point) for point in masks["masks"]["1:22"]
        } - HERO_HEAD_ORNAMENT_POINTS
        for point in locked:
            self.assertEqual(live.getpixel(point), archive.getpixel(point))

    def test_manifest_identifies_selected_sample_and_current_version(self) -> None:
        manifest = json.loads(
            (LIVE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        row = manifest["commanders"]["1"]["classes"][str(0x22)]
        self.assertEqual(
            manifest["asset_version"],
            "identity-mask-and-silhouette-closure-v107",
        )
        self.assertIn("샘플 클래스 선정", row["ai_source_kind"])
        self.assertTrue(row["ai_source_position"].endswith("logical16/04.png"))


if __name__ == "__main__":
    unittest.main()
