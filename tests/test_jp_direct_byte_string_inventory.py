from pathlib import Path
import unittest

from tools.jp_direct_byte_string_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class JapaneseDirectByteStringInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes(), KO_ROM.read_bytes())

    def test_reviewed_candidate_baseline(self):
        self.assertEqual(self.result["candidate_count"], 348)
        self.assertEqual(self.result["reference_count"], 607)
        self.assertEqual(self.result["unclassified_count"], 0)
        self.assertEqual(
            self.result["category_counts"],
            {
                "declared_equipment_category_ui": 1,
                "global_table_interior": 10,
                "global_table_string": 249,
                "internal_secret_name_comparison": 1,
                "reviewed_binary_false_positive": 84,
                "special_illusion_class": 1,
                "structured_name_entry_resource": 2,
            },
        )

    def test_illusion_status_class_is_user_facing_and_relocated(self):
        entry = next(
            row for row in self.result["entries"] if row["target"] == "0x05E5CE"
        )
        self.assertEqual(entry["text"], "ｲﾘｭｰｼﾞｮﾝ")
        self.assertEqual(entry["references"], ["0x05E5CA"])
        self.assertEqual(entry["category"], "special_illusion_class")
        self.assertTrue(self.result["special_illusion"]["selector_valid"])
        self.assertEqual(
            self.result["special_illusion"]["selector_bytes"],
            "43 F9 00 05 E5 CA",
        )
        self.assertTrue(self.result["special_illusion"]["relocated"])
        self.assertEqual(self.result["special_illusion"]["target_korean"], "일루전")

    def test_reserved_name_comparison_is_not_mistaken_for_visible_ui(self):
        entry = next(
            row for row in self.result["entries"] if row["target"] == "0x0A3B9D"
        )
        self.assertEqual(entry["text"], "ﾗﾝｸﾞﾘｯｻｰ")
        self.assertEqual(entry["references"], ["0x02B1D8"])
        self.assertEqual(entry["category"], "internal_secret_name_comparison")


if __name__ == "__main__":
    unittest.main()
