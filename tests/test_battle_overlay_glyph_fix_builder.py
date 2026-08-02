import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_battle_overlay_glyph_fix as overlay_fix


class BattleOverlayGlyphFixBuilderTests(unittest.TestCase):
    @staticmethod
    def stock_table_rom() -> bytes:
        data = bytearray(0x400000)
        for slot, old_tile, _ in overlay_fix.RELOCATIONS:
            command = builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + slot * 4
            tile_id = builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + slot * 2
            builder.put32(data, command, overlay_fix.vdp_write_command(old_tile))
            builder.put16(data, tile_id, old_tile)
        return bytes(data)

    def test_builder_separates_battle_and_preparation_cursor_tiles(self) -> None:
        self.assertEqual(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS[4], 0x07EA)
        self.assertEqual(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS[6], 0x07EC)
        self.assertEqual(builder.BYTE_UI_PREP_DYNAMIC_MAP_TILE_IDS[4], 0x07D0)
        self.assertEqual(builder.BYTE_UI_PREP_DYNAMIC_MAP_TILE_IDS[6], 0x07D1)

    def test_patch_changes_only_two_battle_destinations_and_checksum(self) -> None:
        source = self.stock_table_rom()
        output = bytearray(source)
        overlay_fix.patch(output)

        allowed = {0x18E, 0x18F}
        for slot, _, _ in overlay_fix.RELOCATIONS:
            command = builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + slot * 4
            tile_id = builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + slot * 2
            allowed.update(range(command, command + 4))
            allowed.update(range(tile_id, tile_id + 2))
        changed = {
            index
            for index, (before, after) in enumerate(zip(source, output))
            if before != after
        }
        self.assertTrue(changed <= allowed)

    def test_patch_leaves_preparation_destinations_unchanged(self) -> None:
        source = self.stock_table_rom()
        output = bytearray(source)
        overlay_fix.patch(output)
        start = builder.BYTE_UI_PREP_DYNAMIC_VDP_COMMAND_TABLE
        end = builder.BYTE_UI_PREP_DYNAMIC_TILE_ID_TABLE_LIMIT
        self.assertEqual(output[start:end], source[start:end])


if __name__ == "__main__":
    unittest.main()
