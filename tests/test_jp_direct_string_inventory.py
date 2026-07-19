import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_direct_string_inventory import inventory, markdown_report, scan_candidates


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"
INVENTORY_JSON = ROOT / "localization/direct_word_candidates.json"
INVENTORY_MARKDOWN = ROOT / "docs/direct_word_candidate_inventory.md"


class JapaneseDirectStringInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.result = inventory(cls.japanese, KO_ROM.read_bytes())

    def test_candidate_baseline(self):
        self.assertEqual(len(scan_candidates(self.japanese)), 783)
        self.assertEqual(self.result["candidate_count"], 783)

    def test_checked_in_reports_match_current_rom(self):
        stored = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
        self.assertEqual(stored, self.result)
        self.assertEqual(
            INVENTORY_MARKDOWN.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )

    def test_known_magic_string_is_declared(self):
        row = next(row for row in self.result["candidates"] if row["address"] == "0x082BFE")
        self.assertEqual(row["ownership"], "declared_direct_patch")
        self.assertEqual(row["target_korean"], "매직애로우")
        self.assertTrue(row["modified"])

    def test_every_conservative_candidate_has_an_inventory_owner(self):
        counts = self.result["ownership_counts"]
        self.assertEqual(counts["unclassified_candidate"], 0)
        self.assertTrue(all(row["ownership"] for row in self.result["candidates"]))

    def test_title_main_menu_candidate_has_correct_owner(self):
        row = next(
            row for row in self.result["candidates"] if row["address"] == "0x0A3154"
        )
        self.assertEqual(row["ownership"], "title_main_menu_record")
        self.assertEqual(row["target_korean"], "새 게임 / 불러오기")
        self.assertTrue(row["modified"])
        counts = self.result["ownership_counts"]
        self.assertEqual(counts["title_load_resource"], 7)
        self.assertEqual(counts["title_main_menu_record"], 1)
        self.assertEqual(sum(counts.values()), self.result["candidate_count"])

    def test_render_confirmed_system_message_is_now_declared_and_modified(self):
        row = next(row for row in self.result["candidates"] if row["address"] == "0x082ACE")
        self.assertEqual(row["ownership"], "declared_direct_patch")
        self.assertEqual(row["target_korean"], "레벨이 올랐다.")
        self.assertTrue(row["modified"])

    def test_system_message_patch_rejects_changed_source(self):
        data = bytearray(self.japanese)
        data[0x082ACE] ^= 1
        with self.assertRaisesRegex(ValueError, "system message source changed"):
            builder.patch_direct_strings(data, {}, {0x082ACE: ""}, {}, {})

    def test_word_item_patch_rejects_changed_source_block(self):
        data = bytearray(self.japanese)
        data[0x001106] ^= 1
        with self.assertRaisesRegex(ValueError, "word item-name source changed"):
            builder.patch_direct_strings(data, {}, {0x0010FE: ""}, {}, {})

    def test_live_promoted_lana_name_is_declared(self):
        row = next(row for row in self.result["candidates"] if row["address"] == "0x097418")
        self.assertEqual(row["ownership"], "declared_direct_patch")
        self.assertEqual(row["target_korean"], "라나")
        self.assertTrue(row["modified"])

    def test_promoted_name_table_record_is_declared_and_modified(self):
        row = next(row for row in self.result["candidates"] if row["address"] == "0x097462")
        self.assertEqual(row["ownership"], "declared_direct_patch")
        self.assertEqual(row["target_korean"], "가면기사")
        self.assertTrue(row["modified"])

    def test_late_name_batch_is_stable_and_unsafe_flag_is_idempotent(self):
        self.assertEqual(len(builder.LATE_DIRECT_NAME_GLYPH_OFFSETS), 26)
        for address in builder.LATE_DIRECT_NAME_GLYPH_OFFSETS:
            self.assertIn(address, builder.DIRECT_STRING_PATCHES)
        for address, text in builder.UNSAFE_DIRECT_NAME_PATCHES.items():
            self.assertEqual(
                text,
                builder.DIRECT_STRING_PATCHES[address],
            )

    def test_rendered_non_global_ranges_are_classified(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        self.assertEqual(
            rows["0x05F296"]["ownership"], "structured_game_data_false_positive"
        )
        local = next(
            row for row in self.result["candidates"]
            if row["ownership"] == "local_token_stream"
        )
        self.assertEqual(local["ownership"], "local_token_stream")

    def test_credits_and_name_entry_resources_are_classified(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        credit = rows["0x0A344A"]
        self.assertEqual(credit["ownership"], "declared_credits_translation")
        self.assertIn("시부야 미치오", credit["target_korean"])
        self.assertTrue(credit["modified"])
        self.assertTrue(credit["relocated_pointer"].startswith("0x2B"))
        self.assertEqual(rows["0x0A38A6"]["ownership"], "name_entry_resource")

    def test_pointer_record_interiors_are_not_counted_as_unknown_text(self):
        interior = next(
            row for row in self.result["candidates"]
            if row["ownership"] == "pointer_table_record_interior"
        )
        self.assertIsNotNone(interior["target_korean"])

    def test_condition_glyph_pointer_starts_are_owned_records(self):
        row = next(row for row in self.result["candidates"] if row["address"] == "0x098746")
        self.assertEqual(row["ownership"], "pointer_table_record")
        self.assertEqual(row["owner"], "condition_glyph_lists[0]")

    def test_rendered_item_and_magic_data_ranges_are_classified(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        self.assertEqual(
            rows["0x060128"]["ownership"], "structured_game_data_false_positive"
        )
        self.assertEqual(rows["0x0A14AC"]["ownership"], "item_shop_local_resource")
        self.assertEqual(
            rows["0x082562"]["ownership"], "structured_game_data_false_positive"
        )
        self.assertEqual(
            rows["0x082B78"]["ownership"], "confirmed_unresolved_direct_message"
        )

    def test_game_over_is_intentionally_retained(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        self.assertEqual(
            rows["0x082B3C"]["ownership"],
            "intentionally_retained_system_label",
        )
        self.assertEqual(
            self.result["ownership_counts"]["confirmed_unpatched_system_message"],
            0,
        )
        self.assertEqual(
            self.result["ownership_counts"]["intentionally_retained_system_label"],
            1,
        )

    def test_ending_fragments_are_owned_by_full_record_translations(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        self.assertEqual(
            rows["0x09600E"]["ownership"], "declared_ending_translation"
        )
        self.assertTrue(rows["0x09600E"]["modified"])
        self.assertTrue(rows["0x09600E"]["relocated_pointer"].startswith("0x2D"))

    def test_character_epilogue_fragments_are_owned_by_full_translations(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        self.assertEqual(
            rows["0x09499C"]["ownership"], "declared_epilogue_translation"
        )
        self.assertEqual(
            rows["0x0896DE"]["ownership"], "declared_epilogue_translation"
        )
        self.assertEqual(
            self.result["ownership_counts"]["confirmed_untranslated_epilogue_fragment"],
            0,
        )
        self.assertEqual(
            self.result["ownership_counts"]["declared_epilogue_translation"],
            90,
        )
        self.assertTrue(rows["0x09499C"]["modified"])
        self.assertTrue(rows["0x09499C"]["relocated_pointer"].startswith("0x2C"))

    def test_ending_boundary_starts_at_first_ending_dialogue_record(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        self.assertEqual(
            rows["0x09525E"]["ownership"], "declared_epilogue_translation"
        )
        self.assertEqual(
            rows["0x095594"]["ownership"], "declared_ending_translation"
        )

    def test_final_rendered_gibberish_candidates_are_data_false_positives(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        self.assertEqual(
            rows["0x010976"]["ownership"], "executable_code_or_table_false_positive"
        )
        self.assertEqual(rows["0x09B006"]["ownership"], "local_token_stream")
        self.assertEqual(
            rows["0x0D09DC"]["ownership"], "structured_map_event_data_false_positive"
        )


if __name__ == "__main__":
    unittest.main()
