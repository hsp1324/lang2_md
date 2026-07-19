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
        self.assertGreater(len(glyphs), builder.ITEM_NAME_GLYPH_PRIMARY_COUNT)
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

    def test_item_name_vram_load_is_split_before_the_icon_bank(self):
        glyphs = builder.read_word_list(
            self.data, builder.ITEM_NAME_GLYPH_LIST_RELOC_BASE
        )
        overflow_count = len(glyphs) - builder.ITEM_NAME_GLYPH_PRIMARY_COUNT
        self.assertGreater(overflow_count, 0)
        self.assertLessEqual(overflow_count, builder.ITEM_NAME_OVERFLOW_CAPACITY)
        self.assertEqual(builder.ITEM_NAME_OVERFLOW_VRAM_LIMIT, 0xC000)

        hook_end = (
            builder.ITEM_NAME_GLYPH_LOAD_HOOK
            + len(builder.ITEM_NAME_GLYPH_LOAD_HOOK_ORIGINAL)
        )
        expected_hook = (
            bytes.fromhex("4E B9")
            + builder.ITEM_NAME_GLYPH_LOAD_ROUTINE.to_bytes(4, "big")
            + bytes.fromhex("4E 71") * 7
        )
        self.assertEqual(
            self.data[builder.ITEM_NAME_GLYPH_LOAD_HOOK:hook_end], expected_hook
        )
        expected_routine = builder._build_item_name_glyph_load_routine(len(glyphs))
        self.assertEqual(
            self.data[
                builder.ITEM_NAME_GLYPH_LOAD_ROUTINE :
                builder.ITEM_NAME_GLYPH_LOAD_ROUTINE + len(expected_routine)
            ],
            expected_routine,
        )

    def test_shop_item_renderers_select_the_overflow_vram_bank(self):
        popup_hook_end = (
            builder.ITEM_NAME_POPUP_BUILD_HOOK
            + len(builder.ITEM_NAME_POPUP_BUILD_HOOK_ORIGINAL)
        )
        self.assertEqual(
            self.data[builder.ITEM_NAME_POPUP_BUILD_HOOK:popup_hook_end],
            bytes.fromhex("4E F9")
            + builder.ITEM_NAME_POPUP_BUILD_ROUTINE.to_bytes(4, "big"),
        )
        popup_routine = builder._build_item_name_popup_stream_routine()
        self.assertEqual(
            self.data[
                builder.ITEM_NAME_POPUP_BUILD_ROUTINE :
                builder.ITEM_NAME_POPUP_BUILD_ROUTINE + len(popup_routine)
            ],
            popup_routine,
        )

        for hook, terminator, store, routine in builder.ITEM_NAME_LIST_RENDER_HOOKS:
            self.assertEqual(
                self.data[hook : hook + len(builder.ITEM_NAME_LIST_RENDER_HOOK_ORIGINAL)],
                bytes.fromhex("4E F9") + routine.to_bytes(4, "big"),
            )
            payload = builder._build_item_name_list_render_routine(terminator, store)
            self.assertEqual(self.data[routine : routine + len(payload)], payload)

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

    def test_item_descriptions_remain_aligned_with_original_ids(self):
        descriptions = builder.ITEM_DESCRIPTION_PATCHES
        self.assertEqual(len(descriptions), 37)
        self.assertIn("암흑의 마검", descriptions[13])
        self.assertIn("사거리1-3", descriptions[14])
        self.assertIn("사거리1-6", descriptions[15])
        self.assertIn("마법대미지+2", descriptions[33])
        self.assertIn("DF+1", descriptions[34])
        self.assertIn("A보정+2 D보정+2", descriptions[35])
        self.assertIn("마법저항+15", descriptions[36])

    def test_item_descriptions_fit_four_runtime_rows_before_price(self):
        for item_id, description in enumerate(builder.ITEM_DESCRIPTION_PATCHES, 1):
            lines = []
            for paragraph in description.splitlines():
                lines.extend(
                    builder.wrap_korean(
                        paragraph, builder.ITEM_DESCRIPTION_COLUMNS
                    )
                )
            self.assertLessEqual(
                len(lines),
                builder.ITEM_DESCRIPTION_TEXT_ROWS,
                f"item {item_id} description reaches the price row: {lines!r}",
            )


if __name__ == "__main__":
    unittest.main()
