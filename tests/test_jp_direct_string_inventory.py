from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_direct_string_inventory import inventory, scan_candidates


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class JapaneseDirectStringInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.result = inventory(cls.japanese, KO_ROM.read_bytes())

    def test_candidate_baseline(self):
        self.assertEqual(len(scan_candidates(self.japanese)), 783)
        self.assertEqual(self.result["candidate_count"], 783)

    def test_known_magic_string_is_declared(self):
        row = next(row for row in self.result["candidates"] if row["address"] == "0x082BFE")
        self.assertEqual(row["ownership"], "declared_direct_patch")
        self.assertEqual(row["target_korean"], "마법화살")
        self.assertTrue(row["modified"])

    def test_unclassified_candidates_remain_unreviewed(self):
        counts = self.result["ownership_counts"]
        self.assertGreater(counts["unclassified_candidate"], 0)
        self.assertTrue(
            all(
                not row["reviewed"]
                for row in self.result["candidates"]
                if row["ownership"] == "unclassified_candidate"
            )
        )

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

    def test_known_unsafe_name_table_is_not_unclassified(self):
        row = next(row for row in self.result["candidates"] if row["address"] == "0x097418")
        self.assertEqual(row["ownership"], "known_unsafe_name_record")
        self.assertEqual(row["target_korean"], "라나")

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
        self.assertEqual(rows["0x0A344A"]["ownership"], "confirmed_credits_record")
        self.assertEqual(rows["0x0A38A6"]["ownership"], "name_entry_resource")

    def test_pointer_record_interiors_are_not_counted_as_unknown_text(self):
        interior = next(
            row for row in self.result["candidates"]
            if row["ownership"] == "pointer_table_record_interior"
        )
        self.assertIsNotNone(interior["target_korean"])


if __name__ == "__main__":
    unittest.main()
