from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_text_font_analyzer import read_word_list


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class NameEntryResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = JP_ROM.read_bytes()

    def test_initialization_code_references_known_resources(self):
        expected = {
            0x02ABF8: bytes.fromhex("45 F9 00 0A 38 E0"),
            0x02AC0E: bytes.fromhex("41 F9 00 0A 37 BE"),
            0x02AC22: bytes.fromhex("41 F9 00 0A 38 A6"),
            0x02AC3E: bytes.fromhex("41 F9 00 0A 3B 0C"),
            0x02B4BE: bytes.fromhex("45 F9 00 0A 3B B0"),
            0x02B67A: bytes.fromhex("41 F9 00 0A 3B B0"),
            0x02B68E: bytes.fromhex("41 F9 00 0A 3B C0"),
        }
        for offset, instruction in expected.items():
            self.assertEqual(self.rom[offset : offset + len(instruction)], instruction)

    def test_name_entry_resource_lengths(self):
        self.assertEqual(len(read_word_list(self.rom, 0x0A3BB0)), 7)
        self.assertEqual(len(read_word_list(self.rom, 0x0A3C5A)), 32)
        self.assertEqual(builder.NAME_ENTRY_DEFAULT_COPY_WORDS, 8)
        self.assertEqual(builder.NAME_ENTRY_DEFAULT_WORDS, 5)

    def test_default_buffer_source_is_validated(self):
        data = bytearray(self.rom)
        builder.validate_name_entry_default_source(data)
        data[builder.NAME_ENTRY_DEFAULT_WORD_OFFSET + 4] ^= 1
        with self.assertRaisesRegex(ValueError, "name-entry default source changed"):
            builder.validate_name_entry_default_source(data)

    def test_default_patch_blanks_full_copied_buffer(self):
        data = bytearray(self.rom)
        builder.patch_name_entry_reused_glyphs(data)
        words = [
            int.from_bytes(
                data[
                    builder.NAME_ENTRY_DEFAULT_WORD_OFFSET + index * 2 :
                    builder.NAME_ENTRY_DEFAULT_WORD_OFFSET + index * 2 + 2
                ],
                "big",
            )
            for index in range(builder.NAME_ENTRY_DEFAULT_COPY_WORDS)
        ]
        self.assertEqual(words[:2], [0x0003, 0x002A])
        self.assertEqual(words[2:], [builder.SPACE_GLYPH] * 6)


if __name__ == "__main__":
    unittest.main()
