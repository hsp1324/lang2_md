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
    design_overrides,
    manifest,
    manifest_row,
    pixels,
    rgba,
)


KEY = (3, 0x15)


class LanaWizardLianaTemplateTests(unittest.TestCase):
    def test_lana_wizard_retained_source_and_override_are_live(self) -> None:
        source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[KEY]
        self.assertTrue(source_path.is_file())
        self.assertTrue(
            source_path.as_posix().endswith(
                "lana-wizard-liana-template-v1/logical16/03-15.png"
            )
        )

        document = manifest()
        row = manifest_row(document, *KEY)
        overrides = design_overrides()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        self.assertTrue(row["design_override"])
        self.assertEqual(row["design_revision"], overrides[KEY]["revision"])
        self.assertEqual(
            row["ai_source_position"],
            "latest/lana-wizard-liana-template-v1/logical16/03-15.png",
        )

        expected = compose_untranslated_shared_source(KEY, document=document)
        live = rgba(LIVE_ROOT / "3/15.png")
        self.assertEqual(pixels(expected), pixels(live))
        colors = {
            color for color in flattened_image_data(live) if color[3]
        }
        self.assertLessEqual(len(colors), 15)
        self.assertNotIn((255, 0, 255, 255), colors)
        self.assertNotIn((0, 0, 0, 255), colors)


if __name__ == "__main__":
    unittest.main()
