from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


def token_stream(data: bytes, offset: int) -> list[int]:
    return builder.read_word_list(data, offset)


class ItemShopResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = KO_ROM.read_bytes()

    def test_all_item_name_tokens_are_inside_loaded_glyph_window(self):
        glyphs = builder.read_word_list(
            self.data, builder.ITEM_NAME_GLYPH_LIST_RELOC_BASE
        )
        instruction = self.data[
            builder.ITEM_NAME_GLYPH_LOAD_INSTRUCTION :
            builder.ITEM_NAME_GLYPH_LOAD_INSTRUCTION + 2
        ]
        self.assertEqual(instruction[0], 0x70)
        self.assertEqual(instruction[1], len(glyphs))
        self.assertLessEqual(len(glyphs), builder.ITEM_NAME_GLYPH_LOAD_MAX)

        pointers = builder.read_pointer_table_until(
            self.data, builder.ITEM_NAME_POINTER_TABLE, 0xA1990, 0xA1B90
        )
        self.assertEqual(len(pointers), len(builder.ITEM_NAME_PATCHES))
        for item_index, pointer in enumerate(pointers, 1):
            tokens = token_stream(self.data, pointer)
            self.assertTrue(tokens, f"item {item_index} has an empty name")
            self.assertLess(
                max(tokens), len(glyphs), f"item {item_index} name exceeds loader"
            )

    def test_all_item_description_tokens_are_inside_stock_glyph_window(self):
        glyphs = builder.read_word_list(
            self.data, builder.ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE
        )
        self.assertLessEqual(
            len(glyphs), builder.ITEM_DESCRIPTION_GLYPH_LOAD_COUNT
        )

        pointers = builder.read_pointer_table_until(
            self.data, builder.ITEM_DESCRIPTION_POINTER_TABLE, 0xA1E10, 0xA2C00
        )
        self.assertEqual(len(pointers), len(builder.ITEM_DESCRIPTION_PATCHES))
        for item_index, pointer in enumerate(pointers, 1):
            tokens = token_stream(self.data, pointer)
            self.assertTrue(tokens, f"item {item_index} has an empty description")
            self.assertLess(
                max(tokens), len(glyphs),
                f"item {item_index} description exceeds loader",
            )

    def test_relocated_item_glyph_ranges_do_not_overlap(self):
        name_glyphs = builder.read_word_list(
            self.data, builder.ITEM_NAME_GLYPH_LIST_RELOC_BASE
        )
        name_end = builder.ITEM_NAME_GLYPH_LIST_RELOC_BASE + (len(name_glyphs) + 1) * 2
        self.assertLess(name_end, builder.ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE)

        description_glyphs = builder.read_word_list(
            self.data, builder.ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE
        )
        description_end = (
            builder.ITEM_DESCRIPTION_GLYPH_LIST_RELOC_BASE
            + (len(description_glyphs) + 1) * 2
        )
        self.assertLess(description_end, builder.BYTE_UI_FONT_RESOURCE_RELOC_BASE)


if __name__ == "__main__":
    unittest.main()
