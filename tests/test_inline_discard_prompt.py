from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"

PROMPT = 0x01807E
WIDTH = 13
SOURCE = "ｽﾃﾙ ｱｲﾃﾑ ｾﾝﾀｸ".encode("cp932")
LEA = 0x01804C
LEA_BYTES = bytes.fromhex("45 F9 00 01 80 7E")
COUNT = 0x018052
COUNT_BYTES = bytes.fromhex("70 0C")


class InlineDiscardPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

    def test_japanese_source_and_fixed_count_renderer_are_locked(self):
        self.assertEqual(len(SOURCE), WIDTH)
        self.assertEqual(self.japanese[PROMPT : PROMPT + WIDTH], SOURCE)
        self.assertEqual(self.japanese[PROMPT + WIDTH], 0xFF)
        self.assertEqual(self.japanese[LEA : LEA + len(LEA_BYTES)], LEA_BYTES)
        self.assertEqual(self.japanese[COUNT : COUNT + len(COUNT_BYTES)], COUNT_BYTES)

    def test_builder_declares_the_full_inline_record(self):
        self.assertEqual(builder.INLINE_DISCARD_PROMPT_SOURCE, PROMPT)
        self.assertEqual(builder.INLINE_DISCARD_PROMPT_WIDTH, WIDTH)
        self.assertEqual(builder.INLINE_DISCARD_PROMPT_TEXT, "버릴 아이템")

    def test_korean_record_uses_full_local_tile_indexes(self):
        working = bytearray(self.japanese)
        builder.expand_rom(working)
        code_by_char = builder.patch_byte_ui_strings(working)
        index_by_char, tile_by_index = builder.build_byte_ui_local_mapping(code_by_char)
        expected = bytes(
            [index_by_char[char] for char in builder.INLINE_DISCARD_PROMPT_TEXT]
            + [index_by_char[" "]]
            * (WIDTH - len(builder.INLINE_DISCARD_PROMPT_TEXT))
        )
        self.assertEqual(
            self.korean[
                builder.INLINE_DISCARD_PROMPT_RECORD :
                builder.INLINE_DISCARD_PROMPT_RECORD + WIDTH
            ],
            expected,
        )
        self.assertTrue(
            all(tile_by_index[index] != 0xFFFF for index in expected)
        )

    def test_korean_hook_bypasses_the_original_byte_renderer(self):
        expected = bytes.fromhex("4E F9") + builder.INLINE_DISCARD_PROMPT_RENDER_ROUTINE.to_bytes(4, "big")
        self.assertEqual(self.korean[LEA : LEA + len(expected)], expected)
        routine = builder._build_inline_discard_prompt_renderer()
        self.assertEqual(
            self.korean[
                builder.INLINE_DISCARD_PROMPT_RENDER_ROUTINE :
                builder.INLINE_DISCARD_PROMPT_RENDER_ROUTINE + len(routine)
            ],
            routine,
        )


if __name__ == "__main__":
    unittest.main()
