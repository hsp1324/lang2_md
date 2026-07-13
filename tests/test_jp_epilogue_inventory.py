import json
from pathlib import Path
import unittest

from tools.jp_epilogue_inventory import build_inventory


ROOT = Path(__file__).resolve().parents[1]


class JapaneseEpilogueInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        japanese = (ROOT / "roms/original/Langrisser II (Japan).md").read_bytes()
        mapping = json.loads(
            (ROOT / "localization/english_dialogue_mapping.json").read_text(encoding="utf-8")
        )
        translations = json.loads(
            (ROOT / "localization/epilogue_dialogue_ko.json").read_text(encoding="utf-8")
        )
        cls.result = build_inventory(japanese, mapping, translations)

    def test_ninety_complete_records_are_owned(self):
        self.assertEqual(self.result["record_count"], 90)
        self.assertEqual(len(self.result["records"]), 90)
        self.assertEqual(
            len({row["address"] for row in self.result["records"]}),
            90,
        )
        self.assertEqual(
            len({row["pointer_reference"] for row in self.result["records"]}),
            90,
        )

    def test_expected_source_extent_is_stable(self):
        addresses = {row["address"] for row in self.result["records"]}
        self.assertIn("0x0895A2", addresses)
        self.assertIn("0x094F1A", addresses)
        capacities = [row["capacity_words"] for row in self.result["records"]]
        self.assertEqual(min(capacities), 218)
        self.assertEqual(max(capacities), 544)

    def test_english_reference_indices_are_complete(self):
        self.assertEqual(
            {row["english_record"] for row in self.result["records"]},
            set(range(1901, 1991)),
        )

    def test_translation_progress_is_explicit(self):
        self.assertEqual(self.result["translated_record_count"], 36)
        translated = {
            row["address"]
            for row in self.result["records"]
            if row["translation_status"] == "translated"
        }
        self.assertEqual(
            translated,
            {
                "0x0895A2", "0x089760", "0x089950", "0x089B70", "0x089D50",
                "0x089F2C", "0x08A13A", "0x08A354", "0x08A566",
                "0x08A73A", "0x08A922", "0x08AB30", "0x08AD62", "0x08AF28",
                "0x08B106", "0x08B314", "0x08B50C", "0x08B6D8",
                "0x08B8C4", "0x08BAD2", "0x08BCF8", "0x08BF60", "0x08C182",
                "0x08C358", "0x08C57E", "0x08C790", "0x08C9AA",
                "0x08CBCE", "0x08CE08", "0x08D062", "0x08D2D8", "0x08D4DA",
                "0x08D6F0", "0x08D940", "0x08DB40", "0x08DD68",
            },
        )


if __name__ == "__main__":
    unittest.main()
