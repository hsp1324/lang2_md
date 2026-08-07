from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class PreparationStatLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()

    def words(self, offset: int) -> tuple[int, int]:
        return (
            builder.be16(self.jp, offset),
            builder.be16(self.jp, offset + 2),
        )

    def test_original_word_tiles_prove_mp_and_mv_positions(self):
        # Original compact alphabet: M=0x25, V=0x26, P=0x28.
        self.assertEqual(self.words(0x09AB5E), (0x27, 0x26))  # LV
        self.assertEqual(self.words(0x09AB6C), (0x25, 0x28))  # MP
        self.assertEqual(self.words(0x09AB7E), (0x25, 0x26))  # MV
        self.assertEqual(self.words(0x09ACD2), (0x25, 0x28))  # MP
        self.assertEqual(self.words(0x09ACE0), (0x25, 0x26))  # MV

    def test_korean_patch_preserves_mp_and_mv_semantics(self):
        patches = builder.BYTE_UI_WORD_STRING_PATCHES
        self.assertEqual(patches[0x09AB6C], (2, "MP"))
        self.assertEqual(patches[0x09AB7E], (2, "MV"))
        self.assertEqual(patches[0x09ACD2], (2, "MP"))
        self.assertEqual(patches[0x09ACE0], (2, "MV"))


if __name__ == "__main__":
    unittest.main()
