from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class ConditionResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()

    def test_all_condition_records_have_valid_local_tokens(self):
        for index, lines in enumerate(builder.CONDITION_SCREENS):
            self.assertLessEqual(len(lines), 7)
            self.assertTrue(all(len(line) <= 15 or line in ("승리조건", "패배조건") for line in lines))

            glyph_pointer = builder.be32(
                self.ko, builder.CONDITION_GLYPH_LIST_TABLE + index * 4
            )
            original_glyph_pointer = builder.be32(
                self.jp, builder.CONDITION_GLYPH_LIST_TABLE + index * 4
            )
            self.assertEqual(glyph_pointer, original_glyph_pointer)

            glyphs = builder.read_word_list(self.ko, glyph_pointer)
            self.assertGreater(len(glyphs), 0)
            token_pointer = builder.be32(
                self.ko, builder.CONDITION_POINTER_TABLE + index * 4
            )
            tokens = [
                builder.be16(self.ko, token_pointer + position * 2)
                for position in range(113)
            ]
            self.assertEqual(tokens[-1], 0xFFFF)
            self.assertEqual(len(tokens[:-1]), 7 * 16)
            self.assertTrue(all(token < len(glyphs) for token in tokens[:-1]))

    def test_final_shared_record_is_untouched(self):
        index = 31
        glyph_pointer_offset = builder.CONDITION_GLYPH_LIST_TABLE + index * 4
        token_pointer_offset = builder.CONDITION_POINTER_TABLE + index * 4
        self.assertEqual(
            self.ko[glyph_pointer_offset:glyph_pointer_offset + 4],
            self.jp[glyph_pointer_offset:glyph_pointer_offset + 4],
        )
        glyph_pointer = builder.be32(self.jp, glyph_pointer_offset)
        glyph_capacity = builder.glyph_list_capacity_words(
            self.jp, builder.CONDITION_GLYPH_LIST_TABLE, index, 32
        )
        self.assertEqual(
            self.ko[glyph_pointer:glyph_pointer + glyph_capacity * 2],
            self.jp[glyph_pointer:glyph_pointer + glyph_capacity * 2],
        )
        token_pointer = builder.be32(self.jp, token_pointer_offset)
        token_capacity = 113
        self.assertEqual(
            self.ko[token_pointer:token_pointer + token_capacity * 2],
            self.jp[token_pointer:token_pointer + token_capacity * 2],
        )

    def test_original_turn_limits_and_long_objectives_are_preserved(self):
        self.assertIn("22턴", " ".join(builder.CONDITION_SCREENS[4]))
        self.assertIn("23턴", " ".join(builder.CONDITION_SCREENS[7]))
        self.assertIn("23턴", " ".join(builder.CONDITION_SCREENS[18]))
        self.assertEqual(len(builder.CONDITION_SCREENS[13]), 7)
        self.assertIn("엘윈·제시카·쉐리", builder.CONDITION_SCREENS[13][1])
        self.assertIn("로드 소지자", builder.CONDITION_SCREENS[22][1])
        self.assertIn("로드 탈취", builder.CONDITION_SCREENS[22][4])

if __name__ == "__main__":
    unittest.main()
