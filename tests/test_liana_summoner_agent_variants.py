from __future__ import annotations

import unittest

from tools.build_ai_class_sprite_assets import (
    ASSET_VERSION,
    SHARED_CLASS_TEMPLATE_SOURCES,
    SHARED_LIANA_SUMMONER_AGENT_SOURCE_KEYS,
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


KEYS = {
    (2, 0x25),
    (2, 0x26),
    (2, 0x28),
    (3, 0x25),
    (3, 0x26),
    (3, 0x28),
}


class LianaSummonerAgentVariantTests(unittest.TestCase):
    def test_retained_full_sprite_sources_and_overrides_are_live(self) -> None:
        document = manifest()
        self.assertEqual(document["asset_version"], ASSET_VERSION)
        self.assertEqual(SHARED_LIANA_SUMMONER_AGENT_SOURCE_KEYS, KEYS)
        palettes = []
        for key in sorted(KEYS):
            with self.subTest(key=key):
                source_path, _ = SHARED_CLASS_TEMPLATE_SOURCES[key]
                self.assertTrue(source_path.is_file())
                self.assertIn(
                    "shared-liana-summoner-agent-v1", str(source_path)
                )
                row = manifest_row(document, *key)
                self.assertEqual(
                    row["identity_lock_transparency_mode"],
                    "approved_full_sprite_template",
                )
                self.assertIn(
                    "shared-liana-summoner-agent-v1",
                    row["ai_source_position"],
                )
                expected = compose_untranslated_shared_source(
                    key, document=document
                )
                live = rgba(
                    LIVE_ROOT / f"{key[0]}/{key[1]:02X}.png"
                )
                self.assertEqual(pixels(expected), pixels(live))
                colors = {
                    color
                    for color in flattened_image_data(live)
                    if color[3]
                }
                self.assertLessEqual(len(colors), 15)
                self.assertNotIn((0, 0, 0, 255), colors)
                self.assertNotIn((255, 0, 255, 255), colors)
                palettes.append(colors)
        self.assertEqual(len({frozenset(colors) for colors in palettes}), 6)

    def test_twin_class_geometry_matches_without_collapsing_classes(self) -> None:
        alpha_by_key = {
            key: tuple(
                color[3]
                for color in flattened_image_data(
                    rgba(LIVE_ROOT / f"{key[0]}/{key[1]:02X}.png")
                )
            )
            for key in KEYS
        }
        for class_id in (0x25, 0x26, 0x28):
            source_liana = rgba(
                SHARED_CLASS_TEMPLATE_SOURCES[(2, class_id)][0]
            )
            source_lana = rgba(
                SHARED_CLASS_TEMPLATE_SOURCES[(3, class_id)][0]
            )
            self.assertEqual(
                tuple(
                    color[3]
                    for color in flattened_image_data(source_liana)
                ),
                tuple(
                    color[3]
                    for color in flattened_image_data(source_lana)
                ),
            )
            # Identity restoration and closure add at most one target-specific
            # opaque boundary pixel to the otherwise identical twin geometry.
            self.assertLessEqual(
                sum(
                    left != right
                    for left, right in zip(
                        alpha_by_key[(2, class_id)],
                        alpha_by_key[(3, class_id)],
                    )
                ),
                1,
            )
        self.assertGreaterEqual(
            sum(
                left != right
                for left, right in zip(
                    alpha_by_key[(2, 0x25)], alpha_by_key[(2, 0x28)]
                )
            ),
            5,
        )

    def test_agents_and_zarvera_keep_distinct_color_roles(self) -> None:
        liana_agent = set(
            flattened_image_data(rgba(LIVE_ROOT / "2/25.png"))
        )
        liana_summoner = set(
            flattened_image_data(rgba(LIVE_ROOT / "2/28.png"))
        )
        lana_agent = set(
            flattened_image_data(rgba(LIVE_ROOT / "3/25.png"))
        )
        lana_summoner = set(
            flattened_image_data(rgba(LIVE_ROOT / "3/28.png"))
        )
        lana_zarvera = set(
            flattened_image_data(rgba(LIVE_ROOT / "3/26.png"))
        )
        self.assertIn((146, 0, 73, 255), liana_agent)
        self.assertNotIn((146, 0, 73, 255), liana_summoner)
        self.assertIn((0, 146, 146, 255), lana_agent)
        self.assertNotIn((0, 146, 146, 255), lana_summoner)
        self.assertIn((73, 109, 255, 255), lana_zarvera)
        self.assertIn((109, 219, 255, 255), lana_zarvera)
        self.assertNotIn((0, 146, 146, 255), lana_zarvera)


if __name__ == "__main__":
    unittest.main()
