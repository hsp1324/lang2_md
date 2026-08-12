from __future__ import annotations

from pathlib import Path
import unittest

from tools.build_ai_class_sprite_assets import (
    AI_SOURCE_ORIGINAL_FILES,
    ASSET_VERSION,
    FINAL_PIXEL_OVERRIDES,
)

from tests.ai_class_asset_contract import (
    LIVE_ROOT,
    ROM_SPRITE_ROOT,
    design_overrides,
    manifest,
    manifest_row,
    override_image,
    pixels,
    rgba,
)


ROOT = Path(__file__).resolve().parents[1]
KEY = (1, 0x22)


class ElwinHeroSelectedSampleTests(unittest.TestCase):
    def test_selected_source_original_and_saved_override_are_live(self) -> None:
        source = AI_SOURCE_ORIGINAL_FILES[KEY]
        self.assertEqual(
            source.relative_to(ROOT).as_posix(),
            (
                "assets/class-sprites/source/latest/"
                "sample-class-variants-v4-free-five/01-elwin-22-hero/"
                "ai/04.png"
            ),
        )
        self.assertTrue(source.is_file())

        document = manifest()
        row = manifest_row(document, *KEY)
        embedded_source = rgba(LIVE_ROOT / row["ai_source_original_file"])
        self.assertEqual(pixels(embedded_source), pixels(rgba(source)))

        overrides = design_overrides()
        self.assertIn(KEY, overrides)
        live = rgba(LIVE_ROOT / "1/22.png")
        self.assertEqual(pixels(live), pixels(override_image(KEY, overrides)))
        self.assertEqual(row["design_revision"], overrides[KEY]["revision"])

    def test_identity_pixels_and_final_ornament_are_current(self) -> None:
        document = manifest()
        row = manifest_row(document, *KEY)
        live = rgba(LIVE_ROOT / "1/22.png")
        original = rgba(ROM_SPRITE_ROOT / "1/22-p1.png")
        final_overrides = FINAL_PIXEL_OVERRIDES[KEY]
        locked = {
            tuple(point) for point in row["identity_lock_points"]
        } - set(final_overrides)
        for point in locked:
            if original.getpixel(point)[3]:
                self.assertEqual(live.getpixel(point), original.getpixel(point))
        for point, color in final_overrides.items():
            self.assertEqual(live.getpixel(point), color)

    def test_manifest_names_only_retained_current_inputs(self) -> None:
        document = manifest()
        row = manifest_row(document, *KEY)
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        self.assertIn("샘플 클래스 선정", row["ai_source_kind"])
        self.assertIn(
            "sample-class-variants-v4-free-five/01-elwin-22-hero/ai/04.png",
            row["ai_source_position"],
        )
        self.assertIn("ai_class_design_overrides.json · 1:22", row["ai_source_position"])
        self.assertNotIn("logical16/04.png", row["ai_source_position"])
        self.assertTrue(row["design_override"])


if __name__ == "__main__":
    unittest.main()
