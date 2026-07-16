from pathlib import Path
import unittest

from tools.jp_resource_inventory import inventory, markdown_report


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class JapaneseResourceInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes(), KO_ROM.read_bytes())

    def test_resource_counts(self):
        groups = self.result["groups"]
        expected = {
            "conditions": (32, 31),
            "scenario_descriptions": (31, 31),
            "item_names": (38, 38),
            "item_descriptions": (37, 37),
            "item_word_names": (37, 37),
            "level_item_system_messages": (11, 11),
            "magic_names": (23, 23),
            "mercenary_battle_names": (15, 15),
            "battle_status_messages": (3, 3),
        }
        self.assertEqual(
            {name: (group["entry_count"], group["modified_count"]) for name, group in groups.items()},
            expected,
        )

    def test_review_is_not_inferred_from_byte_changes(self):
        for group in self.result["groups"].values():
            self.assertEqual(group["reviewed_count"], 0)
            self.assertEqual(group["live_verified_count"], 0)
            self.assertTrue(all(not entry["reviewed"] for entry in group["entries"]))

    def test_known_magic_and_mercenary_targets(self):
        groups = self.result["groups"]
        self.assertEqual(groups["magic_names"]["entries"][0]["target_korean"], "매직애로우")
        self.assertEqual(groups["mercenary_battle_names"]["entries"][0]["target_korean"], "파이크")

    def test_report_describes_all_condition_records(self):
        report = markdown_report(self.result)
        self.assertIn("builder patches Scenario 1-31", report)
        self.assertIn("preserves the final preparation-UI record", report)
        self.assertNotIn("patches only Scenario 1", report)


if __name__ == "__main__":
    unittest.main()
