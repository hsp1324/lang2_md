import unittest

from scripts import build_korean_jp_probe as builder
from tools import run_pike_acted_surface_probe as probe


class PikeActedSurfaceProbeTests(unittest.TestCase):
    def test_exact_reported_mercenary_is_pike(self) -> None:
        self.assertEqual(probe.PIKE_CLASS_ID, 0x62)
        self.assertEqual(builder.KOREAN_CLASS_LABELS[probe.PIKE_CLASS_ID], "파이크")

    def test_pike_gray_tiles_are_the_first_ordinary_gray_cache_entry(self) -> None:
        self.assertEqual(probe.PIKE_GRAY_TILE_START, 0x03B0)
        self.assertEqual(probe.PIKE_GRAY_TILE_COUNT, 4)
        self.assertEqual(probe.PIKE_GRAY_VRAM_START, 0x7600)
        self.assertEqual(probe.PIKE_GRAY_VRAM_BYTES, 0x80)

    def test_all_ordinary_gray_classes_fill_the_stock_cache_exactly(self) -> None:
        class_count = (
            builder.ENEMY_ORDINARY_MERCENARY_LAST_CLASS
            - builder.ENEMY_ORDINARY_MERCENARY_FIRST_CLASS
            + 1
        )
        self.assertEqual(class_count, 16)
        self.assertEqual(
            probe.ORDINARY_GRAY_TILE_START
            + class_count * probe.ORDINARY_GRAY_TILES_PER_CLASS,
            0x03F0,
        )

    def test_battle_dynamic_glyphs_cannot_overwrite_pike_gray_tiles(self) -> None:
        pike_tiles = set(
            range(
                probe.PIKE_GRAY_TILE_START,
                probe.PIKE_GRAY_TILE_START + probe.PIKE_GRAY_TILE_COUNT,
            )
        )
        self.assertTrue(
            pike_tiles.isdisjoint(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        )

    def test_coordinate_navigation_is_deterministic(self) -> None:
        self.assertEqual(
            probe.move_keys((10, 12), (8, 15)),
            ["left", "left", "down", "down", "down"],
        )


if __name__ == "__main__":
    unittest.main()
