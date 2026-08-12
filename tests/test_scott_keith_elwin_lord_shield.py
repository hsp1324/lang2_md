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


TARGETS = ((4, 0x04), (6, 0x04), (7, 0x04))


class SherryScottKeithAaronLordTests(unittest.TestCase):
    def test_retained_aaron_equipment_identity_and_closure_are_live(self) -> None:
        document = manifest()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        for key in TARGETS:
            with self.subTest(commander_id=key[0]):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertTrue(source_path.is_file())
                self.assertIn(
                    "shared-sherry-scott-keith-lord-aaron-lord-v1",
                    str(source_path),
                )
                row = manifest_row(document, *key)
                self.assertIn("최신 아론 사용자 편집 로드", row["ai_source_kind"])
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(LIVE_ROOT / f"{key[0]}/04.png")
                self.assertEqual(pixels(expected), pixels(live))

    def test_current_override_precedence_is_explicit(self) -> None:
        document = manifest()
        overrides = design_overrides()
        for key in ((4, 0x04), (6, 0x04)):
            row = manifest_row(document, *key)
            self.assertTrue(row["design_override"])
            self.assertEqual(row["design_revision"], overrides[key]["revision"])
            self.assertFalse(row["design_override_superseded"])
        keith = manifest_row(document, 7, 0x04)
        self.assertFalse(keith["design_override"])
        self.assertFalse(keith["design_override_superseded"])

    def test_character_color_roles_remain_distinct(self) -> None:
        sherry = set(flattened_image_data(rgba(LIVE_ROOT / "4/04.png")))
        scott = set(flattened_image_data(rgba(LIVE_ROOT / "6/04.png")))
        keith = set(flattened_image_data(rgba(LIVE_ROOT / "7/04.png")))
        self.assertTrue(
            {(0, 109, 146, 255), (109, 219, 255, 255)}.issubset(sherry)
        )
        self.assertTrue(
            {(36, 182, 36, 255), (36, 219, 36, 255)}.issubset(scott)
        )
        self.assertTrue(
            {(73, 109, 255, 255), (109, 219, 255, 255)}.issubset(keith)
        )


if __name__ == "__main__":
    unittest.main()
