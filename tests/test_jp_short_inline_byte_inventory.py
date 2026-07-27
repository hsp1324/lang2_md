import json
from pathlib import Path
import unittest

from tools.jp_short_inline_byte_inventory import (
    CLASS_SPRITE_GRAPHICS_ALIGNED_REFERENCE_REVIEWS,
    CLASS_SPRITE_GRAPHICS_REVIEWS,
    COMPRESSED_RESOURCE_BANK_SOURCE_SHA256,
    COMPRESSED_RESOURCE_CANDIDATE_MANIFEST_SHA256,
    COMPRESSED_RESOURCE_POINTER_TABLE_SHA256,
    COMPRESSED_RESOURCE_REPRESENTATIVE_ADDRESSES,
    ENDING_SCENARIO_STRUCTURED_REVIEWS,
    FONT_BITMAP_BANK_END,
    FONT_BITMAP_BANK_START,
    FONT_BITMAP_GLYPH_BYTES,
    FONT_BITMAP_REPRESENTATIVE_ADDRESSES,
    FONT_BITMAP_SOURCE_SHA256,
    ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS,
    ITEM_NAME_GRAPHICS_REVIEWS,
    SCENARIO_LEVEL_PREFIX,
    SYSTEM_GRAPHICS_ENDING_REVIEWS,
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
        cls.font_bank = cls.result["font_bitmap_bank"]
        cls.class_bank = cls.result["class_sprite_graphics_bank"]
        cls.item_bank = cls.result["item_name_graphics_bank"]
        cls.system_bank = cls.result["system_graphics_ending_bank"]
        cls.ending_bank = cls.result["ending_scenario_bank"]
        cls.bank = cls.result["text_ui_bank"]
        cls.compressed_bank = cls.result["compressed_resource_bank"]

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

    def test_compressed_resource_bank_is_source_locked_and_fully_classified(self):
        bank = self.compressed_bank
        self.assertEqual(bank["candidate_count"], 3254)
        self.assertEqual(
            bank["kind_counts"],
            {"ascii": 1014, "halfwidth": 2240},
        )
        self.assertEqual(
            bank["category_counts"],
            {"compressed_resource_payload_false_positive": 3254},
        )
        self.assertEqual(bank["unclassified_count"], 0)
        self.assertEqual(bank["pointer_table_candidate_addresses"], [])
        self.assertEqual(bank["padding_candidate_addresses"], [])
        self.assertEqual(bank["unowned_candidate_addresses"], [])
        self.assertEqual(bank["resource_count"], 429)
        self.assertEqual(bank["first_resource_pointer"], "0x0B06B4")
        self.assertEqual(bank["last_resource_pointer"], "0x13807E")
        self.assertEqual(bank["last_resource_encoded_end"], "0x138152")
        self.assertEqual(
            bank["source_sha256"], COMPRESSED_RESOURCE_BANK_SOURCE_SHA256
        )
        self.assertEqual(
            bank["pointer_table_sha256"],
            COMPRESSED_RESOURCE_POINTER_TABLE_SHA256,
        )
        self.assertEqual(
            bank["candidate_manifest_sha256"],
            COMPRESSED_RESOURCE_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertEqual(
            bank["expected_candidate_manifest_sha256"],
            COMPRESSED_RESOURCE_CANDIDATE_MANIFEST_SHA256,
        )
        self.assertTrue(bank["source_layout_valid"])
        self.assertEqual(bank["encoded_payload_bytes"], 555532)
        self.assertEqual(bank["padding_bytes"], 294720)
        self.assertEqual(
            bank["padding_value_counts"],
            {"0x00": 146, "0xFF": 294574},
        )

    def test_compressed_candidates_have_exact_resource_family_ownership(self):
        bank = self.compressed_bank
        self.assertEqual(bank["resource_count_with_candidates"], 373)
        self.assertEqual(
            bank["asset_family_candidate_counts"],
            {
                "battle_background": 221,
                "battle_scene_graphics": 51,
                "battle_ui": 4,
                "character_portrait": 648,
                "combat_sprite": 867,
                "item_icon_graphics": 17,
                "map_tileset": 660,
                "opening_ending_graphics": 729,
                "platform_logo": 1,
                "title_logo_graphics": 17,
                "ui_font": 29,
                "world_map_graphics": 10,
            },
        )
        rows = {
            int(row["address"], 16): row
            for row in bank["representative_candidates"]
        }
        self.assertEqual(
            rows.keys(), COMPRESSED_RESOURCE_REPRESENTATIVE_ADDRESSES
        )
        self.assertEqual(bank["missing_representative_addresses"], [])
        expected = {
            0x0B0739: (0, "platform_logo"),
            0x0B0AF2: (1, "ui_font"),
            0x0B1B49: (2, "map_tileset"),
            0x0C7D7A: (23, "map_tileset"),
            0x0D4410: (47, "combat_sprite"),
            0x0FEBA8: (223, "battle_ui"),
            0x10149D: (231, "character_portrait"),
            0x11E964: (390, "world_map_graphics"),
            0x11FB91: (391, "item_icon_graphics"),
            0x120F0E: (393, "title_logo_graphics"),
            0x121B4F: (394, "opening_ending_graphics"),
        }
        for address, (index, family) in expected.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(rows[address]["resource_index"], index)
                self.assertEqual(rows[address]["asset_family"], family)
                self.assertEqual(
                    rows[address]["category"],
                    "compressed_resource_payload_false_positive",
                )
                self.assertTrue(rows[address]["context_words"])

    def test_compressed_candidate_reference_windows_do_not_change_ownership(self):
        bank = self.compressed_bank
        self.assertEqual(bank["aligned_absolute_32_reference_count"], 72)
        self.assertEqual(len(bank["aligned_absolute_32_references"]), 17)
        self.assertEqual(bank["pc_relative_lea_pea_reference_count"], 0)
        self.assertEqual(bank["pc_relative_lea_pea_references"], [])

    def test_font_bitmap_bank_is_source_locked_and_fully_classified(self):
        self.assertEqual(self.font_bank["candidate_count"], 1477)
        self.assertEqual(
            self.font_bank["kind_counts"],
            {"ascii": 762, "halfwidth": 715},
        )
        self.assertEqual(
            self.font_bank["category_counts"],
            {"font_bitmap_false_positive": 1477},
        )
        self.assertEqual(self.font_bank["unclassified_count"], 0)
        self.assertEqual(
            self.font_bank["glyph_count"],
            (FONT_BITMAP_BANK_END - FONT_BITMAP_BANK_START)
            // FONT_BITMAP_GLYPH_BYTES,
        )
        self.assertEqual(
            self.font_bank["source_sha256"], FONT_BITMAP_SOURCE_SHA256
        )
        self.assertEqual(
            self.font_bank["expected_source_sha256"],
            FONT_BITMAP_SOURCE_SHA256,
        )
        self.assertTrue(self.font_bank["source_layout_valid"])
        self.assertEqual(
            self.font_bank["candidate_manifest_sha256"],
            "f5763ec3ad9d40cf8e5ae135b9ccae984847a1aca9f388121ba17502a011b956",
        )

    def test_font_bitmap_representatives_have_exact_pixel_ownership(self):
        rows = {
            int(row["address"], 16): row
            for row in self.font_bank["representative_candidates"]
        }
        self.assertEqual(rows.keys(), FONT_BITMAP_REPRESENTATIVE_ADDRESSES)
        self.assertEqual(
            self.font_bank["missing_representative_addresses"], []
        )
        for address, row in rows.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(
                    row["category"], "font_bitmap_false_positive"
                )
                self.assertEqual(
                    row["glyph_index"],
                    (address - FONT_BITMAP_BANK_START)
                    // FONT_BITMAP_GLYPH_BYTES,
                )
                self.assertEqual(
                    row["glyph_byte_offset"],
                    (address - FONT_BITMAP_BANK_START)
                    % FONT_BITMAP_GLYPH_BYTES,
                )
                self.assertTrue(row["context_words"])

    def test_font_bitmap_reference_windows_do_not_change_bitmap_ownership(self):
        self.assertEqual(
            self.font_bank["aligned_absolute_32_reference_count"], 32
        )
        self.assertEqual(
            self.font_bank["pc_relative_lea_pea_reference_count"], 0
        )
        self.assertEqual(
            {
                int(row["target"], 16): [
                    int(address, 16) for address in row["addresses"]
                ]
                for row in self.font_bank[
                    "aligned_absolute_32_references"
                ]
            },
            {
                0x043143: [
                    0x00C2F2,
                    0x01BA16,
                    0x01BA5A,
                    0x01BAAA,
                    0x01C170,
                    0x01C21C,
                ],
                0x04322E: [0x003BEC, 0x00571A],
                0x044A69: [0x001936],
                0x044CDF: [
                    0x00857A,
                    0x00B732,
                    0x011846,
                    0x011C64,
                    0x013678,
                    0x0139FC,
                    0x0155A8,
                    0x018A0C,
                    0x018A72,
                    0x01A9B4,
                    0x01AA00,
                    0x01ABC2,
                    0x01AC5C,
                    0x01B038,
                ],
                0x047001: [
                    0x00B3FC,
                    0x00C33A,
                    0x00CCEE,
                    0x00D260,
                    0x02A02C,
                ],
                0x04B428: [0x012D96],
                0x04C149: [0x01AE00],
                0x04E241: [0x0034B0, 0x01B1B4],
            },
        )

    def test_class_sprite_graphics_bank_has_no_unknown_or_ui_string(self):
        self.assertEqual(self.class_bank["candidate_count"], 62)
        self.assertEqual(
            self.class_bank["category_counts"],
            {
                "class_pointer_table_boundary_false_positive": 1,
                "commander_sprite_mapping_false_positive": 4,
                "packed_sprite_graphics_false_positive": 57,
            },
        )
        self.assertEqual(self.class_bank["unclassified_count"], 0)
        self.assertEqual(self.class_bank["missing_review_addresses"], [])
        self.assertEqual(self.class_bank["stale_review_addresses"], [])

    def test_class_sprite_graphics_review_set_is_exact(self):
        rows = {
            int(row["address"], 16)
            for row in self.class_bank["candidates"]
        }
        self.assertEqual(rows, set(CLASS_SPRITE_GRAPHICS_REVIEWS))

    def test_class_sprite_graphics_examples_preserve_structural_evidence(self):
        rows = {
            int(row["address"], 16): row
            for row in self.class_bank["candidates"]
        }
        expected = {
            0x050019: (
                "AB",
                "0xF4AB",
                "packed_sprite_graphics_false_positive",
            ),
            0x05DD02: (
                "41",
                "0x41FF",
                "commander_sprite_mapping_false_positive",
            ),
            0x05DDA7: (
                "47",
                "0x0047",
                "commander_sprite_mapping_false_positive",
            ),
            0x05E949: (
                "D4 20 20 20 20 20 20 20 20",
                "0xEDD4",
                "class_pointer_table_boundary_false_positive",
            ),
        }
        for address, (raw, word, category) in expected.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(rows[address]["raw_hex"], raw)
                self.assertEqual(rows[address]["containing_word"], word)
                self.assertEqual(rows[address]["category"], category)
                self.assertTrue(rows[address]["context_words"])

    def test_class_sprite_apparent_references_are_reviewed_non_pointers(self):
        self.assertEqual(
            self.class_bank["aligned_absolute_32_reference_count"], 2
        )
        self.assertEqual(
            self.class_bank["pc_relative_lea_pea_reference_count"], 0
        )
        self.assertEqual(
            self.class_bank["missing_aligned_reference_reviews"], []
        )
        self.assertEqual(
            self.class_bank["stale_aligned_reference_reviews"], []
        )
        rows = {
            (int(row["target"], 16), int(row["address"], 16)): row
            for row in self.class_bank["aligned_reference_reviews"]
        }
        self.assertEqual(
            set(rows), set(CLASS_SPRITE_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
        )
        self.assertEqual(
            rows[(0x050019, 0x01CAA2)]["classification"],
            "cross_operand_window",
        )
        self.assertEqual(
            rows[(0x050019, 0x095398)]["classification"],
            "coincidental_data_window",
        )

    def test_item_name_graphics_bank_has_no_unknown_or_ui_string(self):
        self.assertEqual(self.item_bank["candidate_count"], 83)
        self.assertEqual(
            self.item_bank["category_counts"],
            {
                "name_pointer_table_boundary_false_positive": 1,
                "packed_game_graphics_false_positive": 7,
                "packed_tile_sprite_graphics_false_positive": 75,
            },
        )
        self.assertEqual(self.item_bank["unclassified_count"], 0)
        self.assertEqual(self.item_bank["missing_review_addresses"], [])
        self.assertEqual(self.item_bank["stale_review_addresses"], [])

    def test_item_name_graphics_review_set_is_exact(self):
        rows = {
            int(row["address"], 16)
            for row in self.item_bank["candidates"]
        }
        self.assertEqual(rows, set(ITEM_NAME_GRAPHICS_REVIEWS))

    def test_item_name_graphics_examples_preserve_structural_evidence(self):
        rows = {
            int(row["address"], 16): row
            for row in self.item_bank["candidates"]
        }
        expected = {
            0x060D35: (
                "4F",
                "0x244F",
                "packed_game_graphics_false_positive",
            ),
            0x061ABB: (
                "BC 20 20 20 20 20 20 20 20",
                "0x1ABC",
                "name_pointer_table_boundary_false_positive",
            ),
            0x06EFF1: (
                "CC CF",
                "0xEFCC",
                "packed_tile_sprite_graphics_false_positive",
            ),
            0x070C2A: (
                "57 58",
                "0x5758",
                "packed_tile_sprite_graphics_false_positive",
            ),
        }
        for address, (raw, word, category) in expected.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(rows[address]["raw_hex"], raw)
                self.assertEqual(rows[address]["containing_word"], word)
                self.assertEqual(rows[address]["category"], category)
                self.assertTrue(rows[address]["context_words"])

    def test_item_name_graphics_apparent_references_are_reviewed_non_pointers(self):
        self.assertEqual(
            self.item_bank["aligned_absolute_32_reference_count"], 3
        )
        self.assertEqual(
            self.item_bank["pc_relative_lea_pea_reference_count"], 0
        )
        self.assertEqual(
            self.item_bank["missing_aligned_reference_reviews"], []
        )
        self.assertEqual(
            self.item_bank["stale_aligned_reference_reviews"], []
        )
        rows = {
            (int(row["target"], 16), int(row["address"], 16)): row
            for row in self.item_bank["aligned_reference_reviews"]
        }
        self.assertEqual(
            set(rows), set(ITEM_NAME_GRAPHICS_ALIGNED_REFERENCE_REVIEWS)
        )
        self.assertEqual(
            rows[(0x06121F, 0x0A4440)]["classification"],
            "coincidental_data_window",
        )
        self.assertEqual(
            rows[(0x070C2A, 0x01F0A6)]["classification"],
            "cross_instruction_window",
        )
        self.assertEqual(
            rows[(0x070C2A, 0x01F1A8)]["classification"],
            "cross_instruction_window",
        )

    def test_system_graphics_ending_bank_has_no_unknown_or_ui_string(self):
        self.assertEqual(self.system_bank["candidate_count"], 80)
        self.assertEqual(
            self.system_bank["category_counts"],
            {
                "ending_selector_false_positive": 7,
                "packed_tile_resource_false_positive": 7,
                "structured_graphics_false_positive": 53,
                "word_stream_byte_false_positive": 13,
            },
        )
        self.assertEqual(self.system_bank["unclassified_count"], 0)
        self.assertEqual(self.system_bank["missing_review_addresses"], [])
        self.assertEqual(
            self.system_bank["stale_structured_review_addresses"],
            [],
        )

    def test_system_bank_word_stream_rows_end_at_known_controls(self):
        rows = [
            row
            for row in self.system_bank["candidates"]
            if row["category"] == "word_stream_byte_false_positive"
        ]
        self.assertEqual(len(rows), 13)
        for row in rows:
            with self.subTest(address=row["address"]):
                self.assertTrue(
                    is_word_stream_byte_lane(
                        self.japanese,
                        int(row["address"], 16),
                        int(row["end"], 16),
                    )
                )

    def test_system_bank_structured_review_set_is_exact(self):
        rows = {
            int(row["address"], 16)
            for row in self.system_bank["candidates"]
            if row["category"] != "word_stream_byte_false_positive"
        }
        self.assertEqual(rows, set(SYSTEM_GRAPHICS_ENDING_REVIEWS))

    def test_system_bank_examples_preserve_structural_evidence(self):
        rows = {
            int(row["address"], 16): row
            for row in self.system_bank["candidates"]
        }
        expected = {
            0x082ACB: (
                "C2",
                "0x00C2",
                "word_stream_byte_false_positive",
            ),
            0x084401: (
                "45 46 2E 2E 2E",
                "0x0E45",
                "packed_tile_resource_false_positive",
            ),
            0x08721B: (
                "CE",
                "0xFFCE",
                "structured_graphics_false_positive",
            ),
            0x089286: (
                "B6 D8",
                "0xB6D8",
                "ending_selector_false_positive",
            ),
        }
        for address, (raw, word, category) in expected.items():
            with self.subTest(address=f"0x{address:06X}"):
                self.assertEqual(rows[address]["raw_hex"], raw)
                self.assertEqual(rows[address]["containing_word"], word)
                self.assertEqual(rows[address]["category"], category)
                self.assertTrue(rows[address]["context_words"])

    def test_system_bank_candidates_have_no_exact_reference(self):
        self.assertEqual(
            self.system_bank["aligned_absolute_32_reference_count"], 0
        )
        self.assertEqual(
            self.system_bank["pc_relative_lea_pea_reference_count"], 0
        )
        self.assertTrue(
            all(
                not row["aligned_absolute_32_references"]
                and not row["pc_relative_lea_pea_references"]
                for row in self.system_bank["candidates"]
            )
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
