from __future__ import annotations

import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_AARON_HIGH_PRIEST_SOURCE_KEYS,
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


TARGETS = {(commander_id, 0x16) for commander_id in (2, 3, 5, 7, 8, 10)}


class SharedAaronHighPriestTests(unittest.TestCase):
    def test_retained_sources_override_identity_and_closure_are_live(self) -> None:
        document = manifest()
        overrides = design_overrides()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        self.assertEqual(SHARED_AARON_HIGH_PRIEST_SOURCE_KEYS, TARGETS)
        for key in sorted(TARGETS):
            with self.subTest(commander_id=key[0]):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertTrue(source_path.is_file())
                self.assertIn("shared-high-priest-aaron-v1", str(source_path))
                row = manifest_row(document, *key)
                self.assertTrue(row["design_override"])
                self.assertEqual(
                    row["design_revision"], overrides[key]["revision"]
                )
                self.assertIn(
                    "shared-high-priest-aaron-v1",
                    row["ai_source_position"],
                )
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(
                    LIVE_ROOT / f"{key[0]}/{key[1]:02X}.png"
                )
                self.assertEqual(pixels(expected), pixels(live))
                self.assertEqual(live.size, (16, 16))
                self.assertLessEqual(
                    len(
                        {
                            color
                            for color in flattened_image_data(live)
                            if color[3]
                        }
                    ),
                    15,
                )


if __name__ == "__main__":
    unittest.main()
