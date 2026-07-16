import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_compressed_resource_inventory import (
    decompress_type1,
    decompress_type2,
    direct_load_calls,
    inventory,
    markdown_report,
    resource_output_size,
    resource_pointers,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"
INVENTORY_JSON = ROOT / "localization/compressed_resources.json"
INVENTORY_MARKDOWN = ROOT / "docs/compressed_resource_inventory.md"


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

    def test_checked_in_reports_match_current_rom(self):
        stored = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
        self.assertEqual(stored, self.result)
        self.assertEqual(
            INVENTORY_MARKDOWN.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )

    def test_all_output_sizes_and_decoding_match(self):
        self.assertEqual(self.result["entry_count"], 429)
        self.assertEqual(self.result["type_counts"], {"1": 2, "2": 248, "3": 179})
        self.assertEqual(self.result["decoded_counts"], {"1": 2, "2": 248, "3": 179})
        self.assertEqual(self.result["total_original_output_bytes"], 903296)
        self.assertTrue(
            all(entry["original_output_size"] > 0 for entry in self.result["entries"])
        )
        self.assertTrue(
            all(
                (entry["original_decoded_sha256"] is not None)
                is True
                for entry in self.result["entries"]
            )
        )

    def test_type1_rle_and_type2_plane_decoder(self):
        pointers = resource_pointers(self.japanese)
        type1 = [index for index, pointer in enumerate(pointers) if self.japanese[pointer] == 1]
        self.assertEqual(type1, [389, 411])
        self.assertEqual([len(decompress_type1(self.japanese, pointers[index])) for index in type1], [384, 224])
        type2_sizes = [
            resource_output_size(self.japanese, pointer)
            for pointer in pointers
            if self.japanese[pointer] == 2
        ]
        self.assertEqual(len(type2_sizes), 248)
        self.assertEqual(sum(type2_sizes), 306272)
        sample = decompress_type2(self.japanese, pointers[29])
        self.assertEqual(len(sample), 3776)
        self.assertEqual(
            self.result["entries"][29]["original_decoded_sha256"],
            "fde977cddd80d58997844e812050c13a9d965d94f97265ec1a5d23d9d98d08bf",
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
        self.assertEqual(entry["original_output_size"], 8192)
        self.assertEqual(entry["current_output_size"], 8192)
        self.assertTrue(entry["pointer_modified"])
        self.assertTrue(entry["content_modified"])

    def test_direct_loader_calls_are_mapped_without_guessing_dynamic_ids(self):
        calls = direct_load_calls(self.japanese)
        self.assertEqual(len(calls), 75)
        self.assertEqual(sum(call["immediate_resource"] for call in calls), 64)
        self.assertEqual(self.result["dynamic_load_call_count"], 11)
        self.assertEqual(self.result["immediate_referenced_resource_count"], 50)
        font_calls = self.result["entries"][builder.BYTE_UI_FONT_RESOURCE_INDEX][
            "direct_immediate_calls"
        ]
        self.assertEqual(len(font_calls), 6)
        self.assertTrue(all(call["high_bit_flag"] for call in font_calls))


if __name__ == "__main__":
    unittest.main()
