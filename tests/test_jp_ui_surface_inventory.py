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
        self.assertEqual(self.result["declared_patch_count"], 94)
        self.assertEqual(self.result["modified_patch_count"], 93)
        name_rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"].startswith("name_entry_")
        ]
        self.assertEqual(len(name_rows), 6)
        self.assertTrue(all(row["reviewed"] for row in name_rows))
        self.assertTrue(all(row["live_verified"] for row in name_rows))

    def test_ending_status_labels_are_declared(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["address"] == "0x089146"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_korean"], "격파횟수퇴각횟수")
        self.assertTrue(rows[0]["modified"])
        self.assertTrue(rows[0]["reviewed"])
        self.assertTrue(rows[0]["live_verified"])

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
