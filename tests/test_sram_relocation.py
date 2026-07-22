from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class SramRelocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()

    def test_sram_follows_expanded_rom(self):
        self.assertEqual(builder.be32(self.ko, 0x1A4), builder.EXPANDED_ROM_SIZE - 1)
        self.assertEqual(builder.be32(self.ko, 0x1B4), builder.RELOCATED_SRAM_START)
        self.assertEqual(builder.be32(self.ko, 0x1B8), builder.RELOCATED_SRAM_END)
        self.assertGreater(builder.RELOCATED_SRAM_START, builder.be32(self.ko, 0x1A4))

    def test_all_known_sram_long_addresses_move_together(self):
        for offset, original_address in builder.SRAM_LONG_PATCHES.items():
            self.assertEqual(builder.be32(self.jp, offset), original_address)
            self.assertEqual(
                builder.be32(self.ko, offset),
                original_address + builder.SRAM_ADDRESS_DELTA,
            )

    def test_relocated_sram_size_is_unchanged(self):
        original_size = builder.ORIGINAL_SRAM_END - builder.ORIGINAL_SRAM_START
        relocated_size = builder.RELOCATED_SRAM_END - builder.RELOCATED_SRAM_START
        self.assertEqual(relocated_size, original_size)


if __name__ == "__main__":
    unittest.main()
