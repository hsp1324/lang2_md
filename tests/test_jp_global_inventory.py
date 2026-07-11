from pathlib import Path
import unittest

from tools.jp_global_inventory import inventory
from tools.scenario_data import NAME_COUNT, name_for_id


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class JapaneseGlobalInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()
        cls.result = inventory(cls.japanese, cls.korean)

    def test_global_table_counts_and_pointers(self):
        tables = self.result["tables"]
        self.assertEqual(tables["classes"]["entry_count"], 157)
        self.assertEqual(tables["items"]["entry_count"], 38)
        self.assertEqual(tables["names"]["entry_count"], 117)
        self.assertEqual(tables["names"]["pointer_table"], "0x0618E8")

    def test_current_raw_modification_baseline(self):
        tables = self.result["tables"]
        self.assertEqual(tables["classes"]["raw_modified_count"], 28)
        self.assertEqual(tables["items"]["raw_modified_count"], 0)
        self.assertEqual(tables["names"]["raw_modified_count"], 25)

    def test_knife_is_detected_through_modified_font_pixels(self):
        knife = self.result["tables"]["items"]["entries"][1]
        self.assertEqual(knife["original_text"], "ﾅｲﾌ")
        self.assertFalse(knife["raw_modified"])
        self.assertTrue(knife["font_glyph_modified"])
        self.assertEqual(knife["target_korean"], "단검")

    def test_name_table_exposes_all_117_ids(self):
        self.assertEqual(NAME_COUNT, 117)
        final_named = name_for_id(self.japanese, 115)
        self.assertEqual(final_named["id"], 115)
        self.assertTrue(final_named["jp"])

    def test_every_name_id_has_a_source_based_korean_target(self):
        names = self.result["tables"]["names"]
        self.assertEqual(names["known_korean_target_count"], 117)
        self.assertTrue(all(entry["target_korean"] is not None for entry in names["entries"]))


if __name__ == "__main__":
    unittest.main()
