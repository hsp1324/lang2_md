from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.analyze_preparation_vram_ownership import (
    load_gst,
    referenced_tiles,
    reserved_table_tiles,
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

    def test_preparation_only_gray_slots_are_never_battle_destinations(self) -> None:
        gray = set(range(0x03B0, 0x03F0))
        prep_gray = set(builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS) & gray
        self.assertEqual(prep_gray, set(builder.BYTE_UI_PREP_EXTRA_TILE_IDS))
        self.assertTrue(
            set(builder.BYTE_UI_DYNAMIC_TILE_IDS).isdisjoint(prep_gray)
        )

    def test_pike_gray_tile_is_not_a_battle_glyph_destination(self) -> None:
        self.assertNotIn(0x03B0, builder.BYTE_UI_DYNAMIC_TILE_IDS)
        self.assertEqual(builder.KOREAN_CLASS_LABELS[0x62], "파이크")

    def test_preparation_uses_the_audited_battle_map_destinations(self) -> None:
        self.assertEqual(
            builder.BYTE_UI_PREP_DYNAMIC_MAP_TILE_IDS,
            builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS,
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

        used = set()
        reserved = set()
        for path in sorted((ROOT / "captures/analysis").glob("*.gst")):
            state = load_gst(path)
            used.update(referenced_tiles(state))
            reserved.update(reserved_table_tiles(state))
        self.assertTrue(relocated.isdisjoint(used))
        self.assertTrue(relocated.isdisjoint(reserved))

    def test_map_slots_avoid_all_live_vdp_tables_in_current_battle_states(self) -> None:
        states = sorted(
            (ROOT / "captures/run/gray_acted_surface_matrix").glob(
                "*/*/gray-cache-full01/attempts/*/states/active_command.gst"
            )
        )
        self.assertEqual(len(states), 27)
        for path in states:
            with self.subTest(path=path):
                reserved = reserved_table_tiles(load_gst(path))
                self.assertTrue(
                    set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS).isdisjoint(reserved)
                )


if __name__ == "__main__":
    unittest.main()
