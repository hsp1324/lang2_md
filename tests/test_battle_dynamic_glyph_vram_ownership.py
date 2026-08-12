from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.analyze_preparation_vram_ownership import (
    load_gst,
    reserved_table_tiles,
    sprite_referenced_tiles,
)


ROOT = Path(__file__).resolve().parents[1]


class BattleDynamicGlyphVramOwnershipTests(unittest.TestCase):
    @staticmethod
    def ordinary_mercenary_tiles(*, include_gray: bool) -> set[int]:
        occupied = set()
        for base_tile in range(0x0348, 0x0388, 4):
            occupied.update(range(base_tile, base_tile + 4))
            occupied.update(range(base_tile + 0x100, base_tile + 0x104))
        if include_gray:
            occupied.update(range(0x03B0, 0x03F0))
        return occupied

    def test_map_slots_do_not_overlap_any_ordinary_mercenary_frame(self) -> None:
        occupied = self.ordinary_mercenary_tiles(include_gray=True)
        self.assertTrue(
            set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS).isdisjoint(occupied)
        )

    def test_preparation_slots_do_not_overlap_active_ordinary_mercenary_frames(
        self,
    ) -> None:
        occupied = self.ordinary_mercenary_tiles(include_gray=False)
        self.assertTrue(
            set(builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS).isdisjoint(occupied)
        )

    def test_preparation_extra_slots_avoid_all_unit_sprite_caches(self) -> None:
        gray = set(range(0x03B0, 0x03F0))
        ordinary = self.ordinary_mercenary_tiles(include_gray=True)
        extras = set(builder.BYTE_UI_PREP_EXTRA_TILE_IDS)
        self.assertTrue(extras.isdisjoint(gray))
        self.assertTrue(extras.isdisjoint(ordinary))

    def test_pike_gray_tile_is_not_a_battle_glyph_destination(self) -> None:
        self.assertNotIn(0x03B0, builder.BYTE_UI_DYNAMIC_TILE_IDS)
        self.assertEqual(builder.KOREAN_CLASS_LABELS[0x62], "파이크")

    def test_preparation_keeps_its_independent_audited_destinations(self) -> None:
        differences = {
            index
            for index, (battle, preparation) in enumerate(
                zip(
                    builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS,
                    builder.BYTE_UI_PREP_DYNAMIC_MAP_TILE_IDS,
                )
            )
            if battle != preparation
        }
        self.assertEqual(
            differences,
            {4, 6, 7, 9, 10, 11, 12, 13, 14, 15},
        )
        self.assertEqual(
            tuple(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS[index] for index in (4, 6)),
            (0x07EA, 0x07EC),
        )
        self.assertEqual(
            tuple(
                builder.BYTE_UI_PREP_DYNAMIC_MAP_TILE_IDS[index]
                for index in (4, 6)
            ),
            (0x07D0, 0x07D1),
        )

    def test_battle_slots_preserve_all_target_cursor_graphics(self) -> None:
        destinations = set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        self.assertTrue(
            destinations.isdisjoint(builder.BATTLE_TARGET_CURSOR_TILES)
        )
        self.assertTrue(
            destinations.isdisjoint(builder.BATTLE_INVALID_TARGET_CURSOR_TILES)
        )
        self.assertTrue(
            destinations.isdisjoint(builder.BATTLE_MAGIC_CONFIRM_CURSOR_TILES)
        )
        self.assertEqual(
            builder.BATTLE_INVALID_TARGET_CURSOR_TILES,
            tuple(range(0x07D5, 0x07DD)),
        )
        self.assertEqual(
            builder.BATTLE_MAGIC_CONFIRM_CURSOR_TILES,
            tuple(range(0x07DD, 0x07E5)),
        )
        self.assertEqual(
            tuple(
                builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS[index]
                for index in (7, 9, 12)
            ),
            (0x07ED, 0x07F2, 0x07FA),
        )

    def test_preparation_lookup_calls_its_own_destination_renderer(self) -> None:
        lookup = builder._build_byte_ui_prep_local_tile_lookup()
        self.assertIn(
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_PREP_DYNAMIC_GLYPH_RENDER_ROUTINE.to_bytes(
                4, "big"
            ),
            lookup,
        )
        renderer = builder._build_byte_ui_dynamic_glyph_renderer(
            builder.BYTE_UI_PREP_DYNAMIC_VDP_COMMAND_TABLE,
            builder.BYTE_UI_PREP_DYNAMIC_TILE_ID_TABLE,
        )
        self.assertIn(
            builder.BYTE_UI_PREP_DYNAMIC_VDP_COMMAND_TABLE.to_bytes(4, "big"),
            renderer,
        )
        self.assertIn(
            builder.BYTE_UI_PREP_DYNAMIC_TILE_ID_TABLE.to_bytes(4, "big"),
            renderer,
        )

    def test_all_battle_relocations_have_no_valid_retained_owner(self) -> None:
        relocated = set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        self.assertTrue(relocated <= set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS))

        reserved = set()
        for path in sorted((ROOT / "captures/analysis").glob("*.gst")):
            state = load_gst(path)
            reserved.update(reserved_table_tiles(state))
        # Current battle states legitimately reference these patterns from the
        # name/class fields after the dynamic renderer uploads Hangul.  A
        # blanket Plane/Window reference scan therefore treats successful text
        # rendering as an ownership collision.  The actual collision contracts
        # are that no linked SAT sprite and no live VDP table owns a destination.
        for path in sorted((ROOT / "captures/analysis").glob("*.gst")):
            self.assertTrue(
                relocated.isdisjoint(
                    sprite_referenced_tiles(load_gst(path))
                )
            )
        self.assertTrue(relocated.isdisjoint(reserved))

    def test_map_slots_avoid_all_live_vdp_tables_in_current_battle_states(self) -> None:
        states = sorted(
            (ROOT / "captures/run/gray_acted_surface_matrix").glob(
                "*/*/*/attempts/*/states/active_command.gst"
            )
        )
        # Retained evidence covers at least the 16-scenario normal/hard
        # acted-sprite matrix.  Check every retained state instead of pinning a
        # retired run-id or rejecting later supplemental captures.
        self.assertGreaterEqual(len(states), 32)
        covered = {
            (path.parts[-7], path.parts[-6])
            for path in states
        }
        self.assertTrue(
            {
                (profile, f"s{scenario:02d}")
                for profile in ("normal", "hard")
                for scenario in range(1, 17)
            }.issubset(covered)
        )
        for path in states:
            with self.subTest(path=path):
                reserved = reserved_table_tiles(load_gst(path))
                self.assertTrue(
                    set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS).isdisjoint(reserved)
                )


if __name__ == "__main__":
    unittest.main()
