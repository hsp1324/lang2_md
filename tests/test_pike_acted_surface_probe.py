import unittest
from pathlib import Path

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

    def test_reported_monk_uses_its_exact_ordinary_cache_cells(self) -> None:
        self.assertEqual(probe.MONK_CLASS_ID, 0x6C)
        self.assertEqual(builder.KOREAN_CLASS_LABELS[probe.MONK_CLASS_ID], "몽크")
        self.assertEqual(
            probe.ordinary_gray_tile_start(probe.MONK_CLASS_ID),
            0x03D8,
        )
        monk_gray = set(range(0x03D8, 0x03DC))
        self.assertTrue(
            monk_gray.isdisjoint(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        )
        monk_active = set(range(0x0370, 0x0374))
        monk_active_second = set(range(0x0470, 0x0474))
        self.assertEqual(
            probe.ORDINARY_ACTIVE_TILE_START
            + (probe.MONK_CLASS_ID - 0x62)
            * probe.ORDINARY_ACTIVE_TILES_PER_CLASS,
            0x0370,
        )
        self.assertTrue(
            monk_active.isdisjoint(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        )
        self.assertTrue(
            monk_active_second.isdisjoint(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        )

    def test_coordinate_navigation_is_deterministic(self) -> None:
        self.assertEqual(
            probe.move_keys((10, 12), (8, 15)),
            ["left", "left", "down", "down", "down"],
        )

    def test_active_sprite_linkage_counts_only_complete_plane_a_units(self) -> None:
        references = [
            {
                "tile": f"0x{0x44C + index:04X}",
                "hits": (
                    [{"plane": "plane_a"}, {"plane": "plane_a"}]
                    if index != 2
                    else [
                        {"plane": "plane_a"},
                        {"plane": "window"},
                    ]
                ),
            }
            for index in range(4)
        ]
        self.assertEqual(
            probe.complete_plane_a_sprite_occurrences(references),
            1,
        )

    def test_ui_only_tile_hits_do_not_prove_an_active_map_sprite(self) -> None:
        references = [
            {
                "tile": f"0x{0x44C + index:04X}",
                "hits": [{"plane": "window"}],
            }
            for index in range(4)
        ]
        self.assertEqual(
            probe.complete_plane_a_sprite_occurrences(references),
            0,
        )

    def test_external_release_rom_path_remains_reportable(self) -> None:
        external = Path("/mnt/c/example/release.md")
        self.assertEqual(probe.relative(external), str(external))


if __name__ == "__main__":
    unittest.main()
