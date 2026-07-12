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
        builder.expand_rom(data)
        builder.install_blank_custom_space(data)
        glyphs = builder.install_custom_glyphs(
            data, builder.collect_chars(builder.NAME_ENTRY_GRID_CHARS)
        )
        byte_codes = builder.patch_byte_ui_strings(data)
        builder.patch_name_entry_grid(data, glyphs, byte_codes)
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
        self.assertEqual(
            words[:2],
            [
                builder.NAME_ENTRY_GRID_INDICES[
                    builder.NAME_ENTRY_GRID_CHARS.index("엘")
                ],
                builder.NAME_ENTRY_GRID_INDICES[
                    builder.NAME_ENTRY_GRID_CHARS.index("윈")
                ],
            ],
        )
        self.assertEqual(words[2:], [builder.SPACE_GLYPH] * 6)

        glyph_list = [
            int.from_bytes(
                data[
                    builder.NAME_ENTRY_GLYPH_LIST + index * 2 :
                    builder.NAME_ENTRY_GLYPH_LIST + index * 2 + 2
                ],
                "big",
            )
            for index in range(builder.NAME_ENTRY_GLYPH_COUNT)
        ]
        self.assertEqual(glyph_list[70], builder.SPACE_GLYPH)
        self.assertEqual(glyph_list[builder.SPACE_GLYPH], builder.SPACE_GLYPH)
        used_indexes = set(builder.NAME_ENTRY_GRID_INDICES)
        self.assertTrue(
            all(
                value == builder.SPACE_GLYPH
                for index, value in enumerate(glyph_list)
                if index not in used_indexes
            )
        )
        self.assertTrue(
            all(
                glyph_list[index] <= builder.NAME_ENTRY_MAX_SAFE_CUSTOM_GLYPH
                for index in builder.NAME_ENTRY_GRID_INDICES
            )
        )
        for index, char in zip(
            builder.NAME_ENTRY_GRID_INDICES, builder.NAME_ENTRY_GRID_CHARS
        ):
            self.assertEqual(glyph_list[index], glyphs[char])
            self.assertEqual(
                data[builder.NAME_ENTRY_BYTE_VALUE_TABLE + index],
                byte_codes[char],
            )
        hook = data[
            builder.NAME_ENTRY_CONFIRM_COPY_HOOK :
            builder.NAME_ENTRY_CONFIRM_COPY_HOOK
            + len(builder.NAME_ENTRY_CONFIRM_COPY_ORIGINAL)
        ]
        self.assertEqual(
            hook[:6],
            bytes.fromhex("4E B9")
            + builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE.to_bytes(4, "big"),
        )
        self.assertEqual(hook[6:], bytes.fromhex("4E 71") * 6)
        self.assertEqual(
            data[
                builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE :
                builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE
                + len(builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE_BYTES)
            ],
            builder.NAME_ENTRY_CONFIRM_COPY_ROUTINE_BYTES,
        )

    def test_name_entry_layout_decoder_and_grid_capacity(self):
        width, height, cells = builder.decode_byte_tilemap_sources(
            self.rom, builder.NAME_ENTRY_LAYOUT
        )
        self.assertEqual((width, height, len(cells)), (40, 28, 1120))
        self.assertEqual(len(builder.NAME_ENTRY_GRID_CHARS), 57)
        self.assertEqual(len(set(builder.NAME_ENTRY_GRID_CHARS)), 57)
        self.assertEqual(set(builder.BYTE_UI_GLYPH_CODES), set(range(0xA5, 0xE0)))

    def test_byte_ui_patch_preserves_ascii_and_status_graphics(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        resource_entry = builder.BYTE_UI_FONT_RESOURCE_TABLE + builder.BYTE_UI_FONT_RESOURCE_INDEX * 4
        original_offset = builder.be32(data, resource_entry) & 0x00FFFFFF
        original_tiles = builder.decompress_9dfe(data, original_offset + 1)

        codes = builder.patch_byte_ui_strings(data)
        patched_offset = builder.be32(data, resource_entry) & 0x00FFFFFF
        patched_tiles = builder.decompress_9dfe(data, patched_offset + 1)

        self.assertTrue(all(0xA5 <= code <= 0xDF for code in codes.values()))
        for code in (*range(0x00, 0xA5), *range(0xE0, 0x100)):
            start = code * 32
            self.assertEqual(
                patched_tiles[start : start + 32],
                original_tiles[start : start + 32],
                f"byte UI graphic tile 0x{code:02X} changed",
            )


if __name__ == "__main__":
    unittest.main()
