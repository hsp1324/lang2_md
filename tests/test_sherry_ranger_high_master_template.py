from __future__ import annotations

import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_CLASS_TEMPLATE_SOURCES,
)
from tools.pillow_compat import flattened_image_data

from tests.ai_class_asset_contract import (
    LIVE_ROOT,
    compose_untranslated_shared_source,
    manifest,
    manifest_row,
    pixels,
    rgba,
)


KEY = (4, 0x21)


class SherryRangerHighMasterTemplateTests(unittest.TestCase):
    def test_retained_ranger_source_identity_and_closure_are_live(self) -> None:
        source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[KEY]
        self.assertTrue(source_path.is_file())
        self.assertTrue(
            source_path.as_posix().endswith(
                "sherry-ranger-v4/logical16/04-21.png"
            )
        )
        document = manifest()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        row = manifest_row(document, *KEY)
        self.assertEqual(
            row["ai_source_position"],
            "latest/sherry-ranger-v4/logical16/04-21.png",
        )
        self.assertFalse(row["design_override"])
        self.assertTrue(row["design_override_superseded"])
        expected = compose_untranslated_shared_source(KEY, document=document)
        live = rgba(LIVE_ROOT / "4/21.png")
        self.assertEqual(pixels(expected), pixels(live))

    def test_ranger_keeps_high_master_shape_with_distinct_colors(self) -> None:
        ranger = rgba(LIVE_ROOT / "4/21.png")
        high_master = rgba(LIVE_ROOT / "4/23.png")
        ranger_alpha = tuple(
            color[3] for color in flattened_image_data(ranger)
        )
        high_master_alpha = tuple(
            color[3] for color in flattened_image_data(high_master)
        )
        self.assertEqual(ranger_alpha, high_master_alpha)
        self.assertGreaterEqual(
            sum(
                left != right
                for left, right in zip(
                    flattened_image_data(ranger),
                    flattened_image_data(high_master),
                )
            ),
            24,
        )
        self.assertLessEqual(
            len(
                {
                    color
                    for color in flattened_image_data(ranger)
                    if color[3]
                }
            ),
            15,
        )


if __name__ == "__main__":
    unittest.main()
