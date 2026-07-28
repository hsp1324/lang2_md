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
        self.assertEqual(builder.TITLE_VERSION_TEXT, "번역: 1.0.0")
        self.assertEqual(
            builder.TITLE_VERSION_RENDER_POSITION,
            builder.title_version_render_position("번역: 1.0.0"),
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
        text = "번역/밸런스: 1.0.0/1.0.0"
        record = builder.build_title_version_record(text)
        self.assertLessEqual(
            builder.TITLE_VERSION_TEXT_RECORD + len(record),
            builder.BYTE_UI_LOCAL_TILE_LOOKUP_ROUTINE,
        )
        self.assertLess(
            builder.title_version_render_position(text),
            builder.TITLE_VERSION_RENDER_POSITION,
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
            b"LANGRISSER II KOREAN T1.0.0 BY HSP1324",
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


if __name__ == "__main__":
    unittest.main()
