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
        self.assertEqual(self.result["translated_record_count"], 90)
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
                "0x08DF62", "0x08E116", "0x08E316", "0x08E520", "0x08E712",
                "0x08E90A", "0x08EB14", "0x08ECEC", "0x08EED6",
                "0x08F0B0", "0x08F2A8", "0x08F4B0", "0x08F6A2", "0x08F898",
                "0x08FACA", "0x08FCF4", "0x08FEEA", "0x090104",
                "0x090300", "0x09050E", "0x090702", "0x090932", "0x090B5A",
                "0x090D5E", "0x090F64", "0x091144", "0x09135E",
                "0x09158C", "0x091790", "0x0919F4", "0x091C48", "0x091E24",
                "0x09200A", "0x0921F2", "0x092400", "0x092612",
                "0x092820", "0x092A1C", "0x092C50", "0x092E50", "0x0930B6",
                "0x093370",
                "0x0937B2", "0x0939BC", "0x093BCE", "0x093DE4", "0x093FAA",
                "0x09419A", "0x09438A", "0x09458C",
                "0x0947E0", "0x094A1E", "0x094CA2", "0x094F1A",
            },
        )


if __name__ == "__main__":
    unittest.main()
