from pathlib import Path
import unittest

from PIL import ImageFont

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

    def test_loren_second_syllable_has_legible_native_bitmap(self):
        expected_rows = (
            "###.#.#.",
            "..#.#.#.",
            "#######.",
            "#...#.#.",
            "###.#.#.",
            ".#......",
            ".######.",
            "........",
        )
        self.assertEqual(builder.BYTE_UI_TILE_BITMAP_OVERRIDES["렌"], expected_rows)
        font = ImageFont.truetype(str(ROOT / "tools/fonts/Galmuri7.ttf"), 8)
        self.assertEqual(
            builder.render_byte_ui_tile("렌", font),
            builder._encode_byte_ui_bitmap(expected_rows),
        )

    def test_byte_ui_bitmap_override_rejects_invalid_dimensions_and_pixels(self):
        with self.assertRaisesRegex(ValueError, "8x8"):
            builder._encode_byte_ui_bitmap(("........",) * 7)
        with self.assertRaisesRegex(ValueError, "only contain"):
            builder._encode_byte_ui_bitmap(("........",) * 7 + (".......x",))

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
        self.assertEqual(
            set(builder.BYTE_UI_GLYPH_CODES),
            (set(range(0xA5, 0xE0)) - {0xB0})
            | set(builder.BYTE_UI_PRIVATE_ASCII_GLYPH_CODES),
        )

    def test_byte_ui_patch_preserves_ascii_and_status_graphics(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        resource_entry = builder.BYTE_UI_FONT_RESOURCE_TABLE + builder.BYTE_UI_FONT_RESOURCE_INDEX * 4
        original_offset = builder.be32(data, resource_entry) & 0x00FFFFFF
        original_tiles = builder.decompress_9dfe(data, original_offset + 1)

        codes = builder.patch_byte_ui_strings(data)
        patched_offset = builder.be32(data, resource_entry) & 0x00FFFFFF
        patched_tiles = builder.decompress_9dfe(data, patched_offset + 1)

        self.assertTrue(
            all(
                0xA5 <= code <= 0xDF
                or code in builder.BYTE_UI_PRIVATE_ASCII_GLYPH_CODES
                or code in builder.BYTE_UI_EXT_CODE_BY_CHAR.values()
                for code in codes.values()
            )
        )
        for code in (*range(0x00, 0xA5), *range(0xE0, 0x100)):
            if code in builder.BYTE_UI_PRIVATE_ASCII_GLYPH_CODES:
                continue
            start = code * 32
            self.assertEqual(
                patched_tiles[start : start + 32],
                original_tiles[start : start + 32],
                f"byte UI graphic tile 0x{code:02X} changed",
            )
        self.assertEqual(codes["록"], 0xF6)
        self.assertNotIn(ord("I"), builder.BYTE_UI_PRIVATE_ASCII_GLYPH_CODES)
        start = 0xB0 * 32
        self.assertEqual(
            patched_tiles[start : start + 32],
            original_tiles[start : start + 32],
            "battle-result decoration tile 0xB0 changed",
        )

    def test_playable_names_use_verified_sources_and_stable_extension_codes(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        codes = builder.patch_byte_ui_strings(data)

        resource_entry = (
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.BYTE_UI_FONT_RESOURCE_INDEX * 4
        )
        font_offset = builder.be32(data, resource_entry) & 0x00FFFFFF
        font_tiles = builder.decompress_9dfe(data, font_offset + 1)
        extension_tiles = builder.decompress_9dfe(
            data, builder.BYTE_UI_EXT_RESOURCE_BASE + 1
        )
        font = ImageFont.truetype(str(ROOT / "tools/fonts/Galmuri7.ttf"), 8)

        expected_names = {
            0x061AC5: "엘윈",
            0x061ACB: "리아나",
            0x061ACF: "라나",
            0x061AD3: "쉐리",
            0x061AD8: "헤인",
            0x061ADC: "스코트",
            0x061AE1: "키스",
            0x061AE5: "아론",
            0x061AEA: "레스터",
            0x061AEF: "제시카",
        }
        for offset, text in expected_names.items():
            capacity = builder.byte_string_capacity(self.rom, offset)
            expected = bytes(codes[char] for char in text) + b"\xFF"
            self.assertEqual(data[offset : offset + len(expected)], expected)
            self.assertTrue(
                all(value == 0xFF for value in data[offset + len(expected) : offset + capacity])
            )
            for char in text:
                code = codes[char]
                expected_tile = builder.render_byte_ui_tile(char, font)
                if char in builder.BYTE_UI_EXT_CODE_BY_CHAR:
                    tile_index = code - builder.BYTE_UI_EXT_CODE_FIRST
                    actual_tile = extension_tiles[tile_index * 32 : tile_index * 32 + 32]
                else:
                    actual_tile = font_tiles[code * 32 : code * 32 + 32]
                self.assertEqual(actual_tile, expected_tile, f"wrong tile for {char!r}")
        self.assertEqual(
            {char: codes[char] for char in builder.BYTE_UI_EXT_CODE_BY_CHAR},
            builder.BYTE_UI_EXT_CODE_BY_CHAR,
        )

    def test_extended_font_resource_and_renderer_hooks_are_installed(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        builder.patch_byte_ui_strings(data)

        self.assertEqual(
            builder.be32(data, builder.BYTE_UI_RESOURCE_LOOKUP_BASE_INSTRUCTION + 2),
            builder.BYTE_UI_EXT_RESOURCE_TABLE,
        )
        self.assertEqual(
            builder.be32(
                data,
                builder.BYTE_UI_EXT_RESOURCE_TABLE
                + builder.BYTE_UI_EXT_RESOURCE_INDEX * 4,
            ),
            builder.BYTE_UI_EXT_RESOURCE_BASE,
        )
        self.assertEqual(data[builder.BYTE_UI_EXT_RESOURCE_BASE], 3)
        tiles = builder.decompress_9dfe(data, builder.BYTE_UI_EXT_RESOURCE_BASE + 1)
        self.assertEqual(len(tiles), builder.BYTE_UI_EXT_TILE_COUNT * 32)
        self.assertEqual(
            len({tiles[index * 32 : index * 32 + 32] for index in range(6)}),
            6,
        )
        for offset in builder.BYTE_UI_FONT_LOAD_CALLS:
            self.assertEqual(
                data[offset : offset + 6],
                bytes.fromhex("4E B9") + builder.BYTE_UI_FONT_LOAD_ROUTINE.to_bytes(4, "big"),
            )
        for offset in builder.BYTE_UI_PLANE_RENDER_CALLS:
            self.assertEqual(
                data[offset : offset + 6],
                bytes.fromhex("4E B9")
                + builder.BYTE_UI_PLANE_RENDER_ROUTINE.to_bytes(4, "big"),
            )
        for offset in builder.BYTE_UI_PANEL_RENDER_HOOKS:
            self.assertEqual(
                data[offset : offset + len(builder.BYTE_UI_PANEL_RENDER_ORIGINAL)],
                bytes.fromhex("4E B9")
                + builder.BYTE_UI_PANEL_RENDER_ROUTINE.to_bytes(4, "big")
                + bytes.fromhex("4E 71"),
            )
        self.assertEqual(
            data[
                builder.BYTE_UI_PREP_ROSTER_HOOK :
                builder.BYTE_UI_PREP_ROSTER_HOOK
                + len(builder.BYTE_UI_PREP_ROSTER_ORIGINAL)
            ],
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_PREP_ROSTER_ROUTINE.to_bytes(4, "big")
            + bytes.fromhex("4E 71"),
        )
        for offset in builder.BYTE_UI_WORD_RENDER_CALLS:
            self.assertEqual(
                data[offset : offset + 6],
                bytes.fromhex("4E B9") + builder.BYTE_UI_WORD_RENDER_ROUTINE.to_bytes(4, "big"),
            )
        for offset in builder.BYTE_UI_TILE_RENDER_CALLS:
            self.assertEqual(
                data[offset : offset + 6],
                bytes.fromhex("4E B9") + builder.BYTE_UI_TILE_RENDER_ROUTINE.to_bytes(4, "big"),
            )
        for offset in builder.BYTE_UI_MAP_INFO_RENDER_CALLS:
            self.assertEqual(
                data[offset : offset + 6],
                bytes.fromhex("4E B9")
                + builder.BYTE_UI_MAP_INFO_RENDER_ROUTINE.to_bytes(4, "big"),
            )
        for offset in builder.BYTE_UI_DIRECT_MAP_RENDER_CALLS:
            self.assertEqual(
                data[offset : offset + 6],
                bytes.fromhex("4E B9")
                + builder.BYTE_UI_DIRECT_MAP_RENDER_ROUTINE.to_bytes(4, "big"),
            )
        self.assertEqual(
            data[
                builder.BYTE_UI_DIRECT_MAP_RENDER_HOOK :
                builder.BYTE_UI_DIRECT_MAP_RENDER_HOOK + 6
            ],
            bytes.fromhex("4E F9")
            + builder.BYTE_UI_DIRECT_MAP_RENDER_ROUTINE.to_bytes(4, "big"),
        )
        self.assertEqual(
            data[
                builder.BYTE_UI_PREP_SELECTED_NAME_RENDER_HOOK :
                builder.BYTE_UI_PREP_SELECTED_NAME_RENDER_HOOK + 6
            ],
            bytes.fromhex("4E F9")
            + builder.BYTE_UI_PREP_SELECTED_NAME_RENDER_ROUTINE.to_bytes(4, "big"),
        )
        prep_selected_name_renderer = builder._build_byte_ui_prep_selected_name_renderer()
        self.assertTrue(prep_selected_name_renderer.endswith(bytes.fromhex("4E F9 00 02 7A 98")))
        self.assertEqual(
            data[
                builder.BYTE_UI_PREP_SELECTED_PANEL_RENDER_HOOK :
                builder.BYTE_UI_PREP_SELECTED_PANEL_RENDER_HOOK + 6
            ],
            bytes.fromhex("4E F9")
            + builder.BYTE_UI_PREP_SELECTED_PANEL_RENDER_ROUTINE.to_bytes(4, "big"),
        )
        self.assertEqual(
            data[
                builder.BYTE_UI_PREP_HIRE_CLASS_RENDER_HOOK :
                builder.BYTE_UI_PREP_HIRE_CLASS_RENDER_HOOK + 6
            ],
            bytes.fromhex("4E F9")
            + builder.BYTE_UI_PREP_HIRE_CLASS_RENDER_ROUTINE.to_bytes(4, "big"),
        )

    def test_all_name_and_class_records_use_localized_pair_encoding(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        codes = builder.patch_byte_ui_strings(data)
        index_by_char, tile_by_index = builder.build_byte_ui_local_mapping(codes)
        char_by_index = {index: char for char, index in index_by_char.items()}

        def decode(pointer):
            chars = []
            cursor = pointer
            while data[cursor] != 0xFF:
                self.assertEqual(data[cursor], builder.BYTE_UI_LOCAL_MARKER)
                chars.append(char_by_index[data[cursor + 1]])
                cursor += 2
            return "".join(chars)

        for index, expected in enumerate(builder.KOREAN_CLASS_LABELS):
            pointer = builder.be32(
                data, builder.CLASS_BYTE_POINTER_TABLE + index * 4
            )
            self.assertTrue(
                builder.BYTE_UI_CLASS_STRING_RELOC_BASE
                <= pointer
                < builder.BYTE_UI_CLASS_STRING_RELOC_LIMIT
            )
            self.assertEqual(decode(pointer), expected)
        for index in range(builder.NAME_BYTE_RECORD_COUNT):
            pointer = builder.be32(
                data, builder.NAME_BYTE_POINTER_TABLE + index * 4
            )
            self.assertTrue(
                builder.BYTE_UI_NAME_STRING_RELOC_BASE
                <= pointer
                < builder.BYTE_UI_NAME_STRING_RELOC_LIMIT
            )
            self.assertEqual(decode(pointer), builder.KOREAN_NAME_BY_ID[index])

        self.assertLessEqual(len(tile_by_index), 0x100)
        table_words = [
            builder.be16(data, builder.BYTE_UI_LOCAL_TILE_TABLE + index * 2)
            for index in range(len(tile_by_index))
        ]
        self.assertEqual(table_words, tile_by_index)

    def test_full_extension_resources_cover_each_reserved_vram_segment(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        codes = builder.patch_byte_ui_strings(data)
        index_by_char, tile_by_index = builder.build_byte_ui_local_mapping(codes)
        char_by_tile = {
            tile_by_index[index]: char for char, index in index_by_char.items()
        }
        font = ImageFont.truetype(str(ROOT / "tools/fonts/Galmuri7.ttf"), 8)

        for segment_index, (tile_start, tile_count) in enumerate(
            builder.BYTE_UI_FULL_EXT_VRAM_SEGMENTS
        ):
            resource_index = (
                builder.BYTE_UI_FULL_EXT_RESOURCE_FIRST_INDEX + segment_index
            )
            resource_pointer = builder.be32(
                data,
                builder.BYTE_UI_EXT_RESOURCE_TABLE + resource_index * 4,
            )
            tiles = builder.decompress_9dfe(data, resource_pointer + 1)
            self.assertEqual(len(tiles), tile_count * 32)
            for tile in range(tile_start, tile_start + tile_count):
                char = char_by_tile.get(tile)
                if char is None:
                    continue
                start = (tile - tile_start) * 32
                self.assertEqual(
                    tiles[start : start + 32],
                    builder.render_byte_ui_tile(char, font),
                )

    def test_full_extension_font_segments_use_queued_dma_requests(self):
        loader = builder._build_byte_ui_font_loader()
        for segment_index, (tile_start, _) in enumerate(
            builder.BYTE_UI_FULL_EXT_VRAM_SEGMENTS
        ):
            resource_index = (
                builder.BYTE_UI_FULL_EXT_RESOURCE_FIRST_INDEX + segment_index
            )
            request = 0x8000 | resource_index
            call = (
                bytes.fromhex("30 3C")
                + request.to_bytes(2, "big")
                + bytes.fromhex("32 7C")
                + (tile_start * 32).to_bytes(2, "big")
                + bytes.fromhex("4E B9 00 00 99 B2")
            )
            self.assertIn(call, loader)

    def test_loren_second_syllable_uses_runtime_stable_final_segment(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        codes = builder.patch_byte_ui_strings(data)
        index_by_char, tile_by_index = builder.build_byte_ui_local_mapping(codes)

        self.assertEqual(builder.BYTE_UI_FULL_EXT_VRAM_SEGMENTS[-1], (0x05D8, 28))
        self.assertEqual(tile_by_index[index_by_char["렌"]], 0x05E9)

    def test_map_info_renderer_restores_only_the_final_segment(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        builder.patch_byte_ui_strings(data)
        renderer = builder._build_byte_ui_map_info_renderer()
        self.assertEqual(
            renderer[:6],
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_FINAL_BANK_LOAD_ROUTINE.to_bytes(4, "big"),
        )

        loader = builder._build_byte_ui_final_bank_loader()
        segment_index = len(builder.BYTE_UI_FULL_EXT_VRAM_SEGMENTS) - 1
        tile_start, _ = builder.BYTE_UI_FULL_EXT_VRAM_SEGMENTS[segment_index]
        resource_index = builder.BYTE_UI_FULL_EXT_RESOURCE_FIRST_INDEX + segment_index
        self.assertEqual(loader[:4], bytes.fromhex("48 E7 80 40"))
        self.assertIn(
            bytes.fromhex("30 3C") + (0x8000 | resource_index).to_bytes(2, "big"),
            loader,
        )
        self.assertIn(
            bytes.fromhex("32 7C") + (tile_start * 32).to_bytes(2, "big"),
            loader,
        )
        for other_start, _ in builder.BYTE_UI_FULL_EXT_VRAM_SEGMENTS[:-1]:
            self.assertNotIn(
                bytes.fromhex("32 7C") + (other_start * 32).to_bytes(2, "big"),
                loader,
            )

    def test_extension_renderer_maps_only_escape_bytes(self):
        def mapped(value):
            return value + 0x300 if builder.BYTE_UI_EXT_CODE_FIRST <= value <= builder.BYTE_UI_EXT_CODE_LAST else value

        self.assertEqual(mapped(0xEF), 0xEF)
        self.assertEqual(mapped(0xF0), 0x3F0)
        self.assertEqual(mapped(0xF5), 0x3F5)
        self.assertEqual(mapped(0xFE), 0x3FE)

    def test_battle_names_use_event_stable_extension_tiles(self):
        expected = {"소": 0x3AD, "서": 0x3AE, "러": 0x3AF, "록": 0x5D8}
        self.assertEqual(builder.BYTE_UI_BATTLE_STABLE_FULL_EXT_TILE_BY_CHAR, expected)
        data = bytearray(self.rom)
        builder.expand_rom(data)
        codes = builder.patch_byte_ui_strings(data)
        index_by_char, tile_by_index = builder.build_byte_ui_local_mapping(codes)
        self.assertEqual(codes["소"], ord("Q"))
        self.assertEqual(
            [tile_by_index[index_by_char[char]] for char in "소서러"],
            [0x3AD, 0x3AE, 0x3AF],
        )

    def test_direct_map_renderer_preserves_full_extension_tile_ids(self):
        renderer = builder._build_byte_ui_direct_map_renderer()
        byte_mask = bytes.fromhex("02 41 00 FF")

        # The one remaining mask bounds the class/name table index. Localized
        # tile words returned by the lookup must reach VRAM without truncation.
        self.assertEqual(renderer.count(byte_mask), 1)
        self.assertNotIn(
            bytes.fromhex("02 41 00 FF D4 FC 00 02 35 81 00 00"),
            renderer,
        )
        self.assertIn(bytes.fromhex("D4 FC 00 02 35 81 00 00"), renderer)

    def test_scenario_one_status_classes_keep_exact_source_names(self):
        labels = builder.BYTE_UI_SCENARIO1_CLASS_LABELS
        self.assertEqual(labels[13], "매직나이트")
        self.assertEqual(labels[55], "매직나이트")
        self.assertEqual(labels[56], "매직나이트")
        self.assertEqual(labels[69], "나이트마스터")
        self.assertEqual(labels[113], "시민")


if __name__ == "__main__":
    unittest.main()
