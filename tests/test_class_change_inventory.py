import json
from pathlib import Path
import unittest

from tools.class_change_inventory import inventory, markdown_report


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
INVENTORY_JSON = ROOT / "localization/class_change_chains.json"
INVENTORY_MARKDOWN = ROOT / "docs/class_change_chain_inventory.md"


class ClassChangeInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes())

    def test_source_baseline_and_live_scope(self):
        self.assertEqual(self.result["source_pointer_table"], "0x08253A")
        self.assertEqual(self.result["commander_count"], 10)
        self.assertEqual(self.result["transition_count"], 100)
        self.assertEqual(self.result["unique_transition_count"], 76)
        self.assertEqual(self.result["live_verified_transition_count"], 2)
        self.assertEqual(self.result["application_verified_transition_count"], 1)

        verified = [
            (commander["id"], transition)
            for commander in self.result["commanders"]
            for transition in commander["transitions"]
            if transition["live_verified"]
        ]
        self.assertEqual(len(verified), 2)
        commander_id, transition = verified[0]
        self.assertEqual(commander_id, 1)
        self.assertEqual(transition["current"]["id"], 1)
        self.assertEqual(
            [candidate["id"] for candidate in transition["candidates"]],
            [4, 5, 10],
        )
        self.assertTrue(transition["application_verified"])

        commander_id, transition = verified[1]
        self.assertEqual(commander_id, 9)
        self.assertEqual(transition["current"]["id"], 0x10)
        self.assertEqual(
            [candidate["id"] for candidate in transition["candidates"]],
            [0x1D, 0x1F, 0x19],
        )
        self.assertFalse(transition["application_verified"])

    def test_generated_files_match(self):
        self.assertEqual(
            json.loads(INVENTORY_JSON.read_text(encoding="utf-8")), self.result
        )
        self.assertEqual(
            INVENTORY_MARKDOWN.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )


if __name__ == "__main__":
    unittest.main()
