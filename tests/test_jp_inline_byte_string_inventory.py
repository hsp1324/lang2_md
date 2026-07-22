from pathlib import Path
import unittest

from tools.jp_inline_byte_string_inventory import inventory, markdown_report


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
JSON_PATH = ROOT / "localization/inline_byte_strings.json"
MARKDOWN_PATH = ROOT / "docs/inline_byte_string_inventory.md"


class JapaneseInlineByteStringInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes(), KO_ROM.read_bytes())

    def test_conservative_candidate_baseline_has_no_unknown_owner(self):
        self.assertEqual(self.result["halfwidth_candidate_count"], 513)
        self.assertEqual(self.result["ascii_candidate_count"], 133)
        self.assertEqual(self.result["candidate_count"], 646)
        self.assertEqual(self.result["unclassified_count"], 0)

    def test_three_signal_false_positives_have_specific_owners(self):
        rows = {row["address"]: row for row in self.result["candidates"]}
        expected = {
            "0x0096C2": ("BEB9", "executable_code_or_table"),
            "0x060D0D": ("DUR", "structured_game_data"),
            "0x0A4381": ("ｸｹｺ", "structured_character_resource"),
            "0x0A44F3": ("ｫｵｿ", "title_layout_data"),
        }
        for address, (text, category) in expected.items():
            with self.subTest(address=address):
                self.assertEqual(rows[address]["original_text"], text)
                self.assertEqual(rows[address]["category"], category)

    def test_discard_prompt_is_owned_but_not_overclaimed_as_live_verified(self):
        prompt = self.result["discard_prompt"]
        self.assertEqual(prompt["target_korean"], "버릴 아이템")
        self.assertTrue(prompt["hook_installed"])
        self.assertFalse(prompt["live_verified"])

    def test_fukuro_is_the_final_sound_test_label_not_a_summon_table(self):
        sound = self.result["sound_test"]
        self.assertEqual(sound["record_count"], 77)
        self.assertGreater(sound["japanese_label_count"], 0)
        self.assertEqual(sound["rows"][-1]["sound_id"], "0x6C")
        self.assertEqual(sound["rows"][-1]["original_label"], "ﾌｸﾛｳ")
        self.assertEqual(sound["localized_count"], 0)

    def test_generated_reports_match(self):
        import json

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
