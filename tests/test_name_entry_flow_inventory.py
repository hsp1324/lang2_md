import json
from pathlib import Path
import unittest

from tools.name_entry_flow_inventory import inventory, markdown_report


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
INVENTORY_JSON = ROOT / "localization/name_entry_flow_inventory.json"
INVENTORY_MARKDOWN = ROOT / "docs/name_entry_flow_inventory.md"


class NameEntryFlowInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()
        cls.result = inventory(cls.jp, cls.ko)

    def test_fixed_palette_flow_is_complete(self):
        scope = self.result["scope"]
        self.assertTrue(self.result["complete"])
        self.assertEqual(scope["source_input_model"], "fixed 95-glyph palette")
        self.assertEqual(
            scope["localized_input_model"],
            "fixed 57-syllable Korean palette",
        )
        self.assertEqual(scope["selectable_syllable_count"], 57)
        self.assertEqual(scope["unique_selectable_syllable_count"], 57)
        self.assertEqual(scope["maximum_name_syllables"], 8)
        self.assertFalse(
            scope["arbitrary_hangul_composition_required_for_localization"]
        )

    def test_source_ownership_is_locked(self):
        self.assertEqual(len(self.result["source_references"]), 9)
        self.assertEqual(len(self.result["source_locked_ranges"]), 5)
        self.assertTrue(
            all(row["verified"] for row in self.result["source_references"])
        )
        self.assertTrue(
            all(row["verified"] for row in self.result["source_locked_ranges"])
        )

    def test_every_syllable_has_the_expected_safe_bitmap_and_byte_mapping(self):
        glyphs = self.result["glyphs"]
        self.assertEqual(len(glyphs), 57)
        self.assertEqual(len({row["syllable"] for row in glyphs}), 57)
        self.assertEqual(len({row["index"] for row in glyphs}), 57)
        self.assertTrue(all(row["safe_glyph_bank"] for row in glyphs))
        self.assertTrue(all(row["bitmap_verified"] for row in glyphs))

    def test_reserved_controls_and_builder_regions_are_preserved(self):
        controls = self.result["structure"]["controls"]
        self.assertEqual(controls["blank_delete_index"], 0x54)
        self.assertEqual(controls["japanese_composite_reserved_index"], 70)
        self.assertEqual(controls["unused_index_count"], 38)
        self.assertTrue(controls["unused_indexes_blank"])
        self.assertEqual(controls["glyph_list_terminator"], "0xFFFF")
        self.assertTrue(controls["confirmation_hook_exact"])
        self.assertTrue(controls["confirmation_routine_exact"])
        self.assertTrue(
            all(
                row["builder_exact"]
                for row in self.result["structure"]["regions"]
            )
        )

    def test_representative_names_fit_the_palette_and_buffer(self):
        expected = {
            "엘윈",
            "리아나",
            "헤인",
            "레온",
            "베른하르트",
            "에그베르트",
            "발드",
            "레스터",
        }
        rows = self.result["representative_names"]
        self.assertEqual({row["name"] for row in rows}, expected)
        self.assertTrue(all(row["selectable"] for row in rows))
        self.assertTrue(all(row["syllable_count"] <= 8 for row in rows))

    def test_live_evidence_files_exist(self):
        self.assertEqual(len(self.result["live_evidence"]), 6)
        for row in self.result["live_evidence"]:
            self.assertTrue(row["exists"])
            self.assertTrue((ROOT / row["path"]).is_file())

    def test_source_and_production_mutations_are_rejected(self):
        source_mutation = bytearray(self.jp)
        source_mutation[0x02AC52] ^= 1
        with self.assertRaisesRegex(ValueError, "source reference changed"):
            inventory(bytes(source_mutation), self.ko)

        production_mutation = bytearray(self.ko)
        production_mutation[0x02B046] ^= 1
        with self.assertRaisesRegex(ValueError, "confirmation_hook"):
            inventory(self.jp, bytes(production_mutation))

    def test_generated_reports_are_current(self):
        self.assertEqual(
            json.loads(INVENTORY_JSON.read_text(encoding="utf-8")),
            self.result,
        )
        self.assertEqual(
            INVENTORY_MARKDOWN.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )


if __name__ == "__main__":
    unittest.main()
