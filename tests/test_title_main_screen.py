from pathlib import Path
import unittest

from PIL import ImageFont

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class TitleMainScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()
        cls.version_patch = bytearray(cls.jp)
        builder.expand_rom(cls.version_patch)
        builder.patch_byte_ui_strings(cls.version_patch)
        cls.hard_version_text = "번역/밸런스:1.3.8/1.3.8"
        cls.hard_version_patch = bytearray(cls.jp)
        builder.expand_rom(cls.hard_version_patch)
        builder.patch_byte_ui_strings(
            cls.hard_version_patch,
            title_version_text=cls.hard_version_text,
        )

    @staticmethod
    def words(data: bytes | bytearray, offset: int, count: int) -> list[int]:
        return [builder.be16(data, offset + index * 2) for index in range(count)]

    def test_japanese_main_menu_source_record_is_locked(self):
        self.assertEqual(
            tuple(
                self.words(
                    self.jp,
                    builder.TITLE_MAIN_MENU_RECORD,
                    len(builder.TITLE_MAIN_MENU_RECORD_ORIGINAL),
                )
            ),
            builder.TITLE_MAIN_MENU_RECORD_ORIGINAL,
        )

    def test_main_menu_uses_full_korean_labels_and_keeps_terminators(self):
        patch_data = bytearray(self.jp)
        builder.expand_rom(patch_data)
        builder.patch_title_main_menu(patch_data)

        start = self.words(
            patch_data,
            builder.TITLE_MAIN_MENU_START_OFFSET,
            builder.TITLE_MAIN_MENU_START_CAPACITY,
        )
        expected_start = [
            0x0000
            if char == " "
            else builder.TITLE_MAIN_MENU_BYTE_BY_CHAR[char]
            for char in builder.TITLE_MAIN_MENU_START_TEXT
        ]
        expected_start.extend(
            [0x0000]
            * (builder.TITLE_MAIN_MENU_START_CAPACITY - len(expected_start))
        )
        self.assertEqual(start, expected_start)
        self.assertEqual(
            builder.be16(
                patch_data,
                builder.TITLE_MAIN_MENU_START_OFFSET
                + builder.TITLE_MAIN_MENU_START_CAPACITY * 2,
            ),
            0xFFFE,
        )

        load = self.words(
            patch_data,
            builder.TITLE_MAIN_MENU_LOAD_OFFSET,
            builder.TITLE_MAIN_MENU_LOAD_CAPACITY,
        )
        self.assertEqual(
            load,
            [
                builder.TITLE_MAIN_MENU_BYTE_BY_CHAR[char]
                for char in builder.TITLE_MAIN_MENU_LOAD_TEXT
            ],
        )
        self.assertEqual(
            builder.be16(
                patch_data,
                builder.TITLE_MAIN_MENU_LOAD_OFFSET
                + builder.TITLE_MAIN_MENU_LOAD_CAPACITY * 2,
            ),
            0xFFFF,
        )

    def test_hard_main_menu_is_relocated_for_the_long_identity_label(self):
        patch_data = bytearray(self.jp)
        builder.expand_rom(patch_data)
        builder.patch_title_main_menu(patch_data, hard_mode=True)
        self.assertEqual(
            patch_data[
                builder.TITLE_MAIN_MENU_RECORD_LEA:
                builder.TITLE_MAIN_MENU_RECORD_LEA
                + len(builder.TITLE_MAIN_MENU_RECORD_LEA_ORIGINAL)
            ],
            bytes.fromhex("41 F9")
            + builder.TITLE_HARD_MAIN_MENU_RECORD.to_bytes(4, "big"),
        )
        record = builder.build_hard_title_main_menu_record()
        self.assertEqual(
            patch_data[
                builder.TITLE_HARD_MAIN_MENU_RECORD:
                builder.TITLE_HARD_MAIN_MENU_RECORD + len(record)
            ],
            record,
        )
        self.assertIn(
            b"".join(
                word.to_bytes(2, "big")
                for word in builder._title_main_menu_words(
                    builder.TITLE_HARD_MAIN_MENU_START_TEXT
                )
            ),
            record,
        )
        self.assertEqual(
            builder._title_main_menu_words("(하드)"),
            [
                builder.TITLE_MAIN_MENU_BYTE_BY_CHAR["("],
                builder.TITLE_MAIN_MENU_BYTE_BY_CHAR["하"],
                builder.TITLE_MAIN_MENU_BYTE_BY_CHAR["드"],
                builder.TITLE_MAIN_MENU_BYTE_BY_CHAR[")"],
            ],
        )
        for width_offset in builder.TITLE_MAIN_MENU_WINDOW_WIDTH_OFFSETS:
            self.assertEqual(
                builder.be16(patch_data, width_offset),
                builder.TITLE_HARD_MAIN_MENU_WINDOW_WIDTH,
            )

    def test_credit_hooks_and_record_are_installed_in_production_rom(self):
        self.assertEqual(builder.TITLE_CREDIT_TEXT, "한글화: HSP1324")
        self.assertEqual(
            builder.TITLE_CREDIT_TEXT_BYTES,
            bytes(
                [
                    0x4A,
                    0x51,
                    0x57,
                    0x3A,
                    0x00,
                    0x48,
                    0x53,
                    0x50,
                    0x31,
                    0x33,
                    0x32,
                    0x34,
                ]
            ),
        )
        self.assertEqual(builder.TITLE_CREDIT_BITMAP_OVERRIDES, {})
        self.assertEqual(
            self.ko[
                builder.TITLE_CREDIT_FONT_LOAD_HOOK :
                builder.TITLE_CREDIT_FONT_LOAD_HOOK
                + len(builder.TITLE_CREDIT_FONT_LOAD_HOOK_ORIGINAL)
            ],
            bytes.fromhex("4E B9")
            + builder.TITLE_CREDIT_FONT_LOAD_ROUTINE.to_bytes(4, "big")
            + bytes.fromhex("4E 71"),
        )
        self.assertEqual(
            self.ko[
                builder.TITLE_COPYRIGHT_RENDER_HOOK :
                builder.TITLE_COPYRIGHT_RENDER_HOOK
                + len(builder.TITLE_COPYRIGHT_RENDER_HOOK_ORIGINAL)
            ],
            bytes.fromhex("4E F9")
            + builder.TITLE_CREDIT_RENDER_ROUTINE.to_bytes(4, "big")
            + bytes.fromhex("4E 71"),
        )
        self.assertEqual(
            self.ko[
                builder.TITLE_CREDIT_TEXT_RECORD :
                builder.TITLE_CREDIT_TEXT_RECORD + len(builder.TITLE_CREDIT_RECORD_BYTES)
            ],
            builder.TITLE_CREDIT_RECORD_BYTES,
        )

    def test_version_record_is_installed_in_new_builds(self):
        self.assertEqual(builder.TITLE_VERSION_TEXT, "번역:1.3.8")
        self.assertEqual(
            builder.TITLE_VERSION_RENDER_POSITION,
            builder.title_version_render_position("번역:1.3.8"),
        )
        self.assertEqual(
            self.version_patch[
                builder.TITLE_VERSION_TEXT_RECORD :
                builder.TITLE_VERSION_TEXT_RECORD
                + len(builder.TITLE_VERSION_RECORD_BYTES)
            ],
            builder.TITLE_VERSION_RECORD_BYTES,
        )

    def test_hard_version_text_fits_reserved_record_and_title_row(self):
        lines = builder.split_hard_title_version_text(self.hard_version_text)
        self.assertEqual(lines, ("번역:1.3.8", "하드:1.3.8"))
        self.assertIsNotNone(lines)
        translation_text, balance_text = lines
        translation_record = builder.build_title_version_record(
            translation_text
        )
        balance_record = builder.build_title_version_record(balance_text)
        self.assertLessEqual(
            builder.TITLE_HARD_TRANSLATION_TEXT_RECORD
            + len(translation_record),
            builder.TITLE_HARD_BALANCE_TEXT_RECORD,
        )
        self.assertLessEqual(
            builder.TITLE_HARD_BALANCE_TEXT_RECORD + len(balance_record),
            builder.TITLE_HARD_CREDIT_RENDER_ROUTINE,
        )
        translation_position = builder.hard_translation_render_position(
            translation_text
        )
        balance_position = builder.title_version_render_position(balance_text)
        self.assertEqual(
            translation_position & 0xFF,
            builder.TITLE_HARD_TRANSLATION_RENDER_START_CELL * 2,
        )
        self.assertLessEqual(
            builder.TITLE_HARD_TRANSLATION_RENDER_START_CELL
            + len(translation_text),
            (balance_position & 0xFF) // 2,
        )

    def test_hard_version_uses_split_records_and_dedicated_renderer(self):
        lines = builder.split_hard_title_version_text(self.hard_version_text)
        self.assertIsNotNone(lines)
        translation_text, balance_text = lines
        self.assertEqual(
            self.hard_version_patch[
                builder.TITLE_COPYRIGHT_RENDER_HOOK:
                builder.TITLE_COPYRIGHT_RENDER_HOOK
                + len(builder.TITLE_COPYRIGHT_RENDER_HOOK_ORIGINAL)
            ],
            bytes.fromhex("4E F9")
            + builder.TITLE_HARD_CREDIT_RENDER_ROUTINE.to_bytes(4, "big")
            + bytes.fromhex("4E 71"),
        )
        hard_renderer = builder._build_title_credit_renderer(
            self.hard_version_text
        )
        self.assertEqual(
            self.hard_version_patch[
                builder.TITLE_HARD_CREDIT_RENDER_ROUTINE:
                builder.TITLE_HARD_CREDIT_RENDER_ROUTINE + len(hard_renderer)
            ],
            hard_renderer,
        )
        for offset, text in (
            (builder.TITLE_HARD_TRANSLATION_TEXT_RECORD, translation_text),
            (builder.TITLE_HARD_BALANCE_TEXT_RECORD, balance_text),
            (
                builder.TITLE_HARD_MARKER_TEXT_RECORD,
                builder.TITLE_HARD_MARKER_TEXT,
            ),
        ):
            record = builder.build_title_version_record(text)
            self.assertEqual(
                self.hard_version_patch[offset:offset + len(record)],
                record,
            )

    def test_hard_title_logo_uses_a_dedicated_gold_palette(self):
        patch_data = bytearray(self.jp)
        builder.expand_rom(patch_data)
        builder.patch_byte_ui_strings(
            patch_data,
            title_version_text=self.hard_version_text,
        )
        builder.patch_title_logo_resource(patch_data, hard_mode=True)
        for index, original in enumerate(
            builder.TITLE_LOGO_PALETTE_ROW_ORIGINAL
        ):
            expected = builder.TITLE_HARD_LOGO_PALETTE_OVERRIDES.get(
                index, original
            )
            self.assertEqual(
                builder.be16(
                    patch_data,
                    builder.TITLE_LOGO_PALETTE_ROW + index * 2,
                ),
                expected,
            )

    def test_rom_header_metadata_preserves_japanese_title(self):
        data = bytearray(self.jp)
        profile = builder.get_rom_version_profile("normal")
        domestic = data[
            builder.MD_HEADER_DOMESTIC_TITLE:
            builder.MD_HEADER_INTERNATIONAL_TITLE
        ]
        builder.patch_rom_header_metadata(data, profile)
        self.assertEqual(
            data[
                builder.MD_HEADER_DOMESTIC_TITLE:
                builder.MD_HEADER_INTERNATIONAL_TITLE
            ],
            domestic,
        )
        metadata = data[
            builder.MD_HEADER_INTERNATIONAL_TITLE:
            builder.MD_HEADER_INTERNATIONAL_TITLE
            + builder.MD_HEADER_TITLE_SIZE
        ]
        self.assertEqual(
            metadata.rstrip(b" "),
            b"LANGRISSER II KOREAN T1.3.8 BY HSP1324",
        )

    def test_credit_font_is_a_separate_resource_with_exact_overrides(self):
        pointer_offset = (
            builder.BYTE_UI_EXT_RESOURCE_TABLE
            + builder.TITLE_CREDIT_RESOURCE_INDEX * 4
        )
        resource_offset = (
            builder.be32(self.version_patch, pointer_offset) & 0x00FFFFFF
        )
        self.assertEqual(self.version_patch[resource_offset], 0x03)
        tiles = builder.decompress_9dfe(
            self.version_patch,
            resource_offset + 1,
        )
        self.assertEqual(len(tiles), builder.TITLE_CREDIT_TILE_COUNT * 32)

        font_path = ROOT / "tools/fonts/Galmuri7.ttf"
        font = ImageFont.truetype(str(font_path if font_path.exists() else builder.FONT_PATH), 8)
        for tile, char in builder.TITLE_CREDIT_TILE_OVERRIDES.items():
            start = (tile - builder.TITLE_CREDIT_TILE_START) * 32
            bitmap = builder.TITLE_CREDIT_BITMAP_OVERRIDES.get(tile)
            expected = (
                builder._encode_byte_ui_bitmap(bitmap)
                if bitmap is not None
                else builder.render_byte_ui_tile(char, font)
            )
            self.assertEqual(
                tiles[start : start + 32],
                expected,
                f"title credit tile 0x{tile:02X} does not render {char!r}",
            )

    def test_credit_routines_and_record_do_not_overlap(self):
        font_loader_end = (
            builder.TITLE_CREDIT_FONT_LOAD_ROUTINE
            + len(builder._build_title_credit_font_loader())
        )
        renderer_end = (
            builder.TITLE_CREDIT_RENDER_ROUTINE
            + len(builder._build_title_credit_renderer())
        )
        record_end = builder.TITLE_CREDIT_TEXT_RECORD + len(
            builder.TITLE_CREDIT_RECORD_BYTES
        )
        version_record_end = builder.TITLE_VERSION_TEXT_RECORD + len(
            builder.TITLE_VERSION_RECORD_BYTES
        )
        self.assertLessEqual(font_loader_end, builder.TITLE_CREDIT_RENDER_ROUTINE)
        self.assertLessEqual(renderer_end, builder.TITLE_CREDIT_TEXT_RECORD)
        self.assertEqual(record_end, builder.TITLE_VERSION_TEXT_RECORD)
        self.assertLessEqual(
            version_record_end,
            builder.BYTE_UI_LOCAL_TILE_LOOKUP_ROUTINE,
        )
        hard_renderer_end = (
            builder.TITLE_HARD_CREDIT_RENDER_ROUTINE
            + len(
                builder._build_title_credit_renderer(
                    self.hard_version_text
                )
            )
        )
        dynamic_direct_end = (
            builder.BYTE_UI_DYNAMIC_DIRECT_MAP_RENDER_ROUTINE
            + len(builder._build_byte_ui_dynamic_direct_map_renderer())
        )
        self.assertLessEqual(
            dynamic_direct_end,
            builder.TITLE_HARD_TRANSLATION_TEXT_RECORD,
        )
        self.assertLessEqual(
            builder.TITLE_HARD_TRANSLATION_TEXT_RECORD
            + len(builder.build_title_version_record("번역:1.3.8")),
            builder.TITLE_HARD_BALANCE_TEXT_RECORD,
        )
        self.assertLessEqual(
            builder.TITLE_HARD_BALANCE_TEXT_RECORD
            + len(builder.build_title_version_record("하드:1.3.8")),
            builder.TITLE_HARD_CREDIT_RENDER_ROUTINE,
        )
        self.assertLessEqual(
            hard_renderer_end,
            builder.TITLE_HARD_CREDIT_RENDER_ROUTINE_LIMIT,
        )
        self.assertLessEqual(
            builder.TITLE_HARD_MARKER_TEXT_RECORD
            + len(
                builder.build_title_version_record(
                    builder.TITLE_HARD_MARKER_TEXT
                )
            ),
            builder.TITLE_HARD_MAIN_MENU_RECORD,
        )
        self.assertLessEqual(
            builder.TITLE_HARD_MAIN_MENU_RECORD
            + len(builder.build_hard_title_main_menu_record()),
            builder.TITLE_HARD_MAIN_MENU_RECORD_LIMIT,
        )


if __name__ == "__main__":
    unittest.main()
