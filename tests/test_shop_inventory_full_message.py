from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class ShopInventoryFullMessageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

    def test_stock_ten_cell_message_is_locked(self):
        tokens = tuple(
            builder.be16(
                self.japanese,
                builder.SHOP_INVENTORY_FULL_TOKEN_STREAM + index * 2,
            )
            for index in range(10)
        )
        self.assertEqual(tokens, builder.SHOP_INVENTORY_FULL_SOURCE_TOKENS)
        self.assertEqual(
            builder.be16(self.japanese, builder.SHOP_INVENTORY_FULL_TOKEN_STREAM + 20),
            0xFFFF,
        )

    def test_korean_message_uses_local_shop_glyph_slots(self):
        expected = (1, 0, 1, 2, 3, 4, 5, 3, 13, 14)
        actual = tuple(
            builder.be16(
                self.korean,
                builder.SHOP_INVENTORY_FULL_TOKEN_STREAM + index * 2,
            )
            for index in range(10)
        )
        self.assertEqual(actual, expected)
        self.assertEqual(builder.SHOP_INVENTORY_FULL_MESSAGE_TEXT, "아이템 구입 불가")

    def test_inventory_full_glyph_slots_are_localized(self):
        data = bytearray(self.japanese)
        builder.expand_rom(data)
        glyph_by_char = builder.install_custom_glyphs(
            data,
            builder.collect_chars(builder.SHOP_INVENTORY_FULL_MESSAGE_TEXT),
        )
        expected = (glyph_by_char["불"], glyph_by_char["가"])
        # The production IDs belong to the complete global allocation, so
        # compare their rendered glyph bitmaps rather than the numeric IDs.
        production_ids = tuple(
            builder.be16(
                self.korean,
                builder.SHOP_INVENTORY_FULL_GLYPH_LIST + slot * 2,
            )
            for slot in (13, 14)
        )
        for expected_id, production_id in zip(expected, production_ids):
            expected_offset = builder.glyph_data_offset(expected_id)
            production_offset = builder.glyph_data_offset(production_id)
            self.assertEqual(
                data[expected_offset : expected_offset + builder.GLYPH_BYTES],
                self.korean[
                    production_offset : production_offset + builder.GLYPH_BYTES
                ],
            )


if __name__ == "__main__":
    unittest.main()
