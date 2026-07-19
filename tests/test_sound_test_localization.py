from pathlib import Path
import hashlib
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class SoundTestLocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

    def test_stock_sound_ids_and_label_table_are_locked(self):
        start = builder.SOUND_TEST_SOURCE_TABLE
        end = start + builder.SOUND_TEST_ROW_COUNT * builder.SOUND_TEST_ROW_SIZE
        source = self.japanese[start:end]
        self.assertEqual(hashlib.sha256(source).hexdigest(), builder.SOUND_TEST_SOURCE_SHA256)
        self.assertEqual(self.japanese[end], 0xFF)
        self.assertEqual(len(builder.SOUND_TEST_LABELS), builder.SOUND_TEST_ROW_COUNT)
        self.assertTrue(all(len(label) <= builder.SOUND_TEST_LABEL_WIDTH for label in builder.SOUND_TEST_LABELS))

    def test_relocated_rows_are_direct_tile_words(self):
        working = bytearray(self.japanese)
        builder.expand_rom(working)
        code_by_char = builder.patch_byte_ui_strings(working)
        index_by_char, tile_by_index = builder.build_byte_ui_local_mapping(code_by_char)
        expected = bytearray()
        for label in builder.SOUND_TEST_LABELS:
            for char in label.ljust(builder.SOUND_TEST_LABEL_WIDTH):
                tile = ord(char) if ord(char) < 0x80 else tile_by_index[index_by_char[char]]
                expected.extend(tile.to_bytes(2, "big"))
        start = builder.SOUND_TEST_TILE_TABLE
        self.assertEqual(self.korean[start : start + len(expected)], expected)

    def test_renderer_hook_and_routine_are_installed(self):
        hook = bytes.fromhex("4E F9") + builder.SOUND_TEST_RENDER_ROUTINE.to_bytes(4, "big")
        self.assertEqual(
            self.korean[
                builder.SOUND_TEST_RENDER_HOOK :
                builder.SOUND_TEST_RENDER_HOOK + len(hook)
            ],
            hook,
        )
        routine = builder._build_sound_test_renderer()
        self.assertEqual(
            self.korean[
                builder.SOUND_TEST_RENDER_ROUTINE :
                builder.SOUND_TEST_RENDER_ROUTINE + len(routine)
            ],
            routine,
        )

    def test_stock_playback_table_is_unchanged(self):
        start = builder.SOUND_TEST_SOURCE_TABLE
        end = start + builder.SOUND_TEST_ROW_COUNT * builder.SOUND_TEST_ROW_SIZE + 1
        self.assertEqual(self.korean[start:end], self.japanese[start:end])


if __name__ == "__main__":
    unittest.main()
