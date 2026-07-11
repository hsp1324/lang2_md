from pathlib import Path
import unittest

from tools.jp_ui_surface_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class JapaneseUiSurfaceInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes(), KO_ROM.read_bytes())

    def test_declared_patch_baseline(self):
        self.assertEqual(self.result["declared_patch_count"], 74)
        self.assertEqual(self.result["modified_patch_count"], 73)

    def test_compressed_byte_font_is_relocated(self):
        font = self.result["compressed_byte_ui_font"]
        self.assertEqual(font["table_entry"], "0x0B0004")
        self.assertEqual(font["original_pointer"], "0x0B0A84")
        self.assertEqual(font["current_pointer"], "0x290000")
        self.assertTrue(font["relocated"])

    def test_stage_one_keeps_explicit_unknowns(self):
        self.assertGreaterEqual(len(self.result["remaining_inventory_gaps"]), 7)
        self.assertTrue(
            any("class-change" in gap for gap in self.result["remaining_inventory_gaps"])
        )


if __name__ == "__main__":
    unittest.main()
