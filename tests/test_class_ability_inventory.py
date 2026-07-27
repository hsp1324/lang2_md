import json
from pathlib import Path
import unittest

from tools.class_ability_inventory import inventory, markdown_report


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
INVENTORY_JSON = ROOT / "localization/class_abilities.json"
INVENTORY_MARKDOWN = ROOT / "docs/class_ability_inventory.md"


class ClassAbilityInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes())

    def test_source_scope_and_reachability(self):
        self.assertEqual(self.result["ability_count"], 23)
        self.assertEqual(self.result["class_count"], 157)
        self.assertEqual(self.result["commander_count"], 10)
        self.assertEqual(
            self.result["natural_chain_missing_ability_ids"],
            [18],
        )
        self.assertEqual(
            self.result["natural_chain_missing_abilities"],
            ["텔레포트"],
        )
        self.assertEqual(
            self.result["runtime_contract"]["summon_command_mask"],
            "0x00800000",
        )

    def test_agent_is_not_claimed_as_reachable_or_deployed(self):
        agent = self.result["classes"][0x25]
        self.assertEqual(agent["class"]["ko"], "에이전트")
        self.assertFalse(agent["natural_chain_reachable"])
        self.assertEqual(agent["fixed_scenario_record_count"], 0)
        self.assertEqual(agent["ability_ids"], [4, 16, 18, 21])

    def test_maximal_magic_paths_are_recorded(self):
        hein = self.result["commanders"][4]
        jessica = self.result["commanders"][9]
        self.assertEqual(hein["name"], "헤인")
        self.assertEqual(hein["max_path_ability_count"], 13)
        self.assertIn(
            [0x03, 0x0A, 0x11, 0x15, 0x28],
            [row["class_ids"] for row in hein["max_paths"]],
        )
        self.assertEqual(jessica["name"], "제시카")
        self.assertEqual(jessica["max_path_ability_count"], 14)
        self.assertEqual(
            jessica["max_paths"][0]["class_ids"],
            [0x03, 0x08, 0x13, 0x14, 0x26],
        )

    def test_generated_files_match(self):
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
