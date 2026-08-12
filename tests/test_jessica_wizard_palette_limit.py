from __future__ import annotations

from collections import Counter
from pathlib import Path
import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_CLASS_TEMPLATE_SOURCES,
    close_internal_transparency,
)
from tools.pillow_compat import flattened_image_data

from tests.ai_class_asset_contract import (
    LIVE_ROOT,
    manifest,
    manifest_row,
    pixels,
    rgba,
)


ROOT = Path(__file__).resolve().parents[1]
KEY = (10, 0x15)
SOURCE = SHARED_CLASS_TEMPLATE_SOURCES[KEY][0]


class JessicaWizardPaletteLimitTests(unittest.TestCase):
    def test_near_duplicate_purple_is_merged_in_retained_source(self) -> None:
        source = rgba(SOURCE)
        colors = Counter(flattened_image_data(source))
        self.assertEqual(colors[(146, 36, 182, 255)], 0)
        self.assertGreater(colors[(146, 73, 182, 255)], 0)
        self.assertEqual(colors[(36, 73, 255, 255)], 0)
        self.assertLessEqual(
            len({color for color in flattened_image_data(source) if color[3]}),
            15,
        )

    def test_identity_composition_and_closure_are_live(self) -> None:
        composed = rgba(SOURCE)
        closed_points = close_internal_transparency(composed)
        self.assertEqual(len(closed_points), 10)
        live = rgba(LIVE_ROOT / "10/15.png")
        self.assertEqual(pixels(composed), pixels(live))
        self.assertLessEqual(
            len({color for color in flattened_image_data(live) if color[3]}),
            15,
        )

    def test_manifest_records_the_current_retained_source(self) -> None:
        document = manifest()
        row = manifest_row(document, *KEY)
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        self.assertEqual(
            row["ai_source_position"],
            "latest/shared-new-classes-v2-refined/logical16/10-15.png",
        )
        self.assertFalse(row["design_override"])
        self.assertIn("내부 투명 10픽셀", row["feature"])


if __name__ == "__main__":
    unittest.main()
