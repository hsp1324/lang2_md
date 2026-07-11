from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_compressed_resource_inventory import inventory, resource_pointers


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class CompressedResourceInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()
        cls.result = inventory(cls.japanese, cls.korean)

    def test_table_boundary_and_count(self):
        pointers = resource_pointers(self.japanese)
        self.assertEqual(len(pointers), 429)
        self.assertEqual(pointers[0], 0x0B06B4)
        self.assertEqual(pointers[-1], 0x13807E)

    def test_all_resources_decompress_and_types_match(self):
        self.assertEqual(self.result["entry_count"], 429)
        self.assertEqual(self.result["type_counts"], {"1": 2, "2": 248, "3": 179})
        self.assertTrue(
            all(entry["original_decompressed_size"] > 0 for entry in self.result["entries"])
        )

    def test_only_byte_ui_font_is_relocated_and_modified(self):
        self.assertEqual(self.result["modified_count"], 1)
        self.assertEqual(self.result["known_owner_count"], 1)
        entry = self.result["entries"][builder.BYTE_UI_FONT_RESOURCE_INDEX]
        self.assertEqual(entry["owner"], "byte_ui_font")
        self.assertEqual(entry["original_pointer"], "0x0B0A84")
        self.assertEqual(entry["current_pointer"], "0x290000")
        self.assertEqual(entry["original_type"], 3)
        self.assertEqual(entry["current_type"], 3)
        self.assertEqual(entry["original_decompressed_size"], 8192)
        self.assertEqual(entry["current_decompressed_size"], 8192)
        self.assertTrue(entry["pointer_modified"])
        self.assertTrue(entry["content_modified"])


if __name__ == "__main__":
    unittest.main()
