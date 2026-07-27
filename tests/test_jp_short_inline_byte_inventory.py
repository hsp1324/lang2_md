import json
from pathlib import Path
import unittest

from tools.jp_short_inline_byte_inventory import (
    ENDING_SCENARIO_STRUCTURED_REVIEWS,
    SCENARIO_LEVEL_PREFIX,
    TEXT_UI_REVIEWS,
    aligned_absolute_references,
    inventory,
    is_word_stream_byte_lane,
    markdown_report,
    pc_relative_lea_pea_references,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
JSON_PATH = ROOT / "localization/short_inline_byte_candidates.json"
MARKDOWN_PATH = ROOT / "docs/short_inline_byte_candidate_inventory.md"


class JapaneseShortInlineByteInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.result = inventory(cls.japanese, KO_ROM.read_bytes())
        cls.ending_bank = cls.result["ending_scenario_bank"]
        cls.bank = cls.result["text_ui_bank"]

    def test_low_signal_candidate_baseline(self):
        self.assertEqual(self.result["candidate_count"], 6612)
        self.assertEqual(
            self.result["kind_counts"],
            {"ascii": 2177, "halfwidth": 4435},
        )
        self.assertEqual(
            self.result["region_counts"]["halfwidth"]["text_ui_bank"],
            22,
        )
        self.assertEqual(
            self.result["region_counts"]["ascii"]["text_ui_bank"],
            16,
        )

    def test_ending_scenario_bank_has_one_retained_ui_and_no_unknown(self):
        self.assertEqual(self.ending_bank["candidate_count"], 138)
        self.assertEqual(
            self.ending_bank["category_counts"],
            {
                "retained_compact_english_ui": 1,
                "structured_layout_false_positive": 21,
                "word_stream_byte_false_positive": 116,
            },
        )
        self.assertEqual(self.ending_bank["unclassified_count"], 0)
        self.assertEqual(self.ending_bank["missing_review_addresses"], [])
        self.assertEqual(
            self.ending_bank["stale_structured_review_addresses"],
            [],
        )

    def test_ending_scenario_word_stream_rows_end_at_known_controls(self):
        rows = [
            row
            for row in self.ending_bank["candidates"]
            if row["category"] == "word_stream_byte_false_positive"
        ]
        self.assertEqual(len(rows), 116)
        for row in rows:
            with self.subTest(address=row["address"]):
                self.assertTrue(
                    is_word_stream_byte_lane(
                        self.japanese,
                        int(row["address"], 16),
                        int(row["end"], 16),
                    )
                )

    def test_ending_scenario_structured_review_set_is_exact(self):
        rows = {
            int(row["address"], 16)
            for row in self.ending_bank["candidates"]
            if row["category"] == "structured_layout_false_positive"
        }
        self.assertEqual(rows, set(ENDING_SCENARIO_STRUCTURED_REVIEWS))

    def test_scenario_level_prefix_is_retained_compact_ui(self):
        rows = {
            int(row["address"], 16): row
            for row in self.ending_bank["candidates"]
        }
        row = rows[SCENARIO_LEVEL_PREFIX]
        self.assertEqual(row["original_text"], "L-")
        self.assertEqual(row["raw_hex"], "4C 2D")
        self.assertEqual(row["category"], "retained_compact_english_ui")
        self.assertEqual(row["aligned_absolute_32_references"], ["0x025CDE"])
        self.assertEqual(row["pc_relative_lea_pea_references"], [])
        self.assertEqual(
            self.ending_bank["aligned_absolute_32_reference_count"], 1
        )
        self.assertEqual(
            self.ending_bank["pc_relative_lea_pea_reference_count"], 0
        )

        prefix = self.ending_bank["retained_level_prefix"]
        self.assertEqual(prefix["source_bytes"], "4C 2D FF")
        self.assertEqual(prefix["current_bytes"], "4C 2D FF")
        self.assertEqual(prefix["hook_bytes"], "41 F9 00 09 B2 E7")
        self.assertTrue(prefix["source_hook_valid"])
        self.assertTrue(prefix["current_hook_preserved"])
        self.assertTrue(prefix["current_record_preserved"])
        self.assertTrue(prefix["live_verified"])
        self.assertTrue((ROOT / prefix["evidence"]).exists())

    def test_every_text_ui_bank_candidate_has_an_exact_review(self):
        rows = {int(row["address"], 16): row for row in self.bank["candidates"]}
        self.assertEqual(set(rows), set(TEXT_UI_REVIEWS))
        self.assertEqual(self.bank["candidate_count"], 38)
        self.assertEqual(self.bank["unclassified_count"], 0)
        self.assertEqual(self.bank["missing_review_addresses"], [])
        self.assertEqual(self.bank["stale_review_addresses"], [])
        self.assertEqual(
            self.bank["category_counts"],
            {
                "structured_layout_false_positive": 10,
                "word_stream_byte_false_positive": 28,
            },
        )

    def test_reviewed_examples_preserve_containing_word_evidence(self):
        rows = {row["address"]: row for row in self.bank["candidates"]}
        expected = {
            "0x0A1427": (
                "CE",
                "0x00CE",
                "structured_layout_false_positive",
            ),
            "0x0A3161": (
                "54",
                "0x0054",
                "word_stream_byte_false_positive",
            ),
            "0x0A4A36": (
                "A7",
                "0xA7FF",
                "structured_layout_false_positive",
            ),
            "0x0A6F27": (
                "AA",
                "0x00AA",
                "word_stream_byte_false_positive",
            ),
        }
        for address, (raw, word, category) in expected.items():
            with self.subTest(address=address):
                self.assertEqual(rows[address]["raw_hex"], raw)
                self.assertEqual(rows[address]["containing_word"], word)
                self.assertEqual(rows[address]["category"], category)
                self.assertTrue(rows[address]["context_words"])

    def test_reviewed_candidates_have_no_exact_reference(self):
        self.assertEqual(self.bank["aligned_absolute_32_reference_count"], 0)
        self.assertEqual(self.bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertTrue(
            all(
                not row["aligned_absolute_32_references"]
                and not row["pc_relative_lea_pea_references"]
                for row in self.bank["candidates"]
            )
        )

    def test_reference_scanners_find_synthetic_exact_targets(self):
        data = bytearray(32)
        target = 16
        data[0:4] = target.to_bytes(4, "big")
        self.assertEqual(aligned_absolute_references(bytes(data), {target}), {16: [0]})

        data = bytearray(32)
        data[0:4] = bytes.fromhex("41 FA 00 0E")
        data[4:8] = bytes.fromhex("48 7A 00 0A")
        references = pc_relative_lea_pea_references(bytes(data), {target})
        self.assertEqual(
            [(row["instruction"], row["address"]) for row in references[target]],
            [("LEA", 0), ("PEA", 4)],
        )

    def test_generated_reports_match(self):
        self.assertEqual(
            json.loads(JSON_PATH.read_text(encoding="utf-8")),
            self.result,
        )
        self.assertEqual(
            MARKDOWN_PATH.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )


if __name__ == "__main__":
    unittest.main()
