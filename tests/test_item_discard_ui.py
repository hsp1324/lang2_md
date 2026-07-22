from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class ItemDiscardUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

    @staticmethod
    def words(data: bytes, offset: int, count: int) -> tuple[int, ...]:
        return tuple(
            builder.be16(data, offset + index * 2) for index in range(count)
        )

    def test_original_notice_and_selection_records_are_locked(self):
        self.assertEqual(
            builder.be32(self.japanese, builder.ITEM_DISCARD_NOTICE_GLYPH_POINTER),
            builder.ITEM_DISCARD_NOTICE_GLYPH_POINTER_SOURCE,
        )
        self.assertEqual(
            builder.be32(self.japanese, builder.ITEM_DISCARD_NOTICE_TOKEN_POINTER),
            builder.ITEM_DISCARD_NOTICE_TOKEN_POINTER_SOURCE,
        )
        self.assertEqual(
            self.words(
                self.japanese,
                builder.ITEM_DISCARD_NOTICE_GLYPH_LIST,
                len(builder.ITEM_DISCARD_NOTICE_GLYPH_SOURCE),
            ),
            builder.ITEM_DISCARD_NOTICE_GLYPH_SOURCE,
        )
        self.assertEqual(
            self.words(
                self.japanese,
                builder.ITEM_DISCARD_NOTICE_TOKEN_STREAM,
                len(builder.ITEM_DISCARD_NOTICE_SOURCE_TOKENS),
            ),
            builder.ITEM_DISCARD_NOTICE_SOURCE_TOKENS,
        )
        self.assertEqual(
            self.words(
                self.japanese,
                builder.SHOP_ITEM_SELECTION_TOKEN_STREAM,
                len(builder.SHOP_ITEM_SELECTION_SOURCE_TOKENS),
            ),
            builder.SHOP_ITEM_SELECTION_SOURCE_TOKENS,
        )

    def test_notice_is_relocated_with_spaces_preserved(self):
        expected_chars = builder.collect_chars(*builder.ITEM_DISCARD_NOTICE_LINES)
        self.assertEqual(len(expected_chars), 17)
        self.assertEqual(
            builder.be32(self.korean, builder.ITEM_DISCARD_NOTICE_GLYPH_POINTER),
            builder.ITEM_DISCARD_NOTICE_RELOC_GLYPH_LIST,
        )
        self.assertEqual(
            builder.be32(self.korean, builder.ITEM_DISCARD_NOTICE_TOKEN_POINTER),
            builder.ITEM_DISCARD_NOTICE_RELOC_TOKEN_STREAM,
        )
        glyphs = builder.read_word_list(
            self.korean, builder.ITEM_DISCARD_NOTICE_RELOC_GLYPH_LIST
        )
        self.assertEqual(glyphs[0], builder.SPACE_GLYPH)
        self.assertEqual(len(glyphs), len(expected_chars) + 1)
        self.assertEqual(len(set(glyphs)), len(glyphs))
        self.assertTrue(
            all(
                any(
                    start <= value <= end
                    for start, end in builder.CUSTOM_GLYPH_RANGES
                )
                and value not in builder.CUSTOM_GLYPH_RESERVED
                for value in glyphs[1:]
            )
        )
        tokens = builder.read_word_list(
            self.korean, builder.ITEM_DISCARD_NOTICE_RELOC_TOKEN_STREAM
        )
        self.assertEqual(tokens[:3], [0xFFFB, 1, 1])
        self.assertEqual(tokens.count(0), 3)
        decoded = []
        for token in tokens[3:]:
            if token == 0xFFFE:
                decoded.append("\n")
            else:
                decoded.append(" " if token == 0 else expected_chars[token - 1])
        self.assertEqual(
            "".join(decoded),
            "\n".join(builder.ITEM_DISCARD_NOTICE_LINES) + "\n",
        )

    def test_shop_item_selection_prompt_preserves_shop_sell_slots(self):
        glyphs = builder.read_word_list(
            self.korean, builder.SHOP_SELL_GLYPH_LIST
        )
        self.assertEqual(len(glyphs), 14)
        tokens = self.words(
            self.korean,
            builder.SHOP_ITEM_SELECTION_TOKEN_STREAM,
            len(builder.SHOP_ITEM_SELECTION_SOURCE_TOKENS),
        )
        self.assertEqual(
            tokens[5:15],
            (0, 1, 2, 4, 3, 5, 6, 7, 8, 9),
        )
        self.assertEqual(tokens[15:], (0xFFFF,) * 5)
        sell_tokens = self.words(
            self.korean, builder.SHOP_SELL_TITLE_TOKEN_STREAM, 6
        )
        self.assertEqual(sell_tokens, (0, 1, 2, 3, 11, 12))


if __name__ == "__main__":
    unittest.main()
