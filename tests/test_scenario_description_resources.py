from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]


class ScenarioDescriptionResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = (ROOT / builder.OUT_ROM).read_bytes()

    def assert_packed_word_lists(self, pointers, limit):
        ends = []
        for pointer in pointers:
            values = builder.read_word_list(self.rom, pointer)
            self.assertTrue(values)
            ends.append(pointer + (len(values) + 1) * 2)
        self.assertEqual(ends[:-1], pointers[1:])
        self.assertLessEqual(ends[-1], limit)

    def test_all_glyph_lists_are_relocated_before_token_storage(self):
        pointers = [
            builder.be32(
                self.rom,
                builder.SCENARIO_GLYPH_LIST_TABLE + index * 4,
            )
            for index in range(31)
        ]
        self.assertEqual(pointers, sorted(pointers))
        self.assertTrue(
            all(
                builder.SCENARIO_GLYPH_LIST_RELOC_BASE
                <= pointer
                < builder.SCENARIO_GLYPH_LIST_RELOC_LIMIT
                for pointer in pointers
            )
        )
        self.assert_packed_word_lists(pointers, builder.SCENARIO_GLYPH_LIST_RELOC_LIMIT)

    def test_all_description_tokens_are_relocated_and_terminated(self):
        pointers = [
            builder.be32(self.rom, builder.SCENARIO_POINTER_TABLE + index * 4)
            for index in range(31)
        ]
        self.assertEqual(pointers, sorted(pointers))
        self.assertTrue(
            all(
                builder.SCENARIO_TOKEN_RELOC_BASE
                <= pointer
                < builder.SCENARIO_TOKEN_RELOC_LIMIT
                for pointer in pointers
            )
        )
        self.assert_packed_word_lists(pointers, builder.SCENARIO_TOKEN_RELOC_LIMIT)


if __name__ == "__main__":
    unittest.main()
