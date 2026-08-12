from collections import defaultdict
from pathlib import Path
import unittest

from PIL import Image

from scripts import build_korean_jp_probe as builder
from tools.pillow_compat import flattened_image_data


class AiClassPaletteRoleTests(unittest.TestCase):
    def reviewed_assets(self):
        for commander_id, class_id, _ in builder.AI_CLASS_MAP_SPRITE_SPECS:
            path = (
                Path(builder.AI_CLASS_MAP_SPRITE_ASSET_ROOT)
                / str(commander_id)
                / f"{class_id:02X}.png"
            )
            image = Image.open(path).convert("RGBA")
            colors = {
                color
                for color in flattened_image_data(image)
                if color[3] >= 128
            }
            yield commander_id, class_id, image, colors

    def test_reviewed_colours_stay_inside_their_semantic_ramp(self) -> None:
        failures = []
        for commander_id, class_id, image, colors in self.reviewed_assets():
            overrides = builder.ai_class_map_palette_index_overrides(image)
            for color in colors:
                family = builder._ai_class_map_color_family(color)
                if (
                    overrides[color]
                    not in builder.AI_CLASS_MAP_SEMANTIC_PALETTE_RAMPS[family]
                ):
                    failures.append(
                        (commander_id, class_id, color, overrides[color])
                    )
        self.assertEqual(failures, [])

    def test_different_semantic_families_never_collapse_together(self) -> None:
        failures = []
        for commander_id, class_id, image, colors in self.reviewed_assets():
            overrides = builder.ai_class_map_palette_index_overrides(image)
            families_by_index = defaultdict(set)
            for color in colors:
                families_by_index[overrides[color]].add(
                    builder._ai_class_map_color_family(color)
                )
            for palette_index, families in families_by_index.items():
                if len(families) > 1:
                    failures.append(
                        (commander_id, class_id, palette_index, families)
                    )
        self.assertEqual(failures, [])

    def test_every_available_family_shade_is_used_before_collapsing(self) -> None:
        failures = []
        for commander_id, class_id, image, colors in self.reviewed_assets():
            overrides = builder.ai_class_map_palette_index_overrides(image)
            colors_by_family = defaultdict(set)
            for color in colors:
                colors_by_family[
                    builder._ai_class_map_color_family(color)
                ].add(color)
            for family, family_colors in colors_by_family.items():
                used_indexes = {
                    overrides[color]
                    for color in family_colors
                }
                expected_count = min(
                    len(family_colors),
                    len(builder.AI_CLASS_MAP_SEMANTIC_PALETTE_RAMPS[family]),
                )
                if len(used_indexes) != expected_count:
                    failures.append(
                        (
                            commander_id,
                            class_id,
                            family,
                            expected_count,
                            used_indexes,
                        )
                    )
        self.assertEqual(failures, [])

    def test_exact_live_palette_colours_keep_their_index(self) -> None:
        failures = []
        for commander_id, class_id, image, colors in self.reviewed_assets():
            overrides = builder.ai_class_map_palette_index_overrides(image)
            for color, expected_index in (
                builder.AI_CLASS_MAP_PALETTE_EXACT_INDEX.items()
            ):
                if color in colors and overrides[color] != expected_index:
                    failures.append(
                        (
                            commander_id,
                            class_id,
                            color,
                            expected_index,
                            overrides[color],
                        )
                    )
        self.assertEqual(failures, [])

    def test_lester_serpent_lord_keeps_blue_and_two_purple_roles(self) -> None:
        path = (
            Path(builder.AI_CLASS_MAP_SPRITE_ASSET_ROOT)
            / "9"
            / "1F.png"
        )
        overrides = builder.ai_class_map_palette_index_overrides(
            Image.open(path)
        )
        blue = overrides[(73, 109, 255, 255)]
        deep_purple = overrides[(109, 36, 219, 255)]
        pale_purple = overrides[(182, 109, 255, 255)]
        self.assertEqual((blue, deep_purple, pale_purple), (0x4, 0xE, 0xD))
        self.assertEqual(len({blue, deep_purple, pale_purple}), 3)

    def test_magic_confirmation_cursor_has_a_private_battle_range(self) -> None:
        self.assertTrue(
            set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS).isdisjoint(
                builder.BATTLE_MAGIC_CONFIRM_CURSOR_TILES
            )
        )


if __name__ == "__main__":
    unittest.main()
